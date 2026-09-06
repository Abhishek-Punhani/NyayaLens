"""
NyayaLens — Intake Agents
All async node functions for the LangGraph intake graph.
Each uses real LLM calls via langchain_google_genai, wired to the
production prompts library. Evidence provenance is set at write-time on
every Fact produced.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt

from app.config import GOOGLE_API_KEY, MODEL_FLASH
from app.legal_data.property_dispute_schema import get_missing_fields, get_next_priority_field
from app.legal_data.section_mapping import get_applicable_law
from app.prompts.global_policy import inject_policy
from app.prompts.analysis_prompts import CONFIRMATION_FLOW_PROMPTS
from app.prompts.intake_prompts import (
    CASE_TYPE_ROUTER_PROMPT,
    CROSS_QUESTION_PROMPT,
    DOCUMENT_REQUEST_PROMPT,
    FACT_EXTRACTION_PROMPT,
    FUZZINESS_DETECTOR_PROMPT,
)
from app.state import (
    CaseState,
    ConsentRecord,
    DocumentRecord,
    Fact,
    FuzzinessFlag,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM factory
# ---------------------------------------------------------------------------

def _flash_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_FLASH,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,       # low temp for structured output
        max_retries=2,
    )


def _facts_to_json(facts: list[Fact]) -> str:
    return json.dumps([f.model_dump() for f in facts], ensure_ascii=False, indent=2)


def _flags_to_json(flags: list[FuzzinessFlag]) -> str:
    return json.dumps([f.model_dump() for f in flags], ensure_ascii=False, indent=2)


def _parse_json_block(text: str) -> Any:
    """Extract JSON from LLM output that may be wrapped in markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Strip opening and closing fence lines
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


# ---------------------------------------------------------------------------
# Node 1 — Case-Type Router
# ---------------------------------------------------------------------------

async def case_type_router_node(state: CaseState) -> dict:
    """
    Determines case type from the client's opening narrative and resolves
    the dispossession-recency track for property disputes.
    """
    try:
        messages = state.get("messages", [])
        language = state.get("language", "hi")

        llm = _flash_llm()
        system_prompt = inject_policy(CASE_TYPE_ROUTER_PROMPT.format(language=language))

        # Build a lightweight conversation so the LLM has context
        conversation = [("system", system_prompt)]
        for msg in messages[-6:]:   # last 6 messages for context
            if isinstance(msg, HumanMessage):
                conversation.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                conversation.append(("ai", msg.content))

        # Ask the router to classify and produce a JSON result
        conversation.append((
            "human",
            "Based on the conversation so far, return JSON with keys: "
            "case_type (property_dispute|motor_accident|criminal_fir|unknown), "
            "dispossession_track (section_6|title_suit|unclear|not_determined), "
            "reason (one sentence). Only JSON, no markdown."
        ))

        response = await llm.ainvoke(conversation)
        result = _parse_json_block(response.content)

        case_type = result.get("case_type", "property_dispute")
        track = result.get("dispossession_track", "not_determined")

        # Determine law version from event date if known in existing facts
        facts = state.get("facts", [])
        event_date_fact = next(
            (f for f in facts if f.field == "dispossession_recency"), None
        )
        law_ctx = get_applicable_law(event_date_fact.value if event_date_fact else None)

        return {
            "case_type": case_type,
            "dispossession_track": track,
            "law_version_context": law_ctx,
            "intake_phase": "cross_question",
        }

    except Exception as exc:
        logger.error("case_type_router_node error: %s", exc, exc_info=True)
        return {
            "case_type": "property_dispute",
            "dispossession_track": "not_determined",
            "law_version_context": "unknown",
            "intake_phase": "cross_question",
        }


# ---------------------------------------------------------------------------
# Node 2 — Cross-Questioning Agent
# ---------------------------------------------------------------------------

