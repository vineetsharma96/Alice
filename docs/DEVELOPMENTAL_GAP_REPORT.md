# H0-H5 gap closure: bounded adaptive behavior

Completed 22 October 2026; experiments measured 21 October. This is a separate,
opt-in source profile, not a replacement of any historical study or a new
executable release. The prospective [protocol](DEVELOPMENTAL_GAP_PROTOCOL.md)
and fourteen source files were frozen in `artifacts/gap_registration.json`
before five held-out seeds were evaluated. Development used seed 53 only;
confirmation used 11003, 11027, 11047, 11057 and 11071 without subsequent tuning.

## What changed

| Area | Implemented and measured | Remaining boundary |
| --- | --- | --- |
| H0 profiles and persistence | Explicit attachment to selected compatible H5 working-copy inhabitants; bodies, old experience and vocabularies preserved; other people untouched | Older incompatible contracts require an explicit migration, not automatic attachment |
| H1 behavior from experience | Separate material-outcome and reach evidence prevents an out-of-reach attempt from poisoning all food associations; monotonic distance transfer improves new choices | Authored representation, distance ordering and bounded exploration; narrow task, not general intelligence |
| H2 private symbols | Separate private production and comprehension; additional category/location meanings grounded in actual deposits and heard signals | No shared dictionary, LLM labeling or unrestricted language |
| H3 teaching and community | Teacher chooses a previously undisclosed local category/site from its own observations and inventory; receiver attends its own scene; durable teaching resumes once | Novelty, attention and teaching choices are authored. A disclosure is not proof of the peer's understanding; no learned teaching intention |
| H4 everyday agency | Persistent approach/gather/consume frames and round-robin cursor; depleted and stale reports are bounded; need-driven goals and self-triggered source reports | Authored motor, need and information-sharing rules; restricted source and memory budgets |
| H5 combination reuse and inspection | Private category/location factors support a held-out resource/location combination and actual remote gathering/drinking; separate read-only evidence panel | Authored factorization/intersection mechanism; no discovered syntax, grammar or conversation |

The new files are `underworld/adaptive.py`, `context_teaching.py`,
`adaptive_panel.py`, their new web assets, separate CLI/study/audit/continuity
drivers and regression tests. Original `developmental.py`, `symbols.py`,
`community.py`, `wayfinding.py`, `composition.py`, `learning_panel.py`,
`scripts/learner.py`, native code and all registered G/H0-H5 sources remain
byte-identical. No native validator or rejection semantics changed.

## Why the original online learner failed

The old H1 online diagnostic grouped reachable and unreachable food together
inside a coarse distance bin. Native `OUT_OF_REACH` results reduced the same
association used for feasible nearby food, leading to abstention. This was a
representation/update problem, not invalid JSON or an engine accepting an
impossible action. Its original failed result remains unchanged.

The new profile records distance separately. A completed gather updates material
outcome evidence; an out-of-reach rejection constrains reach evidence. `BUSY`
and other rejection classes do not become evidence that food is worthless or
unreachable. A successful distance supports nearer observations and a failed
distance constrains farther ones. This ordering is an authored prior, not a
learned physical law or a hidden exact reach predicate. Native validation still
decides whether every attempted action succeeds.

Persistent plan frames revalidate inventory, needs and locally available evidence.
Plans gather before eating/drinking, consume carried material first, and stop
when a source is depleted. Reports expire after 60 simulated seconds, source
memories after 120; a failed report is not retried without new local evidence.
Plans have a 96-action bound. Logical action and cycle IDs prevent retries from
duplicating physical actions across interruption, archive and fresh-process
resume. State mismatches and missing evidence stop explicitly.

## Held-out results

All protocol gates passed and were independently recomputed from native SQLite
saves, checksum-protected private records and action receipts by
`scripts/adaptive_audit.py`. The audit also checked all six historical source
registrations, final private state, native replay/invariants and zero model calls.

### Outcome/reach transfer

Each seed contained six new reachable and six new unreachable opportunities,
following the original failure diagnostic and development-only training.

