# WhatsApp Groups Monitor

A comprehensive WhatsApp monitoring system that connects to your WhatsApp account, monitors all group chats, records messages throughout the day, and sends daily AI-generated summaries to a specified phone number.

## Features

- **Real-time Message Monitoring**: Automatically captures all messages from WhatsApp groups
- **Message Storage**: Stores all messages in PostgreSQL for summary generation
- **AI-Generated Summaries**: Creates intelligent, context-aware summaries using Gemini Flash LLM
- **Language Detection**: Summaries match the language of the group chat automatically
- **User Tagging**: Mentions users in summaries for better context
- **Scheduled Delivery**: Sends consolidated daily summaries at a configurable time (default: 20:00 UTC+3)
- **On-Demand Summaries**: Send "sikum" to the bot anytime to get instant summaries of all groups
- **Scalable Architecture**: Built with async Python for high performance

## Architecture

```
WhatsApp Web (Docker) → Message Handler → PostgreSQL
                              ↓
                        Daily Scheduler → Summary Generator (Gemini) → WhatsApp Sender
```

## Tech Stack

- **WhatsApp Interface**: aldinokemal2104/go-whatsapp-web-multidevice (Docker)
- **Database**: PostgreSQL 16
- **LLM**: Google Gemini Flash (latest)
- **Backend**: Python 3.11+ with asyncio
- **Deployment**: Railway-ready

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Google Cloud API key (for Gemini)
- Active WhatsApp account
- Railway account (for deployment)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd wa-groups-monitor
```

### 2. Configure Environment Variables

Copy the example environment file and edit it with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `SUMMARY_RECIPIENT_PHONE`: Phone number to receive daily summaries (e.g., +972542607800)
- `WHATSAPP_API_KEY`: Generate a secure API key for WhatsApp webhook authentication

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- WhatsApp Web API on port 3000
- WhatsApp Monitor application on port 8000

### 4. Connect WhatsApp Account

1. Open http://localhost:3000 in your browser
2. Scan the QR code with your WhatsApp mobile app
3. Your WhatsApp account is now connected!

The system will automatically:
- Load all your WhatsApp groups
- Start monitoring new messages
- Schedule daily summaries

### 5. Request On-Demand Summaries

You can get summaries anytime by sending a direct message to the bot:

1. Open WhatsApp on your phone
2. Send a direct message (not in a group) to the bot's number (the same WhatsApp account hosting the bot)
3. Type: **sikum**
4. You'll receive a consolidated summary of all groups immediately

**Note**: Only the authorized phone number (configured in `SUMMARY_RECIPIENT_PHONE`) can request summaries.

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL

```bash
docker-compose up postgres -d
```

### 4. Run the Application

```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WHATSAPP_API_URL` | WhatsApp API endpoint | http://localhost:3000 |
| `WHATSAPP_API_KEY` | API key for webhook auth | your_api_key_here |
| `DATABASE_URL` | PostgreSQL connection URL (async) | postgresql+asyncpg://... |
| `GOOGLE_API_KEY` | Google Gemini API key | **Required** |
| `GEMINI_LLM_MODEL` | LLM model name | models/gemini-flash-latest |
| `SUMMARY_RECIPIENT_PHONE` | Phone to receive summaries | +972542607800 |
| `SUMMARY_SCHEDULE_HOUR` | Hour to send summaries (0-23) | 20 |
| `SUMMARY_SCHEDULE_TIMEZONE` | Timezone for scheduling | Asia/Jerusalem |
| `LOG_LEVEL` | Logging level | INFO |
| `MINIMUM_MESSAGES_FOR_SUMMARY` | Min messages to generate summary | 15 |
| `MAX_MESSAGES_PER_SUMMARY` | Max messages per summary | 1000 |

### Summary Schedule

By default, summaries are sent at **20:00 (8 PM) UTC+3** (Asia/Jerusalem timezone). You can customize this:

```env
SUMMARY_SCHEDULE_HOUR=18  # 6 PM
SUMMARY_SCHEDULE_TIMEZONE=America/New_York
```

## Database Schema

### Groups Table
- `id`: Primary key
- `group_jid`: WhatsApp Group JID (unique)
- `group_name`: Group display name
- `managed`: Whether to monitor this group
- `last_summary_sync`: Timestamp of last summary
- `created_at`, `updated_at`: Timestamps

### Messages Table
- `id`: Primary key
- `message_id`: WhatsApp Message ID (unique)
- `group_jid`: Foreign key to groups
- `sender_jid`: Sender's WhatsApp JID
- `sender_name`: Sender's display name
- `content`: Message text content
- `message_type`: Type (text, image, video, etc.)
- `timestamp`: Message timestamp
- `created_at`: Record creation time

### Summary Logs Table
- `id`: Primary key
- `group_jid`: Foreign key to groups
- `summary_text`: Generated summary
- `message_count`: Number of messages summarized
- `start_time`, `end_time`: Summary period
- `sent_successfully`: Delivery status
- `error_message`: Error details if failed
- `created_at`: Log timestamp

## How It Works

### Message Flow

1. **Message Reception**: WhatsApp API sends new messages via webhook to `/webhook/message`
2. **Message Processing**: Handler parses and validates the message
3. **Database Storage**: Message is saved to PostgreSQL

### Daily Summary Flow

1. **Scheduled Trigger**: APScheduler triggers at configured time (20:00 UTC+3)
2. **Group Processing**: For each managed group:
   - Fetch messages since last summary
   - Check minimum threshold (15+ messages)
   - Generate summary using Gemini LLM
   - Log summary to database
3. **Consolidation**: All group summaries combined into one message
4. **Delivery**: Consolidated summary sent via WhatsApp to recipient
5. **State Update**: Update `last_summary_sync` for all groups

### On-Demand Summary Flow

1. **User Request**: Authorized user sends "sikum" via direct message to bot
2. **Command Detection**: Message handler recognizes the command
3. **Authorization**: Verifies sender is the configured recipient phone
4. **Acknowledgment**: Bot sends "Generating summary..." message
5. **Summary Generation**: Same as daily summary flow
6. **Delivery**: Consolidated summary sent immediately to requester

### Summary Format

```
📱 Daily WhatsApp Groups Summary - 2025-01-15
==================================================

