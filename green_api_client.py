"""Green API WhatsApp client integration."""
import logging
from typing import Any

from whatsapp_api_client_python import API

from config import settings
from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class GreenAPIClient:
    """Client for Green API WhatsApp service."""

    def __init__(self, message_handler: MessageHandler):
        """Initialize Green API client."""
        self.message_handler = message_handler
        self.api = API.GreenAPI(
            settings.green_api_instance_id,
            settings.green_api_token
        )
        logger.info(f"Green API client initialized for instance: {settings.green_api_instance_id}")

    async def start_receiving(self):
        """Start receiving incoming notifications from Green API."""
        logger.info("Starting to receive notifications from Green API...")

        # Start receiving notifications with callback
        self.api.webhooks.startReceivingNotifications(self._on_notification)

        logger.info("✅ Green API notification receiver started")

    def _on_notification(self, type_webhook: str, body: dict[str, Any]):
        """
        Handle incoming notification from Green API.

        Args:
            type_webhook: Type of notification (e.g., "incomingMessageReceived")
            body: Notification body with message data
        """
        try:
            logger.info(f"📩 GREEN API NOTIFICATION - Type: {type_webhook}")
            logger.debug(f"Notification body: {body}")

            # Handle incoming messages
            if type_webhook == "incomingMessageReceived":
                self._handle_incoming_message(body)
            else:
                logger.debug(f"Ignoring notification type: {type_webhook}")

        except Exception as e:
            logger.error(f"Error handling notification: {e}", exc_info=True)

    def _handle_incoming_message(self, body: dict[str, Any]):
        """
        Process incoming message notification.

        Args:
            body: Message notification body from Green API
        """
        try:
            # Extract message data from Green API format
            message_data = body.get("messageData", {})
            sender_data = body.get("senderData", {})

            # Convert to format expected by message_handler
            formatted_data = {
                "info": {
                    "id": {
                        "id": body.get("idMessage", "")
                    },
                    "messageSource": {
                        "senderJID": sender_data.get("sender", ""),
                        "groupJID": sender_data.get("chatId", "") if "@g.us" in sender_data.get("chatId", "") else ""
                    },
                    "timestamp": body.get("timestamp", 0),
                    "pushName": sender_data.get("senderName", "")
                },
                "message": {
                    "conversation": message_data.get("textMessageData", {}).get("textMessage", ""),
                    "extendedTextMessage": message_data.get("extendedTextMessageData", {}),
                    "imageMessage": message_data.get("imageMessageData", {}),
                    "videoMessage": message_data.get("videoMessageData", {}),
                    "documentMessage": message_data.get("documentMessageData", {})
                }
            }

            # Log parsed message
            sender_jid = formatted_data["info"]["messageSource"]["senderJID"]
            group_jid = formatted_data["info"]["messageSource"]["groupJID"]
            content = formatted_data["message"]["conversation"]

            if group_jid:
                logger.info(f"✅ Parsed GROUP message from {sender_jid} in {group_jid}: '{content[:100]}'")
            else:
                logger.info(f"✅ Parsed DIRECT message from {sender_jid}: '{content[:100]}'")

            # Process message through existing handler
            import asyncio
            asyncio.create_task(self.message_handler.process_message(formatted_data))

        except Exception as e:
            logger.error(f"Error processing incoming message: {e}", exc_info=True)

    async def send_message(self, phone: str, message: str) -> dict[str, Any]:
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

    def stop(self):
        """Stop receiving notifications."""
        try:
            # Green API library may not have explicit stop method
            # Just log that we're stopping
            logger.info("Stopping Green API client...")
        except Exception as e:
            logger.error(f"Error stopping Green API client: {e}")
