# Living-world B audit and Milestone C report

20 October 2026. Current bounded C mechanics are implemented. This continues the supplied [living-world prompt](../Prompt/Alice_Living_World_New_Agent_Prompt.md); it does not complete later animal, learning or teaching milestones.

## Review verdict

The other agent's B baseline passed all **142 Python tests** (212.059 s internally) and **4 native checks**. Those checks missed several real defects. The review corrected:

| Defect | Evidence and correction |
|---|---|
| Growth exceeded its 8 kg maturity cap | At 0.007 kg/s, tree-1 reached 8.006 kg after 858 s. Grant only remaining capacity and debit the explicit source ledger by the actual grant. [Reproduction](../artifacts/living_world_b_growth_reproduction.json). |
| Inventory checkpoints accepted only three species | Native restore now allows the bounded material set; a five-species inventory round-trips exactly. |
| Actors could spawn on the new stone pile | Before correction, seeds 15,33,44,99 failed in 8 m / 4-person worlds; seed 44 also failed in the default 16 m region. Initial placement now reserves that footprint. Final regression initializes seeds 0-99 at (8 m,4 people), (16 m,4 people), and (16 m,8 people): **300 valid initializations**. These are initialization checks, not 300 continuous lives. [Pre-fix sweep](../artifacts/living_world_b_initial_placement_audit.json). |
| Caller-selected harvest anchors could place products remotely | Explicit nonzero anchors now stay within 1.8 m of their source tree. Occupied/out-of-bounds placement still fails; native products are not silently relocated. The legacy (0,0) destination sentinel means automatic nearby placement. |
| Repeated harvests could exceed the 200-entity restore limit | Completion rejects ENTITY_LIMIT before creating any products or removing biomass. A crowded 199-entity fixture verifies no partial grant. |
| Viewer kept a mature mesh after the tree became a stump | Entity kind/stage changes rebuild presentation geometry. A real headless browser verifies two mature-tree meshes become one stump mesh, and the completed box appears. |

A review also found A gaps: the old observer could advance a stabilized world through the legacy scheduler, and the 3D packet did not expose controller state. Stabilized worlds now require read-only observer attachment; the CLI drives their scheduler. Both observer projections report controller/selected goal, origin, calls/budget and fallback, with journal checks. Unmanaged selected inhabitants have no other person's controller state projected.

**A remains incomplete:** its requested recurring per-agent eligibility, fair scheduling and global wall/token model budgets were not implemented by the prior handoff. Its lifetime call bound remains. C is verified model-off; no new model-enabled or AppContainer-controller integration gate is claimed.

## Implemented C mechanics

[The preimplementation contract](PHASE_C_CRAFTING.md) fixes quantities, work and acceptance checks. `core/crafting.cpp` supplies a reusable native table rather than separate manufacture functions for every recipe. Branch wood/fiber plus finite stone produce a 0.70 kg axe; felling requires that owned usable axe; 1 kg wood produces 0.8 kg plank and 0.2 kg offcut; planks produce a box, trough, fence or gate.

Tools retain composition, ownership and durability. Each felling/plank operation spends a use; breaking returns the exact original constituents as scrap. Carrying capacity includes owned tools, and survival gathering uses that permitted own-state total. Craft ingredients remain carried until atomic terminal transformation. A construction site receives real inputs, reserves geometry, and saves fixed-step work. Cancellation, competing workers, missing tools, crowded placement, full inventory, gate closure and storage/trough transfers revalidate natively.

A box contains actual bounded material stacks. Fences and closed gates block native movement; an open gate permits passage and refuses to close over an actor. This is 2D circular collision geometry. **Animal containment is not established until D implements animals and their shared movement.**

The recipe registry is an operator API, not automatic agent knowledge. `workshop.py` resolves action targets from the selected inhabitant's permitted observations/owned tools. Fixed waypoints and the production order are explicitly supplied externally for the fixture. Privileged snapshots are used for operator verification, not target selection. The separate `assigned_procedures` evidence row is an operator assignment, not a fabricated book-read, taught memory or learned procedure. The native successful-work counter is authored practice, not proof of learning. General planning/learning and teaching remain E/F.

## Measured evidence

