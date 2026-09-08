"""
NyayaLens — Analysis Agents
Async node functions for the parallel analysis graph.
Each uses real LLM calls (pro tier for complex reasoning, flash for lighter tasks).
Citation discipline enforced: every CitationRecord must have source_id + exact_citation.
"""
from __future__ import annotations

import json
import logging
import uuid
import asyncio
from typing import Any

_sse_queue: asyncio.Queue | None = None

def set_sse_broadcast(q: asyncio.Queue) -> None:
    global _sse_queue
    _sse_queue = q

async def _broadcast(stage: str, status: str, message: str, summary: str = "") -> None:
    if _sse_queue is not None:
        event = {
            "kind": "stage" if status == "start" else "agent_complete",
            "status": status,
            "content": {"stage": stage, "message": message} if status == "start" else {"agent": stage, "summary": summary},
            "id": str(uuid.uuid4())
        }
        await _sse_queue.put(event)

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import GOOGLE_API_KEY, MODEL_FLASH, MODEL_PRO, MODEL_SEARCH
from app.tools.indian_kanoon import research_query
from app.prompts.analysis_prompts import (
    ARGUMENT_HYPOTHESIS_PROMPT,
    LAWYER_CHAT_PROMPT,
    OPPOSITION_PROMPT,
    PACKET_COMPILER_PROMPT,
    READINESS_ANALYSIS_PROMPT,
    WITNESS_CANDIDATE_PROMPT,
)
from app.prompts.global_policy import inject_policy
from app.state import (
    ArgumentHypothesis,
    CaseState,
    CitationRecord,
    ReadinessSignals,
    WitnessCandidate,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _pro_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_PRO,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
        max_retries=2,
    )


def _flash_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_FLASH,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
        max_retries=2,
    )


def _search_llm() -> ChatGoogleGenerativeAI:
    """gemini-2.5-flash — used exclusively for search query generation and keyword extraction."""
    return ChatGoogleGenerativeAI(
        model=MODEL_SEARCH,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.2,
        max_retries=2,
    )


def _to_json(obj: Any) -> str:
    if isinstance(obj, list):
        items = []
        for item in obj:
            if hasattr(item, "model_dump"):
                items.append(item.model_dump())
            else:
                items.append(item)
        return json.dumps(items, ensure_ascii=False, indent=2)
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(), ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _parse_json_block(text: Any) -> Any:
    if isinstance(text, list):
        parts = []
        for part in text:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif hasattr(part, "text"):
                parts.append(getattr(part, "text", ""))
            else:
                parts.append(str(part))
        text = "".join(parts)
    elif not isinstance(text, str):
        text = str(text)

    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text.strip())


def _validate_citation(raw: dict) -> CitationRecord | None:
    """
    Build a CitationRecord only if mandatory fields are present.
    Missing fields are marked 'unclear' rather than invented.
    """
    source_id = raw.get("source_id", "").strip()
    exact_citation = raw.get("exact_citation", "").strip()
    if not source_id or not exact_citation:
        return None   # unusable — drop it

    return CitationRecord(
        source_id=source_id,
        source_url=raw.get("source_url"),
        exact_citation=exact_citation,
        supporting_passage=raw.get("supporting_passage", "unclear"),
        jurisdiction=raw.get("jurisdiction", "India"),
        date=raw.get("date", "unclear"),
        applicability_status=raw.get("applicability_status", "unclear"),
        contradiction_or_limit=raw.get("contradiction_or_limit"),
    )

# ---------------------------------------------------------------------------
# Node 1 — Precedent Research Agent  [Pro]
# ---------------------------------------------------------------------------

