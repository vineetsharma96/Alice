# Alice / Underworld Lab

Alice is an experimental persistent world with inhabitants that have bodies,
needs, memories, private learned associations and social relationships. C++
implements physical laws and action validation; Python coordinates policies,
learning, persistence and a local browser interface. SQLite retains worlds
between runs.

The current integrated runtime is **ALICE-LIFE-1 on UW10W**. It connects weather,
exposure, shelter, affect, emotional memory and social modules to native actions.
It remains a bounded research system: full F12 acceptance, lifelong survival and
general intelligence have not been demonstrated.

**Start here:** [Run locally](#run-locally-on-windows) ·
[Manual controls](#manual-controls) · [Measured results](#measured-results) ·
[Remaining work](#remaining-work) · [Continuation handoff](HANDOFF.md).

## Run locally on Windows

### Requirements

- Python 3.11 or newer, CMake 3.20 or newer, and a C++20 compiler.
- The commands below use MinGW with `g++.exe` and `mingw32-make.exe` in
  `C:\mingw64\bin`. Set your actual toolchain path if it differs.
- A browser for the interface. The integrated emotional core does not require
  an LLM, API key or neural training.

Development verification used Windows, Python 3.12, MinGW GCC 15.2 and CMake
4.1.2. Linux/macOS and other compiler configurations are not certified by these
results. Compiler installation is separate from the bootstrap scripts.

### 1. Obtain the current development branch

```powershell
git clone --branch codex/emotional-memory https://github.com/vineetsharma96/Alice.git
cd Alice
```

For an existing checkout, retain your current worlds and local changes. The
paths below are examples for a **new** world; do not replace an existing save.
World databases, local models and compiled builds are not shipped in Git.

### 2. Build both native runtimes

Run from the repository root in PowerShell:

```powershell
.\scripts\bootstrap.ps1 -ToolchainBin 'C:\mingw64\bin' -SkipTests
.\scripts\build_weather.ps1 -ToolchainBin 'C:\mingw64\bin'

$env:PATH = 'C:\mingw64\bin;' + $env:PATH
$env:UNDERWORLD_TOOLCHAIN = 'C:\mingw64\bin'
$env:UNDERWORLD_BUILD = (Resolve-Path build/living-d).Path
$env:UNDERWORLD_CORE = (Resolve-Path build/living-d/underworld_core.exe).Path
$env:ALICE_WEATHER_BUILD = (Resolve-Path build/weather).Path
```

Bootstrap creates `.venv`, installs the pinned Python build dependency and
builds the UW9 runtime. The second script builds the separate UW10W weather
runtime used by integrated life. `-SkipTests` skips the historical bootstrap
verification; explicit checks appear [below](#verification).

Keep the environment settings in each new terminal that uses these builds.
Stop processes using a native extension before rebuilding it.

### 3. Create a world and open manual controls

```powershell
.venv/Scripts/python.exe scripts/life.py new --source data/my-life-source.sqlite --db data/my-life.sqlite --seed 61 --population 4
.venv/Scripts/python.exe -m underworld.life_control --db data/my-life.sqlite --port 8782
```

Open [the local control page](http://127.0.0.1:8782/) after the server starts.
The world starts **paused**. The first command creates a source world and a
separate integrated copy; both destination paths must be new. To reopen this
same world later, run only the second command.

## Manual controls

| Control | Effect |
| --- | --- |
| Step 1 tick | Advances one physical tick and its normal cognitive updates. |
| One inhabitant turn | Executes the next scheduled inhabitant's policy turn. |
| Run / Resume | Continues scheduling inhabitants with no overall tick or simulated-time limit. |
| Pause | Stops selecting new work after the current transaction completes. |

Closing the browser does not stop the server. Pause first to stop advancing;
use Ctrl+C in the server terminal to close it cleanly. Restarting opens the
same state and starts paused.

No overall tick limit does **not** remove resource, storage or integrity bounds.
The cognitive journal retains its 10,000-operation quota and the physical
journal its 25,000-operation quota. Food and water remain finite. This launcher
is not a validated unattended or indefinite-survival service.

Only one writer may own a save. Stop the control server before using the
headless writer on that database. A separate read-only viewer can coexist:

```powershell
.venv/Scripts/python.exe -m underworld.life_viewer --db data/my-life.sqlite --port 8781
```

Viewers do not advance the simulation. See [manual control details and
verification](docs/MANUAL_LIFE_CONTROL.md).

## Continue, inspect, back up and replay

With other writers stopped:

```powershell
# Inspect current needs, actions, decision origins and scheduler state.
.venv/Scripts/python.exe scripts/life.py inspect --db data/my-life.sqlite

# Continue the same world to successive absolute simulated-time horizons.
.venv/Scripts/python.exe scripts/life.py run --db data/my-life.sqlite --until 90 --wall-budget 600 --output artifacts/my-life-90.json
.venv/Scripts/python.exe scripts/life.py run --db data/my-life.sqlite --until 180 --wall-budget 600 --output artifacts/my-life-180.json

# Write a new backup and verify its operation history.
.venv/Scripts/python.exe scripts/life.py save --db data/my-life.sqlite --destination data/my-life-backup.sqlite
.venv/Scripts/python.exe scripts/life.py replay --db data/my-life-backup.sqlite
```

`--until` is an absolute time, not an added duration. A selected action may
complete slightly beyond it. Reports include simulated and wall-clock durations,
completed actions, achieved need goals, native rejection reasons, decision origins
and replay results. Accepted requests are distinguished from completed actions;
terminal receipts can imply acceptance, which is reported separately from direct
acceptance records. Valid JSON or a proposed plan is not counted as goal success.

Use new output and backup paths: commands refuse overwriting evidence.
Continuation preserves bodies, finite resources, memories, pending actions and
the scheduler cursor; it does not reset bodies between horizons.

To enroll an **existing compatible weather/F0–F5 save**, use `attach` on a new
copy instead of `new`:

```powershell
.venv/Scripts/python.exe scripts/life.py attach --source data/existing-weather-or-f5.sqlite --db data/new-integrated-copy.sqlite
```

That source must already exist locally and match its registered runtime.
Historical UW9 developmental worlds are not automatically migrated. Read
[integration operations and compatibility](docs/LIFE_INTEGRATION_REPORT.md).

## What is connected today

| Area | Current implementation and boundary |
| --- | --- |
| Physical world | Native bodies, action validation, finite materials, needs and persistent action execution. Rejection semantics remain authoritative. |
| Weather and shelter | Persistent weather, seasons, exposure and shelter effects in the UW10W runtime. |
| Everyday agency | Authored prerequisite-aware execution, local routes and bounded supply search, with explicit attribution. These are not learned motor intelligence. |
| F0–F5 | Private affect, mood and emotional memory; the existing F5 pipeline remains the single mood engine. |
| F6–F11 integration | Directional relationships, public inference, regulation scores, native private signals, grounded gratitude and acquired preferences. Several scientific gates remain open. |
| Communication | Private opaque tokens sent through native `speak`; recipients learn associations with their own bodily context. No shared dictionary or LLM-generated emergence. |
| Persistence | Atomic operation journals, source identity checks, backup and fresh-process replay. |
| Controls | Paused startup, single tick, inhabitant turn, pause and continuous scheduling. |
| Historical learning | H-series UW9 experiments and their private vocabularies remain preserved in their own profile; they are not migrated into integrated UW10W life. |

New foundation models are **isolated JSON research modules**, not live native
inhabitants or an extension of the integrated scheduler/viewer:

| Foundation | Implemented stages | Evidence |
| --- | --- | --- |
| Terrain, soil, minerals and water | G0–G3, bounded seeded manifests | [G01 report](docs/WORLD_GENERATION_G01_REPORT.md) |
| Plants and underground processes | G4–G7, finite nutrient accounting | [G47 report](docs/PLANT_UNDERGROUND_G47_REPORT.md) |
| Lifecycle and care | L0–L4 | [L02 report](docs/LIFECYCLE_L02_REPORT.md) |
| Ageing, development and lineage | L5–L9 | [L59 report](docs/LIFECYCLE_L59_REPORT.md) |
| Aggregate microorganisms | M0–M3 | [M03 report](docs/MICRO_ECOLOGY_M03_REPORT.md) |
| Further microbial ecology | M4–M8; disease disabled | [M48 report](docs/MICRO_ECOLOGY_M48_REPORT.md) |

The review corrected mass units, soil depth, care receipts/retries, lifecycle
rollback, checkpoint overwrites, plant nutrient spending and generation-order
validation. Corrected formats are `g01.2` and `g47.2`; older JSON requires its
matching archived sources. See [review details](docs/FOUNDATIONS_CODE_REVIEW.md).

## Measured results

These are separate bounded studies, not interchangeable claims of completion.

- Five held-out four-person worlds continued through 30, 90 and 180 simulated
  seconds. All 20 inhabitants survived and every inhabitant was scheduled.
  There were 224 completed native actions: 135 rest, 69 move, 12 gather and
  eight drink, with zero rejections. No eating occurred in this short horizon.
- One eight-person world reached 90 simulated seconds; all eight survived.
  It completed 17 rest and five speech actions with zero rejections.
- Execution plus replay took 18.893–32.522 wall seconds per four-person world
  and 11.145 seconds for the eight-person probe. Final backups passed
  fresh-process replay; source hashes stayed unchanged. No hidden refills or
  body resets were used.
- Five held-out seeds demonstrated bounded native signal association and
  gratitude-like reciprocation with controls. Signal prediction on four
  post-training probes per seed was 100%, versus 0% for shuffled and frozen
  controls; an unfamiliar partner remained unknown. This is a small contextual
  association experiment, not human language.

Read the [prospective protocol](docs/LIFE_INTEGRATION_PROTOCOL.md) and
[actual results and limitations](docs/LIFE_INTEGRATION_REPORT.md). Survival over
these horizons does not establish sustainability or complete wellbeing.

## Verification

The latest pre-push focused run on 23 October 2026 passed **77 tests and three
subtests in 34.81 seconds**. It covered the foundation modules and fixes,
ordered integration, integrated life, code audit and manual controls.
[Retained test output](artifacts/github_push_checks.log).

Earlier integrated-life verification passed **465 tests and 352 subtests in
944.78 seconds**, plus four native checks in 0.38 seconds. That full-suite run
predates the latest foundation additions; it is historical evidence, not a
fresh full-tree result. See [scope and logs](docs/LIFE_VALIDATION.md).

After building and setting the environment above, run the focused checks:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p test_integrated_life.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -p test_life_control.py -v
.venv/Scripts/python.exe -m unittest discover -s tests -p test_foundations_review.py -v
```

For the full Python and native suites:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
ctest --test-dir build/living-d --output-on-failure
```

Run checks separately from live writers. Reproduction of an old experiment
requires its matching source registration, protocol and world, not simply the
latest code. Large local databases are excluded from Git; published reports
and tracked artifacts describe the retained evidence and its limitations.

## Formats and historical entry points

| Profile | Use and compatibility |
| --- | --- |
| UW9 | Earlier survival, developmental learning/communication and sidecar studies. Requires its matching runtime and source identity. |
| UW10W + ALICE-LIFE-1 | Current opt-in integrated life with weather and social cognition. Compatible weather/F0–F5 saves enroll through an explicit new copy. |
| G/L/M JSON sidecars | Standalone foundation studies with their own format versions; not native world saves. |

Source mismatches fail closed. Do not repin an old world, rescale its data or
reset its body to make it load under new laws.

`run.cmd`, `run.sh` and the optional `UnderworldLab.exe` package launch the
**legacy UW9 desktop profile**, not the integrated manual-control runtime
described above. A compiled executable is not included in a fresh clone.
Keep those entry points for their documented legacy use. See
[earlier instructions and milestone history](README_HISTORY.md).

## Remaining work

- Full F12 acceptance remains unpassed. Useful learned regulation benefit,
  broader relationship repair and causal assistance gates need further evidence.
- Historical H-series learning and vocabularies are not migrated into UW10W.
- Terrain is bounded to at most 64 × 64 cells. Minecraft-style streamed chunks,
  an infinite world and true 3D physical simulation are not implemented.
- G/L/M foundations still need prospective integration and validation before
  affecting native inhabitants. Reproduction is not a connected live feature.
- Indefinite operation, long-term resource sustainability, autonomous animal
  care and autonomous crafting were not established by the population runs.
- Other proposed social emotions lack grounded prerequisites and validated gates.

The Phase 9 learner **failed its original advancement gate**. Its thresholds,
report and historical evidence stay unchanged, and that learner remains outside
live autonomous policies. Later work does not retroactively turn that result
into a pass. See [Phase 9](docs/PHASE9_REPORT.md) and
[failed/deferred features](docs/FAILED_AND_DEFERRED_FEATURES.md).

## Repository guide

| Location | Purpose |
| --- | --- |
| `core/`, `CMakeLists.txt` | Earlier native simulation and build definition. |
| `weather_native/` | Separate UW10W native runtime. |
| `underworld/` | Persistence, policies, cognitive modules and local servers. |
| `scripts/` | Builds, evaluations, audits and command-line operations. |
| `tests/` | Python regression and research checks. |
| `Prompt/` | Supplied specifications; proposals do not by themselves prove implementation. |
| `docs/` | Protocols, stage reports, operations and limitations. |
| `artifacts/` | Tracked evidence, logs, registrations and source archives. |
| `data/` | Local worlds and experiment databases; ignored by Git. |

[HANDOFF.md](HANDOFF.md) records continuation context. Consult
[status](docs/STATUS.md), [architecture](docs/ARCHITECTURE.md),
[action contracts](docs/CONTRACTS.md) and [model limits](docs/MODEL_LIMITS.md)
before extending the system. The [archived README](README_HISTORY.md) preserves
earlier descriptions; its dated session URLs and milestone claims are historical.
