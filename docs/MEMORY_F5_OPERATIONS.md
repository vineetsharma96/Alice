# Running F5 emotional memory

Use the repository's existing Python environment and native weather build. No
new dependency, service, neural model or release version is required. F4 commit
16881c2 was pushed to origin/codex/mood-temperament before this work.

## Copy and run

From the repository, enroll a NEW copy of an existing compatible weather,
F0-F3 or F4 world:

```powershell
.venv/Scripts/python.exe scripts/memory.py attach --db data/mood-f4-life.sqlite --destination data/my-f5-copy.sqlite
.venv/Scripts/python.exe scripts/memory.py policy --db data/my-f5-copy.sqlite --agent agent-1 --id first-f5-choice
.venv/Scripts/python.exe scripts/memory.py inspect --db data/my-f5-copy.sqlite
.venv/Scripts/python.exe scripts/memory.py save --db data/my-f5-copy.sqlite --destination data/my-f5-backup.sqlite
.venv/Scripts/python.exe scripts/memory.py replay --db data/my-f5-copy.sqlite
```

Destination paths must not exist. Default enrollment covers all native actors;
`--agents agent-1 agent-2` explicitly selects a subset. `--memory-mode connected`,
`disconnected` or `frozen` is an enrollment choice, not an unlogged live toggle.
Stable logical IDs deduplicate retries and refuse conflicting reuse. A native
policy request may fail; inspect its original receipt rather than treating
accepted requests or proposed actions as completed goals.

On a fresh clone without local research saves, explicitly create a new weather
world at an unused path, then attach a new F5 copy. This creates a new life; it
does not resume one of the research trajectories:

```powershell
.venv/Scripts/python.exe scripts/weather.py new --db data/new-weather-source.sqlite --seed 53 --population 4
.venv/Scripts/python.exe scripts/memory.py attach --db data/new-weather-source.sqlite --destination data/new-f5-life.sqlite
```

Existing native build/setup instructions remain in the earlier README sections.

The F5 coordinator uses ALICE-MEMORY-F5-1 tables. It retains inactive historical
emotion/mood tables, native pending actions, bodies, stores, policy memories,
learner associations, episodes, temperament and scheduler origin. Original saves
are untouched. F5 starts a new empty private salience index; it does not fabricate
memory of earlier events or rewrite their existing journals. There is no migration
of UW9/H-language saves; these remain runnable with their own matching sources.

Resume an F5 copy through memory_store/memory.py. Earlier weather/emotion/mood
writers do not update its cognitive head and cause drift refusal. Source changes
fail closed; use matching archived source, never silently repin or reset a save.
Keep actual SQLite backups and source archives together. Journal quotas remain
10000 cognitive and25000 physical operations; stopping at a quota preserves the
life, not a license to clear its history.

## Continuous scheduler and observer

```powershell
.venv/Scripts/python.exe scripts/memory_continuity.py --source data/mood-f4-life.sqlite --db data/my-f5-life.sqlite --until 2100 --output artifacts/my-f5-2100.json
.venv/Scripts/python.exe scripts/memory_continuity.py --db data/my-f5-life.sqlite --until 2400 --output artifacts/my-f5-2400.json
.venv/Scripts/python.exe -m underworld.memory_viewer --db data/my-f5-life.sqlite --port 8780
```

Horizons are absolute simulated seconds on a native tick boundary. No automatic
simulation starts when viewing or opening a coding session. Each run has a600s
wall budget and stops on death; no rescue, refill or body reset. The driver
continues the inherited round-robin cursor and all inhabitants' own observations.
The read-only local observer exposes privileged diagnostics for the human;
inhabitants never consume its labels, private evidence or another person's state.

## Reproduce and check

```powershell
.venv/Scripts/python.exe -m unittest discover -s memory_tests -v
.venv/Scripts/python.exe -m scripts.memory_study development --folder data/NEW-f5-dev --output artifacts/NEW-f5-dev.json.gz
.venv/Scripts/python.exe -m scripts.memory_study confirm --folder data/NEW-f5-confirm --output artifacts/NEW-f5-confirm.json.gz --workers 2
.venv/Scripts/python.exe scripts/memory_audit.py --folder data/NEW-f5-confirm --output artifacts/NEW-f5-audit.json
```

Confirmation refuses source drift against artifacts/memory_f5_registration.json.
Use new paths, keep failures, and distinguish guided conditioning from autonomous
choices. Development files and final source seal have separate provenance; do
not reinterpret a failed development result using the final implementation.
F6 relationships, communication changes and full H/weather integration are not
part of this milestone.
