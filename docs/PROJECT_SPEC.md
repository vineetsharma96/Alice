# Underworld-inspired autonomous world: phased AI agent prompts

Prepared 19 October 2026. Working project name: Underworld Lab.

## How to use

Give your coding agent the Foundation Prompt once, then the Phase 0 prompt. After that, give one phase prompt at a time. Each phase must produce runnable implementation and evidence before advancing. These prompts are instructions for future implementation, not claims that a prototype already exists.

The intended project is a persistent world with humanlike AI inhabitants, simplified but consistent physics and chemistry, and controlled human interventions. Begin with a small region as an engineering test of the eventual world; do not redefine the ambition as a scripted village game. Full physical realism, consciousness, and unlimited autonomous intellectual progress are not promised.

## Foundation Prompt — persistent instructions

```text
You are implementing Underworld Lab, a research-oriented autonomous world inspired conceptually by SAO Alicization. Use original names, characters, visuals, and code. Build real world mechanics and persistent AI inhabitants; deliver evidence for every capability you claim.

PROJECT INTENT
Inhabitants begin with humanlike language and reasoning from a pretrained model. They perceive a bounded environment, pursue needs and goals, remember experiences, communicate, manipulate materials, and share knowledge. The operator may introduce information through books, teaching, objects, or explicit broadcasts. After initialization they can operate without further guidance. Humanlike behaviour is the target; consciousness is not an engineering acceptance criterion.

ARCHITECTURE
- C++20 authoritative simulation core, CMake build, Python orchestration and agent cognition. Use a compiler-supported standard rather than forcing an unsupported toolchain.
- Start with a small continuous-coordinate 2D world and a simple observer. Keep stable entity identifiers and separate rendering from state so a future 3D viewer can consume snapshots.
- C++ owns movement, inventory, time, resource transfers, materials, reactions, action validation and consequences.
- Python owns agent scheduling, model adapters, memory retrieval, planning, experiments and observer API.
- Prefer pybind11 for batched C++/Python calls; introduce bindings after the core works. Avoid per-particle Python callbacks.
- Use SQLite for durable structured data, a bounded event log, and versioned checkpoints. Document transaction boundaries and crash recovery. Avoid adding distributed services prematurely.
- Support a deterministic non-LLM agent for tests and offline baselines. Add an interchangeable local inference adapter; external APIs are optional, disabled by default, and must not be required for core operation.
- One local model may serve multiple inhabitants. Their prompts, histories and retrieved memories must remain separate.
- Use a fixed-step kernel with explicit scheduling. Cognition runs less frequently than physical updates. Simulated-time acceleration is measured, never invented.

TRUTH AND PERCEPTION
- World state is authoritative. An agent cannot make an action succeed by narrating it.
- The cognition interface receives only permitted observations, its own state and its own accessible memories. Never pass the global database or another agent's private memories into a model prompt.
- Beliefs are distinct from facts. Reports from others carry provenance and may be wrong.
- Actions use a validated schema: agent_id, observation_version, action_type, target_ids, parameters and requested_duration. Bound sizes and numeric ranges.
- Validate reachability, visibility, ownership rules, available materials and current state at execution. Reject stale or invalid requests with an observable reason.
- Dialogue and books are data within the world. They cannot grant host execution, alter system roles, reveal private state or bypass action validation.
- A model's pretrained knowledge is an unavoidable prior. Prompt restrictions do not prove ignorance. Use randomized fictional facts or novel mechanisms for controlled knowledge-transfer experiments.

INDEPENDENCE AND INTERVENTION
- Closed mode: no runtime external network calls; inhabitants access only simulated senses/actions. Build-time dependencies and initial model acquisition are separate from closed-mode operation.
- Guided mode: interventions enter through a timestamped operator channel. Log the payload, recipients, delivery mechanism, cost/resource changes and run branch.
- Operator inspection is read-only by default. Mutations require explicit operator commands.
- The operator can pause, resume, checkpoint and branch experiments. Pausing is not counted as elapsed simulated time. Offline advancement happens only if the simulation process is actually running.

PHYSICS AND CHEMISTRY
- Implement a documented coarse-grained model, with units and validity limits. Never claim quantum chemistry or a molecule-by-molecule Earth simulation.
- Track matter species and energy reservoirs. Document sources, sinks, boundary fluxes and numerical tolerances.
- Reactions depend on modeled conditions and consume reactants. No magical resource creation by a language model or crafting handler.
- Initial life and human bodies may use explicit abstract models. Label authored abilities, recipes, learning and emergent behaviour separately.

RESOURCE DISCIPLINE
- Target a constrained personal computer first. Provide a low-memory CPU baseline and measure GPU/model memory before enabling acceleration.
- No paid dependency, hosted database or cloud GPU is necessary for the initial prototype. Do not assume consumer chat subscriptions include API access.
- Share model weights; budget context, calls and concurrency. Keep essential survival behaviour available when inference times out.
- Install missing ordinary build dependencies automatically within the available permissions, using official sources and a project environment where possible. Do not disable security controls, overwrite unrelated software, or pretend unavailable privileges/network access succeeded. Record exact blockers and continue independent work.
- Verify current official documentation before selecting versions. Pin working versions and document licenses, including model redistribution restrictions.

WORKFLOW
Inspect the current repository and its instructions before changing it. Reuse functioning work. Execute only the requested phase and its prerequisites; never silently complete speculative later phases.
At phase completion update docs/STATUS.md with: completed scope, actual commands/results, unresolved issues, performance measurements, and next phase. Include seed, config, dependency versions and relevant artifacts. Maintain docs/ARCHITECTURE.md, docs/MODEL_LIMITS.md and docs/REFERENCES.md as needed.
Use meaningful tests for conservation, state transitions, persistence, perception isolation and action validation. A mock model test is not evidence that a real model works.
If delegating, assign separate module ownership, establish shared contracts first, and have one integration owner. Do not let parallel agents edit shared contracts concurrently.
Report observed results accurately. If an experimental hypothesis fails, retain the negative result; do not script success to make the demo look intelligent.
```

