# Setup Guide - WhatsApp Groups Monitor

This guide will walk you through setting up the WhatsApp Groups Monitor from scratch.

## Step-by-Step Setup

### 1. System Requirements

Ensure you have:
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0+
- Python 3.11 or higher (for local development)
- Git
- Active WhatsApp account
- Google Cloud account with Gemini API access

### 2. Get Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key or use existing one
4. Copy the API key (starts with `AIza...`)
5. Keep it safe - you'll need it in step 4

### 3. Clone and Setup Project

```bash
# Clone the repository
git clone <your-repo-url>
cd wa-groups-monitor

# Create .env file from template
cp .env.example .env
```

### 4. Configure Environment Variables

Edit `.env` file with your settings:

```bash
# Generate a secure API key for WhatsApp webhook
# You can use: openssl rand -hex 32
WHATSAPP_API_KEY=your_secure_random_string_here

# Your Google Gemini API key from step 2
GOOGLE_API_KEY=AIzaSy...your_actual_key_here

# Phone number to receive daily summaries (include country code with +)
SUMMARY_RECIPIENT_PHONE=+972542607800

# Optional: Customize summary time (default: 20:00 / 8 PM)
SUMMARY_SCHEDULE_HOUR=20
SUMMARY_SCHEDULE_TIMEZONE=Asia/Jerusalem
```

**Important**:
- Phone number must include country code with `+` prefix
- WHATSAPP_API_KEY should be a secure random string
- Never commit `.env` to version control

### 5. Start the Application

```bash
# Start all services (PostgreSQL, WhatsApp API, Monitor App)
docker-compose up -d

# View logs to ensure everything started correctly
docker-compose logs -f
```

You should see:
```
✓ PostgreSQL started
✓ WhatsApp API started on port 3000
✓ WhatsApp Monitor started on port 8000
```

### 6. Connect Your WhatsApp Account

**This is a one-time setup:**

1. Open your browser to: **http://localhost:3000**

2. You'll see a QR code on the page

3. On your phone:
   - Open WhatsApp
   - Go to Settings → Linked Devices (or WhatsApp Web)
   - Tap "Link a Device"
   - Scan the QR code on your computer

4. Wait for connection confirmation

5. Your WhatsApp is now connected! The session persists even after restarts.

### 7. Verify Setup

Check that the system is working:

```bash
# View application logs
docker-compose logs app

# You should see messages like:
# ✓ WhatsApp Groups Monitor is running!
# ✓ Daily summaries scheduled at 20:00 Asia/Jerusalem
# ✓ Summary recipient: +972542607800
# Syncing existing groups...
# Synced 12 groups
```

### 8. Database Verification

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d whatsapp_monitor

# Check groups were synced
SELECT group_name, managed, last_summary_sync FROM groups;

# Exit PostgreSQL
\q
```

### 9. Test Message Collection

1. Send a test message in one of your WhatsApp groups
2. Check logs: `docker-compose logs -f app`
3. You should see: `Saved message <id> from <sender> in group <jid>`

### 10. Test On-Demand Summary

You can request a summary anytime without waiting for the scheduled time:

**Method 1: Send "sikum" command (Recommended)**
1. On your phone, open WhatsApp
2. Send a direct message to the bot (the same WhatsApp number hosting the bot)
3. Type: **sikum**
4. Wait for the bot to respond with a consolidated summary

**Note**: Only the phone number configured in `SUMMARY_RECIPIENT_PHONE` can use this command.

**Method 2: Wait for scheduled time**
- Summaries are automatically sent at 20:00 UTC+3 by default

## Deployment to Railway

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

Follow the prompts to create a new project.

### 4. Add PostgreSQL Database

**In Railway Dashboard:**

1. Click "New" → "Database" → "Add PostgreSQL"
2. Wait for provisioning
3. Copy the `DATABASE_URL` from Variables tab
4. Click "Connect" and run this SQL:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 5. Add WhatsApp Web Service

**In Railway Dashboard:**

1. Click "New" → "Empty Service"
2. Name it: `whatsapp-api`
3. Go to Settings → Set image source:
   - Image: `aldinokemal2104/go-whatsapp-web-multidevice:latest`
4. Go to Variables tab and add:
   - `WEBHOOK_URL`: (leave empty for now, we'll update later)
   - `WEBHOOK_SECRET`: (same as your WHATSAPP_API_KEY)

### 6. Deploy Main Application

```bash
# Deploy from your local directory
railway up

# Or link to GitHub repo
railway link
```

### 7. Configure Environment Variables in Railway

**In your main service Variables tab, add:**

```
WHATSAPP_API_URL=<whatsapp-api-service-url-from-railway>
WHATSAPP_API_KEY=<your-secure-key>
DATABASE_URL=<postgresql-url-from-railway>
DATABASE_SYNC_URL=<postgresql-url-from-railway-with-psycopg2>
GOOGLE_API_KEY=<your-gemini-api-key>
SUMMARY_RECIPIENT_PHONE=+972542607800
SUMMARY_SCHEDULE_HOUR=20
SUMMARY_SCHEDULE_TIMEZONE=Asia/Jerusalem
LOG_LEVEL=INFO
```

**Important**:
- `DATABASE_URL` should use `postgresql+asyncpg://...`
- `DATABASE_SYNC_URL` should use `postgresql://...` (for migrations)

