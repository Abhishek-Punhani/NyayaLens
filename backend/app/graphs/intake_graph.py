import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from app.state import CaseState
from app.config import SQLITE_CHECKPOINT_PATH
from app.agents.intake_agents import (
    case_type_router_node,
    cross_question_node,
    fuzziness_detector_node,
    entity_tracker_node,
    document_request_node,
    confirmation_flow_node,
)
from app.legal_data.Motor_accident_schema import get_missing_fields


def should_continue_intake(state: CaseState) -> str:
    """
    Conditional edge: decide what to do after cross_question node runs.
    - If documents are requested but not uploaded: route to document_request
    - If interview_stage is 'closure': route to confirmation
    - Otherwise: loop back to cross_question
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


def build_intake_graph():
    builder = StateGraph(CaseState)

    builder.add_node("case_type_router", case_type_router_node)
    builder.add_node("cross_question", cross_question_node)
    builder.add_node("fuzziness_detector", fuzziness_detector_node)
    builder.add_node("entity_tracker", entity_tracker_node)
    builder.add_node("document_request", document_request_node)
    builder.add_node("confirmation_flow", confirmation_flow_node)

    builder.add_edge(START, "case_type_router")
    builder.add_edge("case_type_router", "cross_question")

    # Parallel fan-out from cross_question
    builder.add_edge("cross_question", "fuzziness_detector")
    builder.add_edge("cross_question", "entity_tracker")

    builder.add_conditional_edges(
        "fuzziness_detector",
        should_continue_intake,
        {
            "fuzziness_detector": "fuzziness_detector",
            "document_request": "document_request",
            "confirmation_flow": "confirmation_flow",
            "cross_question": "cross_question",
        },
    )
    builder.add_edge("entity_tracker", "fuzziness_detector")
    builder.add_edge("document_request", "cross_question")
    builder.add_edge("confirmation_flow", END)

    # SqliteSaver v3+ API: pass an open sqlite3 connection (thread_check_same_thread=False for async)
    conn = sqlite3.connect(SQLITE_CHECKPOINT_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer, interrupt_before=["confirmation_flow"])


intake_graph = build_intake_graph()
