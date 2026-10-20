# Phase 7 operational scope complete - 2026-10-19

Bounded unattended operation is implemented and verified. **Longer multi-seed horizons, the proposed 24 simulated hours, and Phase 8/3D remain deferred as requested.** No long-horizon stability claim is made.

Workspace: `C:\Users\abc\Documents\ChatGPT\UnderWorld`, branch `codex/phase-7`. Phase 6 status is preserved in `PHASE6_REPORT.md`; previous reports, artifacts and data remain. The repository has no initial commit; no commit or push is claimed. The provided `PROJECT_SPEC.md` is unchanged, SHA-256 `306e5eafba0f7c53b49002ec8fcd276dc736efb791ede1991f64e685773e84d6`.

## Delivered

- Finite simulated/wall-clock budgets, a process-safe single-writer lease, approximately one-second heartbeat, session-specific stop requests, Ctrl+C grace period and a host watchdog.
- Explicit SQLite tick, cognition and maintenance commit boundaries, hot-journal recovery, checkpoint publication and bounded archive rotation. Reserved checkpoint names cannot accidentally match user checkpoints.
- Finite database/archive quotas, ordinary-episode retention, preserved source reports/practice/pending evidence, exact native cumulative event counts and checked epoch-summary links. Full replay is limited to retained epochs; expired history is deliberately unavailable.
- A durable bounded cognition queue, batch dispatch, lifetime/daily/token/timeout budgets, quota/drop/backlog counters and explicit fallback/interrupted-call counts. Interrupted reserved calls are not silently repeated.
- Windows AppContainer workers with zero network capabilities and a kill-on-close, 512 MiB job limit. Actual token checks and public/private WSAEACCES probes gate execution. Explicit local inference uses bounded JSON through an inherited pipe to a pinned host-side loopback adapter; no network exemption is installed.
- Separate target, wall-limit, requested-stop, quota, population-extinction and system-failure statuses. Every inhabitant receives every physical tick; no distance-based update skipping or 3D work was added.

[PHASE7_OPERATIONS.md](PHASE7_OPERATIONS.md) explains commands, configuration, isolation, retention, deadlines, memory scope and recovery. README, architecture, model limits and references are updated. The existing CPython runtime was copied locally for AppContainer compatibility (27.7 MiB); no package, model or external service was installed/downloaded this phase.

Package **0.8.0**, native **UW6**, SQLite **user_version=7**. Existing physics laws retain their prior identity; the checkpoint format adds counters and receipt maintenance. Older formats need their original runtime; no automatic migration is claimed.

- Native build: `1955dda0d7cd3350527e937dc626a1d3d5dcdb808b82a7207c1102db2957dfbd`.
- Reviewed Python runtime: `995842ce19b4f6cbc5c2180dc41d78e661ec691e33405ec54bfb2778044e4e81`.
- Captured matrix runtime: `bb3447d409db19f62506394801adf76205416ed8b1e070dc3c728a47372d137c`.

## Verification

`artifacts/phase7_checks.json`: **102 Python tests + 4 CTest checks passed**. The 16 added Python tests cover receipt retirement/deduplication, bounded archives, preserved report/pending evidence, user checkpoint names, control/queue/epoch corruption, disk FULL rollback, archive budget refusal, OS-released writer leases, exact crash boundaries, interrupted queue recovery, stop/wall limits, actual AppContainer denial and JSON inference transport, and concurrent isolated launches. Prior physical conservation, bodies, privacy, teaching, culture, cognition and observer tests remain green.

