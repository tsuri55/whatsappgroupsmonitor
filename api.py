"""FastAPI application for Green API webhooks."""
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, date

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlmodel import select

from commands import CommandHandler
from config import settings
from database import close_db, init_db, get_session
from green_api_client import GreenAPIClient
from message_handler import MessageHandler
from models import Group, Message, SummaryLog
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

    # Initialize database
    logger.info("1️⃣ Initializing database...")
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize components
    logger.info("2️⃣ Initializing components...")
    message_handler = MessageHandler()
    green_api_client = GreenAPIClient(message_handler)
    summary_generator = SummaryGenerator(green_api_client)
    command_handler = CommandHandler(green_api_client, summary_generator)
    message_handler.set_command_handler(command_handler)
    logger.info("✅ Components initialized")

    # Start message handler
    logger.info("3️⃣ Starting message handler...")
    await message_handler.start()
    logger.info("✅ Message handler started")

    # Start scheduler
    logger.info("4️⃣ Starting scheduler...")
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


@app.get("/web", response_class=HTMLResponse)
async def web_interface():
    """Web interface to view groups and messages."""
    async with get_session() as session:
        # Get all groups
        result = await session.exec(select(Group).order_by(Group.group_name))
        groups = list(result.all())

        # Get today's date
        today = date.today()

        # Get message count for each group today
        groups_data = []
        for group in groups:
            msg_result = await session.exec(
                select(Message)
                .where(Message.group_jid == group.group_jid)
                .where(Message.timestamp >= datetime.combine(today, datetime.min.time()))
            )
            messages = list(msg_result.all())

            # Get latest summary
            summary_result = await session.exec(
                select(SummaryLog)
                .where(SummaryLog.group_jid == group.group_jid)
                .order_by(SummaryLog.created_at.desc())
                .limit(1)
            )
            latest_summary = summary_result.first()

            groups_data.append({
                "group": group,
                "message_count_today": len(messages),
                "total_messages": len(messages),
                "latest_summary": latest_summary
            })

        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>WhatsApp Groups Monitor</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: #f5f5f5;
                    padding: 20px;
                    direction: rtl;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #128C7E;
                    margin-bottom: 10px;
                    font-size: 32px;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 18px;
                }}
                .stats {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    margin-bottom: 20px;
                }}
                .stats h2 {{
                    color: #128C7E;
                    margin-bottom: 15px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }}
                .stat-card {{
                    background: #f0f0f0;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #128C7E;
                }}
                .stat-label {{
                    color: #666;
                    margin-top: 5px;
                }}
                .groups-grid {{
                    display: grid;
                    gap: 20px;
                }}
                .group-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .group-card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 4px 10px rgba(0,0,0,0.15);
                }}
                .group-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                .group-name {{
                    font-size: 20px;
                    font-weight: bold;
                    color: #128C7E;
                }}
                .group-badge {{
                    background: #25D366;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }}
                .group-info {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 10px;
                }}
                .group-summary {{
                    background: #f9f9f9;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #25D366;
                    margin-top: 15px;
                    white-space: pre-wrap;
                    line-height: 1.6;
                }}
                .summary-title {{
                    font-weight: bold;
                    color: #128C7E;
                    margin-bottom: 10px;
                }}
                .no-summary {{
                    color: #999;
                    font-style: italic;
                }}
                .view-btn {{
                    display: inline-block;
                    background: #128C7E;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    margin-top: 10px;
                    transition: background 0.2s;
                }}
                .view-btn:hover {{
                    background: #0a5f52;
                }}
                .managed-badge {{
                    background: #4CAF50;
                    color: white;
                    padding: 3px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    margin-right: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 WhatsApp Groups Monitor</h1>
                <div class="subtitle">ניטור קבוצות ווטסאפ - {today.strftime('%d/%m/%Y')}</div>

                <div class="stats">
                    <h2>📊 סטטיסטיקות היום</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{len(groups)}</div>
                            <div class="stat-label">קבוצות מנוטרות</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{sum(g['message_count_today'] for g in groups_data)}</div>
                            <div class="stat-label">הודעות היום</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{sum(1 for g in groups_data if g['latest_summary'])}</div>
                            <div class="stat-label">סיכומים זמינים</div>
                        </div>
                    </div>
                </div>

                <div class="groups-grid">
        """

        # Add each group
        for data in groups_data:
            group = data["group"]
            msg_count = data["message_count_today"]
            summary = data["latest_summary"]

            managed_badge = '<span class="managed-badge">מנוטר</span>' if group.managed else ''

            summary_html = ""
            if summary and summary.summary_text:
                summary_date = summary.created_at.strftime('%d/%m/%Y %H:%M')
                summary_html = f"""
                    <div class="group-summary">
                        <div class="summary-title">💬 סיכום אחרון ({summary_date}):</div>
                        {summary.summary_text}
                    </div>
                """
            else:
                summary_html = '<div class="no-summary">אין סיכום זמין</div>'

            html += f"""
                    <div class="group-card">
                        <div class="group-header">
                            <div class="group-name">{managed_badge}{group.group_name or 'ללא שם'}</div>
                            <div class="group-badge">{msg_count} הודעות היום</div>
                        </div>
                        <div class="group-info">
                            🆔 {group.group_jid}<br>
                            📅 נוצר: {group.created_at.strftime('%d/%m/%Y %H:%M')}<br>
                            🔄 סיכום אחרון: {group.last_summary_sync.strftime('%d/%m/%Y %H:%M')}
                        </div>
                        {summary_html}
                        <a href="/web/group/{group.group_jid}" class="view-btn">צפה בהודעות →</a>
                    </div>
            """

        html += """
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html)


@app.get("/web/group/{group_jid}", response_class=HTMLResponse)
async def view_group_messages(group_jid: str):
    """View messages for a specific group."""
    async with get_session() as session:
        # Get group
        result = await session.exec(select(Group).where(Group.group_jid == group_jid))
        group = result.first()

        if not group:
            return HTMLResponse(content="<h1>Group not found</h1>", status_code=404)

        # Get today's messages
        today = date.today()
        msg_result = await session.exec(
            select(Message)
            .where(Message.group_jid == group_jid)
            .where(Message.timestamp >= datetime.combine(today, datetime.min.time()))
            .order_by(Message.timestamp.asc())
        )
        messages = list(msg_result.all())

        # Generate HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{group.group_name} - Messages</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: #e5ddd5;
                    padding: 20px;
                    direction: rtl;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                }}
                .header {{
                    background: #128C7E;
                    color: white;
                    padding: 20px;
                    border-radius: 10px 10px 0 0;
                }}
                .back-btn {{
                    color: white;
                    text-decoration: none;
                    display: inline-block;
                    margin-bottom: 10px;
                    padding: 5px 15px;
                    background: rgba(255,255,255,0.2);
                    border-radius: 5px;
                }}
                .back-btn:hover {{
                    background: rgba(255,255,255,0.3);
                }}
                h1 {{
                    font-size: 24px;
                }}
                .subtitle {{
                    opacity: 0.9;
                    margin-top: 5px;
                }}
                .messages {{
                    background: white;
                    padding: 20px;
                    border-radius: 0 0 10px 10px;
                    min-height: 400px;
                }}
                .message {{
                    background: #DCF8C6;
                    padding: 10px 15px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }}
                .message-sender {{
                    font-weight: bold;
                    color: #128C7E;
                    margin-bottom: 5px;
                }}
                .message-content {{
                    color: #303030;
                    white-space: pre-wrap;
                    line-height: 1.4;
                }}
                .message-time {{
                    color: #667781;
                    font-size: 12px;
                    text-align: left;
                    margin-top: 5px;
                }}
                .no-messages {{
                    text-align: center;
                    padding: 40px;
                    color: #666;
                    font-size: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <a href="/web" class="back-btn">← חזרה לדף הראשי</a>
                    <h1>💬 {group.group_name or 'ללא שם'}</h1>
                    <div class="subtitle">{len(messages)} הודעות היום • {today.strftime('%d/%m/%Y')}</div>
                </div>
                <div class="messages">
        """

        if messages:
            for msg in messages:
                sender = msg.sender_name or msg.sender_jid.split("@")[0]
                time_str = msg.timestamp.strftime('%H:%M')
                html += f"""
                    <div class="message">
                        <div class="message-sender">{sender}</div>
                        <div class="message-content">{msg.content}</div>
                        <div class="message-time">{time_str}</div>
                    </div>
                """
        else:
            html += '<div class="no-messages">אין הודעות היום בקבוצה זו</div>'

        html += """
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html)


@app.post("/webhook")
async def webhook(request: Request):
    """
    Webhook endpoint for Green API notifications.

    Green API will send notifications to this endpoint.
    Configure this URL in your Green API settings:
    https://console.green-api.com/instanceXXXX/webhooks
    """
    try:
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
