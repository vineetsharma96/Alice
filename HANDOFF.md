# Underworld Lab handoff

## Active work

Milestone A from `Prompt/Alice_Living_World_New_Agent_Prompt.md`: consolidate the stabilized runtime without changing legacy experiments.

## Completed in this continuation

- Verified the current session had only performed inspection; no earlier implementation or test outcome was assumed.
- Read the prompt, README, status, architecture/contracts, stabilization operations and relevant runtime/observer/storage modules.
- Added `docs/LIVING_WORLD_PLAN.md` with module mapping, contracts, dependency order and acceptance checks.
- Added an opt-in four-inhabitant configuration and a single `living-world` CLI entry point.
- Added observer reporting for the active controller and stabilization goal/budget attribution.

## Compatibility and commands

Legacy configs and UW6/DB7 worlds remain unchanged. New development run:

```powershell
.venv/Scripts/python.exe -m underworld living-world init --db data/living-world/run.sqlite
.venv/Scripts/python.exe -m underworld living-world run --db data/living-world/run.sqlite --seconds 30
.venv/Scripts/python.exe -m underworld living-world status --db data/living-world/run.sqlite
.venv/Scripts/python.exe -m underworld observe --db data/living-world/run.sqlite --read-only --port 8766
```

## Checks and evidence

Run after implementation from the repository root:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_stabilization
```

No long-horizon or model-enabled run is claimed here. No owned process is running and no database was created by this handoff.

## Next acceptance check

Run the model-off living-world command sequence, save/resume its database, then proceed to Milestone B only after the native and stabilization regression checks pass.
