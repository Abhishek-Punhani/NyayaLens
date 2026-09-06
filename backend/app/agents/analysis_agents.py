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
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import GOOGLE_API_KEY, MODEL_FLASH, MODEL_PRO
from app.legal_data.corpus_builder import search_corpus
from app.legal_data.section_mapping import PROPERTY_DISPUTE_SECTIONS
from app.prompts.analysis_prompts import (
    ARGUMENT_HYPOTHESIS_PROMPT,
    LAWYER_CHAT_PROMPT,
    OPPOSITION_PROMPT,
    PACKET_COMPILER_PROMPT,
    PRECEDENT_RESEARCH_PROMPT,
    READINESS_ANALYSIS_PROMPT,
    WITNESS_CANDIDATE_PROMPT,
)
from app.prompts.global_policy import inject_policy
from app.state import (
    ArgumentHypothesis,
    CaseState,
    CitationRecord,
    Fact,
    FuzzinessFlag,
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


def _parse_json_block(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(text)


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


def _build_static_citations(track: str) -> list[CitationRecord]:
    """Return pre-verified statutory citations appropriate to the track."""
    citations: list[CitationRecord] = []
    if track in ("section_6", "unclear", "not_determined"):
        s = PROPERTY_DISPUTE_SECTIONS["SRA_6"]
        citations.append(CitationRecord(
            source_id="SRA_6_1963",
            source_url="https://indiankanoon.org/doc/1054366/",
            exact_citation=s["exact_citation"],
            supporting_passage=s["summary"],
            jurisdiction="India",
            date="1963",
            applicability_status=s["applicability_status"],
        ))
        citations.append(CitationRecord(
            source_id="SRA_6_RAME_GOWDA_2004",
            source_url="https://indiankanoon.org/doc/1507758/",
            exact_citation="Rame Gowda (Dead) by LRs v. M. Varadappa Naidu, (2004) 1 SCC 769",
            supporting_passage=(
                "A person in settled possession cannot be dispossessed without due process of law, "
                "even by the rightful owner."
            ),
            jurisdiction="Supreme Court of India",
            date="2004",
            applicability_status="good_law",
        ))
    if track in ("title_suit", "unclear"):
        s = PROPERTY_DISPUTE_SECTIONS["LIMITATION_ART_65"]
        citations.append(CitationRecord(
            source_id="LIM_ART65_1963",
            source_url="https://indiankanoon.org/doc/1317393/",
            exact_citation=s["exact_citation"],
            supporting_passage=s["summary"],
            jurisdiction="India",
            date="1963",
            applicability_status=s["applicability_status"],
        ))
    return citations


# ---------------------------------------------------------------------------
# Node 1 — Precedent Research Agent  [Pro]
# ---------------------------------------------------------------------------

async def precedent_research_node(state: CaseState) -> dict:
    """
    Retrieves relevant judgments from ChromaDB + returns verified statutory
    citations. Never calls retrieved content 'transcripts' — always 'judgments'.
    Every CitationRecord is validated for mandatory fields before reaching
    the Argument Builder.
    """
    try:
        llm = _pro_llm()
        facts = state.get("facts", [])
        flags = state.get("fuzziness_flags", [])
        track = state.get("dispossession_track", "not_determined")
        law_ctx = state.get("law_version_context", "unknown")

        # Start with verified static citations
        citations: list[CitationRecord] = _build_static_citations(track)

        # Generate search queries via LLM
        system_prompt = inject_policy(PRECEDENT_RESEARCH_PROMPT.format(
            facts_json=_to_json(facts),
            dispossession_track=track,
            law_version_context=law_ctx,
            fuzziness_flags=_to_json(flags),
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Return a JSON list of search query strings to find relevant judgments/decisions. Only JSON array."),
        ])

        try:
            queries = _parse_json_block(response.content)
            if not isinstance(queries, list):
                queries = [str(queries)]
        except (json.JSONDecodeError, TypeError):
            queries = [f"property possession dispossession {track} India"]

        # Search ChromaDB corpus
        for query in queries[:4]:   # cap at 4 queries
            try:
                results = search_corpus(
                    query=query,
                    case_type="property_dispute",
                    law_version=law_ctx,
                    n_results=3,
                )
                for res in results:
                    meta = res.get("metadata", {})
                    # Build CitationRecord from corpus metadata
                    cit = CitationRecord(
                        source_id=res.get("id", f"CORPUS-{uuid.uuid4().hex[:8]}"),
                        source_url=meta.get("source_url"),
                        exact_citation=meta.get("exact_citation", res.get("id", "")),
                        supporting_passage=res.get("document", "")[:300],   # short paraphrase
                        jurisdiction=meta.get("court", "India"),
                        date=meta.get("date", "unclear"),
                        applicability_status=meta.get("applicability_status", "unclear"),
                        contradiction_or_limit=meta.get("contradiction_or_limit"),
                    )
                    if cit.source_id and cit.exact_citation:
                        citations.append(cit)
            except Exception as search_err:
                logger.warning("Corpus search failed for query '%s': %s", query, search_err)

        # BSA §63 citation if electronic evidence in facts
        has_recording = any(
            "recording" in f.value.lower() or "video" in f.value.lower() or "whatsapp" in f.value.lower()
            for f in facts
        )
        if has_recording and law_ctx in ("post_2024_codes", "mixed", "unknown"):
            s = PROPERTY_DISPUTE_SECTIONS["BSA_63"]
            citations.append(CitationRecord(
                source_id="BSA_63_2023",
                source_url="https://prsindia.org/billtrack/the-bharatiya-sakshya-bill-2023",
                exact_citation=s["exact_citation"],
                supporting_passage=s["summary"],
                jurisdiction="India",
                date="2023",
                applicability_status=s["applicability_status"],
            ))

        return {"precedents": citations}

    except Exception as exc:
        logger.error("precedent_research_node error: %s", exc, exc_info=True)
        return {"precedents": _build_static_citations(state.get("dispossession_track", "unclear"))}


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

        return {"arguments": arguments}

    except Exception as exc:
        logger.error("argument_builder_node error: %s", exc, exc_info=True)
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
    try:
        llm = _flash_llm()
        facts = state.get("facts", [])
        flags = state.get("fuzziness_flags", [])
        precedents = state.get("precedents", [])

        system_prompt = inject_policy(READINESS_ANALYSIS_PROMPT.format(
            facts_json=_to_json(facts),
            fuzziness_flags=_to_json(flags),
            retrieved_citations_json=_to_json(precedents),
            property_schema_fields=json.dumps([
                "dispossession_recency", "property_identification", "ownership_chain",
                "other_party_identity_and_relationship", "how_dispossession_happened",
                "self_help_attempted_by_client", "documents_available",
            ]),
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
        schema_fields = {
            "dispossession_recency", "property_identification", "ownership_chain",
            "other_party_identity_and_relationship", "how_dispossession_happened",
            "self_help_attempted_by_client", "documents_available",
        }
        completeness = len(filled_fields & schema_fields) / len(schema_fields)
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

        return {"readiness_signals": signals}

    except Exception as exc:
        logger.error("readiness_analysis_node error: %s", exc, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Node 6 — Packet Compiler  [Flash]
# ---------------------------------------------------------------------------

async def packet_compiler_node(state: CaseState) -> dict:
    """
    Assembles the full lawyer packet: Markdown, JSON, and WhatsApp summary.
    No win probability anywhere.
    """
    try:
        llm = _flash_llm()

        facts = state.get("facts", [])
        timeline = state.get("timeline", [])
        entity_graph = state.get("entity_graph", {})
        documents = state.get("documents", [])
        flags = state.get("fuzziness_flags", [])
        precedents = state.get("precedents", [])
        opposition = state.get("opposition_case", {})
        witnesses = state.get("witness_candidates", [])
        arguments = state.get("arguments", [])
        readiness = state.get("readiness_signals")
        lawyer_name = state.get("lawyer_name", "Vakeel Sahab")

        system_prompt = inject_policy(PACKET_COMPILER_PROMPT.format(
            facts_json=_to_json(facts),
            timeline_json=_to_json(timeline),
            entity_graph_json=json.dumps(entity_graph, ensure_ascii=False),
            documents_json=_to_json(documents),
            fuzziness_flags=_to_json(flags),
            precedents_json=_to_json(precedents),
            opposition_case_json=json.dumps(opposition, ensure_ascii=False),
            witness_candidates_json=_to_json(witnesses),
            arguments_json=_to_json(arguments),
            readiness_signals_json=_to_json(readiness) if readiness else "{}",
            lawyer_name=lawyer_name,
        ))

        response = await llm.ainvoke([
            ("system", system_prompt),
            ("human", "Compile the complete lawyer packet. Return JSON with keys: markdown (str), packet_json (dict), whatsapp_summary (str, max 500 words in Hinglish)."),
        ])

        try:
            parsed = _parse_json_block(response.content)
        except json.JSONDecodeError:
            # Fallback: use raw response as markdown
            parsed = {
                "markdown": response.content,
                "packet_json": {},
                "whatsapp_summary": "Packet compiled. Please review the full brief.",
            }

        return {
            "lawyer_packet_markdown": parsed.get("markdown", ""),
            "lawyer_packet_json": parsed.get("packet_json", {}),
        }

    except Exception as exc:
        logger.error("packet_compiler_node error: %s", exc, exc_info=True)
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
