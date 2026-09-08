from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import CaseState
from app.agents.intake_agents import (
    case_type_router_node,
    cross_question_node,
    fuzziness_detector_node,
    entity_tracker_node,
    document_request_node,
    confirmation_step1_node,
    confirmation_step2_node,
    confirmation_step3_node,
    confirmation_step4_node,
)

# Shared in-memory saver (swap for SqliteSaver/RedisSaver for multi-process / persistence)
shared_checkpointer = MemorySaver()


def should_continue_intake(state: CaseState) -> str:
    """
    Conditional edge after fuzziness_detector. Priority order:
      1. Requested-but-not-yet-uploaded docs → document_request
      2. Closure stage + blocking fuzziness flags → cross_question (must resolve first)
      3. Closure stage with no blockers → confirmation_step1
      4. All other stages → cross_question for next turn
    """
    stage = state.get("interview_stage", "engage")

    # Priority 1: pending document uploads
    docs_pending = [
        d for d in state.get("documents", [])
        if getattr(d, "upload_status", "") == "requested"
    ]
    if docs_pending:
        return "document_request"

    # Priority 2+3: closure stage
    if stage == "closure":
        blocking_flags = [
            f for f in state.get("fuzziness_flags", [])
            if not f.resolved and f.blocks_handoff
        ]
        if blocking_flags:
            # Cannot hand off with unresolved blocking contradictions
            return "cross_question"
        return "confirmation_step1"

    return "cross_question"


def _consent_step_edge(next_step: str):
    """
    Returns a conditional-edge function for a consent step node.
    If handoff_status is declined or pending, exits to END.
    Otherwise advances to next_step.
    """
    def _edge(state: CaseState) -> str:
        hs = state.get("handoff_status", "")
        if hs in ("declined", "pending"):
            return END
        return next_step
    return _edge


def build_intake_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = shared_checkpointer

    builder = StateGraph(CaseState)

    builder.add_node("cross_question",      cross_question_node)
    builder.add_node("entity_tracker",      entity_tracker_node)
    builder.add_node("fuzziness_detector",  fuzziness_detector_node)
    builder.add_node("document_request",    document_request_node)
    builder.add_node("confirmation_step1",  confirmation_step1_node)
    builder.add_node("confirmation_step2",  confirmation_step2_node)
    builder.add_node("confirmation_step3",  confirmation_step3_node)
    builder.add_node("confirmation_step4",  confirmation_step4_node)

    # ── Main intake loop ────────────────────────────────────────────────────
    builder.add_edge(START, "cross_question")
    builder.add_edge("cross_question", "entity_tracker")
    builder.add_edge("entity_tracker", "fuzziness_detector")

    builder.add_conditional_edges(
        "fuzziness_detector",
        should_continue_intake,
        {
            "document_request":   "document_request",
            "confirmation_step1": "confirmation_step1",
            "cross_question":     "cross_question",
        },
    )
    builder.add_edge("document_request", "cross_question")

    # ── Consent flow: 4 separate nodes, each owns its own interrupt() ───────
    # After each step, check handoff_status — declined/pending exits to END.
    # No interrupt_before needed: each step node blocks on its own interrupt().
    builder.add_conditional_edges(
        "confirmation_step1",
        _consent_step_edge("confirmation_step2"),
        {"confirmation_step2": "confirmation_step2", END: END},
    )
    builder.add_conditional_edges(
        "confirmation_step2",
        _consent_step_edge("confirmation_step3"),
        {"confirmation_step3": "confirmation_step3", END: END},
    )
    builder.add_conditional_edges(
        "confirmation_step3",
        _consent_step_edge("confirmation_step4"),
        {"confirmation_step4": "confirmation_step4", END: END},
    )
    builder.add_edge("confirmation_step4", END)

    # No interrupt_before — each confirmation step manages its own interrupt()
    return builder.compile(checkpointer=checkpointer)


intake_graph = build_intake_graph()
