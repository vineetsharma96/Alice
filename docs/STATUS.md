# Current Alice dashboard - 24 October 2026

The Windows launcher now exposes explicit integrated-life GUI modes:
`run.cmd --readonly --db ...` opens the read-only Alice dashboard, while
`run.cmd --control --db ...` opens the paused single-writer control dashboard;
`readonly` and `control` word aliases are accepted. The packaged executable
was rebuilt with the dynamic life/viewer imports, weather extension and
provenance files required by these modes. Both packaged modes returned the
native `alice.dashboard/1` packet in temporary smoke runs.

Launcher-focused verification: `7 passed in 7.84s`; py_compile,
`npm run lint` and `git diff --check` passed. The most recent completed full
suite (`534 tests and 355 subtests`) predates these launcher-only changes; the
post-change five-minute `python -m pytest -q` attempt reached 23% without
failure output before timeout.

---

The existing integrated-life UI now serves a complete observer/control
dashboard from `underworld/life_viewer.py` and `underworld/life_control.py`.
It uses the authoritative native weather/life head, existing writer lease and
journal. The dashboard includes persistent simulation/calendar/population
status, shared 2D/3D views, selected-inhabitant inspector, evidence-backed
mood charts with tick-aligned mean/range and event markers, directed relationships, bounded event timeline, weather/exposure
telemetry, guided weather override controls, Advanced JSON and copy/download.
Controls include pause/resume, one tick, one turn, speed, bounded tick batch,
run-until simulated time and safe cancellation. Jobs never change the native
timestep, cannot overlap, and return paused after completion.

New dashboard files: `underworld/web/dashboard.html`,
`underworld/web/dashboard.css`, `underworld/web/dashboard.js`. Backend
telemetry is bounded to 240 retained records and explicitly labels unsupported
microbial counts, reproductive fields, target-specific anger and inventory
metadata. See `docs/ALICE_DASHBOARD_REPORT.md`.

Focused verification: life controls `5 passed in 9.13s`; integrated life,
controls and bridge `17 passed in 51.46s`; py_compile, browser module parsing and
`npm run lint` passed. Browser smoke confirmed speed selection,
pause/resume/cancel at safe boundaries, 2D/3D switching and a clean loaded
dashboard. Screenshot:
`artifacts/dashboard_ui_smoke.png`.

---

# Current living-world bridge - 24 October 2026

`underworld/living_world_bridge.py` and `scripts/living_bridge.py` now connect
the G01/G47/L02/L59/M03/M48 sidecars to a new copy of a compatible UW10W/
ALICE-LIFE-1 world. Native time, bodies, resources, weather, action validation
and receipts remain authoritative. The bridge commits native weather/life
journals and its sidecar state atomically, records a hash-chained operation
journal, supports idempotent retry, backup, resume and combined replay, and
rejects source mutation or native advancement outside the bridge.

The adapter binds native seed/bounds/climate to G01; native trees to copied
G47 plant records; native actor IDs/time/alive state to L02/L59; and native
climate/resource observations to M03/M48 habitats. Completed public native
`give` and `speak` receipts create L02 directional relationship evidence.
Native actors are represented as non-reproductive residents because UW10W does
not expose reproductive roles; care/mortality are not fabricated. M7 disease
remains disabled. Detailed mappings and limitations are in
`docs/LIVING_WORLD_BRIDGE_REPORT.md`.

Focused bridge evidence: `4 passed in 20.61s`; combined bridge/foundation
smoke: `6 passed in 24.39s`; integrated life plus foundation review:
`21 passed, 3 subtests passed in 15.76s`; py_compile and `npm run lint` passed.
The correctly configured full repository run passed `534 tests and 355
subtests in 738.52s`. An earlier shell-local environment assignment caused
two scaffold setup errors; the rerun exported `UNDERWORLD_CORE` and passed.

---

# Current foundation review - 23 October 2026

Reviewed the latest other-agent G01/G47, L02/L59 and M03/M48 additions.
Fixed ten reproduced defects: mass units/minimum soil depth, unchecked care
receipts/conflicting retries, incorrect adult function, partial error writes,
checkpoint overwrites, unspent plant nutrients, care replay double-spending,
and the generation-order check that ignored its input.
See docs/FOUNDATIONS_CODE_REVIEW.md for evidence, fixes and compatibility.

Final targeted verification: 76 tests + 3 subtests passed in 25.36s.
All 11 historical source seals and previous integrated production code match.
This review did not rerun the slow full repository suite. Earlier 512-test
claims below are historical other-agent evidence, not current review results.

New numeric data identifiers: g01.2 and g47.2. Old JSON is not silently
rescaled; use archived matching sources. Saves now refuse existing paths.
The foundation models remain isolated JSON experiments, not native-world
integration. Proposals are not authenticated physical receipts. Full social,
ecological, reproductive and long-horizon scientific gates remain unproved.
Original review snapshot: artifacts/foundations_review_original.zip.
Final tests: artifacts/foundations_review_verified_checks.log.
Historical integrity: artifacts/foundations_review_integrity.json.
Existing worlds, Phase 9 failure and unrelated setup changes are untouched.

---

# Current: integrated inhabitants profile - 23 October 2026

## Alice specifications 01–03 foundation slices — October 23, 2026

The supplied Alice environmental, lifecycle and microorganism specifications
now have ordered additive foundations and continuation slices. Alice 01 G0–G3 is implemented in
`underworld/world_generation_g01.py`; Alice 02 L0–L4 is implemented in
`underworld/lifecycle_l02.py`; Alice 03 M0–M3 is implemented in
`underworld/micro_ecology_m03.py`. The ordered cross-stage smoke generates a
G01 soil/plant-litter manifest, feeds that substrate into M03 microbial ecology,
then registers an L02 species and mature individuals. Focused ordered checks
pass. G4–G7, L5–L9 and M4–M8 continuation sidecars are also implemented and the
extended smoke passes G01 → G47 → M03 → M48 → L02 → L59. Disease remains
explicitly disabled. These are sidecars and do not replace native/storage
authority or alter existing worlds. Viewer and live-world integration remain
deferred.

