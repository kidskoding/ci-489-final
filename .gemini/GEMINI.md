# GEMINI Notes

This repo is a Pygame port of the HoloOrbits / Kepler Path prototype.
The current goal is a presentation-ready multiplayer MVP, not full Figma parity.

## What Is Implemented

- Start menu with:
  - player name entry
  - `Host Game`
  - `Join Game`
- Join code flow:
  - visible join code is `CI-489-DEMO`
  - LAN discovery is attempted first
  - direct host IP entry still works as fallback
- Multiplayer MVP:
  - joined players appear in the crew panel
  - remote crew sprites appear in Navigation Bay
  - player movement syncs between clients
  - opening consoles syncs
  - shared orbit measurements sync
- Navigation Bay:
  - crew-facing ship map
  - `Crew Lounge` console for ready gating
  - `Mars Observe`
  - `Mars Measure`
- Orbit / measure screen:
  - orbit path rendering
  - body labels
  - click-two-bodies measurement interaction
  - mission log
- Presentation helpers:
  - `0` or `Home` resets state
  - `PRESENTATION_GUIDE.md`
  - `MULTIPLAYER_NOTES.md`
  - `run_presentation.sh`

## Important Behavior

- The crew must gather at `Crew Lounge` and press `E` to mark ready.
- The host is expected to take everyone into the next task after the crew is ready.
- `Mars Measure` is the main collaborative interaction for the poster demo.
- The current build is intentionally focused on the smallest complete multiplayer slice.

## What We Deliberately Skipped

- Full Figma frame-by-frame coverage
- Shuttle color selection sequence
- Door-fragment ordering puzzle
- Wiring minigame
- Full voting/calibration/mission branches
- Full Nova dialogue trees
- Full role-specific analyst flows from the longer prototype

## Visual Direction

The app was adjusted toward the Figma direction using:

- cyan-on-dark sci-fi UI
- large objective pill in the top left
- circular nav icon top right
- large bottom console/dialog bar
- dark ship map and orbit stage

## Files To Know

- [game.py](./game.py): main game, menu, networking, ship, orbit, and interaction flow
- [main.py](./main.py): launcher
- [orbit.py](./orbit.py): orbital math
- [PRESENTATION_GUIDE.md](./PRESENTATION_GUIDE.md): how to present it tomorrow
- [MULTIPLAYER_NOTES.md](./MULTIPLAYER_NOTES.md): host/join notes

## How To Run

Normal launch:

```bash
python3 main.py
```

Fallback presentation launcher:

```bash
./run_presentation.sh
```

## Multiplayer Flow

1. Start both laptops on the same Wi-Fi.
2. Launch the app on both.
3. Type a player name.
4. On one laptop, choose `Host Game`.
5. On the other laptop, choose `Join Game`.
6. Enter `CI-489-DEMO`.
7. If discovery fails, type the host IP instead.
8. Gather at `Crew Lounge` and press `E` when ready.
9. Host opens `Mars Measure`.
10. Record a measurement and verify it syncs.

## Testing

These checks should stay green:

```bash
python3 check_demo.py
python3 -m unittest discover -s tests
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile game.py main.py check_demo.py orbit.py tests/test_orbit.py
```

## Known Caveats

- LAN discovery depends on campus Wi-Fi allowing local traffic.
- If the network blocks discovery, the host IP fallback is still available.
- Remote sprites are lightweight synced avatars, not full per-frame animation replication.
- This is a presentation MVP. Do not expand scope unless it clearly helps the demo.

## Guidance For Future Work

- Keep the Multiplayer MVP stable first.
- Preserve the start menu and join code flow.
- Keep `Crew Lounge` as the ready gate.
- Add only changes that make the visitor experience easier to understand or harder to break.
- Avoid reintroducing tutorial-only or extra mission branches unless presentation time allows it.
