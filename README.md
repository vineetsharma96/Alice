# Underworld Lab

A persistent-world research project with an authoritative C++ simulation and Python orchestration. **The stabilization milestone adds an opt-in prerequisite-aware everyday-action executor.** Phase 9's failed learning study remains unchanged and its learner stays outside autonomous policies. The Phase 8 Three.js viewer presents the existing two-dimensional mechanics. Phase 7 unattended operation remains a separate runner; true 3D mechanics remain deferred.

The provided brief is preserved in [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md). Read [docs/STATUS.md](docs/STATUS.md) before continuing. Only advance one requested phase at a time.

## Stabilized everyday actions

The new controller persists explicit goals, expands eat/drink into locate → approach → gather → consume, reobserves prerequisites, and records native completion separately from generated plans. Navigation and survival execution are authored logic, including when a model selects the goal. Inference fallback and deterministic need selection are labeled.

```powershell
.venv/Scripts/python.exe -m underworld.stabilization init --db data/stabilized/run.sqlite --calls 0
.venv/Scripts/python.exe -m underworld.stabilization run --db data/stabilized/run.sqlite --seconds 120
.venv/Scripts/python.exe -m underworld.stabilization status --db data/stabilized/run.sqlite
```

The living-world development entry point uses the same explicit controller without changing legacy runs:

```powershell
.venv/Scripts/python.exe -m underworld living-world init --db data/living-world/run.sqlite
.venv/Scripts/python.exe -m underworld living-world run --db data/living-world/run.sqlite --seconds 30
.venv/Scripts/python.exe -m underworld living-world status --db data/living-world/run.sqlite
```

It starts with four inhabitants and finite resources; trees, animals and crafting are later milestones. The observer reports whether the legacy or stabilization controller is active.

See [operations and existing-world handoff](docs/STABILIZATION_OPERATIONS.md), [registered protocol](docs/STABILIZATION_PROTOCOL.md) and [results](docs/STABILIZATION_REPORT.md). Reuse `run` to continue the same world; initializing again would create a different experiment. The legacy utility/model policies remain unchanged for comparison.

## Phase 9 research experiment

Read the [preregistration](docs/PHASE9_PREREGISTRATION.md) and [experiment report](docs/PHASE9_REPORT.md). One non-neural linear policy learns consumption feasibility from verified terminal eat/drink receipts. Five seeds compare it against frozen weights, nearest episodic memory and a stronger domain-informed memory control. Evaluation includes unseen quantities, exact equality, and retention after a second training block. This is a small authored task, not general intelligence, neural training or evolution. The learner is separate from live agents; its deployment gate must pass before integration.

```powershell
# Inspect retained parameters without advancing a world.
.venv/Scripts/python.exe -m underworld.learning status --db data/phase9-study-20261020/seed-11/policy.sqlite
# Explicit replication: choose a NEW directory; existing evidence is never overwritten.
.venv/Scripts/python.exe scripts/phase9_experiment.py --output data/phase9-replication
```

`config/phase9_study.json` and `docs/PHASE9_PREREGISTRATION.md` are SHA-sealed before the first study trial. Altering either makes the runner refuse execution. Each run retains source hashes, native databases, prediction-before-label files, raw training/evaluation traces, checksummed parameters, paired bootstrap intervals and failure cases. A run can take several minutes on this machine and stops at its 900-second or 512-MiB evidence budget. An interrupted reservation never automatically replays an action.

## Explorable 3D viewer

Open the local viewer at `/viewer`; the existing 2D observer remains at `/`. On a fresh checkout, create the explicitly authored lab fixture once:

```powershell
.venv/Scripts/python.exe scripts/phase8_demo.py
.venv/Scripts/python.exe -m underworld observe --db data/phase8-demo/run.sqlite --port 8765
# Open http://127.0.0.1:8765/viewer (starts paused).
```

Existing fixture files are never overwritten. If a preview is already running, use its URL or another port. For an isolated unattended run, attach with `observe --db <run.sqlite> --port 8766 --read-only`; this starts no competing writer and disables mutations. Drag/scroll to navigate, use WASD with viewport focus, select entities to inspect, and use the guided/paused operator form for recorded interventions. The avatar is positioned through the existing message channel. Speech and true 3D mechanics are not implemented.

Three.js 0.180.0 is vendored locally with its MIT license; no Node server or runtime CDN is needed. Low/Standard rendering caps at 30/60 fps. See [viewer protocol and limits](docs/PHASE8_VIEWER_PROTOCOL.md), [design audit](docs/PHASE8_DESIGN.md) and [measured results](docs/STATUS.md).

