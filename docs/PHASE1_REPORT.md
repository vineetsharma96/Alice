# Phase 1 report — authoritative world and durable time

Date: 2026-10-19 (Asia/Calcutta). **Phase 1 complete on the available Windows/MinGW host.** Branch `codex/phase-1`; changes remain uncommitted for review. Phase 0's report is preserved in [PHASE0_REPORT.md](PHASE0_REPORT.md). No Phase 2 or later capability is claimed.

## Completed scope

- C++20 fixed-step kernel with seeded RNG, stable IDs, bounded rectangular terrain, circular actors and a solid rock, swept collision checks, a uniform-grid spatial index, authored day/night energy input, resource piles and exact inventory transfers.
- Actual pybind11 3.0.4 extension exposing batched stepping, per-actor geometric observations, privileged snapshots, validated requests and complete checkpoint export/restore. Successfully built and imported on the installed MinGW/CPython combination; no IPC fallback was needed.
- SQLite run metadata, one-tick atomic commits, monotonically increasing event sequences, bounded recent event log, versioned named checkpoints, online backups, hot-journal recovery and replay from recorded external decisions.
- Headless commands: `new`, `advance`, `inspect`, `save`, `resume`, `replay`. Observe/inspect are query-only and do not advance time. Interrupted ticks are not partially published.
- Deterministic scripted movement for mechanics tests, plus manual mode. These actors have no needs, memories or intelligence. Eating and survival belong to Phase 2.

[PHASE1_MECHANICS.md](PHASE1_MECHANICS.md) records exact units, rules, schemas, transaction boundaries and limits. It explicitly amends the Phase 0 proposal: Foundation spelling `requested_duration` (seconds), a `deposit` action to test inverse transfers, and the implemented mechanics subset of observations/results. Rich per-result effect/event-reference fields remain deferred; provenance is in the request-ID-linked event trace.

## Configuration and dependencies

Baseline `config/baseline.toml`: seed **20261019**, population **8**, region **64 x 64 m**, fixed step **0.1 s**, authored decision interval **50 ticks**, cognition **disabled**, closed mode, event retention **10,000**. Initial material totals: food 16 kg, water 64 kg, inert material 32 kg. Native mass uses integer micrograms; all transfers preserve these totals exactly.

Reused host: Windows 10 Pro x64 10.0.19045, i3-6006U (2 cores/4 threads), 3.89 GiB visible RAM, Intel HD 520. This is the execution host, not an assumed deployment target. GCC 15.2.0 / CMake 4.1.2 / GNU Make 4.4.1 from `C:\mingw64\bin`; CPython 3.12.10 and stdlib SQLite 3.49.1. Installed only `pybind11==3.0.4` in `.venv`, after checking official docs/release/license. No GPU/model/cloud/database service or paid dependency.

Working native build ID: `4328c51aaf1332d82529ae95b6e1c1206123dc736a2d31a28a16f575636c1eea`. Run metadata separately pins Python persistence/config/wire source and canonical config hashes. Saved state is build-specific; incompatible code/checkpoints fail closed instead of silently migrating.

## Commands and actual results

