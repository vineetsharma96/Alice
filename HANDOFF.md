# Underworld Lab - Milestone E handoff (21 October 2026)

Application 0.12.0 / stabilization/4; native UW9 / DB10 / checkpoint 9 remains
build 832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896.
Read [E report](docs/LIVING_WORLD_E_REPORT.md), [operations](docs/PLANNING_OPERATIONS.md),
[protocol](docs/PHASE_E_PLANNING.md) and [fixture amendment](docs/PHASE_E_EVALUATION_AMENDMENT_1.md).
Prior handoff: [archive](HANDOFF_PRE_E_ARCHIVE.md).

## Current behavior

Explicit per-agent authored hierarchical tasks run inside the existing single
writer: food/wood, axe/planks/trough, actual water delivery, animal care,
inspection and rest. Native requests remain authoritative. Urgent needs preempt
between primitives; deadlines, retries, cancellation and model attempts persist.
Private native receipt evidence can bias source choice and reference a reusable
authored procedure. Native workmanship is separate. Pen topology and teaching
remain unsupported, with explicit failure. No Phase 9 learner is active.

## Launch and resume

Use run.cmd, bash run.sh or dist/UnderworldLab.exe for the model-off desktop.
Choose a NEW --db path for E; never migrate/reset a previous controller save.
Source commands require UNDERWORLD_BUILD=build/living-d and the MinGW DLL path.

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe -m underworld living-world init --db data/e-user/run.sqlite --config config/living-world-e.toml --calls 0
.venv/Scripts/python.exe -m underworld living-world task --db data/e-user/run.sqlite --agent agent-1 --goal craft_tool
.venv/Scripts/python.exe -m underworld living-world run --db data/e-user/run.sqlite --seconds 60 --wall-seconds 240
```

The E profile has four humans/two animals in 16 m; confirmation uses smaller
one-human cases. Arbitrary population/layout success is not established.
The normal desktop rejects active model-assisted tasks; use the explicit CLI
model workflow described in operations. Models default off; E caps do not clear
A's recurring fair/global inference-budget gate or add AppContainer guarantees.

## Compatibility and evidence

Controller source pins cover stabilization.py, planning.py and planning_model.py.
The exact pre-E source/config/executable is preserved locally at
build/runtime-before-milestone-e-20261021. Its executable is for food-repair v3
saves; still earlier worlds require their respective archived full runtimes.
Do not mix source versions. Original C/D/food/Phase 9 artifacts remain historical.
The first E utility comparison was invalid; it and its registration are retained.
The corrected cohort uses seeds 1329/1449 with matched native starts and active
utility; E controller digest stayed frozen. See the report for exact results.

Verification: 209 Python tests (315.240 s), four native checks, lint/static/syntax,
real model comparison, broken-tool supplement, packaged source/save interchange,
E task CLI/model-off guard and both read-only viewers pass. The 120-continuous-
second production world uses 32.879 primary wall seconds; a fresh-process backup
resumes 90 seconds in 24.925 wall seconds to exact native state and eight tables.
Primary save: data/living-world-e-continuity-20261021/run.sqlite; counterpart:
data/living-world-e-continuity-20261021/resumed.sqlite. No refill/reset/growth.

Model assistance adds cost without a completion advantage. Source preference
changes later behavior but is slower when a temporary blocker has cleared.
Do not relabel this as general learning, new recipes, mastery or model training.
Evidence is under artifacts/living_world_e_*; raw new worlds under data/living-world-e-*.
The independent Phase 9 audit retains its failed gate and original sources.

## Next work

F: explicit initial knowledge and source-preserving embodied teaching/injection.
G: integrated four-person demonstration and E-aware bounded archival. A global
model budgets, general goal formation, arbitrary cargo/route/pen planning and
long-term husbandry remain incomplete. Breeding/cooking, speech and true 3D are
still deferred. No owned model/viewer process is intentionally left running.
Unrelated OpenCode/npm edits remain local and were not included in the E push.
