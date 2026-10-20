# Edible-food execution repair — 2026-10-21

The persistent authored executor now consumes carried plant food/eggs, accepts
smaller portions, gathers visible finite forage and rechecks freshness. Native
validation, ingestion-based full-goal credit, retries and the sealed Phase 9
gate remain unchanged. Read [the repair report](FOOD_EXECUTION_REPAIR.md) and
[protocol](FOOD_EXECUTION_PROTOCOL.md). General care/planning and other deferred
research features remain incomplete; this is not the whole of milestone E.

Separate confirmation completes 6/6 feasible full meals versus 0/6 with the
frozen previous executor, plus three partial egg portions. No native rejection
or failure occurs in those cases, and food/water/body balances close exactly.
One continuous durable world advances another 120 simulated seconds after its
declared setup in 25.792 primary wall seconds; a backup resumes 119 seconds in
17.396 wall seconds to identical native/controller/memory state, with replay.
The rebuilt executable passes source/save interoperability and both viewer pages.

Final verification passes **190 Python tests (231.412 s)** and **four native
checks**, with protected Phase 9 hashes matching. An earlier parallel isolation
test completion race and its retained failing run are explained in the repair
report; worker limits and successful-outcome/cleanup assertions are unchanged.

Use `artifacts/food_repair_*` evidence for this repair. The exact prior source
and executable are archived at `build/runtime-before-food-fix-20261021`; the
archived executable was verified against the old code-audit save. Existing
controller pins are not migrated/reset. The 20 October results below remain
historical evidence for their original runtime.

---

# Current code audit and desktop launcher — 2026-10-20

Application 0.11.1 adds verified executable/source launch paths and integration fixes, with native UW9/DB10/checkpoint 9 laws unchanged. Read [the audit report](CODE_AUDIT_REPORT.md) and [detailed README](../README.md). Current orchestration/controller pins differ from D; its exact prior runtime is archived locally and original evidence is retained. The model-off desktop can run through one Bash/CMD file or dist/UnderworldLab.exe; it never migrates/reset/refills an old save. Phase 9 remains sealed and failed.

Final verification: **183 Python tests** (229.709 s inside unittest) and **four native checks** pass. Static checks are clean. The standalone executable reaches **120 continuous simulated seconds / 169.582 wall seconds**, completes four human drink goals through 15 native actions, retains all six bodies alive at health 1.0, and passes replay. Its complete native head equals the original final D 120-second head (`da68713042375015e7fc88ba50f863072b4da1416620232215b3ada187837c90`), demonstrating unchanged native behavior for this case. Separate reduced-PATH smoke checks prove executable/source/executable save continuation and packaged backup/replay. Both packaged UI pages pass read-only/asset/privacy checks with no JavaScript errors.

The D and older measurements below are historical. Audit verification and packaged smoke evidence use separate code_audit_* artifacts.

---

# Living-world Milestone D — current scope, 2026-10-20

D adds an opt-in native animal/food ecology profile: two species, finite forage, authored local behavior, real feeding/trough use, persistent familiarity, physical pens/gates, reserve-funded eggs and conservative food aging/storage. **UW9 / DB10 / checkpoint 9 / stabilization/3**, package 0.11.0; use `build/living-d` and `config/living-world-d.toml`. No migration or reset of C/study worlds. See [D contract](PHASE_D_ECOLOGY.md) and [D report](LIVING_WORLD_D_REPORT.md) for measured acceptance and limitations.

Breeding and fuel/heat-coupled cooking remain explicitly deferred. Dietary energy and waste are abstract mass reservoirs, not a biological or thermal metabolism model. Human care procedures are externally assigned; autonomous care planning is E. The A recurring/global model-budget gate remains incomplete, so validation is model-off. Phase 9's failed gate and learner exclusion remain unchanged.

The final build passes **176 Python tests** (243.105 s inside unittest) and **four native checks**. D's four-person/two-animal world reaches **120 continuous simulated seconds / 163.338 primary wall seconds**; its backup at 30 seconds resumes another 90 seconds in a fresh process in **119.440 wall seconds**, measured separately. Complete native state, all eight memory/controller tables, and run/branch identities match. Four human drink goals complete through 15 accepted/completed native actions with no rejection/failure; no human eating goal becomes urgent in this window. All six bodies end alive at health 1.0. Animals perform 67 drinking and 40 forage transfers and lay one 0.06 kg reserve-funded egg quantity; the 120-second forage intake is by the grazer, while the separate 300-second development regression verifies both species actually forage. Food/water/forage regeneration is zero, tree growth adds an explicitly accounted 0.6 kg boundary biomass, and no body/resources are reset. This is bounded continuity, not sustained husbandry or ecosystem survival.

The C and earlier sections below are historical measurements under their own pinned runtime.

---

# Living-world Milestone C — crafting/construction verified within bounded scope — 2026-10-20

Milestone B was independently rechecked: its 142 Python tests and 4 native checks passed, but additional review found defects in growth capping, inventory restoration, viewer lifecycle refresh and entity-quota handling, initial stone placement and remote harvest anchors. Milestone C corrects those and adds native recipes, tools, persistent construction work, storage, trough/fence/gate mechanics and an explicitly assigned physical production demonstration. See [the current audit/report](LIVING_WORLD_C_REPORT.md) and [contract](PHASE_C_CRAFTING.md).

Current runtime: **UW8 / DB9 / checkpoint schema 8 / stabilization/3**. Old UW6/DB7 and UW7/DB8 worlds are preserved and require their original full source/runtime; no migration or reset is performed. Use the `UNDERWORLD_BUILD=build/living-c` launch commands in [HANDOFF.md](../HANDOFF.md). Native format validation rejects accidentally loading the old root build with current Python sources.

Milestone A's model-off wrapper works; its requested recurring/fair/global model budgeting is **not implemented** by the prior handoff. The old lifetime call limit remains. Model-enabled A acceptance and isolated-supervisor integration are not claimed. General autonomous production planning is still Milestone E; animal behavior is Milestone D. Current C verification: **160 Python tests and 4 native checks passed**, followed by **26 crafting/viewer checks**. The 21-action production chain completed in **55.6 simulated / 7.543 wall seconds** with fresh-process construction parity. One four-person world reached **120 continuous simulated / 107.250 primary wall seconds**, completing four drink goals through 15 native actions without rejection. Fresh-process continuation matched native state, eight memory/controller tables and world/branch identities. All runs were model-off. Independent Phase 9 audit verified 3439 retained files; its gate is still false.

The following stabilization and A/B sections retain historical measurements. They are not reruns under the C laws/build.

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

Historical pre-expansion stabilization verification passed: **True**. Ran 139 tests in 160.319s. Native checks and complete subprocess evidence: [stabilization_checks.json](../artifacts/stabilization_checks.json). Protected Phase 9 file hashes match: **True**; its independent original audit is retained separately. Those original native/durable runtime identities and validator semantics applied to that historical evaluation; the living-world expansion explicitly changes compatibility and adds validators.

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