See [ordered foundation report](ALICE_01_02_03_FOUNDATIONS_REPORT.md).

Final repository verification after all three specification continuations:
`512 passed, 352 subtests passed in 728.39s` with
`UNDERWORLD_CORE=build/underworld_core.exe`.
The new ordered foundation group itself is 26/26. A prior full run had two
transient unrelated Windows isolation failures; the final rerun passed.

---

Implemented ALICE-LIFE-1 in life_store.py/life_affect.py. It connects UW10W
weather/exposure/shelter, the single F0-F5 mood/memory engine, and F6-F11
private social modules to native execution. Start with LIFE_INTEGRATION_REPORT.md
and the prospectively written LIFE_INTEGRATION_PROTOCOL.md.

Five held-out seeds pass bounded native-help/directional-trust, native-signal
acquisition (100%; shuffled/frozen 0%), gratitude reciprocation and persistence
probes. Acquired recovery preferences affect choices in two contexts (5/5).
F6 repair/ranking and F7 ambiguity checks also include explicitly synthetic
mechanism evidence. Do not call those complete native social acceptance gates.

F8 real rest reduces fatigue, but useful learned strategy selection is NOT
established; the improvement gate remains unpassed. Full F12 is not achieved.
Other F10 emotions lack grounded prerequisites. Historical H-series UW9 worlds
and vocabularies are preserved separately; there is no UW9-to-UW10W migration.
Native signal learning here starts with new private associations.

All inhabitants in five closed four-person worlds reached 30/90/180 seconds;
20/20 survived, 224 completed actions, no rejection, all actors scheduled.
An eight-person world reached 90 seconds, 8/8 survived, 22 completed actions.
Source unchanged, backups equal and fresh-process replay passed for every run.
Raw evidence: artifacts/life_heldout_20261023.json, life_recovery_heldout.json,
life_continuity_heldout.json. Actual worlds/backups remain under data/life-*.

CLI: scripts/life.py new/attach/run/save/replay/inspect. Use NEW paths to enroll
compatible existing F5/world copies. Run uses absolute simulated horizons and
a default 600-second wall budget. No resets/refills/rescues. Quotas remain.
Viewer: python -m underworld.life_viewer --db PATH --port 8781 (read-only).
Browser inspected; diagnostics loaded, favicon 404 only. Viewing never runs AI.
All 11 historical source seals match (artifacts/life_historical_integrity.json).
Full regression log: artifacts/life_full_suite.log; record its actual outcome.
Previous handoff bytes: HANDOFF_PRE_LIFE_INTEGRATION.md. Earlier sections below
are historical. Failed Phase 9 and unrelated OpenCode/package changes preserved.

Final validation: 465 Python tests + 352 subtests passed in 944.78s;
all 4 native checks passed in 0.38s. See docs/LIFE_VALIDATION.md and raw logs.

---

# Current review: F6–F12 bounded additions — 23 October 2026

Reviewed the other agent's additions and fixed execution, persistence and
measurement bugs. **Full F12 acceptance is not established.** These UW9
sidecars do not yet connect UW10W weather, F0–F5 affect/mood/memory, H-series
communication, or F12 proposals to the live action scheduler. F6–F11 scientific
gates remain pending. Preserve all earlier evidence and source registrations.

Read [F12 code review](F12_CODE_REVIEW.md) for fixes, commands, evidence
and the remaining integration work. Six new cases reproduced pre-fix bugs;
75 focused checks pass. The corrected continuous test reached 90 simulated
seconds in 162.978 wall seconds, with 4/4 healthy in both branches and matching
native states. This demonstrates isolation, not a survival benefit from F12.
Actual databases remain in data/f12-review-20261023-90s/; use new paths for reruns.
The F9 handshake is authored feedback, not verified native signal delivery.

Use the new `record-native` F12 command for native-journal-verified regulation
outcomes. Legacy guided/social/value evidence is still caller-supplied.
All 11 historical registrations match; the frozen native loader was restored
and optional custom-build resolution moved to underworld/native_paths.py.
The exact pre-review handoff is HANDOFF_PRE_F12_REVIEW.md. Earlier sections
below are historical and retain their original claims and dates.

Validation follow-up: full run 456 tests + 343 subtests passed; standalone
native executable checks failed because the invocation omitted the documented
MinGW runtime PATH. With that PATH, all affected checks plus F6-F12 and code
audit passed: 87 tests + 21 subtests in 18.22s. Full logs and limits are in
docs/F12_CODE_REVIEW.md and artifacts/f12_review_final_followup.log.

---

# 22 October 2026 — F8 durable regulation slice started

F9, F10, F11 and F12 bounded slices are now implemented additively. F9 provides
private per-agent emotional signal associations learned from public feedback;
F10 provides prerequisite-gated social/self-evaluative states; F11 separates
declared values from evidence-acquired preferences and revisable commitments;
F12 connects all four overlays to one copied native SQLite world with a single
bounded operation journal, current-observation validation, proposal-only
selection, backup/resume/replay and a final all-path smoke test. These are
implementation/integration results, not claims that the later scientific gates
passed. Native scheduler integration, viewer wiring, humanlike language or
emotion, and indefinite lifelong evaluation remain deferred.

Read [F9 slice](F9_COMMUNICATION_SLICE.md),
[F10 slice](F10_SOCIAL_EMOTIONS_SLICE.md),
[F11 slice](F11_IDENTITY_VALUES_SLICE.md), and
[F12 integration](F12_INTEGRATION_SLICE.md).

---

