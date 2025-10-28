"""Main application entry point."""
import asyncio
import logging
import os
import signal
import sys

import structlog

from commands import CommandHandler
from config import settings
from database import close_db, init_db
from green_api_client import GreenAPIClient
from message_handler import MessageHandler
from scheduler import SummaryScheduler
from summarizer import SummaryGenerator

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.log_level),
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


class Application:
    """Main application orchestrator."""

    def __init__(self):
        """Initialize application."""
        # Initialize core components
        self.message_handler = MessageHandler()
        self.green_api_client = GreenAPIClient(self.message_handler)
        self.summary_generator = SummaryGenerator(self.green_api_client)
        self.command_handler = CommandHandler(self.green_api_client, self.summary_generator)
        self.scheduler = SummaryScheduler(self.green_api_client)
        self._shutdown_event = asyncio.Event()

    async def _heartbeat(self):
        """Heartbeat task to verify event loop is processing coroutines."""
        while not self._shutdown_event.is_set():
            logger.info("💓 EVENT LOOP HEARTBEAT - loop is actively processing tasks")
            await asyncio.sleep(5)

    async def start(self):
        """Start the application."""
        logger.info("=" * 80)
        logger.info("🚀 Starting WhatsApp Groups Monitor...")
        logger.info("=" * 80)

        try:
            # Initialize database
            logger.info("1️⃣ Initializing database...")
            await init_db()
            logger.info("✅ Database initialized")

            # Start message handler
            logger.info("2️⃣ Starting message handler...")
            await self.message_handler.start()
            logger.info("✅ Message handler started")

            # Register command handler with message handler
            logger.info("3️⃣ Registering command handler...")
            self.message_handler.set_command_handler(self.command_handler)
            logger.info("✅ Command handler registered")

            # Start Green API notification receiver
            logger.info("4️⃣ Starting Green API notification receiver...")
            await self.green_api_client.start_receiving()
            logger.info("✅ Green API receiver started - listening for messages")

            # Start scheduler
            logger.info("5️⃣ Starting scheduler...")
            self.scheduler.start()
            logger.info("✅ Scheduler started")

            # Start heartbeat task to verify event loop is processing
            logger.info("6️⃣ Starting event loop heartbeat...")
            asyncio.create_task(self._heartbeat())
            logger.info("✅ Heartbeat started")

            logger.info("=" * 80)
            logger.info("✅ WhatsApp Groups Monitor is running!")
            logger.info("=" * 80)
            logger.info(
                f"📅 Daily summaries scheduled at {settings.summary_schedule_hour:02d}:00 "
                f"{settings.summary_schedule_timezone}"
            )
            logger.info(f"📱 Summary recipient: {settings.summary_recipient_phone}")
            logger.info(f"🤖 On-demand summaries: Send 'sikum' to the bot from {settings.summary_recipient_phone}")
            logger.info(f"🟢 Green API Instance: {settings.green_api_instance_id}")
            logger.info("=" * 80)

            # Wait for shutdown signal
            await self._shutdown_event.wait()

        except Exception as e:
            logger.error(f"❌ Error during startup: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the application."""
        logger.info("Shutting down WhatsApp Groups Monitor...")

        # Stop scheduler
        self.scheduler.stop()

        # Stop Green API client
        self.green_api_client.stop()

        # Stop message handler
        await self.message_handler.stop()

        # Close database connections
        await close_db()

        logger.info("WhatsApp Groups Monitor stopped")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()


async def main():
    """Main entry point."""
    app = Application()

    # Register signal handlers
    signal.signal(signal.SIGINT, lambda s, f: app.signal_handler(s, f))
    signal.signal(signal.SIGTERM, lambda s, f: app.signal_handler(s, f))

    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
