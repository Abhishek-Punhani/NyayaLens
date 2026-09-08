from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class FactCandidate(BaseModel):
    field: str
    value: str
    evidence_type: str = "CLIENT_STATED"
    confidence: float = 0.8
    epistemic_status: str = "direct"

class CrossQuestionOutput(BaseModel):
    spoken_response: str
    next_question: str
    reason: str
    interview_stage_after: str
    updated_fact_candidates: List[FactCandidate]
    client_profile_update: Dict[str, Any]
    requires_human_review: bool

class CaseTypeOutput(BaseModel):
    case_type: str
    accident_subtype: str
    reason: str

class EntityGraph(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class TimelineEvent(BaseModel):
    event: str
    date: str
    time: Optional[str] = None
    fact_refs: List[str]
    certainty: str

class EntityTrackerOutput(BaseModel):
    entity_graph: EntityGraph
    timeline: List[TimelineEvent]
    new_facts: List[Dict[str, Any]]
    client_profile_update: Dict[str, Any]
    ambiguity_questions: List[str]

class FuzzinessFlagItem(BaseModel):
    flag_id: str
    type: str
    severity: str
    fact_refs: List[str]
    explanation: str
    neutral_clarifying_question: str
    blocks_handoff: bool

class FuzzinessOutput(BaseModel):
    flags: List[FuzzinessFlagItem]

class DocumentRequestItem(BaseModel):
    document_type: str
    material_or_optional: str
    upload_instruction: str

class DocumentRequestOutput(BaseModel):
    documents: List[DocumentRequestItem]

class ConsentIntentOutput(BaseModel):
    verdict: str
    reason: str
