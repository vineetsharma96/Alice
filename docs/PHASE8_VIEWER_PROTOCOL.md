# Phase 8 viewer and protocol

The renderer is a presentation client of the existing C++ world. It does not implement a second physics engine, schedule agent actions, generate dialogue or infer success from animation. Visual heights, humanoid glyphs and vessel shapes are illustrative. Native mechanics remain two-dimensional.

## Engine choice and local assets

The profiled machine has an i3-6006U, 4 GiB RAM and Intel HD Graphics 520. Three.js 0.180.0 with WebGL2 was selected as a small browser renderer over Unreal. Epic's current [hardware recommendations](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine) include 32 GB RAM and 8 GB graphics RAM, well above this machine. This comparison is a feasibility decision, not a measured Unreal benchmark. R9's [Unreal C++ documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/programming-with-cplusplus-in-unreal-engine) remains optional migration context.

`scripts/vendor_three.py` fetches the pinned r180 browser modules and OrbitControls. The local manifest records original and distributed SHA-256 hashes. OrbitControls' bare `three` import is changed to the local module path. The MIT license and attribution are preserved in `underworld/web/vendor/LICENSE.three`. Total vendored source is 759832 bytes; no Node package installation, CDN, remote font, model or speech dependency is required at runtime. See [WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html) and [OrbitControls](https://threejs.org/docs/pages/OrbitControls.html).

## Launch and operating modes

```powershell
# Existing saved preview, starts paused:
.venv/Scripts/python.exe -m underworld observe --db data/phase8-handoff-20261020/run.sqlite --port 8765
# Open http://127.0.0.1:8765/viewer

# Read-only attachment, including while an isolated unattended worker owns the run:
.venv/Scripts/python.exe -m underworld observe --db data/phase7-reviewed/population-8/run.sqlite --port 8766 --read-only
```

An already running preview occupies its port; stop that owned process before starting another on the same port. The legacy 2D observer remains at `/`. `scripts/phase8_demo.py` creates the original guided fixture once and refuses to overwrite it. Its book, avatar message and initial native read are explicitly authored setup, documented in `fixture.json`. Later actions use the existing utility policy and native validation, not a scripted cinematic outcome.

Interactive mode uses the existing local observer controller. Resume/pause, one-tick step and 1/5/20x target speed go through `/api/control`; targets do not promise achieved throughput or skip ticks. This is the manual development controller, not an AppContainer worker. With cognition disabled, the supplied preview requires no inference service. Use `--read-only` to observe an unattended AppContainer run without weakening its isolation or starting a competing writer. Read-only mode never calls recovery or starts a writer and rejects every mutation endpoint, even with valid session tokens.

## Snapshot/event protocol

`GET /api/viewer?agent=agent-1&after=0` returns `protocol: underworld.viewer/1`. All run state, selected-agent perception, own memory, action annotations, events and operator history come from **one SQLite read transaction**. The physical native state and policy checksum remain authoritative. Reading does not advance time or modify the DB.

| Field | Meaning |
|---|---|
| `stream_id` | Run ID plus branch ID; reset event presentation when it changes |
| `snapshot` | Native world snapshot plus authoritative state hash, branch/law identity and retained replay root |
| `selected` | The requested inhabitant's native observation and recent action receipts |
| `mind` | That inhabitant's identity and bounded own-accessed episodes/relationships, using existing episodic-memory settings |
| `events` | At most 96 retained events with sequence strictly greater than the requested cursor |
| `event_window` | Earliest available sequence, latest native sequence, returned cursor, gap and more flags |
| `operator_history` | Most recent 64 operator journal entries, newest first; UI shows eight |
| `controls` | Paused state, target speed, writer error and read-only flag |
| `performance` | Actual simulated duration advanced and wall time spent in observer advancement; their ratio is work throughput |
| `coordinates` | Explicit 2D-to-3D mapping and illustrative-height declaration |

