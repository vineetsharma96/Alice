# Underworld Lab stabilization report

The **fresh-cohort everyday-action evaluation passed** its registered thresholds after disclosed development and evaluation failures. This is an authored execution improvement. Phase 9's failed learner remains unchanged and outside live policies. Results below apply to the selected inhabitant/scenarios; they do not establish general autonomous competence or all-population reliability.

## Baseline reproduced before implementation

The unchanged utility and local-model paths were each run for 20 native seconds with initially nonurgent needs and again after 160 seconds of actual body aging. Full inputs, raw outputs, compile status, submissions, receipts, needs and latency are retained in [stabilization_baseline.json](../artifacts/stabilization_baseline.json).

- Nonurgent model call 1 had empty carried inventory in its permitted context, generated/compiled an eat intent, then received native INSUFFICIENT_RESOURCE. Observation and submission were at the same native tick, with no earlier inventory-changing action: this case is not explained by stale state or execution order. The inventory observation was present. The old intent vocabulary cannot express gather/move prerequisites, and the compiler maps eat directly to a fixed consumption request.
- Nonurgent model call 2 exceeded its inference deadline (20.251 s end-to-end), used the explicit authored provider fallback, and completed speech. A completed speech action is not a completed meal or survival goal.
- Both aged-needs model outputs compiled, but the legacy scheduler preempted their pending plans because hunger/thirst were urgent. No native request was submitted. With utility disabled in the model-only arm, nothing supplied the missing execution. This is a scheduler/goal-arbitration failure, not a native rejection.
- Utility completed native gathering/consumption actions in the aged case. Those successes are deterministic utility behavior, not model planning.

These explanations apply to these traced cases. They do not retroactively assign one cause to every earlier Phase 7 rejection. Valid JSON, original-model compilation, submission acceptance, terminal action completion and goal achievement remain separate in the artifacts.

## Implementation

`underworld.stabilization` is an opt-in controller with explicit persistent goals: locate permitted supply → approach → gather → consume. It reobserves before every request, checks bounded alternative approach directions when one is occupied, waits for terminal native receipts, bounds search/retries/deadlines and records scarcity/blocked outcomes. Eating/drinking success requires a real ingested-mass delta and identifies whether the executor or an external action caused consumption.

The model selects an intent/goal; all prerequisite execution is authored. Deterministic need selection after the inference budget/interval and safety overrides of non-survival choices are recorded as fallback. The new context adds only geometry, reach and resource quantities already visible to the inhabitant. Private memory retrieval remains actor-specific. The native validator, legacy utility/model compiler and durable runtime sources are unchanged.

An explicit scheduler handoff disables old automatic utility/cognition dispatch and supersedes pending legacy plans while preserving physical state, pending native actions, inventories, needs, identities, episodes and prior journals. Controller state/audit tables are checksummed and source-pinned. Reservations commit before native ticks; recovery reconciles committed request IDs instead of resubmitting them. An unsubmitted reservation is discarded and replanned. These are separate transactions, not an atomic cross-database promise.

## Protocol, development and fixture amendment

The [protocol](STABILIZATION_PROTOCOL.md) was sealed before modified-policy measurements. Development used seed 101. The original cohort was 202,303,404; the final fresh cohort was 808,909,1001 following [amendment 2](STABILIZATION_AMENDMENT_2.md). Both used the same five scenarios, four arms and thresholds. Each evaluation lasted 90 continuous simulated seconds after native fixture aging/setup. Model arms received one inference attempt at the start, with logical time paused; the stabilized arm then used declared authored execution and deterministic fallback as needed. This budgeted model-only baseline is separate from a utility-plus-model system in which utility can mask model failures.

The first partial held-out attempt was stopped after a fixture bug was found. Actor 2's seeded random position did not guarantee reach to food; its competitor gather was rejected and the supposed depleted food remained available. Its 17 completed cases, native databases, evaluator source, freeze and [failure record](../artifacts/stabilization_heldout_attempt1_failure.json) are retained and excluded from the final comparison. Successful-looking results from that invalid depletion setup are not counted as depletion evidence.