F8 now has an additive pure learner and copy-only SQLite overlay. It proposes
finite strategies (`rest`, moving to safety, requesting help, reconsidering an
uncertain interpretation, and switching a failing plan), filters unsafe
proposals during danger, and learns context-specific efficacy only from the
inhabitant's own observations plus native-shaped result receipts. Efficacy,
uncertainty, failure streaks, elapsed time, supplied cost and burden changes are
bounded and persisted; a completed receipt without observed relief is not a free
stress reset. Focused pure/durable checks pass, including current-native
validation, idempotence, copy-only backup and fresh-process replay. The
prospective F8 comparison gate, native scheduler behavior and viewer integration
remain deferred.

The complete repository suite passes when the existing native-core executable
is supplied (`UNDERWORLD_CORE=build/underworld_core.exe`): 448 tests and 352
subtests in the final run. A prior run had two transient Windows isolation
failures in unrelated pre-existing Phase 7 tests; both passed when rerun
individually and the next full run passed. An unconfigured attempt still stops
at the scaffold setup because `UNDERWORLD_CORE` is absent.

Read [F8 slice](F8_REGULATION_SLICE.md) and [F8 report](F8_REGULATION_REPORT.md).

## Connected-world survival check — October 23, 2026

`scripts/f12_survival_check.py` now runs matched integrated/control branches
with F6 and F7 stores chained into F12, then native stabilization. Over 90
simulated seconds with the four-person `living-world.toml` configuration, the
integrated branch kept 4/4 inhabitants alive at minimum health 1.0, completed
4 survival goals with 0 blocked goals, and matched the native-only control's
native state hash exactly. Source bytes stayed unchanged. F6 replay matched 2
operations, F7 replay matched 7, and F12 replay matched 71. F9 feedback changed
the receiver association; F10 pride prerequisites and F11 survival preference/
summary evidence were retained. This verifies sidecar connection and native
isolation, not causal survival improvement: F8-F11 proposals were not fed into
the native scheduler.

See [F12 survival check](F12_SURVIVAL_CHECK.md) and
`artifacts/f12_survival_90s.json`.

---

# 22 October 2026 — F7 durable understanding slice started

F6's additive durable relationship overlay now has directional native-shaped
event ingestion, bounded evidence, idempotent operations, copy-only attachment,
backup/resume/replay, visible-candidate helper ranking, and a public-offer-based
task-response receipt path. The focused F6/F7 checks pass. F7 starts with a
directional public-observation estimator for another inhabitant's possible needs,
goals and affect, with confidence, uncertainty, provenance and correction. It
rejects private target state and ignores operator labels. Neither stage claims
the full prospective held-out gate or native scheduler integration yet.

F7 now also has a copy-only durable inference overlay with strict current-native
observation checks, public-only envelopes, directional observer-target state,
bounded provenance, idempotent operations and fresh-process replay. Focused F7
checks pass. The overlay now derives a conservative public envelope from the
current native snapshot using only visible geometry/resource/shelter kinds and
public social-report edges. The prospective F7 study, native scheduler behavior
and viewer integration remain deferred.

Read [F6 report](F6_RELATIONSHIPS_REPORT.md),
[F7 slice](F7_UNDERSTANDING_SLICE.md), and
[F7 durable report](F7_UNDERSTANDING_REPORT.md). Earlier F5 results remain below.

---

# 22 October 2026 — F6 relationship slice started

F5 remains verified and frozen. F6 now has an additive bounded relationship
estimator with directional familiarity, trust, reliability, attachment and
uncertainty derived only from strict witnessed event records. Helper ranking is
deterministic and native feasibility remains authoritative. Five F6 unit tests
pass, including directional isolation, repair after negative evidence, bounded
helper choice and rejection of private target state. The native helper-choice,
durable overlay, save/resume and held-out multi-seed F6 gates are not yet run.

Read [the F6 slice](RELATIONSHIPS_F6_SLICE.md). Earlier F5 results remain below.

---

# 22 October 2026 — F5 emotional memory verified

F5 passes all gates on five held-out seeds using 59 frozen source files. Relevant
caution 5/5, unrelated 0/5, correction after safe evidence 5/5. The unchanged F4
baseline succeeds equally on these probes. Private memory retains at most 32
salient/recent links per person; current belief changes without rewriting events.

Independent audit verifies 65 F5 saves plus five source worlds; 2,040 main actions
and all 45 probes complete. No rejection/failure or material refill. Five fresh
mid-conditioning resumes match. Fresh 6 F5 + 5 F4 + 7 emotion + 28 weather tests
pass. Final static inventory: 185 Python files. Historical research/source seals
remain unchanged; Phase9 remains failed and excluded from policies.

A new copy continues the existing four-person life from 1,800 through 2,100 to
2,400 simulated seconds, all health 1, cursor 1,080→1,490. One of 410 completed
choices uses acquired memory to enter shelter where the old F4 estimate would
not select the same alternative. No survival benefit is claimed. Actual food/
water accounting closes; no forcing/reset/refill. Fresh-process continuation of
the 2,100s backup matches exactly. Execution windows: 417.007 wall seconds before
replay; confirmation: 1,430.662 seconds. Failed development 2 and all audit/tool
fixes remain documented with original evidence and source snapshots.

[Results](MEMORY_F5_REPORT.md) · [Operations](MEMORY_F5_OPERATIONS.md) ·
[Failures](MEMORY_F5_DEVELOPMENT_NOTES.md). F6 remains deferred. Earlier entries
below retain their historical scope.

---

# 22 October 2026 - F4 mood and temperament verified

F4 implements persistent declared initial temperament and a single slow mood/stress
component, separate from immediate affect and body values. Five untouched seeds
pass the unchanged55-file prospective protocol;25 native saves independently
replay/audit and2175 assigned native actions complete without rejection.
Cold120s stress balanced.440/sensitive.714; after warm210s, thermal0/harmful
active episodes0 but stress.264/.465; after warm900s,.0057/.0262. Physical heads
match across balanced/sensitive/disabled controls. This is configured temperament,
not learned traits, self-regulation, natural population generalization or improved survival.

