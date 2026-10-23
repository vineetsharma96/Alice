# Microbial ecology M4-M8 bounded overlay report

## Scope and ownership

`underworld/micro_ecology_m48.py` is an additive CPU-side overlay. It accepts a
validated M0-M3 snapshot through `adapt_m03()` and copies the supplied habitats,
stocks and populations. It does not modify `micro_ecology_m03.py`, storage or
native code, existing worlds, F8-F12, lifecycle modules or G01. M03 remains the
owner of the source snapshot; M48 owns only the returned experimental overlay.

## Implemented M4

* Dispersal requires a declared enabled route, a source population and finite
  route capacity. Biomass, reserves and nutrient pools move proportionally.
* Sealed routes can be blocked explicitly. No source and no connectivity means
  no spread.
* Competition is represented by shared finite substrate allocation. Strains
  with different uptake affinity receive different shares under scarcity.
* Traits are bounded to uptake affinity, maintenance multiplier and temperature
  tolerance. Mutation is opt-in, creates a child with an ancestor ID and stores
  an immutable ancestor-control trait record. No new chemistry or disease
  function can be created by mutation.

## Implemented M5

Fictional food/container fermentation tracks substrate, culture biomass, product,
byproduct, gas and exported gas separately. Each process has finite capacity,
temperature and oxygen conditions, seal/vent flags and gas capacity. A sealed
unvented vessel stops when its gas budget is full; a vented vessel exports gas
through the explicit organic boundary ledger. The coarse partition is:

* 10% culture biomass;
* 60% fictional product;
* 20% byproduct;
* 10% gas/export.

The sum is one-for-one in the modeled organic carrier. This is an engineering
accounting model, not molecular stoichiometry, and fermentation is not a safety
or medical claim.

## M6 observer conversion

`to_microcosm()` creates a bounded representation-only cell list plus copied
stocks. `from_microcosm()` validates those stocks and returns the unchanged
aggregate state. It cannot evolve, multiply or delete ecology, so observer
conversion round-trips without changing tracked stocks.

## M7 and M8 boundaries

Disease is disabled with a fixed manifest `{status: "disabled", manifest: null}`;
there is no pathogen implementation. M8 is limited to adapter ownership,
JSON checkpoint/resume, deterministic replay and observer reporting. No live
world scheduler or legacy-backend coupling is introduced.

## Checks

Focused checks:

```text
python -m py_compile underworld/micro_ecology_m48.py
python -m unittest -q tests/test_micro_ecology_m48.py
python -m pytest -q tests/test_micro_ecology_m48.py
```

The focused tests cover no-source/no-spread, route connectivity and capacity,
transfer conservation, competition, ancestor/common-condition adaptation
control, paired fermentation outcomes and mass accounting, sealed/vented
constraints, JSON restart/replay, observer round-trip and disease-disabled
behavior.

Deferred: disease, native/storage integration, existing-world migration, live
plant/host coupling, GPU/detail authority and any claim of real-world food
safety or pathogen behavior.
