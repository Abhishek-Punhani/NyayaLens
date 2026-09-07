"""NyayaLens — State helpers for the API layer."""
from __future__ import annotations

import json
from typing import Optional

from app.state import CaseState, Fact, FuzzinessFlag


def get_state(graph, thread_id: str) -> Optional[CaseState]:
    """Retrieve the latest checkpointed state for a thread."""
    try:
        snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
        if snapshot and snapshot.values:
            return snapshot.values  # type: ignore[return-value]
    except Exception:
        pass
    return None


def state_to_json(state: CaseState) -> dict:
    """JSON-serializable representation of CaseState."""
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
                json.dumps(v)
                out[k] = v
            except (TypeError, ValueError):
                out[k] = str(v)
    return out


def format_facts_for_prompt(facts: list[Fact]) -> str:
    """Format fact list as indented JSON string for prompt injection."""
    return json.dumps(
        [f.model_dump() for f in facts],
        ensure_ascii=False,
        indent=2,
    )


def get_unresolved_flags(flags: list[FuzzinessFlag]) -> list[FuzzinessFlag]:
    """Return flags that are not yet resolved."""
    return [f for f in flags if not f.resolved]


def get_blocking_flags(flags: list[FuzzinessFlag]) -> list[FuzzinessFlag]:
    """Return unresolved flags that block handoff."""
    return [f for f in flags if not f.resolved and f.blocks_handoff]


def get_confirmed_facts(facts: list[Fact]) -> list[Fact]:
    """Return facts with status='confirmed'."""
    return [f for f in facts if f.status == "confirmed"]


def get_document_facts(facts: list[Fact]) -> list[Fact]:
    """Return facts extracted from documents."""
    return [f for f in facts if f.evidence_type == "DOCUMENT_EXTRACTED"]


def schema_completeness(facts: list[Fact]) -> float:
    """Fraction of motor accident schema fields that have been collected."""
    from app.legal_data.Motor_accident_schema import MOTOR_ACCIDENT_FIELDS
    schema_fields = {f["field_name"] for f in MOTOR_ACCIDENT_FIELDS}
    filled = {f.field for f in facts} & schema_fields
    return len(filled) / max(len(schema_fields), 1)
