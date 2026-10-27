# Alice living-world dashboard — 24 October 2026

## What changed

The existing integrated-life observer now opens a complete observer and
control dashboard at the same `life_control.py` URL. It uses the existing
native weather/life SQLite head and the existing control writer; it does not
create a second simulation loop or invent state in the browser.

Start it with:

```powershell
python -m underworld.life_control --db data/my-life.sqlite --port 8782
```

Open `http://127.0.0.1:8782/`.

## Dashboard areas

- Persistent status strip: run state, seed, elapsed simulated time, Day N,
  world-clock time, season, tick, configured tick duration, observed speed and
  population categories.
- Shared 2D/3D observation: the 2D map and existing Three.js renderer consume
  the same native snapshot. Switching views preserves the selected identity and
  does not advance time.
- Inhabitant inspector: stable ID, current task, recorded body values, carried
  inventory, recent native receipts and recorded decision influence.
- Mood chart: slow stress, mood valence or arousal from retained life-operation
  updates. Other inhabitants remain separate traces; a same-measure population
  mean and range are aligned by native tick, with day boundaries and recorded
  event markers. Unrelated dimensions are never averaged together.
- Event timeline: bounded, searchable presentation of retained mood, tick,
  decision and native events. Rows with a recorded actor can focus the
  inspector. Explanations use recorded appraisal codes and evidence
  references; causes are not inferred when the runtime did not record them.
- Directed relationship graph: trust, affection, familiarity and partnership
  layers retain A → B direction. Reverse edges are shown separately when they
  exist. Target-specific anger is explicitly unavailable in this runtime.
- Weather panel: current native weather, temperature, rainfall, wind, daylight,
  season and selected-agent exposure. Guided worlds can submit a native weather
  override with duration; the override is journaled by the existing weather
  runtime and expires back to natural weather. Closed worlds explain why the
  control is unavailable.
- Advanced view: formatted dashboard JSON with copy/download controls.

## Control behavior

The existing life writer now supports:

- pause/resume;
- one tick and one inhabitant turn;
- speed selection without changing the physical timestep;
- bounded batch stepping with completed/remaining state;
- run-until simulated time;
- cancellation at the next safe tick boundary;
- guided weather override requests.

Only one stepping job can be active. A bounded job finishes paused. A pause
request during a job takes effect after the current committed tick. Every
native write still goes through `life_store.commit`, preserving the existing
journal and replay contract. `run_until` accepts only targets aligned to the
native timestep; unaligned targets are rejected instead of being silently
overshot.

## Explicit unsupported fields

The dashboard marks these instead of fabricating them:

- microbial individual counts;
- reproductive births/deaths when no lifecycle sidecar is attached;
- target-specific anger;
- biological sex/gender/life-stage fields absent from native UW10W;
- reserved inventory, tool durability, spoilage and ownership absent from the
  current native observation;
- immediate “return to natural” weather clearing, because the native runtime
  exposes duration-based forcing rather than a separate clear command.

## Verification

Focused backend and dashboard checks:

```text
python -m pytest -q tests/test_life_control.py
5 passed in 9.13s

python -m pytest -q tests/test_integrated_life.py tests/test_life_control.py tests/test_living_world_bridge.py
17 passed in 51.46s

python -m py_compile underworld/life_control.py underworld/life_viewer.py tests/test_life_control.py
passed

node --check underworld/web/dashboard.js
passed

npm run lint
node --check server.js
passed
```

Browser verification used the actual local writer and database. It confirmed:

- dashboard telemetry loads with seed 61, three inhabitants and native tick 0;
- a two-tick batch advances to exactly tick 2 and returns paused;
- 2D → 3D switching creates the existing renderer canvas without changing the
  selected inhabitant or tick;
- no browser console errors occurred after the dashboard loaded (the only
  prior request was the optional missing favicon on the old process);
- screenshot: `artifacts/dashboard_ui_smoke.png`.

The whole-tree command completed with the required native runtime environment:

```text
export UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe"; python -m pytest -q
534 passed, 355 subtests passed in 738.52s (0:12:18)
```

The dashboard is an observer and experiment-control surface. It is not
evidence of intelligence, emotional experience or a completed lifecycle model.
