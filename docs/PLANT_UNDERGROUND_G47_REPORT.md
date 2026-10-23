# Alice 01 G4-G7 sidecar report

## Scope

`underworld/plant_underground_g47.py` is an additive, headless sidecar. It consumes a validated G0-G3 manifest from `world_generation_g01.py`, copies the source cells, and does not modify G01, `storage.py`, native code, existing worlds, lifecycle/micro modules, viewer code, or schedulers.

## Implemented

- **G4:** data-driven catalog with three tree strategies, two shrubs, grasses/herbs, and six flower varieties. Traits include habitat moisture, shade response, roots, nutrient need, biomass ceiling, allocation, lifespan, reproductive window, pollination and dispersal strategy, seed cost, and morphology markers.
- **G5:** individual plants plus finite seed lots. Plants track stage, age, dry biomass, reserves, flowering, pollination, seed supply, and coppice/death behavior. Germination is probabilistic but deterministic from the world seed and lot identity; failed recruitment consumes a seed. Harvesting and planting transfer finite seed counts.
- **G6 interface:** growth records finite nutrient demand and declares the simplified site-pool abstraction. Nutrient uptake is logged separately from biomass and is not immediately refunded while a plant remains alive. A future microbial backend can subscribe to `plant_ledgers.nutrients` and dead/cutting records.
- **G7:** shallow copied strata, finite excavation, spoil and loose-material ledgers, supports, explicit adjacency connectors, occupancy, and route-checked underground movement/hauling. There is no teleportation or stock duplication. Backfill/haul actions consume carried loose material.
- **Persistence:** canonical JSON save/resume, checksummed state, copy-on-write revisions, idempotent operation IDs, and deterministic replay.

## Units and boundaries

Biomass, reserve, seed reserve, spoil, and carried materials are dry kilograms. Excavated volume is cubic metres and mass uses the G01 material density catalog. Plant time is one sidecar day per `days` argument; the caller chooses when to advance it, so no second weather scheduler is introduced. Habitat and pollinator values are bounded engineering abstractions, not real-world botanical predictions. Dense vegetation uses individual records in this bounded slice; larger populations can use cohorts later.

## Checks

Focused tests cover catalog variation, finite growth and cutting, seed accounting, contrasting habitat/light conditions, germination failure path, excavation/support/connectivity/occupancy, no-teleport movement, JSON restart, and replay. Project-wide lint and pytest are run at handoff; any unrelated pre-existing failures are reported separately.

## Deferred by boundary

No viewer/native scheduler integration, agent knowledge integration, deep mining, collapse solver, full water infiltration in opened voids, animal individuals, or microbial decomposition backend is included in G4-G7.
