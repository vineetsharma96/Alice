# Proposed contracts v1

**Current Phase 4 contract:** [PHASE4_TEACHING.md](PHASE4_TEACHING.md), including exact intervention fields, read/speech provenance, branch identity, supported hearing law, native UW3 / SQLite schema 4 and compatibility limits. These implemented contracts take precedence over the older Phase 0 proposals below.

Phase 0 proposals below are retained as the long-term interface direction. [PHASE3_COGNITION.md](PHASE3_COGNITION.md) specifies current identity/episode/plan/provider contracts, separate mental checksums, UW2 native state and SQLite schema 3. [PHASE2_AGENCY.md](PHASE2_AGENCY.md) specifies body/action/sense/report contracts and utility state. [PHASE1_MECHANICS.md](PHASE1_MECHANICS.md) preserves mechanics decisions. Thermodynamics and interventions remain unimplemented. The legacy `initial_scene` record is a Phase 0 probe, not a runtime WorldSnapshot or cognition input. Current exact behavior takes precedence over future proposals below.

## Shared rules

JSON wire format, UTF-8, `schema_version: 1` on every message. Reject unknown major versions and unknown request fields. IDs are opaque nonempty strings up to 128 ASCII characters (`[A-Za-z0-9_-]`); run IDs are UUID strings. Entity IDs are unique and never reused per run. Cross-run references carry run ID. Seeds and uint64 counters use decimal strings on the future JSON wire to avoid JavaScript precision loss; the Phase 0 zero tick/version fields are numeric bootstrap constants. Internal counters are uint64. Timestamps are integer ticks plus `dt_s`; wall-clock times are UTC RFC3339 metadata and cannot drive physics. Metres, seconds, kilograms, kelvin and joules; needs/confidence are dimensionless [0,1]. All numerics finite. Coordinates inside `[0,width_m] x [0,height_m]`; collision radius must fit within bounds at execution.

Limit serialized request to 16 KiB, text to 4096 UTF-8 bytes, targets to 8, parameters to an allowlisted flat schema per action. Reject invalid encoding, duplicate JSON keys, NaN/Infinity, wrong types (including booleans as numbers), overflows and extra nesting before execution. Python and C++ decoders must use the same fixture tests when implemented. Payload budgets also constrain observations/memory retrieval; truncate or paginate with explicit omission metadata, never silently lose provenance.

