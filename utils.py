"""Utility functions."""
import logging
from datetime import datetime

from models import Message

logger = logging.getLogger(__name__)


def format_messages_for_summary(messages: list[Message]) -> str:
    """Format messages into a text suitable for LLM processing."""
    formatted_lines = []

    for msg in messages:
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        sender = msg.sender_name or msg.sender_jid.split("@")[0]
        content = msg.content

        formatted_lines.append(f"[{timestamp}] {sender}: {content}")

    return "\n".join(formatted_lines)


def format_phone_number(phone: str) -> str:
    """Format phone number for WhatsApp (ensure it starts with +)."""
    if not phone.startswith("+"):
        phone = f"+{phone}"
    # Remove any spaces or dashes
    phone = phone.replace(" ", "").replace("-", "")
    return phone
