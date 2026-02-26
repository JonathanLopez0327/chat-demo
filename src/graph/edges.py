"""Conditional edge routing functions for simplified flow."""
from __future__ import annotations

from typing import Literal


def route_after_classify(
    state: dict,
) -> Literal["save", "collect_description", "__end__"]:
    """If classification succeeded → save directly; if failed → retry description.

    After max retries (unhandled) → end without saving.
    """
    if state.get("current_node") == "classify_ok":
        return "save"
    if state.get("current_node") == "unhandled":
        return "__end__"
    return "collect_description"
