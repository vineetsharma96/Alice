# Phase 3 persistence — ALICE-LIFE-2 body needs

Phase 3 builds on a Phase-2 destination and persists native body-need
snapshots.  Native body state remains authoritative for action legality,
resource transfer, health changes and death.  Phase 3 does not create survival
actions, change mortality, or infer a cause for a body change.

## Boundary

`underworld.life_phase3.attach(phase2_db, destination)` requires a Phase-2
database and a NEW destination.  It copies the complete upstream database and
captures the initial native body state for every enrolled actor.  Existing
sources and upstream records remain unchanged.

Each snapshot is a sealed `body_need` contract with:

- native hunger, thirst, fatigue, health and alive values;
- exact native tick and observation version;
- private/native provenance; and
- a source reference to the exact Phase-1 observation carrying the native body.

Later `capture` calls first add matching private Phase-1 observations in the
Phase-3 destination, then append body snapshots.  Capture never advances the
native world and is idempotent for the same native state.

## Readback and replay

`body_need()` and `body_needs()` return validated sealed records.  `inspect()`
returns only bounded counts and native status.  `replay()` verifies Phase 1,
Phase 2, body checksums, owner/privacy bindings, source observation existence,
and equality with the native observation body values.

Tables added by Phase 3:

- `phase3_meta`
- `phase3_body_needs`
- `phase3_operations`

CLI:

```text
python scripts/life_phase3.py attach --source PHASE2_DB --db PHASE3_DB
python scripts/life_phase3.py capture --db PHASE3_DB
python scripts/life_phase3.py body-needs --db PHASE3_DB --agent agent-1
python scripts/life_phase3.py inspect --db PHASE3_DB
python scripts/life_phase3.py replay --db PHASE3_DB
python scripts/life_phase3.py save --db PHASE3_DB --destination BACKUP
```