| Contract | Required fields and semantics |
| --- | --- |
| WorldSnapshot | `schema_version`, `run_id`, `branch_id`, `tick`, `observation_version`, `dt_s`, `simulated_time_s`, `config_hash`, `laws_version`, `world_bounds_m`, `entities[]`, `last_event_seq`. Privileged read-only operator projection. Entities carry stable ID, kind, position, public state; private memories are a separate authorized inspection endpoint. A checkpoint additionally carries full internal RNG, pending actions, scheduler and entity-ID allocator state; a viewer snapshot is insufficient for restore. |
| Observation | `schema_version`, `run_id`, `agent_id`, `tick`, `observation_version`, `own_state`, `visible_entities[]`, `audible_reports[]`, `recent_action_results[]`, `omissions`. Created through geometry/range checks; own inventory/needs permitted, hidden entities and others' memories excluded. Reports have speaker, event/provenance reference and confidence, distinct from engine facts. Version binds to one published committed world revision. |
| ActionRequest | `schema_version`, `run_id`, `request_id`, `agent_id`, `observation_version`, `action_type`, `target_ids[]`, `parameters`, `requested_duration_s`. Allowed planned types: move, gather, drink, eat, rest, inspect, speak; read added with books. Duration [0.1,60] seconds, quantized upward to fixed steps; effect/cost timing per type must be specified before use. move: x_m/y_m finite in bounds; eat/drink/gather: mass_kg in (0,10]; speak: text <=4096 bytes; rest/inspect: no arbitrary parameters. IDs do not imply authority. |
| ActionResult | `schema_version`, `run_id`, `request_id`, `agent_id`, `status`, `error_code`, `reason`, `started_tick`, `completed_tick`, `observation_version`, `event_refs[]`, `observable_effects`. Status rejected/accepted/running/completed/failed. Rejected actions have no world effects or resource costs. Accepted is not completed; interrupt/failure costs must follow authored rules. Effects are filtered to requester; never reveal hidden targets. |
| AgentMemory | `schema_version`, `memory_id`, `run_id`, `agent_id`, `created_tick`, `kind`, `text`, `source_event_refs[]`, `source_memory_refs[]`, `confidence`, `access_scope`. Kinds episode/report/belief/summary/plan; `access_scope=private` default. Facts are stored separately in core. Summaries preserve original episodes and reference evidence. Speaker belief is not an authoritative result. Retrieval filters owner/run before ranking and token budgeting. No model weight update is implied. |
| MaterialDefinition | `schema_version`, `material_id`, `laws_version`, `label`, `species_mass_fractions`, `specific_heat_J_kg_K`, `phase`, `valid_temperature_range_K`, `latent_heat_J_kg`, `reaction_refs[]`. Nonnegative mass fractions sum to 1 within a documented tolerance. Positive heat capacity. Reactions separately specify stoichiometry, energy ledger and validity. Phase 0 food/water/inert labels have quantities only; no thermal properties or reactions are claimed. |
| Intervention | `schema_version`, `intervention_id`, `run_id`, `branch_id`, `operator_id`, `submitted_at_utc`, `delivery_tick`, `mechanism`, `recipient_ids[]`, `payload`, `resource_ledger_deltas`, `parent_checkpoint_id`. Mechanisms book/avatar_message/object/broadcast. Operator-authenticated channel only; exact delivery/visibility is modeled. Payload remains data. Creation logs mass/energy sources and delivery outcomes. Law changes require a new branch/laws version. Closed mode rejects guided teaching mutations; initialization and administrative pause/checkpoint are distinct control events. |

## Rejection and execution semantics

Validate schema, run/agent authorization, exact current observation version, action allowlist and numeric limits before querying targets. Then validate visibility, reach, ownership, available quantities and target state at execution and again when delayed effects occur. No narrative changes truth. Do not expose whether a hidden or nonexistent target exists: return `TARGET_UNAVAILABLE` for either.

Error codes: `UNSUPPORTED_SCHEMA`, `INVALID_ARGUMENT`, `PAYLOAD_TOO_LARGE`, `UNAUTHORIZED`, `STALE_OBSERVATION`, `UNKNOWN_ACTION`, `TARGET_UNAVAILABLE`, `OUT_OF_REACH`, `OWNERSHIP_DENIED`, `INSUFFICIENT_RESOURCE`, `BUSY`, `MODE_FORBIDS_INTERVENTION`, `INTERNAL_ERROR`. Reasons are bounded observable text, not stack traces. Retry stale requests only after receiving a new observation; provider timeout is recorded scheduler fallback, not a successful action. Repeating a request ID with identical payload returns its existing result; conflicting payload is invalid. Deduplication is scoped to run/agent and must persist across restart. None of these runtime guarantees are tested in Phase 0.

## Milestone B tree/material actions

The UW7 native contract adds these validated action types; all use the existing `schema_version`, run/agent identity, observation version, target list and requested duration envelope:

| Action | Targets | Parameters | Authored effect |
| --- | --- | --- | --- |
| `inspect_tree` | one visible tree | `{}` | reports stage, health, radius and tracked biomass; no material change |
| `harvest_branch` | one visible non-stump tree | `{mass_kg}` with optional explicit `{x_m,y_m}` pile anchor | removes finite biomass and creates 90% wood / 10% fiber after terminal validation |
| `fell_tree` | one visible non-stump tree | `{}` with optional explicit `{x_m,y_m}` pile anchor | five-second no-tool bootstrap; removes 90% biomass as 80% wood / 10% fiber and leaves a 10% stump |
| `collect_wood` | one visible wood/fiber/wood-offcut/stone pile | `{material,mass_kg}` | transfers an existing pile quantity into carried inventory under capacity/reach checks |

