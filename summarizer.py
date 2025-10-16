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
from whatsapp import SendMessageRequest, WhatsAppClient

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.google_api_key)


class SummaryGenerator:
    """Generate summaries using Gemini LLM."""

    def __init__(self, whatsapp_client: WhatsAppClient):
        """Initialize summary generator."""
        self.whatsapp = whatsapp_client
        self.model = genai.GenerativeModel(settings.gemini_llm_model)
        logger.info(f"Initialized summary generator with model: {settings.gemini_llm_model}")

    @retry(
        wait=wait_random_exponential(min=settings.retry_min_wait, max=settings.retry_max_wait),
        stop=stop_after_attempt(settings.max_retry_attempts),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def generate_summary(self, group_name: str, messages_text: str) -> str:
        """Generate summary for a group's messages."""
        system_prompt = f"""
Write a quick summary of what happened in the chat group since the last summary.

- Start by stating this is a quick summary of what happened in "{group_name}" group recently.
- Use a casual conversational writing style.
- Keep it short and sweet.
- Write in the same language as the chat group. You MUST use the same language as the chat group!
- Please do tag users while talking about them (e.g., @972536150150).
- Focus on the main topics, decisions, and important information shared.
- If there are questions asked, mention if they were answered.
- Highlight any action items or important dates mentioned.

ONLY answer with the summary, no other text.
"""

        try:
            response = await self.model.generate_content_async(
                f"{system_prompt}\n\nChat Messages:\n{messages_text}"
            )
            summary = response.text.strip()
            logger.info(f"Generated summary for {group_name}")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary for {group_name}: {e}")
            raise

    async def summarize_group(self, session: AsyncSession, group: Group) -> bool:
        """Summarize a single group and return success status."""
        try:
            # Get my JID to exclude own messages
            my_jid = await self.whatsapp.get_my_jid()

            # Get messages since last summary
            messages = await group.get_messages_since_last_summary(session, exclude_sender_jid=my_jid)

            # Check if we have enough messages
            if len(messages) < settings.minimum_messages_for_summary:
                logger.info(
                    f"Not enough messages to summarize in group {group.group_name} "
                    f"({len(messages)} < {settings.minimum_messages_for_summary})"
                )
                return False

            # Limit messages if too many
            if len(messages) > settings.max_messages_per_summary:
                logger.warning(
                    f"Too many messages in {group.group_name}, "
                    f"limiting to {settings.max_messages_per_summary}"
                )
                messages = messages[-settings.max_messages_per_summary :]

            # Format messages for LLM
            messages_text = format_messages_for_summary(messages)

            # Generate summary
            start_time = messages[0].timestamp
            end_time = messages[-1].timestamp

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

    async def generate_and_send_daily_summaries(self):
        """Generate summaries for all managed groups and send consolidated summary."""
        logger.info("Starting daily summary generation...")

        async with get_session() as session:
            # Get all managed groups
            result = await session.exec(select(Group).where(Group.managed == True))  # noqa: E712
            groups = list(result.all())

            if not groups:
                logger.warning("No managed groups found")
                return

            logger.info(f"Processing {len(groups)} groups...")

            # Generate summaries for each group
            summaries_data = []
            for group in groups:
                success = await self.summarize_group(session, group)

                if success:
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

            if not summaries_data:
                logger.info("No summaries generated (all groups below minimum threshold)")
                return

            # Create consolidated summary message
            consolidated_summary = self._format_consolidated_summary(summaries_data)

            # Send to recipient
            try:
                recipient_phone = format_phone_number(settings.summary_recipient_phone)
                await self.whatsapp.send_message(
                    SendMessageRequest(phone=recipient_phone, message=consolidated_summary)
                )

                logger.info(f"Sent daily summary to {recipient_phone}")

                # Mark all summaries as sent
                for summary_data in summaries_data:
                    summary_result = await session.exec(
                        select(SummaryLog).where(SummaryLog.id == summary_data["summary_log_id"])
                    )
                    summary_log = summary_result.first()
                    if summary_log:
                        summary_log.sent_successfully = True
                        session.add(summary_log)

                # Update last_summary_sync for all groups
                for group in groups:
                    group.last_summary_sync = datetime.now()
                    session.add(group)

                await session.commit()

            except Exception as e:
                logger.error(f"Failed to send daily summary: {e}", exc_info=True)

        logger.info("Daily summary generation completed")

    def _format_consolidated_summary(self, summaries_data: list[dict]) -> str:
        """Format consolidated summary message."""
        today = datetime.now().strftime("%Y-%m-%d")
        header = f"📱 Daily WhatsApp Groups Summary - {today}\n"
        header += "=" * 50 + "\n\n"

        body_parts = []
        for data in summaries_data:
            group_section = f"📌 *{data['group_name']}* ({data['message_count']} messages)\n"
            group_section += f"{data['summary']}\n"
            body_parts.append(group_section)

        footer = "\n" + "=" * 50 + "\n"
        footer += "Generated by WhatsApp Groups Monitor"

        return header + "\n\n".join(body_parts) + footer
