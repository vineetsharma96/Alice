# Milestone G: integrated persistent world

21 October 2026. Application 0.14.0 / stabilization/5; native UW9, DB10 and
checkpoint schema 9 remain unchanged. This is bounded authored execution with
operator-assigned tasks and private source-linked care tests. It does not train
a policy. The failed Phase 9 study remains sealed and outside live policies.

## Changes and attribution

Four inhabitants now share one scheduler and physical world while executing
survival and explicitly assigned production/care tasks. A bounded pen blueprint
uses a real storage box, eleven fences and a gate. Material acquisition precedes
site approach; placement clears the builder's body, offcuts enter native storage,
and the final gate is built from outside. Native capacity, placement, tool wear,
resource depletion and rejection semantics remain authoritative.

The CARE claim format links an own-accessed lesson to a durable native feed test.
Receiving a claim grants no skill. Other inhabitants cannot read its private
record. A false water-feeding claim must face the native validator. Ordinary
feeding without a lesson remains explicitly authored execution. Own observed
resource locations can guide return trips; collection still requires a fresh
observation. No operator-only stock diagnostics enter policy observations.

Verified SQLite archives precede pruning. Protected claims, tests, procedure
proofs, pending requests and controller chain anchors survive rotation. Missing
archives, source-reference mismatch, unsafe reservations and quota exhaustion
stop safely. Portable backups copy and verify retained epoch files. Replay starts
at the declared retained checkpoint. This preserves current state while bounding
some history; it does not provide indefinite storage or operation.

Two F defects were corrected: a non-culture observation need not contain a
`present` flag, and pure knowledge injection must not drain native ecology
events. The model-off desktop guard now checks every inhabitant's active task
before advancing time or starting threads.

## Evaluation and retained failures

[The prospective protocol](PHASE_G_INTEGRATION.md),
[development notes](PHASE_G_DEVELOPMENT_NOTES.md), and
[pre-confirmation compute allocation](PHASE_G_COMPUTE_ALLOCATION.md) define the
comparison. Registration pins 43 files before confirmation. Development uses
seed 21; held-out seeds are 2521 and 2549, each with unassigned survival and an
explicitly assigned arm. Each primary cell targets 60 then 300 continuous
simulated seconds. Unassigned survival is not penalized for choosing no
production. The later single-world extension has no equal-horizon comparator.

Earlier development placement and navigation failures remain in their original
logs and databases. A legacy rotation development check also detected runtime
source changes during that early run; it is retained and superseded by frozen
checks. Development4 continued its same life to 360 seconds and completed all
13 pen components in 106 primitives with zero native failures. It also completed
tool, feed and water tasks; tending remained blocked when the target was not
observed. No separate development lifetimes are added together.

## Evidence

All four registered cells reached 60 and 300 continuous simulated seconds.
All software invariants passed; **held-out pen integration remains partial**.
No policy/source changes followed the confirmation results.

| Seed | Arm | Sim s | Wall s | Accepted | Completed | Failed | Rejected | Humans alive |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2521 | unassigned | 300 | 141.094 | 32 | 31 | 1 | 0 | 4/4 |
| 2521 | assigned | 300 | 268.721 | 245 | 244 | 1 | 0 | 4/4 |
| 2549 | unassigned | 300 | 134.687 | 28 | 28 | 0 | 0 | 4/4 |
| 2549 | assigned | 300 | 272.335 | 236 | 234 | 1 | 0 | 4/4 |

Accepted requests are not completed actions. Seed 2549 assigned retains one
in-flight request at its cutoff; each failed action is a native `COLLISION`
during movement (one in each assigned arm and one in seed 2521 unassigned).
No rejection was suppressed or relabelled. No model calls or fallback goals
occurred. The unassigned arm remains authored survival, not a fallback.

Both assigned arms completed tool, source-linked feed, actual trough/water
transfer, food acquisition and rest. Seed 2521 pen stopped after 106 primitives
at `observed_pen_site_occupied`; tending was blocked because the assigned animal
was not observed. Seed 2549 pen remained active; tending completed an inspection,
which does not imply an additional feed effect. Neither held-out pen earns
completion credit at 300 seconds. Development success is not held-out success.

Final hunger/thirst/fatigue values >=0.5 are reported as diagnostic unmet needs:
agent-1 fatigue was 0.5038 and 0.5052 in the assigned arms; other reported need
values were below that cutoff. Animal survivors at 300 seconds were 0/2 and 2/2 for seed2521 unassigned/assigned,
and 1/2 in each seed2549 arm. Two seeds do not establish a survival advantage. Measured
food, water and animal-body balance errors were zero. Both primary arms had
archive epoch 2 at cutoff. DB sizes were 454,656 bytes unassigned and
1,691,648/1,675,264 assigned; retained archives were 761,856/765,952 bytes
unassigned and 3,489,792/3,362,816 assigned.

Wall times include collection/replay and are shared-host measurements, not
model latency or rendering FPS. Primary stages each stayed within their declared
240-second wall budget. [Raw cohort](../artifacts/living_world_g_confirmation.json),
[audit](../artifacts/living_world_g_summary.json), and
[registration](../artifacts/living_world_g_registration.json) preserve receipts,
goals, cost, source hashes and cutoff states.