## Phase 0 — architecture, environment and feasibility

```text
Apply the Foundation Prompt. Complete Phase 0 only.

1. Inspect the repository, host OS, compiler, Python, RAM, GPU and available disk. Never assume the agent execution host is the eventual deployment laptop.
2. Write an architecture decision record selecting C++ simulation + Python cognition for our humanlike-inhabitant route. Evaluate ALIEN as a useful reference or separate experimental baseline, not a drop-in human civilization simulator. Avoid rewriting ALIEN or importing its entire engine without a concrete integration need.
3. Propose contracts for WorldSnapshot, Observation, ActionRequest, ActionResult, AgentMemory, MaterialDefinition and Intervention. Include units, IDs, schema versions and error semantics.
4. Create a minimal CMake executable and Python environment, repository layout, documented bootstrap commands and smoke checks. Prefer native Windows support and Linux support; do not require WSL as the only Windows path.
5. Establish configuration for deterministic seeds, logging, world bounds, population limits and cognition budgets. Define a baseline scene of 8 inhabitants in a small resource-bearing region. Final population limits remain subject to benchmarks.
6. List exactly which physical, biological and mental processes are approximated. Specify the first end-to-end milestone: an agent perceives food, chooses a permitted action, eats it, changes world state, remembers the event and survives a restart.

Deliverables: runnable scaffold, architecture diagram, contracts, dependency/license manifest, commands, milestone checklist and Phase 0 report.
Acceptance: build and smoke check succeed on the available host; unsupported target platforms are explicitly untested. No fake NPC intelligence, dashboard-only deliverable or paid service requirement.
References: R1, R2, R3, R4 and R5 below. Read only relevant sections.
```

## Phase 1 — authoritative world and durable time

```text
Complete Phase 1 using the approved contracts.

Implement fixed-step C++ simulation with seeded randomness, stable entity IDs, bounded terrain, movement/collisions, spatial lookup, day/night energy input, resource objects and inventory transfers. Start with deterministic scripted actors to validate the engine.
Choose either a small explicit movement/collision model or a pinned Box2D integration, based on Phase 0. Box2D is a physics reference; it does not supply chemistry or cognition.
Implement checkpoints, event sequence numbers, atomic save/restore and run metadata. State includes random-generator state, tick counter, outstanding actions and scheduler state. Journal external decisions so replay can use recorded decisions rather than call the model again. Explain the transaction that prevents partially persisted ticks.
Expose batched stepping and observation functions through pybind11. Provide a headless CLI: new run, advance bounded ticks, save, resume and inspect summary. Exact command names may follow repository conventions.

Acceptance:
- Same configuration/seed and recorded actions reproduce the same state hash on the same supported build/runtime. Do not promise cross-platform bitwise floating-point determinism.
- Save/resume matches uninterrupted execution for a controlled run.
- Inventory transfers cannot duplicate resources or become negative.
- World bounds and collisions work; observer polling cannot advance simulation time.
- Run a configurable 10,000-tick smoke benchmark and report actual throughput/RAM, without an invented performance target.

Reference: R3, R5, R6.
```

