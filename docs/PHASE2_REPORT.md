# Phase 2 report — bodies, senses and everyday agency

Date: 2026-10-19 (Asia/Calcutta). **Phase 2 complete on the available native Windows host.** Branch `codex/phase-2`; source changes remain uncommitted for review. Prior reports/evidence are preserved in PHASE0_REPORT.md, PHASE1_REPORT.md and their artifacts. No Phase 3 implementation or model intelligence is claimed.

## Implemented scope

- Eight abstract bodies with positions, inventories, hunger/thirst/fatigue, health and death. Native C++ owns all drift, costs, recovery, material changes, action validation and consequences.
- Movement, gathering, drinking, eating, resting, inspecting and nearby speech, plus the existing deposit action. Food/water consumption transfers mass to explicitly accounted ingested reservoirs. Optional resource recovery is an initial-config boundary source, reconciled in the ledger.
- Native range/spatial/rock-occlusion observations and local audibility. Own body/inventory are available; other actors' private body/inventory values are removed. Speech carries delivery tick, speaker and actual source event, and remains unverified text.
- A deterministic Python utility policy receiving only one actor's permitted observation and its own navigation state. Its separate route dictionaries, actual decision/result journal and native state are committed atomically. No model, remote API, shared private context or training exists.
- Checkpoints/replay preserve bodies, pending actions, messages, ingested/source reservoirs, RNG and scheduler/navigation state. Replay uses recorded decisions/frames without rerunning the policy. Oversize checkpoints fail before replacing a readable committed head.
- A loopback observer with pause/resume, one-tick stepping, target speed, authoritative positions, selected-agent needs/inventory and actual action history. Read-only polling cannot advance time. Real desktop/mobile browser checks passed.

Exact authored rates, units, action durations, ledger equations, schema amendments and limits: [PHASE2_AGENCY.md](PHASE2_AGENCY.md). These are engineered body/sense abstractions, not biochemical humans or humanlike cognition.

## Configuration, environment and reproducibility

Current default for `new`: `config/survival.toml`, seed **20261019**, **8 bodies**, **16 x 16 m**, **dt=0.2 simulated seconds**, utility cadence **25 ticks / 5 s**, initial food **16 kg**, water **64 kg**, inert material **32 kg**, recovery sources **disabled**, event retention **10,000**, cognition provider **disabled**. `config/baseline.toml` preserves the body-disabled Phase 1 mechanics regression scene.

Native build ID: `6c6e214a1cc4318a378e9683a53f6e8906a6c6f0b8fc660d4ae4c439fe58e097`. Survival config hash: `1e3c13fd045a7d43be96b3ac15ac2678b72a4aeae751ac583c8649e7e9b6dc08`. Native checkpoint **UW2**, database **user_version=2**, laws **bodies-2**, package **0.3.0**. Both config/build and Python simulation-orchestration source identities are checked. Old build-specific UW1 saves are not silently migrated or overwritten; new current-build Phase 1 regression runs still work.

Reused tested tools: CPython 3.12.10, SQLite 3.49.1, pybind11 3.0.4, GCC 15.2.0, CMake 4.1.2 and GNU Make 4.4.1. No new Phase 2 dependencies, model downloads, GPU setup or paid services. Existing execution host: Windows 10 Pro x64, i3-6006U, approximately 3.89 GiB RAM, Intel HD 520. Deployment hardware is not assumed. Linux and MSVC remain untested. No new RAM/VRAM or inference benchmark is claimed.

## Commands and verification

Executed successfully from the repository root:

```powershell
.\scripts\bootstrap.ps1
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe --ctest C:\mingw64\bin\ctest.exe
.\.venv\Scripts\python.exe scripts\survival_run.py --ticks 4500
.\.venv\Scripts\python.exe -m underworld new --db data\phase2-preview.sqlite
.\.venv\Scripts\python.exe -m underworld advance --db data\phase2-preview.sqlite --ticks 41
.\.venv\Scripts\python.exe -m underworld observe --db data\phase2-preview.sqlite --port 8765
```

Build and final bootstrap succeeded. **31 Python tests and 3 native CTest checks passed.** `artifacts/phase2_checks.json` records exact commands, exit codes, stdout/stderr and timings. It includes all previous-phase regressions plus:

- Actual food/water consumption, rest recovery while other needs continue drifting, inventory capacity, unavailable consumption and invalid durations, exact material totals and source-rate quantization across restart.
- Scarcity/death and dead-action rejection; observable inspection outcomes linked to real event references.
- Hidden food behind a rock remains absent from observations even when its global mass changes. Different private fatigue in another body leaves an actor's observation and policy decision unchanged. Invented private-memory query fields are rejected. Episodic memories do not exist yet; their actual privacy/retrieval tests belong to Phase 3.
- Speech reaches a nearby actor with provenance while an isolated control receives nothing. Hostile role/private-memory text stays an unverified report. Delivered reports persist across native restore.
- Atomic save/resume of utility navigation, body/action state and recorded replay; replay works even when the policy is patched to fail if called. Rollback discards navigation frames, decisions and physical state together. A checkpoint-size failure preserves the previous committed head.
- Actual local HTTP read-only polling, unauthorized-control rejection, step, target-speed, resume and pause. Existing forced-process-exit recovery tests still pass.

