# Milestone B — trees, harvesting and reusable materials

Milestone B adds the first living-world ecosystem resources without changing the authority boundary: C++ owns tree state, geometry, action validation, transfers and consequences; Python exposes the state and persists the native checkpoint.

## Authored scope

- Three deterministic trees are created in each new native world: one young tree with 2 kg tracked biomass and two mature trees with 8 kg each.
- Tree stages are `young`, `mature` and `stump`. A tree's `mass_ug` equals its `biomass_ug`; health is a bounded authored condition indicator.
- Young trees receive the configured `tree_growth_kg_s` boundary source until reaching 8 kg, then become mature. Growth is not molecular photosynthesis and is explicitly an ecological source in the ledger.
- `inspect_tree` reports stage, health, radius and tracked biomass.
- `harvest_branch` removes a requested positive mass from a non-stump tree and creates 90% `wood` plus 10% `fiber`.
- `fell_tree` is a deliberately authored bootstrap action requiring at least five seconds and no tool. It removes 90% of harvestable biomass as 80% `wood` plus 10% `fiber`, leaving 10% as a `stump`.
- `collect_wood` moves material from an existing `wood`, `fiber`, `wood_offcut` or `stone` pile into the actor inventory, subject to reach, visibility and the existing 2 kg capacity.

Failed, interrupted, stale or occupied-placement actions do not create free products. Completion rechecks tree state and available geometry, so competing harvesters cannot duplicate biomass.

## Compatibility

Tree state is serialized in the `UW7` native checkpoint. The durable coordinator uses SQLite `user_version=8` and checkpoint schema 7. UW6/DB7 worlds are not migrated or reinterpreted; they fail closed with an explicit compatibility error and must be resumed with their original pinned runtime.

## Verification

The focused native suite covers competing harvesters, failed placement, capacity, stump/depletion, growth accounting, checkpoint determinism and old native format rejection. The Python suite covers tree observation/action flow, material conservation, growth restart, config validation and durable DB/checkpoint identities.

This milestone does not implement tools, recipes, construction, animals, cooking, breeding or general hierarchical planning. Those remain later milestones.
