# Connected living-world bridge — 24 October 2026

## Result

`underworld/living_world_bridge.py` now attaches the G01/G47/L02/L59/M03/M48
foundation sidecars to a **new copy** of an existing UW10W/life world. The
native world remains the authority for time, bodies, resources, actions,
receipts and weather. Each bridge operation commits the native life journal,
native weather journal and sidecar checkpoint in one SQLite transaction.

The bridge accepts either a compatible weather/F5 source, which it first
enrolls through the existing `life_store` copy-only path, or an already
enrolled ALICE-LIFE-1 copy, which it backs up directly before adding bridge
tables. The source path must remain unchanged and the destination must be new.

## Connected stages

| Stage | Native binding | Boundary |
| --- | --- | --- |
| G01 | Native seed, world bounds and current weather drive a bounded terrain/soil copy. Soil water advances from native climate. | G01 is an environmental sidecar; it does not replace native terrain or materials. |
| G47 | Native tree observations map to copied plant records. Plant growth uses native climate; native tree mass/stage/alive status is authoritative on every bridge tick. | UW10W tree taxonomy is not exposed, so the mapping uses declared G47 adapter species. |
| L02 | Native actor IDs, elapsed native time, alive state and completed public `give`/`speak` receipts update lifecycle individuals and directional relationship evidence. | Native actors expose no reproductive roles, so bridge records are non-reproductive residents; no conception is created automatically. |
| L59 | Native actor IDs, elapsed biological time and alive state update ageing/function records. | Care needs and mortality hazard are zero because the native source does not expose those biological contracts. |
| M03 | Native tree/resource observations initialize bounded soil, litter, water, food, container and host habitats. Native climate updates habitat environment before each ecological step. | Resource masses are copied as sidecar inputs at attach and retained as observations; native resource authority is never mutated. |
| M48 | M48 is adapted from the initial M03 state and advances with native climate/time. Finite routes and fermentation remain sidecar-only. | M03 remains the M48 source boundary; M7 disease is disabled. |

All six sidecars are persisted in one bridge state row and verified by a
hash-chained bridge operation journal. Reusing an operation ID with the same
command is idempotent; a conflicting command is rejected.

## CLI

Use new paths and stop other writers before operating on a database:

```powershell
python scripts/living_bridge.py attach `
  --source data/my-life.sqlite `
  --db data/my-living-foundations.sqlite `
  --biological-step-s 86400

python scripts/living_bridge.py run `
  --db data/my-living-foundations.sqlite `
  --ticks 360 `
  --output artifacts/my-living-foundations-90s.json

python scripts/living_bridge.py inspect --db data/my-living-foundations.sqlite
python scripts/living_bridge.py replay --db data/my-living-foundations.sqlite
python scripts/living_bridge.py save `
  --db data/my-living-foundations.sqlite `
  --destination data/my-living-foundations-backup.sqlite
```

`--ticks` is a native tick count. `--biological-step-s` controls how much
native simulated time is required before L02/L59 receive one biological step;
the default is one simulated day. `life_store.py` and the existing viewer
remain valid for ordinary ALICE-LIFE-1 copies; the bridge CLI is the explicit
entry point for the six new foundations.

## Verification

Current focused evidence:

```text
python -m pytest -q tests/test_living_world_bridge.py
4 passed in 20.61s

python -m pytest -q tests/test_living_world_bridge.py tests/test_alice_full_ordered_foundations.py tests/test_alice_foundations_integration.py
6 passed in 24.39s

python -m pytest -q tests/test_integrated_life.py tests/test_foundations_review.py
21 passed, 3 subtests passed in 15.76s

python -m py_compile underworld/living_world_bridge.py scripts/living_bridge.py tests/test_living_world_bridge.py
passed

npm run lint
node --check server.js
passed

export UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe"; python -m pytest -q
534 passed, 355 subtests passed in 738.52s
```

The bridge tests cover attach/source preservation, all six sidecars, native
tick advancement, biological-clock advancement, idempotent retry, native
receipt-to-L02 evidence, backup and combined native/life/sidecar replay.

The full repository run above includes the bridge addition and completed with
no errors. An earlier attempt used a shell-local `set UNDERWORLD_CORE=...`
assignment, so the scaffold tests could not see the variable and reported
`528 passed, 2 errors, 346 subtests`; rerunning with `export` fixed that
environment issue.

This is a real copy-only runtime connection, not evidence that the later
scientific reproduction, care, mortality, plant taxonomy, microbial or
long-horizon survival gates have passed. Those contracts remain bounded and
explicitly limited by the adapter notes above.
