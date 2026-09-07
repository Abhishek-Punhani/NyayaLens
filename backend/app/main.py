"""
NyayaLens Backend — FastAPI Application

Handles tool calls from the Gemini Live voice frontend, routes them into
the LangGraph intake and analysis graphs, provides a WebSocket observability
feed for the judge-facing dashboard, and exposes a lawyer follow-up chat endpoint.

Architecture:
  Voice agent (Gemini Live) → POST /api/tool-call → LangGraph graph
  Document upload           → POST /api/upload-document → OCR agent → state update
  Dashboard                 → WebSocket /ws/{thread_id} → real-time state feed
  Lawyer chat               → POST /api/session/{id}/chat → RAG-grounded answer
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.agents.analysis_agents import lawyer_chat
from app.agents.ocr_agent import extract_document
from app.config import GOOGLE_API_KEY, MODEL_FLASH
from app.graphs.analysis_graph import analysis_graph
from app.graphs.intake_graph import intake_graph
from app.legal_data.property_dispute_schema import get_missing_fields
from app.state import (
    CaseState,
    CitationRecord,
    ConsentRecord,
    DocumentRecord,
    Fact,
    FuzzinessFlag,
    ReadinessSignals,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NyayaLens Backend",
    version="3.0.0",
    description="Voice-first legal case intelligence system for Indian property-possession disputes.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten before production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state stores
# ---------------------------------------------------------------------------
# session metadata (thread_id → dict)
active_sessions: Dict[str, Dict[str, Any]] = {}

# WebSocket connections per thread_id
ws_connections: Dict[str, List[WebSocket]] = {}

# SSE subscriber queues per thread_id
sse_subscribers: Dict[str, List[asyncio.Queue]] = {}

# Background analysis tasks (thread_id → asyncio.Task)
analysis_tasks: Dict[str, asyncio.Task] = {}

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    language: str = "hi"
    lawyer_name: Optional[str] = None
    lawyer_contact: Optional[str] = None


class ToolCallRequest(BaseModel):
    session_id: str
    tool_name: str
    arguments: Dict[str, Any] = {}


class ChatRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Broadcast helpers (WebSocket + Server-Sent Events)
# ---------------------------------------------------------------------------

async def broadcast(thread_id: str, payload: dict) -> None:
    """Send a JSON payload to all connected WebSocket clients and SSE queues for a session."""
    dead: list[WebSocket] = []
    for ws in ws_connections.get(thread_id, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_connections.get(thread_id, []).remove(ws)

    # Deliver to SSE thinking subscribers
    for q in sse_subscribers.get(thread_id, []):
        try:
            await q.put(payload)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Graph helpers
# ---------------------------------------------------------------------------

def _graph_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _get_current_state(thread_id: str) -> Optional[CaseState]:
    """Retrieve the latest checkpointed state for a thread."""
    try:
        state_snapshot = intake_graph.get_state(_graph_config(thread_id))
        if state_snapshot and state_snapshot.values:
            return state_snapshot.values  # type: ignore[return-value]
    except Exception as exc:
        logger.warning("Could not fetch state for %s: %s", thread_id, exc)
    return None


def _serialize_state(state: CaseState) -> dict:
    """JSON-serializable dict from CaseState (handles Pydantic models)."""
    out: dict = {}
    for k, v in state.items():
        if v is None:
            out[k] = None
        elif isinstance(v, list):
            out[k] = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in v
            ]
        elif hasattr(v, "model_dump"):
            out[k] = v.model_dump()
        else:
            try:
                json.dumps(v)   # test serializability
                out[k] = v
            except (TypeError, ValueError):
                out[k] = str(v)
    return out


def _initial_state(
    thread_id: str,
    language: str,
    lawyer_name: Optional[str],
    lawyer_contact: Optional[str],
) -> CaseState:
    return {
        "thread_id": thread_id,
        "language": language,
        "case_type": "property_dispute",
        "law_version_context": "unknown",
        "dispossession_track": "not_determined",
        "intake_phase": "open_narrative",
        "messages": [],
        "facts": [],
        "documents": [],
        "entity_graph": {"nodes": [], "edges": []},
        "timeline": [],
        "fuzziness_flags": [],
        "consent": ConsentRecord(),
        "handoff_status": "pending",
        "lawyer_name": lawyer_name,
        "lawyer_contact": lawyer_contact,
        "precedents": [],
        "opposition_case": None,
        "witness_candidates": [],
        "arguments": [],
        "readiness_signals": None,
        "lawyer_packet_markdown": None,
        "lawyer_packet_json": None,
    }


# ---------------------------------------------------------------------------
# Tool-call routing logic
# ---------------------------------------------------------------------------

async def _handle_start_intake(session_id: str, args: dict) -> dict:
    """Initialise the intake graph for this session and return the opening disclosure."""
    initial = _initial_state(
        thread_id=session_id,
        language=active_sessions.get(session_id, {}).get("language", "hi"),
        lawyer_name=active_sessions.get(session_id, {}).get("lawyer_name"),
        lawyer_contact=active_sessions.get(session_id, {}).get("lawyer_contact"),
    )
    # Kick off graph with the opening disclosure message
    opening = HumanMessage(content="Namaskar. Main apni baat aapse share karna chahta hoon.")
    initial["messages"] = [opening]

    await intake_graph.ainvoke(initial, config=_graph_config(session_id))
    await broadcast(session_id, {"event": "intake_started", "session_id": session_id})

    return {
        "status": "started",
        "spoken_response": (
            "Namaskar. Main Nyaya hoon — ek AI sahayak jo aapke vakeel ke liye kaam karta hai. "
            "Aapki awaaz sirf case brief banane ke liye record hogi — aap kabhi bhi mana kar sakte hain. "
            "Kya aap taiyaar hain apni baat share karne ke liye?"
        ),
    }


async def _handle_submit_client_response(session_id: str, args: dict) -> dict:
    """Append client answer to conversation, run entity tracker and fuzziness detector."""
    raw_answer = args.get("raw_answer", "")
    turn_id = args.get("turn_id", f"turn_{uuid.uuid4().hex[:8]}")
    topic = args.get("topic", "general")

    if not raw_answer:
        return {"status": "error", "error": "raw_answer is required"}

    # Resume the graph with the client's answer
    from langgraph.types import Command
    try:
        state_snapshot = await intake_graph.ainvoke(
            Command(resume=raw_answer),
            config=_graph_config(session_id),
        )
    except Exception as exc:
        logger.error("Graph resume error for session %s: %s", session_id, exc)
        state_snapshot = {}

    current_state = _get_current_state(session_id)

    # Detect what changed
    fuzziness_flags = current_state.get("fuzziness_flags", []) if current_state else []
    unresolved = [f for f in fuzziness_flags if not f.resolved and f.blocks_handoff]
    missing = get_missing_fields(current_state.get("facts", []) if current_state else [])

    await broadcast(session_id, {
        "event": "response_processed",
        "topic": topic,
        "fuzziness_count": len(unresolved),
        "missing_fields": missing,
    })

    spoken_response = ""
    fuzziness_question = None

    # Return next fuzziness clarification if blocking flags exist
    if unresolved:
        fuzziness_question = unresolved[0].neutral_clarifying_question
        spoken_response = fuzziness_question
        await broadcast(session_id, {
            "event": "flag_raised",
            "flag": unresolved[0].model_dump(),
        })

    return {
        "status": "recorded",
        "fuzziness_detected": len(unresolved) > 0,
        "fuzziness_question": fuzziness_question,
        "spoken_response": spoken_response,
        "next_priority_field": missing[0] if missing else None,
        "topics_remaining": missing,
    }


async def _handle_flag_document_upload(session_id: str, args: dict) -> dict:
    """Register a document as requested, with BSA §63 flag for recordings."""
    doc_type = args.get("document_type", "unknown")
    has_recording = args.get("has_recording", False)

    doc = DocumentRecord(
        doc_id=f"DOC-{uuid.uuid4().hex[:8]}",
        doc_type=doc_type,
        bsa63_certificate_needed=has_recording,
        upload_status="requested",
    )

    # Update state via graph
    try:
        current = _get_current_state(session_id)
        if current is not None:
            existing_docs = list(current.get("documents", []))
            existing_docs.append(doc)
            await intake_graph.aupdate_state(
                _graph_config(session_id),
                {"documents": existing_docs},
            )
    except Exception as exc:
        logger.warning("Could not update doc state: %s", exc)

    bsa_note = ""
    if has_recording:
        bsa_note = (
            " Is recording ke liye ek technical certificate bhi lagega jisme device ka "
            "maalik aur ek expert dono sign karte hain — isliye abhi device ke baare mein "
            "bata dijiye."
        )

    return {
        "status": "document_flagged",
        "doc_id": doc.doc_id,
        "bsa63_certificate_needed": has_recording,
        "spoken_response": (
            f"Theek hai, {doc_type} ki zaroorat hogi. Kripya ise WhatsApp photo ya upload karein.{bsa_note}"
        ),
    }


async def _handle_update_dispossession_track(session_id: str, args: dict) -> dict:
    """Update the dispossession track and gate subsequent retrieval."""
    track = args.get("track", "unclear")
    try:
        await intake_graph.aupdate_state(
            _graph_config(session_id),
            {"dispossession_track": track},
        )
    except Exception as exc:
        logger.warning("Could not update track: %s", exc)
    return {"status": "track_updated", "dispossession_track": track}


async def _handle_trigger_analysis(
    session_id: str,
    args: dict,
    background_tasks: BackgroundTasks,
) -> dict:
    """Launch the parallel analysis graph as a background task."""
    current = _get_current_state(session_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Session state not found")

    async def _run_analysis():
        try:
            await analysis_graph.ainvoke(current, config=_graph_config(session_id))
            await broadcast(session_id, {"event": "analysis_complete"})
            final = _get_current_state(session_id)
            if final and final.get("readiness_signals"):
                rs = final["readiness_signals"]
                await broadcast(session_id, {
                    "event": "readiness_ready",
                    "readiness": rs.model_dump() if hasattr(rs, "model_dump") else rs,
                })
            if final and final.get("lawyer_packet_markdown"):
                await broadcast(session_id, {"event": "packet_ready"})
        except Exception as exc:
            logger.error("Background analysis failed for %s: %s", session_id, exc)
            await broadcast(session_id, {"event": "analysis_error", "error": str(exc)})

    task = asyncio.create_task(_run_analysis())
    analysis_tasks[session_id] = task

    return {
        "status": "analysis_started",
        "estimated_time_sec": 30,
        "spoken_response": (
            "Shukriya. Main aapki saari jaankari vakeel ke liye tayaar kar raha hoon. "
            "Thodi der mein poora brief ready ho jaayega."
        ),
    }


async def _handle_confirm_step(session_id: str, args: dict) -> dict:
    """Resume the confirmation flow graph with the client's consent answer."""
    step = args.get("step", "recipient")
    confirmed = args.get("confirmed", False)

    answer = "haan" if confirmed else "nahin"

    try:
        from langgraph.types import Command
        await intake_graph.ainvoke(
            Command(resume=answer),
            config=_graph_config(session_id),
        )
    except Exception as exc:
        logger.error("Confirmation step resume error: %s", exc)

    current = _get_current_state(session_id)
    handoff_status = current.get("handoff_status", "pending") if current else "pending"

    if handoff_status == "confirmed":
        await broadcast(session_id, {"event": "packet_sending", "session_id": session_id})
        return {
            "status": "confirmed",
            "spoken_response": "Bahut acha. Brief abhi bheja ja raha hai. Vakeel Sahab jald hi aapse sampark karenge.",
        }
    elif handoff_status == "declined":
        return {
            "status": "declined",
            "spoken_response": "Theek hai — kya aap kuch badalna chahte hain?",
        }
    else:
        # Find next step prompt from consent state
        consent = current.get("consent", ConsentRecord()) if current else ConsentRecord()
        next_prompt = ""
        if not consent.contents_confirmed:
            next_prompt = "Brief ke contents theek hain?"
        elif not consent.attachments_confirmed:
            next_prompt = "Documents attach karne hain?"
        elif not consent.permission_confirmed:
            next_prompt = "Bhejne ki anumati de dein?"
        return {"status": "pending", "spoken_response": next_prompt, "next_step": "contents"}


