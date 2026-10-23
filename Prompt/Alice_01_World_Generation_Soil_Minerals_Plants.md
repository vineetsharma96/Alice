# ALICE 01 — World Generation, Soil, Minerals, Plants and Shallow Underground

## Mission

Continue https://github.com/vineetsharma96/Alice. Implement the most detailed environmental expansion yet: a seeded world generator whose terrain, water, soil, mineral deposits, trees, flowers and other plants interact through consistent simplified rules. Add shallow underground exploration and excavation. Deliver working mechanics, integration, persistence, an observable viewer and reproducible evaluation, not a decorative procedural landscape.

This is the first of three separate specifications. The second adds biological life cycles, relationships and inheritance; the third adds microbial decomposition, nutrient cycling, fermentation and later fictional disease. Read their contracts if supplied, but implement this file's scope first. Do not require all three to be implemented simultaneously.

## Non-negotiable workflow

Read AGENTS.md, README, HANDOFF, current STATUS, architecture, contracts and latest implementation reports. Inspect actual C++/Python/viewer ownership and entry points. Establish a baseline and record the Alice commit. The user reports learning, invented communication, weather and emotions implemented; verify these locally instead of assuming completion. Preserve working systems, failed research evidence, native validation, existing saves and current worlds. Do not reset a world when a coding agent changes. Do not replace the project with another engine, create a separate disconnected demo or tag a release without instruction.

Use free local dependencies, isolated environments and current official documentation. Install missing project dependencies where permitted. Profile available hardware; keep a CPU-capable small-world mode and avoid requiring CUDA. Treat 8 GB system RAM and a 4 GB GPU as a useful modest-device target to verify, not a promised budget. Do not run an unlimited-resolution world or load all chunks merely to show a large map.

Proceed stage by stage, executing actual checks. Continue autonomously when a stage passes. Record failures honestly; never lower thresholds after seeing results without declaring a new experiment. Keep a runnable checkpoint and HANDOFF at session boundaries.

## Reality model and scale

Aim for coherent ecological affordances, not molecular Earth simulation. Document every abstraction, unit, rate and boundary source/sink. Use simulation time. State the relationship between world days, weather seasons, plant growth and biological aging. Do not silently compress one system by years while another advances seconds. Explicit accelerated ecological experiments may use declared time scales with consistent interfaces.

Retain existing authoritative physics and material accounting. If Alice currently has 2D movement, prefer explicit layered 2D/2.5D surface and underground cells with authoritative connectors. Only claim volumetric 3D when movement, collision, excavation and support actually use three dimensions. A viewer cutaway alone is not underground simulation.

## G0 — Inventory, contracts and baseline

Locate current terrain, resource nodes, tree states, food regrowth, growth rules, weather forcing, navigation, construction occupancy, inventories, save/replay and observations. Identify old free refills that must be replaced or labeled as legacy rather than silently combined with new fertility rules.

Define versioned contracts for world generation, substrate cells, material transfers, plants and seeds. Suggested identifiers: WorldId, ChunkCoord, LayerId, MaterialId, SpeciesId, PlantId, SeedLotId and DepositId. Use stable IDs; save/load must not depend on dictionary iteration or rendering order.

Define owner and units for elevation, solid volume/mass, loose material, liquid water, organic matter, plant biomass, available N/P/K pools, mineral-bound nutrient pools and export/sink ledgers. Track dry matter separately from water to avoid double-counting wet biomass. Full atmospheric chemistry is optional; any carbon/light source abstraction must be explicit. Do not claim closed elemental conservation if only a subset is tracked.

Gate: baseline and schema decisions recorded; existing-world behavior remains available; transfers have a single authoritative owner.

## G1 — Seeded world generator

Provide New World and headless generation using seed plus a versioned configuration. Generate a complete bounded world first; larger chunked worlds can follow after invariants pass. Configuration should include dimensions, cell scale, layer depth, climate preset, relief, water availability, geological preset, vegetation density, diversity, starting population and guided/research mode. Store effective config and generator version, not just the seed.

