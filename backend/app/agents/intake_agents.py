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
from app.legal_data.Motor_accident_schema import get_missing_fields, get_missing_fields_by_phase, get_next_priority_field
from app.legal_data.section_mapping import get_applicable_law
from app.prompts.global_policy import inject_policy
from app.prompts.analysis_prompts import CONFIRMATION_FLOW_PROMPTS
from app.prompts.intake_prompts import (
    CASE_TYPE_ROUTER_PROMPT,
    CROSS_QUESTION_PROMPT,
    DOCUMENT_REQUEST_PROMPT,
    FACT_EXTRACTION_PROMPT,
    FUZZINESS_DETECTOR_PROMPT,
    CONSENT_INTENT_PROMPT,
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
    Determines case type from the client's opening narrative and, for motor
    accident cases, resolves the accident sub-type so downstream nodes know
    which statutory provisions / embeddings to pull (MV Act sections, IPC/BNS
    provisions, etc.).
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
            "case_type (motor_accident|criminal_fir|unknown), "
            "accident_subtype (vehicle_vs_pedestrian|vehicle_vs_cyclist|"
            "vehicle_vs_motorcyclist|vehicle_vs_vehicle|vehicle_vs_animal|"
            "vehicle_vs_property|single_vehicle|vehicle_vs_fixed_object|"
            "not_applicable), "
            "reason (one sentence). Only JSON, no markdown."
        ))

        response = await llm.ainvoke(conversation)
        result = _parse_json_block(response.content)

        case_type = result.get("case_type", "motor_accident")
        subtype = result.get("accident_subtype", "not_applicable")

        if case_type == "unknown":
            return {
                "case_type": "unknown",
                "accident_subtype": "not_applicable",
                "law_version_context": "unknown",
                "intake_phase": "human_handoff",
            }
        # Determine applicable law/article context from the accident sub-type
        return {
            "case_type": case_type,
            "accident_subtype": subtype,
            "law_version_context": "unknown",   # resolved later
            "intake_phase": "cross_question",
        }

    except Exception as exc:
        logger.error("case_type_router_node error: %s", exc, exc_info=True)
        return {
            "case_type": "motor_accident",
            "accident_subtype": "not_applicable",
            "law_version_context": "unknown",
            "intake_phase": "cross_question",
        }

# ---------------------------------------------------------------------------
# Node 2 — Cross-Questioning Agent (PEACE Model + Cognitive Interview)
# ---------------------------------------------------------------------------

# PEACE stage progression — each stage advances to the next once its goals are met.
# The LLM decides when to advance by returning interview_stage_after in its JSON output.
_STAGE_ORDER = [
    "engage",
    "narrative",
    "timeline_liability",
    "regulatory",
    "quantum_profiling",
    "defense_audit",
    "closure",
]

