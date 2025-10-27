"""Command handler for interactive bot commands."""
import logging

from config import settings
from summarizer import SummaryGenerator
from whatsapp import normalize_jid

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handle bot commands from users."""

    def __init__(self, green_api_client, summary_generator: SummaryGenerator):
        """Initialize command handler."""
        self.green_api_client = green_api_client
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
        logger.info(f"🔍 COMMAND CHECK - Received message from {sender_jid}: '{message_text}'")

        # Normalize sender JID
        sender_jid_normalized = normalize_jid(sender_jid)
        logger.debug(f"🔍 Normalized sender JID: {sender_jid_normalized}")
        logger.debug(f"🔍 Authorized phone: {self.authorized_phone}")

        # Only process commands from authorized phone
        if sender_jid_normalized != self.authorized_phone:
            logger.warning(
                f"⛔ UNAUTHORIZED - Message from {sender_jid_normalized} (not {self.authorized_phone})"
            )
            return False

        logger.info(f"✅ AUTHORIZED USER - Checking for command keywords...")

        # Check if message is a command
        message_lower = message_text.strip().lower()
        logger.debug(f"🔍 Message lowercase: '{message_lower}'")

        for command_keyword, handler in self.commands.items():
            if message_lower == command_keyword or message_lower.startswith(f"{command_keyword} "):
                logger.info(
                    f"🎯 COMMAND MATCHED - '{command_keyword}' from {sender_jid} - executing handler..."
                )
                await handler(sender_jid, message_text)
                logger.info(f"✅ COMMAND COMPLETED - '{command_keyword}'")
                return True

        logger.debug(f"ℹ️ No command keyword matched in: '{message_lower}'")
        return False

    async def _handle_sikum_command(self, sender_jid: str, message_text: str):
        """Handle 'sikum' command - generate and send on-demand summary."""
        logger.info("📝 SIKUM COMMAND - Starting on-demand summary generation")

        try:
            # Send acknowledgment
            logger.info(f"📤 Sending acknowledgment to {sender_jid}")
            self.green_api_client.send_message(
                phone=sender_jid,
                message="⏳ Generating summary for all groups... This may take a moment."
            )
            logger.info("✅ Acknowledgment sent")

            # Generate and send summaries
            logger.info("🤖 Starting AI summary generation for all groups...")
            await self.summary_generator.generate_and_send_daily_summaries()

            logger.info("✅ On-demand summary completed successfully")

        except Exception as e:
            logger.error(f"❌ Error processing sikum command: {e}", exc_info=True)

            # Send error notification
            try:
                logger.info(f"📤 Sending error notification to {sender_jid}")
                self.green_api_client.send_message(
                    phone=sender_jid,
                    message=f"❌ Error generating summary: {str(e)}"
                )
            except Exception as send_error:
                logger.error(f"❌ Failed to send error notification: {send_error}")