The independent in-flight restart reaches the same 120 simulated seconds across
the 100-second archive boundary: primary 60.838 wall seconds, fresh process
59.938 wall seconds. Native/cognitive state, identity/controller tables and
logical scheduler/epoch fields match exactly. Archive hashes are verified
individually; file-layout-derived hashes are excluded from cross-file equality
as registered. [Continuity evidence](../artifacts/living_world_g_continuity.json).

The registered extension continued the **same seed2521 assigned life from 300 to
537 simulated seconds**, stopping at the 240-wall-second execution limit
(240.516 total wall seconds including final collection). It did not reach 900;
other 900-second cells remain deferred under the predeclared compute allocation.
All four humans remained alive with health1; final fatigue was 0.5406/0.5018 for
agents1/2, and other need diagnostics were below0.5. Both animals were dead at
cutoff, with hunger/thirst1 and health0. One-time care is insufficient for sustained
husbandry. No new goals, lessons, bodies or resources were introduced. Replay
matches, material balance errors remain zero, archive epoch is5, current DB is
1,224,704 bytes and retained archives total4,321,280 bytes. Models/fallbacks stay0.
The extension adds continuity/scarcity evidence, not an equal-horizon comparison.
[Extension evidence](../artifacts/living_world_g_extension.json).

The false CARE-water fixture completes a real bounded test: native `offer_feed`
returns `INVALID_ARGUMENT`; the task blocks, records its own source/test and earns
no goal credit. Injection leaves physical state unchanged. This demonstrates
that valid lesson text and accepted task assignment do not establish truth or
successful action. [Native evidence](../artifacts/living_world_g_false_lesson.json).

## Final verification and executable

- Full regression: **239 Python tests pass in298.263s** (299.422s subprocess
  wall time), plus **four native CTest checks**. The 20 G regression cases cover
  native barriers, capacity/placement, private source access, durable in-flight
  recovery, archive interruption/quota/corruption, source-reference retention,
  model-off guards and portable backups. Existing E and legacy rotation suites
  also remain green. [Full output](../artifacts/living_world_g_checks.json).
- Pyflakes and Python parsing pass. JavaScript syntax and Git Bash syntax pass.
  The static import/header/asset inventory covers101 Python files, with no
  errors or repeated substantial production functions. This does not prove
  every branch/platform. [Inventory](../artifacts/living_world_g_connections.json).
- The rebuilt unsigned Windows executable is12,663,805 bytes, SHA256
  `3f40a7ba64a79004a35a7268a2b36883250ddce830e7a729aec8eca497aac30b`.
  Its native build matches the unchanged D build. [Package](../artifacts/living_world_g_package.json).
  Source/executable/source save interchange and portable replay pass with no
  external Python/compiler on PATH. [General smoke](../artifacts/living_world_g_package_general.json).
- Packaged archive copying/verification, agent4 model-task refusal before time
  advances, and both read-only viewers pass. No page errors; care provenance,
  epochs and operator-diagnostic separation are checked. Rendering used headless
  Edge/software and supplies no hardware FPS claim.
  [Integrated smoke](../artifacts/living_world_g_package_integration.json),
  [viewer evidence](../artifacts/living_world_g_viewer.json).
  The existing single `run.sh` Bash launcher also passes on Windows/Git Bash.
  [Launcher evidence](../artifacts/living_world_g_launcher.json).
- The exact pre-G F archive still matches all54 manifest files, and its original
  executable reads its old F save. [Compatibility](../artifacts/living_world_g_f_compatibility.json).
- Independent Phase9 audit verifies3439 evidence files/four sealed sources,
  360 training trials/840 rollouts/210 pairs/five finished journals; metrics
  match and **advance=false**. [Audit](../artifacts/living_world_g_phase9_audit.json).

The post-measurement [delivery inventory](../artifacts/living_world_g_delivery_audit.json)
checks the exact four-cell cohort and delivery evidence. It records
`verification_passed=true` separately from `held_out_integration_complete=false`.
Its runnable script is `scripts/phase_g_delivery_audit.py`; it advances no world
and introduces no new experimental threshold. The executable and archived
runtime are local ignored build artifacts; Git carries source and evidence,
not a signed binary release. Existing operator viewer8765 was left untouched;
owned verification servers were stopped after their checks.

## Operational limits

The pen is empty; animal capture and arbitrary enclosure topology are absent.
Task queues, decomposition, spatial routing and blueprint geometry are authored.
Receiving initial woodcraft text does not cause autonomous production. There is
no autonomous teaching, general goal formation, neural training, reproduction,
speech or true 3D mechanics. No consciousness, general intelligence or
civilization-emergence claim is supported.

The G profile has finite stocks and zero regeneration/growth. Long-term husbandry
and sustainability are unproven. Native stable receipts and protected knowledge
still have hard quotas. CARE food acquisition is implemented; plant-food/egg
claims can use carried material but lack a general acquisition procedure. A's
global inference-budget/fairness gate remains open; these runs keep models off.

Old F worlds require the exact preserved runtime at
`build/runtime-before-milestone-g-20261021`; older worlds require their own
archives. G does not migrate, reset bodies or replenish a save. The local Windows
executable is unsigned and its package checks apply to this host.

See [operations](INTEGRATED_WORLD_OPERATIONS.md) for runnable commands, archive
bundles and explicit attribution. Raw evidence uses `artifacts/living_world_g_*`;
the preserved databases live under `data/living-world-g-*` locally.
