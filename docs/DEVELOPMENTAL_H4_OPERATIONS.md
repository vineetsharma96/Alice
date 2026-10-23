# H4 operations: native location reports and own-need decisions

Use the existing UW9 native build and source virtual environment. This adds no
release label, model, package dependency or changed browser panel. The G desktop
executable remains unchanged. Read the [protocol](DEVELOPMENTAL_H4_PROTOCOL.md)
before interpreting a task result. Use new paths; initialization refuses existing
saves. Keep all original sources with each research world.

## Reproduce the bounded study

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/wayfinding_study.py --split development --directory data/my-h4-study --output artifacts/my-h4-development.json
.venv/Scripts/python.exe scripts/wayfinding_study.py --register artifacts/my-h4-registration.json
.venv/Scripts/python.exe scripts/wayfinding_study.py --split confirmation --registration artifacts/my-h4-registration.json --directory data/my-h4-confirmation --output artifacts/my-h4-confirmation.json
.venv/Scripts/python.exe scripts/wayfinding_audit.py --study artifacts/my-h4-confirmation.json --registration artifacts/my-h4-registration.json --output artifacts/my-h4-audit.json
```

Registration must occur before confirmation, with no registered source edits
during measurement. The independent audit requires the actual local databases;
it refuses missing worlds and verifies native source records, replay and private
state. A compressed report alone does not substitute for a saved world.

The study trains resource identification and location associations separately.
A new source is placed at one of two personally visited landmarks. An authored
scout visits it, returns, then actually speaks one invented token. The recipient
cannot see the source from the hub. Enabled, muted, scrambled and identity-only
branches begin at identical native heads. An identity word conveys no location
in this trained protocol. These are single-token contexts, not learned syntax.

The assigned task is acquiring remote water. Base water remains available, so
success does not show communication is needed for survival. The one-site attempt
cap is authored; muted/unknown messages cause a private random choice among
previously visited sites. That fallback and missed feasible remote opportunities
are reported. Depletion after scouting must stop without invalid gathering or
false confirmation. The recipient's immutable report remains unverified; a
separate durable native-acquisition record supplies confirmation.

## Continue a trained life explicitly

Keep the experiment's evidence unchanged and create a standalone working backup:

```powershell
.venv/Scripts/python.exe -m underworld save --db data/my-h4-study/43-training.sqlite --name my-h4-life --output data/my-h4-life/world.sqlite --with-archives
.venv/Scripts/python.exe scripts/learner.py wayfinding-status --db data/my-h4-life/world.sqlite
.venv/Scripts/python.exe scripts/learner.py need-step --db data/my-h4-life/world.sqlite --agent agent-2
```

Repeat `need-step` on the same save, not initialization. It evaluates actual
current hunger/thirst and learned own consumption outcomes. Routing and motor
prerequisites are authored. It consumes suitable carried supplies before gathering
again, and can revisit a source remembered from its own observation. If no known
source resolves a need, it can use an actual learned location report; without
useful information it records an authored inquiry/inspection/rest affordance.
This is not a learned request word or autonomous scout recruitment.

`need-step --frozen` explicitly ignores learned relief predictions as a comparison.
It does not erase them. Passive persistence, same-state prediction dependence and
useful learning are different measurements. No automatic emergency survival
override is enabled; fallback counters remain visible. Native death and scarcity
are possible. Six-decision research evidence does not justify unattended operation.

To start a separate blank cohort, whose novice must still learn:

```powershell
.venv/Scripts/python.exe scripts/learner.py wayfinding-init --db data/my-blank-h4/world.sqlite --seed 43
```

## Manual native channel commands

The same `scripts/learner.py` CLI provides:

- `location-remember --agent ID`: record that person's actual current landmark;
  two slots/person. No coordinate or hidden map argument.
- `location-coin --agent ID`: privately invent a token at the current visited site.
- `location-learn --agent SPEAKER --listener RECEIVER --after-seq N`: learn only
  from fresh actual speech while both are visibly nearby in the same spatial cell.
- `scout-observe --agent ID`: store accessible water from that person's own sight.
- `scout-send --agent ID --communication enabled`: report that person's previous
  sighting after a real return journey. `muted`, `scrambled` and `identity` are
  explicit experimental comparisons, not policy conveniences.
- `location-receive --agent SPEAKER --listener RECEIVER --after-seq N`: decode a
  native message as an unverified report using the receiver's private associations.
- `follow-report` with those same arguments: attempt the assigned water context
  using only that receiver's own visited coordinates and current perception.

Movements, native resource introduction, carried demonstration supplies and
properly separated training contexts must be provided explicitly. Commands do
not grant them or copy another person's vocabulary. The finite spatial abstraction,
co-visit training, hearing partner identity and task context are authored priors.
Arbitrary relocation, noisy grounding, homonyms and unseen landmarks are untested.

## Interruption, evidence and limits

```powershell
.venv/Scripts/python.exe scripts/learner.py wayfinding-reconcile --db data/my-h4-life/world.sqlite --agent agent-2
.venv/Scripts/python.exe scripts/learner.py archive --db data/my-h4-life/world.sqlite
```

Reconcile a pending native request before another task. Native physical requests
retain exactly-once reconciliation. Location/outcome updates are atomic and
idempotent by native source identity; repeat the appropriate learning call after
an interrupted update only when its original proof remains available. Never
reset a body or reinitialize the save to clear an error.

The whole multi-action assigned scout circuit is not one atomic transaction.
Inspect state after interruption and resume the appropriate primitive. There is
no general exactly-once guarantee for replaying an entire circuit command.
Native/private quotas stop explicitly; do not delete evidence or repin sources
to bypass them. Referenced epoch eviction is refused by the developmental archive
wrapper. Audits assume one quiescent research controller. Long-term repeated
source checking, stale-report trust, general exploration and learning under
changing affordances remain limitations, separately from the bounded H4 gates.
