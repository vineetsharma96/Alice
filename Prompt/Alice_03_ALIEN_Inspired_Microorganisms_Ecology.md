# ALICE 03 — ALIEN-Inspired Microorganisms, Nutrient Cycling, Fermentation and Disease

## Mission

Continue https://github.com/vineetsharma96/Alice. Add a persistent microbial ecology connected to soil, plants, water, food, bodies and containers. Implement decomposition and nutrient cycling first, fermentation next and fictional disease only after the ecological foundation is validated. Use https://github.com/chrxh/alien as an artificial-life engineering reference, not a claim that ALIEN's digital organisms are realistic microorganisms.

This is prompt 03 of three. Prompt 01 owns geological/soil/plant stocks; prompt 02 owns organism lifecycles, relationships and host births/deaths. Reuse their actual contracts when present. Establish adapter fixtures where absent without claiming whole-world integration. Preserve all working Alice systems, saves and historical experimental evidence.

## M0 — Inspect ALIEN and Alice before design

Read AGENTS.md, README, HANDOFF, current status/contracts and actual implementation. Verify weather, thermal processing, food spoilage, emotion and biological systems rather than assuming they exist. Record Alice and ALIEN source revisions.

Inspect ALIEN's energy accounting, organism/genome representation, reproduction/mutation, environment coupling and GPU execution. Verify current license, dependencies and hardware requirements. Record source files and which ideas are applicable. Current documentation describes a particle-based artificial-life environment; it does not establish real microbial metabolism or disease. Do not reuse code without license review and required attribution.

Choose one of three approaches with evidence: a native CPU population model inspired by selected ALIEN mechanisms, an optional bounded detailed experimental microcosm, or direct integration only if coupling and deployment are demonstrably worthwhile. Prefer native CPU-first populations for the default Alice world. Do not require running a second full GPU universe to decay a log. No paid cloud service or mandatory internet after setup.

Gate: upstream audit, model choice, data ownership and a predeclared evaluation protocol. Do not claim ALIEN was integrated if only conceptual mechanisms were adapted.

## M1 — Habitats, populations and tracked matter

Represent microbial habitats in soil horizons, litter/deadwood, water, carried food, storage/fermentation vessels and appropriate host surfaces/interiors if modeled. Each has finite substrate, water, thermal conditions, oxygen or a declared oxygen-availability approximation and bounded populations/biomass.

Use aggregate populations/cohorts per functional strain rather than one object per bacterium. Initial guilds may include aerobic decomposers, low-oxygen decomposers, yeast-like fermenters and acid-producing fermenters. Fungal decomposers may be a later guild with explicit spatial limits; do not label every microorganism a bacterium. Initial guilds are designed ecological functions, not evidence their metabolisms evolved from nothing.

Population records include strain/lineage ID, habitat, biomass/count relationship, reserves, activity/dormancy and trait version. Habitat records include accessible substrate pools, plant-available nutrient pools via shared soil ownership, environmental bounds and transfer events. Keep viable population, dead microbial biomass, toxins/byproducts and substrate separate.

Use explicit biomass and water units. If count is estimated from biomass, declare the conversion and do not independently multiply both. Organic carbon/N/P pools are preferable if existing contracts support them; otherwise state the smaller tracked mass model honestly. Energy comes from declared substrates or external inputs and leaves as waste heat/exports. Do not treat heat as recyclable chemical food.

Gate: empty sterile habitats cannot produce biomass spontaneously without a declared inoculum/source; no negative substrates; habitat transfers conserve the modeled quantities.

## M2 — Growth, maintenance, death and reproduction

Implement substrate-limited uptake, maintenance cost, bounded conversion yields, population increase, mortality and optional dormancy. Temperature, moisture, oxygen availability and competition influence rates. Use numerical substeps or analytic bounded updates rather than unstable exponential growth followed by resource-deleting clamps.

Asexual division needs accumulated biomass/reserves and resource availability, not merely a timer. Sexual reproduction and male/female categories are not required for these microorganisms. Expose lineage events compatibly with prompt 02 without storing every historical division indefinitely. Every death transfers biomass to a declared pool; death does not erase matter.

Rate equations should use simulation time and have controlled behavior under different supported step sizes. Populations may go extinct. Avoid magical reseeding; inocula originate from initial world generation, recorded transfers, surviving reservoirs or explicit operator intervention.

Gate: growth depletes substrate, maintenance matters, depleted populations decline/dormant as modeled and matched time-step trials remain within declared tolerance.

