# Underworld Lab handoff

## Active work

Milestone B from `Prompt/Alice_Living_World_New_Agent_Prompt.md`: add authoritative trees and finite reusable materials without changing legacy experiments.

## Completed in this continuation

- Verified the current session had only performed inspection; no earlier implementation or test outcome was assumed.
- Read the prompt, README, status, architecture/contracts, stabilization operations and relevant runtime/observer/storage modules.
- Added `docs/LIVING_WORLD_PLAN.md` with module mapping, contracts, dependency order and acceptance checks.
- Added an opt-in four-inhabitant configuration and a single `living-world` CLI entry point.
- Added observer reporting for the active controller and stabilization goal/budget attribution.
- Added native UW7 tree entities, growth accounting, harvest/felling/collection actions, material piles and occupied-placement validation.
- Added Python bindings/configuration/storage integration, DB8/checkpoint-schema-7 compatibility, focused tree tests and viewer colors/inspection fields.

## Compatibility and commands

Legacy configs and UW6/DB7 worlds remain historical and fail closed under the current UW7/DB8 runtime. New development run:

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

Run the focused tree/native/Python regression checks and a model-off living-world smoke run. If they pass, proceed to Milestone C (data-driven crafting and construction).
