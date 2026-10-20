# Stabilized everyday-action execution

The opt-in controller expands survival goals into **authored** prerequisite steps. A model can select an eat/drink goal; it does not invent the navigation, gathering or consumption algorithm. Phase 9's failed learner is not used.

## Fresh world

Run from the repository root. Initialization refuses an existing file.

```powershell
.venv/Scripts/python.exe -m underworld.stabilization init --db data/stabilized/run.sqlite --calls 0
.venv/Scripts/python.exe -m underworld.stabilization run --db data/stabilized/run.sqlite --seconds 120 --wall-seconds 240
.venv/Scripts/python.exe -m underworld.stabilization status --db data/stabilized/run.sqlite
```

Initialization uses the existing survival configuration: eight inhabitants, dt=0.2 s, finite food/water and no regeneration. Benchmark timings for a selected inhabitant at dt=1 s are not performance guarantees for this default population/configuration.

For the existing pinned local model, start its loopback server with `scripts/local-model.ps1 -Start`, then use a **new** world:

```powershell
.venv/Scripts/python.exe -m underworld.stabilization init --db data/stabilized-model/run.sqlite --model --calls 2
.venv/Scripts/python.exe -m underworld.stabilization run --db data/stabilized-model/run.sqlite --model --endpoint http://127.0.0.1:8081 --seconds 120 --wall-seconds 240
```

The call limit is per inhabitant for the lifetime of this controller state. Re-running `run` resumes it and does not reset the budget. Model failures, non-survival choices overridden by needs, and later deterministic selection after the inference budget/interval are recorded explicitly. All prerequisite execution remains authored. Failed inference reservations consume budget after interruption.

## Existing inhabitants

Pause/stop the current writer first. Preserve the original with a named SQLite backup, then explicitly hand the backup to the new controller:

```powershell
# Replace the source filename with a compatible UW6/DB7 run you own.
.venv/Scripts/python.exe -c "from underworld import storage; storage.save('data/your-run.sqlite', 'stabilization_handoff', 'data/stabilized-existing.sqlite')"
.venv/Scripts/python.exe -m underworld.stabilization attach --db data/stabilized-existing.sqlite --calls 0
.venv/Scripts/python.exe -m underworld.stabilization run --db data/stabilized-existing.sqlite --seconds 120
```

Attach performs a logged, explicit scheduler handoff. It disables automatic utility/cognition dispatch, marks pending legacy plans as superseded, and retains the native checkpoint, pending physical actions, resources, needs, identities, episodes and prior journals. Controller call/goal/navigation schedules then persist in additional checksummed tables. It does not migrate incompatible older native/runtime formats. Attaching twice is rejected; use `run` to resume.

Default attachment controls all inhabitants. Benchmark internals explicitly select actor 1 and leave actor 2 as the logged competition fixture. Do not interpret that benchmark as validation of every possible multi-actor crowd arrangement.

Known Phase 9 study paths are protected from attachment. Do not use a copy of its study world to imply that its failed learning gate has changed. Use new stabilization worlds or explicit backups of ordinary compatible runs.

## Observation and provenance

Use the existing viewer as a reader while the controller owns the writer lease:

```powershell
.venv/Scripts/python.exe -m underworld observe --db data/stabilized/run.sqlite --read-only --port 8766
# Open http://127.0.0.1:8766/viewer
```

Use the stabilization `run` command to advance these worlds. The legacy viewer's manual resume and the Phase 7 supervisor do not drive this new executor. The new runner is a bounded host-side development controller, not a newly verified AppContainer service or a 24-hour deployment.

Native `decisions` and receipts retain their existing semantics. Additional `stabilization_events` record goal selection, source, inference reservation/result, request reservation and terminal feedback. Native requests from this controller appear as external submissions, with explicit authored attribution in the control journal:

The legacy observer's provider setting and cognition-call count describe the disabled legacy scheduler. New controller calls live in its own checksummed state/events; use stabilization status and benchmark artifacts for those counts. A legacy count of zero does not mean the attached model controller made no inference calls.

- `model_selection`: the model selected the goal; execution is authored.
- `authored_need_selection`: deterministic need selection and authored execution.
- `deterministic_fallback`: provider failure, need override, or selection after the model budget/interval.
- `external_native_consumption_not_executor_credit`: another native action achieved consumption; the executor must not claim that action.

Valid JSON, successful compilation, accepted request, terminal completion and achieved consumption are separate facts. Eating/drinking goals require an actual increase in the corresponding ingested-mass reservoir. A completed gather alone does not complete an eat/drink goal.

## Interruption and bounds

A request reservation commits before the native tick. If the native journal contains the request after a restart, the controller waits for/reconciles its receipt rather than submitting it again. An unsubmitted reservation is discarded and replanned from fresh perception. These are separate transactions, not an atomic cross-table/native commit. A native action completed just before a crash can be reflected in logical goal state on the next controller tick.

Goals have at most two physical failures, 24 movement steps and 120 simulated seconds; absent observed supply gets a short bounded search. Audit events have an 8192-record quota and a 64-KiB payload cap. Existing native request/checkpoint/storage limits still apply. A capacity-blocked or inaccessible goal is recorded as blocked; this implementation does not provide arbitrary cargo rearrangement or a general planner. Finite repeated runs can eventually exhaust resources or quotas.

Save with the existing `storage.save` API. Backup includes controller tables. Inspecting status checks their checksums/source identity; replay checks the native recorded physical commands. Keep the pinned controller source for existing attached worlds: source changes require an explicit version/migration decision, not silent reinterpretation of stored plans.

Evaluation design: [STABILIZATION_PROTOCOL.md](STABILIZATION_PROTOCOL.md). Results and limitations: [STABILIZATION_REPORT.md](STABILIZATION_REPORT.md).
