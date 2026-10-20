# Alice: living world expansion and new-agent handoff

Prepared 20 October 2026. Repository: https://github.com/vineetsharma96/Alice

## Start here — paste this prompt into the new coding agent

```text
Continue the existing Alice / Underworld Lab repository. Implement the living-world expansion described in this file, in ordered milestones. This is continuation of an existing simulation, not permission to replace it with a new game or decorative dashboard.

The user wants a richer autonomous world: trees -> harvested wood -> useful objects; wild animals and livestock; food production; and inhabitants that can plan, learn practical procedures and teach one another. The operator must be able to start a new experiment with selected initial knowledge, or introduce knowledge to one chosen inhabitant of an existing world.

Treat general intelligence as a research ambition. Deliver measurable planning, skill acquisition, transfer and adaptation. Do not claim AGI, consciousness or endogenous model improvement because an LLM talks, a skill counter rises or an authored recipe works.

First read this specification and perform Milestone A. Continue implementing the later milestones sequentially when their prerequisites pass. Keep a runnable baseline after each milestone; finish as many complete milestones as the available session permits. Do not stop after writing a plan. At a genuine resource/dependency blocker, finish independent work and leave a precise handoff. Never skip validation or substitute hardcoded success to declare the expansion complete.
```

## Existing project: verify before changing

```text
Inspect local repository state, applicable instructions, README, docs/STATUS.md, STABILIZATION_REPORT.md, STABILIZATION_OPERATIONS.md, ARCHITECTURE.md, MODEL_LIMITS.md and FAILED_AND_DEFERRED_FEATURES.md. Read phase-specific contracts when modifying their modules. Check local uncommitted work and remote updates; preserve unrelated changes. If local files differ from this handoff, inspect actual implementation and evidence before deciding what is current.

Reviewed baseline as of 20 October 2026:
- C++20 authoritative world, Python orchestration/cognition, pybind11, SQLite, Three.js viewer.
- Native UW6 / DB7 baseline; current source identities must be verified locally.
- Bodies/needs, permitted perception, private episodic memory, book/report provenance, interventions, a small thermal/cultural apparatus and bounded unattended operation already exist.
- Opt-in stabilization supplies authored survival prerequisite execution. It is separate from the old observer writer and Phase 7 isolated supervisor.
- Reported stabilization evaluation: 24/24 feasible goals per stabilized arm; one-active-inhabitant continuity reached 1200 simulated seconds. These are bounded results, not all-population reliability.
- Phase 9's three-weight learning experiment failed its advancement gate. Preserve its registered study, source snapshots and results. Do not integrate that learner or change its thresholds.
- Default local model is a small pretrained CPU model; do not assume it can reliably perform complex planning.

Some overview documents retain stale current-phase statements. Reconcile their live summaries while preserving historical phase reports, sealed protocols and archived source snapshots. Root LICENSE is MIT; check current dependency/model notices separately.

Install missing ordinary project dependencies within existing permissions using official sources and a project environment. Record genuine permission, network or hardware blockers. Avoid unnecessary heavyweight dependencies and paid services. A consumer chat subscription is not an inference API entitlement.
```

## Non-negotiable architecture

```text
1. C++ remains the authority for living entities, resources, elapsed time, action validation and all physical consequences. Python plans and schedules; the model proposes structured goals/actions. Neither narrative nor a GUI can declare physical success.
2. Inhabitants see only local permitted observations and their own accessible memories. Operator diagnostics, animal hidden state and the recipe registry are not automatically agent knowledge.
3. Reuse one coordinated scheduler and single-writer lease. Extend the stabilized executor through explicit handoff rather than running several competing controllers. First preserve a model-off fallback.
4. Use stable IDs, versioned actions/events, transaction-safe persistence, restartable in-flight actions and source-linked outcomes. Document new checkpoint/database versions. Never silently rewrite incompatible saved worlds. Supply an explicit migration only if tested; otherwise create a new compatible experiment and preserve the old one.
5. Integrate simulation systems spatially: tree/animal location, reach, visibility, obstacles and item placement affect what can actually happen. A growing tree must not silently overlap an actor or trap it without a declared rule.
6. Start with a small 2D authoritative region and existing 3D presentation. More varied meshes do not constitute true 3D mechanics. Use lightweight original/procedural visuals first.
7. Explicitly model material/energy sources, products, waste and boundary fluxes. Reuse integer mass accounting. Do not label arbitrary biomass increases as conservation.
8. Label authored rules, model-selected goals, authored execution, observed learning, practice improvements and operator teaching separately in traces and UI.
```