New5 F4,7 legacy emotion and28 weather checks pass. Actual Edge desktop/mobile
observer checks pass. All nine older source registrations match; Phase9 still
verifies3439files/4sources/advance:false. No native/release/dependency changes.

F4 attaches only to a NEW backup copy, preserving old learning/history/body state.
A four-person copy progresses1200->1500->1800sim seconds, all health1; source
world remains unchanged. Cursor550->1080;530 completed new policy actions,
529 authored survival and1 reused learned cue;0 extra mood-threshold choices.
Food4.9+ingested3.1=8kg; water10.85+ingested5.15=16kg, no forcing/refill/reset.
Fresh-process backup continuation matches exactly. Progression250.785wall seconds
excludes post-window replay; primary confirmation1017.282s/audit66.768s.

See [F4 report](MOOD_F4_REPORT.md), [operations](MOOD_F4_OPERATIONS.md) and HANDOFF.md.
F5 and later remain outside this milestone. Prior entries below retain their scope.

---

# 22 October 2026 - F0-F3 emotion milestone verified

Opt-in copied UW10W/ALICE-WEATHER-2 saves now have private affect, bodily signals,
appraisal, learned threat/safety expectations and atomic/replayable cognition.
Five held-out seeds pass;60 native probes complete;105 actual saves independently
replay/audit. Learned safety choice5/5 vs0/5 in each frozen/disconnected/disabled
control; harmless avoidance0/5, safe reversal5/5. Prospective44-file seal unchanged.

Original335 Python +4 native, new7 emotion and28 weather checks pass. Existing
G/H/gap/weather source pins and Phase9's3439 evidence files/failed result remain
unchanged. No copied upstream code or new service/dependency/model. Actual Edge
3D observer/private evidence panel checks pass at desktop and mobile widths.

Supplementary four-person life reaches1200sim seconds, all health1,550 completed
AUTHORED actions, no learned contributions, rejections, fallback, forcing or refills.
Food5.8kg+ingested2.2=8; water12.8+ingested3.2=16. Fresh-process300->600 save/resume
matches exactly. Progression130.958wall seconds includes assigned physical setup
and excludes post-window replay checks; confirmation887.396wall seconds.

Development2's failed reversal and exact matching source archive retained; native
rounded9.9C to10, so it was the wrong cue. Corrected fixture before confirmation;
no learner/threshold change. F4-F12, broader affect-driven attention/regulation,
relationships and combined H-learning/communication/weather profile remain unvalidated.
Read [emotion report](EMOTION_REPORT.md), [operations](EMOTION_OPERATIONS.md) and HANDOFF.md.

---

# 22 October 2026 - W0-W6 opt-in weather validated

Persistent native weather, four fictional seasons, exposure proxies and real
material-built shelters are implemented in a separate UW10W runtime. All seven
registered bounded gates pass across three held-out conditions; native-save audit
recomputes actual protection, health, work, resource accounting and replay.
Known roofs reached in1.25sim seconds; after real assigned ingredient collection,
authored reactive construction+protection took14.25s. Four people physically share
one capacity4 roof; overflowing occupants receive no protection.

28weather checks plus the original335Python and4native checks pass. Real Edge
desktop/mobile read-only 3D observer checks pass. One continuously saved four-person
life reached2400sim seconds (one accelerated year), all alive/health1, no resets,
regeneration or weather forcing;481.164wall seconds after134sim seconds of explicit
physical setup. Food3.45kg/water9kg remain, with exact ingestion/resource closure.

Three failed sharing development candidates are retained; authored priorities and
scheduler frame lengths were corrected BEFORE untouched confirmation. Weather
forcing's one-tick expiry bug was fixed and its failure retained. An additional
unchanged existing utility-policy control confirms outside exposure under matched
conditions; it is labeled supplementary after primary registration.

Original G/H/gap/Phase9 sources, old worlds and build/living-d are unchanged.
Weather requires NEW worlds and matching native/source contracts; no migration.
Weather decisions are authored, not learned intelligence. Rain collection, storms,
real thermoregulation, developmental weather integration, unknown-material bootstrap,
multi-seed year-long survival and indefinite operation remain unproven/deferred.
Read [weather report](WEATHER_SEASONS_REPORT.md) and [operations](WEATHER_OPERATIONS.md).
Earlier entries below retain their original study scope.

---

# 22 October 2026 - H0-H5 adaptive gap profile verified

A separate opt-in profile repairs the measured H1 online reach/outcome failure,
adds durable need-driven plans, stale/depleted-source handling, private
category/location symbol reuse and context-triggered physical teaching.
Five held-out seeds: nearby acquisition 30/30 vs unchanged legacy online 0/30;
unreachable transfer attempts 0/30 vs frozen 30/30; remote water acquisition
and thirst relief 5/5 vs muted/scrambled/whole-message controls 0/5 each.
Native-grounded teaching updates 10 vs muted 0. Independent native-save audit
and all historical G/H0-H5 source registrations pass. 335 Python tests and four
native checks pass; real Edge desktop/mobile evidence-panel checks pass.

One continuous four-person life reached 1806 simulated seconds (418.850 wall
seconds after physical warm-up), all alive/health 1, 168 completed relief goals,
no replenishment, resets, models or operator interventions. Matched continuation
controls both completed 28 further goals: no survival superiority is established.
Source pins, body accounting, archive/fresh-process resume and scheduler retries
are verified. Original worlds and failed Phase9 result remain unchanged.

