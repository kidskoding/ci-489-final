# Kepler Path

A collaborative multiplayer astronomy simulation game built with Pygame and pygbag.

## Live Links
- **Play:** [kidskoding.itch.io/ci489-final](https://kidskoding.itch.io/ci489-final)
- **WebSocket Relay:** [ci-489-final.onrender.com](https://ci-489-final.onrender.com)

## Architecture

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Game client | Pygame + pygbag | Browser-playable simulation |
| WebSocket relay | Node.js (Render) | Multiplayer room sync |
| CI/CD | GitHub Actions + butler | Auto-deploy to itch.io on push |

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Multiplayer Relay (local)

```bash
cd server
npm install
npm start
```

## Web Build

```bash
make install-build
make web
```

Output goes to `build/web/`. GitHub Actions builds and uploads to itch.io automatically on every push to `main`.

## Mac App

```bash
make mac-app
```

Creates `dist/Kepler Path.app`.

## Controls

### Navigation Bay
| Key | Action |
|-----|--------|
| WASD | Move |
| E | Interact with console |
| T | Start interactive tutorial |
| 1 / 2 / 3 | Jump to Kepler Law labs |

### Orbital Simulation
| Key | Action |
|-----|--------|
| Space | Pause / Resume |
| + / - | Zoom |
| Left / Right | Rotate |
| M | Measure mode |
| O | Observe mode |
| S | Save measurements |
| Backspace | Delete last measurement |
| Tab / Q | Return to ship |
| R | Reset simulation |

## Testing

```bash
PYTHONPATH=. pytest
```

## License
CI-489 Final Project — UIUC
