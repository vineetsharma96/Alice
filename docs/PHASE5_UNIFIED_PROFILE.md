# Phase 5 persistence — ALICE-LIFE-2 unified profile

Phase 5 binds the five ALICE-LIFE-2 records into one lineage ledger.  It does
not add a sixth cognitive subsystem and does not modify native simulation
behaviour.

## Boundary

`underworld.life_phase5.attach(phase4_db, destination)` requires a Phase-4
database and a NEW destination.  It copies all upstream state and creates a
unified snapshot for each enrolled actor.  Existing worlds and upstream phase
databases remain unchanged.

Each unified snapshot binds, by checksum and stable ID:

- Phase 1 identity;
- the exact Phase 1 private observation at the snapshot tick;
- Phase 2 memories sourced from that observation or its source events;
- the Phase 3 body-need record at the same tick; and
- the Phase 4 affect trace at the same tick.

The snapshot has its own canonical lineage checksum.  It is a read-side
coordinator record, not a new source of native truth.  No memory, body state,
or affect state is invented by the coordinator.

Later captures first run the Phase 4 → Phase 3 → Phase 1 sidecar capture chain,
then append unified snapshots.  Native time is not advanced, and repeating a
capture at the same native state is idempotent.

## Readback and replay

`snapshot()` and `snapshots()` return validated lineage records.  `inspect()`
returns bounded human-readable counts.  `replay()` verifies Phase 1–4, every
source checksum, exact tick alignment, memory source linkage and the unified
lineage checksum.

Tables added by Phase 5:

- `phase5_meta`
- `phase5_snapshots`
- `phase5_operations`

CLI:

```text
python scripts/life_phase5.py attach --source PHASE4_DB --db PHASE5_DB
python scripts/life_phase5.py capture --db PHASE5_DB
python scripts/life_phase5.py snapshots --db PHASE5_DB --agent agent-1
python scripts/life_phase5.py inspect --db PHASE5_DB
python scripts/life_phase5.py replay --db PHASE5_DB
python scripts/life_phase5.py save --db PHASE5_DB --destination BACKUP
```