async def precedent_research_node(state: CaseState) -> dict:
    """
    Live case law research via Indian Kanoon API.
    ONLY fetches judgments (Supreme Court / High Court).

    Statute lookup is fully handled by statute_analysis_node (parallel node).
    This node does NOT touch statutes at all.

    Flow:
      1. LLM (gemini-2.5-flash) reads case facts → generates 3-4 targeted
         judgment search queries.
      2. Each query hits Indian Kanoon (doctypes:judgments).
      3. Full text fetched for top 2 results per query.
      4. Deduplication prevents the same judgment appearing twice.
    """
    await _broadcast("precedent_research", "start", "Precedent Agent: Searching Indian Kanoon for similar MACT cases...")
    try:
        llm     = _search_llm()
        facts   = state.get("facts", [])
        flags   = state.get("fuzziness_flags", [])
        track   = state.get("accident_subtype", "not_applicable")
        law_ctx = state.get("law_version_context", "unknown")

        citations: list[CitationRecord] = []
        seen_ids: set[str] = set()

        # ── Step 1: LLM generates targeted case law search queries ──
        query_prompt = (
            "You are an expert Indian Legal Research Analyst.\n"
            "Analyze the case facts below and generate 3-4 targeted search queries "
            "to find RELEVANT Supreme Court and High Court JUDGMENTS on Indian Kanoon.\n"
            "Focus on: motor accident compensation, negligence, rash/negligent driving, "
            "MACT tribunal jurisdiction, MV Act compensation quantum, insurance liability — "
            "whatever the specific facts and accident sub-type point to.\n\n"
            f"Case Facts:\n{_to_json(facts)}\n\n"
            f"Accident Sub-type: {track}\n"
            f"Law Version Context: {law_ctx}\n"
            f"Fuzziness Flags:\n{_to_json(flags)}\n\n"
            "Return ONLY a valid JSON array of query strings. Examples:\n"
            '["motor accident compensation negligence Supreme Court India",\n'
            ' "MACT tribunal jurisdiction MV Act 166 High Court",\n'
            ' "rash negligent driving BNS section compensation"]\n'
            "Return ONLY the JSON array, no explanation."
        )

        response = await llm.ainvoke([
            ("system", inject_policy(query_prompt)),
            ("human", "Generate the case law search queries as a JSON array."),
        ])

        try:
            case_law_queries = _parse_json_block(response.content)
            if not isinstance(case_law_queries, list):
                case_law_queries = []
        except Exception:
            case_law_queries = []

        # Fallback if LLM fails
        if not case_law_queries:
            case_law_queries = [f"settled possession dispossession {track} Supreme Court India"]

        case_law_queries = [str(q) for q in case_law_queries if q][:4]

        logger.info("[PrecedentResearch] Generated %d judgment queries", len(case_law_queries))

        # ── Step 2: Fetch live judgments from Indian Kanoon ──
        for cq in case_law_queries:
            try:
                results = await research_query(cq, doctypes="judgments")
                for res in results:
                    sid = res.get("source_id", "")
                    if not sid or sid in seen_ids:
                        continue
                    if not res.get("exact_citation"):
                        continue
                    seen_ids.add(sid)
                    citations.append(CitationRecord(
                        source_id=sid,
                        exact_citation=res["exact_citation"],
                        source_url=res.get("source_url"),
                        supporting_passage=res.get("supporting_passage", "")[:500],
                        jurisdiction=res.get("jurisdiction", "India"),
                        date=res.get("date", ""),
                        applicability_status="case_law",
                        contradiction_or_limit=res.get("contradiction_or_limit"),
                    ))
            except Exception as cq_err:
                logger.warning("[PrecedentResearch] Query '%s' failed: %s", cq, cq_err)

        logger.info("[PrecedentResearch] Retrieved %d unique live judgments", len(citations))
        await _broadcast("precedent_research", "completed", "", f"Retrieved {len(citations)} judgments")
        return {"precedents": citations}

    except Exception as exc:
        logger.error("precedent_research_node error: %s", exc, exc_info=True)
        await _broadcast("precedent_research", "completed", "", "Failed to retrieve judgments")
        return {"precedents": []}





# ---------------------------------------------------------------------------
# Node 1b — Statute Analysis Node  [Search LLM + Local JSON DB + IK for new codes]
# ---------------------------------------------------------------------------

