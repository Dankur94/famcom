/**
 * WhatsApp Web Bridge for FamCom
 *
 * Uses Baileys v7 (no Chromium needed, ~50 MB RAM).
 * Forwards messages to the Python backend via HTTP.
 *
 * Start: node bridge.js
 * First run: scan QR code with your phone
 */

const { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, makeCacheableSignalKeyStore, downloadMediaMessage } = require('baileys');
const QRCode = require('qrcode');
const NodeCache = require('node-cache');
const http = require('http');
const pino = require('pino');

// --- Group metadata cache (prevents rate limits and not-acceptable errors) ---
const groupCache = new NodeCache({ stdTTL: 300 });

// --- Config ---
const PYTHON_BACKEND = 'http://localhost:8001';
const TARGET_GROUP = process.env.WA_GROUP_NAME || 'FamCom';
const PORT = 3002;
const AUTH_DIR = './wa-session';

// --- State ---
let sock = null;
let targetGroupId = null;
let currentQR = null;
const sentMessageIds = new Set();

// --- Connect to WhatsApp ---
async function connectWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();
    console.log(`Using WA version: ${version.join('.')}`);

    const logger = pino({ level: 'warn' });

    sock = makeWASocket({
        version,
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, logger),
        },
        logger,
        browser: ['FamCom', 'Chrome', '120.0.0'],
        connectTimeoutMs: 60000,
        qrTimeout: 60000,
        syncFullHistory: false,
        markOnlineOnConnect: true,
        cachedGroupMetadata: async (jid) => groupCache.get(jid),
    });

    // Save credentials on update
    sock.ev.on('creds.update', saveCreds);

    // Connection events
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            currentQR = qr;
            console.log('\n========================================');
            console.log('  SCAN QR CODE: http://localhost:3002/qr');
            console.log('========================================\n');
        }

        if (connection === 'open') {
            currentQR = null;
            console.log('\n✅ WhatsApp Bridge connected and ready!');
            console.log(`Listening for messages in group: "${TARGET_GROUP}"`);
            findTargetGroup();
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`Disconnected (code: ${statusCode}). Reconnect: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(connectWhatsApp, 5000);
            } else {
                console.log('Logged out. Delete wa-session folder and restart to re-scan.');
                process.exit(1);
            }
        }
    });

    // Message handler
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            if (!msg.message) continue;
            // Skip messages sent by this bridge (but allow user's own messages)
            if (sentMessageIds.has(msg.key.id)) {
                sentMessageIds.delete(msg.key.id);
                continue;
            }

            // Only handle group messages
            const isGroup = msg.key.remoteJid?.endsWith('@g.us');
            if (!isGroup) continue;

            // Get group name (use cache)
            let groupName = '';
            try {
                let metadata = groupCache.get(msg.key.remoteJid);
                if (!metadata) {
                    metadata = await sock.groupMetadata(msg.key.remoteJid);
                    groupCache.set(msg.key.remoteJid, metadata);
                }
                groupName = metadata.subject;
            } catch {
                continue;
            }

            // Only process messages from target group
            if (!groupName.includes(TARGET_GROUP)) continue;

            // Get sender name
            const senderPhone = msg.key.participant || msg.key.remoteJid;
            const senderName = msg.pushName || senderPhone;

            // Save target group ID for sending
            if (!targetGroupId) {
                targetGroupId = msg.key.remoteJid;
            }

            const timestamp = new Date((msg.messageTimestamp || 0) * 1000).toISOString();

            // --- Voice Note handling ---
            if (msg.message.audioMessage?.ptt === true) {
                console.log(`[${senderName}]: 🎤 Voice note received`);
                try {
                    const buffer = await downloadMediaMessage(msg, 'buffer', {});
                    const audio_base64 = buffer.toString('base64');
                    const voicePayload = {
                        audio_base64,
                        sender: senderName,
                        sender_phone: senderPhone,
                        timestamp,
                        group: groupName,
                    };
                    const response = await forwardToBackend(voicePayload, '/voice');
                    if (response && response.reply) {
                        await sendWithRetry(msg.key.remoteJid, response.reply);
                    }
                } catch (err) {
                    console.error('Voice processing error:', err.message);
                }
                continue;
            }

            // Extract text
            const text = msg.message.conversation
                || msg.message.extendedTextMessage?.text
                || '';
            if (!text) continue;

            const payload = {
                text: text,
                sender: senderName,
                sender_phone: senderPhone,
                timestamp,
                group: groupName,
            };

            console.log(`[${senderName}]: ${text}`);

            // Forward to Python backend
            try {
                const response = await forwardToBackend(payload);
                if (response && response.reply) {
                    await sendWithRetry(msg.key.remoteJid, response.reply);
                }
            } catch (err) {
                console.error('Send error:', err.message);
            }
        }
    });
}

// --- Send with retry (handles session sync delays) ---
async function sendWithRetry(jid, text, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const result = await sock.sendMessage(jid, { text });
            if (result?.key?.id) sentMessageIds.add(result.key.id);
            console.log(`[Bot]: ${text}`);
            return;
        } catch (err) {
            console.error(`Send attempt ${attempt}/${maxRetries} failed: ${err.message}`);
            if (attempt < maxRetries) {
                const delay = attempt * 5000;
                console.log(`Retrying in ${delay / 1000}s...`);
                await new Promise(r => setTimeout(r, delay));
            }
        }
    }
    console.error('All send attempts failed.');
}

// --- Find target group ---
async function findTargetGroup() {
    try {
        const groups = await sock.groupFetchAllParticipating();
        for (const [id, metadata] of Object.entries(groups)) {
            if (metadata.subject.includes(TARGET_GROUP)) {
                targetGroupId = id;
                groupCache.set(id, metadata);
                console.log(`Target group found: "${metadata.subject}" (${id}, ${metadata.participants.length} members, cached)`);
                return;
            }
        }
        console.warn(`Group "${TARGET_GROUP}" not found! Make sure a group with "${TARGET_GROUP}" in its name exists.`);
    } catch (err) {
        console.error('Error finding group:', err.message);
    }
}

// --- Forward to Python Backend ---
function forwardToBackend(payload, path = '/message') {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(payload);
        const url = new URL(`${PYTHON_BACKEND}${path}`);

        const options = {
            hostname: url.hostname,
            port: url.port,
            path: url.pathname,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(data),
            },
        };

        const req = http.request(options, (res) => {
            let body = '';
            res.on('data', (chunk) => body += chunk);
            res.on('end', () => {
                try {
                    resolve(JSON.parse(body));
                } catch {
                    resolve(null);
                }
            });
        });

        req.on('error', reject);
        req.setTimeout(30000, () => {
            req.destroy();
            reject(new Error('Backend timeout'));
        });

        req.write(data);
        req.end();
    });
}

// --- HTTP server for Python backend to send scheduled messages ---
const server = http.createServer(async (req, res) => {
    if (req.method === 'GET' && req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: sock ? 'connected' : 'disconnected', group: !!targetGroupId }));
        return;
    }

    if (req.method === 'GET' && req.url === '/qr') {
        if (!currentQR) {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end('<html><body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;font-size:2em;background:#111;color:#0f0">Already connected! No QR needed.</body></html>');
        } else {
            QRCode.toDataURL(currentQR, { width: 400, margin: 2 }, (err, dataUrl) => {
                res.writeHead(200, { 'Content-Type': 'text/html' });
                res.end(`<html><body style="display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;background:#111;color:#fff;font-family:sans-serif">
<h2>Scan with WhatsApp</h2>
<p>WhatsApp &rarr; Linked Devices &rarr; Link a Device</p>
<img src="${dataUrl}" style="border:8px solid #fff;border-radius:12px">
<p style="color:#888;margin-top:20px">Page auto-refreshes every 30s</p>
<meta http-equiv="refresh" content="30">
</body></html>`);
            });
        }
        return;
    }

    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { text } = JSON.parse(body);
                if (!targetGroupId) await findTargetGroup();
                if (targetGroupId && sock) {
                    await sendWithRetry(targetGroupId, text);
                    console.log(`[Bot scheduled]: ${text}`);
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ status: 'sent' }));
                } else {
                    res.writeHead(404, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Group not found or not connected' }));
                }
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: err.message }));
            }
        });
        return;
    }

    res.writeHead(404);
    res.end();
});

server.listen(PORT, () => {
    console.log(`Bridge HTTP server on port ${PORT}`);
});

// --- Start ---
console.log('Starting FamCom WhatsApp Bridge...');
connectWhatsApp();