Generation pipeline:
1. Validate inputs and compute memory/cell budgets before allocation.
2. Generate coherent elevation, slopes and drainage potential, avoiding white-noise terrain.
3. Generate coarse geological parent material and weathered surface deposits with spatial continuity.
4. Derive initial temperature/moisture regimes from declared forcing. Use current weather/season system afterward; do not duplicate it.
5. Place water bodies and drainage paths consistent with elevation. Define outlets and closed basins explicitly. A simple depression-fill/drainage method is acceptable; report its limits.
6. Generate spatially varying soil profiles from parent material, slope, moisture and ecological preset, using declared heuristics rather than claiming geological history was simulated.
7. Place compatible vegetation, finite initial litter, viable seeds and optional deadwood.
8. Select initial spawn areas based on traversability and declared resources, then validate connectivity.
9. Return generation diagnostics and an immutable generation manifest.

Use stable per-domain/per-chunk random streams derived from seed and coordinates. Generating chunk B before A must not move deposits in A. Specify and test determinism on supported platforms; don't promise cross-platform floating-point identity unless demonstrated.

Required presets: temperate woodland/meadow, dry scrub/rocky ground, and wet riparian ground. Variation must affect soils and life, not just colors. Generation must allow scarce or difficult worlds. Helpful spawn constraints belong in a named preset; no hidden rescue after startup. Previewing a seed must not start or mutate the active world. Regeneration creates a new WorldId and never overwrites the current save by default.

Gate: same seed/config/version yields the same generated-state hash on the supported runtime; generation order is invariant; at least 20 bounded seeds pass structural validity, with ecological feasibility reported separately. Different seeds produce measurable terrain/deposit/plant variation.

## G2 — Geological substrate and soil profiles

Represent a shallow profile using optional organic litter, topsoil, subsoil, weathered parent material and bedrock. These approximate O/A/B/C/R; not every cell requires every horizon. Allow erosion, deposition or excavation to remove/expose layers; never spawn a fresh topsoil layer automatically after digging.

Per horizon/cell track thickness or volume, material composition, bulk density or porosity, water content/capacity, texture fractions, organic matter, available nutrient stocks and compaction. If pH is added, declare a bounded buffering approximation; do not average pH as if it were conserved mass. Texture fractions must remain nonnegative and sum to one. Display geology truth to observers while limiting inhabitant knowledge to what they can inspect.

Initial materials: sand, silt, clay, gravel, stone, weathered rock, organic litter and a small set of ores/minerals such as iron-bearing ore and copper-bearing ore. Rock, ore and refined metal are distinct. Choose a manageable catalog rather than hundreds of unused elements. Give each material hardness, density, excavation cost, particle/storage unit and relevant construction properties. Document fictional values and simplified geology.

Deposits must have finite recoverable stock, host material and grade. Digging an ore-bearing cell creates both recovered ore and accounted gangue/spoil. A rock does not regenerate because it leaves the camera. Weathering is an optional slow transfer from parent material with accounted stock; initial deposit placement is not simulated mineral formation.

Gate: extraction cannot exceed stock; material transfers conserve the tracked quantities within declared tolerances; horizon exposure and extracted inventories survive restart.

## G3 — Soil-water-climate coupling

Rain supplies water from a declared atmospheric boundary. Implement bounded infiltration, storage, percolation, evaporation, plant uptake and surface runoff. Distinguish soil saturation from visible standing water. Texture, organic matter and compaction should have documented influences; avoid making one soil universally best.

Groundwater may initially be a bounded shallow reservoir with explicit exchange. Reservoirs are not infinite water nodes. Include inlet/outlet and vapor loss in the water ledger. Runoff transports only sediment/nutrients that were actually present. Start with stable local equations and positivity-preserving time steps; add substeps where necessary rather than clamp away large accounting errors.

Temperature and daylight influence evapotranspiration and growth using existing weather/calendar state. Document ignored factors such as full fluid dynamics or freeze-thaw if deferred. Never silently implement a second sun or second rainfall generator.

Gate: dry soil wets during rain and can dry afterward; waterlogged and drought conditions affect plants; a no-inflow test cannot create water; results remain reasonably consistent across supported time steps.

## G4 — Plant species and functional diversity

Implement a data-driven catalog with at least three tree strategies, two shrubs, grasses/herbs and six distinguishable flower varieties, provided each adds meaningful traits. Use clearly labeled fictional ecological analogues or sourced real-species parameters. Avoid claiming realistic numerical botany from invented constants.

Suggested diversity: light-demanding fast-growing tree, shade-tolerant slower tree, dry-adapted tree, fruiting shrub, non-fruiting shelter shrub, annual meadow flower, perennial flower, early-season flower, late-season flower, wet-ground flower and dry-ground flower. These are functional design targets, not predetermined vernacular names inhabitants know at birth.

