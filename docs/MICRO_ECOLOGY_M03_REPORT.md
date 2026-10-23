# Microbial ecology M0-M3 report

## Scope and ownership

This is the first bounded ALICE 03 slice. It is an additive CPU-first sidecar in
`underworld/micro_ecology_m03.py`; it does not import or modify
`native/storage.py`, native code, existing worlds, F8-F12, lifecycle modules, or
world-generation files. It is not a replacement for any current backend and it
does not claim whole-world integration.

The sidecar owns only the habitats and stocks supplied to `initial()`. Callers
must explicitly transfer or inoculate material. Existing Alice weather/resource/
life systems remain authoritative for their own saves and resources.

## M0 audit and model choice

The repository's current `HANDOFF.md`, `docs/STATUS.md`, `README.md`, resource
helper, weather transactional store and integrated life sidecar were read before
implementation. The current project is intentionally protective of historical
saves and uses additive copy-only overlays, so this slice follows that contract.

The ALIEN repository was inspected at its public `develop` documentation during
the M0 review. Its README describes a CUDA/GPU particle artificial-life engine,
aggregate digital organisms built from cells and genomes, energy accounting,
lineages/mutation and spatially varying environments. Its repository page
identifies the project as BSD-3-Clause licensed. No ALIEN source, dependency,
binary or license text is copied into Alice. The only adapted idea is the use of
bounded aggregate cohorts and explicit lineage/source identity; this module is a
coarse material model, not an ALIEN backend. See:

* https://github.com/chrxh/alien/blob/develop/README.md
* https://github.com/chrxh/alien/blob/develop/LICENSE

The selected approach is a native-independent, standard-library CPU aggregate
model. A GPU microcosm would add a second execution universe and is unnecessary
for the M0-M3 accounting gates. Detailed cells, mutation, competition studies,
fermentation UI and disease are deferred.

## State contract

`initial()` creates explicit `soil`, `litter`, `water`, `food`, `container` and
caller-defined `host` habitats. Each habitat contains:

* finite named substrate records with organic mass, N/P/K composition and
  accessibility;
* temperature, moisture and oxygen availability;
* available nutrients, aggregate viable guild populations, dead microbial
  biomass/dead nutrients and separate byproduct pools.

The four initial functional guilds are:

* `aerobic_decomposer`
* `low_oxygen_decomposer`
* `yeast_fermenter`
* `acid_producer`

Population biomass and reserves are kilograms of organic carrier material. N/P/K
are tracked as separate element pools, so nutrient immobilization in biomass and
return to available pools can be audited without pretending that the coarse
organic carrier is a molecular model. Inoculum sources and lineage IDs are
retained with bounded source history. No population is created in a sterile
habitat.

Public operations are copy-on-write:

```python
from underworld import micro_ecology_m03 as ecology

state = ecology.initial(seed=7, habitats=habitats, inocula=[
    {"habitat_id": "soil-a", "guild": "aerobic_decomposer",
     "biomass_kg": 0.2, "source": "plant-litter-seed"},
])
state = ecology.step(state, 86400)
state = ecology.transfer(state, "soil-a", "water-a",
                        "aerobic_decomposer", 0.01, source_id="water-route")
state = ecology.decompose(state, "soil-a", "dead_biomass", 0.001)
report = ecology.inspect(state)
```

`save()` and `resume()` use a SHA-256-protected JSON checkpoint. `replay()`
reapplies explicit `step`, `inoculate`, `transfer` and `decompose` commands from
a validated starting state. Recursive validation rejects fields containing
private, operator, model, secret, hidden, LLM or prompt labels.

## M1-M3 numerical rules

* Growth is substrate-limited and bounded by the guild's maximum daily uptake,
  environmental factor and accessible substrate. Uptake partitions into biomass,
  reserves and declared products.
* Maintenance consumes reserves first and then biomass. Maintenance material is
  emitted to the CO2 product pool and its tracked nutrients are mineralized into
  available nutrients.
* Mortality is bounded by viable biomass and increases under poor environmental
  conditions or substrate exhaustion. Death transfers biomass and nutrients to
  the habitat dead pools; it never erases matter.
* Division is represented by bounded aggregate division progress/events, not by
  one object per microbe. Division requires biomass gain from an actual finite
  substrate.
* Temperature, moisture and oxygen are smooth guild-specific Gaussian/linear
  suitability factors. Aerobic and low-oxygen guilds therefore respond in
  opposite directions to oxygen availability.
* Every step is internally split into one-hour substeps. Supported public steps
  are bounded to 31 simulated days. This avoids unstable exponential growth and
  resource-deleting clamps.
* `decompose()` converts a finite substrate or dead-biomass amount into declared
  soluble/CO2 products and returns its tracked N/P/K to available nutrients.
  The function is explicit so a future integration can assign one owner to
  world-litter decay rather than double-consuming it with a legacy timer.

The conservation ledger tracks organic carrier mass and N/P/K separately. The
validator rejects negative stocks and requires current totals to match initial
totals plus explicit boundary ledgers within `2e-8`.

## Timestep sensitivity fixture

Command:

```powershell
python -m pytest -q tests/test_micro_ecology_m03.py
```

The focused fixture runs the same 3-day favorable soil case as one 3-day call
and as 72 one-hour calls. Both paths produced:

* aerobic biomass: `0.5123498836386823 kg`;
* remaining plant litter: `3.134147141333787 kg`.

The equality is expected because the public step uses the same one-hour bounded
substeps. Revision counters differ (one public operation versus 72), while
ecological stocks agree to the test tolerance. The conservation validator passes
both trajectories.

## Checks and result

Focused checks run on 23 October 2026:

```powershell
python -m py_compile underworld/micro_ecology_m03.py
python -m pytest -q tests/test_micro_ecology_m03.py
```

Result: `8 passed` and the module compiled successfully. The tests cover sterile
controls, substrate exhaustion and dormancy/decline, favorable versus cold/dry
conditions, non-negative stocks, timestep tolerance, litter-to-biomass/products
and nutrient return, explicit inoculum transfer connectivity, JSON
save/resume/replay, and rejection of private/operator/model fields.

## Deferred gates

M4 dispersal ecology beyond explicit transfer, M5 food-spoilage/fermentation
containers, M6 detailed ALIEN-inspired cells/GPU visualization, M7 disease and
M8 live world integration are not implemented here. No disease, UI, native
backend replacement, plant scheduler coupling or whole-world survival claim is
made by this report.
