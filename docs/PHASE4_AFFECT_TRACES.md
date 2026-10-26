# Phase 4 persistence — ALICE-LIFE-2 affect traces

Phase 4 builds on a Phase-3 destination and records the private affect state
already present in the integrated-life runtime.  It does not create a second
affect engine, infer hidden causes, use an LLM, expose operator projections as
private state, or change native policy/action behaviour.

## Boundary

`underworld.life_phase4.attach(phase3_db, destination)` requires a Phase-3
database and a NEW destination.  It copies upstream state and captures one
affect trace per enrolled actor.  Each trace is a sealed `affect_trace`
contract with:

- body signals from the private runtime state;
- recorded appraisal when present, otherwise `explanation_status=unavailable`;
- fast affect and slow mood fields as recorded;
- explicit emotional-memory and social-change references when present;
- private/derived provenance; and
- a source reference to the exact Phase-3 body snapshot at the same native tick.

Later captures append matching Phase-3 body observations first, then append
affect traces without advancing native time.  Repeating a capture at the same
native state is idempotent.

## Readback and replay

`affect_trace()` and `affect_traces()` return validated private records.
`inspect()` returns bounded counts and native status.  `replay()` verifies
Phase 1–3, trace checksums, private ownership/provenance, interval ordering,
and equality of each trace's body source/tick.

Tables added by Phase 4:

- `phase4_meta`
- `phase4_affect_traces`
- `phase4_operations`

CLI:

```text
python scripts/life_phase4.py attach --source PHASE3_DB --db PHASE4_DB
python scripts/life_phase4.py capture --db PHASE4_DB
python scripts/life_phase4.py affect-traces --db PHASE4_DB --agent agent-1
python scripts/life_phase4.py inspect --db PHASE4_DB
python scripts/life_phase4.py replay --db PHASE4_DB
python scripts/life_phase4.py save --db PHASE4_DB --destination BACKUP
```