Species data: habitat tolerances, root depth, light/shade response, moisture and nutrient requirements, growth allocation, mature size, seed mass, seed production cost, dormancy, lifespan, reproductive season/window, pollination strategy and dispersal. Colors, petal forms, leaf shapes, bark, seed shapes and size variation should reflect stable species/individual traits, with viewer instancing/LOD where appropriate. Do not make decorative flowers mechanically identical if claiming ecological variety.

Track individual plant biomass/reserves or documented population cohorts for dense vegetation. Light competition may use a canopy approximation. Roots access only reachable soil layers; neighboring plants compete for the same finite stocks. Trees change shade and contribute actual litter. Leaves falling seasonally must debit biomass or a declared seasonal pool.

Gate: resource/climate differences alter relative growth; plants cannot gain unlimited biomass without declared resource inputs; cutting removes wood from real biomass and leaves roots/stumps according to species rules.

## G5 — Seeds, flowering and regeneration

Replace timer-only tree respawn with a visible seed-to-tree lifecycle: viable seed -> dormancy when applicable -> germination -> seedling -> juvenile -> reproductive adult -> senescence/death. Growth responds to water, light, temperature, nutrients, competition and reserves. Germination can fail; not every seed becomes a tree. Coppicing/resprouting can be an explicit species trait with stored reserves rather than a free stump reset.

Track seeds in plant reproductive pools, inventories and soil seed banks with origin, species, viability, age and reserve mass. Create SeedLot records or cohorts rather than allocating millions of objects. Harvesting seeds must reduce the source's seed supply. Seeds used as food cannot also germinate.

Model flowering, pollination compatibility, fertilization/seed set and dispersal as distinct processes. Support wind pollination and a small explicit animal-pollination service; if insects are not individual organisms, label the pollinator population as an ecological abstraction with bounded activity and declared source. Never claim full insect behavior from an invisible pollination probability. Wind, gravity, animal transport and human planting can move seeds. Movement transfers seed stock; it does not duplicate it.

Planting needs a carried seed, reachable prepared location and work. Germination depth matters in a simplified way. Seasonal cues can trigger flowering and dormancy. Realistic variation means mixed success, seedling mortality, seasonal blooms and habitat limits, not only prettier assets.

Gate: a finite seeded stand produces seedlings and some mature descendants under favorable conditions; drought/shade changes recruitment; seed conservation holds; removing all viable seeds prevents unexplained sexual recruitment.

## G6 — Nutrient and litter interfaces

Implement plant nutrient uptake and return organic matter through leaves, dead roots, dead plants and animal waste where those inputs exist. Avoid treating all organic matter as immediately available fertilizer. Define separate organic-bound and plant-available pools.

Before prompt 03 is installed, use one explicit simplified decomposition backend with accounted transfers and versioning. After microbial activation, replace that backend; never run both. Use stable substrate/consumer/transfer events so the third expansion can subscribe without rewriting plants. Track N/P/K if implemented, and a carbon/dry-matter ledger at the chosen resolution. Nutrient cycling redistributes finite stocks; external inputs such as weathering or atmospheric deposition must be explicit.

Gate: growing biomass debits nutrients; dead material enters the appropriate pool; no immediate full nutrient refund while the plant is alive.

## G7 — Shallow underground, excavation and discovery

Add a bounded shallow layer system, for example several explicit strata with configurable depth. Preserve coordinates, occupancy and surface connections. Initially permit pits, trenches, exposed banks and short supported tunnels; deep mines and entire planetary caves are future scope.

Authoritative actions: inspect exposed ground, sample soil, dig, quarry, collect spoil, backfill, prospect exposed rock, build/remove supports and move between connected elevations/layers. Define tool prerequisites, work duration, energy costs, inventory/hauling limits and interruptions. Multiple inhabitants cannot extract the same stock simultaneously.

Unknown underground cells remain unknown to inhabitants. Surface clues may give uncertain estimates; exact ore maps require exposure/sampling. Remembered deposits can be depleted and must be revalidated. Observer x-ray mode must not leak into planning.

Connectivity must forbid teleporting through rock or descending through an unbuilt opening. Excavation changes navigation and affects nearby foundations and roots. Use a declared structural support approximation: spans/depth/material/supports determine instability. Warn through observable cracks or debris if supported by mechanics. A collapse transfers existing material into voids and can block paths; it must not duplicate rock or delete trapped entities silently. Model simple infiltration/flooding where wet ground is opened, or explicitly gate water-adjacent excavation until it exists.

