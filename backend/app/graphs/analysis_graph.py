import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.sqlite import SqliteSaver
from app.state import CaseState
from app.config import SQLITE_CHECKPOINT_PATH
from app.agents.analysis_agents import (
    precedent_research_node,
    opposition_formulator_node,
    witness_candidate_node,
    argument_builder_node,
    readiness_analysis_node,
    packet_compiler_node,
)


def fan_out_analysis(state: CaseState):
    """Fan out to three independent agents in parallel."""
    return [
        Send("precedent_research", state),
        Send("opposition_formulator", state),
        Send("witness_candidate", state),
    ]


def build_analysis_graph():
    builder = StateGraph(CaseState)

    builder.add_node("precedent_research", precedent_research_node)
    builder.add_node("opposition_formulator", opposition_formulator_node)
    builder.add_node("witness_candidate", witness_candidate_node)
    builder.add_node("argument_builder", argument_builder_node)
    builder.add_node("readiness_analysis", readiness_analysis_node)
    builder.add_node("packet_compiler", packet_compiler_node)

    builder.add_conditional_edges(
        START,
        fan_out_analysis,
        ["precedent_research", "opposition_formulator", "witness_candidate"],
    )

    builder.add_edge("precedent_research", "argument_builder")
    builder.add_edge("opposition_formulator", "argument_builder")
    builder.add_edge("witness_candidate", "packet_compiler")  # witness goes directly to compiler

    builder.add_edge("argument_builder", "readiness_analysis")
    builder.add_edge("readiness_analysis", "packet_compiler")
    builder.add_edge("packet_compiler", END)

    # SqliteSaver v3+ API: pass an open sqlite3 connection
    conn = sqlite3.connect(SQLITE_CHECKPOINT_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer)


analysis_graph = build_analysis_graph()