Actual commands:

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$pythonExe=(Resolve-Path '.venv/Scripts/python.exe').Path
cmake -S . -B build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
cmake --build build --parallel 2
.venv/Scripts/python.exe scripts/verify.py --core build/underworld_core.exe --ctest C:/mingw64/bin/ctest.exe
.venv/Scripts/python.exe scripts/phase7_evidence.py --model
.venv/Scripts/python.exe scripts/phase7_final_validation.py
```

The build succeeded; final full Python tests took 73.54 wall seconds and CTest 0.12 seconds. Host: i3-6006U, two cores/four threads, 4 GiB RAM, Windows; CPython 3.12.10, SQLite 3.49.1, GCC 15.2.0, CMake 4.1.2, pybind11 3.0.4. GPU inference is disabled.

Early integration failures identified the wrong Windows pipe handle wrapper, process-spawn restrictions, a pipe-close race and shared-runtime setup concurrency. Review also fixed checkpoint publication retries and a wildcard that could match user checkpoint names. `phase7_initial_checks_failure.json`, `phase7_review_failure.json` and the early probe files retain failure evidence. The final full suite passes after those fixes. No visual/3D changes were made; no new browser-verification claim is made.

## Current-runtime serial population checks

`artifacts/phase7_final_validation.json`: seed **11**, dt **1 s**, batch **25 ticks**, epoch **50 ticks**, three retained archives, 60 wall-second budget. No test suite or other benchmark ran concurrently. All cases reached 120 simulated seconds and all current/retained heads replay. Latency is null for disabled cognition; current/peak cognition backlog and invalid-action counts are zero in these three utility cases.

| Inhabitants | Simulated s | Worker wall s | Host wall s | Simulated s / wall s | Peak worker MiB | DB bytes (growth) | Archive bytes | Failed actions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 120 | 2.822 | 7.328 | 42.53 | 29.49 | 229376 (+106496) | 495616 | 1 |
| 16 | 120 | 7.710 | 13.125 | 15.56 | 29.67 | 344064 (+221184) | 708608 | 14 |
| 32 | 120 | 53.686 | 58.563 | 2.24 | 31.52 | 679936 (+544768) | 1437696 | 114 |

Host time includes profile setup/cleanup; worker time includes persistence, inspection and maintenance. These are short durable-world measurements, not rendering FPS or a controlled scaling law. Physical failures are retained rather than confused with invalid requests. The original population matrix overlapped verification: it reached 300 s for 8/16 inhabitants, but the 32-inhabitant run stopped at its wall budget at tick 121. That result remains in the raw matrix and is not relabeled as a completed 300-second run.

A separate **current-runtime** 8-inhabitant local-model case reached 120 simulated seconds in **27.899 worker / 33.516 host wall seconds** (4.30 simulated s/wall s). Its two model requests both planned successfully, with zero fallbacks and latency p50 **7.732 s**, p95 **16.927 s**. Peak worker memory was 29.64 MiB, DB 249856 bytes, archives 536576 bytes. The separate server peak was 482.98 MiB. Both model plans requested eating without carried food and were rejected by the native engine (`INSUFFICIENT_RESOURCE`): **2 native rejections, zero successful model actions** in this check. The explicitly owned CPU model server was stopped afterward.

## Short five-seed matrix

`artifacts/phase7_summary.json` / `.csv`: seeds **11, 22, 33, 44, 55**, 8 inhabitants, replenished resources, dt **1 s**. The total matrix/diagnostic host wall time was **582.5 s**; summed simulated durations across independent runs are not one continuous world horizon.

| Arm | Seeds | Simulated duration per seed | Worker wall range | Cognition samples | Outcome |
|---|---:|---:|---:|---:|---|
| Utility survival | 5 | 300 s | 4.90-10.09 s | 0 | 8/8 alive in every seed |
| Utility + authored cognition | 5 | 300 s | 6.15-8.88 s | 4 per seed | 8/8 alive; no fallbacks |
| Utility, episodes disabled | 5 | 300 s | 4.77-7.13 s | 0 | 8/8 alive; reduced DB growth |
| Utility + pinned local model | 5 | 120 s | 26.04-29.21 s | 2 per seed | 8/8 alive; 10 structured plans; 9 native rejections; no fallbacks |

The model is the existing **SmolLM2-360M-Instruct Q8_0**, llama.cpp **b11721-ff5a23376**, CPU, two threads, context 2048, deterministic sampling, input budget 1536/output budget 128, timeout 20 s. Its adapter/server/model pins were checked. Model-server peak working set reached **644.96 MiB** in the matrix and is separate from worker/job memory. Both owned evidence servers were intentionally terminated after their checks.

Authored cognition per-seed p50 was **0.609-0.753 ms**, p95 **1.221-2.220 ms**. Model per-seed p50 was **8.054-8.513 s**, p95 **13.856-16.868 s**. These are end-to-end call latencies, with only four/two samples per seed. Both cognition arms peaked at backlog **8**, drained to **0**, and counted later dispatches blocked by the lifetime call budget. The utility, authored and episode-disabled arms recorded zero native rejections. The model arm recorded **9 native request rejections across 10 structured plans** (2, 2, 2, 2, 1 per seed), despite zero provider fallbacks. The `invalid_actions` metric counts every native `action_rejected`, including unmet physical preconditions; it does not mean nine JSON/schema failures. A stored `planned` status confirms parsing/compilation, not physical execution. These negative model results are retained. Full counters, action failures, memory, growth, timing and configurations remain in JSON.

This is sparse cognition layered on an authored utility survival policy, not eight continuously thinking LLM agents. Model and control horizons differ, so survival scores do not establish model superiority. The utility policy does not read episodes: disabling them yields exactly matching native/policy state hashes in all five matched seeds. That ablation demonstrates storage/privacy configuration, not a memory-driven behavioral advantage. No neural-weight update or new cultural claim is made.

The matrix's exact pre-review runtime is captured in `artifacts/phase7_benchmark_runtime` with per-file checksums. Final setup/retention fixes have a different runtime identity. Reports keep the identities actually tested. Use `scripts/replay_phase7_benchmark.py --db <matrix database>` to read those saved experiments; the current CLI intentionally refuses a runtime mismatch. **All 70 matrix/diagnostic databases and retained archives replayed successfully** in a fresh process with the captured runtime (`phase7_benchmark_replays.json`). Current-runtime checks and their identities are separately recorded in `phase7_final_validation.json`; all **12 current databases/retained archives** also replay (`phase7_reviewed_replays.json`).

## Recovery and distinct stop outcomes

The actual isolated forced-exit cases exit with code 77 and report system failure, then resume:

| Forced exit point | Recovered committed tick | Tick after adding 3 simulated s |
|---|---:|---:|
| Before tick 3 commit | 2 | 5 |
| After tick 3 commit | 3 | 6 |
| After checkpoint publication at tick 10 | 10 | 13 |

All resumed heads and retained archives replay. Tests additionally kill before the rotation transaction commits and recreate a checkpoint receipt interrupted before publication. No committed physical tick is lost or silently repeated; unfinished cognition remains an auditable consumed attempt. This does not test power loss or storage hardware failure.

The 1 MiB database diagnostic stopped with `quota_reached` at tick **95**, preserved its committed head and replayed. The no-food/no-water/no-maintenance case stopped with `population_extinct` at tick **550**, with zero alive/present inhabitants. The actual session stop request returned `stopped` at tick **56** and replayed. Thus extinction, deliberate stop, quota, wall budget and worker failure remain distinct. All recorded worker network probes denied both public and private outbound TCP with **WSAEACCES 10013**, and normal profile cleanup succeeded. Successful-run memory is measured in the worker; failure-recovery reports sample the host supervisor after the worker has exited and must not be treated as worker peak memory.

## Handoff and remaining limits

Start a new reviewed run using `config/unattended.toml` and the commands in `PHASE7_OPERATIONS.md`; `data/phase7-reviewed/population-8/run.sqlite` is a current-runtime saved example. No experiment, observer or owned model server is left running.

Longer multi-seed horizons and 24-hour model throughput remain deferred. Finite archive retention cannot reconstruct expired lifetime history. Wall deadlines are cooperative around an in-flight transaction/call/maintenance and final reporting, with a separate hard job watchdog. DB quotas exclude transient rollback/VACUUM space and fixed runtime/model assets. The implementation is Windows-specific; Linux/MSVC, host death cleanup and power-failure durability remain unverified. Short replenished-resource survival does not establish long-term sustainability, learning or social emergence. Phase 8/3D has not started.
