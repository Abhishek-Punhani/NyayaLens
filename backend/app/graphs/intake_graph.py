from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import CaseState
from app.agents.intake_agents import (
    case_type_router_node,
    cross_question_node,
    fuzziness_detector_node,
    entity_tracker_node,
    document_request_node,
    confirmation_flow_node,
)
from app.legal_data.Motor_accident_schema import get_missing_fields

# Shared in-memory saver
shared_checkpointer = MemorySaver()


def should_continue_intake(state: CaseState) -> str:
    """
    Conditional edge after fuzziness_detector:
    - Pending documents → document_request
    - Closure stage → confirmation
    - Otherwise → back to cross_question for next turn
    """
    stage = state.get("interview_stage", "engage")
    docs_pending = [
        d for d in state.get("documents", [])
        if getattr(d, "upload_status", "") == "requested"
    ]

    if docs_pending:
        return "document_request"

    if stage == "closure":
        return "confirmation_flow"

    return "cross_question"


def build_intake_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = shared_checkpointer

    builder = StateGraph(CaseState)

    builder.add_node("cross_question", cross_question_node)
    builder.add_node("entity_tracker", entity_tracker_node)
    builder.add_node("fuzziness_detector", fuzziness_detector_node)
    builder.add_node("document_request", document_request_node)
    builder.add_node("confirmation_flow", confirmation_flow_node)

    # ── Fast path ──────────────────────────────────────────────────────────────
    # START → cross_question (LLM → interrupt → wait for client answer)
    # When client answers, graph resumes inside cross_question, saves raw fact,
    # then flows to the enrichment pipeline below.
    builder.add_edge(START, "cross_question")

    # ── Enrichment pipeline (runs AFTER cross_question returns from interrupt) ─
    # Runs sequentially: entity extraction → fuzziness detection → next question
    builder.add_edge("cross_question", "entity_tracker")
    builder.add_edge("entity_tracker", "fuzziness_detector")

    builder.add_conditional_edges(
        "fuzziness_detector",
        should_continue_intake,
        {
            "document_request": "document_request",
            "confirmation_flow": "confirmation_flow",
            "cross_question": "cross_question",
        },
    )
    builder.add_edge("document_request", "cross_question")
    builder.add_edge("confirmation_flow", END)

    return builder.compile(checkpointer=checkpointer, interrupt_before=["confirmation_flow"])


intake_graph = build_intake_graph()
