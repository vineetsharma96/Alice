# Phase 9 experiment report — 2026-10-20

The registered advancement gate **failed**. The learner remains outside autonomous agents. No advancement or deployment is authorized by these results. The bounded five-seed experiment completed; a completed research experiment is distinct from evidence that its mechanism is useful.

## Hypothesis and preregistration

Test whether a non-neural three-weight online policy can learn consumption feasibility from its own native action receipts and outperform frozen and memory-only controls on fixed unseen quantities, while retaining task A after learning task B. The [preregistration](PHASE9_PREREGISTRATION.md) and [sealed configuration](../config/phase9_study.json) were written before the first study trial. No pilot, hyperparameter amendment or outcome-driven rerun occurred. Unit fixtures tested implementation separately and were never training data. The first native source-verification unit test exposed a missing run-ID argument during checkpoint restoration; it was fixed before the study.

The seal artifact's `registered_at_utc` uses the pre-work clock reading 00:08:58 UTC. Its observed filesystem creation/write time was 00:12:21 UTC, before the study began at 2026-10-20T00:15:18.406182+00:00; the earlier field should not be interpreted as the exact sealing instant. The study finished at 2026-10-20T00:28:19.789481+00:00.

## Protocol and controls

Five seeds (11,22,33,44,55) shuffle training order independently. Each trains 36 eat trials, evaluates A, trains 36 drink trials with the same weights, evaluates B, then reevaluates A. Features are own available kg, proposed kg and bias. A normalized perceptron updates on mistakes only, learning rate 0.25, weights clipped to [-8,8]. Training deliberately attempts every curriculum candidate to obtain native feedback; evaluation selects attempt or rest using each arm's prediction, with all training state frozen. This is supervised online action selection, not reinforcement learning or neural optimization.

Frozen starts and stays at zero weights (always attempt). Nearest-memory uses one nearest native training receipt. Bracket-memory is an explicitly stronger, domain-informed authored baseline that derives an inventory-minus-request threshold from receipt margins. It has the same records and no trained weights. All controls and the learner use identical training feedback. No prompts, books, pretrained models, inherited parameters, private cross-agent data or viewer diagnostics influence predictions.

The 14-case fixed evaluation per stage contains unseen requested quantities and availability fractions 0,0.9,0.99,1,1.01,1.1,2. Predictions are persisted before the native probe executes. Each probe and the four arms start from an exact paired saved head; evaluation labels update neither parameters nor memory. Every rollout advances 10 ticks at dt=0.2 seconds, including rejections and rest. Native gathering creates inventory; no direct body edits are used. Each fresh episode has one actor, fixed 16 kg food/64 kg water, no regeneration, and at most three simulated seconds. These are short episodes with persistent parameters, not a long continuous world horizon.

## Results

Primary accuracy averages A-after-A and B-after-B equally, then the five seeds. Remaining columns aggregate all three evaluation stages: 210 rollouts per arm. A false negative is a missed feasible action, so abstaining cannot manufacture a win.

| Arm | Primary balanced accuracy | Rejections | Abstentions | Missed feasible | Consumed kg |
|---|---:|---:|---:|---:|---:|
| frozen | 50.00% | 90 | 0 | 0 | 38.800000 |
| nearest_memory | 67.71% | 30 | 100 | 40 | 19.400000 |
| bracket_memory | 83.33% | 30 | 60 | 0 | 38.800000 |
| online | 65.21% | 39 | 82 | 31 | 31.370000 |

Per-seed primary balanced accuracy and online retention loss (A-after-A minus A-after-B; positive means forgetting):

| Seed | Frozen | Nearest memory | Bracket memory | Online | A retention loss |
|---|---:|---:|---:|---:|---:|
| 11 | 50.00% | 67.71% | 83.33% | 66.67% | +0.00 pp |
| 22 | 50.00% | 67.71% | 83.33% | 63.54% | -18.75 pp |
| 33 | 50.00% | 67.71% | 83.33% | 66.67% | +0.00 pp |
| 44 | 50.00% | 67.71% | 83.33% | 64.58% | +10.42 pp |
| 55 | 50.00% | 67.71% | 83.33% | 64.58% | +0.00 pp |

| Comparator | Mean online minus control | Paired bootstrap 95% interval |
|---|---:|---|
| frozen | +15.21 pp | [+14.17, +16.25] pp |
| nearest_memory | -2.50 pp | [-3.54, -1.46] pp |
| bracket_memory | -18.12 pp | [-19.17, -17.08] pp |

Intervals enumerate all 5^5 paired bootstrap resamples of training-order seeds. They are descriptive and conditional on this one authored task and fixed evaluation set. They do not estimate broad task generalization or provide strong population evidence. Strongest memory control: `bracket_memory`.

## Gate and failure cases

- over_frozen: **pass**.
- over_each_memory: **fail**.
- positive_bootstrap_lower: **fail**.
- retention_mean: **pass**.
- retention_each_seed: **fail**.
- no_system_failures: **pass**.

The locked gate requires >=10 percentage points over frozen, >=5 points over EACH memory control, a strictly positive bootstrap lower bound against the strongest memory control, and <=5 points of A retention loss both on average and for every seed, with no system/integrity failures. The gate was not weakened after results.