## M3 — Decomposition and nutrient return

Consume accessible litter, roots, deadwood, animal waste, corpses and spoiled food from actual world stocks. Different substrate classes can have distinct accessibility/rates; a whole log should not disappear as quickly as loose leaves simply because both are 'organic'. Outputs include microbial biomass, transformed organic material, mineralized nutrients and declared gaseous/dissolved/waste products.

Partition existing N/P/K or other tracked elements according to the substrate's actual composition. Available nutrients cannot exceed released stocks. Uptake into microbial biomass can temporarily immobilize nutrients; it is not always an immediate fertility bonus. All tracked element outputs must reconcile with inputs and explicitly modeled boundary exchanges.

Deactivate the old timer/simplified decomposition backend for the same substrates when this backend owns them. Never let microbes and a legacy decay callback each consume the same leaf and release nutrients twice. Corpses are physical material and historical identity records are separate.

Gate: plant -> litter -> microbial biomass/products -> available soil nutrients -> new plant uptake is an accountable loop. Removing decomposers changes the loop without breaking unrelated physics. Report any generic nutrient abstraction as such.

## M4 — Dispersal, competition and ecological variation

Move microbes through finite inoculum transfers: water movement, soil transport, contact, carried food and declared limited environmental dispersal. A transfer subtracts from its source or uses an explicitly accounted shedding process. Sealed containers block routes according to actual seal rules, not UI appearance.

Competition follows shared substrates and environmental tolerances. Add bounded strain-level mutation only after baseline ecology works. Possible traits include uptake affinity, maintenance cost and temperature tolerance, with documented tradeoffs. Mutation cannot create arbitrary new metabolic chemistry or conjure a disease function from nowhere. Avoid optimizing directly for a predetermined 'advanced microbe' label.

Test inherited adaptation against unchanged ancestral controls in multiple environments; population turnover or a changing graph alone does not prove evolution. Store representative lineage history and aggregate statistics within explicit retention limits.

Gate: spread requires connectivity and a source; resource competition affects composition; any claimed adaptation is heritable and survives an appropriate common-condition comparison.

## M5 — Food spoilage and fermentation

Replace duplicate spoilage timers with one declared owner or a documented coupling. Track food substrate, microbial activity and transformation products separately from edible quantity and nutritional value. Spoilage, fermentation and pathogenicity are distinct; fermentation is not automatically safe and visible mold is not the only possible hazard.

Implement a fictional substrate plus yeast-like and acid-producing cultures in real containers. Filling, inoculating, mixing, covering, heating, cooling and transferring require available materials, time and existing validated actions. Reaction yields and gases/products follow declared simplified stoichiometry/mass partitions; do not claim a molecular model if using coarse pools. Oxygen conditions affect the modeled process but fermentation is not simply interchangeable with anaerobic respiration.

Containers have finite capacity and defined seal/air exchange; gas accumulation and pressure need either actual mechanics or an explicit vented-vessel constraint. Do not let an unmodeled sealed vessel store unlimited gas. Heating can reduce populations according to a declared thermal model; do not apply an unconditional 'heated equals sterile' flag. Discarded or spilled contents enter the environment as actual transfers.

Inhabitants discover transformations only through perceivable changes, tools and experience. Observer microbe counts are not private knowledge. Provide learnable smell/appearance cues with uncertainty, not perfect omniscient detection of safety. Procedures learned from experiments/books remain source-traceable. Do not provide real-world food-safety or medical assurances from this fictional model.

Gate: controlled paired containers produce different documented outcomes from culture/environment differences, with no extra calories or product mass appearing from a timer. Save/resume mid-process preserves trajectories within declared tolerance.

## M6 — Optional detailed ALIEN-inspired microcosm

Only after population ecology works, provide an isolated microscope/experimental view with a bounded set of digital cells or agent-like microbes. ALIEN-inspired mechanisms may include local energy exchange, simple sensory responses, heredity and mutation. Mark these as authored rules with potential emergent outcomes.

Define whether this is visualization of aggregate state, an independent experiment, or an authoritative detailed backend. Never show decorative particles as if each is a real simulated organism. If exchanging with world habitats, use conservative coarse/detailed conversion and explicit coupling intervals. No double evolution of the same stock, no population multiplied when zooming in and no material duplicated on zoom-out.

