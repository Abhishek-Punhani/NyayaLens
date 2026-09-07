import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.sqlite import SqliteSaver
from app.state import CaseState
from app.config import SQLITE_CHECKPOINT_PATH
from app.agents.analysis_agents import (
    precedent_research_node,
    statute_analysis_node,
    opposition_formulator_node,
    opposition_analysis_node,
    witness_candidate_node,
    argument_builder_node,
    readiness_analysis_node,
    packet_compiler_node,
)


def build_analysis_graph():
    builder = StateGraph(CaseState)

    builder.add_node("precedent_research",   precedent_research_node)
    builder.add_node("statute_analysis",     statute_analysis_node)
    builder.add_node("witness_candidate",    witness_candidate_node)
    builder.add_node("opposition_analysis",  opposition_analysis_node)
    builder.add_node("opposition_formulator", opposition_formulator_node)
    builder.add_node("argument_builder",     argument_builder_node)
    builder.add_node("readiness_analysis",   readiness_analysis_node)
    builder.add_node("packet_compiler",      packet_compiler_node)

    # Pure sequential DAG ensures no double-execution during fan-in
    # and provides a beautiful step-by-step SSE stream for the UI.
    builder.add_edge(START, "precedent_research")
    builder.add_edge("precedent_research", "statute_analysis")
    builder.add_edge("statute_analysis", "witness_candidate")
    
    # The two opposition nodes (Analysis first for charges, Formulator second for arguments)
    builder.add_edge("witness_candidate", "opposition_analysis")
    builder.add_edge("opposition_analysis", "opposition_formulator")
    
    builder.add_edge("opposition_formulator", "argument_builder")
    builder.add_edge("argument_builder", "readiness_analysis")
    builder.add_edge("readiness_analysis", "packet_compiler")
    builder.add_edge("packet_compiler", END)

    conn = sqlite3.connect(SQLITE_CHECKPOINT_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer)

analysis_graph = build_analysis_graph()