## Unattended experiments

See [Phase 7 operations](docs/PHASE7_OPERATIONS.md) for run/stop/resume commands, the explicit local-model pipe, disk and retention limits, commit boundaries and measurements. Use a dedicated case folder with `config/unattended.toml`; `run` requires finite simulated and wall-clock durations. [Current status](docs/STATUS.md) records the short horizons actually tested.

## Native Windows bootstrap

Requires Python 3.11+ with development headers/libraries, CMake 3.20+, and a C++20 compiler. This host uses Python 3.12.10 and MinGW GCC 15.2.0 / CMake 4.1.2 / GNU Make 4.4.1 in `C:\mingw64\bin`. The bootstrap installs pinned pybind11 3.0.4 in `.venv`, builds the native module and runs checks. No model download or global package installation is involved.

From the repository root in PowerShell:

```powershell
# Execute the script in your normal permitted PowerShell environment.
.\scripts\bootstrap.ps1
# For a different existing MinGW toolchain:
.\scripts\bootstrap.ps1 -ToolchainBin 'D:\tools\mingw64\bin'
```

If local script policy prevents execution, use these commands directly; no policy change is required:

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$pythonExe = (Resolve-Path '.venv\Scripts\python.exe').Path
cmake -S . -B build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
cmake --build build --parallel 2
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe
.\.venv\Scripts\python.exe -m underworld inspect --core build\underworld_core.exe
```

The pybind11 extension was built and imported successfully on this MinGW/CPython host. MSVC: use a Developer PowerShell and CMake's default Visual Studio generator; build with `--config Release`, then pass `build\Release\underworld_core.exe` to the verification script. MSVC is **untested**. Keep MinGW's bin directory on PATH for native executables. The Python loader adds the toolchain DLL directory for the extension. For custom paths set `UNDERWORLD_TOOLCHAIN` and `UNDERWORLD_BUILD`. No binaries are bundled for redistribution.

## Linux bootstrap (untested)

With an existing GCC/Clang C++20 compiler, CMake, make and Python 3.11+:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="$PWD/.venv/bin/python"
cmake --build build --parallel 2
.venv/bin/python scripts/verify.py --core build/underworld_core
.venv/bin/python -m underworld inspect --core build/underworld_core
```

The model-off baseline requires no WSL, network access, paid service, API key, GPU or downloaded model. The optional model adapter contacts a literal loopback origin only. OS-enforced egress isolation of the whole application is a later acceptance test.

## Run a persistent world

From the repository root in PowerShell:

```powershell
# New runs default to config/survival.toml: eight bodies in a 16 x 16 m region.
.\.venv\Scripts\python.exe -m underworld new --db data\experiment.sqlite
.\.venv\Scripts\python.exe -m underworld observe --db data\experiment.sqlite --port 8765
```