async def statute_analysis_node(state: CaseState) -> dict:
    """
    Identifies ALL applicable statutory provisions from the local law database.

    Flow:
      1. Build a compact "menu" — just section_number + title for each relevant act.
         Old codes (IPC/CrPC/IEA/CPC…) → sourced from local JSON files (civictech_db/).
         New codes (BNS/BNSS/BSA) → section titles listed from known ranges.
      2. LLM (gemini-2.5-flash) reads the menu + case facts → picks only what applies.
      3. For picked old-code sections → fetch full text from local JSON (0ms, no network).
      4. For picked new-code sections → fetch verbatim text from Indian Kanoon API.
      5. Return merged CitationRecords appended to state['precedents'].
    """
    await _broadcast("statute_analysis", "start", "Statute Agent: Mapping applicable MV Act sections...")
    import asyncio as _asyncio
    from app.legal_data.statute_db import (
        ACT_LABELS, LOCAL_ACTS, LIVE_ACTS,
        get_section, get_section_index, get_citation_string,
    )

    try:
        llm     = _search_llm()
        facts   = state.get("facts", [])
        track   = state.get("accident_subtype", "not_applicable")
        law_ctx = state.get("law_version_context", "unknown")
        flags   = state.get("fuzziness_flags", [])

        # ── Step 1: Build compact section menu from actual JSON DB indexes ──────
        if law_ctx == "pre_2024_codes":
            local_acts = ["IPC", "IEA", "CRPC", "CPC", "MVA", "NIA"]
            live_acts  = []
        elif law_ctx == "post_2024_codes":
            local_acts = ["CPC", "MVA", "NIA"]
            live_acts  = ["BNS", "BNSS", "BSA"]
        else:  # mixed / unknown — both
            local_acts = ["IPC", "IEA", "CRPC", "CPC", "MVA", "NIA"]
            live_acts  = ["BNS", "BNSS", "BSA"]

        menu_lines = []

        # Old codes: section number + title directly from the downloaded JSON files
        for act in local_acts:
            idx = get_section_index(act)   # [{section_number, section_title}, ...]
            if not idx:
                continue
            label = ACT_LABELS.get(act, act)
            menu_lines.append(f"\n{act} ({label}) — {len(idx)} sections:")
            for s in idx:
                menu_lines.append(f"  §{s['section_number']} — {s['section_title']}")

        # New codes: no local file exists. Tell LLM which acts to pick from;
        # it picks section numbers from its own knowledge.
        # Indian Kanoon API is the verification — only sections IK confirms survive.
        if live_acts:
            menu_lines.append("\n--- New codes (events on/after 01-Jul-2024) ---")
            menu_lines.append("For the acts below, identify section numbers you know are relevant.")
            menu_lines.append("Each picked section will be verified against Indian Kanoon API.")
            menu_lines.append("If IK cannot confirm it, it will be dropped. Do not guess wildly.")
            for act in live_acts:
                label = ACT_LABELS.get(act, act)
                menu_lines.append(f"  {act} ({label})")

        menu_text = "\n".join(menu_lines)

        # ── Step 2: LLM picks from menu (old codes) + identifies new code sections ──
        pick_prompt = (
            "You are an expert Indian motor accident and criminal law analyst.\n"
            "Based on the case facts, pick EVERY applicable section:\n\n"
            "For OLD codes (IPC/IEA/CRPC/CPC/NIA/MVA): pick ONLY from the numbered menu below.\n"
            "For NEW codes (BNS/BNSS/BSA): identify section numbers you know apply. "
            "Each will be verified against Indian Kanoon — only confirmed sections are used.\n\n"
            f"Case Facts:\n{_to_json(facts)}\n\n"
            f"Accident Sub-type: {track}\n"
            f"Law Version Context: {law_ctx}\n"
            f"Fuzziness Flags: {_to_json(flags)}\n\n"
            f"AVAILABLE SECTIONS:\n{menu_text}\n\n"
            "Return ONLY a valid JSON array. Each element:\n"
            '{"act": "MVA", "section": "166", "reason": "one sentence why it applies"}\n'
            "Return ONLY the JSON array, no markdown, no explanation."
        )

        response = await llm.ainvoke([
            ("system", inject_policy(pick_prompt)),
            ("human", "Pick all applicable sections as a JSON array."),
        ])

        try:
            picked = _parse_json_block(response.content)
            if not isinstance(picked, list):
                picked = []
        except Exception:
            picked = []

        logger.info("[StatuteAnalysis] LLM picked %d sections for track='%s'", len(picked), track)

        # ── Step 3: Fetch full text ───────────────────────────────────────────
        statute_citations: list[CitationRecord] = []
        seen_ids: set[str] = set()

        old_picks  = [p for p in picked if isinstance(p, dict) and str(p.get("act","")).upper() in LOCAL_ACTS]
        new_picks  = [p for p in picked if isinstance(p, dict) and str(p.get("act","")).upper() in LIVE_ACTS]

        # Old codes — local JSON lookup, zero network calls
        for prov in old_picks:
            act     = str(prov.get("act", "")).strip().upper()
            section = str(prov.get("section", "")).strip()
            reason  = str(prov.get("reason", ""))
            if not act or not section:
                continue

            entry = get_section(act, section)
            if not entry:
                logger.debug("[StatuteAnalysis] %s §%s not in local DB", act, section)
                continue

            cid = f"STATUTE_{act}_{section}"
            if cid in seen_ids:
                continue
            seen_ids.add(cid)

            statute_citations.append(CitationRecord(
                source_id=cid,
                exact_citation=get_citation_string(act, section),
                source_url="https://indiacode.gov.in",
                supporting_passage=(
                    f"[{entry.get('section_title', '')}] "
                    f"{entry.get('section_desc', '')[:450]}"
                ),
                jurisdiction=f"India — {ACT_LABELS.get(act, act)}",
                date="Central Act",
                applicability_status="statute",
                contradiction_or_limit=reason,
            ))

        logger.info("[StatuteAnalysis] %d old-code sections from local JSON", len(statute_citations))

        # New codes — fetch verbatim text from Indian Kanoon API
        if new_picks:
            ik_tasks = []
            for prov in new_picks:
                act     = str(prov.get("act", "")).strip().upper()
                section = str(prov.get("section", "")).strip()
                if act and section:
                    query = f"Section {section} {ACT_LABELS.get(act, act)}"
                    ik_tasks.append((prov, query))

            ik_results = await _asyncio.gather(
                *[research_query(q, doctypes="laws") for _, q in ik_tasks],
                return_exceptions=True,
            )

            for (prov, _), result in zip(ik_tasks, ik_results):
                if isinstance(result, Exception) or not result:
                    continue
                act     = str(prov.get("act", "")).strip().upper()
                section = str(prov.get("section", "")).strip()
                reason  = str(prov.get("reason", ""))
                cid     = f"STATUTE_{act}_{section}"
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)

                top = result[0]
                statute_citations.append(CitationRecord(
                    source_id=cid,
                    exact_citation=get_citation_string(act, section),
                    source_url=top.get("source_url", "https://indiankanoon.org"),
                    supporting_passage=top.get("supporting_passage", "")[:450],
                    jurisdiction=f"India — {ACT_LABELS.get(act, act)}",
                    date=top.get("date", "2024"),
                    applicability_status="statute",
                    contradiction_or_limit=reason,
                ))

            logger.info("[StatuteAnalysis] %d new-code sections fetched from Indian Kanoon", len(new_picks))

        # ── Step 4: Return new citations (LangGraph operator.add will append them) ──
        existing     = state.get("precedents", []) or []
        existing_ids = {c.source_id for c in existing if hasattr(c, "source_id")}
        new_only     = [c for c in statute_citations if c.source_id not in existing_ids]

        logger.info("[StatuteAnalysis] Returning %d new statutory citations", len(new_only))
        await _broadcast("statute_analysis", "completed", "", f"Mapped {len(new_only)} sections")
        return {"precedents": new_only}

    except Exception as exc:
        logger.error("statute_analysis_node error: %s", exc, exc_info=True)
        await _broadcast("statute_analysis", "completed", "", "Failed to map sections")
        return {}


