"""Summary generation using Google Gemini."""
import logging
from datetime import datetime

import google.generativeai as genai
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

from config import settings
from database import get_session
from models import Group, SummaryLog
from utils import format_messages_for_summary, format_phone_number

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.google_api_key)


class SummaryGenerator:
    """Generate summaries using Gemini LLM."""

    def __init__(self, green_api_client):
        """Initialize summary generator."""
        self.green_api_client = green_api_client
        self.model = genai.GenerativeModel(settings.gemini_llm_model)
        logger.info(f"Initialized summary generator with model: {settings.gemini_llm_model}")

    @retry(
        wait=wait_random_exponential(min=1, max=30),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate_summary(self, group_name: str, messages_text: str) -> str:
        """Generate summary for a group's messages."""
        logger.info(f"🤖 AI GENERATION - Starting for group '{group_name}'")
        logger.debug(f"🤖 Messages text length: {len(messages_text)} characters")

        system_prompt = f"""
Write a quick summary of what happened in the chat group since the last summary.

- Start by stating this is a quick summary of what happened in "{group_name}" group recently.
- Use a casual conversational writing style.
- Keep it short and sweet.
- Write in the same language as the chat group. You MUST use the same language as the chat group!
- When mentioning users, use their names as they appear in the chat (not phone numbers).
- Focus on the main topics, decisions, and important information shared.
- If there are questions asked, mention if they were answered.
- Highlight any action items or important dates mentioned.

ONLY answer with the summary, no other text.
"""

        try:
            logger.debug(f"🤖 Calling Gemini API for group '{group_name}'...")
            response = await self.model.generate_content_async(
                f"{system_prompt}\n\nChat Messages:\n{messages_text}"
            )
            summary = response.text.strip()
            logger.info(f"✅ AI GENERATION SUCCESS - Generated {len(summary)} chars for '{group_name}'")
            logger.debug(f"Summary preview: {summary[:200]}...")
            return summary

        except Exception as e:
            logger.error(f"❌ AI GENERATION FAILED for {group_name}: {e}")
            raise

    async def summarize_group(self, session: AsyncSession, group: Group, *, force: bool = False) -> bool:
        """Summarize a single group and return success status."""
        try:
            logger.debug(f"📊 Summarizing group: {group.group_name}")

            # For Green API, we don't have a direct way to get our JID
            # We'll exclude messages based on a pattern or skip this for now
            if force:
                # When force=True (sikum command), get ALL messages from today (00:00 to now)
                logger.debug(f"🔍 Fetching all messages from today for {group.group_name}...")
                messages = await group.get_messages_today(session, exclude_sender_jid=None)
            else:
                # For scheduled summaries, only get messages since last summary
                logger.debug(f"🔍 Fetching messages since last summary for {group.group_name}...")
                messages = await group.get_messages_since_last_summary(session, exclude_sender_jid=None)

            # Check if we have any messages
            if len(messages) == 0:
                if force:
                    logger.info(f"ℹ️ Force mode: zero messages in {group.group_name}, skipping but not failing")
                    return False
                logger.info(f"ℹ️ No messages to summarize in group {group.group_name}")
                return False

            logger.info(f"📬 Found {len(messages)} messages in {group.group_name}")

            # Limit messages if too many
            if len(messages) > settings.max_messages_per_summary:
                logger.warning(
                    f"⚠️ Too many messages in {group.group_name} ({len(messages)}), "
                    f"limiting to {settings.max_messages_per_summary}"
                )
                messages = messages[-settings.max_messages_per_summary :]

            # Format messages for LLM
            logger.debug(f"📝 Formatting {len(messages)} messages for AI...")
            messages_text = format_messages_for_summary(messages)

            # Generate summary
            start_time = messages[0].timestamp
            end_time = messages[-1].timestamp
            logger.debug(f"⏰ Message time range: {start_time} to {end_time}")

            try:
                summary = await self.generate_summary(group.group_name or "group", messages_text)

                # Save summary log
                summary_log = SummaryLog(
                    group_jid=group.group_jid,
                    summary_text=summary,
                    message_count=len(messages),
                    start_time=start_time,
                    end_time=end_time,
                    sent_successfully=False,
                )
                session.add(summary_log)
                await session.commit()

                logger.info(
                    f"Generated summary for {group.group_name} "
                    f"({len(messages)} messages from {start_time} to {end_time})"
                )

                return True

            except Exception as e:
                logger.error(f"Error generating summary for {group.group_name}: {e}")
                # Save failed summary log
                summary_log = SummaryLog(
                    group_jid=group.group_jid,
                    summary_text="",
                    message_count=len(messages),
                    start_time=start_time,
                    end_time=end_time,
                    sent_successfully=False,
                    error_message=str(e),
                )
                session.add(summary_log)
                await session.commit()
                return False

        except Exception as e:
            logger.error(f"Error in summarize_group for {group.group_name}: {e}", exc_info=True)
            return False

    async def generate_and_send_daily_summaries(self, force: bool = False) -> bool:
        """Generate summaries for all managed groups and send consolidated summary.

        Args:
            force: When True, bypass minimum message threshold and attempt summaries anyway.

        Returns:
            bool: True if summaries were generated and sent, False otherwise.
        """
        logger.info("=" * 80)
        logger.info("📊 DAILY SUMMARY GENERATION STARTED")
        logger.info("=" * 80)

        async with get_session() as session:
            # Get all managed groups
            logger.debug("🔍 Fetching managed groups from database...")
            result = await session.exec(select(Group).where(Group.managed == True))  # noqa: E712
            groups = list(result.all())

            if not groups:
                logger.warning("⚠️ No managed groups found in database")
                return False

            logger.info(f"📋 Found {len(groups)} managed groups to process:")
            for idx, group in enumerate(groups, 1):
                logger.info(f"  {idx}. {group.group_name} ({group.group_jid})")

            # Generate summaries for each group
            summaries_data = []
            logger.info("")
            logger.info("🔄 Processing each group...")
            for idx, group in enumerate(groups, 1):
                logger.info(f"\n--- Group {idx}/{len(groups)}: {group.group_name} ---")
                success = await self.summarize_group(session, group, force=force)

                if success:
                    logger.debug(f"✅ Summary generated for {group.group_name}, fetching from database...")
                    # Get the latest summary for this group
                    summary_result = await session.exec(
                        select(SummaryLog)
                        .where(SummaryLog.group_jid == group.group_jid)
                        .order_by(SummaryLog.created_at.desc())
                        .limit(1)
                    )
                    summary_log = summary_result.first()

                    if summary_log and summary_log.summary_text:
                        summaries_data.append(
                            {
                                "group_name": group.group_name,
                                "summary": summary_log.summary_text,
                                "message_count": summary_log.message_count,
                                "summary_log_id": summary_log.id,
                            }
                        )
                        logger.info(f"✅ Added summary to send list ({summary_log.message_count} messages)")
                    else:
                        logger.warning(f"⚠️ Summary log not found or empty for {group.group_name}")
                else:
                    logger.info(f"⏭️ No summary generated for {group.group_name} (insufficient messages)")

            logger.info("")
            logger.info(f"📊 Summary generation complete: {len(summaries_data)}/{len(groups)} groups have summaries")

            if not summaries_data:
                if force:
                    logger.info("ℹ️ Force mode: no summaries produced; nothing to send")
                    return False
                logger.info("ℹ️ No summaries to send (all groups had insufficient messages)")
                return False

            # Create consolidated summary message
            logger.info("")
            logger.info("📝 Formatting consolidated summary...")
            consolidated_summary = self._format_consolidated_summary(summaries_data)
            logger.debug(f"📝 Consolidated summary length: {len(consolidated_summary)} characters")

            # Send to recipient
            try:
                recipient_phone = format_phone_number(settings.summary_recipient_phone)
                logger.info(f"📤 Sending consolidated summary to {recipient_phone}...")
                logger.info("📤 Sending consolidated summary message via Green API")
                self.green_api_client.send_message(
                    phone=recipient_phone, message=consolidated_summary
                )

                logger.info(f"✅ Successfully sent daily summary to {recipient_phone}")

                # Mark all summaries as sent
                logger.debug("💾 Marking summaries as sent in database...")
                for summary_data in summaries_data:
                    summary_result = await session.exec(
                        select(SummaryLog).where(SummaryLog.id == summary_data["summary_log_id"])
                    )
                    summary_log = summary_result.first()
                    if summary_log:
                        summary_log.sent_successfully = True
                        session.add(summary_log)

                # Update last_summary_sync for all groups
                logger.debug("💾 Updating last_summary_sync timestamps...")
                for group in groups:
                    group.last_summary_sync = datetime.now()
                    session.add(group)

                await session.commit()
                logger.info("✅ Database updated successfully")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to send daily summary: {e}", exc_info=True)
                return False

        logger.info("=" * 80)
        logger.info("📊 DAILY SUMMARY GENERATION COMPLETED")
        logger.info("=" * 80)
        return True

    def _format_consolidated_summary(self, summaries_data: list[dict]) -> str:
        """Format consolidated summary message."""
        today = datetime.now().strftime("%Y-%m-%d")
        header = f"📱 סיכום יומי של קבוצות ווטסאפ - {today}\n"
        header += "=" * 50 + "\n\n"

        body_parts = []
        for data in summaries_data:
            group_section = f"📌 *{data['group_name']}* ({data['message_count']} הודעות)\n"
            group_section += f"{data['summary']}\n"
            body_parts.append(group_section)

        footer = "\n" + "=" * 50 + "\n"
        footer += "נוצר על ידי WhatsApp Groups Monitor"

        return header + "\n\n".join(body_parts) + footer