async def cross_question_node(state: CaseState) -> dict:
    """
    Conducts the evidence-driven cross-questioning interview.
    Uses interrupt() to pause the graph and wait for the client's answer.
    Each new fact is written with evidence_type=CLIENT_STATED.
    """
    try:
        llm = _flash_llm()
        language = state.get("language", "hi")
        facts = state.get("facts", [])
        fuzziness_flags = state.get("fuzziness_flags", [])
        track = state.get("dispossession_track", "not_determined")

        missing_fields = get_missing_fields(facts)
        unresolved_flags = [f for f in fuzziness_flags if not f.resolved and f.blocks_handoff]

        system_prompt = inject_policy(CROSS_QUESTION_PROMPT.format(
            language=language,
            facts_json=_facts_to_json(facts),
            dispossession_track=track,
            missing_fields=json.dumps(missing_fields),
            fuzziness_flags=_flags_to_json(unresolved_flags),
        ))

        # Get the last user turn as context
        messages = state.get("messages", [])
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", last_user_msg or "Namaskar, mujhe apni baat batani hai."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            # Fallback: treat entire response as the spoken_response
            parsed = {
                "spoken_response": response.content,
                "next_question": response.content,
                "reason": "llm_free_text",
                "updated_fact_candidates": [],
                "requires_human_review": False,
            }

        next_question = parsed.get("next_question", parsed.get("spoken_response", ""))
        spoken_response = parsed.get("spoken_response", next_question)
        candidates = parsed.get("updated_fact_candidates", [])

        # ── Pause graph — wait for client's spoken answer ────────────────────
        client_answer: str = interrupt(value={
            "spoken_response": spoken_response,
            "next_question": next_question,
        })

        # ── Write new facts with evidence provenance ─────────────────────────
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        new_facts: list[Fact] = []

        for candidate in candidates:
            new_facts.append(Fact(
                fact_id=f"F-{uuid.uuid4().hex[:8]}",
                field=candidate.get("field", "unknown"),
                value=candidate.get("value", ""),
                evidence_type="CLIENT_STATED",   # provenance set at write-time
                source_ref=turn_id,
                confidence=candidate.get("confidence", 0.7),
                status="unconfirmed",
                contradicts=[],
            ))

        # Also write the raw client answer as a fact
        if client_answer:
            next_field = get_next_priority_field(facts + new_facts) or "general_statement"
            new_facts.append(Fact(
                fact_id=f"F-{uuid.uuid4().hex[:8]}",
                field=next_field,
                value=client_answer,
                evidence_type="CLIENT_STATED",
                source_ref=turn_id,
                confidence=0.6,
                status="unconfirmed",
                contradicts=[],
            ))

        return {
            "facts": new_facts,
            "messages": [
                AIMessage(content=spoken_response),
                HumanMessage(content=client_answer),
            ],
        }

    except Exception as exc:
        logger.error("cross_question_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 3 — Fuzziness Detector
# ---------------------------------------------------------------------------

async def fuzziness_detector_node(state: CaseState) -> dict:
    """
    Runs after every new fact is added. Detects contradictions, timeline
    conflicts, vague accounts, missing documents, and jurisdiction ambiguity.
    Never concludes anyone is lying — only flags specific discrepancies.
    """
    try:
        llm = _flash_llm()
        facts = state.get("facts", [])
        timeline = state.get("timeline", [])

        if not facts:
            return {"fuzziness_flags": []}

        system_prompt = inject_policy(FUZZINESS_DETECTOR_PROMPT.format(
            facts_json=_facts_to_json(facts),
            timeline_json=json.dumps(timeline, ensure_ascii=False),
        ))

        response = await llm.ainvoke([("system", system_prompt)])

        try:
            raw_flags = _parse_json_block(response.content)
            if not isinstance(raw_flags, list):
                raw_flags = raw_flags.get("flags", [])
        except (json.JSONDecodeError, AttributeError):
            return {"fuzziness_flags": []}

        # Validate and convert to FuzzinessFlag objects
        new_flags: list[FuzzinessFlag] = []
        existing_ids = {f.flag_id for f in state.get("fuzziness_flags", [])}

        for raw in raw_flags:
            try:
                flag = FuzzinessFlag(
                    flag_id=raw.get("flag_id", f"FZ-{uuid.uuid4().hex[:8]}"),
                    flag_type=raw["type"],
                    severity=raw.get("severity", "medium"),
                    fact_refs=raw.get("fact_refs", []),
                    explanation=raw.get("explanation", ""),
                    neutral_clarifying_question=raw.get("neutral_clarifying_question", ""),
                    blocks_handoff=raw.get("blocks_handoff", False),
                    resolved=False,
                )
                # Skip duplicates (same flag_id)
                if flag.flag_id not in existing_ids:
                    new_flags.append(flag)
                    existing_ids.add(flag.flag_id)
            except Exception as parse_err:
                logger.warning("Could not parse fuzziness flag: %s — %s", raw, parse_err)

        return {"fuzziness_flags": new_flags}

    except Exception as exc:
        logger.error("fuzziness_detector_node error: %s", exc, exc_info=True)
        return {"fuzziness_flags": []}


# ---------------------------------------------------------------------------
# Node 4 — Entity / Character-Tree Tracker
# ---------------------------------------------------------------------------

async def entity_tracker_node(state: CaseState) -> dict:
    """
    Extracts people, properties, events, relationships, and timeline entries
    from the conversation. Updates the entity graph and timeline.
    """
    try:
        llm = _flash_llm()
        messages = state.get("messages", [])
        facts = state.get("facts", [])

        # Build transcript string from messages
        transcript_lines = []
        for msg in messages[-20:]:   # last 20 turns
            if isinstance(msg, HumanMessage):
                transcript_lines.append(f"CLIENT: {msg.content}")
            elif isinstance(msg, AIMessage):
                transcript_lines.append(f"NYAYA: {msg.content}")
        transcript = "\n".join(transcript_lines)

        system_prompt = inject_policy(FACT_EXTRACTION_PROMPT.format(
            transcript=transcript,
            existing_facts=_facts_to_json(facts),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Extract entities and timeline. Return JSON with keys: entity_graph, timeline, new_facts."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            return {}

        entity_graph = parsed.get("entity_graph", state.get("entity_graph", {"nodes": [], "edges": []}))
        timeline = parsed.get("timeline", state.get("timeline", []))

        # Parse new facts from extraction (DOCUMENT_EXTRACTED or CLIENT_STATED)
        raw_facts = parsed.get("new_facts", [])
        new_facts: list[Fact] = []
        for rf in raw_facts:
            try:
                evidence_type = rf.get("evidence_type", "UNKNOWN")
                if evidence_type not in ("CLIENT_STATED", "DOCUMENT_EXTRACTED", "LEGAL_SOURCE", "INFERENCE", "UNKNOWN"):
                    evidence_type = "UNKNOWN"
                new_facts.append(Fact(
                    fact_id=rf.get("fact_id", f"F-{uuid.uuid4().hex[:8]}"),
                    field=rf.get("field", "unknown"),
                    value=rf.get("value", ""),
                    evidence_type=evidence_type,
                    source_ref=rf.get("source_ref", "entity_tracker"),
                    confidence=rf.get("confidence", 0.5),
                    status="unconfirmed",
                    contradicts=rf.get("contradicts", []),
                ))
            except Exception:
                pass

        return {
            "entity_graph": entity_graph,
            "timeline": timeline,
            "facts": new_facts,
        }

    except Exception as exc:
        logger.error("entity_tracker_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 5 — Document Request Agent
# ---------------------------------------------------------------------------

async def document_request_node(state: CaseState) -> dict:
    """
    Identifies which documents are needed, issues a specific request for each,
    and handles the special BSA §63 certificate question for any recordings.
    Uses interrupt() to wait for the client to upload.
    """
    try:
        llm = _flash_llm()
        language = state.get("language", "hi")
        facts = state.get("facts", [])
        fuzziness_flags = state.get("fuzziness_flags", [])
        lawyer_name = state.get("lawyer_name") or "Vakeel Sahab"

        system_prompt = inject_policy(DOCUMENT_REQUEST_PROMPT.format(
            language=language,
            facts_json=_facts_to_json(facts),
            fuzziness_flags=_flags_to_json(fuzziness_flags),
            lawyer_name=lawyer_name,
        ))

        response = await llm.ainvoke([("system", system_prompt)])

        try:
            doc_requests = _parse_json_block(response.content)
            if not isinstance(doc_requests, list):
                doc_requests = doc_requests.get("requests", [])
        except json.JSONDecodeError:
            doc_requests = []

        # Build DocumentRecord objects for each requested document
        new_docs: list[DocumentRecord] = []
        request_message_parts: list[str] = []

        for req in doc_requests:
            doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
            is_recording = req.get("material_or_optional", "material") == "material" and (
                "recording" in req.get("document_type", "").lower()
                or "video" in req.get("document_type", "").lower()
                or "whatsapp" in req.get("document_type", "").lower()
            )
            doc = DocumentRecord(
                doc_id=doc_id,
                doc_type=req.get("document_type", "unknown"),
                bsa63_certificate_needed=is_recording,
                upload_status="requested",
                limitations_flag=None,
            )
            new_docs.append(doc)
            request_message_parts.append(req.get("upload_instruction", f"Kripya {doc.doc_type} upload karein."))

        request_message = " ".join(request_message_parts) or "Kripya zaruri documents upload karein."

        # ── Pause graph — wait for client to upload ──────────────────────────
        upload_confirmation: str = interrupt(value={
            "spoken_response": request_message,
            "pending_documents": [d.doc_id for d in new_docs],
        })

        return {
            "documents": new_docs,
            "messages": [
                AIMessage(content=request_message),
                HumanMessage(content=upload_confirmation or "Document upload kiya."),
            ],
        }

    except Exception as exc:
        logger.error("document_request_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 6 — Confirmation Flow (4-step finite-state consent)
# ---------------------------------------------------------------------------

_AMBIGUOUS = {"shayad", "pata nahi", "dekh lo", "maybe", "not sure", "hmm", "ummm"}
_AFFIRMATIVE = {"haan", "yes", "ha", "bhejiye", "theek hai", "ok", "okay", "bilkul", "sure"}
_NEGATIVE = {"nahin", "nahi", "no", "nope", "mat bhejo", "ruk jao", "cancel"}


def _parse_consent(answer: str) -> str:
    """Returns 'yes', 'no', or 'ambiguous'."""
    lower = answer.strip().lower()
    if any(w in lower for w in _AFFIRMATIVE):
        return "yes"
    if any(w in lower for w in _NEGATIVE):
        return "no"
    if any(w in lower for w in _AMBIGUOUS):
        return "ambiguous"
    # Heuristic: short affirmative
    if len(lower) <= 3 and lower in {"ha", "ok"}:
        return "yes"
    return "ambiguous"


async def confirmation_flow_node(state: CaseState) -> dict:
    """
    4-step finite-state consent flow. Each step is a separate interrupt() call.
    Only advances on unambiguous confirmation. On any 'no', aborts and returns
    to intake.

    Writes a ConsentRecord with per-step booleans and a UTC timestamp.
    """
    facts = state.get("facts", [])
    documents = state.get("documents", [])
    fuzziness_flags = state.get("fuzziness_flags", [])
    lawyer_name = state.get("lawyer_name") or "Vakeel Sahab"
    lawyer_contact = state.get("lawyer_contact") or "WhatsApp"

    # Summary strings for the confirmation messages
    facts_summary = f"{len(facts)} baatein"
    timeline_events = state.get("timeline", [])
    timeline_summary = f"{len(timeline_events)} ghataayein"
    open_flags = [f for f in fuzziness_flags if not f.resolved]
    doc_list = ", ".join(d.doc_type for d in documents) if documents else "koi document nahi"

    consent = ConsentRecord()

    # ── STEP 1 — Recipient ────────────────────────────────────────────────────
    step1_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_1"].format(
        lawyer_name=lawyer_name,
        recipient_channel=lawyer_contact,
    )
    for _attempt in range(2):
        ans1: str = interrupt(value={"spoken_response": step1_prompt, "consent_step": "recipient"})
        verdict = _parse_consent(ans1)
        if verdict == "yes":
            consent.recipient_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        # ambiguous — re-ask once
        step1_prompt = f"Kripya spasht karein — kya {lawyer_name} ko brief bhejna hai? Sirf 'haan' ya 'nahin' boliye."
    else:
        # Still ambiguous after 2 attempts — route to human
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 2 — Contents ─────────────────────────────────────────────────────
    step2_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_2"].format(
        facts_summary=facts_summary,
        timeline_summary=timeline_summary,
        fuzziness_flag_count=len(open_flags),
    )
    for _attempt in range(2):
        ans2: str = interrupt(value={"spoken_response": step2_prompt, "consent_step": "contents"})
        verdict = _parse_consent(ans2)
        if verdict == "yes":
            consent.contents_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        step2_prompt = "Kya brief ke contents theek hain? Sirf 'haan' ya 'nahin' boliye."
    else:
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 3 — Attachments ─────────────────────────────────────────────────
    step3_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_3"].format(
        n=len(documents),
        document_list=doc_list,
    )
    for _attempt in range(2):
        ans3: str = interrupt(value={"spoken_response": step3_prompt, "consent_step": "attachments"})
        verdict = _parse_consent(ans3)
        if verdict == "yes":
            consent.attachments_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        step3_prompt = f"Kya ye {len(documents)} documents attach karne hain? Sirf 'haan' ya 'nahin' boliye."
    else:
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 4 — Final permission ─────────────────────────────────────────────
    for _attempt in range(2):
        ans4: str = interrupt(value={"spoken_response": CONFIRMATION_FLOW_PROMPTS["STEP_4"], "consent_step": "permission"})
        verdict = _parse_consent(ans4)
        if verdict == "yes":
            consent.permission_confirmed = True
            consent.timestamp = datetime.now(timezone.utc).isoformat()
            consent.consent_transcript_ref = f"turn_{uuid.uuid4().hex[:8]}"
            return {
                "handoff_status": "confirmed",
                "consent": consent,
                "intake_phase": "complete",
            }
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        # ambiguous
    return {"handoff_status": "pending", "consent": consent}