# ---------------------------------------------------------------------------
# Node 2 — Opposition Case Formulator  [Pro]
# ---------------------------------------------------------------------------


async def opposition_formulator_node(state: CaseState) -> dict:
    """
    Builds the strongest plausible opposing narrative.
    Always uses 'the opposing side may argue...' framing.
    Never asserts opposition claims as established fact.
    """
    try:
        llm = _pro_llm()
        facts = state.get("facts", [])
        flags = state.get("fuzziness_flags", [])
        precedents = state.get("precedents", [])
        timeline = state.get("timeline", [])

        system_prompt = inject_policy(OPPOSITION_PROMPT.format(
            facts_json=_to_json(facts),
            timeline_json=_to_json(timeline),
            fuzziness_flags=_to_json(flags),
            retrieved_citations_json=_to_json(precedents),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Build the opposition case. Return JSON with keys: hypotheses (list), strongest_attack_vector (str), client_clarifications_needed (list[str])."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            parsed = {
                "hypotheses": [],
                "strongest_attack_vector": "Insufficient documentary evidence",
                "client_clarifications_needed": [],
            }

        # Sanitise: ensure "may argue" framing in hypotheses
        hypotheses = parsed.get("hypotheses", [])
        sanitised = []
        for h in hypotheses:
            text = h if isinstance(h, str) else h.get("opposing_position", str(h))
            if not text.lower().startswith("the opposing side may argue"):
                text = "The opposing side may argue: " + text
            sanitised.append(text)
        parsed["hypotheses"] = sanitised

        return {"opposition_case": parsed}

    except Exception as exc:
        logger.error("opposition_formulator_node error: %s", exc, exc_info=True)
        return {"opposition_case": {"hypotheses": [], "strongest_attack_vector": "unknown", "client_clarifications_needed": []}}


OPPOSITION_ANALYSIS_PROMPT = """You are a senior Indian MACT defense advocate analyzing the OPPOSITION's case.

You have the client's facts, timeline, and the FIR/charges pressed against them.

Your job:
1. Evaluate EACH charge pressed (FIR sections) — is it valid, excessive, or fabricated?
2. Find the opposition's STRONGEST arguments (what the insurance company / other party will argue)
3. Find the opposition's WEAK POINTS (what can be challenged)
4. List every fact where the client hesitated, contradicted themselves, or gave unclear info — these are investigation targets for the lawyer
5. List what critical evidence is MISSING that hurts our case

Return ONLY valid JSON:
{{
  "charges_analysis": [
    {{"section": "279 IPC", "description": "Rash driving", "validity": "valid|excessive|fabricated", "reasoning": "...", "challenge_strategy": "..."}}
  ],
  "opposition_strong_points": ["string list"],
  "opposition_weak_points": ["string list"],  
  "client_hesitation_flags": ["facts where client was unclear or contradicted themselves"],
  "missing_critical_evidence": ["what evidence is absent that opposition will exploit"],
  "investigation_targets": ["specific lawyer investigation tasks"]
}}

Facts: {facts_json}
Timeline: {timeline_json}
FIR/Charges: {charges_info}
Fuzziness flags: {flags_json}
"""

async def opposition_analysis_node(state: CaseState) -> dict:
    await _broadcast("opposition_analysis", "start", "Opposition Agent: Analyzing validity of pressed charges...")
    
    try:
        llm = _pro_llm()
        facts = state.get("facts", [])
        flags = state.get("fuzziness_flags", [])
        timeline = state.get("timeline", [])
        
        client_profile = state.get("client_profile", {})
        charges_info = client_profile.get("charges_pressed") or client_profile.get("fir_sections") or "Unknown"
        
        system_prompt = inject_policy(OPPOSITION_ANALYSIS_PROMPT.format(
            facts_json=_to_json(facts),
            timeline_json=_to_json(timeline),
            charges_info=charges_info,
            flags_json=_to_json(flags),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Return ONLY the requested JSON."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            parsed = {}
        
        num_charges = len(parsed.get("charges_analysis", []))
        num_weak_points = len(parsed.get("opposition_weak_points", []))
        await _broadcast("opposition_analysis", "completed", "", f"Analyzed {num_charges} charges, found {num_weak_points} opposition weak points")
        
        await _broadcast("opposition_analysis", "completed", "", "Opposition Agent: Finished analyzing charges.")
        return {"opposition_analysis_dict": parsed}

    except Exception as exc:
        logger.error("opposition_analysis_node error: %s", exc, exc_info=True)
        await _broadcast("opposition_analysis", "completed", "", "Failed to analyze opposition case.")
        return {}


# ---------------------------------------------------------------------------
# Node 3 — Witness Candidate Agent  [Flash]
# ---------------------------------------------------------------------------

async def witness_candidate_node(state: CaseState) -> dict:
    """
    Surfaces entities with plausible first-hand knowledge.
    Explicitly forbidden from ranking by loyalty or inferring credibility
    from demographic attributes.
    """
    try:
        llm = _flash_llm()
        entity_graph = state.get("entity_graph", {"nodes": [], "edges": []})
        facts = state.get("facts", [])

        system_prompt = inject_policy(WITNESS_CANDIDATE_PROMPT.format(
            entity_graph_json=json.dumps(entity_graph, ensure_ascii=False),
            facts_json=_to_json(facts),
        ))

        response = await llm.ainvoke([("system", system_prompt)])

        try:
            raw_candidates = _parse_json_block(response.content)
            if not isinstance(raw_candidates, list):
                raw_candidates = raw_candidates.get("candidates", [])
        except json.JSONDecodeError:
            return {"witness_candidates": []}

        candidates: list[WitnessCandidate] = []
        for raw in raw_candidates:
            # Validate: reject any candidate with a "strength" or "supports_client" field
            if "strength" in raw or "supports_client" in raw or "loyalty" in raw:
                logger.warning("Rejecting witness candidate with forbidden ranking field: %s", raw.keys())
                continue
            try:
                candidates.append(WitnessCandidate(
                    entity_id=raw.get("entity_id", f"E-{uuid.uuid4().hex[:8]}"),
                    name_or_description=raw.get("name_or_description", "Unknown"),
                    possible_first_hand_knowledge=raw.get("possible_first_hand_knowledge", ""),
                    supporting_fact_refs=raw.get("supporting_fact_refs", []),
                    independence_or_bias_indicators=raw.get("independence_or_bias_indicators"),
                    availability=raw.get("availability", "unknown"),
                    lawyer_verification_question=raw.get("lawyer_verification_question", ""),
                ))
            except Exception as parse_err:
                logger.warning("Could not parse witness candidate: %s", parse_err)

        return {"witness_candidates": candidates}

    except Exception as exc:
        logger.error("witness_candidate_node error: %s", exc, exc_info=True)
        return {"witness_candidates": []}


# ---------------------------------------------------------------------------
# Node 4 — Argument Hypothesis Builder  [Pro]
# ---------------------------------------------------------------------------

async def argument_builder_node(state: CaseState) -> dict:
    """
    Builds client-side argument hypotheses using ONLY confirmed facts and
    citations already retrieved this run. No parametric memory citations.
    """
    await _broadcast("argument_builder", "start", "Arguments Agent: Building compensation calculation and liability arguments...")
    try:
        llm = _pro_llm()
        facts = state.get("facts", [])
        precedents = state.get("precedents", [])
        opposition = state.get("opposition_case", {})

        # Only use confirmed or unconfirmed CLIENT_STATED / DOCUMENT_EXTRACTED facts
        usable_facts = [
            f for f in facts
            if f.evidence_type in ("CLIENT_STATED", "DOCUMENT_EXTRACTED")
        ]

        # Build a set of valid source_ids from retrieved precedents
        valid_source_ids = {c.source_id for c in precedents}

        system_prompt = inject_policy(ARGUMENT_HYPOTHESIS_PROMPT.format(
            facts_json=_to_json(usable_facts),
            retrieved_citations_json=_to_json(precedents),
            opposition_hypotheses_json=json.dumps(
                opposition.get("hypotheses", []), ensure_ascii=False
            ),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Build argument hypotheses. Return JSON list of ArgumentHypothesis objects."),
        ])

        try:
            raw_args = _parse_json_block(response.content)
            if not isinstance(raw_args, list):
                raw_args = raw_args.get("arguments", [])
        except json.JSONDecodeError:
            return {"arguments": []}

        arguments: list[ArgumentHypothesis] = []
        for raw in raw_args:
            # Validate citations — only allow those from retrieved precedents
            raw_citations = raw.get("supporting_citations", [])
            validated_citations: list[CitationRecord] = []
            for rc in raw_citations:
                sid = rc.get("source_id", "")
                if sid in valid_source_ids:
                    cit = _validate_citation(rc)
                    if cit:
                        validated_citations.append(cit)
                else:
                    logger.warning(
                        "Argument builder tried to use citation not in retrieved set: %s — stripped.", sid
                    )

            # Reject any win-probability framing
            confidence = raw.get("confidence_status", "partial")
            if confidence not in ("supported", "partial", "unsupported"):
                confidence = "partial"

            try:
                arguments.append(ArgumentHypothesis(
                    proposition=raw.get("proposition", ""),
                    supporting_fact_refs=raw.get("supporting_fact_refs", []),
                    supporting_citations=validated_citations,
                    missing_evidence=raw.get("missing_evidence", []),
                    strongest_counterargument=raw.get("strongest_counterargument", ""),
                    confidence_status=confidence,
                ))
            except Exception as parse_err:
                logger.warning("Could not parse argument hypothesis: %s", parse_err)

        await _broadcast("argument_builder", "completed", "", f"Built {len(arguments)} arguments")
        return {"arguments": arguments}

    except Exception as exc:
        logger.error("argument_builder_node error: %s", exc, exc_info=True)
        await _broadcast("argument_builder", "completed", "", "Failed to build arguments")
        return {"arguments": []}


# ---------------------------------------------------------------------------
# Node 5 — Readiness & Evidence-Gap Analysis  [Flash]
# ---------------------------------------------------------------------------

_FORBIDDEN_FIELDS = {"win_probability", "win_chance", "success_rate", "odds", "likelihood_of_success"}


async def readiness_analysis_node(state: CaseState) -> dict:
    """
    Factor-level readiness assessment only. No win probability, ever.
    Validated by checking LLM output for forbidden field names.
    """
    await _broadcast("readiness_analysis", "start", "Readiness Agent: Scoring case completeness...")
    try:
        llm = _flash_llm()
        facts = state.get("facts", [])
        flags = state.get("fuzziness_flags", [])
        precedents = state.get("precedents", [])

        from app.legal_data.Motor_accident_schema import MOTOR_ACCIDENT_FIELDS
        schema_field_names = [f["field_name"] for f in MOTOR_ACCIDENT_FIELDS]

        system_prompt = inject_policy(READINESS_ANALYSIS_PROMPT.format(
            facts_json=_to_json(facts),
            fuzziness_flags=_to_json(flags),
            retrieved_citations_json=_to_json(precedents),
            property_schema_fields=json.dumps(schema_field_names),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Return ReadinessSignals JSON. Keys: evidence_completeness (float), evidence_completeness_reason, precedent_alignment, precedent_alignment_reason, open_fuzziness_load (int), open_fuzziness_details, documentary_corroboration (float), documentary_corroboration_reason, lawyer_summary. NO win probability field."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            parsed = {}

        # Reject any win-probability field
        for forbidden in _FORBIDDEN_FIELDS:
            if forbidden in parsed:
                del parsed[forbidden]
                logger.warning("Readiness node stripped forbidden field: %s", forbidden)

        # Compute defaults from state for any missing fields
        filled_fields = {f.field for f in facts}
        schema_fields = set(schema_field_names)
        completeness = len(filled_fields & schema_fields) / max(len(schema_fields), 1)
        open_high_flags = [f for f in flags if not f.resolved and f.severity in ("high", "medium")]
        doc_facts = [f for f in facts if f.evidence_type == "DOCUMENT_EXTRACTED"]
        doc_corr = len(doc_facts) / max(len(facts), 1)

        signals = ReadinessSignals(
            evidence_completeness=parsed.get("evidence_completeness", round(completeness, 2)),
            evidence_completeness_reason=parsed.get(
                "evidence_completeness_reason",
                f"{len(filled_fields & schema_fields)} of {len(schema_fields)} schema fields filled"
            ),
            precedent_alignment=parsed.get("precedent_alignment", "moderate"),
            precedent_alignment_reason=parsed.get(
                "precedent_alignment_reason",
                f"{len(precedents)} judgments retrieved"
            ),
            open_fuzziness_load=parsed.get("open_fuzziness_load", len(open_high_flags)),
            open_fuzziness_details=parsed.get(
                "open_fuzziness_details",
                f"{len(open_high_flags)} medium/high severity unresolved flags"
            ),
            documentary_corroboration=parsed.get("documentary_corroboration", round(doc_corr, 2)),
            documentary_corroboration_reason=parsed.get(
                "documentary_corroboration_reason",
                f"{len(doc_facts)} document-extracted facts of {len(facts)} total"
            ),
            lawyer_summary=parsed.get(
                "lawyer_summary",
                "Review the evidence completeness and open flags before filing."
            ),
        )

        await _broadcast("readiness_analysis", "completed", "", "Scored case completeness")
        return {"readiness_signals": signals}

    except Exception as exc:
        logger.error("readiness_analysis_node error: %s", exc, exc_info=True)
        await _broadcast("readiness_analysis", "completed", "", "Failed to score case completeness")
        return {}


# ---------------------------------------------------------------------------
# Node 6 — Packet Compiler  [Flash]
# ---------------------------------------------------------------------------

async def packet_compiler_node(state: CaseState) -> dict:
    """
    Assembles the full lawyer packet: Markdown, JSON, and WhatsApp summary.
    Includes win probability computed via PRO model.
    """
    await _broadcast("packet_compiler", "start", "Packet Compiler: Drafting final lawyer case packet...")
    try:
        llm = _pro_llm()

        facts = state.get("facts", [])
        timeline = state.get("timeline", [])
        documents = state.get("documents", [])
        flags = state.get("fuzziness_flags", [])
        precedents = state.get("precedents", [])
        opposition = state.get("opposition_case", {})
        opposition_analysis = state.get("opposition_analysis_dict", {})
        
        # Merge them safely
        combined_opposition = {**opposition, **opposition_analysis}
        
        arguments = state.get("arguments", [])
        readiness = state.get("readiness_signals")
        client_profile = state.get("client_profile", {})

        unresolved_flags = [f for f in flags if getattr(f, "resolved", False) == False]
        statutes = [p for p in precedents if getattr(p, "applicability_status", "") == "statute"]
        case_laws = [p for p in precedents if getattr(p, "applicability_status", "") != "statute"]

        system_prompt = inject_policy(f"""You are compiling a final case packet for an Indian MACT advocate.
You must construct the output as a valid JSON with the EXACT structure below. Do not deviate.

Required keys:
1. "markdown": A comprehensive markdown report of the case.
2. "whatsapp_summary": A max 500-word Hinglish summary.
3. "packet_json": Must have the exact 7 keys detailed below.

packet_json structure:
{{
  "initial_details": {{
    "incident_narrative": "write a clear summary of the incident",
    "chronological_timeline": [], // use provided timeline
    "client_profile": {{}}, // use provided client profile
    "victim_profile": {{}} // extract from facts where field starts with "victim_"
  }},
  "opposition_case": {{}}, // use provided opposition case
  "precedents": [], // use provided case laws
  "fuzziness_and_gaps": [], // use provided unresolved flags
  "law_sections": [], // use provided statutes
  "our_arguments": [], // use provided arguments
  "win_probability": {{
    "score": 0.0-1.0,
    "label": "Strong|Moderate|Weak|Unknown",
    "reasoning": "compute this based on evidence_completeness, precedent_alignment, and open_fuzziness_load",
    "caveat": "This is a preliminary AI assessment, not legal advice"
  }}
}}

Data:
Timeline: {_to_json(timeline)}
Client Profile: {_to_json(client_profile)}
Facts: {_to_json(facts)}
Opposition: {_to_json(combined_opposition)}
Case Laws: {_to_json(case_laws)}
Statutes: {_to_json(statutes)}
Unresolved Flags: {_to_json(unresolved_flags)}
Arguments: {_to_json(arguments)}
Readiness Signals: {_to_json(readiness) if readiness else 'None'}
""")

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Return ONLY the requested JSON."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            parsed = {
                "markdown": response.content,
                "packet_json": {},
                "whatsapp_summary": "Packet compiled. Please review the full brief.",
            }

        await _broadcast("packet_compiler", "completed", "", "Compiled case packet")
        return {
            "lawyer_packet_markdown": parsed.get("markdown", ""),
            "lawyer_packet_json": parsed.get("packet_json", {}),
        }

    except Exception as exc:
        logger.error("packet_compiler_node error: %s", exc, exc_info=True)
        await _broadcast("packet_compiler", "completed", "", "Failed to compile packet")
        return {
            "lawyer_packet_markdown": "# Error\nPacket compilation failed. Please retry.",
            "lawyer_packet_json": {},
        }


# ---------------------------------------------------------------------------
# Standalone — Lawyer Follow-Up Chat  [Flash]
# Used directly from the API layer, not in the graph
# ---------------------------------------------------------------------------

async def lawyer_chat(question: str, packet_json: dict, thread_id: str) -> dict:
    """
    Answers a lawyer's follow-up question grounded in the case packet.
    Same citation discipline as every other agent.
    """
    try:
        llm = _flash_llm()
        system_prompt = inject_policy(LAWYER_CHAT_PROMPT.format(
            case_thread_id=thread_id,
            lawyer_packet_json=json.dumps(packet_json, ensure_ascii=False, indent=2),
        ))
        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", question),
        ])
        # Try to extract citations from response
        text = response.content
        return {
            "answer": text,
            "citations_used": [],  # TODO: parse citations from LLM structured output
        }
    except Exception as exc:
        logger.error("lawyer_chat error: %s", exc, exc_info=True)
        return {"answer": "Sorry, an error occurred. Please try again.", "citations_used": []}