| Policy | Completed nearby food acquisitions / 30 | Attempts at new unreachable targets / 30 | Balanced prequential Brier loss |
| --- | ---: | ---: | ---: |
| New adaptive profile | 30 | 0 | 0.139451 |
| Unchanged legacy online learner | 0 | 0 | 0.253086 |
| Frozen baseline | 30 | 30 | 0.250000 |
| Memory-only baseline | 30 | 30 | 0.250000 |
| Authored exact-distance control | 30 | 0 | 0.000000 |

Registered thresholds were at least 27/30 nearby successes, at least nine more
than legacy, and at most 15 new far attempts and half the frozen count. The
legacy policy's zero far attempts also accompany 30 missed feasible nearby
opportunities. The new result distinguishes safe abstention from indiscriminate
abstention. The authored control demonstrates that this task can be solved
without learning; it is not evidence for the learner.

Across the entire online diagnostic/training/transfer streams, native reach
rejections were adaptive 5, legacy 20, frozen 55, memory 35 and authored 0.
The adaptive five were its initial range exploration, one per seed; necessary
exploration and genuinely unreachable targets are reported separately from
missed feasible actions. The Brier score measures predictions on this balanced
task; it does not establish calibrated semantic confidence or broad uncertainty
calibration.

### Symbol combinations with actual everyday utility

People first personally visit three 8 m location cells and observe ten actual
physical teaching events: food at all three sites and water at the first two,
twice each. Water at the third site is the held-out combination. A scout observes
that source, returns and emits its private category/location sequence. The
recipient must interpret the actual native heard event, travel, gather the
correct remote source and drink 0.05 kg with positive own thirst relief.
Operator target labels are used only for scoring.

| Fresh-process continuation | Completed remote acquisition and thirst relief / 5 |
| --- | ---: |
| Learned factors | 5 |
| Muted message | 0 |
| Scrambled factors | 0 |
| Whole-message lookup | 0 |

The registered threshold was 5/5 learned and an advantage of at least two over
each control. All arms start from matched native heads and preserve their private
state. There were 135 new completed native requests across scored cooperation
arms and no cooperation native rejection. Each successful learned continuation
took 25 simulated seconds; its starting clock varied with physical training
(248-280 seconds). These results require actual gathering, ingestion and relief,
not just an accepted request, emitted signal or generated plan.

Context-triggered teaching produced ten native-grounded receiver updates across
five seeds, versus zero in matched muted controls. Each teacher became quiet
after its two own disclosures. It does not inspect the listener's dictionary or
claim that the listener understood. The decision to teach is still an authored
novelty rule; native feedback updates private meanings. No LLM was used, no
shared dictionary was inserted, and no general language-emergence claim follows.

## Continuous operation and accounting

One four-person development life used physically executed warm-up actions,
ending at 117 simulated seconds. Subsequent windows ran in fresh processes
against the same saved world, with no body, learner, RNG or scheduler reset.

| Continuous clock | Frames in window | Wall seconds | Food stock kg | Water stock kg |
| --- | ---: | ---: | ---: | ---: |
| 117 to 329 | 51 | 37.618 | 7.60 | 15.25 |
| 329 to 926 | 138 | 135.899 | 6.40 | 13.40 |
| 926 to 1806 | 206 | 245.332 | 4.60 | 10.60 |

Total measured continuation time was 418.850 wall seconds, excluding warm-up.
At 1806 seconds all four inhabitants were alive with health 1, hunger 0.456 and
thirst approximately 0.409; each completed 42 need-relief goals (168 total).
Native resource stock plus carried mass plus ingested mass equals initial food
8 kg and water 16 kg throughout. No regeneration, boundary inputs, operator
material or operator interventions occurred. At 329 seconds, the accounting
explicitly includes 0.05 kg water still carried between gathering and drinking.

