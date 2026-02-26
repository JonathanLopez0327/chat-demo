"""Assemble and compile the LangGraph StateGraph.

Simplified flow (1 user interaction, auto-save):
  START → greeting → collect_description → classify →(cond)→ save → END
                           ↑                    |
                           └────────────────────┘ (retry)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.edges import route_after_classify
from src.graph.nodes import (
    classify_node,
    collect_description_node,
    greeting_node,
    save_node,
)
from src.graph.state import ConversationState


def build_graph():
    """Build and compile the incident reporting graph."""
    builder = StateGraph(ConversationState)

    # ── Nodes ────────────────────────────────────────────────────
    builder.add_node("greeting", greeting_node)
    builder.add_node("collect_description", collect_description_node)
    builder.add_node("classify", classify_node)
    builder.add_node("save", save_node)

    # ── Edges ────────────────────────────────────────────────────
    builder.add_edge(START, "greeting")
    builder.add_edge("greeting", "collect_description")
    builder.add_edge("collect_description", "classify")
    builder.add_conditional_edges("classify", route_after_classify)
    builder.add_edge("save", END)

    return builder.compile()


agent = build_graph()
