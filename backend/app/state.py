from __future__ import annotations
from typing import TypedDict, Literal, Optional, Annotated, Union, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from langgraph.graph import add_messages
import operator
import re

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


EmploymentType = Literal[
    "permanent_salaried",
    "self_employed",
    "daily_wager",
    "homemaker",
    "student",
    "retired",
]

IncomeProofType = Literal[
    "itr",
    "salary_slip",
    "bank_statement",
    "minimum_wage_notification",
    "none",
]

DrivingLicenseValidity = Literal[
    "valid",
    "expired",
    "suspended",
    "no_license",
]

CriminalHistory = Literal[
    "none",
    "pending_fir",
    "prior_conviction",
    "traffic_challans",
]


class Dependent(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    age: Optional[int] = None
    financial_dependency: Optional[str] = None  # full | partial | none | dependent | independent


class ClientProfile(BaseModel):
    """
    Legally required Indian MACT Client & Victim Profile.
    Anchored to:
    - Sarla Verma v. DTC (2009) [Multiplier table & personal living expense deductions]
    - National Insurance v. Pranay Sethi (2017) [Future prospects & conventional heads]
    - Raj Kumar v. Ajay Kumar (2011) [Functional disability vs earning capacity loss]
    - Motor Vehicles Act, 1988 (§166, §168, §147-150)
    - Bharatiya Sakshya Adhiniyam, 2023 (§149 / IEA §146)
    """
    model_config = ConfigDict(extra="allow")

    full_name: Optional[str] = None
    age: Optional[int] = None
    dob: Optional[str] = None
    education_qualification: Optional[str] = None  # e.g. 10th, 12th, Graduate, Postgraduate, Professional
    occupation: Optional[str] = None
    employer_name: Optional[str] = None
    employment_type: Optional[Union[EmploymentType, str]] = None
    monthly_income: Optional[float] = None
    income_proof_type: Optional[Union[IncomeProofType, str]] = None
    dependents: list[dict] = Field(default_factory=list)  # list of dict (name, relation, age, financial_dependency)
    driving_license_number: Optional[str] = None
    driving_license_validity: Optional[Union[DrivingLicenseValidity, str]] = None
    criminal_history: Optional[Union[CriminalHistory, str]] = None
    pre_existing_conditions: Optional[str] = None
    disability_percentage: Optional[float] = None
    functional_disability_impact: Optional[str] = None

    @field_validator("age", mode="before")
    @classmethod
    def _coerce_age(cls, v: Any) -> Optional[int]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return int(v)
        if isinstance(v, str):
            digits = "".join(ch for ch in v if ch.isdigit())
            return int(digits) if digits else None
        return None

    @field_validator("monthly_income", "disability_percentage", mode="before")
    @classmethod
    def _coerce_float(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            cleaned = v.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("%", "").strip()
            m = re.search(r"[-+]?\d*\.?\d+", cleaned)
            if m:
                return float(m.group(0))
        return None


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
    # Comprehensive MACT Victim/client profile conforming to ClientProfile schema
    client_profile: Optional[Union[dict, ClientProfile]]

