# Interactive Tutorial Redesign

**Date:** 2026-05-19  
**Branch:** learning-modes-tutorial  
**File:** `game.py`

## Goal

Replace the 4-step passive tutorial with a 7-step guided experience. Each step highlights the target UI element with a pulsing ring and blocks progression until the correct action is taken.

## Data Model

New `TutorialStep` dataclass at module level:

```python
@dataclass
class TutorialStep:
    message: str
    event: str        # string key consumed by advance_tutorial
    target: str | None  # body name, "nav", or None
```

New module-level constant `TUTORIAL_STEPS: list[TutorialStep]` replaces the hardcoded list inside `tutorial_message()`.

## Steps

| # | Message | Event | Highlight target |
|---|---|---|---|
| 1 | "Click the Red Dwarf star to select it." | `star` | `"Red Dwarf"` |
| 2 | "Now click Aphelion — the farthest orbit point — to measure the star's distance." | `aphelion_measure` | `"Aphelion"` |
| 3 | "Red Dwarf is pre-selected. Now click Perihelion — the nearest point." | `perihelion_measure` | `"Perihelion"` |
| 4 | "Perihelion is much closer. The star sits at a focus, not the center — Kepler's First Law! Click anywhere to continue." | `continue` | `None` |
| 5 | "Press Space to pause and resume the orbit." | `pause` | `None` |
| 6 | "Press + or − to zoom in and out." | `zoom` | `None` |
| 7 | "All done! Click the nav icon to return to the ship." | `nav` | `"nav"` |

## Visual Highlight

New method `draw_tutorial_highlight()` called from the sim draw loop when `tutorial_active` is `True`.

- Looks up current step's `target` from `TUTORIAL_STEPS[self.tutorial_step]`
- If target is a body name: `pos = self.world_to_screen(self.bodies()[target].pos)`
- If target is `"nav"`: `pos = (978, 38)`
- If target is `None`: no-op
- Draws two concentric pulsing rings in ACCENT color:
  - Outer: `radius = body.radius + 14 + pulse`, width 2
  - Inner: `radius = body.radius + 8`, width 1, alpha ~120
  - `pulse = int(math.sin(pygame.time.get_ticks() / 300) * 4)`
- Nav badge highlight uses fixed radius 36 (slightly larger than badge's 28)

## Click Handler Changes

In tutorial mode, the click handler:

- **Step 1 (star):** click Red Dwarf → `advance_tutorial("star")`; Red Dwarf stays selected
- **Step 2 (aphelion_measure):** `selected == "Red Dwarf"` + clicked Aphelion → record measurement, `advance_tutorial("aphelion_measure")`
- **Step 3 (perihelion_measure):** clicked Perihelion (Red Dwarf auto-reselected in step 2's advance) → record measurement, `advance_tutorial("perihelion_measure")`
- **Step 4 (continue):** any body click or Space → `advance_tutorial("continue")`
- **Wrong-click redirect:** only when `target is not None` — if clicked body is not the highlighted target, set `self.notice = f"Try clicking {target} instead."`; do not record measurement or advance
- **Step 4 (continue, target=None):** any click on any body advances — no redirect

## Key Handler Changes

- `K_EQUALS` / `K_PLUS` and `K_MINUS` already handle zoom (`self.zoom ±0.08`); add `advance_tutorial("zoom")` call on those keys in tutorial mode
- Space already fires `advance_tutorial("pause")`; when step 4 is active (expected event is `"continue"`), Space should also advance — handled by checking `expected[tutorial_step] == "continue"` before the pause branch

## `advance_tutorial` Changes

- `expected` list updated to 7 event strings matching `TUTORIAL_STEPS`
- After advancing past step 2 (aphelion_measure): `self.selected = "Red Dwarf"` (auto-reselect for step 3)
- `self.lesson_success` triggers when `tutorial_step >= len(TUTORIAL_STEPS)`

## `tutorial_message()`

Returns `TUTORIAL_STEPS[self.tutorial_step].message` (or completion message if past end). No hardcoded list.

## Progress Display

`draw_lesson_panel` uses `len(TUTORIAL_STEPS)` instead of hardcoded `4`:
```python
self.screen.blit(self.small.render(f"Progress: {progress}/{len(TUTORIAL_STEPS)}", True, ACCENT), ...)
```

## Draw Loop Integration

In `draw_scene`, after drawing bodies and before drawing the panel, call `self.draw_tutorial_highlight()` when `self.tutorial_active and self.screen_state != "ship"`.