| Check | Observed result |
|---|---|
| Final full regression | **160 Python tests**, 201.900 s internally; all passed. **4 native CTests**, all passed. [Raw checks](../artifacts/living_world_c_checks_final.json). |
| Follow-up crafting/viewer checks | **26 tests**, 14.956 s; all passed after local target projection and operator-only contents diagnostics were separated. [Output](../artifacts/living_world_c_targeted_checks.json). |
| Physical production chain | **21 accepted and 21 completed requests**, no rejection/failure. One person gathers branches/fiber/stone, crafts axe, fells tree, cuts planks, builds a usable box and transfers offcuts in/out. **55.6 simulated s / 7.543 wall s**, including setup, replay and a fresh child process. Model calls **0**. [Receipts/events](../artifacts/living_world_c_demo.json). |
| Interrupted construction | Backup at **2.2 / 8 work seconds**; fresh Python continuation matched the uninterrupted native head. Inputs, footprint and partial work persisted. Unit checks also cover cancellation and in-flight crafting. |
| Four-inhabitant continuity | One world, stages **2 + 8 + 20 + 90 = 120 continuous simulated s**; **107.250 primary wall s**. All four alive, each completed one drinking goal. **15 accepted / 15 completed actions**, no rejected/failed native actions. No food goal was needed yet: hunger ended about 0.47. Model/fallback calls **0**. [Raw continuity](../artifacts/living_world_c_continuity.json). |
| Fresh-process continuous counterpart | Backup at 30 s, then independently re-executed the next 90 s through the same model-off scheduler. **77.828 child wall s** is separate from primary duration. Native head and eight identity/memory/controller tables match. Run/branch IDs also match. [Identity check](../artifacts/living_world_c_identity_check.json). The counterpart is not added to the primary lifetime. |
| Viewer | Headless Edge with software rendering, current tree/box/controls and lifecycle checks; no hardware FPS or mobile claim. [Browser evidence](../artifacts/living_world_c_viewer.json), [screenshot](../artifacts/living_world_c_viewer.png). |
| Protected Phase 9 study | **3,439 files**, four pinned source files, 360 training records, 840 evaluation rollouts and five journals audited. Recomputed metrics match; **advance=false**. [Independent audit](../artifacts/living_world_phase9_audit.json), [six protected hashes](../artifacts/living_world_phase9_preservation.json). No learner is imported into the controller or workshop. |

Production's tree/wood/fiber/plank/offcut family totals **18 kg before and after**, including the axe and box composition. Stone remains **4 kg**; offcut waste remains **0.2 kg**. The 8 kg felling target partitions into 6.4 kg wood, 0.8 kg fiber and a 0.8 kg stump. Four-person continuity retains finite food/water with regeneration zero; 1.2 kg water moves to four ingested reservoirs. Tree growth adds a separately declared 0.6 kg ecological boundary source. Growth has no coupled water/nutrient/sunlight simulation and is not molecular photosynthesis or closed-system biomass conservation.

These are bounded engineering checks. Some development timing overlapped verification; no fair policy-speed comparison or scaling claim is made. Native throughput, inference time and rendering FPS remain different quantities.

## Failed/superseded checks retained

An initial C full run had one Windows writer-lease test error. The virtual-environment launcher and real interpreter can have different PIDs; that ambiguity was reproduced. The fixture now asserts and kills/waits the actual owner PID using the base interpreter. Three repeated checks and the final full suite pass; the production lease was not weakened. The original intermittent cleanup race was not isolated beyond that process-identity ambiguity. [Failure](../artifacts/living_world_c_checks.json), [PID evidence](../artifacts/living_world_windows_lease_reproduction.json).

The [pre-placement candidate](../artifacts/living_world_c_checks_before_placement.json), [earlier production](../artifacts/living_world_c_demo_before_placement.json) and [earlier continuity](../artifacts/living_world_c_continuity_before_placement.json) remain separate from final evidence. A superseded [candidate run was deliberately stopped](../artifacts/living_world_c_checks_candidate_interrupted.json) when review added locality validation; it is not counted as a pass. During development, fixed-route test paths hit real obstacles and operator diagnostics initially tried to read contents from the private observation projection; those fixtures/diagnostics were corrected without granting the planner privileged contents or changing native collision/visibility rules.

## Compatibility, commands and limits

Current package **0.10.0**, native **UW8**, SQLite **DB9**, checkpoint schema **8**, controller **stabilization/3**. Native build ID: `8c10de9ec672c0fd37baf6a7262d96a234ee7341b9bf0523d3a63dbb84cc35af`. Same-format saves also pin the exact build and orchestration source. No migration or saved-world rewrite was performed. Root `build/` retains the old B build; current Python refuses that UW7 module. Use **build/living-c** as documented in [HANDOFF.md](../HANDOFF.md). Pre-placement C binaries are retained locally in `build/c-before-placement-20261020`; those development runs are not final acceptance evidence.

Reproduce with a NEW output directory, never reinitialize an existing run:

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
$env:UNDERWORLD_BUILD = (Resolve-Path build/living-c).Path
.venv/Scripts/python.exe scripts/verify_living_world.py --build build/living-c --ctest C:/mingw64/bin/ctest.exe --output artifacts/my-c-checks.json
.venv/Scripts/python.exe scripts/phase_c_demo.py --output data/my-NEW-production
.venv/Scripts/python.exe scripts/phase_c_continuity.py --output data/my-NEW-continuity --evidence artifacts/my-continuity.json
```

Remaining limits: craft work consumes time and abstract body costs, with no new mechanical/chemical energy conversion model; authored recipes/waypoints and counters; no autonomous woodcraft choice or learned procedural transfer; no animals, food production, cooking, breeding, neural training or true 3D mechanics. Boxes hold material stacks, not owned tool entities. Circular fence segments need actual gap-free placement; no pen/animal demonstration is claimed. Empty piles, spent tools and cancelled sites retain IDs and count toward the 200-entity cap; no indefinite archive/compaction support is claimed. Long horizons, multi-seed survival and sustained 8-person operation remain unverified. Model-enabled A budgeting remains unfinished. New controller/workshop runs are host development processes, not a newly certified isolated unattended service. No consciousness, AGI or civilization-emergence claim is made.

The unrelated existing OpenCode/npm edits were preserved. `opencode debug config` returned zero with no validation errors; this does not establish that the credential-dependent TinyFish service is connected. [Local tooling check](../artifacts/living_world_unrelated_tooling_audit.json).
