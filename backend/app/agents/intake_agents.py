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
from pydantic import BaseModel as _PydanticBase

from app.config import GOOGLE_API_KEY, MODEL_FLASH
from app.legal_data.Motor_accident_schema import (
    get_missing_fields_by_phase,
    get_next_priority_field,
)
from app.legal_data.section_mapping import get_applicable_law
from app.prompts.analysis_prompts import CONFIRMATION_FLOW_PROMPTS
from app.prompts.loader import render_prompt
from app.schemas.llm_schemas import (
    CaseTypeOutput,
    CrossQuestionOutput,
    EntityTrackerOutput,
    FuzzinessOutput,
    DocumentRequestOutput,
    ConsentIntentOutput,
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
# Constants
# ---------------------------------------------------------------------------
TEMPERATURE         = 0.1
MAX_RETRIES         = 2
TRANSCRIPT_WINDOW   = 20
CONVERSATION_WINDOW = 10
CONSENT_MAX_RETRIES = 2
DEFAULT_LAWYER_NAME = "Vakeel Sahab"

_ELECTRONIC_EVIDENCE_TYPES: frozenset[str] = frozenset({
    "cctv_footage", "dashcam_recording", "mobile_video", "audio_recording",
    "whatsapp_message_screenshot", "call_recording", "social_media_post",
    "email", "sms_screenshot", "traffic_camera_footage",
})


# ---------------------------------------------------------------------------
# Shared LLM factory
# ---------------------------------------------------------------------------

def _flash_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_FLASH,
        google_api_key=GOOGLE_API_KEY,
        temperature=TEMPERATURE,
        max_retries=MAX_RETRIES,
    )


def _facts_to_json(facts: list[Fact]) -> str:
    return json.dumps([f.model_dump() for f in facts], ensure_ascii=False, indent=2)


def _flags_to_json(flags: list[FuzzinessFlag]) -> str:
    return json.dumps([f.model_dump() for f in flags], ensure_ascii=False, indent=2)


def _retry_prompt(reason: str, lawyer_name: str) -> str:
    return (
        f"Mujhe thoda confusion hua — {reason} Kripya spasht batayein: "
        f"kya {lawyer_name} ko brief bhejna hai? Sirf 'haan' ya 'nahin' boliye."
    )


# ---------------------------------------------------------------------------
# BSA §63 classification — structured LLM call, NOT substring matching
# ---------------------------------------------------------------------------

async def _classify_doc_needs_bsa63(llm: ChatGoogleGenerativeAI, doc_type: str) -> bool:
    """
    Classifies whether a document requires a BSA §63 electronic-evidence
    certificate. Uses a structured LLM call against a closed taxonomy.
    Fails SAFE: errors default to True (over-request rather than miss cert).
    """
    class _DocClass(_PydanticBase):
        canonical_type: str
        needs_bsa63_certificate: bool
        reason: str

    try:
        prompt = (
            f"You are a legal evidence classifier under the Bharatiya Sakshya Adhiniyam 2023.\n"
            f"Classify this document type: '{doc_type}'\n"
            f"Types requiring BSA §63 certificate: {sorted(_ELECTRONIC_EVIDENCE_TYPES)}\n"
            f"Return: canonical_type (closest match or 'physical_document'), "
            f"needs_bsa63_certificate (true if electronic), reason (one sentence)."
        )
        result = await llm.with_structured_output(_DocClass).ainvoke([("system", prompt)])
        return result.needs_bsa63_certificate
    except Exception as exc:
        logger.warning("BSA §63 classification failed for '%s', defaulting True: %s", doc_type, exc)
        return True


# ---------------------------------------------------------------------------
# Node 1 — Case-Type Router
# ---------------------------------------------------------------------------