## Milestone A — consolidate runtime and establish scope

```text
Read the real code before edits, then create docs/LIVING_WORLD_PLAN.md and a concise HANDOFF.md. Map existing modules to proposed changes; record contracts and a dependency order.

Make the stabilized scheduler selectable through one documented runtime entry point. Expose its goals, stage, goal origin, model-call budget and fallback in the observer. Preserve read-only attachment and one writer. If enabling the isolated supervisor requires work, explicitly test the integration; do not inherit its security claims automatically.

Replace the two-call-lifetime research default for the new living-world configuration with a bounded, paced model budget: per-agent eligibility, a global wall-time/token allowance and fair scheduling. Keep the original benchmark settings available unchanged. Logical-time decisions and inference timeouts must have one documented policy. LLM calls are reserved for planning/dialogue; routine execution uses cheap controllers.

Add an explicit new configuration for the expansion. Begin with 4 human inhabitants, a few trees and a small animal population; cap growth and measure before scaling to 8 humans. These are initial engineering choices, not performance promises. Preserve established fixtures and experiments.

Acceptance: legacy regression checks pass, new runtime can save/resume, observer reports the actual active controller, and model-off operation works. Record an actual baseline benchmark before adding ecosystem work.
```

## Milestone B — trees, harvesting and reusable materials

```text
Add native trees with ID, position, stage, health and accounted biomass. Start with young/mature/stump states and a small configurable growth model. Declare sunlight/water/nutrient inputs and environmental carbon or an explicit biomass boundary source. If omitting photosynthesis, label it as an authored ecological source, not molecular chemistry.

Implement inspect_tree, harvest_branch, fell_tree and collect_wood using the project's strict action envelope. Define tool requirements, reach, time, fatigue, capacity, interruption and depletion semantics. A mature tree produces finite logs/branches and a stump/residue; its tracked mass is partitioned, not duplicated. The first version may allow slow gathering of fallen branches without a tool to avoid an impossible bootstrap dependency.

Introduce timber/wood, fiber, stone and wood offcuts as distinct material/item definitions as needed. Existing inert material must not silently become every new species. Each pile/item needs persistent identity or an explicit stack policy. Tools have material composition and durability; breakage creates declared scrap/residue.

Test: two harvesters cannot duplicate the same wood; a failed/interrupted harvest does not create free products; inventories stay within capacity; stump state and resources survive restart; placement respects occupied geometry. Test growth ledger closure and population caps. Show trees, wood piles and actual action history in the viewer.
```

## Milestone C — crafting and construction

```text
Implement reusable data-driven recipe and construction contracts, not a separate handcrafted code path for every future object. Native validators check ingredients, tools, location, work, skill and output placement. Define when inputs are reserved, consumed or returned, including cancellation/restart. Keep quantities deterministic within the declared model.

Initial small chain:
fallen branch + stone + fiber -> crude axe;
tree + usable axe -> logs and residue;
logs + work -> planks and offcuts;
planks -> storage box, trough or small fence segment.

Select exact authored quantities before coding and expose their material balance in tests. Do not model nails/smelting unless their prerequisites exist. Construction reserves space and work, consumes real carried/delivered material, and persists partial progress. A storage box contains real items; it cannot duplicate an inventory. Fence topology and gates must actually restrict animal movement under authoritative collision rules.

Represent procedural knowledge separately from skill and recipe truth. The native recipe registry defines valid world mechanics; an agent receives only permitted known/discovered procedures, not the full registry. Unknown attempts can fail or reveal observable feedback; the engine does not accept model-invented outcomes.

Acceptance: an inhabitant physically completes a short production chain, restart preserves it mid-task, completed storage is usable, blocked output placement is handled, and material/waste accounting closes. Test missing tools, full inventory and competing construction requests.
```