GPU acceleration is optional and follows profiling; CPU mode remains usable. Bound memory and cells. A resource limit pauses/checkpoints or switches only through a validated aggregation path. It never silently deletes organisms.

Gate: representation round-trips preserve tracked stocks; visual zoom does not change ecological outcomes; detailed experiments are labeled separately from established ecology.

## M7 — Fictional disease, only after ecology gates pass

Implement abstract fictional pathogen types, not real pathogen engineering or laboratory protocols. Begin with one route such as contaminated water/food; add contact or respiratory spread separately with explicit environmental requirements. Infection requires exposure and a modeled dose-response probability. Symptoms are consequences, not proof the agent knows the cause.

Separate environmental pathogen population, exposure, infection state, latent/incubation intervals, symptoms, infectious shedding, recovery and any bounded immunity. Each host has its own state. Do not make every exposure guarantee infection or give all hosts instant knowledge of every case. Host effects alter actual health/needs and capability within native validation. Reconcile pathogen resources with the chosen abstraction; if within-host multiplication is coarse, document its limits.

Support feasible responses: cleaner water routes, observed cleanliness practices, avoiding spoiled supplies, rest, care and reducing contacts through actual actions. Do not invent effective medicine without implemented recipes/mechanisms. No realistic claim of clinical prediction or safety. Disease should remain disabled in ordinary worlds until ecological and host-model gates pass; enable only with recorded configuration. Explicit contaminated-start experiments must be distinguished from naturally established reservoirs.

Integrate emotion through perceived illness, uncertainty, trusted help and loss. Do not set universal panic or automatic hostility toward sick inhabitants. Knowledge of transmission develops through evidence or declared teaching. Operator dashboards can see ground truth but agents cannot.

Gate: no source/no exposure controls remain uninfected under the declared model; route blocking reduces modeled exposure; save/resume preserves incubation; disease burden and recovery respect resources and declared parameters. Include ambiguous symptoms and false beliefs, not only perfect diagnoses.

## M8 — World integration, operations and validation

Use prompt 01 soil/plant/weather events and prompt 02 body/death/waste events as the authoritative inputs. Publish accountable microbe outputs through shared transfers. Persist habitat stocks, strain state, lineages, pending updates, host states and RNG as required. Replay must not multiply nutrients, infections or populations twice. Preserve old saves with explicit disabled/default/migration behavior and original backups.

Observer tools: microbial activity, substrate availability, soil nutrient changes, decomposition progress, vessel state, lineage summaries and, when enabled, infection/exposure timelines. Separate observable inhabitant cues from observer truth and speculative causal diagnosis. Browser-verify actual viewer changes or explicitly report visual limitations.

Set memory/population budgets and batch inactive habitats without hiding ecological effects. Profile headless throughput and viewer overhead separately. Initial target is a small world with hundreds of habitats/aggregate populations, tuned to actual hardware rather than a promise of millions of cells.

Predeclare development/held-out scenarios and numerical thresholds. Test at least several held-out seeds where practical: sterile/no-inoculum controls; substrate exhaustion; cold/dry versus favorable habitat; oxygen route variation; litter nutrient release; plant nutrient uptake; sealed/unsealed transfers; legacy-backend exclusion; fermentation controls; mutation-frozen ancestors; coarse/detailed transfer if added; disease-disabled/no-exposure controls; checkpoint/replay and longer ecological cycles. Keep raw per-run data and report mass residuals, biomass, substrates, nutrients, plant productivity, variability, extinction and computation cost.

Deliver code integrated into actual runtime, appropriate regressions, reproducible scenarios, exact commands/results, configs, upstream attribution/license notices, concise reports and updated HANDOFF/STATUS. Mark ALIEN-inspired adaptation separately from direct code reuse. Mark implemented, passed, failed and deferred capabilities individually. Begin M0-M3 first, validate, then advance in order. Never skip to disease because its animations are easier to demonstrate.

## Reference starting points

- ALIEN source and current documentation: https://github.com/chrxh/alien
- Ecosystem matter/energy cycles: https://openstax.org/books/biology-2e/pages/46-3-biogeochemical-cycles
- Fermentation concepts: https://openstax.org/books/microbiology/pages/8-4-fermentation
- Resource-limited population growth: https://openstax.org/books/biology-2e/pages/45-3-environmental-limits-to-population-growth

These motivate concepts, not default numerical constants. Verify content and label engineering approximations. The goal is accountable interconnected artificial ecology, not a claim that realistic microbiology emerges automatically from ALIEN.
