# Milestone E update — 21 October 2026

Bounded explicitly assigned hierarchy/recovery now covers food/wood, tools,
planks/troughs, real water delivery and local animal-care tasks. It uses native
receipts and own observations; general autonomous task formation, pen topology
and teaching remain incomplete. [E report](LIVING_WORLD_E_REPORT.md) records
209 passing Python tests/four native checks and the corrected confirmation.
Four real model calls show no completion benefit and add cost. Authored source
preference changes behavior but can become stale and slower. Placement can waste
preparatory work before the final site is rejected. Do not call these general
learning or husbandry success. A's global inference budgets and Phase 9's failed
gate remain unchanged; F/G and long-term archival remain later work.

# Food execution repair — 21 October 2026

**Fixed:** the persistent executor overlooked carried plant food/eggs and visible
forage, and required a full meal before consuming any food. It now requests real
native forage gathering and freshness-aware partial consumption, retaining the
unchanged full-goal ingestion threshold. [Repair report](FOOD_EXECUTION_REPAIR.md)
records separate confirmation cases, native receipts, remaining limitations and
the corrected evaluation fixture. This is authored execution, not learned skill.
The historical learning/teaching gates below remain unchanged.

# Milestone D update — 20 October 2026

Native animals, finite forage, physical containment, care actions, reserve-funded eggs and food freshness are implemented in the opt-in D profile. [D report](LIVING_WORLD_D_REPORT.md) records the current evidence and failures. Breeding and cooking are **deferred**, not implemented. A fixed care route may overfeed or collide; the native validator reports those failures. General autonomous husbandry, long-horizon sustainability and fair recurring/global model budgets remain incomplete. Earlier statements that animal behavior is unimplemented describe the historical C boundary below. The sealed failed Phase 9 result remains unchanged.

---

# Failed checks, incomplete features, and their causes

Updated: 20 October 2026. Phase 9 results below remain historical and unchanged. The living-world B review and current C capability/limits are in [LIVING_WORLD_C_REPORT.md](LIVING_WORLD_C_REPORT.md).

Living-world follow-up: B's regression suite passed but did not cover maturity overshoot, inventories with more than three species, the viewer's stale tree mesh, or the entity quota. C adds those corrections and crafting/construction regression coverage. The A recurring/global model-budget/fairness requirement remains incomplete. Animal containment, autonomous woodcraft planning and new teaching experiments are later work. No failed scientific gate has been relaxed.

The main unresolved result is that the experimental learning policy **did not outperform memory-only controls and failed one retention requirement**. Its code runs, but it has not earned integration into autonomous inhabitants. Local-model action reliability and consistently successful teaching also remain limited.

The historical Phase 9 regression run passed **122 Python tests and 4 native checks**. Those checks establish the tested software behavior; they do not establish that every research objective succeeded.

Status meanings:

- **Failed acceptance:** implemented and evaluated, but a declared requirement was not met.
- **Partial:** working capability with recorded unsuccessful cases or limited evidence.
- **Deferred:** deliberately not implemented or evaluated in the current scope; no failed attempt is implied.
- **Unverified:** evidence is missing; failure has not been established.
- **Fixed:** an earlier implementation defect was corrected and is retained for transparency.

## 1. Features that failed a measured requirement

### Online learning beyond episodic memory — failed acceptance

**Implemented:** a three-weight non-neural policy that predicts whether an eat/drink action is feasible. Parameters persist across short episodes and update from verified native action receipts.

**What failed:**

| Requirement | Measured result | Outcome |
|---|---|---|
| Improve over frozen parameters by at least 10 percentage points | 65.21% balanced accuracy versus 50.00%; +15.21 points | Passed |
| Improve over EACH memory control by at least 5 points | Nearest memory: 67.71%; bracket memory: 83.33%. Online was below both. | Failed |
| Positive lower bound of paired 95% bootstrap interval against strongest memory | Online-minus-bracket interval: **[-19.17, -17.08] points** | Failed |
| At most 5 points of retention loss for EVERY seed | Seed 44 lost **10.42 points** on task A after block B | Failed |
| At most 5 points of mean retention loss | Mean loss was approximately **-1.67 points**, meaning a small mean improvement | Passed |
| No system/integrity failure during the study | Native replay and evidence audit passed | Passed |

**Why it did not advance:** the measured predictions were less reliable than the memory controls. Across all three evaluation stages, online made **39 infeasible attempts** and missed **31 feasible actions**. Its parameters also changed in a way that harmed retention for one seed. Seed 22 improved by 18.75 points, so the mean alone hides the failing seed.

