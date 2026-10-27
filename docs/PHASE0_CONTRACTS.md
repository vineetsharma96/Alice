# Phase 0 contracts — ALICE-LIFE-2

Phase 0 freezes the boundary for the next five-subsystem implementation without
changing native behaviour or existing `ALICE-LIFE-1` saves.

## Scope

`underworld/life_contracts.py` defines sealed, deterministic shadow records for:

- `identity`
- `observation`
- `memory`
- `body_need`
- `affect_trace`

Every record carries the `ALICE-LIFE-2` profile, contract version, owner, run,
branch, native tick, observation version, source event IDs, provenance, privacy
scope and a canonical SHA-256 checksum.

## Invariants

- Native observations are always private and native-provenance records.
- Memory source references are explicit; source records are not overwritten by
  summaries or corrections.
- Body values are bounded to `[0, 1]`; `alive` is explicit.
- Affect traces store both interval ticks and separate body/appraisal/fast/slow
  fields.
- Unknown versions, privacy changes, provenance changes, malformed ranges and
  checksum changes fail closed.
- These records are shadow-only in Phase 0. They are not attached to existing
  databases yet.

## Compatibility gate

No native checkpoint schema, `ALICE-LIFE-1` table, frozen source registration,
or existing save is modified by this phase. Phase 1 may persist these records
only in a new copy-only destination after the shadow tests and replay contract
are extended.
