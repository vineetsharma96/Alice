# Underworld Lab handoff

## Current milestone

Living-world **C: crafting/construction**, implemented and verified within the bounded scope in [LIVING_WORLD_C_REPORT.md](docs/LIVING_WORLD_C_REPORT.md). B's 142-test baseline passed, but review found and fixed growth overshoot, >3-species restore, stone/actor spawn overlap, remote harvest anchors, entity-limit overflow and stale tree meshes.

C adds native data-driven recipes, owned axes/durability/scrap, finite felling/planks/offcuts, reserved construction sites with saved work, real box/trough stock and solid fence/gate behavior. The production fixture is explicitly operator assigned; its target resolution uses permitted observations. It is not autonomous learned woodcraft. Recipe truth, assigned procedure evidence and authored skill counters remain separate. The failed Phase 9 learner stays excluded.

## Compatibility and launch

Package 0.10.0; **UW8 / DB9 / checkpoint schema 8 / stabilization/3**. Exact build/source pins also apply. No migration or world rewrite. UW6/DB7 and UW7/DB8 need their original full runtime. The root build is historical; current native loading rejects it. Use:

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
cmake -S . -B build/living-c -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$((Resolve-Path .venv/Scripts/python.exe).Path)"
cmake --build build/living-c --parallel 2
$env:UNDERWORLD_BUILD = (Resolve-Path build/living-c).Path
# Inspect or CONTINUE the existing verified four-person world; do not init it again.
.venv/Scripts/python.exe -m underworld living-world status --db data/living-world-c-four-release-20261020/run.sqlite
.venv/Scripts/python.exe -m underworld living-world run --db data/living-world-c-four-release-20261020/run.sqlite --seconds 30 --wall-seconds 120
.venv/Scripts/python.exe -m underworld observe --db data/living-world-c-four-release-20261020/run.sqlite --read-only --port 8766
# Explicitly NEW production or continuity experiments:
.venv/Scripts/python.exe scripts/phase_c_demo.py --output data/my-NEW-production
.venv/Scripts/python.exe scripts/phase_c_continuity.py --output data/my-NEW-continuity --evidence artifacts/my-continuity.json
```

For a fresh ordinary four-person world, use `living-world init --db <NEW path> --calls 0`. Production examples do not silently attach/reset old saves. Stabilized worlds require read-only viewer attachment; the CLI owns their scheduler.

## Verification and evidence

- Final current native build: `8c10de9ec672c0fd37baf6a7262d96a234ee7341b9bf0523d3a63dbb84cc35af`.
- 160 Python tests / 4 native checks pass; 26 additional current crafting/viewer checks pass. See `artifacts/living_world_c_checks_final.json` and `living_world_c_targeted_checks.json`.
- One-person production: seed 20261020, 8 m fixture, 21 accepted/completed requests, 55.6 simulated s / 7.543 wall s, zero model calls. `data/living-world-c-measured-20261020/run.sqlite`; raw receipts in `artifacts/living_world_c_demo.json`.
- Four people: seed 20261020, 16 m region, 120 continuous simulated s / 107.250 primary wall s; 15 native completions, four drink goals, no rejection, all alive. Backup at 30 s and fresh-process 90 s continuation took 77.828 wall s separately; native head, eight memory/controller tables, run and branch IDs match. `data/living-world-c-four-release-20261020/{run,resumed}.sqlite`.
- Native material/energy invariants and replay pass. Tree growth is explicitly sourced; food/water regeneration is zero. The 300-case seed sweep verifies initial placement only.
- Headless Edge/software-rendering viewer check passes; `artifacts/living_world_c_viewer.{json,png}`. No hardware performance claim.
- Independent Phase 9 audit verifies 3439 files and unchanged failed gate; no original study or thresholds changed.
- The first C full-check lease fixture failure and interrupted/superseded candidates remain retained. The PID-verified fixture preserves actual exclusion/release assertions; production leases were not weakened.

Owned verifier viewer on port 8767 was stopped; no model server was started. Existing unrelated OpenCode/npm files were preserved; config validation passed, external TinyFish connectivity was not tested. C changes are local and have not been pushed.

## Next work

Milestone D is next: native animal/forage/trough/pen mechanics, then validated food production. Read the original prompt and C contract before changing formats. General woodcraft planning/recovery/learning is E; teaching/knowledge profiles are F. Animal containment and integrated G are not completed by circular fence tests.

**Outstanding A gate:** recurring/fair per-agent and global wall/token model budgets are still missing from the other agent's wrapper. Keep model-off operation until that integration has its own measured validation. New controller isolation, long-term archival/compaction, full-day/multi-seed survival and sustained 8-person operation remain unverified. Do not reuse historical stabilization scores as current UW8 performance evidence.