This closes bounded implementation gaps. Teaching choice, factorization, needs,
motor routing and sharing remain authored. Learned grammar/conversation,
learned teaching/request intentions, arbitrary feature transfer, semantic
calibration and indefinite/multi-seed long survival remain unachieved.
Read [gap report](DEVELOPMENTAL_GAP_REPORT.md),
[prospective protocol](DEVELOPMENTAL_GAP_PROTOCOL.md) and
[operations](DEVELOPMENTAL_GAP_OPERATIONS.md). Earlier entries below are preserved
as historical evidence and describe their original study boundaries.

---

# 21 October 2026 - H5 bounded symbol sequences and operator evidence

H5's prospective native reuse gate and independent audit pass: learned sequences
complete 30/30 held-out references versus 6/30 whole-message lookup,6/30 muted,
6/30 first-symbol and 4/30 second-symbol controls, across five confirmation seeds.
The encoder's category/mass factorization, teaching scaffold and overlap rule
are authored. Private symbol meanings come from native observation; this does
not demonstrate discovered syntax, conversation or autonomous language emergence.

The separate read-only operator panel displays actual signals, uncertain feature
hypotheses/counts, source IDs, native responses and distinct teaching, learned,
authored-decision, random-tie and protective-fallback counters. Real Edge desktop/
mobile checks pass, including refresh, privacy boundaries, safe text display,
missing-evidence handling and refusal of write requests.

317 Python tests and four native checks pass; two additional epoch-continuity
checks also pass. Pending messages/teaching survive archive and resume once in
fresh processes. Study 342.164wall seconds; longest 93sim seconds, all four alive/
health 1,300new completed native requests, zero rejections/models. These brief
counterfactual reference branches are not unattended-survival evidence.

Original G/H0-H4 registrations/worlds/reports and failed Phase9 evidence are
preserved. Phase9 independently verifies 3439files and retains advance:false;
its learner remains outside live policies. Earlier H1 online and G husbandry
failures and the original rejected H3 gate remain failed. Long survival, location
composition, autonomous requests/teaching, calibrated semantic confidence and
unscaffolded grammar remain unestablished. No release/version/executable change,
neural training, reproduction, new speech engine or true3D.

Read [H5 results and limitations](DEVELOPMENTAL_H5_REPORT.md),
[operations](DEVELOPMENTAL_H5_OPERATIONS.md),
[prospective protocol](DEVELOPMENTAL_H5_PROTOCOL.md) and [handoff](../HANDOFF.md).
Earlier records below are historical; their deferred H5 notes are superseded
only by this narrowly measured implementation. Initial import/routing/fixture
failures and development traces remain retained separately.

---

# 21 October 2026 - H4 bounded native integration

H4 communication and engineered need-policy gates pass independently: 10/10
remote-water goals enabled, 5/10 muted, 0/10 scrambled; identity alone never
provides a location. Five depleted-source cases stop without invalid gathering.
The separate own-need scheduler completes nine native drink goals versus zero
under prediction ablation. 304 Python tests and four native checks pass.
Original G/H0-H3 sources/evidence/worlds remain unchanged; Phase9's 3439-file
audit still retains its failed outcome and its learner is excluded from live policy.

This is authored scout/task integration and an engineered need scheduler, not
autonomous scouting or language emergence. Transmitted learned requests, general
exploration, stale-report trust, long unattended survival and H5 remain deferred.
An entire scout circuit is not one atomic restartable transaction. Primitive and
learning updates retain tested recovery. Initial H4 eating-duration and return-
normalization failures are recorded; prior H1 online/G husbandry failures remain.
No release label, packaged H4 UI/executable, neural training, reproduction or true 3D.

See [H4 report](DEVELOPMENTAL_H4_REPORT.md),
[operations](DEVELOPMENTAL_H4_OPERATIONS.md), and [handoff](../HANDOFF.md).
Earlier records below are historical; earlier deferred H4 notes are superseded
only by these scoped new results.

---

# 21 October 2026 - native developmental integration

GitHub main through d54a007 is integrated and reviewed. The original dictionary-
only H3 gate is not accepted. A separately preregistered native replacement now
passes: newcomer, post-interference retention and authored repair each 60/60,
versus 19/60 untrained and 17/60 unrepaired. Native receipt/private-proof audit,
287 Python tests and four native checks pass. Original G/H1/H2 source pins and
historical evidence are restored, not repinned; Phase9's 3439-file audit retains
its failed result and its learner remains outside live autonomous policies.

H3 remains scaffolded research: assigned tasks, authored demonstrations, count-
based learning, explicit retention protection and tie-triggered physical repair.
H4/H5, six-animal expansion, autonomous teaching/grammar, longer unattended
survival, neural training, reproduction and true 3D remain deferred. The incoming
Node world imitation was replaced with a launcher for the native application.
The first native H3 setup attempt failed at an occupied station; its log/worlds
are retained. The H1 online-adaptation counterexample and G husbandry failures
remain failures. Existing worlds are not reset or replenished.

See [integration results and remaining limits](H3_INTEGRATION_REVIEW.md),
[operations](DEVELOPMENTAL_OPERATIONS.md), and [current handoff](../HANDOFF.md).
The earlier status/evidence below is retained as its historical record.

---

# Milestone G - 21 October 2026

Application **0.14.0 / stabilization/5** adds bounded authored pen construction,
private source-linked care tests, observed-source routing and verified history
rotation/portable epoch backups. Native UW9/DB10/checkpoint9 laws are unchanged.
Read [G report](LIVING_WORLD_G_REPORT.md), [operations](INTEGRATED_WORLD_OPERATIONS.md)
and [prospective protocol](PHASE_G_INTEGRATION.md).

Both held-out seeds and both arms reach 300 continuous simulated seconds, all
four inhabitants alive, with zero material balance errors and matching replay.
Assigned tool/feed/water/food/rest goals complete in both seeds. Pen completion
remains partial: seed2521 stops at an observed occupied site; seed2549 is active
at cutoff. Tending is blocked when its target is not observed in seed2521.
Development's complete empty pen does not establish held-out reliability.

