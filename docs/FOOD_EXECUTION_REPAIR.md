# Edible-food execution repair — 21 October 2026

## Failure and implementation

The native engine already implements edible plant food and eggs, but the
persistent prerequisite executor recognized only legacy `food`. It also required
a complete 0.2 kg portion before eating. Inhabitants could therefore overlook
carried edible food and visible forage, or fail to use a smaller available meal.
This was an execution integration gap, not a validator defect or failed training.

The executor now consumes permitted own carried food, choosing the soonest
expiring usable material first; gathers visible finite forage through
`gather_plant`; and uses the remaining ingestion target after partial meals.
Observed freshness must exceed meal duration plus one tick. Each new request
uses a fresh actor observation. Native validation still rechecks stock, reach,
capacity and completion-time expiration. Retry, deadline and request bounds are
unchanged. Only actual ingested mass meets a goal; a 0.06 kg egg portion does not
meet the unchanged 0.2 kg goal. Authored logic receives all execution credit.

The assigned-procedure helper also uses the requested actor's observation when
calculating its step duration. Packaging accepts an explicit evidence output so
new builds need not replace earlier audit evidence. Native code/laws, legacy
deterministic policy, model adapter and sealed Phase 9 learner are unchanged.

## Evaluation

Read the [protocol and fixture amendment](FOOD_EXECUTION_PROTOCOL.md). Frozen
previous source is compared with current execution on identical native starting
checkpoints. Development seed 21 and confirmation seeds 717/818 each cover
carried plant food, eggs, forage, empty forage and expiring food. Receipt-level
evidence and checkpoints: [results](../data/food-repair-confirmation-20261021/results.json).

| Measure across 15 cases per arm | Previous executor | Repaired executor |
|---|---:|---:|
| Completed full meals among 6 feasible full-meal cases | 0/6 | 6/6 |
| Missed those feasible full meals | 6 | 0 |
| Additional 0.06 kg egg portions consumed | 0/3 | 3/3 |
| Total native ingestion | 0 kg | 1.38 kg |
| Native completed actions, including bounded search | 15 | 21 |
| Submission rejections / terminal failures | 0 / 0 | 0 / 0 |
| Food/water/body balance error | 0 | 0 |
| Model calls | 0 | 0 |

These are bounded assigned eating goals. Empty and expiring supplies correctly
leave goals unmet. Survival in these short checks does not prove sustainability.
Per-case simulated and wall durations, alive status, actions and blocking reasons
are in the result. Direct native fixture speed is not durable scheduler throughput.
There is no model-policy or fallback-improvement claim; both arms use authored
execution. Seed variation here does not demonstrate broad navigation ability.

The first evaluation is retained at
`data/food-repair-eval-20261021/results.json`: its egg fixture left other edible
food accessible, invalidating the expected partial-only outcome. The fixture was
corrected and fresh confirmation seeds used without retuning the policy.

Seven new native-backed regression cases additionally exercise approach,
partial-meal accounting, mixed-material selection, expiry failure semantics and
in-flight persistent save/resume with exact replay. The selection-only mixed
inventory test uses a copied observation; it does not inject stock into a world.
Other cases acquire food through native actions and preserve integer balances.

The first full regression run passed 189/190 Python tests and all four native
checks. The parallel Windows isolation test inspected results while one launch
thread was still running; it passed alone in 34.295 s including setup/cleanup.
Its test harness now waits up to 90 s for both workflows and explicitly asserts
that no thread remains alive. Each worker retains its original 20 s budget;
both target-reached outcomes and cleaned isolation profiles are still required.
This changes test synchronization, not an experimental acceptance threshold or
production isolation rule. The failed run is retained in
`artifacts/food_repair_regressions.json`.

The final full rerun passes **190 Python tests in 231.412 seconds** and **four
native checks**. Protected Phase 9 hashes also match.
[Final full regression evidence](../artifacts/food_repair_regressions_final.json).

The durable continuity check advances the same finite-resource world from tick
163 to 283: **120 continuous simulated seconds / 25.792 primary wall seconds**,
in successive 1/29/30/60 s calls. Setup first advances a newly declared world to
160 s and acquires plant food through native actions, reaching tick 163; setup
cost is recorded separately. A tick-164 backup resumes another 119 simulated
seconds in 17.396 wall seconds to the identical native head, controller and
private memories. Replay passes, the human remains alive, and two goals finish
through four submissions, including 0.2 kg actual food ingestion. There is no
reset/refill or regeneration; this is a one-human check, not population survival.
[Continuity evidence](../artifacts/food_repair_continuity.json).

The rebuilt executable passes reduced-PATH executable/source/executable identity,
backup/replay and default-config checks. Both packaged viewer pages pass asset,
animal display, privacy and read-only-control checks with zero JavaScript errors
under headless Edge software rendering. This does not measure hardware FPS.
[Package smoke](../artifacts/food_repair_package_smoke.json),
[viewer evidence](../artifacts/food_repair_viewer.json).

Static Python lint, JavaScript syntax and Git Bash launcher syntax pass. Static
connection checking parses 78 Python modules, finds no missing local edges and
no repeated substantial whole production functions; it cannot prove all dynamic
branches correct. README's legacy Windows encoding was converted to UTF-8.

The full regression command is:

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/verify_living_world.py --output artifacts/your-new-checks.json --timeout 480
```

It exercises configuration/native mechanics; bodies, senses and needs;
cognition compilation and failure handling; private memory/provenance and
teaching; thermal/material conservation; retention, quotas and Windows isolated
operation; viewer APIs; the preserved learning implementation's regression
behavior; tree growth; crafting/construction; animal/food ecology; persistent
prerequisite execution; and the desktop/connection fixes. It does not prove
every function/branch, every platform, fresh live-model reliability or success
of historical failed scientific objectives. The independent packaged browser,
continuity and food receipt checks supplement that suite.

## Compatibility and remaining work

Controller source pins change. Prior source, configs and the exact prior
executable are preserved at `build/runtime-before-food-fix-20261021`, including
a SHA manifest. Use its `UnderworldLab.exe` for an existing pre-repair save;
do not silently reset or migrate it. Existing 20 October scientific/audit
artifacts remain historical. New saves use the rebuilt `dist/UnderworldLab.exe`.
The preserved executable successfully reads the original code-audit 120-second
world; its output is retained in `artifacts/food_repair_legacy_runtime_check.json`.

General husbandry/navigation, recurring fair/global inference budgets, autonomous
crafting, breeding, cooking, speech, neural training and true 3D remain incomplete
or deferred. Phase 9's failed learning gate is unchanged and its learner remains
excluded. This repair does not implement the whole of milestone E or establish
long-term survival, consciousness, intelligence or civilization emergence.
