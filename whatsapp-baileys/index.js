import makeWASocket, {
    DisconnectReason,
    useMultiFileAuthState,
    makeInMemoryStore,
    Browsers
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import { Boom } from '@hapi/boom';

// Configuration from environment variables
const WEBHOOK_URL = process.env.WEBHOOK_URL || 'http://localhost:8000/webhook/message';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

// Logger
const logger = pino({ level: LOG_LEVEL });

// Store for message handling
const store = makeInMemoryStore({ logger });

/**
 * Forward message to webhook endpoint
 */
async function forwardToWebhook(messageData) {
    try {
        logger.info(`Forwarding message to webhook: ${WEBHOOK_URL}`);

        const response = await axios.post(WEBHOOK_URL, messageData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000
        });

        logger.info(`Webhook response: ${response.status}`);
        return response.data;
    } catch (error) {
        logger.error(`Failed to forward to webhook: ${error.message}`);
        if (error.response) {
            logger.error(`Response status: ${error.response.status}`);
            logger.error(`Response data: ${JSON.stringify(error.response.data)}`);
        }
    }
}

/**
 * Convert Baileys message to format expected by webhook
 */
function formatMessage(msg) {
    const messageContent = msg.message;
    const messageKey = msg.key;

    // Extract text content
    let content = '';
    let messageType = 'text';

    if (messageContent.conversation) {
        content = messageContent.conversation;
    } else if (messageContent.extendedTextMessage) {
        content = messageContent.extendedTextMessage.text;
    } else if (messageContent.imageMessage) {
        content = messageContent.imageMessage.caption || '[Image]';
        messageType = 'image';
    } else if (messageContent.videoMessage) {
        content = messageContent.videoMessage.caption || '[Video]';
        messageType = 'video';
    } else if (messageContent.documentMessage) {
        content = '[Document]';
        messageType = 'document';
    } else if (messageContent.audioMessage) {
        content = '[Audio]';
        messageType = 'audio';
    }

    // Format in the structure expected by your Python app
    return {
        info: {
            id: {
                id: messageKey.id
            },
            messageSource: {
                senderJID: messageKey.participant || messageKey.remoteJid,
                groupJID: messageKey.remoteJid?.endsWith('@g.us') ? messageKey.remoteJid : ''
            },
            timestamp: msg.messageTimestamp,
            pushName: msg.pushName || ''
        },
        message: {
            conversation: content,
            extendedTextMessage: messageContent.extendedTextMessage || {},
            imageMessage: messageContent.imageMessage || {},
            videoMessage: messageContent.videoMessage || {},
            documentMessage: messageContent.documentMessage || {}
        }
    };
}

/**
 * Start WhatsApp connection
 */
async function startWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info');

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: true,
        logger: pino({ level: LOG_LEVEL }),
        browser: Browsers.ubuntu('Chrome'),
        // Mark messages as read automatically
        markOnlineOnConnect: true,
    });

    store.bind(sock.ev);

    // Handle connection updates
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            logger.info('📱 QR Code generated - scan with WhatsApp mobile app');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error instanceof Boom)
                ? lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut
                : true;

            logger.info(`Connection closed. Reconnecting: ${shouldReconnect}`);

            if (shouldReconnect) {
                setTimeout(() => startWhatsApp(), 3000);
            }
        } else if (connection === 'open') {
            logger.info('✅ Connected to WhatsApp successfully!');
        }
    });

    // Handle credential updates
    sock.ev.on('creds.update', saveCreds);

    // Handle incoming messages
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        logger.info(`Received ${messages.length} message(s) - type: ${type}`);

        for (const msg of messages) {
            // Skip if no message content
            if (!msg.message) {
                logger.debug('Skipping message without content');
                continue;
            }

            // Skip if message is from status broadcast
            if (msg.key.remoteJid === 'status@broadcast') {
                logger.debug('Skipping status broadcast');
                continue;
            }

            logger.info(`📩 Message from: ${msg.key.remoteJid}`);
            logger.debug(`Message key: ${JSON.stringify(msg.key)}`);
            logger.debug(`Message content: ${JSON.stringify(msg.message)}`);

            // Format and forward to webhook
            const formattedMessage = formatMessage(msg);
            await forwardToWebhook(formattedMessage);
        }
    });

    // Handle message updates (edits, deletes, etc.)
    sock.ev.on('messages.update', (updates) => {
        logger.debug(`Message updates: ${JSON.stringify(updates)}`);
    });

    return sock;
}

// Start the application
logger.info('🚀 Starting WhatsApp Baileys Bridge...');
logger.info(`📡 Webhook URL: ${WEBHOOK_URL}`);

startWhatsApp().catch((error) => {
    logger.error(`Failed to start: ${error.message}`);
    process.exit(1);
});

// Handle graceful shutdown
process.on('SIGINT', () => {
    logger.info('Shutting down...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    logger.info('Shutting down...');
    process.exit(0);
});