Pure knowledge injection no longer drains ecology events; non-culture recipients
work without a present flag. Every managed inhabitant now faces the model-off
desktop task guard. Source links, pending requests and controller anchors survive
bounded archival; missing/corrupt archives fail closed.

Verification passes239 Python tests and four native checks, packaged save/archive
interchange, both read-only viewers and the Bash launcher. All43 registered
files remain unchanged. Independent Phase9 audit verifies3439 files and retains
advance=false. See artifacts/living_world_g_delivery_audit.json.

Remaining: reliable integrated pen completion, animal capture, arbitrary pen
topology, autonomous teaching/goal formation, long-term husbandry, indefinite
receipt/knowledge retention and A's global model budgets. CARE plant-food/egg
claims lack general acquisition beyond carried stock. Models remain off; no
neural training, reproduction, speech or true3D is added. Phase9 stays sealed,
failed and outside live policies. Use a new G save; old F saves require
build/runtime-before-milestone-g-20261021. Final checks, continuous extension and
package evidence are detailed in the G report. The same seed2521 assigned life
reaches537 simulated seconds within240.516 additional wall seconds; all four
humans survive but both animals die. Sustained husbandry is not demonstrated.
Older entries below are historical.

---

# Milestone F � 21 October 2026

Application **0.13.0**, native UW9/DB10/checkpoint 9 unchanged. Explicit new-world
knowledge profiles, private guided operator injection, own-lesson native testing
and separate source counts are implemented. Read [F report](LIVING_WORLD_F_REPORT.md),
[operations](KNOWLEDGE_OPERATIONS.md) and [protocol](PHASE_F_KNOWLEDGE.md).

Both held-out randomized apparatus cases pass: false lessons physically fail;
the recipient tests, pays to write, and a second reproduces after actual reading.
The isolated third stays unknown. Each world runs 49.8 continuous simulated seconds,
in 20.099/16.804 wall seconds in the final source repeat, including fresh-process
parity checks (shared-host timing; original 12.329/12.394 seconds). Execution is
an authored laboratory driver with zero model/fallback calls, not autonomous teaching.

Verification: 219 Python tests plus four native checks; the final F-specific
checks and retained-lesson ablation guard also pass. Independent Phase 9 audit
verifies 3439 files and keeps advance=false.

Old E worlds require build/runtime-before-milestone-f-20261021; no migration/reset.
Profiles do not erase authored E recipes or pretrained facts. E teach_procedure/pen
planning remain unsupported. Desktop teaching remains read-only; explicit CLI
intervention is available between controller runs. G integration, bounded archival,
long-term husbandry and A global model budgets remain incomplete. Phase 9 remains
failed, sealed and outside live policies. Older entries below are historical.

---

# Milestone E — 2026-10-21

Application **0.12.0 / stabilization/4** adds explicitly assigned hierarchical
production/care tasks, bounded recovery, survival preemption and own native
receipt-linked source preference/procedures. Native UW9/DB10/checkpoint 9 laws
are unchanged. Read [E report](LIVING_WORLD_E_REPORT.md),
[operations](PLANNING_OPERATIONS.md) and [evaluation correction](PHASE_E_EVALUATION_AMENDMENT_1.md).

Corrected confirmation seeds 1329/1449 start each arm from matching native
checkpoints and verify actual utility activity. Every hierarchical mode completes
6/6 feasible task goals. Native terminal failures across all cases are 8 authored,
8 episodic-only, 2 adaptive and 5 model-assisted; unavailable/blocked tasks stay
unmet. Four real model calls add 21.686 wall seconds without a completion benefit.
Receipt-derived source preference changes later choices but can be stale/slower.
The original invalid inactive-utility comparison remains retained and disclosed.
The separate broken-tool supplement succeeds in 8/8 task cases across two new
confirmation seeds, with real native scrap/replacement and exact replay.

Final software verification: **209 Python tests (315.240 s)**, **four native
checks**, static/syntax checks, packaged task/desktop guard, save interchange and
both read-only UIs pass. One finite one-human production world runs 120 continuous
simulated seconds / 32.879 primary wall seconds. Fresh-process continuation from
30 seconds matches native state and eight memory/controller tables exactly.
The independent sealed Phase 9 audit still returns advance=false.

Source/controller pins change; old worlds require their preserved full runtime
at build/runtime-before-milestone-e-20261021 or their earlier exact archive.
There is no automatic migration/reset. The new profile retains four humans/two
animals, but confirmations are smaller controlled cases. F knowledge workflows
and G integrated demonstration remain next; global model budgets, general goal
formation, pen planning/teaching, long-term archival/husbandry and prior deferred
features remain incomplete. Older sections below are historical evidence.

---

# Edible-food execution repair — 2026-10-21

The persistent authored executor now consumes carried plant food/eggs, accepts
smaller portions, gathers visible finite forage and rechecks freshness. Native
validation, ingestion-based full-goal credit, retries and the sealed Phase 9
gate remain unchanged. Read [the repair report](FOOD_EXECUTION_REPAIR.md) and
[protocol](FOOD_EXECUTION_PROTOCOL.md). General care/planning and other deferred
research features remain incomplete; this is not the whole of milestone E.

Separate confirmation completes 6/6 feasible full meals versus 0/6 with the
frozen previous executor, plus three partial egg portions. No native rejection
or failure occurs in those cases, and food/water/body balances close exactly.
One continuous durable world advances another 120 simulated seconds after its
declared setup in 25.792 primary wall seconds; a backup resumes 119 seconds in
17.396 wall seconds to identical native/controller/memory state, with replay.
The rebuilt executable passes source/save interoperability and both viewer pages.

