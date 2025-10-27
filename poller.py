"""Message polling service for go-whatsapp-web-multidevice API."""
import asyncio
import logging
from datetime import datetime

from message_handler import MessageHandler
from whatsapp import WhatsAppClient

logger = logging.getLogger(__name__)


class MessagePoller:
    """Poll for new messages from WhatsApp API."""

    def __init__(self, whatsapp_client: WhatsAppClient, message_handler: MessageHandler, interval: int = 5):
        """
        Initialize message poller.

        Args:
            whatsapp_client: WhatsApp API client
            message_handler: Message handler to process messages
            interval: Polling interval in seconds (default: 5)
        """
        self.whatsapp = whatsapp_client
        self.message_handler = message_handler
        self.interval = interval
        self._running = False
        self._task = None
        self._last_check = {}  # Track last check time per chat

    async def start(self):
        """Start the polling loop."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Message poller started (interval: {self.interval}s)")

    async def stop(self):
        """Stop the polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Message poller stopped")

    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                await self._check_messages()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)

            await asyncio.sleep(self.interval)

    async def _check_messages(self):
        """Check for new messages from all chats."""
        try:
            # Get list of chats (this is a placeholder - the API might not support this)
            # For now, we'll just log that we're checking
            logger.debug("Polling for new messages...")

            # TODO: Implement actual message fetching when API supports it
            # The go-whatsapp-web-multidevice API doesn't have a "get recent messages" endpoint
            # We need to use webhooks or find an alternative approach

        except Exception as e:
            logger.error(f"Error checking messages: {e}", exc_info=True)