## Milestone D — animals and food ecology

```text
Create native autonomous animals. Begin with a grazer such as a fictional sheep/goat-like species and one egg-laying livestock species. Wild/domestic are individual states/history, not cosmetic labels. Add a simple forage plant or grass resource with explicit regeneration inputs.

Animals have position, health, hunger/thirst, energy/reserve abstraction, age/life stage and bounded senses. Use cheap authored behaviour: seek forage/water, eat/drink, rest, avoid threats, wander, and react to familiar caretakers. Do not run an LLM for every animal tick. Movement, feeding and human-animal interactions obey shared spatial/resource rules.

Implement observe_animal, offer_feed, fill_trough, guide_or_lure and collect_eggs. Feeding consumes actual inventory or trough stock. Familiarity increases only through recorded interactions and affects a bounded authored handling rule. It is not instant obedience, genetic evolution or neural learning. Pens must contain animals physically, not by setting a decorative ownership flag.

Egg production must debit food/body reserves using a declared conversion with waste/residue and an explicit species ledger. Add breeding only after feeding/production works: compatible adults, minimum age/condition, gestation/incubation, birth cost, offspring identity and population bounds. All rates are accelerated simulation rules, not biological estimates. Preserve mass by declared transfers or clearly accounted boundary sources; do not invent a free newborn.

For now use plant food and eggs as new food sources. Model food freshness/storage and a small cook_food action using actual fuel/heat. Do not pretend existing thermal vessels already provide world-wide fire, cooking or smoke. Scope a validated coupling, conserving input/output/water/waste and reconciling energy. Keep dietary quality abstract and explicit.

Acceptance: unfed animals lose condition; caretaking improves outcomes; forage cannot be overdrawn; trough filling conserves water; an actual pen limits movement and an open gate permits exit; collection cannot duplicate eggs. Production, animal state and interactions survive restart. Report any omitted breeding/cooking scope honestly.
```

## Milestone E — planning, learning and caretaking intelligence

```text
Implement a reusable hierarchical goal/task planner over the real action contracts. Model goals include obtain_food, obtain_wood, craft_tool, build_pen, provide_water, tend_animal, inspect_problem, teach_procedure and rest. Allow priorities and plans to change with observations, resources and consequences.

A planner can propose prerequisite sequences such as obtain timber -> make trough -> carry water -> fill trough -> observe animal. Native execution still checks every step. Mark hand-authored decompositions as such. Build plan recovery for depletion, broken tools, blocked routes, absent peers and conflicting urgent needs. Unsupported tasks remain explicit failures, not successful dialogue.

Maintain separate episodic memories, beliefs/hypotheses, procedural knowledge and physically earned skill. A successful procedure can become a source-linked reusable plan; a failure updates confidence or triggers reconsideration. Demonstrating changed future behaviour from recorded experience is required before claiming learning. Memory summaries retain origins; use bounded retrieval suitable for the host.

Evaluate more than eat/drink: harvest/craft, animal thirst, depleted forage, broken tool and blocked access. Separate development configurations from held-out resource/layout changes. Compare utility/authored planner, model-assisted planner, and relevant memory/teaching controls. Measure task success, resources spent, avoidable failures, adaptation after change, model/fallback contributions and latency. Model assistance must show an actual benefit to justify its cost; reporting no benefit is valid.

No new neural training is required here. Keep the failed Phase 9 learner separate. General intelligence and open-ended invention remain unproven even if these tasks pass.
```

## Milestone F — starting knowledge and teaching one person