**What is known about the cause:** the implementation uses shared linear weights, a fixed update rule and a shuffled finite curriculum. The result demonstrates order sensitivity and errors around the feasibility boundary. The study did **not** isolate whether representation, update rule, curriculum length or another design choice is the dominant cause. Changing those is a new experiment, not a confirmed fix.

**Current effect:** the learner remains outside live autonomous policies. The experiment completed successfully as an evaluation; the proposed benefit did not pass.

**What would clear the blocker:** a separately preregistered study that meets the comparison, uncertainty, retention and integrity requirements. Do not relax the existing gate or tune this completed study until it appears to pass.

Evidence: [Phase 9 report](PHASE9_REPORT.md), [preregistration](PHASE9_PREREGISTRATION.md), [measured summary and failures](../artifacts/phase9_summary.json).

## 2. Working features with unsuccessful behavioral results

| Feature | Status and evidence | What caused the recorded failures | Remaining gap |
|---|---|---|---|
| Local-model planning and action execution | **Partial.** The Phase 7 five-seed model arm recorded 9 native rejections across 10 structured plans. A separate current-runtime check had 2 rejected plans and zero successful model actions. | In that separate check, both plans requested eating without carried food: native `INSUFFICIENT_RESOURCE`. Successful parsing/planning did not establish executable action preconditions. The reports do not establish one common cause for all nine matrix rejections. | Reliable physical action selection by the model is unproven. Valid JSON, no provider fallback and a stored `planned` status are insufficient success criteria. |
| Teaching and cultural task transfer | **Partial.** Teaching completed in 3/5 seeds, versus 1/5 in each control. Only seeds 33 and 55 had source-backed transfer success. | Seeds 11 and 44 declined cooperative study and their blind fallback failed. In seed 22, the teacher withheld sharing and the identical blind choice succeeded in every arm; that success cannot be credited to teaching. These motive rules are authored. | Consistent transfer across motives/seeds is unproven. There is positive evidence for two source-backed cases, not universal teaching success or spontaneous model-driven education. |
| Higher-population simulation throughput | **Partial performance evidence.** An earlier 32-inhabitant target of 300 simulated seconds stopped at its wall budget at tick 121. A later isolated 120-second validation completed. | The earlier run exhausted its wall budget while overlapping verification. The isolated 32-inhabitant case took 53.686 worker seconds for 120 simulated seconds and recorded 114 failed actions. The report does not assign one cause to every failed action. | Longer sustained horizons and scaling are unverified. The completed shorter run does not turn the unfinished 300-second run into a success. |

Evidence: [Phase 7 report](PHASE7_REPORT.md), [Phase 6 report](PHASE6_REPORT.md). Counts above refer to their recorded experiments, not a new rerun.

## 3. Features deliberately deferred or outside the current model

These items were not failed implementations. The reason they are missing is stated below.

| Feature | Current state | Why it is absent / what blocks a completion claim |
|---|---|---|
| True 3D world mechanics | **Deferred.** The viewer renders authoritative 2D mechanics in 3D. | Heights and glyphs are presentation only. Native 3D movement, collision, reach and material rules require a separately scoped engine migration and validation. Camera movement is not inhabitant movement. |
| Longer continuous multi-seed horizons and 24-hour operation evidence | **Deferred.** Bounded unattended operation exists. | Longer tests were explicitly deferred. Short replenished-resource runs and summed durations across independent episodes do not demonstrate one continuously stable world or long-term sustainability. |
| General lifelong learning in live inhabitants | **Not established; integration blocked.** Phase 9 persists parameters across fresh episodes of at most three simulated seconds. | Its tiny fixed task does not establish continuous-world learning or broad transfer, and its advancement gate failed. |
| Neural policy/model-weight training | **Not implemented in the selected study.** The implemented learner is non-neural. | Phase 9 selected one mechanism and did not require a neural dependency. No neural training trial was attempted; no failed neural implementation or proven hardware impossibility is claimed. |
| Inherited parameters and generations | **Deferred.** No generation/reproduction mechanism was added. | Only one learning mechanism was evaluated. Cohort initialization, inheritance, variation/selection rules, population limits and inherited-versus-acquired controls still need an explicit study. |
| Intergenerational cultural transfer | **Deferred.** Phase 6 demonstrates limited transfer between existing inhabitants. | That does not implement cohort replacement or establish knowledge retention across generations. Explicit artifact-transfer rules and intergenerational controls are missing. |
| Artificial-life origins/evolution track | **Deferred; separate research direction.** | No cellular-automata or simpler-organism evolution experiment was implemented. Its evidence must remain separate from pretrained/humanlike-agent research. |
| Speech input/output | **Deferred optional adapter.** Text dialogue exists. | Speech adapters and their measured resource costs/license requirements were not implemented and validated. There is no recorded failed speech integration. |
| Open-ended discovery and civilization emergence | **Unproven.** Discovery/teaching experiments use bounded authored apparatus and controllers. | Finite search, authored motives and practice rules do not establish unrestricted invention, learned planning, spontaneous society formation or civilization emergence. |
| General-purpose real chemistry and biological realism | **Outside the current coarse model.** Simplified coupled materials/heat and authored chemistry exist. | Their validity limits exclude full molecular chemistry and realistic biology. More detail requires new modeled laws and validation; absence of full realism is not a failed conservation test. |
| Complete expired-history replay | **Not provided under bounded retention.** Current and retained archive heads can replay. | Old history is intentionally discarded when retention expires. Reconstructing an entire lifetime requires a different storage/archival policy and budget. |

