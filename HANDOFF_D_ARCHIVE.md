# Underworld Lab handoff — Milestone D

D's bounded native animal/care/food-production loop is implemented. Read [D report](docs/LIVING_WORLD_D_REPORT.md) and [contract/protocol](docs/PHASE_D_ECOLOGY.md) before continuing. The historical C handoff is [archived separately](HANDOFF_C_ARCHIVE.md).

## Current runtime and scope

Package 0.11.0; **UW9 / DB10 / checkpoint 9 / stabilization/3**. Native build `832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896`. No migration or reset of old worlds. Exact source/build pins apply. Keep C and failed Phase 9 evidence intact. The original C binary remains in build/living-c, but older saves require their complete original Python/native runtime. The pre-hysteresis D candidate binary remains in build/d-before-hysteresis-20261020; its candidate databases/evidence are retained separately.

Two fictional species use native authored local sensing, collision, needs and behavior. Forage is finite with an explicit optional biomass boundary source, default zero. Real feeding/trough actions affect reserves and receipt-backed familiarity; physical fences/gates contain animals. Eggs debit reserves with explicit residue; new food ages conservatively through storage/transfers. Human care is an externally assigned bounded procedure, not autonomous learning. The failed Phase 9 learner remains outside policies.

Final review fixed a native water/forage threshold oscillation; the new regression requires both animals to actually drink and eat reachable forage. The previous candidate and its observations remain recorded. Final measured care: 300 continuous simulated seconds per case, development seed 21 and new held-out 303/404. Care improves survival to 5/6 versus 0/6 untreated, but one hen dies and another case ends with very low health. Raw route failures remain visible; no reliable husbandry claim.

## Build, inspect and continue

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
cmake -S . -B build/living-d -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$((Resolve-Path .venv/Scripts/python.exe).Path)"
cmake --build build/living-d --parallel 2
$env:UNDERWORLD_BUILD = (Resolve-Path build/living-d).Path
# CONTINUE the compatible saved four-person/two-animal world. Do not init it again.
.venv/Scripts/python.exe -m underworld living-world status --db data/living-world-d-four-hysteresis-20261020/run.sqlite
.venv/Scripts/python.exe -m underworld living-world run --db data/living-world-d-four-hysteresis-20261020/run.sqlite --seconds 30 --wall-seconds 180
.venv/Scripts/python.exe -m underworld observe --db data/living-world-d-four-hysteresis-20261020/run.sqlite --read-only --port 8766
# Explicit NEW experiment only:
.venv/Scripts/python.exe -m underworld living-world init --config config/living-world-d.toml --db data/my-NEW-ecology/run.sqlite --calls 0
# Separate explicitly authored evaluation fixtures; refuse an existing output directory.
.venv/Scripts/python.exe scripts/phase_d_eval.py --output data/my-NEW-care-evaluation --evidence artifacts/my-care-evaluation.json
.venv/Scripts/python.exe scripts/phase_d_continuity.py --output data/my-NEW-continuity --evidence artifacts/my-continuity.json
.venv/Scripts/python.exe scripts/verify_living_world.py --build build/living-d --output artifacts/my-checks.json
```

Ordinary config/living-world.toml retains its four-human profile. Animals require the D config. The existing survival scheduler does not automatically select woodcraft or husbandry goals. Observers are read-only on stabilized worlds; the CLI owns logical time.

## Evidence

Final verification: **176 Python tests / 4 native checks pass**. Four humans/two animals: 120 continuous simulated s / 163.338 primary wall s; fresh-process continuation 119.440 wall s separately, exact native + eight-table + identity parity. All six bodies health 1.0, four human drink goals, 15 accepted/completed actions, no failed/rejected human request. Zero model calls. This window demonstrates drinking, not human eating or long-term survival.

- artifacts/living_world_d_evaluation.json: six 300-second cases, all food/water/body balances exactly zero, complete native replay parity from 120 seconds, zero model calls, raw accepted/rejected/terminal distinctions.
- artifacts/living_world_d_checks_final.json: current full Python/native regression results and sealed Phase 9 hash checks.
- artifacts/living_world_d_continuity.json: current four-person/two-animal SQLite run, simulated/wall duration, fresh-process backup continuation and eight memory/controller table comparisons.
- artifacts/living_world_d_viewer.json/png: functional headless/software-rendering check, not a hardware performance claim.
- artifacts/living_world_d_phase9_audit.json: 3439 retained files, four sealed sources, recomputed metrics match, advance false.
- artifacts ending _before_hysteresis.json and data/living-world-d-four-20261020 retain the superseded native candidate. Final candidate uses the explicitly named hysteresis directories above.

## Remaining work

Breeding and actual heat/fuel-coupled cooking remain deferred and have no exposed action contract. No neural training, reproduction, speech or true 3D was added. Metabolism/food quality/waste remain declared abstractions. Waste is retained in aggregate ledgers; no detailed manure/nutrient cycle or sustainability claim.

Milestone E is next only when requested: general prerequisite planning and recovery over crafting/care, measured adaptation and attribution. Fix care quantity choice, stale reach and obstruction recovery there; do not silently change this evaluation after seeing held-out failures. F is knowledge/teaching and G the integrated demo. A's recurring fair per-agent/global wall-token model budgets are still missing, so keep model calls at zero until that separate acceptance gate is met. New supervisor isolation, archival/compaction, full-day multi-seed survival and sustained eight-person operation remain unverified.

Changes are local; this request does not push or overwrite prior experiments. Preserve the existing unrelated OpenCode/npm work.

The verifier-owned read-only viewer on port 8767 was stopped; no model server was started. The existing user viewer on port 8765 was not controlled.