Final verification passes **190 Python tests (231.412 s)** and **four native
checks**, with protected Phase 9 hashes matching. An earlier parallel isolation
test completion race and its retained failing run are explained in the repair
report; worker limits and successful-outcome/cleanup assertions are unchanged.

Use `artifacts/food_repair_*` evidence for this repair. The exact prior source
and executable are archived at `build/runtime-before-food-fix-20261021`; the
archived executable was verified against the old code-audit save. Existing
controller pins are not migrated/reset. The 20 October results below remain
historical evidence for their original runtime.

---

# Current code audit and desktop launcher — 2026-10-20

Application 0.11.1 adds verified executable/source launch paths and integration fixes, with native UW9/DB10/checkpoint 9 laws unchanged. Read [the audit report](CODE_AUDIT_REPORT.md) and [detailed README](../README.md). Current orchestration/controller pins differ from D; its exact prior runtime is archived locally and original evidence is retained. The model-off desktop can run through one Bash/CMD file or dist/UnderworldLab.exe; it never migrates/reset/refills an old save. Phase 9 remains sealed and failed.

Final verification: **183 Python tests** (229.709 s inside unittest) and **four native checks** pass. Static checks are clean. The standalone executable reaches **120 continuous simulated seconds / 169.582 wall seconds**, completes four human drink goals through 15 native actions, retains all six bodies alive at health 1.0, and passes replay. Its complete native head equals the original final D 120-second head (`da68713042375015e7fc88ba50f863072b4da1416620232215b3ada187837c90`), demonstrating unchanged native behavior for this case. Separate reduced-PATH smoke checks prove executable/source/executable save continuation and packaged backup/replay. Both packaged UI pages pass read-only/asset/privacy checks with no JavaScript errors.

The D and older measurements below are historical. Audit verification and packaged smoke evidence use separate code_audit_* artifacts.

---

# Living-world Milestone D — current scope, 2026-10-20

D adds an opt-in native animal/food ecology profile: two species, finite forage, authored local behavior, real feeding/trough use, persistent familiarity, physical pens/gates, reserve-funded eggs and conservative food aging/storage. **UW9 / DB10 / checkpoint 9 / stabilization/3**, package 0.11.0; use `build/living-d` and `config/living-world-d.toml`. No migration or reset of C/study worlds. See [D contract](PHASE_D_ECOLOGY.md) and [D report](LIVING_WORLD_D_REPORT.md) for measured acceptance and limitations.

Breeding and fuel/heat-coupled cooking remain explicitly deferred. Dietary energy and waste are abstract mass reservoirs, not a biological or thermal metabolism model. Human care procedures are externally assigned; autonomous care planning is E. The A recurring/global model-budget gate remains incomplete, so validation is model-off. Phase 9's failed gate and learner exclusion remain unchanged.

The final build passes **176 Python tests** (243.105 s inside unittest) and **four native checks**. D's four-person/two-animal world reaches **120 continuous simulated seconds / 163.338 primary wall seconds**; its backup at 30 seconds resumes another 90 seconds in a fresh process in **119.440 wall seconds**, measured separately. Complete native state, all eight memory/controller tables, and run/branch identities match. Four human drink goals complete through 15 accepted/completed native actions with no rejection/failure; no human eating goal becomes urgent in this window. All six bodies end alive at health 1.0. Animals perform 67 drinking and 40 forage transfers and lay one 0.06 kg reserve-funded egg quantity; the 120-second forage intake is by the grazer, while the separate 300-second development regression verifies both species actually forage. Food/water/forage regeneration is zero, tree growth adds an explicitly accounted 0.6 kg boundary biomass, and no body/resources are reset. This is bounded continuity, not sustained husbandry or ecosystem survival.

The C and earlier sections below are historical measurements under their own pinned runtime.

---

# Living-world Milestone C — crafting/construction verified within bounded scope — 2026-10-20

Milestone B was independently rechecked: its 142 Python tests and 4 native checks passed, but additional review found defects in growth capping, inventory restoration, viewer lifecycle refresh and entity-quota handling, initial stone placement and remote harvest anchors. Milestone C corrects those and adds native recipes, tools, persistent construction work, storage, trough/fence/gate mechanics and an explicitly assigned physical production demonstration. See [the current audit/report](LIVING_WORLD_C_REPORT.md) and [contract](PHASE_C_CRAFTING.md).

Current runtime: **UW8 / DB9 / checkpoint schema 8 / stabilization/3**. Old UW6/DB7 and UW7/DB8 worlds are preserved and require their original full source/runtime; no migration or reset is performed. Use the `UNDERWORLD_BUILD=build/living-c` launch commands in [HANDOFF.md](../HANDOFF.md). Native format validation rejects accidentally loading the old root build with current Python sources.

Milestone A's model-off wrapper works; its requested recurring/fair/global model budgeting is **not implemented** by the prior handoff. The old lifetime call limit remains. Model-enabled A acceptance and isolated-supervisor integration are not claimed. General autonomous production planning is still Milestone E; animal behavior is Milestone D. Current C verification: **160 Python tests and 4 native checks passed**, followed by **26 crafting/viewer checks**. The 21-action production chain completed in **55.6 simulated / 7.543 wall seconds** with fresh-process construction parity. One four-person world reached **120 continuous simulated / 107.250 primary wall seconds**, completing four drink goals through 15 native actions without rejection. Fresh-process continuation matched native state, eight memory/controller tables and world/branch identities. All runs were model-off. Independent Phase 9 audit verified 3439 retained files; its gate is still false.

The following stabilization and A/B sections retain historical measurements. They are not reruns under the C laws/build.

The opt-in persistent prerequisite executor is implemented and evaluated. The failed Phase 9 study remains unchanged and its learner stays outside live autonomous policies. Its previous status is preserved in [PHASE9_STATUS.md](PHASE9_STATUS.md).

