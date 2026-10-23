# Continuing the H0–H5 gap profile

This is an opt-in source capability, with its own source contracts. Existing G
worlds, all H0–H5 studies and the executable keep their original runtime. The
new driver never imports Phase9's learner. Do not attach to scored evidence saves.
Use a working backup of a source-compatible H5 life; attachment preserves its
body, vocabulary, experience, random state and other people's private fields.

Windows PowerShell, existing native build:

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/adaptive_learner.py init --db data/my-adaptive.sqlite --seed 53
.venv/Scripts/python.exe scripts/adaptive_learner.py status --db data/my-adaptive.sqlite
.venv/Scripts/python.exe -m underworld.adaptive_panel --db data/my-adaptive.sqlite --port 8776
```

Open [the read-only evidence panel](http://127.0.0.1:8776/). A new learner correctly
has no outcome/signal meanings. The panel shows actual native action results,
current needs and pending plan, uncertain source-linked meanings, quality/reach
evidence and separate teaching, learned, authored, exploration and protection
counters. Human-readable glosses derive from the person's recorded observations;
they remain operator-only inferences. Models receive no panel data. POST requests
are refused; refresh never advances the world. The original viewer is untouched.

Existing H5 working-copy attachment requires explicit selected people:

```powershell
.venv/Scripts/python.exe scripts/adaptive_learner.py attach --db data/h5-working-copy.sqlite --agents agent-1 agent-2
```

First use the existing `storage.save` API to create the working backup with a
unique checkpoint name. Never copy only a SQLite file without its protected
epochs when that save requires them. Source mismatches, missing archives and
existing profiles refuse; do not re-pin old studies to bypass these checks.

The native action vocabulary and exploration/attention affordances are authored.
For a new profile, actual successful gather/consume warm-up must teach relief;
the continuing-world initializer performs this physically and accounts for all
supplies. An untrained `step` rests rather than inventing outcome knowledge.

```powershell
.venv/Scripts/python.exe scripts/adaptive_learner.py step --db data/my-adaptive.sqlite --agent agent-1 --id my-cycle-1
.venv/Scripts/python.exe scripts/adaptive_learner.py cohort-step --db data/my-adaptive.sqlite
```

`step` chooses from its own needs and learned relief, using visible sources,
personally remembered positions or fresh learned reports. Native approach,
gather and consumption run as durable frames. Repeating the same `--id` replays
the same result without repeating physics. A pending frame must resume with its
original cycle ID. `cohort-step` supplies durable round-robin identities and saves
its cursor; repeating a process after a commit interruption preserves scheduling.
Never create a new ID to conceal an unknown action outcome.

`observe --site` records a personally visited cell and current own visible sources.
There are three landmark slots. `encode --target ID --coin` privately coins absent
location/category factors; omit `--coin` for frozen production. `share` selects
new known information when a peer is locally visible. Its novelty/peer rule is
authored, not learned intention. Hearing does not validate a report's contents.
Reports expire after60 simulated seconds and are attempted at most once. Source
memories expire after120 seconds; observed depletion blocks reuse until a fresh
positive sighting. Valid scarcity stops before invalid gathering, without goal
credit. No resource is secretly replenished.

Optional context teaching uses the same real native deposit/speech channel:

```powershell
.venv/Scripts/python.exe scripts/adaptive_learner.py teaching-attach --db data/my-adaptive.sqlite --agents agent-1 agent-2
.venv/Scripts/python.exe scripts/adaptive_learner.py attend --db data/my-adaptive.sqlite --agent agent-2
.venv/Scripts/python.exe scripts/adaptive_learner.py teach --db data/my-adaptive.sqlite --agent agent-1
.venv/Scripts/python.exe scripts/adaptive_learner.py attend --db data/my-adaptive.sqlite --agent agent-2
```

Teaching requires real carried material, a nearby visible peer/resource and no
previous disclosure of that category/site to that peer. The receiver attends to
its own scene, not a supplied target. The teacher's peer model records its own
disclosures and labels understanding **unverified**; it never reads the receiver's
private dictionary/body. The demonstration-choice rule, exposure model and joint
attention are authored. This is self-initiated physical teaching, not evidence of
a learned teaching algorithm, grammar, request language or understanding others'
minds. No inventory means no demonstration. `act` is an explicit authored native
action instrument with stable `--id`, never a learned-policy success by itself.

Reproduce research in new unused paths; never overwrite registrations/evidence:

```powershell
.venv/Scripts/python.exe scripts/adaptive_study.py run --development --directory data/gap-new-dev --output artifacts/gap-new-dev.json
.venv/Scripts/python.exe scripts/adaptive_study.py run --directory data/gap-new-confirmation --output artifacts/gap-new-confirmation.json
.venv/Scripts/python.exe scripts/adaptive_audit.py --study artifacts/gap-new-confirmation.json --output artifacts/gap-new-audit.json
.venv/Scripts/python.exe -m unittest tests.test_adaptive tests.test_adaptive_surfaces tests.test_context_teaching -v
node scripts/verify_adaptive_panel.mjs http://127.0.0.1:8776/ artifacts/gap-new-browser
```

The frozen confirmation source manifest must still match. Both old online-learning
and strong authored/frozen/memory baselines are retained. Separate context-teaching
and resource/location trials do not constitute one learned language. Actual native
world databases are required by the independent audit; JSON summaries alone are
insufficient proof of execution or zero model use.

For longer operation, use a new explicitly named life, then repeatedly continue
that **same database**; do not re-run initialization between horizons:

```powershell
.venv/Scripts/python.exe scripts/adaptive_continuity.py init --db data/my-continuing-life.sqlite --output artifacts/my-life-initial.json
.venv/Scripts/python.exe scripts/adaptive_continuity.py run --db data/my-continuing-life.sqlite --until 300 --output artifacts/my-life-300.json
.venv/Scripts/python.exe scripts/adaptive_continuity.py run --db data/my-continuing-life.sqlite --until 900 --output artifacts/my-life-900.json
.venv/Scripts/python.exe scripts/adaptive_continuity.py run --db data/my-continuing-life.sqlite --until 1800 --output artifacts/my-life-1800.json
```

This scheduler controls all four bodies. Original native8kg food/16kg water are
finite, with regeneration disabled; training uses actual gathered material.
Source/evidence/action quotas stop explicitly. Finite observed survival is not an
indefinite-run guarantee. `adaptive_control.py` can compare matched backups of an
already continuing life against the unchanged H4 need policy. It gives both arms
the same actually observed legacy source memories and never pools their clocks.
Archive only with existing protected developmental APIs; never delete required
epochs. Native primitives, teaching circuits and scheduler frames have tested
recovery; an entire experimental curriculum remains a sequence of explicit stages.

The browser verification script expects an already trained four-person study
working copy containing actual learned signals. An empty newly initialized life
correctly has no such evidence and will not satisfy that fixture. The panel
itself can inspect either life without advancing it.

Recorded results and limits are in [the gap report](DEVELOPMENTAL_GAP_REPORT.md).
Portable exact traces use gzip; the auditor accepts `.json.gz` directly. Native
SQLite saves remain local under `data/`; the source commit contains their SHA256
inventory, not those saves. For the retained original experiment:

```powershell
.venv/Scripts/python.exe scripts/adaptive_audit.py --study artifacts/gap_confirmation.json.gz --output artifacts/my-gap-audit.json
.venv/Scripts/python.exe scripts/adaptive_continuity_audit.py
```

The continuity supplement targets the recorded local development paths and
rewrites only its audit output. It verifies the three contiguous windows and
secondary matched control. `package_adaptive_evidence.py` recreates exact gzip
archives from retained raw traces, inventories closed native saves and exercises
the auditor with disposable false reports. It does not change scored saves.
