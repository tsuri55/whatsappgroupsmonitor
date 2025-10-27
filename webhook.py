"""Webhook server for receiving WhatsApp messages."""
import logging

from aiohttp import web

from message_handler import MessageHandler

logger = logging.getLogger(__name__)


class WebhookServer:
    """Webhook server to receive WhatsApp messages."""

    def __init__(self, message_handler: MessageHandler, port: int = 8000):
        """Initialize webhook server."""
        self.message_handler = message_handler
        self.port = port
        self.app = web.Application()
        self.runner = None
        self._setup_routes()

    def _setup_routes(self):
        """Setup webhook routes."""
        self.app.router.add_post("/webhook/message", self._handle_message)
        self.app.router.add_get("/health", self._health_check)

    async def _handle_message(self, request: web.Request) -> web.Response:
        """Handle incoming message webhook."""
        try:
            data = await request.json()

            # Extract key info for logging
            info = data.get("info", {})
            message = data.get("message", {})
            sender_jid = info.get("messageSource", {}).get("senderJID", "unknown")
            group_jid = info.get("messageSource", {}).get("groupJID", "")

            # Get message text
            content = ""
            if "conversation" in message:
                content = message["conversation"]
            elif "extendedTextMessage" in message:
                content = message["extendedTextMessage"].get("text", "")

            # Log detailed webhook receipt
            if group_jid:
                logger.info(f"📩 WEBHOOK RECEIVED - Group message from {sender_jid} in {group_jid}: '{content[:100]}'")
            else:
                logger.info(f"📩 WEBHOOK RECEIVED - Direct message from {sender_jid}: '{content[:100]}'")

            logger.debug(f"Full webhook data: {data}")

            # Process message asynchronously (don't block webhook response)
            request.app.loop.create_task(self.message_handler.process_message(data))

            return web.json_response({"status": "ok"})

        except Exception as e:
            logger.error(f"❌ Error handling webhook: {e}", exc_info=True)
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy"})

    async def start(self):
        """Start the webhook server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await site.start()
        logger.info(f"Webhook server started on port {self.port}")

    async def stop(self):
        """Stop the webhook server."""
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook server stopped")
