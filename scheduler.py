"""Scheduler for daily summaries."""
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from summarizer import SummaryGenerator
from whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)


class SummaryScheduler:
    """Scheduler for daily summary generation."""

    def __init__(self, whatsapp_client: WhatsAppClient):
        """Initialize scheduler."""
        self.whatsapp = whatsapp_client
        self.summary_generator = SummaryGenerator(whatsapp_client)
        self.scheduler = AsyncIOScheduler()
        self.timezone = pytz.timezone(settings.summary_schedule_timezone)

    def start(self):
        """Start the scheduler."""
        # Create cron trigger for daily summary at configured hour
        trigger = CronTrigger(
            hour=settings.summary_schedule_hour,
            minute=0,
            timezone=self.timezone,
        )

        # Add job to scheduler
        self.scheduler.add_job(
            self._run_daily_summary,
            trigger=trigger,
            id="daily_summary",
            name="Generate and send daily summaries",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler started. Daily summaries will be sent at "
            f"{settings.summary_schedule_hour:02d}:00 {settings.summary_schedule_timezone}"
        )

    async def _run_daily_summary(self):
        """Run daily summary generation task."""
        logger.info("Running scheduled daily summary task...")
        try:
            await self.summary_generator.generate_and_send_daily_summaries()
            logger.info("Daily summary task completed successfully")
        except Exception as e:
            logger.error(f"Error in daily summary task: {e}", exc_info=True)

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def run_summary_now(self):
        """Manually trigger summary generation (for testing)."""
        logger.info("Manually triggering summary generation...")
        await self._run_daily_summary()