- bracket_memory: 30 false positives (infeasible action attempted).
- frozen: 90 false positives (infeasible action attempted).
- nearest_memory: 30 false positives (infeasible action attempted).
- nearest_memory: 40 false negatives (feasible action missed).
- online: 39 false positives (infeasible action attempted).
- online: 31 false negatives (feasible action missed).

First retained online errors (the summary contains every error, including boundary/equality cases):

- Seed 11, A_after_A, eat: inventory 0.153000 kg, request 0.170000 kg; predicted True, native feasible False.
- Seed 11, A_after_A, eat: inventory 0.168300 kg, request 0.170000 kg; predicted True, native feasible False.
- Seed 11, A_after_A, eat: inventory 0.423000 kg, request 0.470000 kg; predicted True, native feasible False.
- Seed 11, A_after_A, eat: inventory 0.465300 kg, request 0.470000 kg; predicted True, native feasible False.
- Seed 11, B_after_B, drink: inventory 0.117000 kg, request 0.130000 kg; predicted True, native feasible False.
- Seed 11, B_after_B, drink: inventory 0.128700 kg, request 0.130000 kg; predicted True, native feasible False.
- Seed 11, B_after_B, drink: inventory 0.477000 kg, request 0.530000 kg; predicted True, native feasible False.
- Seed 11, B_after_B, drink: inventory 0.524700 kg, request 0.530000 kg; predicted True, native feasible False.

Task B shares the same feasibility law as task A. Its retention test probes only narrow interference under a second shuffled training block on the same quantity grid; it does not establish general resistance to catastrophic forgetting. Learning depends on curriculum order and a tiny linear representation. A useful next research change would require a new explicit study and preregistration, not tuning this study until it passes.

## Native provenance and costs

There were **360 verified training trials** (180 completed candidates, 180 native inventory rejections), **116 parameter-changing mistakes**, **840 evaluation rollouts**, and **210 native counterfactual probes**. All **1410** training/probe/rollout databases passed native replay during the study; evaluation rollouts also checked material conservation. Five final journals each contain exactly 72 finished records. The independent audit verified 3439 retained evidence files, paired states/prediction commitments and recomputed metrics. Policy-state hashes were unchanged across each evaluation stage.

Trial/evaluation wall time: **781.469 seconds** against the registered 900-second limit, excluding final evidence hashing and separate audit/report publication. Retained evidence before final manifest/hash inventory: **206.53 MiB** against 512 MiB. Disk quota is checked between bounded cases; this research script is not an OS memory or network sandbox. [A process-memory sample](../artifacts/phase9_resources.json) records only the actual study Python process's observed peak during the run, excluding browser/GPU/other-process totals; it is not a final whole-machine peak. No inference server, neural dependency, C++ rebuild, database migration or runtime-policy integration was added. Source IDs are pinned in the [study manifest](../artifacts/phase9_study_manifest.json); native UW6/DB7 and the durable orchestration identity remain unchanged.

Native world commits and policy commits are separate. Reservations capture pre-action evidence; finishing verifies the committed request and reproduces the native terminal head before applying feedback exactly once. A crash before submission leaves an unresolved reservation and never replays a physical action. A partial action is not completion. Checksum/update-chain tests and source checks detect accidental corruption or foreign receipts, not an adversary who can rewrite every local artifact. Full pre-action checkpoints are privileged audit metadata; prediction functions use only weights and own receipt features/labels.

## Published local artifacts and verification

- [Study manifest](../artifacts/phase9_study_manifest.json), [summary and all failures](../artifacts/phase9_summary.json), [audit](../artifacts/phase9_audit.json), and [evidence hashes](../artifacts/phase9_file_hashes.json).
- [Training receipts and weight changes](../artifacts/phase9_training.jsonl) and [evaluation requests/receipts](../artifacts/phase9_evaluations.jsonl).
- Native SQLite worlds and final parameters: `data\phase9-study-20261020`. These generated data files are ignored by Git and retained locally; the compact reports/traces above are publishable workspace artifacts.
- Twelve new learning tests cover native feedback, persistence/restart, exactly-once reconciliation, incomplete actions, foreign/forged sources, tampering, frozen controls, input boundaries, equality and conservation.
- An initial full verification attempt timed out at 120 seconds while competing with this study; its four native checks passed. That attempt is preserved in [phase9_verification_attempt1.json](../artifacts/phase9_verification_attempt1.json). The separate final run passed **122 Python tests and all 4 native checks**. Python reported 123.327 seconds internally and CTest 0.22 seconds; exact subprocess timings and output are in the [full verification record](../artifacts/phase9_checks.json).

Reproduce only into a new directory with `python scripts/phase9_experiment.py --output data/phase9-replication`. Audit retained results with `python scripts/phase9_audit.py --study data/phase9-study-20261020`. Neither inspection nor report publication advances the running Phase 8 preview.

No claim of sentience, biological reproduction, generalized endogenous improvement or guaranteed civilization emergence follows. Generations/inheritance, the separate artificial-life origins track, longer world horizons, speech and true 3D mechanics remain deferred. R7/R8/R10/R11 context and boundaries are recorded in [REFERENCES.md](REFERENCES.md).