[Amendment 1](STABILIZATION_AMENDMENT_1.md) moved the competitor natively to a declared reachable position, retained all setup time/costs, and added assertions for its completed receipt and actual empty source. Three independent native fixture validations and a repeated development run passed before the second comparison. The v1 controller remained frozen for that comparison.

The second, valid-fixture comparison then **failed**: model-selected unavailable food led to a missed feasible water goal. At (1,1), the single radial approach point for water was blocked by the visible peer at (2,1). The controller kept reporting no_perceived_route without trying another approach. This was a navigation defect, not a timeout, missing observation or native rejection. Its partial [results](../artifacts/stabilization_heldout_v2_failed.json), [failure record](../artifacts/stabilization_heldout_v2_failure.json), source and databases remain preserved.

[Amendment 2](STABILIZATION_AMENDMENT_2.md) added development regressions and controller version 2's bounded approach candidates using existing perceived-geometry helpers. The unchanged utility baseline already uses approach candidates. The repaired source was frozen before the final **new cohort** (808,909,1001), with no threshold, quantity or inference-budget relaxation. Earlier exposed seeds are excluded from the final aggregate. This is a fresh-cohort evaluation after an outcome-prompted disclosed repair, not a claim that the original hold-out stayed untouched. Failed attempts are not combined into favorable totals.

## Fresh-cohort comparison

| Arm | Feasible goals completed | Missed feasible | Native submission rejections | Completed actions | Calls / provider failures | Median case wall s |
|---|---:|---:|---:|---:|---|---:|
| utility | 24/24 | 0 | 0 | 300 | 0 / 0 | 8.867 |
| legacy_model | 0/24 | 24 | 0 | 0 | 15 / 3 | 26.228 |
| stable_authored | 24/24 | 0 | 0 | 138 | 0 / 0 | 12.280 |
| stable_model | 24/24 | 0 | 0 | 127 | 15 / 4 | 29.946 |

Each arm has 24 feasible food/water goals across 15 cases. Unavailable/depleted food is excluded only from the feasible-food denominator; hunger, missing consumption, waits and all errors remain recorded. Native competitor receipts confirm real depletion in every corrected depleted case. Necessary scarcity is not a failed feasible goal. Completion-time physical failures are reported separately from fresh submission errors; they are not all assumed unavoidable.

Case wall time includes inference, controller/persistence work and, for interrupted cases, a second uninterrupted continuation used for parity. Main-process CPU fields exclude model-server/child CPU. Exact per-case timings, accepted/completed action kinds, rejection reasons, needs and source attribution are in [the fresh-cohort raw comparison](../artifacts/stabilization_heldout_v3.json) and [summary](../artifacts/stabilization_summary.json). These host-specific timings are not a universal speed claim.

The summary also derives consumption-completion latency in simulated seconds from native terminal receipts, separately for food/water. Those latencies are conditional on completion; missing goals stay in the missed-feasible denominator and are not assigned an artificial zero latency. Need maxima and seconds above 0.85 remain reported for each arm, including scarcity cases.

The stabilized model arm made 15 inference attempts: 11 raw valid-JSON outputs and 11 original outputs that compiled; 4 provider failures. Its median end-to-end inference latency was 17.947 s. The legacy model arm had 12 original outputs compile across 15 attempts; a compiled plan still does not imply submission or completion.

The stabilized model arm recorded 6 native consumption-goal completions whose goal was model-selected and 18 whose goal was fallback-selected. Its 130 execution steps were authored. Model selection of eat does not establish that the model planned the approach/gather sequence. Matching utility here does not establish a model advantage over deterministic survival.

### Locked checks