📌 Family Chat (45 messages)
Quick summary of Family Chat group recently. Mom asked about dinner plans
for Friday, @972501234567 suggested Italian restaurant. Dad shared photos
from his trip. Discussion about Uncle's birthday gift - decided on a watch.

📌 Work Team (78 messages)
Quick summary of Work Team group recently. @972509876543 presented Q4
results showing 15% growth. Team discussed new project timeline, deadline
set for March 1st. Sarah raised concerns about resources, meeting scheduled
for Monday to address.

==================================================
Generated by WhatsApp Groups Monitor
```

## Railway Deployment

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Login to Railway

```bash
railway login
```

### 3. Create New Project

```bash
railway init
```

### 4. Add PostgreSQL Database

In Railway dashboard:
1. Click "New" → "Database" → "PostgreSQL"
2. Note the connection URL

### 5. Deploy WhatsApp API

Add a new service:
1. Click "New" → "Empty Service"
2. Name it "whatsapp-api"
3. Set image: `aldinokemal2104/go-whatsapp-web-multidevice:latest`
4. Add environment variables:
   - `WEBHOOK_URL`: https://your-app-domain.railway.app/webhook/message
   - `WEBHOOK_SECRET`: Your API key

### 6. Deploy Main Application

```bash
railway up
```

### 7. Set Environment Variables

In Railway dashboard:
- Copy all variables from `.env.example`
- Set your actual values (especially `GOOGLE_API_KEY`)
- Update `WHATSAPP_API_URL` to Railway WhatsApp service URL
- Update `DATABASE_URL` to Railway PostgreSQL URL

### 8. Connect WhatsApp

1. Open your WhatsApp API Railway service URL
2. Scan QR code with WhatsApp mobile app
3. Connection persists across deployments

## API Endpoints

### Webhook Endpoints

- `POST /webhook/message` - Receive WhatsApp messages
- `GET /health` - Health check endpoint

### WhatsApp API Endpoints (via go-whatsapp-web-multidevice)

- `POST /send/message` - Send a message
- `GET /groups` - List all groups
- `GET /user/info` - Get account info

## Monitoring & Logs

### View Logs (Docker)

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f whatsapp
docker-compose logs -f postgres
```