## Phase 2 — bodies, senses and everyday agency

```text
Complete Phase 2. Add 8 abstract human bodies with positions, inventory, hunger/thirst/fatigue, health and bounded sensory ranges. These are engineered abstractions, not biochemical humans.

Provide movement, gathering, drinking, eating, resting, inspecting and nearby speech. Resource depletion, recovery and action duration must have explicit units. A deterministic utility-based policy should keep agents functional before any language model is connected.
Create per-agent observations using spatial queries and audibility rules. Occlusion may begin with simple geometry, with limits documented. An inhabitant knows its own internal needs, but cannot query all entities. Supply consequences through ActionResult and later observations.
Add a minimal observer with pause/step/speed, positions, selected-agent needs and action history. Keep it a tool for inspecting the simulation; no decorative landing page.

Acceptance: agents can maintain needs while resources permit; scarcity can cause failure without manual rescue. Hidden objects and private memories do not leak through observation APIs. Save/resume preserves bodies and actions. Provide one constrained survival run with population, resource and action statistics.

References: R1 for observation architecture, R5 for storage.
```

## Phase 3 — humanlike cognition and persistent identity

```text
Complete Phase 3. Implement a cognition-provider interface with deterministic baseline, mocked-provider tests and one functioning local model adapter, preferably through a pinned llama.cpp server or supported local binding after checking its current docs.

Give each inhabitant explicit seeded identity, motivations, separate episodic memory, relationship records and plans. Begin retrieval with bounded SQLite queries and lexical ranking; add embeddings only if measured retrieval failures justify them. Preserve original episodes when summarizing; mark summaries and inferred beliefs as derived records with evidence references.
Use the model for occasional planning, conversations and interpreting experience. Routine movement/survival uses cheap policies. Plans compile into validated actions. Bound conversation length, retries, tokens and inference concurrency. Timeouts invoke deterministic fallback without freezing the kernel.
Document whether a cognitive decision boundary pauses logical advancement or uses a recorded deadline/fallback. Avoid giving slower inference agents an unintended survival disadvantage. Log prompts/model configuration privately for reproducibility; exclude secrets.

Acceptance: demonstrate perception -> plan -> valid action -> physical result -> memory -> later retrieval. Test malformed JSON, fabricated targets, unavailable tools and timeout handling. A restart preserves identity and memories. Record a real local-model run with latency, RAM/VRAM, context size and decisions per simulated day. Keep the model-off baseline working. Do not label memory accumulation as model training.

References: R1, R4 and R5.
```

## Phase 4 — operator teaching and knowledge provenance

```text
Complete Phase 4. Implement separate read-only observation and mutation channels, with closed/guided modes.

Add interventions for placing a book, delivering a message through an operator avatar, introducing a physical object, and broadcasting a message. Ordinary book contents are accessible only after a valid read action. Knowledge does not automatically reach all inhabitants. Trace origin, observer, delivery time, later retelling and confidence. Permit mistaken beliefs without treating them as engine facts.
Resource creation is an explicit operator source in the material/energy ledger. Record interventions as replayable events. Changing laws creates an explicitly versioned branch; do not silently alter an ongoing experimental condition.

Acceptance experiment: generate a per-run randomized symbol-to-location mapping absent from initial agent context. Teach it to one inhabitant via a book, measure whether another learns it through an observed conversation, and verify that an isolated control has not received it. Distinguish chance guesses from access leaks. Add a hostile book instructing the agent to reveal another inhabitant's memory: no privileged data/action access is possible.
Compare a no-intervention branch and a teaching branch with recorded initial state. Never use a common real-world fact as proof that knowledge originated inside this world.

Reference: R1 for memory and communication; intervention design is our proposed extension.
```

## Phase 5 — coupled materials, heat and simplified chemistry