### 8. Update WhatsApp API Webhook

**Go back to whatsapp-api service:**

1. Go to Variables tab
2. Update `WEBHOOK_URL` to: `https://<your-main-app-url>.railway.app/webhook/message`
3. Redeploy the service

### 9. Connect WhatsApp on Railway

1. Open the WhatsApp API service URL (get from Railway dashboard)
2. Scan QR code with WhatsApp mobile app
3. Connection is now live on Railway!

### 10. Monitor Railway Deployment

```bash
# View logs
railway logs

# Check status
railway status
```

## Troubleshooting Setup Issues

### Issue: "Cannot connect to Docker daemon"

**Solution**: Ensure Docker Desktop is running

```bash
# Check Docker status
docker info

# Start Docker Desktop (varies by OS)
# Windows/Mac: Open Docker Desktop application
# Linux: sudo systemctl start docker
```

### Issue: "Port already in use"

**Solution**: Another service is using ports 3000, 5432, or 8000

```bash
# Find process using port
# Windows:
netstat -ano | findstr :3000

# Mac/Linux:
lsof -i :3000

# Kill the process or change ports in docker-compose.yml
```

### Issue: "QR code not appearing"

**Solution**: Check WhatsApp API logs

```bash
docker-compose logs whatsapp

# Restart the service
docker-compose restart whatsapp
```

### Issue: "Database connection failed"

**Solution**: Verify PostgreSQL is running

```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker-compose exec postgres pg_isready -U postgres

# Should output: "postgres:5432 - accepting connections"
```

### Issue: "Gemini API errors"

**Solutions**:

1. **Invalid API Key**:
   - Verify `GOOGLE_API_KEY` in `.env`
   - Ensure no extra spaces or quotes

2. **Quota Exceeded**:
   - Check [Google AI Studio](https://makersuite.google.com) for quota
   - Consider upgrading plan or rate limiting

3. **Network Issues**:
   - Ensure container has internet access
   - Check firewall settings

### Issue: "Messages not being saved"

**Solution**: Check webhook configuration

```bash
# Verify webhook is receiving requests
docker-compose logs app | grep webhook

# Test webhook manually
curl -X POST http://localhost:8000/health
# Should return: {"status":"healthy"}

# Check WhatsApp API webhook URL is correct
# Should be: http://app:8000/webhook/message (in Docker network)
```

### Issue: "Summaries not being sent"

**Solutions**:

1. **Not enough messages**:
   - Groups need minimum 15 messages (configurable)
   - Check: `MINIMUM_MESSAGES_FOR_SUMMARY` in `.env`

2. **Wrong schedule time**:
   - Verify `SUMMARY_SCHEDULE_HOUR` and timezone
   - Check server time: `docker-compose exec app date`

3. **Phone number format**:
   - Must include `+` and country code
   - Example: `+972542607800` (not `972542607800`)

## Next Steps

After successful setup:

1. **Monitor Logs**: Keep an eye on logs for first 24 hours
   ```bash
   docker-compose logs -f app
   ```

2. **Verify Data Collection**: Check messages are being stored
   ```bash
   docker-compose exec postgres psql -U postgres -d whatsapp_monitor -c "SELECT COUNT(*) FROM messages;"
   ```

3. **Test On-Demand Summary**: Send "sikum" to the bot to verify the command works

4. **Wait for First Scheduled Summary**: Summaries are sent at configured time (20:00 UTC+3 by default)

5. **Customize Settings**: Adjust `.env` as needed:
   - Change summary time
   - Modify message thresholds
   - Update recipient phone

6. **Backup WhatsApp Session**: The session data is stored in Docker volume `whatsapp_data`
   ```bash
   # Backup session data
   docker cp $(docker-compose ps -q whatsapp):/app/storages ./whatsapp_backup
   ```

## Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify environment variables: `cat .env`
3. Test database connection
4. Ensure WhatsApp is still connected
5. Check Google API quota
6. Review troubleshooting section above
7. Open an issue on GitHub with logs

## Production Recommendations

For production deployment:

1. **Use managed PostgreSQL** (Railway, AWS RDS, etc.)
2. **Set up monitoring** (Sentry, Datadog, etc.)
3. **Configure backups** for database and WhatsApp session
4. **Use HTTPS** for webhook endpoints
5. **Set up alerts** for failures
6. **Implement rate limiting** for Gemini API calls
7. **Use secrets management** (Railway secrets, AWS Secrets Manager)
8. **Enable auto-restart** policies
9. **Monitor API quotas** (Gemini, WhatsApp)
10. **Set up log aggregation** (Papertrail, Loggly)

Congratulations! Your WhatsApp Groups Monitor is now set up and running.
