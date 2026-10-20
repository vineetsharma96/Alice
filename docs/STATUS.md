# Living-world Milestone B — trees and materials in progress — 2026-10-20

Milestone A is complete within its measured scope. Milestone B now adds an opt-in `config/living-world.toml` development profile with four inhabitants, native UW7 trees/materials, finite harvesting and explicit growth accounting. Legacy survival, unattended and Phase 9 paths remain unchanged. Animals, crafting and general planning are not implemented yet.

The opt-in persistent prerequisite executor is implemented and evaluated. The failed Phase 9 study remains unchanged and its learner stays outside live autonomous policies. Its previous status is preserved in [PHASE9_STATUS.md](PHASE9_STATUS.md).

Read the [stabilization report](STABILIZATION_REPORT.md), [operations/handoff guide](STABILIZATION_OPERATIONS.md), [original protocol](STABILIZATION_PROTOCOL.md) and disclosed [fixture](STABILIZATION_AMENDMENT_1.md)/[navigation](STABILIZATION_AMENDMENT_2.md) amendments.

## Fresh-cohort outcomes

| Arm | Feasible goals completed | Missed feasible | Native submission rejections | Completed actions | Calls / provider failures | Median case wall s |
|---|---:|---:|---:|---:|---|---:|
| utility | 24/24 | 0 | 0 | 300 | 0 / 0 | 8.867 |
| legacy_model | 0/24 | 24 | 0 | 0 | 15 / 3 | 26.228 |
| stable_authored | 24/24 | 0 | 0 | 138 | 0 / 0 | 12.280 |
| stable_model | 24/24 | 0 | 0 | 127 | 15 / 4 | 29.946 |

The final cohort used seeds 808,909,1001 with carried food, gathering, unavailable food, depleted targets and interrupted plans. Feasible goals exclude genuinely unavailable/depleted food; needs, scarcity and all action outcomes remain recorded. Generated JSON/plans, submitted/accepted requests, completed actions and achieved ingestion are distinct stages. These are selected-inhabitant scenario results, not a general population reliability guarantee.

The first partial attempt had an invalid competitor fixture. The second valid-fixture attempt exposed a real occupied-approach defect and missed water. Both remain preserved as failures. The repaired controller was tested on a new cohort with unchanged thresholds, not repeatedly tuned against the original held-out set. Route selection and prerequisite execution are authored, even for a model-selected goal.

## Continuous operation and verification

| Arm | Actual continuous simulated s | Primary wall s | Alive | Fresh-process and recorded-request parity |
|---|---:|---:|---|---|
| stable_authored | 1200 | 127.707 | True | True |
| stable_model | 1200 | 166.808 | True | True |

Finite food/water, regeneration zero, no body reset or silent replenishment. Save/resume at 120 seconds preserved source-pinned goals, inference budgets, navigation/schedules, native state and memories. Exact actual horizons, cutoffs, primary wall time and separate recorded-command parity costs are in the report. These are not 24-hour or long-term sustainability claims.

Full verification passed: **True**. Ran 139 tests in 160.319s. Native checks and complete subprocess evidence: [stabilization_checks.json](../artifacts/stabilization_checks.json). Protected Phase 9 file hashes match: **True**; its independent original audit is retained separately. Original native/durable runtime identities and validator semantics are unchanged.

## Handoff and remaining limits

Use `python -m underworld.stabilization init/attach/run/status` or the living-world wrapper as documented. This is an explicit opt-in scheduler handoff; no existing Phase 8/9 world was silently switched or reset. The viewer can attach read-only. The legacy viewer time controller and Phase 7 supervisor do not automatically drive the new executor; its model calls use separate audited counters.

Crowd layouts, arbitrary cargo rearrangement/complex tasks, unavailable-water combinations, long-term supply and full-day operation remain outside this evidence. The host-side controller is not a newly verified AppContainer service. Native hashes and controller-journal checks are separate; journals and requests have finite quotas. No neural training, reproduction, speech, true 3D, consciousness, general intelligence or civilization-emergence claim was added. Phase 9's failed advancement gate was not changed.

## Milestone A checks

- `.venv/Scripts/python.exe -m py_compile underworld/__main__.py underworld/stabilization.py underworld/observer.py`: passed.
- `.venv/Scripts/python.exe -m unittest tests.test_stabilization`: passed, 17 tests.
- `.venv/Scripts/python.exe -m underworld living-world --help`: passed.
- Model-off smoke initialized `data/living-world-smoke/run.sqlite`, ran 2 simulated seconds, matched replay, saved `checkpoint.sqlite`, and resumed another 2 simulated seconds; both runs reached their targets.
- Observer state smoke reported `controller.active=stabilization` and the selected controller budget.
- `.venv/Scripts/python.exe -m unittest tests.test_scaffold tests.test_stabilization`: blocked by missing `UNDERWORLD_CORE` in `tests.test_scaffold.CoreTests`; stabilization tests still passed independently. No scaffold-suite pass is claimed until the native core path is supplied.

See [LIVING_WORLD_PLAN.md](LIVING_WORLD_PLAN.md) and [HANDOFF.md](../HANDOFF.md) for the dependency order and next acceptance check.

## Milestone B checks

- `"/c/mingw64/bin/mingw32-make.exe" -C build -j2`: passed.
- `./build/underworld_native_tests.exe`: passed, including tree lifecycle, competing harvesters, placement, growth and UW6 rejection.
- `./build/underworld_thermal_tests.exe`: passed.
- `.venv/Scripts/python.exe -m unittest tests.test_phase_b_trees`: passed, 3 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase1.MechanicsTests`: passed, 8 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase2.BodySenseTests`: passed, 8 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase5 tests.test_phase6`: passed, 26 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase7 tests.test_phase8 tests.test_phase9`: passed, 36 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_stabilization`: passed, 17 tests.
- `UNDERWORLD_CORE="build/underworld_core.exe" .venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`: passed, 142 tests in 173.584s.
- `node --check underworld/web/scene.js && node --check underworld/web/viewer.js && node --check underworld/web/observer.js`: passed.
- Living-world CLI smoke initialized `data/living-world-b-smoke/run.sqlite` from the new config, ran 2 simulated seconds with replay parity, saved `checkpoint.sqlite`, resumed another 2 simulated seconds, and reported trees/stone through the observer state.

No full-day ecosystem run or model-enabled tree planner is claimed. The native tree actions are available to validated callers; autonomous tree/crafting planning is deferred to later milestones.
