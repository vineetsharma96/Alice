# Phase 9 preregistration: native consumption feasibility

Registered 2026-10-20 before any Phase 9 training or evaluation. The registration JSON is sealed by SHA-256 in `artifacts/phase9_registration.json` before implementation trials. No pilot runs or outcome-driven hyperparameter changes are permitted. Any amendment needs a new study identifier and disclosure; failed runs remain evidence.

## Hypothesis and mechanism

A three-weight, non-neural normalized perceptron can learn whether its own proposed eat/drink action will complete from native terminal action receipts, and outperform both unchanged weights and episodic-memory controls on fixed unseen quantities. This tests one online skill-policy mechanism across fresh short episodes, not uninterrupted lifelong learning, neural training, inheritance, consciousness, or open-ended evolution.

Features are own inventory kg, requested kg, and bias 1. Initial weights are zero. Score >= 0 predicts feasible. On a training mistake only, update `w += 0.25 * y * x / dot(x,x)` for y in {-1,+1}, clipping each weight to [-8,8]. No prompts, pretrained model, hidden world state, hand-written inventory comparison in the learner, or evaluation feedback enters updates. Parameters persist separately from the native world. Raw receipt memories are bounded to 72 records per seed.

## Fixed protocol

Seeds 11,22,33,44,55 independently shuffle each training pass. Block A trains eat, block B trains drink using shared weights. Each block has two passes over requested kg {0.1,0.3,0.6} crossed with available fractions {0,0.35,0.7,1.15,1.55,2}: 36 trials/block, 72/seed. Evaluate A after A, B after B, and A after B for retention. Evaluation uses requests A={0.17,0.47}, B={0.13,0.53}, crossed with fractions {0,0.9,0.99,1,1.01,1.1,2}: 14 cases per stage. These include exact equality and unseen near-boundary quantities. Every seed has the same fixed evaluation set. No evaluation updates to weights or memories.

Each case has a fresh closed native world, one living actor, dt 0.2 seconds, authored stable 16 m square environment, 16 kg food and 64 kg water, no regeneration, utility policy, cognition, thermal apparatus, or cohort replacement. Obtain inventory through native gathering (one second); no direct inventory edits. Candidate requests last two seconds. All candidate/abstention rollouts advance ten native ticks, including rejected requests. Agent population and resource bounds remain fixed. Each episode lasts at most three simulated seconds. Study wall budget 900 seconds; retained data budget 512 MiB. No unattended long-horizon operation is enabled.

For each evaluation case, clone the exact pre-action native head into one counterfactual probe and four policy rollouts. Native probe receipt supplies the label; policies never receive it before their prediction. An arm attempts the candidate if feasible and otherwise rests. Retain physical head hashes, requests, receipts, seed/stage/case identity, and policy-state hashes. Each arm uses the same training receipts and starts from the same physical head. Fixed simulation duration prevents rejecting early from creating an artificial timing advantage.

Controls: frozen zero weights always attempt; nearest-memory predicts the label of the earliest nearest receipt in Euclidean (available kg, requested kg) distance; bracket-memory derives a threshold midway between greatest failed inventory-minus-request margin and smallest successful margin, defaulting to the sole observed label or feasible if empty. Bracket-memory is deliberately domain-informed and recomputes from episodes without learned weights. It is a strong authored memory baseline, not an independent intelligence claim.

## Outcomes, uncertainty, and advancement

Primary endpoint: balanced accuracy pooled equally over A-after-A and B-after-B, then averaged across seeds. Report confusion counts, feasible completions, native rejections, abstentions including missed feasible actions, consumed mass, simulation ticks, weight changes, training errors, and wall/disk costs. Report A-after-B retention separately and delta from A-after-A. Every non-inventory native rejection, source mismatch, tamper/integrity error, incomplete trial, or budget exhaustion is a system failure; never convert it into a learning label.

Use the exact enumeration of all 5^5 paired bootstrap samples for 95% percentile intervals of mean differences (descriptive uncertainty with only five seeds, not strong population evidence). Strongest memory means the control with the highest primary mean; ties use declared arm order. Retain per-seed results and all near-boundary failures.

Advance only if online improves balanced accuracy by >=0.10 over frozen and >=0.05 over EACH memory control; paired bootstrap lower 95% bound against strongest memory is strictly >0; mean and every seed's A retention loss are <=0.05; and no system/integrity failure occurs. Otherwise keep deployment closed. No tuning after results. A negative result completes this experiment but does not authorize deployment or a new mechanism.

## Provenance and limitations

Use native receipts from the same actor and committed request only. A journal reservation precedes physical execution. Native completion and sidecar update are separate transactions: recovery may apply a verified completed receipt exactly once, but must never automatically replay a physical action. Accepted submission alone is not a success label. Evaluation records do not enter the training journal. Learner/source/registration hashes and native/orchestration IDs accompany the report.

The task law and curriculum are authored. Weight changes can fit that tiny law; they do not establish generalized planning, new knowledge beyond controls, biological evolution, or origins of intelligence. R7 (Enhanced POET), R8 (ASAL), R10 (PyTorch), and R11 (Flow-Lenia) motivate distinct research tracks; no replication or neural/alife results are claimed here. No new dependency is needed.