- stable_feasible_goals: **pass**.
- stable_no_preventable_rejections: **pass**.
- stable_no_empty_eat: **pass**.
- survival: **pass**.
- replay_conservation: **pass**.
- stable_no_worse_than_utility: **pass**.
- stable_model_improves_missing_legacy_goals: **pass**.
- attributed_execution: **pass**.
- complete_durations: **pass**.
- resume_parity: **pass**.
- depleted_fixture_valid: **pass**.

## Continuous worlds and save/resume

| Arm | Actual continuous simulated s | Primary wall s | Alive | Fresh-process and recorded-request parity |
|---|---:|---:|---|---|
| stable_authored | 1200 | 127.707 | True | True |
| stable_model | 1200 | 166.808 | True | True |

Each stabilized arm used one continuous one-inhabitant world with 2 kg initial food, 4 kg water and regeneration zero. Cumulative targets were 30,120,600,1200 seconds with a 240-second primary wall allowance per arm. A backup at 120 seconds was resumed by fresh Python processes. Each child verified exact incoming native/body/memory/controller state; call budgets and goal/navigation schedules were not reset. Actual cutoffs, if any, remain in [continuity evidence](../artifacts/stabilization_continuity.json).

Conservation and boundary-source checks compare against the original world. The uninterrupted native counterpart uses the same recorded commands, without regenerating inference; its final physical hash and own-memory view are compared to the resumed world. That is native/mental recorded-command parity, not a replay of every controller decision. Separate regression tests compare uninterrupted versus resumed full controller/scheduler state mid-action. Primary wall time excludes the additional recorded-command parity pass, whose cost is retained separately. Independent evaluation cases and the two continuous arms are not one summed lifelong horizon.

## Verification and preserved research

Full verification success: **True**. Ran 139 tests in 160.319s. All native CTest results, exact commands, output and wall times are retained in [stabilization_checks.json](../artifacts/stabilization_checks.json). New regression cases cover prerequisite ordering, current inventory, depleted supply, scarcity, native conservation, handoff, disabled legacy scheduling, private input, audit corruption, inference fallback budgets, external interruption/consumption attribution, mid-action save/resume and both sides of the reservation/native-commit gap.

Protected Phase 9 files match their pre-milestone hashes: **True**. The independent original study audit is retained in [stabilization_phase9_preservation.json](../artifacts/stabilization_phase9_preservation.json). Its failed comparison and retention gate is unchanged. The new executor has no learner import and introduces no neural training, reproduction, speech or true 3D mechanics.

## Remaining limitations and operation

- This is a bounded authored survival-goal executor, not a general planner. Capacity-blocked cargo rearrangement, arbitrary complex tasks, broad need combinations and all crowd layouts remain outside the demonstrated reliability claim. The primary evaluation controls actor 1 with a second fixture/competitor actor; continuous evidence is one active inhabitant per world.
- Repeated finite-resource operation can still exhaust supply. Scarcity search/cooldown can delay another need. No long-term sustainability, full-day stability, water-scarcity generalization or unrestricted goal arbitration is established.
- The model is still a small pretrained prior. The context and execution architecture changed together; this comparison does not isolate a prompt-only effect or demonstrate learned multi-step planning. Fallback dependence is part of the result.
- The opt-in runner is a bounded host-side development controller, not a newly verified AppContainer service. The old viewer/supervisor does not drive it automatically; use a read-only viewer and the new run command. No broad security, power-loss or cross-platform guarantee is added.
- Native state hashes exclude the additional control tables. Controller checksums/source identity and native replay are separate checks. Local checksums do not authenticate evidence against a hostile writer who can rewrite everything. Journals/native request limits remain finite; no controller-history compaction or source migration is provided.
- Small fixed scenario sets and the disclosed repair/evaluation iterations limit generalization. Fresh seeds do not establish broad task diversity. A further mechanism or changed acceptance criterion needs a new explicit evaluation, not a silent weakening of this one.

Runnable commands and existing-world backup/handoff are in [STABILIZATION_OPERATIONS.md](STABILIZATION_OPERATIONS.md). The original brief and Phase 9 study remain preserved. No consciousness, general intelligence or civilization-emergence claim follows from these results.
