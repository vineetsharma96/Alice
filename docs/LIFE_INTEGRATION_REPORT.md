# Integrated inhabitants — 23 October 2026

The new opt-in `ALICE-LIFE-1` profile connects UW10W weather, seasons,
exposure, shelter, F0–F5 affect/mood/memory, and F6–F11 social modules to actual
native action execution. The earlier UW9 F12 sidecar remains available with its
own evidence. **Full master-prompt F12 acceptance is not achieved:** F8 causal
efficacy and several broader social gates remain open.

## Runtime and authority

`life_store.py` derives a checked copy of the existing atomic coordinator,
without editing any historical registered source. One transaction writes native
actions, policy state, each inhabitant's own cognitive updates and an idempotent
operation journal. F5 remains the single affect/mood engine. All native actors
are enrolled by default; inherited F5 bodies, memories, associations, pending
native actions, policy state and scheduler cursor are preserved on a new copy.
Historical cognitive tables remain inactive evidence after enrollment.

The executor gives urgent needs and protection priority. Optional decisions can
use directional relations, public need hypotheses, learned signal associations,
native-grounded gratitude, acquired recovery preferences and regulation scores.
The final proposal is submitted through unchanged native validation. Authored
local routes, transfer rules, signal/context labels and supply-search fallback
are explicitly attributed. No learned motor control is claimed. Supply search
uses only own observations and known bounds, with a 96-attempt budget.

F6 trust in a helper requires actual own material gain for symmetric native
`resource_given` reports. Giving does not mistakenly teach trust in the
recipient. F10 gratitude requires both that report and observed material benefit;
reciprocation is an actual feasible transfer with a protected own reserve.
F11 learns from actual fatigue relief, ingestion and completed transfers, rather
than emotional labels. Summaries are authored templates linked to retained facts.

F9 produces private opaque tokens through native `speak`. Listeners receive
only delivered tokens and learn from their **own** contemporaneous bodily
context. This is fallible co-occurrence, not access to the speaker's intended
meaning. No shared dictionary or LLM is involved. The authored categories
`calm` and `distress` are internal coding labels, not invented humanlike words.

## Prospective protocol and results

[Protocol](LIFE_INTEGRATION_PROTOCOL.md) was written before implementing and
measuring this profile. Development seed 61; held-out seeds 20301, 20309,
20317, 20323 and 20333. Separate databases retain connected, disconnected,
frozen, relationships-disabled and shuffled controls.

| Probe | Actual held-out result | Limit |
| --- | --- | --- |
| Native help and directional trust | 5/5: recipient trust rises, nonparticipant relations unchanged | Broader helper ranking/repair uses separately labeled synthetic mechanism histories; full F6 social gate is not established |
| F7 ambiguity/correction | 5/5 mechanism probes retain ambiguity and revise with new evidence | Public inference is wired into assistance material selection, but causal assistance benefit is unproven |
| Native signal acquisition | 5/5: 100% prediction on four post-training probes per seed; shuffled and frozen 0%; unfamiliar partner unknown | Two co-occurring body contexts, six demonstrations each; common exposure can explain success; no language emergence or general emotional understanding claim |
| Gratitude-like reciprocation | 5/5 connected: completed `give`; disconnected: `rest` | Only gratitude has real prerequisite grounding here; guilt, grief, envy, embarrassment and moral norms remain unsupported runtime capabilities |
| Recovery preference | 5/5: acquired preferences select recovery in two physical contexts; frozen does not acquire that goal | This demonstrates bounded choice influence, not superiority or human identity |
| F8 regulation | 5/5: real time-costed rest reduces fatigue and records its exact interval | **Learning benefit not established.** Runtime candidates are rest-duration variants sharing one efficacy table; this is insufficient evidence of useful learned strategy selection |
| Persistence | Every measured branch replayed and its backup matched | Explicit quotas apply; not indefinite operation |

Raw social results: `artifacts/life_heldout_20261023.json`.
Recovery results: `artifacts/life_recovery_heldout.json`. F8's improvement flag is
deliberately false because the experiment does not establish that comparison;
it is not a measured positive effect or evidence of statistical inferiority.
F6/F7 mechanism checks must not be described as naturally acquired interaction
histories or a fully passed stage. Later-stage probes remain bounded isolated
experiments while earlier full gates are pending.

Development failures are retained: v2 attempted weather forcing in a closed
world and correctly received `GUIDED_WEATHER_ONLY`; v3 had an experiment-result
path-formatting error after its first branch. Both were corrected in the runner
before held-out measurements. No validator was weakened. Development source
archives retain earlier versions; held-out source ZIP is in the experiment folder.

## All-inhabitant continuous worlds