async def case_type_router_node(state: CaseState) -> dict:
    """
    Determines case type from the client's opening narrative and, for motor
    accident cases, resolves the accident sub-type so downstream nodes know
    which statutory provisions to pull.
    """
    try:
        messages = state.get("messages", [])
        language = state.get("language", "hi")

        llm = _flash_llm()
        system_prompt = render_prompt("case_type_router.yaml", {"language": language})

        conversation = [("system", system_prompt)]
        for msg in messages[-6:]:
            if isinstance(msg, HumanMessage):
                conversation.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                conversation.append(("ai", msg.content))

        conversation.append(("human", "Classify the case type and accident subtype."))

        try:
            response = await llm.with_structured_output(CaseTypeOutput).ainvoke(conversation)
            case_type = response.case_type
            subtype = response.accident_subtype
        except Exception as exc:
            logger.error("case_type_router structured output failed: %s", exc)
            case_type = "unknown"
            subtype = "not_applicable"

        if case_type == "unknown":
            return {
                "case_type": "unknown",
                "accident_subtype": "not_applicable",
                "law_version_context": "unknown",
                "intake_phase": "human_handoff",
            }

        return {
            "case_type": case_type,
            "accident_subtype": subtype,
            "law_version_context": "unknown",
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
# Node 2 — Cross-Questioning Agent (PEACE Model)
# ---------------------------------------------------------------------------

_STAGE_ORDER = [
    "engage", "narrative", "timeline_liability",
    "regulatory", "quantum_profiling", "defense_audit", "closure",
]


async def cross_question_node(state: CaseState) -> dict:
    """
    Conducts the PEACE-model phased interview for motor accident cases.
    Stages: engage → narrative → timeline_liability → regulatory →
            quantum_profiling → defense_audit → closure
    """
    try:
        llm = _flash_llm()
        language = state.get("language", "hi")
        facts = state.get("facts", [])
        fuzziness_flags = state.get("fuzziness_flags", [])
        subtype = state.get("accident_subtype", "not_applicable")
        current_stage = state.get("interview_stage") or "engage"
        client_profile = state.get("client_profile") or {}

        missing_by_phase = get_missing_fields_by_phase(facts)
        unresolved_flags = [f for f in fuzziness_flags if not f.resolved]

        system_prompt = render_prompt("cross_question.yaml", {
            "language": language,
            "interview_stage": current_stage,
            "facts_json": _facts_to_json(facts),
            "accident_subtype": subtype,
            "missing_fields": json.dumps(missing_by_phase),
            "fuzziness_flags": _flags_to_json(unresolved_flags),
            "client_profile_json": json.dumps(client_profile, ensure_ascii=False, indent=2),
        })

        messages = state.get("messages", [])
        conversation = [("system", system_prompt)]
        for msg in messages[-CONVERSATION_WINDOW:]:
            if isinstance(msg, HumanMessage):
                conversation.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                conversation.append(("ai", msg.content))

        if len(conversation) == 1:
            conversation.append(("human", "Namaskar, mujhe apni baat batani hai."))

        try:
            response = await llm.with_structured_output(CrossQuestionOutput).ainvoke(conversation)
            parsed = response.model_dump()
        except Exception as exc:
            logger.error("cross_question_node LLM failure: %s", exc)
            fallback_msg = "Kripya dobara bolein." if language == "hi" else "Please repeat that."
            parsed = {
                "spoken_response": fallback_msg,
                "next_question": fallback_msg,
                "reason": "llm_failure_fallback",
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

        updated_profile = {**client_profile}
        for k, v in profile_update.items():
            if v is not None and v != "" and v != [] and v != {}:
                updated_profile[k] = v

        client_answer: str = interrupt(value={
            "spoken_response": spoken_response,
            "next_question": next_question,
            "interview_stage": current_stage,
        })

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

        law_ctx_update = {}
        accident_date_fact = next(
            (f for f in new_facts if f.field == "accident_datetime"), None
        )
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


# ---------------------------------------------------------------------------
# Node 3 — Fuzziness Detector
# ---------------------------------------------------------------------------

async def fuzziness_detector_node(state: CaseState) -> dict:
    """
    Runs after every new fact is added. Detects contradictions, timeline
    conflicts, vague accounts, missing documents, liability ambiguity, and
    jurisdiction ambiguity. Deduplicates on (flag_type, fact_refs), not
    on LLM-generated flag_ids which are effectively random.
    """
    try:
        llm = _flash_llm()
        facts = state.get("facts", [])
        timeline = state.get("timeline", [])

        if not facts:
            return {"fuzziness_flags": []}

        system_prompt = render_prompt("fuzziness_detector.yaml", {
            "facts_json": _facts_to_json(facts),
            "timeline_json": json.dumps(timeline, ensure_ascii=False),
        })

        try:
            response = await llm.with_structured_output(FuzzinessOutput).ainvoke(
                [("system", system_prompt)]
            )
            raw_flags = response.model_dump().get("flags", [])
        except Exception as exc:
            logger.error("fuzziness_detector_node LLM failure (NOT zero flags): %s", exc)
            return {"fuzziness_flags": [], "_fuzziness_node_error": True}

        existing_sigs = {
            (f.flag_type, frozenset(f.fact_refs))
            for f in state.get("fuzziness_flags", [])
        }
        new_flags: list[FuzzinessFlag] = []

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
                sig = (flag.flag_type, frozenset(flag.fact_refs))
                if sig not in existing_sigs:
                    new_flags.append(flag)
                    existing_sigs.add(sig)
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
    victim profile data from the conversation. Updates entity graph,
    timeline, and client_profile (for MACT quantum calculation).
    """
    try:
        llm = _flash_llm()
        messages = state.get("messages", [])
        facts = state.get("facts", [])
        client_profile = state.get("client_profile") or {}

        transcript_lines = []
        for msg in messages[-TRANSCRIPT_WINDOW:]:
            if isinstance(msg, HumanMessage):
                transcript_lines.append(f"CLIENT: {msg.content}")
            elif isinstance(msg, AIMessage):
                transcript_lines.append(f"NYAYA: {msg.content}")
        transcript = "\n".join(transcript_lines)

        system_prompt = render_prompt("fact_extraction.yaml", {
            "transcript": transcript,
            "existing_facts": _facts_to_json(facts),
            "existing_client_profile": json.dumps(client_profile, ensure_ascii=False),
        })

        try:
            response = await llm.with_structured_output(EntityTrackerOutput).ainvoke([
                ("system", system_prompt),
                ("human", "Extract entities, timeline, new_facts, and client_profile_update."),
            ])
            parsed = response.model_dump()
        except Exception as exc:
            logger.error("entity_tracker_node LLM failure: %s", exc)
            return {"_entity_tracker_error": True}

        entity_graph = parsed.get(
            "entity_graph", state.get("entity_graph", {"nodes": [], "edges": []})
        )
        timeline = parsed.get("timeline", state.get("timeline", []))

        raw_facts = parsed.get("new_facts", [])
        new_facts: list[Fact] = []
        for rf in raw_facts:
            try:
                evidence_type = rf.get("evidence_type", "UNKNOWN")
                if evidence_type not in (
                    "CLIENT_STATED", "DOCUMENT_EXTRACTED",
                    "LEGAL_SOURCE", "INFERENCE", "UNKNOWN"
                ):
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
                    epistemic_status=rf.get("epistemic_status"),
                ))
            except Exception:
                pass

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
    Identifies which documents are needed, issues structured requests, and
    classifies BSA §63 certificate requirement via a structured LLM call
    against a closed taxonomy (not substring matching on LLM-written labels).
    """
    try:
        llm = _flash_llm()
        language = state.get("language", "hi")
        facts = state.get("facts", [])
        fuzziness_flags = state.get("fuzziness_flags", [])
        lawyer_name = state.get("lawyer_name") or DEFAULT_LAWYER_NAME

        system_prompt = render_prompt("document_request.yaml", {
            "language": language,
            "facts_json": _facts_to_json(facts),
            "fuzziness_flags": _flags_to_json(fuzziness_flags),
            "lawyer_name": lawyer_name,
        })

        try:
            response = await llm.with_structured_output(DocumentRequestOutput).ainvoke(
                [("system", system_prompt)]
            )
            doc_requests = response.model_dump().get("documents", [])
        except Exception as exc:
            logger.error("document_request_node LLM failure: %s", exc)
            doc_requests = []

        new_docs: list[DocumentRecord] = []
        request_message_parts: list[str] = []

        for req in doc_requests:
            doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
            is_recording = await _classify_doc_needs_bsa63(llm, req.get("document_type", ""))
            doc = DocumentRecord(
                doc_id=doc_id,
                doc_type=req.get("document_type", "unknown"),
                bsa63_certificate_needed=is_recording,
                upload_status="requested",
                limitations_flag=None,
            )
            new_docs.append(doc)
            fallback_instr = (
                f"Kripya {doc.doc_type} upload karein."
                if language == "hi"
                else f"Please upload {doc.doc_type}."
            )
            request_message_parts.append(req.get("upload_instruction", fallback_instr))

        request_message = " ".join(request_message_parts) or (
            "Kripya zaruri documents upload karein."
            if language == "hi"
            else "Please upload the required documents."
        )

        upload_confirmation: str = interrupt(value={
            "spoken_response": request_message,
            "pending_documents": [d.doc_id for d in new_docs],
        })

        # Mark docs uploaded — prevents should_continue_intake infinite loop
        for doc in new_docs:
            doc.upload_status = "uploaded"

        return {
            "documents": new_docs,
            # request_message already delivered via interrupt payload — don't double-write
            "messages": [
                HumanMessage(content=upload_confirmation or "Document upload kiya."),
            ],
        }

    except Exception as exc:
        logger.error("document_request_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Consent helpers
# ---------------------------------------------------------------------------

async def _judge_consent(
    llm: ChatGoogleGenerativeAI, question_asked: str, answer: str
) -> tuple[str, str]:
    """
    LLM-judges client intent (yes/no/ambiguous). Defaults to 'ambiguous'
    on failure — consent must never be silently assumed.
    """
    try:
        prompt = render_prompt("consent_intent.yaml", {
            "question_asked": question_asked,
            "client_reply": answer,
        })
        response = await llm.with_structured_output(ConsentIntentOutput).ainvoke(
            [("system", prompt)]
        )
        verdict = (
            response.verdict
            if response.verdict in ("yes", "no", "ambiguous")
            else "ambiguous"
        )
        return verdict, response.reason
    except Exception as exc:
        logger.warning("Consent LLM classification failed, treating as ambiguous: %s", exc)
        return "ambiguous", "classification_error_treated_as_ambiguous"


async def _ask_consent_step(
    llm: ChatGoogleGenerativeAI, step_key: str, prompt_text: str, state: CaseState
) -> tuple[str, str, str]:
    answer: str = interrupt(value={"spoken_response": prompt_text, "consent_step": step_key})
    verdict, reason = await _judge_consent(llm, prompt_text, answer)
    return answer, verdict, reason


# ---------------------------------------------------------------------------
# Nodes 6a–6d — Confirmation Flow (4 separate nodes, 1 interrupt each)
#
# WHY 4 NODES: LangGraph replays the entire node body on every resume.
# Multiple interrupt()s in one node means every LLM call between them
# re-executes on replay. By step 4 you'd have silently re-invoked
# _judge_consent ~7 times instead of 4, and non-zero temperature can
# flip an already-confirmed "yes" to "ambiguous".
# One interrupt per node eliminates this entirely.
# ---------------------------------------------------------------------------

async def confirmation_step1_node(state: CaseState) -> dict:
    """Consent step 1 — confirm recipient. One interrupt, no replay risk."""
    llm = _flash_llm()
    lawyer_name = state.get("lawyer_name") or DEFAULT_LAWYER_NAME
    lawyer_contact = state.get("lawyer_contact") or "WhatsApp"
    consent = state.get("consent") or ConsentRecord()

    if consent.recipient_confirmed:
        return {}

    prompt = CONFIRMATION_FLOW_PROMPTS["STEP_1"].format(
        lawyer_name=lawyer_name, recipient_channel=lawyer_contact,
    )
    for _attempt in range(CONSENT_MAX_RETRIES):
        _, verdict, reason = await _ask_consent_step(llm, "recipient", prompt, state)
        if verdict == "yes":
            consent.recipient_confirmed = True
            return {"consent": consent}
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        prompt = _retry_prompt(reason, lawyer_name)
    return {"handoff_status": "pending", "consent": consent}


async def confirmation_step2_node(state: CaseState) -> dict:
    """Consent step 2 — confirm contents. Shows actual field names (informed consent)."""
    llm = _flash_llm()
    consent = state.get("consent") or ConsentRecord()
    if consent.contents_confirmed:
        return {}

    facts = state.get("facts", [])
    timeline_events = state.get("timeline", [])
    open_flags = [f for f in state.get("fuzziness_flags", []) if not f.resolved]

    unique_fields = list({f.field for f in facts})[:10]
    fact_fields_str = ", ".join(unique_fields) or "koi baatein nahi"
    facts_summary = f"{len(facts)} baatein ({fact_fields_str})"
    timeline_summary = f"{len(timeline_events)} ghatnaayein"

    prompt = CONFIRMATION_FLOW_PROMPTS["STEP_2"].format(
        facts_summary=facts_summary,
        timeline_summary=timeline_summary,
        fuzziness_flag_count=len(open_flags),
    )
    for _attempt in range(CONSENT_MAX_RETRIES):
        _, verdict, reason = await _ask_consent_step(llm, "contents", prompt, state)
        if verdict == "yes":
            consent.contents_confirmed = True
            return {"consent": consent}
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        prompt = f"{reason} Kya brief ke contents theek hain? Sirf 'haan' ya 'nahin' boliye."
    return {"handoff_status": "pending", "consent": consent}


async def confirmation_step3_node(state: CaseState) -> dict:
    """Consent step 3 — confirm attachments."""
    llm = _flash_llm()
    consent = state.get("consent") or ConsentRecord()
    if consent.attachments_confirmed:
        return {}

    documents = state.get("documents", [])
    doc_list = ", ".join(d.doc_type for d in documents) if documents else "koi document nahi"

    prompt = CONFIRMATION_FLOW_PROMPTS["STEP_3"].format(
        n=len(documents), document_list=doc_list,
    )
    for _attempt in range(CONSENT_MAX_RETRIES):
        _, verdict, reason = await _ask_consent_step(llm, "attachments", prompt, state)
        if verdict == "yes":
            consent.attachments_confirmed = True
            return {"consent": consent}
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        prompt = (
            f"{reason} Kya ye {len(documents)} documents attach karne hain? "
            f"Sirf 'haan' ya 'nahin' boliye."
        )
    return {"handoff_status": "pending", "consent": consent}


async def confirmation_step4_node(state: CaseState) -> dict:
    """Consent step 4 — final permission with real audit trail."""
    llm = _flash_llm()
    consent = state.get("consent") or ConsentRecord()
    if consent.permission_confirmed:
        return {}

    prompt = CONFIRMATION_FLOW_PROMPTS["STEP_4"]
    for _attempt in range(CONSENT_MAX_RETRIES):
        _, verdict, reason = await _ask_consent_step(llm, "permission", prompt, state)
        if verdict == "yes":
            consent.permission_confirmed = True
            now_iso = datetime.now(timezone.utc).isoformat()
            consent.timestamp = now_iso
            messages = state.get("messages", [])
            # Real audit trail: message index + UTC timestamp (not a random UUID)
            consent.consent_transcript_ref = f"msg_idx={len(messages)};ts={now_iso}"
            return {
                "handoff_status": "confirmed",
                "consent": consent,
                "intake_phase": "complete",
            }
        if verdict == "no":
            return {"handoff_status": "declined", "consent": consent}
        prompt = f"{reason} Kripya final permission dein — sirf 'haan' ya 'nahin' boliye."
    return {"handoff_status": "pending", "consent": consent}
