# Phase 2 persistence — ALICE-LIFE-2 private memory

Phase 2 builds on a Phase-1 destination and persists explicitly supplied
private memories.  It does not infer memories from an operator projection, use
an LLM to invent content, or modify native weather/life state.

## Boundary

`underworld.life_phase2.attach(phase1_db, destination)` requires a Phase-1
database and a new destination.  It copies the complete Phase-1 database and
adds only Phase-2 tables.  Existing sources and Phase-1 records remain
unchanged.

`write_memory` requires:

- an enrolled native actor as owner;
- a non-empty `source_refs` list;
- every source reference to resolve to a Phase-1 observation ID or a source
  event ID carried by a Phase-1 observation;
- explicit content, memory kind, confidence, salience and provenance.

The memory record remains private and carries the `ALICE-LIFE-2` checksum.
Phase 2 does not generate a memory merely because an observation exists.

## Corrections

Memory payloads are never rewritten.  A correction is a new memory with
`supersedes=<old-memory-id>`.  The old record remains available and its
effective status is computed from an append-only `superseded` event.  Explicit
removal uses an append-only `invalidated` event.  `memory()` and `memories()`
return the sealed record plus `effective_validity` and lifecycle event IDs.

## Tables

- `phase2_meta`
- `phase2_memories`
- `phase2_memory_events`
- `phase2_operations`

`replay()` validates Phase 1, all memory checksums, source references,
owner/privacy bindings, supersession links and operation metadata.

## CLI

```text
python scripts/life_phase2.py attach --source PHASE1_DB --db PHASE2_DB
python scripts/life_phase2.py write --db PHASE2_DB --agent agent-1 \
  --memory-id memory-1 --kind episode --content '{"text":"..."}' \
  --source-ref 'capture:...'
python scripts/life_phase2.py memories --db PHASE2_DB --agent agent-1
python scripts/life_phase2.py invalidate --db PHASE2_DB --memory-id memory-1
python scripts/life_phase2.py inspect --db PHASE2_DB
python scripts/life_phase2.py replay --db PHASE2_DB
python scripts/life_phase2.py save --db PHASE2_DB --destination BACKUP
```
