# Stabilization evaluation protocol v1

Registered before implementation measurements, 2026-10-20. This milestone is authored execution engineering, not Phase 9 learning. Preserve Phase 9 registration, reports, code, traces and native study databases unchanged. No learner import into live policies.

## Baseline and diagnosis

Before implementing the controller, reproduce the existing utility and local-model paths in fresh bounded worlds. Record permitted input, raw JSON, compiler outcome, plan status, decision submission, terminal receipt, need changes, native error codes, fallback and end-to-end latency. Use the pinned existing CPU model. Do not equate any intermediate stage with a completed goal. Repeat a nonurgent empty-inventory case and an aged-needs case to distinguish compiler behavior from scheduler preemption. Existing baseline implementations must remain unchanged.

## Development versus held-out

Development uses seed 101 and quantities food 0.8 kg, water 1.2 kg. Development fixtures cover gathering, carried food, scarcity and saving during an action. Unit fixtures may inject interruptions and provider errors. Development may change implementation; freeze its source hash before running held-out evaluation.

Held-out seeds are 202,303,404. Each has five scenarios: carried food, gathering required, unavailable food, depleted target, interrupted plan. Each fixture ages bodies through 160 actual native seconds without a policy; no direct body or inventory writes. Population two, dt=1 s, regeneration zero, finite initial food 0.6 kg and water 1.8 kg (unavailable: food zero; depleted: food 0.4 kg). Actor 1 is evaluated. Carried-food fixture gathers 0.2 kg natively. Gathering/depleted fixtures move actor 1 natively to (6,2). Depleted fixture has actor 2 gather all source food at relative tick 2. This logged competitor action is identical across arms. Interrupted fixture saves and reopens at relative tick 5, retaining pending physical and logical state. All fixtures retain the setup history and costs.

Compare four arms from identical fixture backups: unchanged utility, unchanged legacy local-model scheduler/compiler, stabilized authored goal selection, stabilized local-model selection with explicitly labeled authored execution/safety fallback. Utility scheduling interval is one native second in all utility-baseline fixtures. Each arm gets 90 continuous evaluation seconds. Local-model arms have one actual inference call at evaluation start, timeout 20 s, input 1536/output 128 tokens; no automatic inference retry. Thereafter stabilized model uses a disclosed deterministic need selector if another goal is necessary. Hold logical time during inference. Preserve the raw choice even when safety execution overrides it. No extra model knowledge or training is introduced.

Food goal: ingest >=0.2 kg during evaluation. Water goal: ingest >=0.3 kg during evaluation. Feasible food goals: carried, gathering, interrupted; water feasible in all scenarios. Unavailable/depleted food is excluded from the feasible-food denominator, but missing food, needs, waits and action failures remain reported. Depleted food is removed before the distant actor can reach it. Do not classify legitimate scarcity as a policy defect. Record attempted food goals separately from physical feasibility. Gathered-only food is not goal completion.

Metrics: goal completions, missed feasible goals, accepted requests, terminal completed/failed actions by kind, native rejection reasons, preventable rejections (freshly missing inventory, capacity or known out-of-reach target), necessary race/physical failures, survival, per-tick need means/maxima and time above 0.85, provider JSON/compiled-plan counts, model-selected versus fallback-selected goals, authored execution steps, fallback reasons, model latency, controller/whole-run wall cost, simulated duration, DB bytes and replay/conservation.

## Locked acceptance thresholds

- Stabilized authored AND stabilized-model arms complete every feasible food/water goal in every held-out scenario within 90 simulated seconds; scarcity/depletion must not induce an eat-without-food request.
- Zero preventable native rejections from stabilized execution; record necessary rejections separately and do not suppress native errors.
- All evaluated actors survive; no increase in missed feasible goals versus utility. Stabilized-model improves feasible goal completion over legacy-model if that baseline misses goals; otherwise matches it.
- Every action/goal has origin attribution. Model inference errors and quota/need overrides are explicit; model-independent completion is not credited to learned/model planning.
- Native replay, material accounting, own-memory boundary, bounded retries, save/resume of scheduler/needs/memory/active goals all pass. No hidden resource regeneration, body reset or goal success inferred solely from a plan/submission.
- Any failing threshold remains a failure. Do not retune against held-out outcomes. Repair implementation bugs only with a disclosed amendment and preserve the original held-out run.

## Continuous checks

After held-out evaluation, use one persistent finite-resource world per stabilized arm: one actor, food 2 kg, water 4 kg, no regeneration, dt=1 s. Check cumulative horizons 30,120,600,1200 seconds progressively, with a 240-second wall allowance per arm. At 120 seconds save a backup and resume in a fresh Python process; never reset bodies, resources, memories or controller state. Model arm has at most two inference attempts over the entire continuous run; later need decisions are deterministic fallback and reported. Compare the saved/resumed continuation with an uninterrupted counterpart using the same already committed decisions (no regenerated inference). Record simulated and wall duration and any cutoff without extrapolating to 24 hours.

## Boundaries

Execution sequence: locate using permitted perception -> approach -> gather -> consume; reobserve before each submission and after every receipt. At most two physical failures per goal, 24 movement/search steps, 120 simulated seconds per goal, finite journal and inference budgets. Unknown/absent supply is blocked or searched with bounds; no omniscient resource location. Persistence must reserve a request before submission and reconcile receipt after interruption, without double consumption. Existing native validator and all rejection semantics stay unchanged. Explicit handoff may stop the old utility/legacy-plan scheduler, but must preserve physical state, memories and prior journals and record the handoff. Existing Phase 8/9 data is never silently converted.
