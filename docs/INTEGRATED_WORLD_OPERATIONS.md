# Integrated world operations

Milestone G uses application 0.14.0 / stabilization5. Native UW9 / DB10 /
checkpoint9 laws remain unchanged. Model calls default off. Use a NEW save;
the exact F runtime is preserved at build/runtime-before-milestone-g-20261021.
Earlier saves need their own original runtime. No automatic migration/reset.

## Create and run

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe -m underworld living-world init --db data/g-user/world.sqlite --config config/living-world-g.toml --calls 0 --knowledge-profile woodcraft --knowledge-recipient agent-1
.venv/Scripts/python.exe -m underworld living-world run --db data/g-user/world.sqlite --seconds 60 --wall-seconds 240
```

Every run advances that existing world. Bodies, identities, material stocks,
native requests, memories and scheduler state persist. Repeating the command
adds time; it never starts another episode or replenishes food/water.

The G profile has four inhabitants and two native animals, finite food/water,
three trees and finite forage in 16 m. All regeneration/growth is zero. It is a
guided experiment, so explicit interventions are journaled. Initial woodcraft
text is external information, not a restriction on pre-existing authored recipes.
Unassigned inhabitants use authored survival; production does not automatically
follow from receiving a profile. Optional E model budgets remain a separate limit.

## Explicit production and care

```powershell
.venv/Scripts/python.exe -m underworld living-world task --db data/g-user/world.sqlite --agent agent-1 --goal build_pen --params '{"position_m":[11,11]}'
```

The bounded authored pen method crafts a usable axe, planks and a storage box,
stores real offcuts when capacity requires it, then attempts eleven fences and
one gate on a 3.6 m square with 1.2 m spacing. The gate is closed on completion.
There are at most 192 task primitives, four native failures and 900 simulated
seconds including survival preemption. Existing E goals keep their own bounds.
The blueprint builds an empty pen; it does not teleport or capture animals.
Occupied sites can block the task. Native placement and carrying limits decide.

Care uses an explicitly accessed claim such as:

```text
CARE {"material":"food","task":"feed-v1"}
```

Introduce it through the F guided injection, a native book or actual hearing.
The intended recipient's `knowledge` output gives its own episode id. Then:

```powershell
.venv/Scripts/python.exe -m underworld knowledge --db data/g-user/world.sqlite --agent agent-2
.venv/Scripts/python.exe -m underworld living-world task --db data/g-user/world.sqlite --agent agent-2 --goal feed_animal --params '{"target":"animal-1","lesson_episode_id":2,"mass_kg":0.025}'
```

Replace 2 with the real own lesson id; do not guess it. `feed_animal` tests one
bounded material claim through an actual native transfer. Arbitrary prose is
not executable. A false water/wood feeding claim faces native rejection. Reading
or injection alone grants no skill. The task records source identity separately
from its authored decomposition and native terminal result. Supplying no lesson
uses the existing authored food rule and is not counted as taught execution.

Other useful assigned goals are `craft_tool`, `make_planks`, `provide_water`
(optional `position_m` chooses the trough site), `tend_animal`, `obtain_food`
and `rest`. An already well animal's inspection is not counted as feeding.
Actual transfers and consumption require native receipt evidence. Autonomous
teaching, arbitrary enclosure topology and automatic animal capture remain absent.

Own observed source locations can guide a return trip, but every gather requires
fresh visibility and native revalidation. That bounded authored spatial memory
does not reveal stocks behind walls, share private memories or train weights.

## Archives and portable backups

G automatically rotates history every 200 physical ticks (100 s at dt0.5).
A full SQLite checkpoint is published and verified before pruning. Active native
requests, E procedure proofs, F claims/test links and operator records survive.
Controller event prefixes become hash-anchored archived history. Replay starts
from the declared retained epoch checkpoint, not from the original birth state.

```powershell
.venv/Scripts/python.exe -m underworld living-world archive --db data/g-user/world.sqlite
.venv/Scripts/python.exe -m underworld living-world archives --db data/g-user/world.sqlite
.venv/Scripts/python.exe -m underworld save --db data/g-user/world.sqlite --name my-portable-checkpoint --output data/g-backup/world.sqlite --with-archives
```

Use a new output path and checkpoint name. The portable backup includes the
verified retained epoch files in `world.sqlite.epochs`. A plain SQLite save still
contains its present physical/private state and retained replay prefix; a run
requiring its audit archives refuses missing files. Keep the bundle together.
An interrupted partial bundle must not be treated as a verified portable backup.

Missing/corrupt retained archives, inconsistent source references and unsafe
unsubmitted reservations fail closed. Reconcile an unsubmitted reservation by
resuming the normal controller, rather than deleting it. Archive disk exhaustion
stops safely and preserves existing recovery points. Inspect real status/reason;
do not erase saved bodies to make a demonstration continue.

Retained archives are bounded (three by default) and old files are evicted only
after a verified replacement commits. Native stable receipts and protected
knowledge remain subject to hard quotas; this is not indefinite operation.
No silent forgetting of referenced knowledge is used to hide those limits.

## Reproduce the integration experiment

```powershell
.venv/Scripts/python.exe scripts/phase_g_demo.py --split development --directory data/g-example --output artifacts/g-example.json
```

This creates new named worlds and compares unassigned survival with explicit
operator task queues. It records successes, failed/unmet goals, accepted versus
completed native actions, balances, source chains and actual simulated/wall time.
No requested outcome is guaranteed. Longer horizons stop at the wall/stock/quota
limits and remain one continuous world. Do not add separate seed lifetimes.

Both read-only viewers show selected task status, care source, tools/durability,
history epoch and labelled operator stock/animal diagnostics. Those diagnostics
are never input to the inhabitants' policies. Rendering FPS, simulation throughput
and model latency are separate measurements. The desktop remains read-only for
interventions; use explicit CLI teaching between controller runs.

## Verification tools

```powershell
.venv/Scripts/python.exe scripts/verify_living_world.py --output artifacts/my-g-checks.json --timeout 600
.venv/Scripts/python.exe scripts/phase_g_audit.py
.venv/Scripts/python.exe scripts/package_app.py --evidence artifacts/my-g-package.json
```

The cohort audit reads the fixed retained confirmation/registration paths; it
does not run another experiment. Full verification requires the native build,
CMake/CTest and Python test environment. Packaging additionally requires
PyInstaller. Optional browser harnesses require Node, an importable `playwright`
package and installed Microsoft Edge; these are development verification tools,
not executable runtime dependencies. No model server is needed for G.

`smoke_integrated_package.py` requires a finished G source database with its
`.epochs` directory and a fresh output directory. It operates on a copied world,
tests the nondefault-inhabitant model guard, portable archives and both read-only
viewers, then stops its own server. It does not change the original experiment.
