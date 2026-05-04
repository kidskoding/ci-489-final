# Kepler Path: Pygame Edition

A collaborative astronomy simulation and exploration game.

## 🚀 Live Production Links
- **Game simulation (Static):** [https://kidskoding.github.io/ci-489-final/](https://kidskoding.github.io/ci-489-final/)
- **Mission Control (Login/Multiplayer):** *[Deploy the `/server` folder to Render/Railway to get this URL]*

## Architecture

The project consists of three main components:
- **Pygame Client:** The core simulation, orbit mechanics, and ship navigation.
- **Node.js Relay Server:** A WebSocket-based relay server that enables real-time collaboration between multiple players.
- **Web Build:** Support for running the game in the browser via `pygbag`.

## Quick Start

### 1. Client Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### 2. Multi-player Relay (Optional)

If you want to host a collaborative session, start the relay server:

```bash
cd server
npm install
node server.js
```

## Controls

### Navigation Bay (Ship)
- **WASD**: Move your crew member
- **E**: Interact with a console/terminal

### Orbital Simulation
- **M**: Measure mode (Click two bodies to record distance)
- **O**: Observe mode (Inspect labels)
- **P**: Play mode (Active orbit animation)
- **Space**: Pause/Resume simulation
- **+ / -**: Zoom in/out
- **Left / Right**: Rotate view
- **S**: Save measurements to `logs/`
- **Backspace**: Delete latest measurement
- **Tab / Q**: Return to Ship
- **R**: Reset simulation
- **Esc**: Quit

## Assets & Clean Migration

The project has been fully migrated from Unity. All necessary assets are now organized in the `assets/` directory:
- `assets/planets/`: Celestial body textures.
- `assets/player/`: Character animation frames.
- `assets/ship/`: Environment maps.
- `assets/ui/`: Collaborative interface elements.

## Development & Testing

Run the suite of orbital mechanics and game state tests using pytest:
```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Verify asset loading and demo integrity:
```bash
python3 check_demo.py
```

## License
CI-489 Final Project - UIUC.
