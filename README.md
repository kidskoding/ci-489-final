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

Or, after the virtualenv is active:

```bash
make install
make run
```

### 2. Multiplayer Relay (Optional)

If you want to host a collaborative session, start the relay server:

```bash
cd server
npm install
npm start
```

## Export Builds

Install the build tools once:

```bash
source .venv/bin/activate
make install-build
```

### Web Build

```bash
make web
```

This creates the browser build at `build/web/`. You can upload that folder to GitHub Pages, Netlify, itch.io, or any static web host. The included GitHub Actions workflow also builds and deploys this automatically when pushed to `main`.

For free multiplayer hosting, deploy the static game to GitHub Pages and deploy the `server/` app to Render Free using `render.yaml`. See `WEB_DEPLOYMENT.md` for the exact steps.

### Mac App Build

```bash
make mac-app
```

This creates `dist/Kepler Path.app`, which can be opened on macOS. If Gatekeeper blocks it on another Mac, right-click the app and choose Open, or codesign/notarize it for public distribution.

## Controls

### Navigation Bay (Ship)
- **WASD**: Move your crew member
- **E**: Interact with a console/terminal
- **T**: Start the interactive tutorial
- **1 / 2 / 3**: Jump to the Kepler Law 1, 2, or 3 labs

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

### Learning Modes
- **Training Sim**: Guided tutorial that walks students through selecting the star, measuring perihelion distance, pausing the orbit, and returning to ship.
- **Law 1 Lab**: Interactive orbit-shape challenge for eccentricity and ellipse foci.
- **Law 2 Lab**: Equal-time area capture challenge for sweep comparisons.
- **Law 3 Lab**: Planet preset comparison for the `T^2 / a^3` period relationship.

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