Tree-derived material placement is checked against occupied geometry. A failed or interrupted action does not create products; competing terminal completions revalidate remaining biomass. The native checkpoint is `UW7`; the durable coordinator is SQLite user_version 8 with checkpoint schema 7. See [PHASE_B_TREES.md](PHASE_B_TREES.md) for limits and exact ledgers.

## Current Milestone C action contract (UW8 / DB9)

The B table above is historical. C `fell_tree` requires `{tool_id}` and optional `{x_m,y_m}`. `craft` takes no target and `{recipe_id}` plus `{tool_id}` when required. `begin_construction` takes no target and `{recipe_id,x_m,y_m}`. `work_construction`, `cancel_construction` and `toggle_gate` take one target and empty parameters. `store_item`, `take_item` and `fill_trough` take one target and `{material,mass_kg}`. `cancel_action` takes no target/parameters and terminates the actor's current pending request as failed/CANCELLED. Every action uses the existing strict schema-1 envelope, canonical observation tick and bounded `requested_duration`.

Native recipes specify ingredients, tool, initial skill requirement, work and products. Construction transfers ingredients to a persistent site; fixed-step work is saved every tick. Native tool composition and owned-tool capacity, contents capacities, output geometry, cancellation, terminal revalidation and exact quantities are specified in [PHASE_C_CRAFTING.md](PHASE_C_CRAFTING.md). Added reasons include UNKNOWN_RECIPE, INSUFFICIENT_WORK, INSUFFICIENT_SKILL, MISSING_TOOL, TARGET_BUSY, ENTITY_LIMIT and NO_PENDING_ACTION. Existing validation order still determines which legitimate rejection is reported. Visibility may reject before an occupied-placement check.

Recipes are not automatically cognition input. Agent own state includes owned tools, total carried mass and an authored successful-work counter; the privileged recipe registry requires the operator channel. No Phase 9 learner is used. Native UW8 and SQLite user_version 9/checkpoint schema 8 reject older source/format identities rather than modifying old saves.

## Milestone D actions (UW9 / DB10 / checkpoint 9)

All use the existing strict schema-1 action envelope. One target and empty parameters: observe_animal (>=0.2 s), guide_or_lure (>=1 s). One target and {mass_kg}: gather_plant (>=1 s). One target and {material,mass_kg}: offer_feed and collect_eggs (>=1 s); collection requires material eggs. Existing fill_trough retains its real water-only transfer. Care reach is 1.5 m; observation is bounded to 4 m and line of sight. Prerequisites are checked again on terminal completion. New reasons include DEAD_TARGET and UNFAMILIAR; native validation order is preserved.

Eating retains the historical {mass_kg} food default and adds optional material plant_food or eggs. Those two materials can be stored/taken through boxes. Their remaining lifetimes mix by minimum, halve aging rate in boxes, and transfer to non-edible retained residue on expiry. Historical abstract food remains nonperishable. Source forage is gathered by gather_plant, not the generic gather contract. All animal reserve, egg, waste, life/familiarity/guide state and food freshness persist. No breeding or cook_food contract is exposed.
# Milestone E controller contract — 21 October 2026

Native UW9/DB10/checkpoint 9 actions and validation remain unchanged. Optional
hierarchical tasks use stabilization/4 with source pins spanning stabilization,
planning and planning_model. A pending request has one owner (survival or task),
is reconciled against the native decision journal and receives native completion
before procedure credit or cancellation. Whole-goal satisfaction and completed
primitive actions are distinct. Externally/already satisfied goals get no new
executor procedure credit. Only own source-backed episodes can be reused.
Old controller worlds require the prior full runtime, not implicit migration.
Full contracts and outcome gates: [PHASE_E_PLANNING](PHASE_E_PLANNING.md),
[evaluation amendment](PHASE_E_EVALUATION_AMENDMENT_1.md).

## Milestone F external records

External initialization and operator injection are private unverified episodes,
separate from native read/hearing events and physical practice. One-step lesson
tests reserve own provenance before submitting a native action; terminal memory
and the test link commit together. Native laws/skill remain authoritative.
See [F report](LIVING_WORLD_F_REPORT.md) and [operations](KNOWLEDGE_OPERATIONS.md).
The bounded authored apparatus demo is not autonomous teaching or general learning.
