"""Main application entry point."""
import asyncio
import logging
import signal
import sys

import structlog

from commands import CommandHandler
from config import settings
from database import close_db, init_db
from message_handler import MessageHandler, sync_existing_groups
from scheduler import SummaryScheduler
from summarizer import SummaryGenerator
from webhook import WebhookServer
from whatsapp import WhatsAppClient

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
        self.whatsapp_client = WhatsAppClient()
        self.message_handler = MessageHandler(self.whatsapp_client)
        self.summary_generator = SummaryGenerator(self.whatsapp_client)
        self.command_handler = CommandHandler(self.whatsapp_client, self.summary_generator)
        self.scheduler = SummaryScheduler(self.whatsapp_client)
        self.webhook_server = WebhookServer(self.message_handler)
        self._shutdown_event = asyncio.Event()

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

            # Sync existing groups
            logger.info("4️⃣ Syncing existing WhatsApp groups...")
            await sync_existing_groups(self.whatsapp_client)
            logger.info("✅ Groups synced")

            # Start webhook server
            logger.info("5️⃣ Starting webhook server on port 8000...")
            await self.webhook_server.start()
            logger.info("✅ Webhook server started - listening for messages at POST /webhook/message")

            # Start scheduler
            logger.info("6️⃣ Starting scheduler...")
            self.scheduler.start()
            logger.info("✅ Scheduler started")

            logger.info("=" * 80)
            logger.info("✅ WhatsApp Groups Monitor is running!")
            logger.info("=" * 80)
            logger.info(
                f"📅 Daily summaries scheduled at {settings.summary_schedule_hour:02d}:00 "
                f"{settings.summary_schedule_timezone}"
            )
            logger.info(f"📱 Summary recipient: {settings.summary_recipient_phone}")
            logger.info(f"🤖 On-demand summaries: Send 'sikum' to the bot from {settings.summary_recipient_phone}")
            logger.info(f"🌐 Webhook endpoint: http://0.0.0.0:8000/webhook/message")
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

        # Stop webhook server
        await self.webhook_server.stop()

        # Stop message handler
        await self.message_handler.stop()

        # Close WhatsApp client
        await self.whatsapp_client.close()

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
