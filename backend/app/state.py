from __future__ import annotations
from typing import TypedDict, Literal, Optional, Annotated
from pydantic import BaseModel, Field
from langgraph.graph import add_messages
import operator

EvidenceType = Literal["CLIENT_STATED", "DOCUMENT_EXTRACTED", "LEGAL_SOURCE", "INFERENCE", "UNKNOWN"]

class Fact(BaseModel):
    fact_id: str
    field: str
    value: str
    evidence_type: EvidenceType
    source_ref: str          # turn_id or document_id
    confidence: float        # 0.0–1.0
    status: Literal["unconfirmed", "confirmed", "superseded"]
    contradicts: list[str]   # fact_ids this contradicts
    epistemic_status: Optional[Literal["direct", "hearsay", "inferred"]] = None  # ← add

class CitationRecord(BaseModel):
    source_id: str
    source_url: Optional[str] = None
    exact_citation: str      # e.g. "Section 6, Specific Relief Act, 1963"
    supporting_passage: str  # short paraphrase, never long verbatim
    jurisdiction: str
    date: str                # judgment date or enactment date
    applicability_status: Literal["good_law", "superseded", "distinguishable", "unclear"]
    contradiction_or_limit: Optional[str] = None

class WitnessCandidate(BaseModel):
    entity_id: str
    name_or_description: str
    possible_first_hand_knowledge: str
    supporting_fact_refs: list[str]
    independence_or_bias_indicators: Optional[str] = None  # only if client stated it
    availability: Literal["known", "unknown"]
    lawyer_verification_question: str

class ArgumentHypothesis(BaseModel):
    proposition: str
    supporting_fact_refs: list[str]
    supporting_citations: list[CitationRecord]
    missing_evidence: list[str]
    strongest_counterargument: str
    confidence_status: Literal["supported", "partial", "unsupported"]

class ConsentRecord(BaseModel):
    recipient_confirmed: bool = False
    contents_confirmed: bool = False
    attachments_confirmed: bool = False
    permission_confirmed: bool = False
    timestamp: Optional[str] = None
    consent_transcript_ref: Optional[str] = None

class FuzzinessFlag(BaseModel):
    flag_id: str
    flag_type: Literal[
        "contradiction", "timeline_conflict", "vague_account",
        "missing_document", "liability_ambiguity",
        "jurisdiction_ambiguity", "witness_or_evidence_gap",
        "quantum_data_gap", "limitation_risk", "defense_vulnerability"
    ]
    severity: Literal["low", "medium", "high"]
    fact_refs: list[str]
    explanation: str
    neutral_clarifying_question: str
    blocks_handoff: bool
    resolved: bool = False

class DocumentRecord(BaseModel):
    doc_id: str
    doc_type: str
    filename: Optional[str] = None
    ocr_text: Optional[str] = None
    extracted_facts: list[Fact] = Field(default_factory=list)
    key_clauses: list[str] = Field(default_factory=list)
    registration_status: Optional[Literal["registered", "unregistered", "unclear"]] = None
    bsa63_certificate_needed: bool = False
    upload_status: Literal["requested", "uploaded", "failed", "ocr_done"]
    limitations_flag: Optional[str] = None

class ReadinessSignals(BaseModel):
    evidence_completeness: float        # 0–1, fraction of schema fields filled
    evidence_completeness_reason: str
    precedent_alignment: str            # "strong" | "moderate" | "weak" | "none"
    precedent_alignment_reason: str
    open_fuzziness_load: int            # count of unresolved high+medium flags
    open_fuzziness_details: str
    documentary_corroboration: float    # fraction of facts with document backing
    documentary_corroboration_reason: str
    lawyer_summary: str                 # plain-language: "here's what's solid and what's open"

class CaseState(TypedDict):
    thread_id: str
    language: str                        # detected language code
    case_type: Literal["property_dispute", "motor_accident", "criminal_fir"]
    law_version_context: Literal["pre_2024_codes", "post_2024_codes", "mixed", "unknown"]
    dispossession_track: Literal["section_6", "title_suit", "unclear", "not_determined"]
    intake_phase: Literal["open_narrative", "cross_question", "document_request", "confirmation", "complete", "human_handoff"]
    messages: Annotated[list, add_messages]   # full conversation history
    facts: Annotated[list[Fact], operator.add]
    documents: list[DocumentRecord]
    entity_graph: dict                   # networkx-serializable adjacency dict
    timeline: list[dict]                 # {event, date, fact_refs, certainty}
    fuzziness_flags: Annotated[list[FuzzinessFlag], operator.add]
    consent: ConsentRecord
    handoff_status: Literal["pending", "confirmed", "declined", "sent"]
    lawyer_name: Optional[str]
    lawyer_contact: Optional[str]
    precedents: Annotated[list[CitationRecord], operator.add]
    opposition_case: Optional[dict]
    opposition_analysis_dict: Optional[dict]
    witness_candidates: Annotated[list[WitnessCandidate], operator.add]
    arguments: Annotated[list[ArgumentHypothesis], operator.add]
    readiness_signals: Optional[ReadinessSignals]
    lawyer_packet_markdown: Optional[str]
    lawyer_packet_json: Optional[dict]
    accident_subtype: Optional[str]
    # PEACE model interview stage — controls cross_question_node behavior
    interview_stage: Optional[Literal[
        "engage", "narrative", "timeline_liability",
        "regulatory", "quantum_profiling", "defense_audit", "closure"
    ]]
    # Victim/client profile for Sarla Verma / Pranay Sethi MACT compensation calculation
    client_profile: Optional[dict]
