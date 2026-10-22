# F4 runtime and compatibility

F4 uses the existing offline Python environment and unchanged native UW10W
weather build. It introduces no dependency, service, neural training or release.
Source guards preserve the exact F0-F3 runtime and its research worlds.

PowerShell, from the repository, using unused destinations:

If no compatible save exists, first create a one-person source with
`.venv/Scripts/python.exe scripts/weather.py new --db data/new-weather-source.sqlite --population 1`,
then use that source in the attachment command below.

```powershell
.venv/Scripts/python.exe scripts/mood.py attach --db data/emotion-life-20261022.sqlite --destination data/my-mood-life.sqlite --temperament balanced
.venv/Scripts/python.exe scripts/mood.py inspect --db data/my-mood-life.sqlite
.venv/Scripts/python.exe scripts/mood.py policy --db data/my-mood-life.sqlite --agent agent-1 --id my-first-frame
.venv/Scripts/python.exe scripts/mood.py save --db data/my-mood-life.sqlite --destination data/my-mood-backup.sqlite
.venv/Scripts/python.exe scripts/mood.py replay --db data/my-mood-life.sqlite
.venv/Scripts/python.exe -m underworld.mood_viewer --db data/my-mood-life.sqlite --port 8779
```

Default attachment enrolls every native inhabitant, inheriting their F0-F3 mode,
learned cue values, stress, episodes, factual history links and pending body state.
Choose `--agents ...` explicitly to restrict enrollment, or `--profile` explicitly
to override the inherited learned/frozen/disconnected/disabled mode. Balanced,
sensitive and calm are authored initial parameter presets; no trait learning or
random temperament occurs. The API also accepts validated numeric parameters or
an explicit per-person map. `--disconnected-mood` retains mood but disables its
additional caution-threshold influence. It does not erase existing learned cues.

Only a NEW SQLite backup copy is changed. New ALICE-MOOD-F4-1 tables retain a
replay root, origin hash, inherited scheduler offset and the parameter selection.
Copied old emotion tables remain inactive historical evidence. Original source
worlds remain byte-identical. UW9/H-profile migration is still unsupported;
their separate learning and communication histories are preserved in their worlds.
After handoff, use only the mood writer for that copy. Legacy writer use causes
intentional head-drift refusal; do not bypass source checks or reset a life.

F4 derives a separate profile from our own frozen code using checked literal
hooks in `profile_derivation.py`. It verifies all44 legacy pins and expected hook
occurrence counts, then compiles the deterministic variant in its own namespace.
Only our fixed repository source is compiled; no world/user/model text enters
those hooks. The original stress update is replaced, not executed and overwritten.
Native physics and the original Python files are never changed. New namespaces,
schema and request/update IDs separate F4 continuation from old history.

The new slow stress tracks a declared body-discomfort target with separate rise
and recovery constants. Mood valence derives from that one slow state; it is not
a second independent mood engine. Fast affect still uses the old short time scale.
Constant-input integration is timestep independent; changing bodies are sampled
at interval endpoints, as before. Pausing causes no wall-clock decay.

F4 mood only eases a negative learned-cue threshold by at most.04. It cannot
create a threat prior, ignore urgent needs, invent a roof, remove injury or
bypass native validation. Native movement cost and retry cooldown still apply.
This additional effect is authored, not acquired regulation or personality.

For all-person continuous execution, preserving inherited scheduler order:

```powershell
.venv/Scripts/python.exe scripts/mood_continuity.py --source data/emotion-life-20261022.sqlite --db data/my-mood-cohort.sqlite --until 1500 --output artifacts/my-mood-1500.json
.venv/Scripts/python.exe scripts/mood_continuity.py --db data/my-mood-cohort.sqlite --until 1800 --output artifacts/my-mood-1800.json
```

The first call copies an existing life. Later calls resume the SAME mood copy;
`--until` is absolute native time. Cursor is inherited offset plus committed F4
policy count. No supplies, mood, memories or bodies are reset. Wall/journal quotas
stop explicitly and leave the life recoverable. A manual one-agent `policy` call
is not an all-person scheduler.

Reproduce development/confirmation in NEW directories and outputs:

```powershell
.venv/Scripts/python.exe -m unittest discover -s mood_tests -v
.venv/Scripts/python.exe -m scripts.mood_study development --folder data/my-mood-development --output artifacts/my-mood-development.json.gz
.venv/Scripts/python.exe -m scripts.mood_study confirm --folder data/my-mood-confirmation --output artifacts/my-mood-confirmation.json.gz --workers 2
.venv/Scripts/python.exe -m scripts.mood_audit --folder data/my-mood-confirmation --raw artifacts/my-mood-confirmation.json.gz --output artifacts/my-mood-audit.json
```

Confirmation requires the exact55-file registration. The independent auditor is
supplementary and records its own source hash. Its exponential-law/body checks
are separate from replay. Controlled weather and finite-stock native feeding
are assigned apparatus, not autonomous survival or learned regulation. F5 onward
requires its own authorization, implementation and prospective gates.
