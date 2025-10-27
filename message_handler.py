"""Message collection and processing pipeline."""
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Group, Message
from whatsapp import WhatsAppClient, WhatsAppMessage, normalize_jid

if TYPE_CHECKING:
    from commands import CommandHandler

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handle incoming WhatsApp messages."""

    def __init__(self, whatsapp_client: WhatsAppClient):
        """Initialize message handler."""
        self.whatsapp = whatsapp_client
        self._my_jid: str | None = None
        self._command_handler: "CommandHandler | None" = None

    def set_command_handler(self, command_handler: "CommandHandler"):
        """Set the command handler for processing bot commands."""
        self._command_handler = command_handler
        logger.info("Command handler registered with message handler")

    async def start(self):
        """Start the message handler."""
        self._my_jid = await self.whatsapp.get_my_jid()
        logger.info("Message handler started")

    async def stop(self):
        """Stop the message handler."""
        logger.info("Message handler stopped")

    async def process_message(self, message_data: dict):
        """Process incoming WhatsApp message."""
        try:
            logger.debug("🔄 Processing message data...")

            # Parse message data
            wa_message = self._parse_message_data(message_data)
            if not wa_message:
                logger.warning("⚠️ Message parsing returned None, skipping")
                return

            # Log parsed message details
            if wa_message.group_jid:
                logger.info(
                    f"✅ Parsed GROUP message: "
                    f"sender={wa_message.sender_jid}, "
                    f"group={wa_message.group_jid}, "
                    f"content='{wa_message.content[:100]}'"
                )
            else:
                logger.info(
                    f"✅ Parsed DIRECT message: "
                    f"sender={wa_message.sender_jid}, "
                    f"content='{wa_message.content[:100]}'"
                )

            # Skip messages from self
            if wa_message.sender_jid == self._my_jid:
                logger.debug(f"⏭️ Skipping message from self (my_jid={self._my_jid})")
                return

            # Check if message is a command (only for direct messages, not group messages)
            if not wa_message.group_jid and self._command_handler:
                logger.info(
                    f"🤖 Checking if direct message is a command: '{wa_message.content}' "
                    f"from {wa_message.sender_jid}"
                )
                is_command = await self._command_handler.process_command(
                    wa_message.sender_jid, wa_message.content
                )
                if is_command:
                    logger.info(f"✅ Command processed successfully from {wa_message.sender_jid}")
                    return  # Don't save command messages
                else:
                    logger.debug(f"ℹ️ Not a command, treating as regular direct message")

            # Save message to database (only group messages or non-command DMs)
            if wa_message.group_jid:
                logger.debug(f"💾 Saving group message to database...")
                async with get_session() as session:
                    await self._save_message(session, wa_message)
            else:
                logger.debug("ℹ️ Direct message (non-command) - not saving to database")

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)

    def _parse_message_data(self, data: dict) -> WhatsAppMessage | None:
        """Parse raw message data into WhatsAppMessage."""
        try:
            # Adapt this based on the actual API response format
            info = data.get("info", {})
            message = data.get("message", {})

            # Extract message ID
            message_id = info.get("id", {}).get("id", "")
            if not message_id:
                logger.warning("Message without ID received")
                return None

            # Extract group JID (may be empty for direct messages)
            group_jid = info.get("messageSource", {}).get("groupJID", "")

            # Extract sender info
            sender_jid = info.get("messageSource", {}).get("senderJID", "")
            sender_name = info.get("pushName", "")

            # Extract message content
            content = ""
            message_type = "text"

            if "conversation" in message:
                content = message["conversation"]
            elif "extendedTextMessage" in message:
                content = message["extendedTextMessage"].get("text", "")
            elif "imageMessage" in message:
                content = message["imageMessage"].get("caption", "[Image]")
                message_type = "image"
            elif "videoMessage" in message:
                content = message["videoMessage"].get("caption", "[Video]")
                message_type = "video"
            elif "documentMessage" in message:
                content = "[Document]"
                message_type = "document"

            if not content:
                logger.debug("Message without text content")
                return None

            # Get timestamp
            timestamp = info.get("timestamp", int(datetime.now().timestamp()))

            return WhatsAppMessage(
                message_id=message_id,
                group_jid=normalize_jid(group_jid) if group_jid else "",
                sender_jid=normalize_jid(sender_jid),
                sender_name=sender_name,
                content=content,
                message_type=message_type,
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Error parsing message data: {e}")
            return None

    async def _save_message(self, session: AsyncSession, wa_message: WhatsAppMessage):
        """Save message to database."""
        # Check if message already exists
        result = await session.exec(
            select(Message).where(Message.message_id == wa_message.message_id)
        )
        existing_message = result.first()

        if existing_message:
            logger.debug(f"Message {wa_message.message_id} already exists")
            return

        # Ensure group exists
        await self._ensure_group_exists(session, wa_message.group_jid, wa_message.group_name)

        # Create message record
        message = Message(
            message_id=wa_message.message_id,
            group_jid=wa_message.group_jid,
            sender_jid=wa_message.sender_jid,
            sender_name=wa_message.sender_name,
            content=wa_message.content,
            message_type=wa_message.message_type,
            timestamp=datetime.fromtimestamp(wa_message.timestamp),
        )

        session.add(message)
        await session.commit()
        await session.refresh(message)

        logger.info(
            f"Saved message {message.message_id} from {message.sender_name} in group {message.group_jid}"
        )

    async def _ensure_group_exists(
        self, session: AsyncSession, group_jid: str, group_name: str | None
    ):
        """Ensure group exists in database."""
        result = await session.exec(select(Group).where(Group.group_jid == group_jid))
        group = result.first()

        if not group:
            group = Group(
                group_jid=group_jid,
                group_name=group_name,
                managed=True,
            )
            session.add(group)
            await session.commit()
            logger.info(f"Created new group record: {group_name} ({group_jid})")


async def sync_existing_groups(whatsapp_client: WhatsAppClient):
    """Sync existing WhatsApp groups to database."""
    logger.info("Syncing existing groups...")

    try:
        groups = await whatsapp_client.get_groups()

        async with get_session() as session:
            for group_data in groups:
                group_jid = group_data.get("jid", "")
                group_name = group_data.get("name", "")

                if not group_jid:
                    continue

                group_jid = normalize_jid(group_jid)

                # Check if group exists
                result = await session.exec(select(Group).where(Group.group_jid == group_jid))
                existing_group = result.first()

                if not existing_group:
                    new_group = Group(
                        group_jid=group_jid,
                        group_name=group_name,
                        managed=True,
                    )
                    session.add(new_group)
                    logger.info(f"Added new group: {group_name} ({group_jid})")
                else:
                    # Update group name if changed
                    if existing_group.group_name != group_name:
                        existing_group.group_name = group_name
                        session.add(existing_group)
                        logger.info(f"Updated group name: {group_name} ({group_jid})")

            await session.commit()

        logger.info(f"Synced {len(groups)} groups")

    except Exception as e:
        logger.error(f"Error syncing groups: {e}", exc_info=True)
