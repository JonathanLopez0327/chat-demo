"""Conditional edge routing functions for incident flow."""
from __future__ import annotations

from typing import Literal


def route_after_classify(
    state: dict,
) -> Literal["save", "collect_required_evidence", "collect_description", "__end__"]:
    """If classification succeeded → save directly; if failed → retry description.

    After max retries (unhandled) → end without saving.
    """
    if state.get("current_node") == "classify_ok":
        return "save"
    if state.get("current_node") == "requirements_needed":
        return "collect_required_evidence"
    if state.get("current_node") == "unhandled":
        return "__end__"
    return "collect_description"


def route_after_collect_required_evidence(
    state: dict,
) -> Literal["save", "collect_required_evidence"]:
    """If all required evidence/info is complete → save; else keep collecting."""
    if state.get("current_node") == "requirements_ok":
        return "save"
    return "collect_required_evidence"