### View Logs (Railway)

```bash
railway logs
```

### Database Queries

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d whatsapp_monitor

# View groups
SELECT group_name, managed, last_summary_sync FROM groups;

# Count messages by group
SELECT g.group_name, COUNT(m.id) as message_count
FROM groups g
LEFT JOIN messages m ON g.group_jid = m.group_jid
GROUP BY g.group_name;

# View recent summaries
SELECT group_jid, message_count, sent_successfully, created_at
FROM summary_logs
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### WhatsApp Connection Issues

**Problem**: QR code not appearing
- Check WhatsApp API container logs: `docker-compose logs whatsapp`
- Restart WhatsApp container: `docker-compose restart whatsapp`

**Problem**: Connection lost
- WhatsApp session may have expired
- Rescan QR code at http://localhost:3000

### Database Issues

**Problem**: Connection refused
- Ensure PostgreSQL is running: `docker-compose ps`
- Check DATABASE_URL in `.env`

### Summary Issues

**Problem**: No summaries being sent
- Check scheduler logs for errors
- Verify SUMMARY_RECIPIENT_PHONE format (+countrycode...)
- Ensure groups have minimum messages threshold

**Problem**: Summaries in wrong language
- Gemini should auto-detect language from messages
- Check if messages have enough text content

## Development

### Code Style

```bash
# Format code
black .

# Lint code
ruff check .
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

### On-Demand Summary Commands

The bot supports the following interactive commands via direct message:

**Command**: `sikum`
**Description**: Generate and send a summary of all groups for the current day
**Usage**:
1. Send a direct message to the bot (not in a group)
2. Type: `sikum`
3. Wait for the bot to generate and send summaries

**Authorization**: Only the phone number configured in `SUMMARY_RECIPIENT_PHONE` can use commands.

**Example**:
```
You: sikum
Bot: ⏳ Generating summary for all groups... This may take a moment.
Bot: [Sends consolidated summary of all groups]
```

## Project Structure

```
wa-groups-monitor/
├── config.py              # Configuration management
├── database.py            # Database connection & session
├── models.py              # SQLModel database models
├── whatsapp.py           # WhatsApp API client wrapper
├── message_handler.py    # Message processing pipeline
├── commands.py           # Bot command handler (sikum, etc.)
├── summarizer.py         # Summary generation with Gemini
├── scheduler.py          # APScheduler for daily summaries
├── webhook.py            # Webhook server for messages
├── main.py               # Application entry point
├── utils.py              # Utility functions
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker services configuration
├── Dockerfile            # Application container
├── railway.toml          # Railway deployment config
├── railway.json          # Railway schema
├── .env.example          # Environment template
└── README.md            # This file
```

## Security Considerations

1. **API Keys**: Never commit `.env` file with real credentials
2. **Database**: Use strong passwords in production
3. **WhatsApp**: Keep session data secure (stored in Docker volume)
4. **Webhook**: Use secure WEBHOOK_SECRET for authentication
5. **Network**: Consider using HTTPS for webhook endpoint in production

## Future Enhancements

- [ ] Web dashboard for viewing summaries
- [x] On-demand summary generation via WhatsApp command (implemented via "sikum")
- [ ] Analytics and insights (trending topics, active users)
- [ ] Custom summary schedules per group
- [ ] Multi-language summary translation
- [ ] Message retention policies
- [ ] Group filtering/blacklisting
- [ ] Sentiment analysis
- [ ] Integration with Slack/Discord
- [ ] Additional bot commands (e.g., "stats", "help")

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs for error messages

## Acknowledgments

- [go-whatsapp-web-multidevice](https://github.com/aldinokemal/go-whatsapp-web-multidevice) - WhatsApp Web API
- [Google Gemini](https://ai.google.dev/) - LLM for AI-generated summaries
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases with Python type annotations
