# Phase 1 persistence — ALICE-LIFE-2

Phase 1 persists the Phase 0 identity and private-observation contracts in a
new, copy-only SQLite destination.  It does not modify the source world or
rewrite native weather/life state.

## Attach boundary

`underworld.life_phase1.attach(source, destination)` accepts either:

- a native weather source, which is enrolled through the existing
  copy-only `life_store.attach` path; or
- an existing ALICE-LIFE-1 copy, which is backed up byte-for-byte first.

The destination must not already exist.  The source file hash is checked before
and after the copy.  A source that already contains Phase 1 tables is rejected;
use `save` for a backup instead of re-enrolling it.

At attach time, every selected native actor receives:

- one immutable identity record;
- one private native observation at the current native tick; and
- one operation record tying the records to the native state hash.

No names, traits, beliefs, or memories are invented.  Until an authored
identity operation exists, `public_name` is the explicit native actor ID and
the authored/self-model mappings are empty.

## Capture and readback

`capture(path)` records one private native observation per selected actor at the
current native head.  Repeating a capture at the same run/agent/tick is
idempotent.  It only writes Phase 1 sidecar tables; it does not advance the
native world.

Use `identities(path)` and `observations(path, agent_id=...)` for validated
contract readback.  `inspect(path)` returns a bounded human-readable summary;
it does not expose raw private observation payloads.

## Tables and replay

Phase 1 adds only these tables to the new destination:

- `phase1_meta`
- `phase1_identity`
- `phase1_observations`
- `phase1_operations`

Every payload has a canonical checksum.  `replay(path)` validates all Phase 0
records, row checksums, actor identity bindings and operation metadata.  Native
weather/life replay remains owned by the existing stores.

CLI:

```text
python scripts/life_phase1.py attach --source SOURCE --db DESTINATION
python scripts/life_phase1.py capture --db DESTINATION
python scripts/life_phase1.py inspect --db DESTINATION
python scripts/life_phase1.py observations --db DESTINATION --agent agent-1
python scripts/life_phase1.py replay --db DESTINATION
python scripts/life_phase1.py save --db DESTINATION --destination BACKUP
```
