# F7 understanding durable slice

Implemented on October 22, 2026 as an additive copy-only overlay in
`underworld/others_store_f7.py`, using the existing general SQLite world through
`storage._connect` and `storage._head`.

## Durable contract

- `attach(source, destination)` requires a new destination, performs a SQLite
  backup, checks source bytes before and after initialization, and creates one
  independent directional inference state for every ordered pair of distinct
  native actors.
- `record_observation` validates that the supplied native observation is the
  observer's current native observation. A stale, foreign, or altered native
  observation is rejected. The native observation is not stored in the F7
  journal.
- The persisted command contains only a strict public envelope: observer and
  target IDs, bounded visible cues, and bounded witnessed social reports.
  Extra fields, target private mood/goals/memories/inventory/lexicon, and
  operator labels are rejected by the F7 estimator contract.
- `record_current_observation` derives a conservative public envelope directly
  from the current native snapshot using visible actor geometry, visible
  resource/shelter kinds, and public social-report edges. It never copies the
  target's body, inventory, private cognition, or operator diagnostics.
- Each journal operation stores a canonical operation ID, command, before hash,
  after hash, and deterministic result. Retrying an operation ID with the same
  command returns the prior result without applying evidence twice; a conflicting
  command is rejected.
- Evidence is bounded by the pure F7 estimator. Hypotheses include bounded
  belief, confidence, uncertainty, status, and source-event provenance. New
  public evidence recomputes retained evidence deterministically, allowing a
  later public cue to correct an earlier estimate.
- `inspect`, `save`, `resume`, and `replay` validate the overlay. Backups are
  no-overwrite SQLite copies and replay works in a fresh Python process.

## Scope and non-claims

F7 is a pure inference journal with a read-only native-observation projection.
It does not modify native behavior, scheduler
decisions, storage.py, F5 sources, F6 files, historical registrations, native
code, or viewer behavior. It does not expose or reconstruct target-private
state. The full prospective F7 study and scheduler integration are deferred.

## Checks

```text
python -m unittest tests.test_others_store_f7 tests.test_others_f7
python -m py_compile underworld/others_store_f7.py scripts/others_f7.py tests/test_others_store_f7.py
npm run lint
```
