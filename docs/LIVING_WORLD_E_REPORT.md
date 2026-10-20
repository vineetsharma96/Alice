# Milestone E — bounded planning and receipt-linked adaptation

21 October 2026. Application **0.12.0**, controller **stabilization/4**; native
UW9 / DB10 / checkpoint 9 and build
`832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896` are unchanged.
[Protocol](PHASE_E_PLANNING.md), [fixture amendment](PHASE_E_EVALUATION_AMENDMENT_1.md),
[operations](PLANNING_OPERATIONS.md), [final registration](../artifacts/living_world_e_registration_final.json).

## Implemented behavior and attribution

The existing stabilization coordinator now executes explicitly assigned
hierarchical tasks: obtain food/wood, craft an axe, produce planks, build a trough,
deliver water, tend an observed animal, inspect a problem and rest. Shared
operators resolve real ingredients, tools, carrying capacity, approach, harvest,
collection, construction work and ingestion. Every primitive goes through native
validation and the existing durable pending-request reconciliation. General pen
topology and teaching requests remain explicit unsupported outcomes.

Goals/procedural decompositions are externally assigned and authored. Inhabitants
do not receive the native operator recipe registry. Routine survival preempts
between native actions; deadlines also include preempted time. Source selection
uses only local permitted sight, own stock/tools, and own verified action results.
Coarse navigation has bounded finer-grid/visibility-graph fallbacks over perceived
geometry. No teleport, hidden stock map or replenishment is used.

Task stage, failures, request ownership, cancellation requests, source hypotheses,
procedure episode references and optional inference reservations persist in the
checksummed controller store. Own successful terminal receipts plus an observable
goal predicate can create a reusable authored-procedure evidence record. Already
satisfied/external outcomes get no new procedure credit. Missing procedure backing
fails closed. Episodic memory, authored failure preferences, procedural evidence
and native workmanship remain separate; no skill or model weights are injected.

Cancellation waits for an in-flight primitive's actual receipt and retains its
effects. Only one existing writer owns the world. Both read-only viewers display
task state/origin/outcome. The normal desktop rejects an active model-assisted
task before advancing, keeping its model-off guarantee.

## Corrected confirmation comparison

The first utility fixture accidentally disabled its scheduler with scripted=False.
Its original report/data and registration remain intact; its utility comparison
is invalid even though its limited original gates printed passed=true. The
amendment fixes only fixture activation and matched warmup, adds activation and
initial-physics gates, and uses fresh seeds **1329/1449**. The controller digest
stayed frozen at `2ba240466a8bb0850837af0fc7d3d842df305f99b61be4eaf9122c088a9ccb1c`.
Development seeds 21/31 and earlier 929/1049 results are separate evidence.

Each arm has 12 cases: two each of harvest-to-axe, water delivery, empty forage,
blocked construction site, animal thirst and absent peer. Six have feasible
assigned goals; the other six correctly leave goals unmet. Initial native hashes
match across arms for every seed/case. The animal fixture has an identical declared
80-second native preparation before policy measurement, with bodies/stock retained.
Each comparison allows 60 simulated / 180 wall seconds; completed tasks stop early.

| Arm | Feasible assigned goals | Completed native actions | Submission rejections | Terminal failures | Model calls | Sum of case wall s |
|---|---:|---:|---:|---:|---:|---:|
| Utility survival reference | 0/6* | 34 | 0 | 0 | 0 | 15.233 |
| Authored hierarchy | 6/6 | 118 | 0 | 8 | 0 | 53.117 |
| Episodic-only control | 6/6 | 118 | 0 | 8 | 0 | 51.939 |
| Adaptive authored source preference | 6/6 | 142 | 0 | 2 | 0 | 59.198 |
| Model-assisted operator choice | 6/6 | 150 | 0 | 5 | 4 | 80.458 |

*Utility has no production/care assignment interface. It actually runs and
completes survival actions; lack of those task goals is not a survival defect.
Its 60-second wall cost is not time-to-production. Counts for other arms include
survival preemption. Every human is alive at its own cutoff, but exposure differs;
this is not a comparative long-term survival result. Summed case durations are
not one continuous life.

Native failures above are NO_PLACEMENT during preparatory harvesting in blocked
construction cases. Native refusal preserves mass. Repeating that failure on
the same source is an avoidable retry; first-failure avoidability is not isolated.
Adaptive preference reduces retries but also does more work on alternative
sources before the assigned impossible site is rejected. Site feasibility is
checked at the construction stage, so preparatory work can be wasted. Fewer
failures alone does not establish better total efficiency.

All integer food/water/body balances close, native invariants and replay pass,
and unavailable cases are not counted as policy defects or successful goals.
Per-case simulated/wall duration, actual transfer requests, initial/final material
totals, boundary inputs, failures and provenance are retained in
[final evaluation](../artifacts/living_world_e_evaluation_final.json) and
[summary](../artifacts/living_world_e_summary.json); raw saves/receipts are in
`data/living-world-e-confirmation-valid-20261021`. Transfer totals count movement
through stages, not net matter creation or net resource consumption.

## What adaptation and model results establish

