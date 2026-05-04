# Local Multiplayer Setup

Use this if both laptops are on the same Wi-Fi.

## Normal Menu Flow

Start the game on both laptops:

```bash
python3 main.py
```

On the first laptop, click **Host Game**.

On the second laptop, click **Join Game**, type:

```text
CI-489-DEMO
```

Then press `Enter`.

The game will try to find the host automatically on the local network.

## If Join Code Does Not Work

If campus Wi-Fi blocks local discovery, type the host IP instead of the join code.

Find the host IP on the host laptop:

```bash
ipconfig getifaddr en0
```

## Command-Line Backup

Host laptop:

```bash
python3 main.py --host-session --name Presenter
```

Visitor laptop:

```bash
python3 main.py --join HOST_IP --name Visitor
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
