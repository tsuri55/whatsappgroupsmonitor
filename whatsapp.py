"""WhatsApp data models and utilities for Green API."""
from typing import Optional

from pydantic import BaseModel


class WhatsAppMessage(BaseModel):
    """WhatsApp message data model."""

    message_id: str
    group_jid: str
    group_name: Optional[str] = None
    sender_jid: str
    sender_name: Optional[str] = None
    content: str
    message_type: str = "text"
    timestamp: int  # Unix timestamp


def normalize_jid(jid: str) -> str:
    """
    Normalize WhatsApp JID format for Green API.

    Green API uses:
    - User JIDs: number@c.us (e.g., 972542607800@c.us)
    - Group JIDs: groupId@g.us (e.g., 120363407075043193@g.us)

    Handles input formats:
    - With suffix: 972542607800@c.us, 120363407075043193@g.us
    - Without suffix: 972542607800, +972542607800
    - Old format: 972542607800@s.whatsapp.net
    """
    if not jid:
        return ""

    # If already in correct format, return as-is
    if jid.endswith("@c.us") or jid.endswith("@g.us"):
        return jid

    # Extract number part (remove any suffix and + prefix)
    number = jid.split("@")[0].lstrip("+")

    # Group JIDs typically contain '-' and end with @g.us
    if "-" in number:
        return f"{number}@g.us"

    # User JIDs end with @c.us for Green API
    return f"{number}@c.us"
