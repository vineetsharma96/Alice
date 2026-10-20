# Phase 8 complete - 2026-10-20

A modest explorable 3D viewer is implemented and verified. **The C++ world remains authoritative and its mechanics remain 2D.** Longer multi-seed horizons, true 3D mechanics, speech and Phase 9 remain deferred.

Open the running paused handoff preview at **http://127.0.0.1:8765/viewer**. It uses `data/phase8-handoff-20261020/run.sqlite`, an explicitly authored guided lab fixture, paused at tick 15 when handed off. The earlier `phase8-preview` file had advanced after the original checks; it is preserved, not reset. The 2D observer remains at `/`.

Workspace: `C:\Users\abc\Documents\ChatGPT\UnderWorld`, branch `codex/phase-8`. Previous status is preserved in `PHASE7_REPORT.md`. Earlier reports, saved experiments and evidence remain. The repository still has no initial commit; no commit or push is claimed. The original project brief remains unchanged, SHA-256 `306e5eafba0f7c53b49002ec8fcd276dc736efb791ede1991f64e685773e84d6`.

## Delivered

- Local Three.js 0.180.0 / WebGL2 rendering with orbit, zoom, pan, focus, fit and viewport-focused WASD camera navigation. All scene positions come from authoritative snapshots. No renderer-side physical extrapolation, state mutation or hidden world stepping is implemented.
- Inspectable native inhabitants, materials, books, thermal vessels/tools and operator avatar; health/busy indicators and selected-agent needs/actions derive from native body and pending-action data.
- Source-bounded memory and book-read provenance, recent native action receipts, privileged operator history and retained event traces. Unread books remain unread for the selected inhabitant; operator history is labeled separately from inhabitant knowledge.
- The existing validated guided intervention channel for book/material placement, avatar positioning plus text communication and broadcast. Pause/step/resume and target-speed controls use the existing observer writer. Camera motion and ground picking do not move world entities.
- A documented `underworld.viewer/1` feed, projected from one SQLite read transaction. Full snapshots, bounded event cursors, gap/catch-up handling and session reconnection preserve the source boundary.
- Read-only attachment to an externally owned run, including an AppContainer worker; no competing writer or recovery is started, and valid-token mutation attempts remain rejected.
- Locally vendored, checksum-pinned MIT browser assets; no runtime CDN, downloaded font, Node server, model download or speech service. Low/Standard quality caps, reduced-motion support, responsive layouts and WebGL/context-loss fallbacks.

[PHASE8_VIEWER_PROTOCOL.md](PHASE8_VIEWER_PROTOCOL.md) documents operating modes, security, cursor semantics, coordinate mapping, resource budgets and limitations. [PHASE8_DESIGN.md](PHASE8_DESIGN.md) records the audit/design choices. README, architecture, model limits and references are updated.

## Authority and compatibility

Native `(x,y)` metres map to renderer `(x,illustrative_height,-y)`. Mesh heights and humanoid/vessel glyphs are visual extrusion, not 3D collision, human anatomy or new material laws. The operator avatar is the actual native entity; the existing `avatar_message` command positions it and communicates the entered text. No new walking/3D movement engine is implied.

The durable runtime is unchanged: package 0.8.0, native **UW6**, SQLite **user_version 7**. Phase 7 saved runs remain compatible with their existing native/runtime identities. Viewer sources have a separate content manifest rather than changing persisted world identities:

- Native build: `1955dda0d7cd3350527e937dc626a1d3d5dcdb808b82a7207c1102db2957dfbd`.
- Durable Python runtime: `995842ce19b4f6cbc5c2180dc41d78e661ec691e33405ec54bfb2778044e4e81`.
- Viewer source build: `2b9d949b2baa3ae1a7100e12979a0e3022eb2a710f955bfb68c7f7282678d93d` (`artifacts/phase8_manifest.json`).

Interactive time controls use the existing manual development controller. To preserve Phase 7's worker OS-network isolation, attach with `observe --read-only` to a separately launched AppContainer run. The browser's self-only asset/network policy and loopback-only server do not turn the manual controller into an AppContainer. No broader isolation claim is made.

## Verification

`artifacts/phase8_checks.json`: **110 Python tests + 4 native CTest checks passed**. All 102 prior cases remain green; eight new cases cover byte-read-only packets, single-commit consistency during external advancement, selected-agent source access, identical recorded outcomes with the viewer feed on/off, cursor catch-up/gaps and invalid values, HTTP assets/tokens/operator validation, read-only attachment under an existing writer lease, and pinned asset/license integrity. Python tests took **86.736 s** internally; the captured subprocess wall time was **87.54 s**. CTest passed all four cases (0.20 s internally, 0.52 s captured subprocess wall time).

```powershell
.venv/Scripts/python.exe scripts/vendor_three.py
.venv/Scripts/python.exe scripts/phase8_demo.py
$env:PATH='C:\mingw64\bin;'+$env:PATH
.venv/Scripts/python.exe scripts/verify.py --core build/underworld_core.exe --ctest C:/mingw64/bin/ctest.exe
.venv/Scripts/python.exe scripts/phase8_manifest.py
```

