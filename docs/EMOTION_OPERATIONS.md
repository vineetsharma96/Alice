# Run the opt-in F0-F3 profile

Use the project's existing Python environment and matching UW10W weather build.
The emotional core requires no additional dependency or model. If the weather
runtime is absent, build with `./scripts/build_weather.ps1`; existing worlds need
their exact matching build and source. Do not rebuild over a loaded module.

PowerShell, from the repository:

```powershell
# Create a NEW one-person weather world, leaving all previous worlds untouched.
.venv/Scripts/python.exe scripts/weather.py new --db data/my-weather-source.sqlite --population 1
# Native + policy state is backed up to an unused copy before attaching cognition.
.venv/Scripts/python.exe scripts/emotion.py attach --db data/my-weather-source.sqlite --destination data/my-emotion-world.sqlite
.venv/Scripts/python.exe scripts/emotion.py policy --db data/my-emotion-world.sqlite --id personal-frame-1
.venv/Scripts/python.exe scripts/emotion.py inspect --db data/my-emotion-world.sqlite
.venv/Scripts/python.exe scripts/emotion.py save --db data/my-emotion-world.sqlite --destination data/my-emotion-backup.sqlite
.venv/Scripts/python.exe scripts/emotion.py replay --db data/my-emotion-world.sqlite
.venv/Scripts/python.exe -m underworld.emotion_viewer --db data/my-emotion-world.sqlite --port 8778
```

Open http://127.0.0.1:8778 . The existing 3D weather scene and new private evidence
panel are read-only. GET, refresh, selection, wall time and pausing do not advance
time. POST refuses. A `policy` command advances an actual proposed native action.
Repeat the SAME id only to retry the SAME logical operation; a new intended action
needs a new id. `step --ticks N --id unique-step` advances native time without a
new policy decision and updates every enrolled person's own affect.

An existing compatible weather life can be copied, with all of its enrolled
inhabitants, through `emotion_store.attach(source,new_destination,agents=[...])`.
The CLI single-person example enrolls only the selected person; it is not a full
population scheduler. Existing UW9/H-learning worlds require their old runtime;
this profile does not migrate or discard their private learning/vocabularies.
Never replace a source hash or initialize over an existing file to bypass this.

After attachment, write only through the emotional coordinator. The old weather
viewer/replayer still works; an old weather WRITER does not update cognition and
will deliberately cause a drift refusal on the emotion head. Preserve that life
for diagnosis instead of resetting it. Both heads and journals commit atomically;
crash before commit leaves the previous state, retry never applies learning twice.

For a supplementary four-person finite-stock continuous life:

```powershell
.venv/Scripts/python.exe scripts/emotion_continuity.py --db data/emotion-life.sqlite --until 300 --output artifacts/my-emotion-life-300.json
.venv/Scripts/python.exe scripts/emotion_continuity.py --db data/emotion-life.sqlite --until 600 --output artifacts/my-emotion-life-600.json
```

The first invocation creates a new world only if the target does not exist. It
records real assigned roof construction and physical cohort placement near it,
copies that head, then enrolls all four.
Subsequent invocations continue the SAME save; `--until` is absolute native time.
The scheduler uses inherited weather cursor plus committed emotional policy count,
preserving resume order. No forcing, regrowth, refills or body resets are enabled.
Native rest/consumption/shelter goals are authored; learned contributions are
reported separately. Explicit wall/journal budgets stop without resetting the life.

Reproduce research in unused destinations (do not overwrite the retained study):

```powershell
.venv/Scripts/python.exe -m unittest discover -s emotion_tests -v
.venv/Scripts/python.exe -m unittest discover -s weather_tests -v
.venv/Scripts/python.exe -m scripts.emotion_study development --folder data/my-emotion-development --output artifacts/my-emotion-development.json.gz
.venv/Scripts/python.exe -m scripts.emotion_study confirm --folder data/my-emotion-confirmation --output artifacts/my-emotion-confirmation.json.gz --workers 2
.venv/Scripts/python.exe -m scripts.emotion_audit --folder data/my-emotion-confirmation --output artifacts/my-emotion-audit.json
```

Confirmation requires the exact44-file registration and five specified untouched
seeds. Its guided weather and assigned real feeding are conditioning apparatus,
not autonomous survival evidence. Raw compressed per-run results and actual SQLite
saves are distinct; audit requires the saves. Changing the frozen implementation
requires a new prospective study, not overwriting historical registration/results.
The independent auditor and continuity driver are supplementary and versioned
separately from the primary experiment.
