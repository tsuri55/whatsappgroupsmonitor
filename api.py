"""FastAPI application for Green API webhooks."""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from commands import CommandHandler
from config import settings
from database import close_db, init_db
from encryption import init_encryption
from green_api_client import GreenAPIClient
from message_handler import MessageHandler
from scheduler import SummaryScheduler
from summarizer import SummaryGenerator

# Configure logging to ensure all logs are visible
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True,  # Override any existing configuration
)

logger = logging.getLogger(__name__)

# Global instances
message_handler: MessageHandler = None
green_api_client: GreenAPIClient = None
command_handler: CommandHandler = None
scheduler: SummaryScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app."""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting WhatsApp Groups Monitor...")
    logger.info("=" * 80)

    global message_handler, green_api_client, command_handler, scheduler

    # Initialize encryption
    logger.info("1️⃣ Initializing encryption...")
    init_encryption(settings.encryption_key)
    logger.info("✅ Encryption initialized")

    # Initialize database
    logger.info("2️⃣ Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize components
    logger.info("3️⃣ Initializing components...")
    message_handler = MessageHandler()
    green_api_client = GreenAPIClient(message_handler)
    summary_generator = SummaryGenerator(green_api_client)
    command_handler = CommandHandler(green_api_client, summary_generator)
    message_handler.set_command_handler(command_handler)
    logger.info("✅ Components initialized")

    # Start message handler
    logger.info("4️⃣ Starting message handler...")
    await message_handler.start()
    logger.info("✅ Message handler started")

    # Start scheduler
    logger.info("5️⃣ Starting scheduler...")
    scheduler = SummaryScheduler(green_api_client)
    scheduler.start()
    logger.info("✅ Scheduler started")

    logger.info("=" * 80)
    logger.info("✅ WhatsApp Groups Monitor is running!")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("Shutting down WhatsApp Groups Monitor...")
    scheduler.stop()
    await message_handler.stop()
    await close_db()
    logger.info("WhatsApp Groups Monitor stopped")


# Create FastAPI app
app = FastAPI(
    title="WhatsApp Groups Monitor",
    description="Monitor WhatsApp groups and generate AI summaries",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"status": "ok", "message": "WhatsApp Groups Monitor is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret")
):
    """
    Webhook endpoint for Green API notifications.

    Green API will send notifications to this endpoint.
    Configure this URL in your Green API settings:
    https://console.green-api.com/instanceXXXX/webhooks

    Security:
    - Set WEBHOOK_SECRET environment variable to enable authentication
    - Send the secret in the X-Webhook-Secret header with each request
    """
    try:
        # Validate webhook secret if configured
        if settings.webhook_secret:
            if not x_webhook_secret:
                logger.warning("🚫 Webhook request rejected: Missing X-Webhook-Secret header")
                raise HTTPException(
                    status_code=401,
                    detail="Missing X-Webhook-Secret header"
                )
            if x_webhook_secret != settings.webhook_secret:
                logger.warning("🚫 Webhook request rejected: Invalid secret")
                raise HTTPException(
                    status_code=403,
                    detail="Invalid webhook secret"
                )

        # Parse incoming webhook data
        data = await request.json()

        # Log webhook receipt
        type_webhook = data.get("typeWebhook", "unknown")
        logger.info(f"📩 Webhook received: {type_webhook}")
        logger.debug(f"Webhook data: {data}")

        # Process based on webhook type
        if type_webhook == "incomingMessageReceived":
            # Extract message data
            message_data = data.get("messageData", {})
            sender_data = data.get("senderData", {})
            instance_data = data.get("instanceData", {})

            # Convert to format expected by message handler
            formatted_data = {
                "info": {
                    "id": {"id": data.get("idMessage", "")},
                    "messageSource": {
                        "senderJID": sender_data.get("sender", ""),
                        "groupJID": sender_data.get("chatId", "") if sender_data.get("chatId", "").endswith("@g.us") else "",
                        "groupName": sender_data.get("chatName", ""),  # Add group/chat name
                    },
                    "timestamp": data.get("timestamp", 0),
                    "pushName": sender_data.get("senderName", ""),
                },
                "message": {
                    "conversation": (message_data.get("textMessageData") or {}).get("textMessage", "") or
                                   (message_data.get("extendedTextMessageData") or {}).get("text", ""),
                },
            }

            # Process message
            await message_handler.process_message(formatted_data)

        elif type_webhook == "stateInstanceChanged":
            state = (data.get("stateInstanceData") or {}).get("stateInstance")
            logger.info(f"🟢 Instance state changed: {state}")
        else:
            logger.debug(f"Ignoring webhook type: {type_webhook}")

        return JSONResponse({"status": "ok"})

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status=500)
