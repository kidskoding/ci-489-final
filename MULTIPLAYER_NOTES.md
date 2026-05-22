# Local Multiplayer Setup

Use this if both laptops are on the same Wi-Fi.

## Normal Menu Flow

Start the game on both laptops:

```bash
python3 main.py
```

On the first laptop, click **Host Game**. In local Python mode, the host starts
the relay inside the game process and advertises it on the Wi-Fi network.

On the second laptop, click **Join Game**, type:

```text
CI-489-DEMO
```

Then press `Enter`.

The game will try to find the host automatically on the local network.

## Optional Standalone Relay

You can still run a standalone relay for debugging:

```bash
python3 server.py
```

or:

```bash
cd server
npm install
npm rebuild
node server.js
```

If `better-sqlite3` is not rebuilt for your Node version, the Node server falls
back to in-memory auth so WebSocket multiplayer can still run. Local discovery
is enabled by default for `node server.js`. Keep `ENABLE_DISCOVERY=false` only
on hosted services such as Render.

## If Join Code Does Not Work

If campus Wi-Fi blocks local discovery, type the host IP instead of the join code.
The game will use port `3000` automatically.

Find the host IP on the host laptop:

```bash
ipconfig getifaddr en0
```

## Command-Line Backup

Host laptop:

```bash
python3 main.py --host-session --name Presenter --port 3000
```

Visitor laptop:

```bash
python3 main.py --join HOST_IP --name Visitor --port 3000
```

## What Syncs

- Joined players in the crew panel
- Player sprites moving in Navigation Bay
- Opening Mars Measure
- Recorded measurements
- Returning to Navigation Bay

## Fallback

If campus Wi-Fi blocks laptop-to-laptop connections, use one laptop:

```bash
./run_presentation.sh
```

The single-laptop mode still shows the collaborative team flow in the UI.
