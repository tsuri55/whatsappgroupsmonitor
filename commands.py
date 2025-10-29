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
            "stats": self._handle_stats_command,
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
        logger.info(f"🔍 Raw sender JID: {sender_jid}")
        logger.info(f"🔍 Normalized sender JID: {sender_jid_normalized}")
        logger.info(f"🔍 Authorized phone: {self.authorized_phone}")
        logger.info(f"🔍 JIDs match: {sender_jid_normalized == self.authorized_phone}")

        # Only process commands from authorized phone
        if sender_jid_normalized != self.authorized_phone:
            logger.warning(
                f"⛔ UNAUTHORIZED - Message from {sender_jid_normalized} (not {self.authorized_phone})"
            )
            return False

        logger.info(f"✅ AUTHORIZED USER - Checking for command keywords...")

        # Check if message is a command
        message_lower = message_text.strip().lower()
        logger.info(f"🔍 Message lowercase: '{message_lower}'")

        for command_keyword, handler in self.commands.items():
            logger.debug(f"🔍 Checking command keyword: '{command_keyword}'")
            if message_lower == command_keyword or message_lower.startswith(f"{command_keyword} "):
                logger.info(
                    f"🎯 COMMAND MATCHED - '{command_keyword}' from {sender_jid} - executing handler..."
                )
                await handler(sender_jid, message_text)
                logger.info(f"✅ COMMAND COMPLETED - '{command_keyword}'")
                return True

        logger.info(f"ℹ️ No command keyword matched in: '{message_lower}'")
        return False

    async def _handle_sikum_command(self, sender_jid: str, message_text: str):
        """Handle 'sikum' command - generate and send on-demand summary."""
        logger.info("📝 SIKUM COMMAND - Starting on-demand summary generation")

        try:
            # Send acknowledgment
            logger.info(f"📤 Sending acknowledgment to {sender_jid}")
            self.green_api_client.send_message(
                phone=sender_jid,
                message="⏳ מייצר סיכום לכל הקבוצות... זה עשוי לקחת רגע."
            )
            logger.info("✅ Acknowledgment sent")

            # Generate and send summaries
            logger.info("🤖 Starting AI summary generation for all groups...")
            success = await self.summary_generator.generate_and_send_daily_summaries(force=True)

            if not success:
                # No messages to summarize - send notification
                logger.info("📤 No messages found - sending notification to user")
                self.green_api_client.send_message(
                    phone=sender_jid,
                    message="ℹ️ אין הודעות חדשות לסכם היום בקבוצות."
                )

            logger.info("✅ On-demand summary completed successfully")

        except Exception as e:
            logger.error(f"❌ Error processing sikum command: {e}", exc_info=True)

            # Send error notification
            try:
                logger.info(f"📤 Sending error notification to {sender_jid}")
                self.green_api_client.send_message(
                    phone=sender_jid,
                    message=f"❌ שגיאה ביצירת הסיכום: {str(e)}"
                )
            except Exception as send_error:
                logger.error(f"❌ Failed to send error notification: {send_error}")

    async def _handle_stats_command(self, sender_jid: str, message_text: str):
        """Report basic DB stats: groups count and recent messages count."""
        logger.info("📊 STATS COMMAND - Gathering database statistics")
        try:
            from database import get_session
            from models import Group, Message
            from sqlmodel import select

            async with get_session() as session:
                groups_count = (await session.exec(select(Group))).all()
                messages_count = (await session.exec(select(Message))).all()

            text = (
                f"📊 Stats:\n"
                f"Groups: {len(groups_count)}\n"
                f"Messages: {len(messages_count)}\n"
            )
            self.green_api_client.send_message(phone=sender_jid, message=text)
            logger.info("✅ Stats sent")
        except Exception as e:
            logger.error(f"❌ Error generating stats: {e}")
            try:
                self.green_api_client.send_message(phone=sender_jid, message=f"❌ Stats error: {e}")
            except Exception:
                pass
