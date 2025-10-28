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
        # Capture the running event loop to schedule work from webhook thread
        import asyncio
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

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
            # For quicker diagnostics, log concise highlights at INFO and full body at DEBUG
            try:
                highlights = {
                    "type": type_webhook,
                    "idMessage": body.get("idMessage"),
                    "timestamp": body.get("timestamp"),
                    "sender": (body.get("senderData") or {}).get("sender"),
                    "chatId": (body.get("senderData") or {}).get("chatId"),
                    "stateInstance": (body.get("stateInstanceData") or {}).get("stateInstance"),
                }
                logger.info(f"🔎 Notification highlights: {highlights}")
            except Exception:
                # noop – best-effort highlights only
                pass
            logger.debug(f"Notification body: {body}")

            # Route processing based on type
            if type_webhook == "incomingMessageReceived":
                self._handle_incoming_message(body)
            elif type_webhook in {"outgoingMessageReceived", "outgoingAPIMessageReceived"}:
                logger.debug("Ignoring outgoing message notification")
            elif type_webhook == "stateInstanceChanged":
                state = (body.get("stateInstanceData") or {}).get("stateInstance")
                logger.info(f"🟢 Instance state changed: {state}")
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

            # Determine if this is a group chat
            chat_id = sender_data.get("chatId", "")
            is_group = chat_id.endswith("@g.us")

            # Prefer extended/text payloads
            text = (
                (message_data.get("textMessageData") or {}).get("textMessage")
                or (message_data.get("extendedTextMessageData") or {}).get("text")
                or ""
            )

            # Convert to format expected by message_handler
            formatted_data = {
                "info": {
                    "id": {"id": body.get("idMessage", "")},
                    "messageSource": {
                        "senderJID": sender_data.get("sender", ""),
                        "groupJID": chat_id if is_group else "",
                    },
                    "timestamp": body.get("timestamp", 0),
                    "pushName": sender_data.get("senderName", ""),
                },
                "message": {
                    "conversation": text,
                    "extendedTextMessage": message_data.get("extendedTextMessageData", {}),
                    "imageMessage": message_data.get("imageMessageData", {}),
                    "videoMessage": message_data.get("videoMessageData", {}),
                    "documentMessage": message_data.get("documentMessageData", {}),
                },
            }

            # Log parsed message
            sender_jid = formatted_data["info"]["messageSource"]["senderJID"]
            group_jid = formatted_data["info"]["messageSource"]["groupJID"]
            content_preview = (formatted_data["message"]["conversation"] or "").strip()

            if group_jid:
                logger.info(f"✅ Parsed GROUP message from {sender_jid} in {group_jid}: '{content_preview[:120]}'")
            else:
                logger.info(f"✅ Parsed DIRECT message from {sender_jid}: '{content_preview[:120]}'")

            if not formatted_data["info"]["id"]["id"]:
                logger.warning("⚠️ Message without idMessage; skipping")
                return

            # Process message through existing handler on the main asyncio loop
            import asyncio
            logger.info("🔧 Preparing to schedule message processing on asyncio loop...")

            if self._loop is None:
                logger.warning("⚠️ Loop is None, attempting to get running loop...")
                try:
                    self._loop = asyncio.get_running_loop()
                    logger.info(f"✅ Got running loop: {self._loop}")
                except RuntimeError as e:
                    logger.error(f"❌ Failed to get running loop: {e}")
                    self._loop = None

            if self._loop is not None:
                logger.info(f"🚀 Scheduling process_message on loop: {self._loop}")
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.message_handler.process_message(formatted_data), self._loop
                    )
                    logger.info(f"✅ Coroutine scheduled, future: {future}")

                    # Add callback to log any exceptions
                    def check_result(f):
                        logger.info("🎯 Future callback triggered")
                        try:
                            result = f.result()
                            logger.info(f"✅ Message processing completed successfully: {result}")
                        except Exception as e:
                            logger.error(f"❌ Exception in process_message coroutine: {e}", exc_info=True)

                    future.add_done_callback(check_result)
                    logger.info("✅ Callback registered to future")
                except Exception as e:
                    logger.error(f"❌ Error scheduling coroutine: {e}", exc_info=True)
            else:
                logger.warning("⚠️ No asyncio loop captured; message will not be processed")

        except Exception as e:
            logger.error(f"Error processing incoming message: {e}", exc_info=True)

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

    def stop(self):
        """Stop receiving notifications."""
        try:
            # Green API library may not have explicit stop method
            # Just log that we're stopping
            logger.info("Stopping Green API client...")
        except Exception as e:
            logger.error(f"Error stopping Green API client: {e}")