async def _handle_abort_and_revise(session_id: str, args: dict) -> dict:
    try:
        await intake_graph.aupdate_state(
            _graph_config(session_id),
            {"handoff_status": "declined"},
        )
    except Exception:
        pass
    return {
        "status": "revising",
        "return_to": "intake",
        "spoken_response": "Theek hai. Kya badalna hai — bata dijiye.",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "model_flash": MODEL_FLASH, "api_key_set": bool(GOOGLE_API_KEY)}


@app.post("/api/session/create")
async def create_session(request: CreateSessionRequest):
    """Create a new case session and initialise graph state."""
    thread_id = str(uuid.uuid4())
    active_sessions[thread_id] = {
        "language": request.language,
        "lawyer_name": request.lawyer_name,
        "lawyer_contact": request.lawyer_contact,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "INTAKE",
    }
    logger.info("Session created: %s", thread_id)
    return {"thread_id": thread_id, "status": "created"}


@app.post("/api/tool-call")
async def handle_tool_call(request: ToolCallRequest, background_tasks: BackgroundTasks):
    """
    Core routing endpoint — called by the Gemini Live voice agent after every tool call.
    Routes to the appropriate LangGraph action and returns the spoken response.
    """
    session_id = request.session_id
    tool_name = request.tool_name
    args = request.arguments

    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    logger.info("Tool call: session=%s tool=%s", session_id, tool_name)

    try:
        if tool_name == "start_intake":
            return await _handle_start_intake(session_id, args)

        elif tool_name == "submit_client_response":
            return await _handle_submit_client_response(session_id, args)

        elif tool_name == "flag_document_upload":
            return await _handle_flag_document_upload(session_id, args)

        elif tool_name == "update_dispossession_track":
            return await _handle_update_dispossession_track(session_id, args)

        elif tool_name == "request_clarification":
            flag_id = args.get("flag_id", "")
            question = args.get("question_asked", "")
            await broadcast(session_id, {"event": "clarification_asked", "flag_id": flag_id, "question": question})
            return {"status": "clarification_logged", "spoken_response": question}

        elif tool_name == "trigger_analysis":
            return await _handle_trigger_analysis(session_id, args, background_tasks)

        elif tool_name == "initiate_confirmation":
            from langgraph.types import Command
            # Move graph to confirmation_flow node
            await intake_graph.ainvoke(
                Command(goto="confirmation_flow"),
                config=_graph_config(session_id),
            )
            current = _get_current_state(session_id)
            lawyer_name = current.get("lawyer_name", "Vakeel Sahab") if current else "Vakeel Sahab"
            return {
                "status": "confirmation_started",
                "spoken_response": f"Maine ek case brief taiyaar kiya hai. Ise {lawyer_name} ko bhejna hai — kya ye sahi hai?",
                "consent_step": "recipient",
            }

        elif tool_name == "confirm_step":
            return await _handle_confirm_step(session_id, args)

        elif tool_name == "abort_and_revise":
            return await _handle_abort_and_revise(session_id, args)

        else:
            logger.warning("Unknown tool: %s", tool_name)
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Tool call error (%s): %s", tool_name, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/upload-document")
async def upload_document(
    session_id: str = Form(...),
    doc_type: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Accepts a document image, runs OCR via Gemini Vision, extracts facts,
    updates the session state, and broadcasts the result over WebSocket.
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        doc_record = await extract_document(image_bytes, doc_type, session_id)
    except Exception as exc:
        logger.error("OCR failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"OCR error: {exc}")

    # Append the document record to state
    try:
        current = _get_current_state(session_id)
        existing_docs = list(current.get("documents", []) if current else [])
        # Replace placeholder if doc_type matches a requested doc
        existing_docs = [d for d in existing_docs if d.doc_type != doc_type or d.upload_status != "requested"]
        existing_docs.append(doc_record)

        extracted_facts = doc_record.extracted_facts or []

        await intake_graph.aupdate_state(
            _graph_config(session_id),
            {
                "documents": existing_docs,
                "facts": extracted_facts,   # operator.add appends
            },
        )
    except Exception as exc:
        logger.warning("State update after OCR failed: %s", exc)

    await broadcast(session_id, {
        "event": "document_processed",
        "doc_id": doc_record.doc_id,
        "doc_type": doc_record.doc_type,
        "bsa63_needed": doc_record.bsa63_certificate_needed,
        "extracted_facts": len(doc_record.extracted_facts),
        "limitations_flag": doc_record.limitations_flag,
    })

    return {
        "doc_id": doc_record.doc_id,
        "ocr_status": doc_record.upload_status,
        "extracted_facts_count": len(doc_record.extracted_facts),
        "bsa63_needed": doc_record.bsa63_certificate_needed,
        "key_clauses": doc_record.key_clauses,
        "limitations_flag": doc_record.limitations_flag,
    }


@app.get("/api/session/{thread_id}")
async def get_session(thread_id: str):
    """Return full current state for the judge-facing observability dashboard."""
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    current = _get_current_state(thread_id)
    if current is None:
        return {"thread_id": thread_id, "status": "initializing", "state": {}}

    return {
        "thread_id": thread_id,
        "status": active_sessions[thread_id].get("status", "INTAKE"),
        "state": _serialize_state(current),
    }


@app.get("/api/session/{thread_id}/packet")
async def get_packet(thread_id: str):
    """Return the compiled lawyer packet (only available after analysis completes)."""
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    current = _get_current_state(thread_id)
    if not current or not current.get("lawyer_packet_markdown"):
        raise HTTPException(status_code=404, detail="Packet not yet compiled — analysis may still be running")

    return {
        "thread_id": thread_id,
        "markdown": current.get("lawyer_packet_markdown", ""),
        "json": current.get("lawyer_packet_json", {}),
        "whatsapp_summary": current.get("lawyer_packet_json", {}).get("whatsapp_summary", ""),
    }


@app.post("/api/session/{thread_id}/chat")
async def lawyer_follow_up_chat(thread_id: str, request: ChatRequest):
    """
    Lawyer follow-up chat endpoint — RAG-grounded, same citation discipline
    as every other agent. No win probability.
    """
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    current = _get_current_state(thread_id)
    packet_json = current.get("lawyer_packet_json", {}) if current else {}

    result = await lawyer_chat(
        question=request.question,
        packet_json=packet_json,
        thread_id=thread_id,
    )

    return {
        "thread_id": thread_id,
        "question": request.question,
        "answer": result.get("answer", ""),
        "citations_used": [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in result.get("citations_used", [])
        ],
    }


@app.get("/api/session/{thread_id}/thinking-stream")
async def thinking_stream(thread_id: str):
    """
    Server-Sent Events (SSE) endpoint for streaming agent cognitive reasoning
    and LangGraph internal deliberation directly to the Claude-style thinking block.
    """
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    queue: asyncio.Queue = asyncio.Queue()
    sse_subscribers.setdefault(thread_id, []).append(queue)
    logger.info("SSE client connected for session %s (total: %d)", thread_id, len(sse_subscribers[thread_id]))

    async def event_generator():
        try:
            # Yield initial connection heartbeat
            init_msg = json.dumps({"type": "connected", "thread_id": thread_id, "timestamp": datetime.now(timezone.utc).isoformat()})
            yield f"data: {init_msg}\n\n"

            while True:
                payload = await queue.get()
                data_str = json.dumps(payload, ensure_ascii=False)
                yield f"data: {data_str}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if thread_id in sse_subscribers and queue in sse_subscribers[thread_id]:
                sse_subscribers[thread_id].remove(queue)
            logger.info("SSE client disconnected for session %s", thread_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    Real-time observability feed for the judge-facing dashboard.
    Broadcasts events: fact_added, flag_raised, document_processed,
    analysis_complete, readiness_ready, packet_ready.
    """
    await websocket.accept()
    ws_connections.setdefault(thread_id, []).append(websocket)
    logger.info("WebSocket connected: %s (total: %d)", thread_id, len(ws_connections[thread_id]))

    # Send current state snapshot on connect
    current = _get_current_state(thread_id)
    if current:
        await websocket.send_json({
            "event": "state_snapshot",
            "state": _serialize_state(current),
        })

    try:
        while True:
            # Keep connection alive — client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_connections.get(thread_id, []).remove(websocket)
        logger.info("WebSocket disconnected: %s", thread_id)


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("NyayaLens backend v3 starting up")
    logger.info("API key set: %s", bool(GOOGLE_API_KEY))
    # Auto-seed ChromaDB corpus if collection is empty and key is real
    from app.startup import validate_startup_config
    asyncio.create_task(validate_startup_config())


@app.on_event("shutdown")
async def shutdown_event():
    # Cancel any running analysis tasks
    for tid, task in list(analysis_tasks.items()):
        if not task.done():
            task.cancel()
    logger.info("NyayaLens backend shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
