# Kepler Path Presentation Guide

## Run

```bash
python3 main.py
```

## Two-Laptop Multiplayer

Start the game on both laptops:

```bash
python3 main.py
```

On the first laptop, click **Host Game**.

On the second laptop, click **Join Game**, type `CI-489-DEMO`, then press `Enter`.

If the join code does not work on campus Wi-Fi, type the host IP instead. Find it on the host Mac with `ipconfig getifaddr en0`.

What syncs:

- Crew list / joined players
- Player sprites moving in Navigation Bay
- Opening Mars Measure
- Recorded measurements
- Returning to Navigation Bay

Keep both laptops on the same Wi-Fi. If networking is unreliable, use the normal one-laptop run command above.

## Reliable Demo Controls

- `0` or `Home`: reset to a clean starting state.
- `Esc`: quit.

## Visitor Flow

1. Start in Navigation Bay.
2. Move with `WASD` or click a console.
3. Press `E` near Mars Measure.
4. Let visitors observe the team-ready state.
5. Ask visitors which two orbit points they want to compare.
6. Click two bodies to record the measurement.
7. Point out the mission log.

## Presenter Script

This prototype is about team coordination in an astronomy learning task. Students begin together in the Navigation Bay, choose a console, wait for the team to be ready, then collaborate on an orbital measurement.

For the poster session, the prototype runs on one laptop, so team presence is represented in-app through the crew panel and ready states. The intended full experience is collaborative: students discuss which orbital bodies to compare, make a shared measurement, and record it in the mission log.

## What To Point Out

- Navigation Bay: the hub for choosing group activities.
- Crew panel: shows the team context and readiness.
- Crew Lounge: quick group check-in before the mission.
- Nova/console dialog: guides the group through the task.
- Mars Measure: lets visitors measure orbital distances.
- Mission Log: records the team result.

## If Something Goes Wrong

Press `0` or `Home` to reset the prototype before the next visitor.
