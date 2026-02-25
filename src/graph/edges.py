"""Conditional edge routing functions."""
from __future__ import annotations

from typing import Literal


def route_after_greeting(
    state: dict,
) -> Literal["register_user", "collect_description"]:
    if state.get("current_node") == "greeting_new":
        return "register_user"
    return "collect_description"


def route_after_register(
    state: dict,
) -> Literal["register_user", "collect_description"]:
    if state.get("current_node") == "greeting_new":
        return "register_user"
    return "collect_description"


def route_after_classify(
    state: dict,
) -> Literal["confirm_classification", "collect_description"]:
    if state.get("classification_candidates"):
        return "confirm_classification"
    # classify_failed → retry description
    return "collect_description"


def route_after_confirm_classification(
    state: dict,
) -> Literal["collect_fields", "collect_description", "confirm_classification"]:
    cn = state.get("current_node", "")
    if cn == "confirmed":
        return "collect_fields"
    if cn == "retry_description":
        return "collect_description"
    # retry_classify
    return "confirm_classification"


def route_after_collect_fields(
    state: dict,
) -> Literal["collect_fields", "confirmation"]:
    if state.get("missing_fields"):
        return "collect_fields"
    return "confirmation"


def route_after_process_confirmation(
    state: dict,
) -> Literal["save", "edit", "__end__"]:
    cn = state.get("current_node", "")
    if cn == "save":
        return "save"
    if cn == "edit":
        return "edit"
    return "__end__"


def route_after_edit(
    state: dict,
) -> Literal["collect_fields", "edit"]:
    if state.get("current_node") == "edit_ok":
        return "collect_fields"
    return "edit"
