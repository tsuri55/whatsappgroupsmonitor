# Webhook Setup Guide

## Overview

The application now uses **FastAPI webhooks** instead of polling. This is more efficient and provides real-time message processing.

## Architecture

```
WhatsApp → Green API → Webhook (Your Server) → Process Messages → Database
```

## Deployment Steps

### 1. Deploy to Railway

The application will automatically deploy when you push to GitHub. Railway will:
- Build the Docker image
- Run `uvicorn api:app` on port 8000
- Provide a public URL (e.g., `https://your-app.railway.app`)

### 2. Configure Green API Webhook

1. Go to your Green API console: https://console.green-api.com/
2. Select your instance
3. Go to **Settings** → **Webhooks**
4. Set the webhook URL to: `https://your-app.railway.app/webhook`
5. Enable the following webhook types:
   - `incomingMessageReceived` ✅
   - `stateInstanceChanged` ✅ (optional, for monitoring)
6. Save settings

### 3. Test the Webhook

Send a message to one of your monitored WhatsApp groups. You should see:

1. In Railway logs:
   ```
   📩 Webhook received: incomingMessageReceived
   MESSAGE HANDLER - Starting to process message data...
   💾 Saving group message to database
   ```

2. The message should be saved to the SQLite database

### 4. Test Commands

Send "sikum" or "stats" directly to the bot phone number (not in a group). You should receive a response.

## Endpoints

The FastAPI server provides these endpoints:

- `GET /` - Health check (returns status: ok)
- `GET /health` - Health check endpoint
- `POST /webhook` - Webhook endpoint for Green API notifications

## Environment Variables

Required variables in Railway:

```bash
# Green API (from https://green-api.com/)
GREEN_API_INSTANCE_ID=your_instance_id
GREEN_API_TOKEN=your_token

# Google Gemini API
GOOGLE_API_KEY=your_api_key

# Notification settings
SUMMARY_RECIPIENT_PHONE=+972542607800
SUMMARY_SCHEDULE_HOUR=20
SUMMARY_SCHEDULE_TIMEZONE=Asia/Jerusalem

# Optional settings
LOG_LEVEL=INFO
PORT=8000
```

## Database

The application now uses **SQLite** instead of PostgreSQL:
- File: `whatsapp_monitor.db` (created automatically)
- No external database service needed
- Data persists in Railway's volume storage

## Troubleshooting

### Webhook Not Receiving Messages

1. Check Railway logs for errors
2. Verify webhook URL in Green API console
3. Test endpoint: `curl https://your-app.railway.app/health`
4. Check if instance is authenticated in Green API

### Messages Not Saving

1. Check logs for database errors
2. Verify SQLite file has write permissions
3. Check message format in logs

### Commands Not Working

1. Verify `SUMMARY_RECIPIENT_PHONE` matches your phone number
2. Check logs for authorization errors
3. Ensure phone number format: `+972542607800@c.us`

## Monitoring

Watch Railway logs in real-time:
```bash
railway logs --follow
```

Look for these log patterns:
- `📩 Webhook received` - Incoming webhook
- `MESSAGE HANDLER` - Message processing
- `💾 Saving group message` - Database write
- `🤖 Checking if direct message is a command` - Command detection

## Migration from Polling

The old system used:
- Green API's polling mechanism (startReceivingNotifications)
- Complex asyncio event loop management
- PostgreSQL with pgvector

The new system uses:
- FastAPI webhooks (more efficient)
- Simpler architecture
- SQLite (easier to deploy)

No data migration needed - the database schema is the same.