Five separate closed four-person worlds each continued through 30, 90 and 180
simulated seconds. All 20 inhabitants survived; every one was scheduled, with
11–12 turns each by 180 seconds. Across final trajectories there were 224
completed native actions: 135 rest, 69 move, 12 gather and 8 drink; zero native
rejections. No eat occurred in this short horizon. Final needs are retained in
the raw report rather than treating survival as complete wellbeing.

Total execution plus replay wall times per world: 18.893, 32.522, 29.788,
28.233 and 22.562 seconds. Four-person peak private-state sizes at the final
checkpoint were 48,129–50,141 bytes per inhabitant. Memory index remains capped
at 32 links; social modules retain their finite evidence bounds.

An eight-person closed world reached 90 simulated seconds in 11.145 wall seconds
including replay. All eight survived and received 2–3 turns, with 17 rest and
five native speech actions completed and no rejection. This is a population
scaling probe, not an additional held-out seed.

Every world retained its source, native material ledgers, needs and scheduler.
Every final backup matched and passed fresh-process replay. Source hashes stayed
unchanged. Native ecology, animals, thermal processes and crafting mechanics are
enabled in new sources; animal actions and shelter construction were not scored
as autonomous achievements in these continuity runs. Zero food/water/forage
regeneration is configured; no rescues, resets, injections or hidden refills.

Raw results: `artifacts/life_continuity_heldout.json`. Actual worlds, backups and
source files remain under `data/life-continuity-heldout/`. These horizons do not
establish long-term survival or resource sustainability.

## Run, save and view

Use new paths; existing worlds are never automatically replaced:

```powershell
.venv/Scripts/python.exe scripts/life.py new --source data/my-life-source.sqlite --db data/my-life.sqlite --seed 61 --population 4
.venv/Scripts/python.exe scripts/life.py run --db data/my-life.sqlite --until 90 --output artifacts/my-life-90.json
.venv/Scripts/python.exe scripts/life.py run --db data/my-life.sqlite --until 180 --output artifacts/my-life-180.json
.venv/Scripts/python.exe scripts/life.py save --db data/my-life.sqlite --destination data/my-life-backup.sqlite
.venv/Scripts/python.exe scripts/life.py replay --db data/my-life-backup.sqlite
.venv/Scripts/python.exe -m underworld.life_viewer --db data/my-life.sqlite --port 8781
```

To preserve a compatible existing F5 life, explicitly enroll a **new copy**:

```powershell
.venv/Scripts/python.exe scripts/life.py attach --source data/memory-f5-final-life.sqlite --db data/my-integrated-copy.sqlite
```

Horizons are absolute simulated seconds; actual clocks are reported. A selected
policy action may finish beyond the requested horizon. Default wall budget is
600 seconds. Quotas remain 10,000 cognitive and 25,000 physical operations;
stop and retain the life at a quota rather than clearing history. Accepted
requests are distinguished from completed actions and achieved need goals.
Legacy baseline acceptances inferred from terminal receipts are counted in a
separate field from directly recorded submit acceptances.

The read-only observer displays weather/native state plus bodily affect, mood,
memory, directional relationships, public hypotheses, regulation, private signal
associations, social prerequisites, values and last decision influence. Browser
inspection at `http://127.0.0.1:8781/` confirmed loaded diagnostics and all four
selectable inhabitants. Its only console error was the absent favicon; this
does not affect the observer. Screenshot: `artifacts/life_observer_20261023.png`.

Reproduce the experiments using unused folders and result paths:

```powershell
.venv/Scripts/python.exe scripts/life_experiment.py --folder data/new-social-study --output artifacts/new-social-study.json
.venv/Scripts/python.exe scripts/life_recovery_experiment.py --folder data/new-recovery-study --output artifacts/new-recovery-study.json
.venv/Scripts/python.exe scripts/life_continuity_experiment.py --folder data/new-continuity-study --output artifacts/new-continuity-study.json
```

## Remaining work and preservation

This implements real runtime connections, but does not complete every research
gate. Distinct, feasible F8 strategies need prospective causal evaluation; F7
needs useful inference comparisons; F6 needs fully native helper reliability and
repair evidence. Other F10 states lack grounded prerequisites and remain deferred.
Historical H-series UW9 learning/communication worlds and vocabularies are
preserved with their original runtime. They are **not migrated into UW10W** or
silently merged into a new person's vocabulary. The integrated channel uses
native speech and new independent associations. No cross-format migration is
claimed. No LLM, neural training, reproduction or new 3D engine was added.

All 11 historical source registrations still match
(`artifacts/life_historical_integrity.json`), including F0–F5 and H-series seals.
Phase 9 remains failed and its learner remains outside these policies. The
upstream/license decisions in EMOTION_UPSTREAM_AUDIT.md are unchanged; new code
is original and adds no dependency. A full regression result is recorded in
`artifacts/life_full_suite.log` when completed.
