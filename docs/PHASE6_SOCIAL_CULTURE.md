# Phase 6 persistence — ALICE-LIFE-2 social and cultural provenance

In the ALICE-LIFE-2 persistence sequence, Phase 6 adds an append-only ledger
for optional social interactions and explicitly authored cultural artifacts.
It does not force cooperation, create native actions, infer trust, or expose
another inhabitant's private state without a recorded access event.

## Boundary

`attach(phase5_db, destination)` requires a Phase-5 destination and a NEW copy.
`record_event` stores a bounded interaction such as speech, gift, offer,
response, shared task, artifact read or departure. Every event has enrolled
participants and at least one Phase-1 observation/source-event reference.

`write_artifact` stores an explicitly authored procedure, book, report or tool.
Artifact content is not returned by ordinary listing. A non-owner must use
`read_artifact` with its own enrolled identity and a source reference; that
operation records an `artifact_read` event and grants access to that reader.
This is modeled access, not omniscient UI telemetry.

All records are checksummed and private. `replay` verifies upstream Phases 1–5,
source references, owners, participants, artifact access and operation rows.
No neural weights, native action rules or automatic scientific progress are
added by this phase.

Tables:

```text
phase6_meta
phase6_events
phase6_artifacts
phase6_operations
```

CLI:

```text
python scripts/life_phase6.py attach --source PHASE5_DB --db PHASE6_DB
python scripts/life_phase6.py event --db PHASE6_DB --event-id e1 --kind speech --actor agent-1 --other agent-2 --source-ref OBS_REF
python scripts/life_phase6.py artifact --db PHASE6_DB --artifact-id book-1 --owner agent-1 --kind procedure --content '{"text":"..."}' --source-ref OBS_REF
python scripts/life_phase6.py read --db PHASE6_DB --artifact-id book-1 --reader agent-2 --source-ref OBS_REF
python scripts/life_phase6.py replay --db PHASE6_DB
```