async def cross_question_node(state: CaseState) -> dict:
    """
    Conducts the PEACE-model phased interview for motor accident cases.
    Stages:
      engage → narrative → timeline_liability → regulatory →
      quantum_profiling → defense_audit → closure

    Each stage has specific rules:
    - engage: trauma-informed ground rules only, NO case questions
    - narrative: ONE open TED prompt, NO interruptions
    - timeline_liability: funnel (open → specific → closed → confirm)
    - regulatory: FIR/MLC/FAR/DAR/limitation check
    - quantum_profiling: victim age, occupation, income, dependents (Sarla Verma inputs)
    - defense_audit: DL validity, helmet, intoxication, overloading
    - closure: reflect and confirm

    Facts from prior turns are passed via facts_json so the LLM never re-asks.
    Client profile is accumulated across stages.
    """
    try:
        llm = _flash_llm()
        language = state.get("language", "hi")
        facts = state.get("facts", [])
        fuzziness_flags = state.get("fuzziness_flags", [])
        subtype = state.get("accident_subtype", "not_applicable")
        current_stage = state.get("interview_stage") or "engage"
        client_profile = state.get("client_profile") or {}

        missing_fields = get_missing_fields(facts)
        missing_by_phase = get_missing_fields_by_phase(facts)
        unresolved_flags = [f for f in fuzziness_flags if not f.resolved]

        system_prompt = inject_policy(CROSS_QUESTION_PROMPT.format(
            language=language,
            interview_stage=current_stage,
            facts_json=_facts_to_json(facts),
            accident_subtype=subtype,
            missing_fields=json.dumps(missing_by_phase),
            fuzziness_flags=_flags_to_json(unresolved_flags),
            client_profile_json=json.dumps(client_profile, ensure_ascii=False, indent=2),
        ))

        # Build the conversation with full context (last 10 turns)
        messages = state.get("messages", [])
        conversation = [("system", system_prompt)]
        for msg in messages[-10:]:
            if isinstance(msg, HumanMessage):
                conversation.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                conversation.append(("ai", msg.content))

        # Fallback seed if conversation is empty
        if len(conversation) == 1:
            conversation.append(("human", "Namaskar, mujhe apni baat batani hai."))

        response = await llm.ainvoke(conversation)

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            parsed = {
                "spoken_response": response.content,
                "next_question": response.content,
                "reason": "llm_free_text",
                "interview_stage_after": current_stage,
                "updated_fact_candidates": [],
                "client_profile_update": {},
                "requires_human_review": False,
            }

        spoken_response = parsed.get("spoken_response", "")
        next_question = parsed.get("next_question", spoken_response)
        candidates = parsed.get("updated_fact_candidates", [])
        new_stage = parsed.get("interview_stage_after", current_stage)
        profile_update = parsed.get("client_profile_update") or {}

        # Merge profile update into existing profile (shallow merge, never overwrite with blank)
        updated_profile = {**client_profile}
        for k, v in profile_update.items():
            if v is not None and v != "" and v != [] and v != {}:
                updated_profile[k] = v

        # ── Pause graph — wait for client's spoken answer ────────────────────
        client_answer: str = interrupt(value={
            "spoken_response": spoken_response,
            "next_question": next_question,
            "interview_stage": current_stage,
        })

        # ── Write new facts from LLM candidates ─────────────────────────────
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        new_facts: list[Fact] = []

        for candidate in candidates:
            if not candidate.get("field") or not candidate.get("value"):
                continue
            new_facts.append(Fact(
                fact_id=f"F-{uuid.uuid4().hex[:8]}_cq",
                field=candidate["field"],
                value=candidate["value"],
                evidence_type="CLIENT_STATED",
                source_ref=turn_id,
                confidence=candidate.get("confidence", 0.7),
                status="unconfirmed",
                contradicts=[],
                epistemic_status=candidate.get("epistemic_status", "direct"),
            ))

        # Also write raw client answer as a general fact for the entity_tracker to process
        if client_answer and client_answer.strip():
            next_field = get_next_priority_field(facts + new_facts) or "general_statement"
            new_facts.append(Fact(
                fact_id=f"F-{uuid.uuid4().hex[:8]}_raw",
                field=next_field,
                value=client_answer,
                evidence_type="CLIENT_STATED",
                source_ref=turn_id,
                confidence=0.5,
                status="unconfirmed",
                contradicts=[],
            ))

        # Determine applicable law from accident date if now known
        law_ctx_update = {}
        accident_date_fact = next((f for f in new_facts if f.field == "accident_datetime"), None)
        if accident_date_fact:
            law_ctx_update["law_version_context"] = get_applicable_law(accident_date_fact.value)

        return {
            "facts": new_facts,
            "interview_stage": new_stage,
            "client_profile": updated_profile,
            **law_ctx_update,
            "messages": [
                AIMessage(content=spoken_response),
                HumanMessage(content=client_answer),
            ],
        }

    except Exception as exc:
        logger.error("cross_question_node error: %s", exc, exc_info=True)
        return {}

    except Exception as exc:
        logger.error("cross_question_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 3 — Fuzziness Detector
# ---------------------------------------------------------------------------
async def fuzziness_detector_node(state: CaseState) -> dict:
    """
    Runs after every new fact is added. Detects contradictions, timeline
    conflicts, vague accounts, missing documents, liability ambiguity, and
    jurisdiction ambiguity for motor accident cases. Never concludes anyone
    is lying — only flags specific discrepancies.
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
    Extracts people, vehicles, events, relationships, timeline entries, and
    victim profile data from the conversation. Updates the entity graph,
    timeline, and client_profile (for MACT quantum calculation).
    """
    try:
        llm = _flash_llm()
        messages = state.get("messages", [])
        facts = state.get("facts", [])
        client_profile = state.get("client_profile") or {}

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
            existing_client_profile=json.dumps(client_profile, ensure_ascii=False),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Extract entities, timeline, new_facts, and client_profile_update. Return JSON."),
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
                    fact_id=rf.get("fact_id", f"F-{uuid.uuid4().hex[:8]}_et"),
                    field=rf.get("field", "unknown"),
                    value=rf.get("value", ""),
                    evidence_type=evidence_type,
                    source_ref=rf.get("source_ref", "entity_tracker"),
                    confidence=rf.get("confidence", 0.5),
                    status="unconfirmed",
                    contradicts=rf.get("contradicts", []),
                    epistemic_status=rf.get("epistemic_status")
                ))
            except Exception:
                pass

        # Merge any client profile data extracted from the conversation
        profile_update = parsed.get("client_profile_update") or {}
        updated_profile = {**client_profile}
        for k, v in profile_update.items():
            if v is not None and v != "" and v != [] and v != {}:
                updated_profile[k] = v

        result: dict = {
            "entity_graph": entity_graph,
            "timeline": timeline,
            "facts": new_facts,
        }
        if updated_profile != client_profile:
            result["client_profile"] = updated_profile

        return result

    except Exception as exc:
        logger.error("entity_tracker_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 5 — Document Request Agent
# ---------------------------------------------------------------------------

async def document_request_node(state: CaseState) -> dict:
    """
    Identifies which documents are needed for a motor accident case, issues a
    specific request for each, and handles the special BSA §63 certificate
    question for any recordings/CCTV/dashcam footage. Uses interrupt() to
    wait for the client to upload.
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

        # Keywords that trigger the BSA §63 electronic-evidence certificate
        # requirement — broadened for motor accident cases, where CCTV and
        # dashcam footage are as common as phone recordings.
        RECORDING_KEYWORDS = ("recording", "video", "whatsapp", "cctv", "dashcam", "audio")

        for req in doc_requests:
            doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
            doc_type_lower = req.get("document_type", "").lower()
            is_recording = any(kw in doc_type_lower for kw in RECORDING_KEYWORDS)
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
# ---------------------------------------------------------------------------
# Node 6 — Confirmation Flow (4-step finite-state consent)
# ---------------------------------------------------------------------------



async def _judge_consent(llm, question_asked: str, answer: str) -> tuple[str, str]:
    """
    Uses the LLM to judge client intent (yes/no/ambiguous) for a consent
    question. If the LLM call fails or returns something unparsable, we
    deliberately default to "ambiguous" rather than guessing — consent must
    never be silently assumed. This forces the existing retry/pending path
    to handle it (re-ask, or fall to human review) instead of a keyword
    heuristic making the call.
    Returns (verdict, reason).
    """
    try:
        prompt = CONSENT_INTENT_PROMPT.format(
            question_asked=question_asked,
            client_reply=answer,
        )
        response = await llm.ainvoke([("system", prompt)])
        parsed = _parse_json_block(response.content)
        verdict = parsed.get("verdict", "ambiguous")
        reason = parsed.get("reason", "")
        if verdict not in ("yes", "no", "ambiguous"):
            verdict = "ambiguous"
        return verdict, reason
    except Exception as exc:
        logger.warning("Consent LLM classification failed, treating as ambiguous: %s", exc)
        return "ambiguous", "classification_error_treated_as_ambiguous"


async def confirmation_flow_node(state: CaseState) -> dict:
    """
    4-step finite-state consent flow for a motor accident case brief. Each
    step is a separate interrupt() call. Consent intent at each step is
    judged entirely by the LLM (no keyword matching) so partial, hedged, or
    non-literal replies are handled correctly. Any classification failure is
    treated as ambiguous, never as an assumed yes/no. Only advances on
    unambiguous confirmation. On any 'no', aborts and returns to intake.

    Writes a ConsentRecord with per-step booleans and a UTC timestamp.
    """
    llm = _flash_llm()
    facts = state.get("facts", [])
    documents = state.get("documents", [])
    fuzziness_flags = state.get("fuzziness_flags", [])
    lawyer_name = state.get("lawyer_name") or "Vakeel Sahab"
    lawyer_contact = state.get("lawyer_contact") or "WhatsApp"

    # Summary strings for the confirmation messages
    facts_summary = f"{len(facts)} baatein"
    timeline_events = state.get("timeline", [])
    timeline_summary = f"{len(timeline_events)} ghatnaayein"
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
        verdict, reason = await _judge_consent(llm, step1_prompt, ans1)
        if verdict == "yes":
            consent.recipient_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        step1_prompt = (
            f"Mujhe thoda confusion hua — {reason} Kripya spasht batayein: "
            f"kya {lawyer_name} ko brief bhejna hai? Sirf 'haan' ya 'nahin' boliye."
        )
    else:
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 2 — Contents ─────────────────────────────────────────────────────
    step2_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_2"].format(
        facts_summary=facts_summary,
        timeline_summary=timeline_summary,
        fuzziness_flag_count=len(open_flags),
    )
    for _attempt in range(2):
        ans2: str = interrupt(value={"spoken_response": step2_prompt, "consent_step": "contents"})
        verdict, reason = await _judge_consent(llm, step2_prompt, ans2)
        if verdict == "yes":
            consent.contents_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        step2_prompt = f"{reason} Kya brief ke contents theek hain? Sirf 'haan' ya 'nahin' boliye."
    else:
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 3 — Attachments ─────────────────────────────────────────────────
    step3_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_3"].format(
        n=len(documents),
        document_list=doc_list,
    )
    for _attempt in range(2):
        ans3: str = interrupt(value={"spoken_response": step3_prompt, "consent_step": "attachments"})
        verdict, reason = await _judge_consent(llm, step3_prompt, ans3)
        if verdict == "yes":
            consent.attachments_confirmed = True
            break
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        step3_prompt = (
            f"{reason} Kya ye {len(documents)} documents attach karne hain? "
            f"Sirf 'haan' ya 'nahin' boliye."
        )
    else:
        return {"handoff_status": "pending", "consent": consent}

    # ── STEP 4 — Final permission ─────────────────────────────────────────────
    step4_prompt = CONFIRMATION_FLOW_PROMPTS["STEP_4"]
    for _attempt in range(2):
        ans4: str = interrupt(value={"spoken_response": step4_prompt, "consent_step": "permission"})
        verdict, reason = await _judge_consent(llm, step4_prompt, ans4)
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
        step4_prompt = f"{reason} Kripya final permission dein — sirf 'haan' ya 'nahin' boliye."
    return {"handoff_status": "pending", "consent": consent}