Run from repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install pybind11==3.0.4
$env:PATH = "C:\mingw64\bin;$env:PATH"
$pythonExe = (Resolve-Path '.venv\Scripts\python.exe').Path
cmake -S . -B build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
cmake --build build --parallel 2
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe --ctest C:\mingw64\bin\ctest.exe
.\.venv\Scripts\python.exe scripts\benchmark.py --ticks 10000
.\scripts\bootstrap.ps1
```

All final commands exited 0. Native executable/library and Python module compiled/linked successfully; no project compiler warnings observed. pybind11 disables unsupported MinGW LTO; the module uses its NO_EXTRAS path. The final documented bootstrap completed and reran validation.

Final CTest: **3/3 passed**, 0.11 s reported test time. Python unittest: **18/18 passed**, 6.264 s reported test time (including malformed-input subcases and the original Phase 0 regressions). Recorded verification process wall times: CTest 0.200 s, unittest 6.717 s, legacy probe 0.280 s, readable evidence generation 7.756 s. See JSON for unrounded values and exact stdout/stderr.

Acceptance evidence:

- Same seed/config produced the same complete native state hash in independent runs. A checkpoint at tick 37 retained outstanding actions; resume through tick 200 matched uninterrupted execution. SHA256: `a4116f5e673de53f9a68a30d5d4db846bc23a10a94f0e8296ad2fac47263dc7b`.
- External gather decisions are recorded, replayed without a provider and deduplicated across restart. A transfer checkpoint taken halfway through its duration completes with exactly 1 kg added to the requesting inventory and exactly 1 kg removed from its pile.
- Gather/deposit tests preserve exact species totals. Duplicate requests cannot transfer twice; conflicting IDs, negative/oversize/sub-microgram requests, insufficient quantities, stale observations and invalid targets are rejected. Competing 10 kg requests against a 16 kg pile yield one completed transfer and one insufficient-resource failure, with no negative quantity.
- Swept terrain/actor collision tests and circle-adjusted bounds pass. Spatial observations omit other actors' inventories. Repeated observer queries preserve both the native checkpoint and actual database file bytes.
- Injected transaction exception rolls back state, decisions and events together. Independent subprocesses forcibly exit with code 77 before and after tick 7's commit. Recovery returns tick 6 or tick 7 respectively; replay and further advancement succeed. This tests abrupt process exit, not hardware power loss.
- A day/night check advances every 1-second native step from dawn through noon and into night; noon flux reaches 100 W/m² and the reservoir receives no night input. This authored source is not chemistry or heat simulation.

An initial Windows backup test exposed an invalid flush on a read-only file descriptor; using a writable descriptor fixed it and save/recovery tests pass. Test-only SQLite handles were made explicitly closing to permit Windows temporary-file cleanup. Very deeply nested JSON is now converted to a bounded validation error. Final source/check evidence includes these fixes; the benchmark's valid-input physical kernel is unchanged.

## Measured 10,000-tick benchmark

Same baseline, eight scripted actors, no model. **10,000 physical ticks = 1,000 simulated seconds (16 minutes 40 seconds)**. Every physical tick was executed. Native timing includes batched stepping/event conversion; durable timing includes invariant checks, complete state serialization and one FULL-synchronous SQLite transaction per tick. Startup/setup and replay are outside the timing; peak memory covers each whole isolated worker process, including interpreter/extension and its validation/replay work.

| Path | Wall time | Ticks per wall second | Simulated seconds per wall second | Peak process working set |
| --- | ---: | ---: | ---: | ---: |
| Batched native, no persistence | 0.357518 s | 27,970.61 | 2,797.06 | 33.31 MiB |
| Durable, one commit per tick | 274.668576 s | 36.41 | 3.64075 | 24.86 MiB |

Native, durable and reconstructed replay state hashes match: `74a5ee5b594444a8cd7df75223ec7ad7ba671e7e400a2385902d8fdca9c2eb99`. Durable database size at completion: **1,851,392 bytes**; retained events **10,000**; external decisions **0** (the benchmark uses internal authored movement). Food/water/inert totals remained exact. Recorded daylight input/reservoir: 14,885,425.730108099 J.

These are single-run observations for a tiny model-off region, not inference throughput, population-scaling guarantees or humanlike-world performance. Durable execution is substantially slower than the isolated kernel because its commit/checkpoint path is deliberately conservative; no unmeasured optimization is claimed. No 16/32-agent or unattended survival run was performed.

## Artifacts

- `artifacts/phase1_checks.json`: exact final commands, exit codes, stdout/stderr, Python/SQLite/platform and wall times.
- `artifacts/phase1_evidence.json`: same-seed and save/resume hashes, in-flight state, replay result, external transfer request, after-restart observation and actual event trace.
- `artifacts/phase1_benchmark.json`: full config, native build ID, commands, throughput, peak working-set bytes, mass totals, database size and replay/hash comparison.
- `artifacts/host.json`, `artifacts/initial_scene.json`, `artifacts/phase0_checks.json`: preserved Phase 0 evidence.

Temporary test/benchmark databases are removed after extracting evidence; the scripts regenerate them. User-created databases go in ignored `data/`. No secrets or prompts/model weights were needed.

## Remaining limits and next phase

No Phase 1 acceptance blocker remains on this host. Linux and MSVC are documented but untested. Same-build/runtime determinism only; no cross-platform bitwise guarantee. Power-loss/flush hardware behavior, backup directory-entry durability and non-NTFS filesystems were not tested. Native World objects require single-thread ownership; observers use separate restored objects/database snapshots rather than racing a shared object during GIL-released stepping. The CLI is a trusted operator interface, not an authenticated service.

Prototype guards: 64 allocated actors maximum (only 8 benchmarked), native batch 10,000, advance call 100,000 ticks, run head 1,000,000 ticks, 10,000 native request dedup records, 10,000 external decisions and 16 checkpoints including initial. At native request capacity, new actions are rejected and scripted actors may cease moving. Long unattended retention/backpressure is deferred to Phase 7; do not infer it from a bounded smoke run. No model RAM/VRAM or cognition latency was measured.

Next is **Phase 2 only when requested**: abstract bodies and needs, eating/drinking/resting/gathering, deterministic utility policy, sensory/audibility rules, minimal observer controls and a constrained survival run. Humanlike model cognition and persistent identity remain Phase 3; the overall ambition is unchanged.
