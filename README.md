# WhatsApp Groups Monitor

An intelligent WhatsApp group monitoring system that captures messages from all your WhatsApp groups, stores them in a database, and generates AI-powered daily summaries using Google Gemini.

## Features

- **Real-time Monitoring**: Automatically captures messages from all WhatsApp groups via Green API webhooks
- **Smart Storage**: Stores messages in PostgreSQL or SQLite with group and sender information
- **AI Summaries**: Generates intelligent summaries using Google Gemini with automatic language detection
- **Scheduled Delivery**: Sends consolidated daily summaries at a configurable time (default: 20:00 Asia/Jerusalem)
- **On-Demand Summaries**: Request instant summaries with customizable keywords (default: "sikum", "סיכום", "summary", "summarize")
- **Web Interface**: View groups and messages in a Hebrew-language web dashboard
- **Command System**: Configurable command keywords for summary and stats commands

## Architecture

```
Green API Webhook → FastAPI → Message Handler → Database (PostgreSQL/SQLite)
                                      ↓
                                  Scheduler
                                      ↓
                           Summarizer (Gemini AI)
                                      ↓
                            Green API Client → WhatsApp
```

## Tech Stack

- **WhatsApp Integration**: Green API (WhatsApp Business API)
- **Backend**: Python 3.11+, FastAPI, asyncio
- **Database**: SQLModel, SQLAlchemy (PostgreSQL or SQLite)
- **AI**: Google Gemini Flash
- **Scheduling**: APScheduler
- **Deployment**: Railway-ready with Dockerfile

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Google Gemini API key ([Get one here](https://ai.google.dev/))
- Green API account ([Sign up here](https://green-api.com/))
- PostgreSQL (optional, SQLite works for development)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd wa-groups-monitor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Green API (required)
GREEN_API_INSTANCE_ID=your_instance_id
GREEN_API_TOKEN=your_api_token

# Google Gemini (required)
GOOGLE_API_KEY=your_gemini_api_key

# Database (optional, defaults to SQLite)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/whatsapp_monitor

# Summary recipient phone (required)
SUMMARY_RECIPIENT_PHONE=+1234567890

# Optional settings
SUMMARY_SCHEDULE_HOUR=20
SUMMARY_SCHEDULE_TIMEZONE=Asia/Jerusalem
SUMMARY_KEYWORDS=sikum,סיכום,summary,summarize
LOG_LEVEL=INFO
```

### 4. Run the Application

```bash
# Run with uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000

# Or run in development mode with reload
uvicorn api:app --reload
```

The application will:
- Start the FastAPI server on port 8000
- Create database tables automatically
- Begin listening for webhook messages
- Schedule daily summaries

### 5. Configure Green API Webhook

In your Green API dashboard:
1. Go to Settings → Webhooks
2. Set webhook URL: `https://your-domain.com/webhook`
3. Enable "Incoming Messages" notifications
4. Save the configuration

### 6. Access Web Interface

Open `http://localhost:8000/web` to view:
- Total groups monitored
- Today's message counts
- Recent summaries
- Individual group messages

## Usage

### On-Demand Summaries

Send a direct message to your bot's WhatsApp number (not in a group):

```
You: sikum
Bot: Generating summary for all groups... This may take a moment.
Bot: [Sends consolidated summary of all today's messages from all groups]
```

### Available Commands

**Summary Commands** (configurable via `SUMMARY_KEYWORDS`):
- Default keywords: `sikum`, `סיכום`, `summary`, `summarize`
- Action: Generate summary of today's messages from all groups
- Customize by setting `SUMMARY_KEYWORDS` in your `.env` file

**Other Commands**:
- `stats` - Show group and message statistics

**Authorization**: Only the phone number in `SUMMARY_RECIPIENT_PHONE` can use commands.

### Scheduled Summaries

The system automatically sends daily summaries at the configured time. The summary includes:
- All groups with messages since the last summary
- Message count per group
- AI-generated summary in the group's language
- User mentions with phone numbers

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GREEN_API_INSTANCE_ID` | Your Green API instance ID | **Required** |
| `GREEN_API_TOKEN` | Your Green API token | **Required** |
| `GOOGLE_API_KEY` | Google Gemini API key | **Required** |
| `SUMMARY_RECIPIENT_PHONE` | Phone number to receive summaries | **Required** |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./whatsapp_monitor.db` |
| `GEMINI_LLM_MODEL` | Gemini model name | `models/gemini-flash-latest` |
| `SUMMARY_SCHEDULE_HOUR` | Hour to send summaries (0-23) | `20` |
| `SUMMARY_SCHEDULE_TIMEZONE` | Timezone for scheduling | `Asia/Jerusalem` |
| `SUMMARY_KEYWORDS` | Comma-separated keywords that trigger summary | `sikum,סיכום,summary,summarize` |
| `MINIMUM_MESSAGES_FOR_SUMMARY` | Min messages to generate summary | `15` |
| `MAX_MESSAGES_PER_SUMMARY` | Max messages per summary | `1000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PORT` | Server port | `8000` |

### Database Support

**SQLite** (default, good for development):
```env
DATABASE_URL=sqlite+aiosqlite:///./whatsapp_monitor.db
```

**PostgreSQL** (recommended for production):
```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database
```

## Database Schema

### Groups Table
- Stores WhatsApp group information
- Tracks managed status and last summary timestamp
- Auto-extracts group names from webhooks

### Messages Table
- Stores individual messages with metadata
- Supports text, image, video, document types
- Includes sender information and timestamps

### Summary Logs Table
- Audit trail of generated summaries
- Tracks success/failure status
- Records message counts and time ranges

## Deployment

### Railway Deployment

1. Install Railway CLI:
```bash
npm install -g @railway/cli
railway login
```

2. Initialize project:
```bash
railway init
```

3. Add PostgreSQL database in Railway dashboard

4. Deploy:
```bash
railway up
```

5. Set environment variables in Railway dashboard:
   - All variables from `.env.example`
   - Update `DATABASE_URL` to Railway PostgreSQL URL

6. Configure Green API webhook to point to your Railway URL

### Docker Deployment

Build and run with Docker:

```bash
# Build image
docker build -t wa-groups-monitor .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  wa-groups-monitor
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/health` | Health status |
| `GET` | `/web` | Web dashboard (Hebrew) |
| `GET` | `/web/group/{group_jid}` | Group message view |
| `POST` | `/webhook` | Green API webhook receiver |

## Project Structure

```
wa-groups-monitor/
├── api.py                 # FastAPI application and endpoints
├── config.py              # Environment configuration
├── database.py            # Database session management
├── models.py              # SQLModel ORM models
├── whatsapp.py            # WhatsApp message data models
├── green_api_client.py    # Green API client wrapper
├── message_handler.py     # Webhook message processing
├── commands.py            # Bot command handler
├── summarizer.py          # AI summary generation
├── scheduler.py           # Daily summary scheduling
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Code quality config (Black, Ruff)
├── Dockerfile             # Container definition
├── railway.json           # Railway deployment config
├── .env.example           # Environment template
└── README.md              # This file
```

## How It Works

### Message Flow

1. Green API sends incoming message to `/webhook`
2. Message handler parses and validates the data
3. Message saved to database with group and sender info
4. If message is a command, command handler processes it

### Daily Summary Flow

1. APScheduler triggers at configured time
2. For each managed group:
   - Fetch messages since last summary
   - Check if minimum threshold met (15+ messages)
   - Generate AI summary using Gemini
   - Log summary to database
3. Consolidate all summaries into one message
4. Send via Green API to recipient
5. Update last_summary_sync for all groups

### On-Demand Summary Flow

1. User sends "sikum" command
2. System verifies authorization
3. Generates summaries for all groups (today's messages only)
4. Sends consolidated result immediately

## Troubleshooting

### No messages being captured
- Verify Green API webhook URL is correctly configured
- Check Green API instance is connected and active
- Review logs: `LOG_LEVEL=DEBUG` in `.env`

### Summaries not being sent
- Verify `SUMMARY_RECIPIENT_PHONE` format includes country code (e.g., `+1234567890`)
- Check if groups have minimum messages threshold
- Review scheduler logs for errors

### Database connection issues
- For PostgreSQL: verify connection string format and credentials
- For SQLite: ensure write permissions in application directory

### Commands not working
- Verify sender phone matches `SUMMARY_RECIPIENT_PHONE`
- Send commands as direct message (not in group)
- Check command spelling matches `SUMMARY_KEYWORDS` setting (default: "sikum", "סיכום", "summary", "summarize")
- For stats command, use: "stats"

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
# Run tests (when available)
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## Security Considerations

- Never commit `.env` file with credentials
- Keep Green API tokens secure
- Use HTTPS for webhook endpoint in production
- Restrict command access to authorized phone numbers only
- Use strong database passwords in production

## License

MIT License (or specify your license)

## Support

For issues and questions:
- Open an issue on GitHub
- Review logs with `LOG_LEVEL=DEBUG`
- Check Green API dashboard for connection status

## Acknowledgments

- [Green API](https://green-api.com/) - WhatsApp Business API provider
- [Google Gemini](https://ai.google.dev/) - AI-powered summarization
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases with Python