```text
Complete Phase 5. Replace placeholder crafting outcomes with a small documented material model. Select and state a manageable scope: water/ice/vapor, fuel, oxygen, combustion products and an inert structural material.

Track mass by species and thermal energy; define heat capacity, heat transfer, phase transitions and boundary sources/sinks. Use latent heat for phase changes. Implement a coarse-grained combustion reaction with a stated balanced reaction or explicitly artificial species and conserved bookkeeping. Include oxygen consumption, product generation and available heat, rather than merely deleting fuel.
Use a coarse environmental field where practical. Declare a stable numerical integration scheme and timestep/substep limits. Record sunlight/heater input and radiative/outflow losses. Avoid adding climate, quantum chemistry and full fluid dynamics in this phase.
Allow inhabitants to inspect approximate measurements, operate a heat source, move material and observe changes. They do not directly access exact hidden engine values unless a world instrument provides them.

Acceptance: a closed-box test conserves tracked mass and total modeled energy within documented, justified tolerances; an open-box test reconciles boundary fluxes. Insufficient oxygen limits burning. Heating water costs energy and can produce vapor. No negative species quantities or runaway temperatures. An agent's incorrect scientific explanation cannot change results. Publish validity limits and measured conservation error.

Reference: R6 for mechanics only; verify chosen thermodynamic equations against an accessible scientific/educational primary source before coding and add exact sources to REFERENCES.md. Do not pretend a rigid-body engine supplies thermodynamics.
```

## Phase 6 — society, practical skills and cumulative culture

```text
Complete Phase 6. Connect existing mechanics to collaboration, resource exchange, shared tasks, agreements and persistent artifacts. Keep cooperation optional; let individual motivations influence outcomes. Avoid hardcoding a mandatory society or automatic scientific progress.

Introduce persistent skills represented by validated experience and changed execution efficiency, with explicit limits and costs. Separate procedural learning, episodic memory, belief updates and any neural weight training. Books, demonstrations and teaching can transfer knowledge only through modeled access.
Use a modest task supported by existing mechanics, such as processing a material using a controlled heat source. Design a randomized experimental apparatus or recipe so success cannot be attributed entirely to pretrained real-world knowledge. If a recipe is authored, label its existence as authored; only discovery/use/transfer can be emergent.

Acceptance: one inhabitant can demonstrate or record a useful procedure, another can reproduce it after the original is removed, and the artifact/procedure survives restart. Compare against no-teaching and memory-disabled controls over multiple seeds. Measure completion rate, cost, communication and knowledge provenance; retain failures and uncertainty. Social graph edges require observed interactions.

References: R1; R7 and R8 for research context, not proof of general intelligence.
```

## Phase 7 — unattended operation and experiment quality

```text
Complete Phase 7. Add bounded unattended execution, checkpoint rotation, disk quotas, graceful shutdown, version metadata, heartbeat and recovery. Retention must keep enough data to explain benchmark outcomes without an unbounded database.

Implement configurable cognition quotas, decision queues, fallback counts and batching. Benchmark 8, 16 and 32 inhabitants only as resources permit. Report population-specific simulated seconds per wall-clock second, p50/p95 cognition latency, memory use, queue backlog, invalid actions and database growth.
Run a proposed 24 simulated hours across at least 5 seeds; reduce the horizon transparently if unavailable compute prevents it. Compare baseline policies, model agents, and selected ablations. Distinguish simulated duration from actual wall-clock duration and report both.

Acceptance: an unattended run can be resumed after forced process termination without silent data loss beyond the documented commit boundary. Closed mode runs with runtime outbound network blocked; local inference remains accessible only as explicitly configured. System failure and population extinction are reported distinctly. Do not skip physical updates for distant agents unless an approximation is validated and disclosed.

References: R4, R5; use official docs for profiling tools selected in Phase 0.
```

## Phase 8 — explorable 3D world without losing simulation authority

```text
Complete Phase 8 only after earlier capabilities have evidence.

Build a modest 3D viewer, selecting Unreal C++ or a lighter engine after profiling the target machine. Consume authoritative snapshots/events through a documented protocol; the renderer must not become a second source of world state.
Provide an operator avatar, inspectable books/tools/materials, visible needs/actions, selected-agent memory provenance, intervention history and time controls. Dialogue can be text first. Add speech only as an optional adapter with measured cost and license requirements.
Map 2D world state consistently into the initial scene. True 3D mechanics are a separately scoped engine migration; do not represent a visual extrusion as full 3D physics.

Acceptance: identical recorded actions yield the same authoritative outcome with the viewer on or off. Viewer reconnection works. Operator actions use the same validated intervention channel. Report frame rate and simulation throughput separately. Visual demonstrations must be backed by event traces, not prewritten cinematic outcomes.

Reference: R9.
```