Use one action/geometry design that cannot remove a cell still supporting a world object without an explicit outcome. Backfilling consumes transported spoil; it is not a terrain reset. Emergency recovery is an operator intervention recorded separately, never an autonomous survival success.

Gate: shallow extraction and hauling complete, stock depletion is respected, support failure has an accounted outcome, water and entrances remain consistent and occupied cells save/resume correctly.

## G8 — Knowledge, emotion and autonomous work

Expose perceptible texture, moisture, plant morphology, flowering, visible ore and outcomes through existing observation contracts. Exact soil chemistry is observer knowledge unless the inhabitant has an implemented test or learned estimate. Existing learned signals may refer to experienced plants/materials; do not auto-populate a universal botanical or mineral dictionary.

Enable learnable activities: collect seeds, compare planting sites, water seedlings, avoid known unstable ground, revisit a discovered deposit and adjust after depletion. Starting recipes remain authored/seeded knowledge unless acquired by actual learning or documented teaching. A crafting recipe existing in code does not imply every inhabitant knows it.

Feed injuries, failed harvests, shelter, useful discoveries and safe recovery into existing emotional appraisal. Do not force love of flowers or fear of mines into every person. Emotions cannot reveal unobserved geology or change physical outcomes. Keep model contributions and fallback actions distinct.

Gate: at least one agent acquires and reuses source-location or planting-outcome knowledge without global knowledge updates, including recovery from stale information.

## G9 — Viewer, persistence and performance

Integrate New World, seed/config preview and load/resume in the actual application. Provide terrain/vegetation view, seasons and growth stages, optional observer soil/moisture/nutrient layers, plant/seed inspector, geology cutaway and visible excavation. Distinguish unknown inhabitant knowledge from observer truth. Explain failed germination and rejected digging actions through diagnostics. Generated world assets must not be polished at the expense of authoritative mechanics.

Persist generator/version/config, chunk modifications, water/soil stocks, plants, seeds, deposits, jobs, actor positions and RNG state needed by existing replay semantics. Do not regenerate harvested deposits when chunks reload. Unloaded regions must advance with a declared conservative method or remain explicitly frozen; do not secretly refill them on reentry. Protect old saves; optional migration must preserve original backups. New systems cannot silently alter an existing seed's terrain.

Profile headless and viewer costs separately. Report generated dimensions, active chunks, entity/cohort counts, peak RAM/VRAM and throughput. Start with bounded dense storage where simpler, then optimize based on evidence. Reconcile aggregate and detailed representations without duplicate stocks. A resource limit should pause/stop explicitly with a checkpoint, not erase living entities or material.

## G10 — Validation and deliverables

Write the evaluation protocol before tuning. Use development and held-out seed sets. Required checks: deterministic generation; generation order invariance; invalid configs; finite deposit extraction under contention; water and nutrient ledgers; seasonal seed/flower progression; seed-bank exhaustion; drought and waterlogging; plant shade competition; mining connectivity/support; save/replay and chunk reload parity; observer-state leakage; old-save protection. Run appropriate existing regressions once changes warrant them.

Integrated demonstration: generate woodland/meadow -> inhabitants discover seeds and a shallow deposit -> plant at two contrasting sites -> growth differs for explained reasons -> harvest finite materials -> excavate and haul -> save/restart -> resources, learned locations and unfinished work persist. The demo need not guarantee survival in every scarce world; report extinction and failed tasks honestly.

Provide runnable code, versioned species/material/world configs, commands, raw per-run results, an operations guide, dependency/license attribution and concise status/handoff. Suggested stage reports may be consolidated to avoid documentation sprawl. Mark mechanics implemented, experimentally validated, failed or deferred separately. Do not claim real-world scientific prediction or autonomous technological invention from authored recipes.

## Scientific/reference starting points

- Alice implementation: https://github.com/vineetsharma96/Alice
- USDA NRCS soil horizons: https://www.nrcs.usda.gov/resources/education-and-teaching-materials/a-soil-profile
- Oregon State Extension plant reproductive structures: https://extension.oregonstate.edu/catalog/em-9900-reproductive-plant-parts
- OpenStax ecosystem matter/energy cycles: https://openstax.org/books/biology-2e/pages/46-3-biogeochemical-cycles

Read these and current official numerical/procedural-generation documentation as needed. They motivate qualitative structure; they do not validate invented simulation parameters. Record which assumptions are sourced and which are engineering choices. Begin G0 now and implement sequentially rather than returning only a plan.
