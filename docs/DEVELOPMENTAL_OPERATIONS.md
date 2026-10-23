# Developmental research operations

Use the existing G native build. Models remain disabled. This is an opt-in
research path; ordinary G executables, saves and survival controllers keep their
original behavior. No package/application release label has been assigned.

The unified convenience CLI is `scripts/learner.py`. For example, these commands
continue the same new learner through two processes and retain its experiences:

```powershell
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/learner.py init --db data/my-persistent-learner/world.sqlite --seed 41
.venv/Scripts/python.exe scripts/learner.py food-trial --db data/my-persistent-learner/world.sqlite --alternatives resource-1 resource-2
.venv/Scripts/python.exe scripts/learner.py status --db data/my-persistent-learner/world.sqlite
```

Repeat `food-trial` or `status`, not `init`, in later sessions. `food-trial` is
explicit online adaptation, separate from frozen scored evaluation. The offered
candidate set is an authored task constraint. A no-feasible-candidate trial does
not mean the entire world has no food. Stronger world autonomy remains H4 work.
The same CLI offers `symbol-init`, `demonstrate`, `reference`, `reconcile` and
`archive`. Demonstration requires real carried supplies and visibility; it never
grants either. Reference takes a private speaker `--target` and public
`--alternatives`, but the listener function never receives the intended answer.

```powershell
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe -m underworld.developmental init --db data/my-new-learner/world.sqlite --seed 41
.venv/Scripts/python.exe -m underworld.developmental status --db data/my-new-learner/world.sqlite
.venv/Scripts/python.exe -m underworld.developmental choose --db data/my-new-learner/world.sqlite --agent agent-1 --targets resource-1 resource-2
```

Initialization refuses an existing file. This creates a new research cohort,
not a blank replacement for an existing inhabitant. Status is an operator audit;
policy access uses a principal-checked private API. The manifest declares the
novice profile's authored priors and initially absent learned content. Profiles
are limited practical knowledge, not a biological infant simulation.

The curriculum is run separately, against new named worlds:

```powershell
.venv/Scripts/python.exe scripts/developmental_study.py --split development --directory data/my-h1-development --output artifacts/my-h1-development.json
```

Confirmation requires a prospective source registration and the fixed held-out
seeds. Read [protocol](DEVELOPMENTAL_PROTOCOL.md) and
[record contracts](DEVELOPMENTAL_CONTRACTS.md) before interpreting results.
Native interventions introducing trial sources are declared scaffolding and
accounted boundary inputs. Native action completion is distinct from food-goal
completion. Short scaffolded research does not establish independent survival.

Save a compatible learner through the existing SQLite save command; the private
extension tables and random state are included. Use portable `--with-archives`
when epochs exist. Do not separate a saved DB from its required `.epochs`
bundle. Before requesting another learner action after interruption, use:

```powershell
.venv/Scripts/python.exe -m underworld.developmental reconcile --db data/my-new-learner/world.sqlite --agent agent-1
.venv/Scripts/python.exe -m underworld.developmental archive --db data/my-new-learner/world.sqlite
```

Reconciliation consumes a committed own receipt once. It never replays an
already submitted physical action. Missing sources, incompatible mechanisms,
conflicting requests and uncertain unsubmitted intents stop explicitly. Native
and private quotas remain enforced. No automatic source migration or forgetting
of referenced experience is provided.

Use the developmental archive command for learner saves. It additionally verifies
the private-table snapshot before native history pruning and prevents eviction
of source-bearing epochs. The generic G archive fingerprint knows nothing about
this opt-in extension. A protected-source retention quota is an explicit stop,
not permission to erase experience. See [development record](DEVELOPMENTAL_DEVELOPMENT_NOTES.md)
for the retained pre-repair study/source and repeat rationale.

The old continuous G world is separate. Starting a coding session or research
study does not reset that world, its bodies, memories or elapsed time. The Phase9
learner remains sealed and excluded; this path imports no Phase9 update code.

## Invented-symbol study

After the recorded repaired H1 gate passes, run a new developmental naming study:

```powershell
.venv/Scripts/python.exe scripts/symbol_study.py --split development --directory data/my-h2-development --output artifacts/my-h2-development.json
```

The primary learner uses no shared dictionary or model. Native deposit/speech
demonstrations teach private associations; message-only evaluation removes
deposits and freezes vocabularies. The learned scored arm resumes in a fresh
process. Silence, actual shuffled emissions, a private random control and a
privileged target-oracle comparator are explicit experimental branches. The
oracle is not a shared code and never enters learner state. See
[H2 protocol](DEVELOPMENTAL_H2_PROTOCOL.md). This is a three-class naming protocol,
not unrestricted language, spontaneous teaching or independent goal formation.

Research native saves/SQLite tables use the source runtime. The existing desktop
executable remains the G application, with its original capabilities and pins.
No developmental UI panel was added; H5 observer explanations remain deferred.

## Native H3 community verification

The incoming dictionary-only H3 experiment is retained but does not establish
native behavior. The replacement uses actual movement, speech, deposits and
inspection receipts. Read [the new protocol](DEVELOPMENTAL_H3_NATIVE_PROTOCOL.md).
H1/H2 and G default configurations are unchanged; only a new H3 cohort has four
people in a 32 by 32 metre world. There is no animal expansion in this study.

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/community_study.py --split development --directory data/my-h3-development --output artifacts/my-h3-development.json
.venv/Scripts/python.exe scripts/community_study.py --register artifacts/my-h3-registration.json
.venv/Scripts/python.exe scripts/community_study.py --split confirmation --registration artifacts/my-h3-registration.json --directory data/my-h3-confirmation --output artifacts/my-h3-confirmation.json
.venv/Scripts/python.exe scripts/community_audit.py --study artifacts/my-h3-confirmation.json --registration artifacts/my-h3-registration.json --output artifacts/my-h3-audit.json
```

All output worlds must be new paths. Each confirmation arm resumes a saved
training life in a new process. Branches are counterfactuals, not consecutive
episodes, and native needs/resources keep advancing. The independent audit
requires those local database files; checked-in compressed traces alone cannot
prove a live database exists. Missing databases fail explicitly.

For a separate manual research cohort:

```powershell
.venv/Scripts/python.exe scripts/learner.py community-init --db data/my-community/world.sqlite --seed 41
.venv/Scripts/python.exe scripts/learner.py recruit --db data/my-community/world.sqlite --agent agent-3
.venv/Scripts/python.exe scripts/learner.py community-status --db data/my-community/world.sqlite
```

`community-demonstrate` and `community-reference` accept the same explicit
speaker, listener, target and alternatives as the H2 commands. They require
actual visibility, hearing range and carried supplies; they grant none of these.
Teaching and tie-triggered repair are authored scaffolding. Unknown signals
remain uncertain, and a repair request is an authored flag, not invented grammar.
After an interruption, `community-reconcile --agent ID` reconciles a pending
native request and then its bounded memory. Repeat for the listener if interrupted
between grounding and budget consolidation. Do not reinitialize the cohort.

`npm start -- --seconds 0` now opens the existing native application's viewer.
It prefers the existing Windows executable, or uses the source virtual environment
and `build/living-d`. `PORT` forwards the native viewer port; the existing native
launcher options still apply. This entry point contains no separate JavaScript
simulation, cloned learner state, invented bodies or synthetic evidence panel.