Read the [stabilization report](STABILIZATION_REPORT.md), [operations/handoff guide](STABILIZATION_OPERATIONS.md), [original protocol](STABILIZATION_PROTOCOL.md) and disclosed [fixture](STABILIZATION_AMENDMENT_1.md)/[navigation](STABILIZATION_AMENDMENT_2.md) amendments.

## Fresh-cohort outcomes

| Arm | Feasible goals completed | Missed feasible | Native submission rejections | Completed actions | Calls / provider failures | Median case wall s |
|---|---:|---:|---:|---:|---|---:|
| utility | 24/24 | 0 | 0 | 300 | 0 / 0 | 8.867 |
| legacy_model | 0/24 | 24 | 0 | 0 | 15 / 3 | 26.228 |
| stable_authored | 24/24 | 0 | 0 | 138 | 0 / 0 | 12.280 |
| stable_model | 24/24 | 0 | 0 | 127 | 15 / 4 | 29.946 |

The final cohort used seeds 808,909,1001 with carried food, gathering, unavailable food, depleted targets and interrupted plans. Feasible goals exclude genuinely unavailable/depleted food; needs, scarcity and all action outcomes remain recorded. Generated JSON/plans, submitted/accepted requests, completed actions and achieved ingestion are distinct stages. These are selected-inhabitant scenario results, not a general population reliability guarantee.

The first partial attempt had an invalid competitor fixture. The second valid-fixture attempt exposed a real occupied-approach defect and missed water. Both remain preserved as failures. The repaired controller was tested on a new cohort with unchanged thresholds, not repeatedly tuned against the original held-out set. Route selection and prerequisite execution are authored, even for a model-selected goal.

## Continuous operation and verification

| Arm | Actual continuous simulated s | Primary wall s | Alive | Fresh-process and recorded-request parity |
|---|---:|---:|---|---|
| stable_authored | 1200 | 127.707 | True | True |
| stable_model | 1200 | 166.808 | True | True |

Finite food/water, regeneration zero, no body reset or silent replenishment. Save/resume at 120 seconds preserved source-pinned goals, inference budgets, navigation/schedules, native state and memories. Exact actual horizons, cutoffs, primary wall time and separate recorded-command parity costs are in the report. These are not 24-hour or long-term sustainability claims.

Historical pre-expansion stabilization verification passed: **True**. Ran 139 tests in 160.319s. Native checks and complete subprocess evidence: [stabilization_checks.json](../artifacts/stabilization_checks.json). Protected Phase 9 file hashes match: **True**; its independent original audit is retained separately. Those original native/durable runtime identities and validator semantics applied to that historical evaluation; the living-world expansion explicitly changes compatibility and adds validators.

## Handoff and remaining limits

Use `python -m underworld.stabilization init/attach/run/status` or the living-world wrapper as documented. This is an explicit opt-in scheduler handoff; no existing Phase 8/9 world was silently switched or reset. The viewer can attach read-only. The legacy viewer time controller and Phase 7 supervisor do not automatically drive the new executor; its model calls use separate audited counters.

Crowd layouts, arbitrary cargo rearrangement/complex tasks, unavailable-water combinations, long-term supply and full-day operation remain outside this evidence. The host-side controller is not a newly verified AppContainer service. Native hashes and controller-journal checks are separate; journals and requests have finite quotas. No neural training, reproduction, speech, true 3D, consciousness, general intelligence or civilization-emergence claim was added. Phase 9's failed advancement gate was not changed.

## Milestone A checks

- `.venv/Scripts/python.exe -m py_compile underworld/__main__.py underworld/stabilization.py underworld/observer.py`: passed.
- `.venv/Scripts/python.exe -m unittest tests.test_stabilization`: passed, 17 tests.
- `.venv/Scripts/python.exe -m underworld living-world --help`: passed.
- Model-off smoke initialized `data/living-world-smoke/run.sqlite`, ran 2 simulated seconds, matched replay, saved `checkpoint.sqlite`, and resumed another 2 simulated seconds; both runs reached their targets.
- Observer state smoke reported `controller.active=stabilization` and the selected controller budget.
- `.venv/Scripts/python.exe -m unittest tests.test_scaffold tests.test_stabilization`: blocked by missing `UNDERWORLD_CORE` in `tests.test_scaffold.CoreTests`; stabilization tests still passed independently. No scaffold-suite pass is claimed until the native core path is supplied.

See [LIVING_WORLD_PLAN.md](LIVING_WORLD_PLAN.md) and [HANDOFF.md](../HANDOFF.md) for the dependency order and next acceptance check.

## Milestone B checks

- `"/c/mingw64/bin/mingw32-make.exe" -C build -j2`: passed.
- `./build/underworld_native_tests.exe`: passed, including tree lifecycle, competing harvesters, placement, growth and UW6 rejection.
- `./build/underworld_thermal_tests.exe`: passed.
- `.venv/Scripts/python.exe -m unittest tests.test_phase_b_trees`: passed, 3 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase1.MechanicsTests`: passed, 8 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase2.BodySenseTests`: passed, 8 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase5 tests.test_phase6`: passed, 26 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_phase7 tests.test_phase8 tests.test_phase9`: passed, 36 tests.
- `.venv/Scripts/python.exe -m unittest tests.test_stabilization`: passed, 17 tests.
- `UNDERWORLD_CORE="build/underworld_core.exe" .venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`: passed, 142 tests in 173.584s.
- `node --check underworld/web/scene.js && node --check underworld/web/viewer.js && node --check underworld/web/observer.js`: passed.
- Living-world CLI smoke initialized `data/living-world-b-smoke/run.sqlite` from the new config, ran 2 simulated seconds with replay parity, saved `checkpoint.sqlite`, resumed another 2 simulated seconds, and reported trees/stone through the observer state.

No full-day ecosystem run or model-enabled tree planner is claimed. The native tree actions are available to validated callers; autonomous tree/crafting planning is deferred to later milestones.