A separate in-flight-meal artifact saves at tick 10 with a half-finished eat action, resumes through tick 15 and matches uninterrupted execution. Agent 1 ingests exactly **200,000,000 ug / 0.2 kg** of food; hunger changes and the complete mass ledger remains exact. Resumed/uninterrupted hash: `968949673062ad069a33a1716cd8a2cc0bbd1027d48a3c486d008a8507b30f4d`. Actual requests/results/event traces and replay are in `artifacts/phase2_body_evidence.json`.

## Constrained survival run and scarcity control

Both conditions use the same seed, body rules, observation-only utility policy, 8 initial bodies and **4,500 physical ticks = 900 simulated seconds / 15 simulated minutes**. No physical updates were skipped and no manual rescue was applied. These are bounded single-seed observations, not general survival or intelligence evidence.

| Condition | Execution | Wall time | Living at end | Recorded failures |
| --- | --- | ---: | ---: | --- |
| Food 16 kg / water 64 kg, no recovery | Durable one-tick SQLite transactions | 54.542121 s | **8/8** | 1 COLLISION |
| Food 0 / water 0, no recovery | Native stepping with the same Python observation-only policy | 2.380906 s | **0/8** | 10 COLLISION, 8 death events |

The scarcity control intentionally uses zero available food/water. It proves that the authored needs model can fail without rescue; it is not evidence of realistic starvation times. The execution paths differ, so their wall times are not a controlled performance comparison.

Resourced run statistics:

- 248 accepted requests: **128 move, 40 gather, 40 rest, 24 drink, 16 eat**.
- 247 completions, 1 failed collision; no failure was removed or converted into success.
- All 8 final health values **1.0**; hunger approximately **.45**, thirst **.1413–.2388**, fatigue **.1300–.17416**.
- Final piles: food **9.6 kg**, water **49.6 kg**. Across bodies, ingested food **3.2 kg** and water **7.2 kg**; carried material and piles reconcile exactly with initial food **16 kg**, water **64 kg**, inert **32 kg**. Boundary sources remained zero.
- Durable throughput observed **82.505 ticks per wall second / 16.501 simulated seconds per wall second** for this small model-off run. Database at completion **929,792 bytes**. No model latency or GPU memory was measured.
- Recorded-decision/navigation replay matches the final head hash: `7e77e0e6dc73ff2a9a8ce495090057794c21914b6f35de3f82bf700f315de915`.

Full config, final body/resource states, counts, failures, timings and replay results for both conditions are retained in `artifacts/phase2_survival.json`. Temporary experiment databases were removed only after exporting evidence. This run is not the later multi-seed unattended experiment.

## Observer evidence and preview

Browser-tested at **1440 x 1000** and **390 x 844**: eight actor markers, four need meters, actual selected-agent coordinates/action history, no horizontal overflow, no visible errors and no console errors after fixing the favicon route. A real button click changed tick 0 to 1; resume advanced to tick 41; pause followed by polling kept tick 41 unchanged. Selected-agent coordinates matched the API. Screenshots and structured observations:

- `artifacts/phase2_observer_desktop.png`
- `artifacts/phase2_observer_mobile.png`
- `artifacts/phase2_browser_checks.json`

A current-build preview database was independently created and advanced through the engine to tick 41, and the observer is running **paused** at [http://127.0.0.1:8765](http://127.0.0.1:8765), using `data/phase2-preview.sqlite`. It performs no autonomous advancement unless Resume or Step is selected. It is a local process, so restart with the command above if the session ends. Stop the observer before rebuilding the native module or using another writer on that database.

The observer adds no external assets/framework dependencies. Its range circle is a guide, not the occlusion mask. It is privileged operator inspection, never a cognition input. GET is query-only; controls are separate same-origin/token-bearing POST commands.

## Artifacts and remaining scope

Current evidence: `phase2_checks.json`, `phase2_mechanics_evidence.json`, `phase2_body_evidence.json`, `phase2_survival.json`, browser checks and two screenshots. All are under `artifacts/`. Earlier Phase 0/1 reports/checks/benchmark evidence remain preserved. The source specification is unchanged.

No Phase 2 acceptance blocker remains on this host. Limits: authored rates, simple circle/segment geometry, fixed sensory ranges, coarse exact pile measurements, bounded navigation and report history, no body biochemistry, no persistent episodic memories, no LLM. Source/checkpoint/journal/population quotas remain prototype limits; long or speech-heavy unattended operation, multi-seed survival, network-enforced closed mode, hardware power-loss behavior and other platforms are unproven. No claim of consciousness, general intelligence or model training is made.

Next is **Phase 3 only when requested**: cognition-provider interface, persistent seeded identity/motivations/relationships/episodic memory, bounded lexical retrieval/planning and one measured real local-model adapter while retaining the utility/model-off baseline. The available low-memory CPU host will need actual model feasibility measurements; none has been invented in this phase.
