"""Assemble and compile the LangGraph StateGraph.

Fully connected graph using interrupt() for human-in-the-loop.
Debug/test with: langgraph dev

Flow:
  START → greeting →(cond)→ register_user ─┐
                    →(cond)→ collect_description ←┘
                              ↓
                           classify →(cond)→ confirm_classification
                                             →(cond)→ collect_fields ←──┐
                                                       ↓(loop)──────────┘
                                                    confirmation
                                                       ↓
                                                 process_confirmation
                                                   →(cond)→ save → END
                                                   →(cond)→ edit → collect_fields
                                                   →(cond)→ END (cancel)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.graph.edges import (
    route_after_classify,
    route_after_collect_fields,
    route_after_confirm_classification,
    route_after_edit,
    route_after_greeting,
    route_after_process_confirmation,
    route_after_register,
)
from src.graph.nodes import (
    classify_node,
    collect_description_node,
    collect_fields_node,
    confirmation_node,
    confirm_classification_node,
    edit_node,
    greeting_node,
    process_confirmation_node,
    register_user_node,
    save_node,
)
from src.graph.state import ConversationState


def build_graph():
    """Build and compile the incident reporting graph."""
    builder = StateGraph(ConversationState)

    # ── Nodes ────────────────────────────────────────────────────
    builder.add_node("greeting", greeting_node)
    builder.add_node("register_user", register_user_node)
    builder.add_node("collect_description", collect_description_node)
    builder.add_node("classify", classify_node)
    builder.add_node("confirm_classification", confirm_classification_node)
    builder.add_node("collect_fields", collect_fields_node)
    builder.add_node("confirmation", confirmation_node)
    builder.add_node("process_confirmation", process_confirmation_node)
    builder.add_node("edit", edit_node)
    builder.add_node("save", save_node)

    # ── Edges ────────────────────────────────────────────────────
    builder.add_edge(START, "greeting")
    builder.add_conditional_edges("greeting", route_after_greeting)
    builder.add_conditional_edges("register_user", route_after_register)
    builder.add_edge("collect_description", "classify")
    builder.add_conditional_edges("classify", route_after_classify)
    builder.add_conditional_edges("confirm_classification", route_after_confirm_classification)
    builder.add_conditional_edges("collect_fields", route_after_collect_fields)
    builder.add_edge("confirmation", "process_confirmation")
    builder.add_conditional_edges("process_confirmation", route_after_process_confirmation)
    builder.add_conditional_edges("edit", route_after_edit)
    builder.add_edge("save", END)

    return builder.compile()


agent = build_graph()
