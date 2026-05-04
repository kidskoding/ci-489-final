## Previous version with dialogues can be found in Archive-2024-Feb-26

## Pygame port

The new standalone port lives in `pygame_port/`. It starts in a spaceship
navigation bay using the ship map, player sprites, and sci-fi UI assets, then
opens the Kepler orbit tools through ship consoles. It keeps the core orbit,
play/observe/measure modes, selectable bodies, distance records, and CSV export
in Python/Pygame. All runtime textures now live under `pygame_port/assets/`.

Run it with:

```bash
cd pygame_port
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python check_demo.py
python main.py
```

Controls:

- `WASD`: move through the Navigation Bay
- `E`: interact with a nearby console
- `Tab` or `Q`: return from an orbit activity to the ship
- `Space`: pause/resume orbit activity
- `P`: play mode inside orbit activity
- `O`: observe mode inside orbit activity
- `M`: measure mode inside orbit activity
- Click two bodies in measure mode to record distance
- `+` / `-`: zoom
- `Left` / `Right`: rotate view
- `S`: save measurements to `pygame_port/logs/`
- `Backspace`: delete latest measurement
- `R`: reset
- `Esc`: quit

Run the orbit tests with:

```bash
cd pygame_port
python3 -m unittest discover -s tests
```

Start Codex with the project-local Figma MCP config from inside the port:

```bash
cd pygame_port
CODEX_HOME=$PWD/.codex codex
```
