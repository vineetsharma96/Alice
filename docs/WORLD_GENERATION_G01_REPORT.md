# World generation G0–G3 bounded slice

Implemented in `underworld/world_generation_g01.py` as an additive pure Python
module. It does not import or modify `underworld.storage`, the native C++ world,
existing saves, or the current scheduler. A caller can generate a separate JSON
manifest, inspect it, apply copy-on-write research operations, and resume it.

## Contracts and scope

- Contract: `alice.world.g01/v1`; generator: `g01.1`.
- Stable identifiers include `world_id`, coordinate cells, horizon `layer_id`,
  `deposit_id`, and `seed_lot_id`.
- Config is stored in the manifest. Dimensions are bounded to at most 4096 cells;
  each cell has optional O/A/B/C/R-like horizons, finite material stocks and
  bounded moisture/elevation/slope values.
- Materials are a deliberately small fictional catalog: sand, silt, clay, gravel,
  stone, weathered rock, organic litter, iron ore and copper ore. Values are
  engineering abstractions, not geological predictions.
- Presets: `temperate_woodland_meadow`, `dry_scrub_rocky`, and `wet_riparian`.
  Presets alter moisture, parent material, water table, deposits and seed density.

## Determinism

Generation uses SHA-256 coordinate/domain streams rather than a shared mutable
PRNG. Cell/deposit/seed results therefore do not move when callers request cells
in another order. The supported determinism claim is same Python/runtime and
contract version; cross-platform floating-point identity is not claimed.

## Soil-water abstraction

`soil_step` applies declared rainfall input, texture/organic/compaction-influenced
infiltration, layer-to-layer percolation, temperature/daylight evaporation, a
bounded plant uptake abstraction, and runoff. Each step appends a water ledger with
inlet, storage, transfers, loss, uptake and balance error. Water is never created
when rainfall is zero. Standing surface water is separate from soil saturation.

## Finite material operations

`extract` removes finite ore and proportional gangue; both ore and gangue/spoil
are recorded. `excavate` removes existing horizon volume and accounts for spoil;
it never creates fresh topsoil. `deposit` consumes loose stock and inserts an
explicit backfill horizon. Revisions and optional operation IDs provide
copy-friendly contention/idempotence behavior; no hidden refill exists.

## Durable use

`save` writes canonical, checksum-bearing JSON through a temporary file and atomic
replace. `resume` validates the contract and checksum. `replay` applies a bounded
operation list (`soil_step`, `extract`, `excavate`, `deposit`) to a copied state.
This is a research-sidecar persistence format, not a migration or replacement for
the native SQLite authority.

Focused tests cover 20 seeds, structural validation, same-seed hashes, order
invariance, seed variation, invalid configs, extraction conservation/contention,
no-inflow water behavior, drought/wet response, excavation/spoil accounting and
JSON restart/replay. G4+ plant lifecycles, native integration, viewer wiring,
deep underground support and full weather coupling remain deferred.