Evidence: [current status](STATUS.md), [Phase 8 report](PHASE8_REPORT.md), [Phase 7 operations](PHASE7_OPERATIONS.md), [Phase 6 limitations](PHASE6_REPORT.md), [model limits](MODEL_LIMITS.md), [Phase 5 thermal model](PHASE5_THERMAL.md).

## 4. Validation that is still missing

| Area | What remains unverified |
|---|---|
| Durability outside tested interruption cases | Power loss, storage hardware failure and host-death cleanup. Process interruption/recovery tests do not prove these cases. |
| Other platforms/toolchains | Linux/MSVC behavior and portability of the Windows-specific unattended isolation implementation. |
| Broader rendering performance | Sustained thermal behavior, real mobile-device GPU performance and other browser/driver combinations. The recorded desktop/mobile viewport checks are not tests on every device. |
| Complete machine resource peaks | Browser/GPU/whole-machine peaks were not measured by the study-process working-set sample. |
| Broad learning generalization | Five training-order seeds and one authored fixed task do not establish competence across unrelated tasks or environments. |

These are evidence gaps, not confirmed defects. See [Phase 7 report](PHASE7_REPORT.md), [Phase 8 report](PHASE8_REPORT.md) and [Phase 9 report](PHASE9_REPORT.md).

## 5. Earlier implementation failures that were fixed

| Issue | Recorded cause | Current status |
|---|---|---|
| Phase 9 receipt-verification unit tests initially failed | Restoring the native checkpoint without the original run ID caused `UNAUTHORIZED`. | **Fixed before the study:** restore uses the reserved request's run ID; the relevant tests and study passed. |
| First Phase 9 full regression attempt did not finish | The verifier's 120-second subprocess allowance expired while it ran alongside the study. | **Resolved:** timeout output is now retained and the separate final run passed with a 240-second allowance. Its Python suite took 123.327 seconds internally, so the old limit was also below the final observed suite duration. |
| Phase 6 integration serialization failed | A departure set was not JSON-serializable. | **Fixed:** changed to a list; the failure artifact remains. |
| Phase 7 worker/supervisor integration failed during development | Windows pipe wrapper, process-spawn restrictions, pipe-close race and shared-runtime setup concurrency issues. | **Fixed in the reported implementation:** final tests passed; earlier failure/probe files remain. |
| Phase 3 model adapter produced an intermediate fallback | Adapter metadata bug. | **Fixed and regression-tested** before the successful recorded trace. |

Evidence: [Phase 9 verification attempt](../artifacts/phase9_verification_attempt1.json), [final checks](../artifacts/phase9_checks.json), and the respective [Phase 9](PHASE9_REPORT.md), [Phase 6](PHASE6_REPORT.md), [Phase 7](PHASE7_REPORT.md), [Phase 3](PHASE3_REPORT.md) reports.

## 6. Expected rejections that must not be reported as broken features

- Native rejection of an action without the required inventory preserves physical authority. The unresolved problem is a policy choosing that action, not the validator refusing it.
- Rejecting foreign-memory access, forged provenance, unauthorized interventions or stale requests is intended boundary enforcement.
- The Phase 8 avatar-placement collision was a valid native collision rejection. Forced WebGL/context-loss checks exercised the fallback and recovery paths.
- Controlled quota exhaustion, resource-starvation extinction, explicit stop requests and forced worker exits test distinct operational outcomes. They are not evidence that every normal run crashes or becomes extinct.

No sentience/consciousness criterion was tested. It is not listed as a failed implementation or as something the current evidence could certify.

This document summarizes retained project evidence as of the date above. It does not rerun experiments, change acceptance thresholds, activate a learner or authorize implementing deferred work.
