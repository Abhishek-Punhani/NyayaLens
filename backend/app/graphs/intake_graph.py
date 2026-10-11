from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.state import CaseState
from app.agents.intake_agents import (
    ask_node,
    extract_merge_node,
    document_request_node,
    confirmation_step1_node,
    confirmation_step2_node,
    confirmation_step3_node,
    confirmation_step4_node,
)

# Shared in-memory saver (swap for SqliteSaver/RedisSaver for multi-process / persistence)
shared_checkpointer = MemorySaver()


def _route_after_extract(state: CaseState) -> str:
    """
    Conditional edge after extract_merge_node. Priority order:
      1. intake_phase == "confirmation"  → confirmation_step1
      2. Requested-but-not-yet-uploaded docs → document_request
      3. All other stages → ask (next question)
    """
    # Completion signalled by ask_node when next_question() returned None
    if state.get("intake_phase") == "confirmation":
        return "confirmation_step1"

    # Pending document uploads
    docs_pending = [
        d for d in state.get("documents", [])
        if getattr(d, "upload_status", "") == "requested"
    ]
    if docs_pending:
        return "document_request"

    return "ask"


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

    # ── Core nodes ────────────────────────────────────────────────────────────
    builder.add_node("ask",              ask_node)
    builder.add_node("extract_merge",    extract_merge_node)
    builder.add_node("document_request", document_request_node)
    builder.add_node("confirmation_step1", confirmation_step1_node)
    builder.add_node("confirmation_step2", confirmation_step2_node)
    builder.add_node("confirmation_step3", confirmation_step3_node)
    builder.add_node("confirmation_step4", confirmation_step4_node)

    # ── Main intake loop ──────────────────────────────────────────────────────
    # START → ask (suspends via interrupt) → extract_merge → route
    builder.add_edge(START, "ask")
    builder.add_edge("ask", "extract_merge")

    builder.add_conditional_edges(
        "extract_merge",
        _route_after_extract,
        {
            "ask":               "ask",
            "document_request":  "document_request",
            "confirmation_step1": "confirmation_step1",
        },
    )
    # After document upload, resume interview loop
    builder.add_edge("document_request", "ask")

    # ── Consent flow: 4 separate nodes, each owns its own interrupt() ─────────
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

    return builder.compile(checkpointer=checkpointer)


intake_graph = build_intake_graph()

