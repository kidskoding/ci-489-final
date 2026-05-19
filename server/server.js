const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const dgram = require('dgram');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const path = require('path');
const db = require('./db');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const SECRET = process.env.JWT_SECRET || 'kepler-secret-key-123';
const PORT = process.env.PORT || 3000;
const JOIN_CODE = process.env.JOIN_CODE || 'CI-489-DEMO';
const DISCOVERY_PORT = Number(process.env.DISCOVERY_PORT || 48901);
const GAME_URL = process.env.GAME_URL || 'https://kidskoding.github.io/ci-489-final/';
const ENABLE_DISCOVERY = process.env.ENABLE_DISCOVERY === 'true';

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
  res.redirect('/play.html');
});

app.get('/healthz', (req, res) => {
  res.json({ ok: true });
});

app.get('/config.js', (req, res) => {
  res.type('application/javascript');
  res.send(`window.KEPLER_CONFIG = ${JSON.stringify({ gameUrl: GAME_URL })};`);
});

// Auth APIs
app.post('/api/register', (req, res) => {
  const { username, password } = req.body;
  const hash = bcrypt.hashSync(password, 10);
  try {
    const info = db.prepare('INSERT INTO users (username, password) VALUES (?, ?)').run(username, hash);
    res.json({ success: true, userId: info.lastInsertRowid });
  } catch (err) {
    res.status(400).json({ error: 'Username already exists' });
  }
});

app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username);
  if (user && bcrypt.compareSync(password, user.password)) {
    const token = jwt.sign({ id: user.id, username: user.username }, SECRET, { expiresIn: '24h' });
    res.json({ success: true, token });
  } else {
    res.status(401).json({ error: 'Invalid credentials' });
  }
});

// WebSocket Relay Logic
// roomCode -> Set<WebSocket>. The free deployment runs one backend instance, so
// all room state can live in this process.
const rooms = new Map();

function roomPlayers(roomCode) {
  if (!rooms.has(roomCode)) return [];
  return [...rooms.get(roomCode)]
    .filter(client => client.readyState === WebSocket.OPEN && client.playerName)
    .map(client => client.playerName);
}

function uniquePlayerName(roomCode, requestedName, ws) {
  const base = String(requestedName || 'Player').trim() || 'Player';
  const existing = new Set(roomPlayers(roomCode).filter(name => name !== ws.playerName));
  if (!existing.has(base)) {
    return base;
  }

  let suffix = 2;
  while (existing.has(`${base} ${suffix}`)) {
    suffix += 1;
  }
  return `${base} ${suffix}`;
}

function broadcast(roomCode, message, exclude = null) {
  if (!rooms.has(roomCode)) return;
  const payload = JSON.stringify(message);
  rooms.get(roomCode).forEach(client => {
    if (client !== exclude && client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  });
}

function broadcastRoster(roomCode) {
  broadcast(roomCode, { type: 'players', players: roomPlayers(roomCode).slice(0, 4) });
}

wss.on('connection', (ws, req) => {
  let currentRoom = null;
  ws.playerName = null;

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data);
      
      // Basic Handshake to join a room
      if (msg.type === 'join') {
        currentRoom = msg.room;
        if (!rooms.has(currentRoom)) {
          rooms.set(currentRoom, new Set());
        }
        rooms.get(currentRoom).add(ws);
        ws.send(JSON.stringify({ type: 'players', players: roomPlayers(currentRoom).slice(0, 4) }));
        return;
      }

      if (msg.type === 'hello') {
        const assigned = uniquePlayerName(currentRoom, msg.name, ws).slice(0, 24);
        ws.playerName = assigned;
        ws.send(JSON.stringify({ type: 'hello_ack', name: assigned }));
        if (currentRoom) {
          broadcastRoster(currentRoom);
        }
        return;
      }

      // Relay message to everyone else in the same room
      if (currentRoom && rooms.has(currentRoom)) {
        broadcast(currentRoom, msg, ws);
      }
    } catch (e) {
      console.error('WS Error:', e);
    }
  });

  ws.on('close', () => {
    if (currentRoom && rooms.has(currentRoom)) {
      rooms.get(currentRoom).delete(ws);
      if (rooms.get(currentRoom).size === 0) {
        rooms.delete(currentRoom);
      } else {
        broadcastRoster(currentRoom);
      }
    }
  });
});

server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});

if (ENABLE_DISCOVERY) {
  const discovery = dgram.createSocket('udp4');

  discovery.on('message', (message, remote) => {
    const text = message.toString('utf8');
    if (text !== `HOLOORBIT_DISCOVER:${JOIN_CODE}`) {
      return;
    }
    const response = Buffer.from(`HOLOORBIT_HOST:${JOIN_CODE}:${PORT}`);
    discovery.send(response, remote.port, remote.address);
  });

  discovery.on('error', (error) => {
    console.warn(`Discovery disabled: ${error.message}`);
    discovery.close();
  });

  discovery.bind(DISCOVERY_PORT, () => {
    discovery.setBroadcast(true);
    console.log(`Discovery listening on udp://0.0.0.0:${DISCOVERY_PORT}`);
  });
}
