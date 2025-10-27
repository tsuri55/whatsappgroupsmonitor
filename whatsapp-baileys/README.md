# WhatsApp Baileys Bridge

A Node.js service that connects to WhatsApp using Baileys library and forwards messages to a webhook endpoint.

## Features

- Real-time message reception via WebSocket
- QR code authentication
- Automatic reconnection
- Forwards messages to configurable webhook URL
- Supports text, images, videos, documents, and audio messages

## Environment Variables

- `WEBHOOK_URL`: URL to forward messages to (default: `http://localhost:8000/webhook/message`)
- `LOG_LEVEL`: Logging level (default: `info`)

## Local Development

```bash
cd whatsapp-baileys
npm install
npm start
```

Scan the QR code with your WhatsApp mobile app.

## Docker

```bash
docker build -t whatsapp-baileys .
docker run -e WEBHOOK_URL=https://your-webhook-url.com/webhook/message whatsapp-baileys
```

## Railway Deployment

1. Create new service in Railway
2. Connect this directory
3. Set environment variable:
   - `WEBHOOK_URL=https://whatsappgroupsmonitor-production.up.railway.app/webhook/message`
4. Deploy
5. Check logs for QR code, scan with WhatsApp mobile app
6. Messages will be forwarded to your main application

## Message Format

Messages are forwarded in the format expected by the Python application:

```json
{
  "info": {
    "id": {"id": "message_id"},
    "messageSource": {
      "senderJID": "sender@s.whatsapp.net",
      "groupJID": "group@g.us"
    },
    "timestamp": 1234567890,
    "pushName": "Sender Name"
  },
  "message": {
    "conversation": "Message text"
  }
}
```