```text
Implement three explicit, distinct workflows:

1. New world / experiment: choose a reproducible initial-knowledge profile. Examples: basic survival, woodcraft, livestock care or one selected taught specialist. Record its version and each inhabitant's initial knowledge as external initialization. Do not give everyone all procedures by default.
2. Existing world: choose one inhabitant and introduce a book, speak through the operator avatar, or conduct a bounded demonstration. Only valid reading/hearing/observation grants access; preserve source chains through later teaching. Claims remain unverified until tested.
3. Explicit direct knowledge injection: support the user's requested one-person injection as a guided operator intervention if desired. Log recipient, payload, tick, source type operator_injection and branch. It directly inserts an externally supplied knowledge record, not a fabricated read event or skill increase. It cannot import model code, grant tools, create material, reveal other memories or change weights. Keep it distinct from embodied teaching in metrics and UI.

A new chat/agent session must NOT reset the saved world, refill resources, erase personalities or secretly teach inhabitants. Persist state across process/session restarts. If the operator wants a fresh knowledge experiment, require an explicitly named new world or branch through existing commands. New-world initialization and ongoing-world intervention are different sources.

Demonstration: teach one inhabitant a randomized fictional animal-care signal or apparatus rule. Let that inhabitant test it, write/share a procedure, and let a second use it through actual access. An isolated third inhabitant is a control. Ordinary pretrained facts cannot prove teaching origin; prompts cannot reliably erase pretrained knowledge.

Acceptance: only the recipient initially gains the injected record; listeners learn only through permitted interaction; false lessons can fail physically; writing/reading costs exist; teaching does not instantly grant mastery. Save/restart preserves identity and acquired knowledge. Raw book text never grants host/operator privileges.
```

## Milestone G — one integrated living-world demonstration

```text
Use a new documented scenario with 4 inhabitants, a few trees, forage and a small bounded animal group. Start one inhabitant with woodcraft knowledge; teach another animal care through a recorded intervention. Let available goals lead to real wood collection, tool making, a pen/trough, feeding/watering and food collection.

This is an integration scenario, not a guaranteed cinematic sequence. If no one chooses the tasks, report that; do not secretly script successful events. Offer explicit operator-assigned goals as a separate demonstration mode with honest attribution.

Run progressively longer continuous horizons as compute permits, with population/resource limits and checkpoints. Record real simulated and wall time; never sum independent runs into one lifetime or reset resources between continuity segments. Evaluate multiple seeds when affordable. Separate simulation throughput from rendering FPS and inference latency.

Show selected-agent goal, plan steps, failure reason, learned procedure/source, tool durability, animal condition, material stocks and intervention history. Keep operator-only diagnostics separate from cognition input. Add bounded archive/compaction support compatible with new controller/knowledge references before claiming long-term operation.

Acceptance: physical effects and source-linked memory persist together; model-off baseline runs; interventions teach only their intended recipients; save/resume matches the declared replay contract; no duplicated matter/actions or competing writers; every demonstrated outcome has event evidence.
```

## References and how to use them

Read the repository's existing references first; verify current official APIs before adopting dependencies. These sources support components and research context, not an AGI claim:

- Existing project contracts and evidence: https://github.com/vineetsharma96/Alice/tree/main/docs
- Generative Agents: https://arxiv.org/abs/2304.03442 — memory/planning/social-agent context.
- llama.cpp: https://github.com/ggml-org/llama.cpp — local inference; preserve existing working pins until a measured upgrade is justified.
- pybind11: https://github.com/pybind/pybind11 — batched native integration.
- SQLite: https://www.sqlite.org/docs.html — durable transactions, backups and schema evolution.
- Existing PHASE5_THERMAL.md and REFERENCES.md — declared heat equations and scope limits. Extend only with explicit coupling and tests.
- Enhanced POET: https://proceedings.mlr.press/v119/wang20l.html — learning-task research context; do not claim replication.
- Three.js: https://threejs.org/docs/ — extend the current lightweight viewer, preserving locally pinned assets/licenses.

## Required handoff at every completed milestone

```text
Update HANDOFF.md and docs/STATUS.md with:
- Active milestone and completed capabilities.
- Files/modules changed, source/schema compatibility, exact launch/resume commands.
- Checks actually run and observed results; failures and unsupported platforms.
- Seeds/configurations, simulated and wall duration, resource costs and model attribution.
- Any paused/running owned process, database path and safe next step.
- Remaining work and next acceptance check.

Keep HANDOFF.md concise and point to detailed reports. Preserve historical reports and negative experiments. A new coding agent should be able to resume using this file plus the relevant contracts, without rereading the entire repository or assuming checkboxes prove humanlike intelligence.
```