An additional, separately labeled development control copied the actual
1806-second life into matched branches and gave both policies the same genuinely
observed legacy source memories. The new policy reached 2114 simulated seconds
with 28 additional goals in 64 frames and 171.900 wall seconds. Unchanged H4
`wayfinding.policy_step` reached 2100 seconds with 28 goals in 226 frames and
334.030 wall seconds. Both ended with food 4 kg and water 9.8 kg, all four alive
at health 1 and no operator interventions. Different step sizes explain the
different final clocks. This is not a matched-tick performance benchmark and
does not demonstrate a survival advantage. These supplementary control/audit
scripts were added after the primary source freeze and do not change its gates.

`scripts/adaptive_continuity_audit.py` verified contiguous saved snapshots,
unchanged run identity, retained private versions, actual final native replay,
invariants, ingestion accounting and both real control worlds. Regression tests
also cover interrupted gathering across verified archive/checkpoint and a fresh
process, exactly-once scheduler retries, teaching interruption, stale messages,
depleted targets and refusal of missing proof. Long windows did not themselves
rotate epochs. This remains one finite development life, not five independent
survival runs, animal care or indefinite unattended survival.

## Verification, cost and evidence

- 335 Python regression tests passed in 673.525 seconds (driver wall 674.922),
  plus four native checks. Build ID remains
  `832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896`, UW9.
- Five-seed confirmation took 573.338 wall seconds; per-seed times were 90.069,
  105.710, 120.687, 148.537 and 108.322. Tests/control work overlapped, so these
  are measured elapsed times, not isolated CPU benchmarks. Model calls were zero.
- Development runs 1-4 took 59.279, 70.883, 82.076 and 84.391 wall seconds;
  exact separate traces and source ZIPs retain intermediate implementations.
- Real headless Edge checks at 1440x900 and 390x844 passed: selection/refresh,
  source-linked actual signals, uncertainty, no horizontal overflow, safe text,
  missing-evidence clearing, no page errors and refusal of write requests.
- Initial unit fixture failures remain in `gap_unit_attempt1.log`: an overlong
  checkpoint name and a head comparison spanning epoch rotation. Fixtures were
  corrected; native semantics were not weakened. All eleven adaptive, two panel/
  CLI and three context-teaching tests are included in the passing full suite.
- Phase9 audit still verifies 3439 files and four source files, recomputes the
  original metrics and returns `advance: false`. Its learner remains excluded
  from live autonomous policies.

Portable evidence is under `artifacts/gap_*`: frozen registration, exact gzip
confirmation/development/continuity traces, independent audits, regression and
browser outputs, screenshots and source ZIPs. `gap_evidence_archives.json`
records raw/compressed SHA256 hashes and actual local native-save inventory.
The packager also tests refusal of a fabricated goal, fabricated receipt, missing
world and changed registration using disposable reports. Original raw traces
and SQLite saves remain local and unchanged; native worlds are ignored data,
not included in the source commit. Re-running the independent native audit
requires those actual saves or reproducing the protocol, not hashes alone.

## Remaining limitations and use

No new neural training, reproduction, speech engine, true 3D or release label.
No consciousness, general intelligence or civilization-emergence claims.
Experiences retain the existing 2048-record/person ceiling; exhausted budgets
stop explicitly rather than inventing memory, resetting bodies or replenishing
resources. Factor/source/site limits, freshness windows, attention, need choice,
motor routing and sharing/teaching rules are authored and visible in the
protocol. Protective fallback, exploration, external teaching, native outcomes
and learned evidence have separate records/counters. The successful controlled
communication cases are not evidence that all inhabitants spontaneously acquired
these meanings during the long survival run.

Still unachieved: learned teaching/request/repair intentions, unrestricted
conversation, discovered grammar, arbitrary unseen-feature transfer, calibrated
semantic probabilities, multi-seed long survival and indefinite operation.
The historical failed studies remain failed. New bounded positive results do
not retroactively change them.

Use the separate CLI and evidence panel described in
[DEVELOPMENTAL_GAP_OPERATIONS.md](DEVELOPMENTAL_GAP_OPERATIONS.md).
Attachment is explicit and limited to compatible H5 working backups. Do not
attach to scored evidence saves. The old viewer and existing worlds continue
using their original policies until an operator explicitly selects this profile.
