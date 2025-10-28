"""Green API WhatsApp client for sending messages."""
import logging
from typing import Any

from whatsapp_api_client_python import API

from config import settings

logger = logging.getLogger(__name__)


class GreenAPIClient:
    """Client for Green API WhatsApp service."""

    def __init__(self, message_handler=None):
        """Initialize Green API client."""
        self.message_handler = message_handler
        self.api = API.GreenAPI(
            settings.green_api_instance_id,
            settings.green_api_token
        )
        logger.info(f"Green API client initialized for instance: {settings.green_api_instance_id}")

    def send_message(self, phone: str, message: str) -> dict[str, Any]:
        """
        Send a message via Green API.

        Args:
            phone: Phone number (e.g., "972542607800" or "972542607800@c.us")
            message: Message text to send

        Returns:
            Response from Green API
        """
        try:
            # Clean phone number format (remove @ suffix if present)
            chat_id = phone.split("@")[0] if "@" in phone else phone

            # Ensure phone number has @c.us suffix for Green API
            if not chat_id.endswith("@c.us") and not chat_id.endswith("@g.us"):
                chat_id = f"{chat_id}@c.us"

            logger.info(f"📤 Sending message to {chat_id}")

            response = self.api.sending.sendMessage(chat_id, message)

            logger.info(f"✅ Message sent successfully to {chat_id}")
            return response

        except Exception as e:
            logger.error(f"❌ Failed to send message to {phone}: {e}")
            raise