Tick and event counters remain decimal strings. The journal cursor is nonnegative and within SQLite's signed integer range. Invalid agents/cursors fail with a JSON error. A cursor ahead of the head, or behind the retained window, sets `gap`; the packet still contains a complete current snapshot. `more` requests prompt catch-up polling. No lost event is reconstructed or invented. The UI retains 96 event records and shows 32. Native event counters remain exact even when presentation history expires.

The browser polls every approximately 900 ms, or 100 ms while catching up. Concurrent polls do not overlap. A failed connection freezes the last snapshot and retries reads; it never queues or automatically repeats a mutation. A new session refreshes its control tokens. Camera motion, selection, quality changes, visibility changes, context recovery and reconnection cannot write simulation state.

This is a privileged **operator** feed. It includes global world diagnostics and operator history. It is not a provider context or an inhabitant's omniscient sensory view. Selected-agent reports and memory remain source bounded: an unread book is shown as unread for that inhabitant. Operator history may contain the operator's original book text, explicitly labeled as privileged history. Existing provider-context construction and native read gates are unchanged.

## Coordinates and operator interaction

One world metre is one renderer unit. Native `(x, y)` maps to Three.js `(x, visual_height, -y)`; the ground is height zero. Ground picking reverses this mapping and fills the intervention form. It does not move an entity. Bounds/radii come from the authoritative snapshot. Dead/departed states, health indicators and busy markers derive from native body/pending-action data. Mesh materials and heights do not define collision, reach, energy or mass.

Drag or touch to orbit, scroll/pinch to zoom and right-drag to pan. Focus and fit operate only on the camera. WASD moves the camera while the viewport has keyboard focus; Shift increases camera speed. The operator avatar is a real native `operator_avatar` entity if one exists. The existing `avatar_message` intervention positions it and delivers the operator's text; this is an explicit recorded placement/message, not a new walking or 3D movement mechanic.

Book placement, material introduction, avatar communication and broadcast use the original `teaching.intervene` channel. Guided mode, paused state, separate operator token, run/branch IDs, current observation version and native collision/resource constraints still apply. Closed mode rejects world interventions. Exact source mass/energy inputs and event references remain journaled. An attempted avatar placement at the central rock was rejected with `intervention collision` and left the hash unchanged.

## Safety, rendering and measurement

The server remains loopback-only with exact Host/Origin checks, separate observer/operator tokens, explicit static-file allowlist and a self-only content security policy. Source text is assigned through `textContent` or form values, never executed as HTML. A literal script-containing book was stored and displayed as operator history without execution. Browser response loss leaves an intervention ID for history inspection; no silent retry creates a duplicate command.

Low quality caps presentation at 30 fps and uses `0.8 * min(devicePixelRatio, 1.25)`; Standard caps at 60 fps and `min(devicePixelRatio, 1.25)`. No MSAA, postprocessing, texture assets, dynamic shadows or autonomous camera motion is enabled. Geometry/materials are shared; replaced grid geometry and GPU resources are disposed. Rendering pauses when the document is hidden; visibility changes reset measurement windows. Reduced motion disables orbit damping. WebGL failure offers the existing 2D observer and leaves DOM inspection available. Context loss freezes graphics; context restoration redraws current snapshots without advancing physics.

Render fps and frame intervals use the actual presentation loop, with a rolling 300-frame sample. They include the configured cap and browser scheduling; they are not GPU-only timings or a maximum capability benchmark. Live simulation throughput is measured independently from native clock progression over wall time. The controller's work ratio excludes deliberate pacing/paused time, so it differs from observed end-to-end progress. Headless parity uses identical action requests/ticks; it is not a claim that viewer polling has zero CPU cost.

See `STATUS.md` and `artifacts/phase8_browser_checks.json` for measured Intel HD 520 results. Short foreground browser samples do not validate sustained thermals, all browser/driver combinations, large worlds or mobile GPU performance. True 3D physics, speech, long-horizon experiments and Phase 9 remain separately scoped.