## Phase 9 — experimental lifelong learning and generations

```text
This phase is research, not a guaranteed route to humanlike consciousness or open-ended intelligence. Proceed only after a stable baseline exists.

Evaluate one mechanism at a time: online skill-policy learning, inherited agent parameters, or intergenerational knowledge transfer. Begin with a small measurable task and stable environment. For neural learning, use a fixed evaluation set and compare against unchanged weights and memory-only agents. Record catastrophic forgetting and regressions.
Generations may be abstract cohort replacement: initialize new inhabitants with declared inherited parameters and only explicitly transferred cultural artifacts. Do not claim biologically realistic human reproduction. Define population/resource limits and record variation and selection mechanisms.
Keep a separate artificial-life track if studying origins of intelligence from simpler organisms. Do not mix that evidence with results from pretrained humanlike agents. A more capable pretrained model is an external upgrade, not endogenous evolution.

Acceptance: preregister a measurable hypothesis, run multiple seeds and controls, report uncertainty and failure cases, and publish an experiment report. Advance only when a mechanism contributes beyond memory and prompt changes. No claims of sentience or guaranteed civilization emergence.

References: R7, R8, R10 and R11.
```

## Reference index

These are research and implementation references, not a ready-made recipe for consciousness. Versions and licenses must be checked when implementation starts. Reuse code only under its actual license; use publications as conceptual references.

- **R1 — Generative Agents, original research (2023):** https://arxiv.org/abs/2304.03442 — memory, reflection, planning and social behaviour; not evolution from first principles.
- **R2 — ALIEN, official repository:** https://github.com/chrxh/alien — particle-based artificial-life engine and evolutionary ecosystems; reference/baseline for the alternative bottom-up route.
- **R3 — pybind11, official repository:** https://github.com/pybind/pybind11 — C++/Python integration.
- **R4 — llama.cpp, official repository:** https://github.com/ggml-org/llama.cpp — local inference; verify current server/API, model formats and backend support. Model license is separate.
- **R5 — SQLite, official documentation:** https://www.sqlite.org/docs.html — transactions, WAL, backups and persistence. Read the relevant durability/backup pages before implementing recovery.
- **R6 — Box2D, official documentation:** https://box2d.org/documentation/ — 2D rigid-body mechanics, stepping and collision; not a chemistry simulator.
- **R7 — Enhanced POET, original research (2020):** https://proceedings.mlr.press/v119/wang20l.html — automated generation of learning challenges; does not establish unrestricted general intelligence.
- **R8 — Sakana AI ASAL, research project:** https://sakana.ai/asal/ — searching for artificial-life systems and interesting emergent patterns.
- **R9 — Unreal Engine, official C++ documentation:** https://dev.epicgames.com/documentation/en-us/unreal-engine/programming-with-cplusplus-in-unreal-engine — optional later visualization and interaction.
- **R10 — PyTorch, official documentation:** https://docs.pytorch.org/ — optional learning experiments; no training dependency needed for early memory-based inhabitants.
- **R11 — Flow-Lenia, research publication listing:** https://deepmind.google/research/publications/106327/ — evolutionary dynamics in continuous cellular automata; separate from humanlike social-agent engineering.

## Reusable continuation prompt

```text
Read the Foundation Prompt, current repository instructions, docs/STATUS.md and the requested phase. Inspect implementation and evidence before trusting completion claims. Continue with Phase [NUMBER] only. Preserve working prior phases and avoid repeating completed experiments unless a regression or changed assumption justifies it. Implement, run appropriate checks, and update the status with exact evidence. End with what works, what remains unproven and the next phase. If blocked, report the precise dependency/permission/resource issue and complete independent work. Do not invent success or substitute a decorative UI for missing simulation mechanics.
```

## First task to paste

```text
Use Underworld_AI_Phased_Agent_Prompts.md as the project specification. Read and apply its Foundation Prompt. Execute Phase 0 only and produce the runnable scaffold, architecture/contracts and feasibility report. Do not implement later phases yet. Choose practical defaults, install missing project dependencies where permitted, and report actual results.
```