In each matched saved-branch comparison, a moving peer causes an actual native
collision approaching wood-a. After the peer withdraws, both branches have the
same physical observation and own collision evidence. Adaptive mode chooses
wood-b; episodic-only chooses wood-a. Both finish and replay exactly. The choice
change is caused by the authored receipt-derived preference, not a new sensor
or another actor's memory. It takes **3.4 simulated seconds versus 2.0** after the
blocker has cleared: stale avoidance is slower here. This demonstrates bounded
experience-dependent behavior, not general performance improvement or learned
planning. There is no new training or integration of the Phase 9 learner.

Four real pinned SmolLM2 calls yield valid operator-index JSON; four selected
requests are accepted and complete. Only two associated full goals complete,
because the other two request an impossible construction site. These are distinct
stages. Model reason text includes incorrect permission assertions, so it is
stored as untrusted narrative and grants no authority. Execution/decomposition
stays authored. Total measured inference wall cost is **21.686 seconds**,
**826 input / 90 generated tokens**. No completion advantage or justified model
benefit is demonstrated. Models remain optional/off by default. Worker memory
samples do not measure total llama-server, browser or whole-machine peaks.
Across that arm's 153 task-primitive selections, only **4** come from model
indices; **40** use explicit deterministic fallback after bounded eligibility,
and **109** are routine authored choices with one available operator. Physical
execution is authored for all 153. Survival preemption is separate. A valid model
reply must not be credited for the rest of that procedure.

## Broken tool and continuous persistence

The separate [prospective tool supplement](PHASE_E_TOOL_RECOVERY_SUPPLEMENT.md)
uses development seed 21 and confirmation seeds **2129/2149**. A declared aged
axe with one use remaining is actually broken by native plank crafting; its
constituents return physically. All four task modes in both confirmation seeds
craft a new real axe: **8/8**, one completed repair request each, **4.2 simulated
seconds** including reconciliation, zero inference calls, zero rejections/failures,
zero balance errors and exact replay. Utility performs survival work and does not
repair. The fixture's **53.4-second native preparation** preserves needs/resources
and is recorded separately from the NEW durable comparison checkpoint.
[Tool evidence](../artifacts/living_world_e_tool_recovery.json),
[receipt diagnostics](../artifacts/living_world_e_tool_diagnostics.json).

One separate model-off one-human/no-animal 8 m world runs **120 continuous
simulated seconds / 32.879 primary wall seconds**, in 2/8/20/90-second segments.
Its assigned provide_water task bootstraps axe → planks → trough → real 0.3 kg
water delivery and completes after 65.5 simulated seconds. It records one genuine
placement failure with recovery, 40 task primitives and one survival drink goal.
No regeneration, body reset or stock refill occurs. A backup at 30 seconds resumes
90 seconds in a fresh process in **24.925 wall seconds**, matching native state,
identity, private memories and all eight controller/memory tables exactly.
Replay passes. Wall measurements are host observations, not dedicated throughput
benchmarks. [Continuity evidence](../artifacts/living_world_e_continuity.json).

## Full software verification

Final regression verification passes **209 Python tests in 315.240 seconds** and
**four native checks**. The 19 E regressions cover the task chain, real collision
adaptation/ablation, aged/broken-tool repair, scarcity, urgent preemption,
deadline/cancellation, missing-source failure, model reservation/fallback,
desktop boundaries, active utility and matched warmup, plus in-flight backup and
crash recovery. Existing earlier-phase tests remain intact.
[Full checks](../artifacts/living_world_e_checks_final.json).

The rebuilt executable is **12,617,523 bytes**, SHA256
`a4060affb114b35bea4ff7214c8f0b3e6176b577054ccd18db33ae4d581f93ca`.
Reduced-PATH smoke checks pass executable → source → executable continuation,
backup/replay/default config, packaged E assignment and native inspection,
procedure-backed completion, source pin parity and refusal of model-assisted
desktop execution without advancing time. Both UIs show E task status, preserve
read-only controls and pass privacy/animal rendering checks without page errors.
[Package](../artifacts/living_world_e_package.json),
[basic smoke](../artifacts/living_world_e_package_smoke.json),
[task/desktop smoke](../artifacts/living_world_e_package_tasks.json),
[viewer](../artifacts/living_world_e_viewer.json).

Python lint, JavaScript/Git Bash syntax and static connection checks pass. The
connection inventory parses 86 Python modules, finds no missing local links and
no repeated substantial whole production functions; this is not full branch
coverage. The independent Phase 9 audit recomputes its original metrics and
keeps advance=false. Protected source/report/study hashes match.
[Phase 9 audit](../artifacts/living_world_e_phase9_audit.json).

## Limits and remaining milestones

Tasks are assigned, not spontaneously formed by a model or society. Arbitrary
cargo rearrangement, crowded layouts, unseen peers/resources, full storage/trough
recovery, pen topology planning, general teaching and universal animal-care
success are not established. Confirmation changes some human/resource positions;
care and collision layouts are controlled and do not prove broad geometry
generalization. Two confirmation seeds are limited evidence. Experience bias can
be stale; reusable records retain authored decompositions rather than inventing
new recipes. E-aware long-term pruning/archival remains G work; missing evidence
cannot silently acquire a new source.

A's recurring fair/global inference budgeting remains incomplete. E uses separate
small lifetime/per-task/pacing bounds and does not inherit AppContainer claims.
F knowledge initialization/embodied teaching and G integrated four-person
demonstration remain next work. Breeding, cooking, speech, neural training and true
3D remain deferred. Phase 9's sealed failed gate and source corpus are unchanged.
No intelligence/consciousness/civilization claim follows from these results.