The existing native build was reused; no C++ physics rebuild or database migration was needed. Assets total **759832 bytes**, including the retained MIT license and the locally redirected OrbitControls import. Unreal was not installed or benchmarked. Its published recommended 32 GB RAM / 8 GB graphics RAM informed selecting a lighter renderer for this 4 GiB Intel HD 520 machine.

## Browser acceptance and traces

`artifacts/phase8_browser_checks.json` and `phase8_browser_action_parity.json` retain the browser results and native comparisons:

- WASD changed the camera while the world tick and hash stayed unchanged. Ray selection chose an actual inhabitant. Picking the ground centre filled native coordinates **(8.00, 8.00)**. Attempted avatar placement there hit the native central rock and returned `intervention collision`, leaving the hash unchanged.
- An actual browser-issued book placement was replayed headlessly from an identical saved head. Both hashes matched. Browser step/resume/pause subsequently advanced to **tick 85**; replaying exactly those ticks headlessly again produced identical native/policy hash `75bfbaa5b8426d1db8706a8275082dfa0bc8f0b3d9d7ca3a92b65406d1308c91`. Both saved worlds replay successfully.
- Agent 8 saw the fixture book as unread; agent 1 saw the real accessed report, source event **16**, origin **1**. The initial successful read is authored fixture setup, not spontaneous learning. A script-containing book string was displayed literally in privileged operator history without execution.
- After a real server stop/restart, the client froze the last snapshot at **tick 16**, reconnected with the same hash, refreshed its session and successfully performed an explicit step to **17**. No mutation was automatically replayed.
- A read-only 32-inhabitant viewer observed a separate AppContainer worker advancing from **0 to 2** ticks. The worker's public/private outbound denial probes passed and its profile cleaned up. Viewer mutation controls stayed disabled (`phase8_readonly_isolation.json`).
- Forced graphics-context loss displayed the fallback, restored the renderer and preserved the exact physical hash throughout. Forced WebGL startup failure offered the 2D observer and retained DOM inspection. Desktop **1440x900**, mobile **390x844** and reduced-motion checks passed without horizontal overflow. Screenshots were visually inspected.

One early browser navigation raced server startup and was retried after a successful HTTP readiness check. Connection errors during intentional shutdown, context-loss diagnostics and the intentional 400 collision response are expected test evidence, not unexplained application failures. The full Python suite passed on its first completed Phase 8 run.

## Rendering and simulation performance

Actual foreground browser samples reported **ANGLE / Intel HD Graphics 520 / Direct3D11**, not a software renderer. Fixed geometry, zero texture assets and no MSAA/shadows/postprocessing keep the scene modest. DPR was 1 on the profiled browser; Low used 0.8 and Standard 1.0. Measurements are short roughly 3-4 second samples with explicit caps, not maximum-GPU or sustained thermal claims.

| Presentation sample | Actual render fps | Frame interval p50 / p95 | Draw calls | Triangles | Canvas backing pixels |
|---|---:|---:|---:|---:|---|
| 8 inhabitants, Low, simulation advancing | 30.0 | 33.3 / 33.4 ms | 55 | 1904 | 756 x 486 |
| 8 inhabitants, Standard, paused | 60.0 | 16.7 / 16.8 ms | 53 | 1744 | 946 x 608 |
| 32 inhabitants, Low, paused | 30.0 | 33.3 / 33.5 ms | 117 | 4468 | 756 x 486 |
| 32 inhabitants, Standard, paused | 59.99 | 16.7 / 16.8 ms | 117 | 4468 | 946 x 608 |

During the 8-inhabitant Low sample, the native world advanced **68 physical ticks / 13.6 simulated seconds** over **4.185 wall seconds**, or **3.25 observed simulated s/wall s**, while rendering remained approximately 30 fps. The requested speed was 5x; it was a target, not an achieved guarantee. Cumulative controller advancement was 13.8 simulated seconds in 2.9045 seconds spent doing advancement work (**4.75 simulated s/work wall s**); this excludes pacing/paused time and is intentionally separate from observed progress and rendering fps. The scene has thermal/cultural mechanics and dt=0.2 s, so this is not directly comparable to Phase 7's dt=1 s survival benchmarks.

The clean handoff's actual Python worker PID **4992** peaked at **32.38 MiB** working set when sampled. Earlier samples in the browser artifact were venv launcher processes and have been relabeled; they are not simulation-worker memory. Browser/GPU total memory was not measured. Renderer resource counts were six geometries and zero textures. No claim is made about complete machine peak RAM or VRAM.

## Handoff and deferred work

The paused clean preview is `data/phase8-handoff-20261020/run.sqlite`; process identities and source ID are recorded in `artifacts/phase8_preview.json`. Other QA servers and the isolated test worker have stopped. Earlier `phase8-preview`, `phase8-demo`, paired headless and 32-inhabitant files remain for inspection. Current handoff screenshots are `artifacts/phase8-handoff-desktop.png` and `phase8-handoff-mobile.png`.

No long multi-seed horizon, speech adapter, true 3D physics, endogenous learning or Phase 9 work was started. Reading/rendering books does not train model weights or verify claims. The viewer's privileged diagnostics are never fed into provider context. Large-world, mobile-device GPU, other-browser/driver, sustained thermal and true-3D mechanics validation remain outside this phase.