Open [the local observer](http://127.0.0.1:8765). It starts paused. Use **Resume**, **Pause**, **Step one tick**, and the target-speed selector; select an inhabitant for its needs, position, inventory and actual action history. GET polling is read-only. Stop the observer writer with Ctrl+C before advancing the same database from another terminal or rebuilding the native module.

Headless commands remain available:

```powershell
.\.venv\Scripts\python.exe -m underworld advance --db data\experiment.sqlite --ticks 100
.\.venv\Scripts\python.exe -m underworld inspect --db data\experiment.sqlite
.\.venv\Scripts\python.exe -m underworld inspect --db data\experiment.sqlite --agent agent-1
.\.venv\Scripts\python.exe -m underworld save --db data\experiment.sqlite --name tick100 --output data\saved.sqlite
.\.venv\Scripts\python.exe -m underworld resume --db data\saved.sqlite --ticks 100
.\.venv\Scripts\python.exe -m underworld replay --db data\saved.sqlite
```

`new`/backup refuse to overwrite files. `resume` without `--ticks` recovers/verifies the committed head without advancing time. `inspect` is query-only. `save` creates a named checkpoint and optionally an atomic SQLite backup; resume the backup at its head. It does not rewrite an existing run's history to an old tick.

Use `new --manual` to disable autonomous policy decisions, then `advance --decisions path\actions.jsonl`. Each line contains `at_tick` and a complete ActionRequest; use the run ID/version from inspection. [Phase 2 agency](docs/PHASE2_AGENCY.md) specifies body rates, units, fields, senses, recovery sources, errors and persistence. `new --config config/baseline.toml` retains the body-disabled Phase 1 scripted mechanics scene. The CLI is a trusted local operator interface, not an authenticated multiuser server.

Current new-world checkpoints/database use **UW7 / user_version=8** with checkpoint schema 7, native build, Python runtime and separate mental-store checksums. Earlier UW6/DB7 saved files/reports remain preserved but are incompatible with this runtime; no automatic migration is claimed. Create a new compatible living-world run or use the original pinned runtime.

## Practical skills and cultural transfer

```powershell
# Five seeded teaching / no-teaching / persistent-memory-disabled comparisons:
.\.venv\Scripts\python.exe scripts\phase6_evidence.py --directory data\fresh-culture-evidence
.\.venv\Scripts\python.exe -m underworld procedure --db data\fresh-culture-evidence\seed-33\teaching-restarted.sqlite --agent agent-2
.\.venv\Scripts\python.exe -m underworld observe --db data\fresh-culture-evidence\seed-33\teaching-restarted.sqlite --port 8765
# Or create a new manual cultural lab:
.\.venv\Scripts\python.exe -m underworld new --manual --db data\my-culture.sqlite --config config\culture.toml
# Explicitly fork a memory-ablation branch; parent stays unchanged:
.\.venv\Scripts\python.exe -m underworld fork --db data\my-culture.sqlite --output data\memory-control.sqlite --episodic-memory disabled
```

Practice increases only after physically validated work; reading transfers an unverified recipe, without granting execution skill. An inhabitant can spend carried material and time to write a physical book, which remains usable after its author departs. Gifts conserve carried mass; agreements can be accepted, declined or expire. The observer shows skills, agreement outcomes and event-backed social/procedure provenance. [Phase 6 contracts, authored assumptions and controls](docs/PHASE6_CULTURE.md) document the task, tool schemas and experimental limits. Neither the finite search nor the two-inhabitant transfer experiment demonstrates open-ended intelligence.

## Coupled heat and materials

```powershell
# Four authored native traces plus a durable heating/inspection/transfer demonstration:
.\.venv\Scripts\python.exe scripts\phase5_evidence.py --directory data\fresh-thermal-evidence
.\.venv\Scripts\python.exe -m underworld observe --db data\fresh-thermal-evidence\lab.sqlite --port 8765
# Or start a fresh manual lab with open thermal boundaries:
.\.venv\Scripts\python.exe -m underworld new --manual --db data\my-lab.sqlite --config config\thermal-open.toml
```

The observer labels exact operator instruments separately from inhabitant measurements. Inhabitants can inspect approximate temperatures/phases, switch a reachable heater and transfer material between reachable vessels through validated timed actions. The evidence runner records mass/energy residuals, oxygen limits, vapor production, cold-water heating, save/resume and replay. It refuses an existing output directory. [Phase 5 equations, actions and validity limits](docs/PHASE5_THERMAL.md) explain the explicitly artificial reaction and fixed-pressure approximation. Closed/guided operator mode is independent of insulated/open thermal boundaries. Existing survival configurations keep the lab disabled.

## Operator teaching and branches

```powershell
# Closed remains the default. Fork into a new guided experiment without changing the parent:
.\.venv\Scripts\python.exe -m underworld fork --db data\experiment.sqlite --output data\guided.sqlite --mode guided
# Or start a fresh guided region:
.\.venv\Scripts\python.exe -m underworld new --db data\teaching.sqlite --config config\guided.toml
.\.venv\Scripts\python.exe -m underworld observe --db data\teaching.sqlite --port 8765
```

The paused observer has explicit **Place a book**, **Speak through avatar**, **Introduce material or object**, and **Broadcast** controls in guided mode. Read-only observation never delivers knowledge. Book text becomes available to an inhabitant only after a valid completed read; normal speech remains local and broadcasts are explicitly global. Source event, parent event, observer, time and unverified confidence remain attached to acquired reports. Each resource addition has an operator material/energy source.

```powershell
# Trusted operator JSON file; exact schema is in docs/PHASE4_TEACHING.md:
.\.venv\Scripts\python.exe -m underworld intervene --db data\teaching.sqlite --request lesson.json
.\.venv\Scripts\python.exe -m underworld interventions --db data\teaching.sqlite
.\.venv\Scripts\python.exe -m underworld recall --db data\teaching.sqlite --agent agent-3 --symbol sig_example
# Law changes create a new versioned branch; the parent is read-only:
.\.venv\Scripts\python.exe -m underworld fork --db data\teaching.sqlite --output data\short-hearing.sqlite --hearing-range-m 1
# Three fresh random mappings with paired controls, restart, replay and hostile-book probes:
.\.venv\Scripts\python.exe scripts\phase4_evidence.py --directory data\fresh-teaching-evidence
```

`recall` is bounded lexical lookup of authored `FACT symbol -> location` lines in an inhabitant's own original reports. It reports unverified claims, conflicting reports or unknown, never an engine fact. The successful teaching experiment uses an explicitly authored read/share baseline; it does not prove spontaneous LLM teaching or semantic understanding. [Phase 4 contracts and limits](docs/PHASE4_TEACHING.md) document channels, provenance, ledgers and branching.

## Cognition and memory

```powershell
# Authored deterministic cognition; no model server needed:
.\.venv\Scripts\python.exe -m underworld new --db data\minds.sqlite --config config\cognition.toml
.\.venv\Scripts\python.exe -m underworld advance --db data\minds.sqlite --ticks 100
.\.venv\Scripts\python.exe -m underworld mind --db data\minds.sqlite --agent agent-1 --query ingested
.\.venv\Scripts\python.exe -m underworld observe --db data\minds.sqlite --port 8765

# Optional pinned local CPU model: download once, verify SHA-256 and start a hidden server.
.\scripts\local-model.ps1 -Start
# Wait until http://127.0.0.1:8081/health reports ok.
.\.venv\Scripts\python.exe -m underworld new --db data\model.sqlite --config config\local-model.toml
.\.venv\Scripts\python.exe -m underworld advance --db data\model.sqlite --ticks 100
# Stop the specific server PID printed by local-model.ps1 when finished.
```

`think --db ... --agent agent-1` requests one budgeted thought without advancing physical time. `mind` is read-only privileged operator inspection, not a new capability granted to inhabitants. The observer shows selected identity, plan status and recent private episodes. `--manual` disables both automatic utility and cognition scheduling; explicit `think` remains available when the configured provider is enabled. A shared logical pause, killable timeout and deterministic fallback prevent slower inference from adding survival ticks to one inhabitant. See [Phase 3 contracts and limits](docs/PHASE3_COGNITION.md).

The optional downloads total about 406 MB before archive extraction; weights and binaries remain ignored. Downloading needs network access; inference uses loopback only. This host's measured Q8 360M model fits, but its reasoning and conversation are weak. Prompts/configuration live privately in the ignored SQLite run, with no secrets. Run the real measurement explicitly against a running server: `python scripts/phase3_evidence.py --server-pid <PID> --db data\fresh-evidence.sqlite`. Paths must be new; nothing is overwritten.

```powershell
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe --ctest C:\mingw64\bin\ctest.exe
# Constrained 900 s durable survival run plus a resource-free native control:
.\.venv\Scripts\python.exe scripts\survival_run.py --ticks 4500
# Optional mechanics benchmark (not required again for Phase 2):
.\.venv\Scripts\python.exe scripts\benchmark.py --ticks 10000
```

The durable benchmark includes full-state serialization, invariant checks and one FULL-synchronous SQLite commit per tick. It can take several minutes on this machine. Native and durable throughput, peak process working set, simulated duration and wall time are reported separately; neither measures inference. Benchmark databases are temporary; JSON evidence remains in `artifacts/`.

## Layout

- `core/`: authoritative kernel, pybind11 binding, native tests and legacy Phase 0 probe.
- `underworld/`: strict config/JSON, native loader, utility policy, private memory/cognition, operator teaching/branches, SQLite coordinator, CLI and observer.
- `config/`: seed, bounds, population, cognition declarations and event retention.
- `tests/`, `scripts/`: smoke validation and repeatable bootstrap.
- `docs/`: architecture, proposed contracts, limits, licenses, milestones, status.
- `opencode.json`, `.opencode/agents/`: project-local Codex-oriented agents plus TinyFish and Playwright MCP setup; see [OpenCode setup](docs/OPENCODE.md).
- `artifacts/`: archived Phase 0/1 evidence, Phase 2 tests/body/replay/survival evidence and actual observer screenshots.

Run commands from the repository root. There is no editable-install or binary packaging step yet. Runs pin config and code/build identities; change conditions through a new run or explicit fork. Linux/MSVC, long-horizon unattended operation, full-day model throughput and power-failure durability remain untested. See [status](docs/STATUS.md) for evidence and limits. Phase 9 adds a separately gated learning experiment; longer horizons, generations and true 3D mechanics remain deferred.
