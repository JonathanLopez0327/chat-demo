"""LangGraph conversation state definition."""
from __future__ import annotations

from typing import Annotated, Any, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ConversationState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    # User identification
    user_phone: str
    user_profile: Optional[dict]  # serialized UserProfile
    # Incident being built
    current_incident: dict  # partial IncidentRecord fields
    # Classification
    classification_candidates: list[dict]  # top 3 from LLM
    selected_code: Optional[str]
    # Field collection
    missing_fields: list[str]
    current_field: Optional[str]
    # Flow control
    confirmed: Optional[bool]
    current_node: str
    error: Optional[str]
    # User description of the incident
    user_description: str
    # Multimedia attachments accumulated during conversation
    media_attachments: list[dict]  # [{bytes, filename, type, description}]
