"""Command handler for interactive bot commands."""
import logging

from config import settings
from summarizer import SummaryGenerator
from whatsapp import WhatsAppClient, normalize_jid

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handle bot commands from users."""

    def __init__(self, whatsapp_client: WhatsAppClient, summary_generator: SummaryGenerator):
        """Initialize command handler."""
        self.whatsapp = whatsapp_client
        self.summary_generator = summary_generator
        self.authorized_phone = normalize_jid(settings.summary_recipient_phone)

        # Command keywords (case-insensitive)
        self.commands = {
            "sikum": self._handle_sikum_command,
            "/summarize": self._handle_sikum_command,
            "/summary": self._handle_sikum_command,
            "summary": self._handle_sikum_command,
            "summarize": self._handle_sikum_command,
        }

        logger.info(f"Command handler initialized. Authorized user: {self.authorized_phone}")

    async def process_command(self, sender_jid: str, message_text: str) -> bool:
        """
        Process incoming message for commands.

        Returns:
            bool: True if message was a command and was processed, False otherwise
        """
        # Normalize sender JID
        sender_jid_normalized = normalize_jid(sender_jid)

        # Only process commands from authorized phone
        if sender_jid_normalized != self.authorized_phone:
            logger.debug(f"Ignoring message from non-authorized user: {sender_jid}")
            return False

        # Check if message is a command
        message_lower = message_text.strip().lower()

        for command_keyword, handler in self.commands.items():
            if message_lower == command_keyword or message_lower.startswith(f"{command_keyword} "):
                logger.info(f"Processing command '{command_keyword}' from {sender_jid}")
                await handler(sender_jid, message_text)
                return True

        return False

    async def _handle_sikum_command(self, sender_jid: str, message_text: str):
        """Handle 'sikum' command - generate and send on-demand summary."""
        logger.info("Processing 'sikum' command - generating on-demand summary")

        try:
            # Send acknowledgment
            from whatsapp import SendMessageRequest
            await self.whatsapp.send_message(
                SendMessageRequest(
                    phone=sender_jid,
                    message="⏳ Generating summary for all groups... This may take a moment."
                )
            )

            # Generate and send summaries
            await self.summary_generator.generate_and_send_daily_summaries()

            logger.info("On-demand summary completed successfully")

        except Exception as e:
            logger.error(f"Error processing sikum command: {e}", exc_info=True)

            # Send error notification
            from whatsapp import SendMessageRequest
            try:
                await self.whatsapp.send_message(
                    SendMessageRequest(
                        phone=sender_jid,
                        message=f"❌ Error generating summary: {str(e)}"
                    )
                )
            except Exception as send_error:
                logger.error(f"Failed to send error notification: {send_error}")
