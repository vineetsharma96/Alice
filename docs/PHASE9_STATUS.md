# Phase 9 experiment complete; advancement gate failed — 2026-10-20

Phase 9 evaluated one bounded mechanism: a non-neural online consumption-feasibility policy. The preregistered five-seed study completed, but the learner failed the locked comparison and per-seed retention requirements. It remains outside autonomous agents. No generation/inheritance mechanism or artificial-life origins track was introduced.

Read [PHASE9_REPORT.md](PHASE9_REPORT.md) for the experiment, uncertainty, errors and limitations, and [PHASE9_PREREGISTRATION.md](PHASE9_PREREGISTRATION.md) for the plan sealed before study trials. Previous status is preserved in [PHASE8_REPORT.md](PHASE8_REPORT.md). The original project brief remains unchanged.

## Results

| Arm | Primary mean balanced accuracy |
|---|---:|
| Frozen parameters | 50.00% |
| Nearest episodic memory | 67.71% |
| Domain-informed bracket memory | 83.33% |
| Online learned parameters | 65.21% |

Online improved over frozen by 15.21 percentage points, but fell below nearest memory by 2.50 points and bracket memory by 18.12 points. The exact paired-bootstrap 95% interval against bracket memory was [-19.17, -17.08] points. Seed 44 lost 10.42 points on task A after block B, above the 5-point per-seed retention limit. Seed 22 improved on A by 18.75 points, so the mean alone would obscure the failing seed. Five training-order seeds on one authored fixed task give descriptive uncertainty, not broad generalization evidence.

There were 360 native training trials, 116 parameter-changing mistakes, 840 evaluation policy rollouts and 210 counterfactual probes. Every evaluation predicted before obtaining its native label, started each arm from the same saved physical head, and froze parameters and receipt memory. The study ran once, with no outcome-driven amendments or retuning. A negative result completes the research evaluation; it does not permit advancing the learner.

## Implementation and provenance

- New opt-in underworld.learning module: three bounded weights, own inventory/request features, native terminal-receipt labels, a separate schema-1 SQLite policy journal, reservation before action, source/head verification and exactly-once update reconciliation. A reservation never automatically replays a physical action.
- Fixed experiment runner with five seeds, frozen/nearest/bracket controls, held-out quantities including equality, second-block retention, recorded predictions/receipts, paired bootstrap intervals, strict failure handling and bounded case-level budgets.
- Independent evidence audit checks 3439 retained files, source hashes, exact shuffled curricula/evaluation grids, paired physical heads, prediction commitments, five finished journals and recomputed metrics. All 1410 training/probe/rollout databases replayed successfully; evaluation also checked mass conservation.
- Native worlds remain in data/phase9-study-20261020. Compact publishable evidence is in artifacts/phase9_summary.json, phase9_study_manifest.json, phase9_training.jsonl, phase9_evaluations.jsonl, phase9_file_hashes.json and phase9_audit.json. The generated native databases remain local and Git-ignored.

Trial/evaluation wall time was 781.469 seconds, below the registered 900-second budget; final evidence hashing and separate audit/report work are excluded. Evidence before final manifest/hash inventory was 206.53 MiB, below 512 MiB. The sampled actual study Python process's observed peak working set was 36.53 MiB, excluding browser/GPU/other-process totals and not a final whole-machine peak. These are short fresh episodes lasting at most three simulated seconds, with parameters retained across episodes, not a longer continuous world experiment.

## Verification

Twelve new Phase 9 tests passed separately. The initial combined regression attempt hit its old 120-second subprocess timeout while competing with the study; all four native checks passed in that attempt. It is retained in artifacts/phase9_verification_attempt1.json. The verifier now preserves timeout output and allows an explicit per-check timeout.

The separate final regression run passed **122 Python tests and all 4 native CTest checks**, including all 110 earlier Python tests. Python reported 123.327 seconds internally; CTest reported 0.22 seconds. The complete commands, captured output, subprocess timings and unchanged native/runtime/viewer identities are retained in artifacts/phase9_checks.json. No skipped or failed check is being counted as a pass.

## Compatibility and handoff

Native UW6, SQLite user_version 7 and package 0.8.0 remain unchanged. Durable orchestration ID is 995842ce19b4f6cbc5c2180dc41d78e661ec691e33405ec54bfb2778044e4e81; viewer ID remains 2b9d949b2baa3ae1a7100e12979a0e3022eb2a710f955bfb68c7f7282678d93d. Research sources have separate hashes in the study manifest. No C++ rebuild, migration, dependency/model download, new inference service or live policy integration was needed.

The existing Phase 8 viewer at http://127.0.0.1:8765/viewer and its saved worlds were left in place; research/report commands did not advance them. Earlier browser acceptance evidence remains in PHASE8_REPORT.md. No new visual feature or browser acceptance claim is made in Phase 9.

Workspace branch is codex/phase-9. The repository still has no initial commit; no commit or push is claimed. Longer world horizons, speech, true 3D mechanics, inheritance/generations and the separate artificial-life track remain deferred. Phase 9 is the last numbered phase in the provided brief. Another learning mechanism requires an explicitly scoped new study and preregistration; the failed gate must not be silently relaxed.
