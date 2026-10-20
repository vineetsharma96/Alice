# Knowledge workflows

Milestone F, application 0.13.0. Native UW9 / DB10 / checkpoint 9. Every command
requires the matching source runtime, MinGW DLL path and UNDERWORLD_BUILD set
to build/living-d. Model calls are not required.

## Explicit starting knowledge

Create a NEW named world. Existing paths are refused. The default profile is
`none`; no new knowledge is added during attach, run, save, resume or a new chat.
Named profiles are `basic_survival`, `woodcraft`, `livestock_care`, `specialist`.
Choose exactly one recipient. Others retain empty initial knowledge assignments.
The versioned per-person manifest is in run metadata; the recipient receives an
`external_initialization` episode. No read event or skill is invented.

```powershell
.venv/Scripts/python.exe -m underworld living-world init --db data/f-new/world.sqlite --config config/living-world-e.toml --calls 0 --knowledge-profile woodcraft --knowledge-recipient agent-1
```

For a custom lesson, use `--knowledge-profile specialist --knowledge-recipient
agent-2 --knowledge-text lesson.txt`. This reads bounded plain text. Profiles are
recorded information, not access controls on E's existing authored recipes or
survival executor. E task assignment still supplies its authored decomposition;
starting without a profile does not erase that code or pretrained facts.

## Embodied teaching in an existing compatible world

Use an already guided world or create an explicit guided branch with `fork`.
The original world remains unchanged. In either observer, pause and select
Place book or Speak through avatar. Native placement and source ledgers apply.
Book text enters private memory only after a completed native `read`; avatar
speech reaches only actual audible recipients under distance/occlusion laws.
An avatar message is not a one-person targeting guarantee. Broadcast is global.

A fresh manual laboratory can be started explicitly with:

```powershell
.venv/Scripts/python.exe -m underworld new --db data/f-manual/world.sqlite --config config/knowledge-lab-f.toml --manual
.venv/Scripts/python.exe -m underworld observe --db data/f-manual/world.sqlite
```

Native `write_book` requires an accessible native report or own validated batch
event, at least 0.01 kg carried inert material, and five seconds of writing.
An injected episode is not a native event reference: test it physically first
before citing the resulting native validation in a book. Reading costs native
time. All received text remains an unverified report even if its author cites
an earlier successful test; a changed context or false lesson can fail.

## Explicit one-person injection

In a paused guided observer, select the inhabitant, then choose **Inject unverified
knowledge into selected inhabitant**. Both viewers display separate counts for
initialization, injection, reading, hearing and physical knowledge tests.
This is a privileged operator action. It supplies only text to one person's
private episode store. It creates no native action, read event, skill, body,
material, executable code or model weights. Hostile strings remain textContent.

The desktop runner and observers attached to stabilization worlds are read-only;
their teaching forms stay disabled. Use the CLI intervention between controller
runs for those worlds. The writable `observe` command is for legacy/manual worlds
and still refuses a second scheduler on a stabilized save.

CLI equivalent: save a JSON file using the current run/branch/tick from `inspect`:

```json
{
  "schema_version": 1,
  "run_id": "CURRENT-RUN-ID",
  "branch_id": "CURRENT-BRANCH-ID",
  "intervention_id": "unique-lesson-id",
  "observation_version": "CURRENT-TICK",
  "kind": "inject_knowledge",
  "parameters": {"recipient": "agent-1", "text": "An unverified lesson"}
}
```

```powershell
.venv/Scripts/python.exe -m underworld intervene --db data/f-new/world.sqlite --request injection.json
.venv/Scripts/python.exe -m underworld knowledge --db data/f-new/world.sqlite --agent agent-1
```

The request uses the existing writer lease, branch authorization, SQLite atomic
commit, intervention idempotency and bounded journals. A conflicting id, stale
tick, extra fields, wrong recipient, closed world or disabled episodic retention
fails. Text is at most 1024 UTF-8 bytes. No overwrite/migration is implicit.

## Bounded procedure test and audit

`knowledge --test-episode ID` explicitly tests an own accessed apparatus lesson
in the existing strict `PROCEDURE` format. It uses an authored laboratory driver,
not an autonomous teacher or model planner. It performs one native process action;
there is no search, heating, navigation, retry or privileged answer lookup.
Arrange those prerequisites with ordinary physical actions first. Native request
rejection, terminal failure and terminal completion remain distinct.

A durable own `knowledge_test_intent` precedes execution. The native result and
`knowledge_test` source link commit together through memory.capture; an interrupted
intent can remain pending and is not silently retried or credited. Native replay
verifies retained injection records as no-physics decisions; it does not claim to
reconstruct the whole cognitive history from an initial native checkpoint.

Full demonstration evidence links external lesson episode -> test request -> native
validation event -> artifact writing -> second person's read -> second native test.
The audit may inspect all private stores as operator evidence. Acting drivers use
only their own lesson and permitted native observations. No recipient can query
someone else's private episodes through the test API.

```powershell
.venv/Scripts/python.exe scripts/phase_f_demo.py --split development --directory data/f-example --output artifacts/f-example.json
```

The demo authors an explicit randomized apparatus lesson. It is not evidence of
animal-care generalization, autonomous teaching, intelligence or mastery. E's
`teach_procedure` hierarchical goal remains unsupported. No neural training.

## Compatibility

F changes the orchestration/controller source identities. Old E worlds require
the exact archived E executable/source/config in
`build/runtime-before-milestone-f-20261021`. There is no automatic migration.
Do not open old worlds with a new runtime expecting reset or conversion. Backups
are actual SQLite backups and include all identity, episode and controller tables.
Finite storage quotas still stop safely; F does not provide long-term compaction.
