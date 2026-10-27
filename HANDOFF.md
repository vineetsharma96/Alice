# Current Alice dashboard - 24 October 2026

The Windows executable/launcher now supports explicit integrated-life GUI
modes: `run.cmd --readonly --db ...` (read-only dashboard) and
`run.cmd --control --db ...` (paused single-writer control dashboard). The word
aliases `run.cmd readonly ...` and `run.cmd control ...` are also accepted.
`underworld.app` dispatches these modes for both source and packaged launches;
`life_viewer` and `life_control` open the browser by default, with
`--no-browser` available for headless use. `scripts/package_app.py` now bundles
the life/viewer hidden imports, weather extension and provenance files needed
by the packaged modes. The rebuilt executable was smoke-tested for both modes.

Launcher-focused verification: `7 passed in 7.84s`; py_compile, `npm run lint`
and `git diff --check` passed. Packaged `--control --help` and
`--readonly --help` passed, and temporary packaged servers returned the native
`alice.dashboard/1` packet in both modes. The post-launcher full pytest command
was started with the required five-minute limit and reached 23% without failure
output before timeout; the completed `534 tests and 355 subtests` run recorded
below predates these launcher-only changes.

---

The existing integrated-life observer is now a complete observer/control
dashboard at the same `life_control.py` URL. It reads one authoritative native
weather/life head and uses the existing writer lease and journal. The dashboard
provides persistent run/calendar/population status, shared 2D/3D observation,
selected-inhabitant inspection, carried inventory, evidence-backed mood
charts with tick-aligned mean/range and event markers, directed relationship graph, filtered event timeline, native weather
telemetry, guided weather overrides, Advanced JSON, copy/download, pause,
resume, one tick, bounded tick batches, run-until simulated time and safe
cancellation.

New UI/backend files: `underworld/web/dashboard.html`,
`underworld/web/dashboard.css`, `underworld/web/dashboard.js`,
`underworld/life_viewer.py` and extended `underworld/life_control.py`.
Dashboard telemetry is bounded to 240 retained operation/event records. Mood
traces use recorded stress/valence/arousal updates only; explanations state
when a cause is not recorded. Microbial counts, target-specific anger,
reproductive events and unsupported inventory metadata are explicitly marked
unavailable rather than guessed. See `docs/ALICE_DASHBOARD_REPORT.md`.

Focused verification: `5 passed in 9.13s` for life controls,
`17 passed in 51.46s` for integrated life, controls and the living-world bridge, py_compile,
`node --check underworld/web/dashboard.js`, `node --check underworld/web/scene.js`
and `npm run lint` passed. Browser verification confirmed speed selection,
pause/resume/cancel at safe boundaries, 2D/3D switching, Advanced JSON and a
clean loaded dashboard; screenshot:
`artifacts/dashboard_ui_smoke.png`. No commit or push was made.

The whole-tree check was then completed with the native runtime environment:
`export UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe"; python -m pytest -q`
passed `534 tests and 355 subtests in 738.52s`.

---

# Current living-world bridge - 24 October 2026

The six Alice foundation sidecars are now connected to an explicit copy-only
UW10W/ALICE-LIFE-1 bridge in `underworld/living_world_bridge.py`. The bridge
preserves native authority and writes native weather/life journals plus G01,
G47, L02, L59, M03 and M48 state in one transaction. It accepts a compatible
weather/F5 source or an already enrolled life copy, always requires a NEW
destination, and refuses native changes made outside the bridge.

CLI: `scripts/living_bridge.py attach/run/inspect/replay/save`. The default
biological clock is one simulated day per L02/L59 step; use
`--biological-step-s` for a bounded experiment. Native tree observations are
mapped to G47 copied plants, native actor identities/time/alive state bind L02
and L59, native climate drives G01/G47/M03/M48, and completed public native
`give`/`speak` receipts add L02 relationship evidence. No automatic
reproduction/care/mortality action is created; M7 disease remains disabled.

Focused bridge verification: 4 tests passed in 20.61s; combined foundation
smoke 6 passed in 24.39s; integrated life plus foundations review 21 passed
and 3 subtests passed in 15.76s; py_compile and `npm run lint` passed. The
correctly configured full repository run passed 534 tests and 355 subtests in
738.52s. The first attempt had 528 passed and 2 scaffold setup errors because
the shell-local `set UNDERWORLD_CORE=...` did not export the variable; the
rerun with `export` passed. See `docs/LIVING_WORLD_BRIDGE_REPORT.md`. No
commit or push was made.

---

# Fluctlight-style sidecar and live-session diagnosis - 25 October 2026

The existing `data/my-life.sqlite` was inspected after a long manual run. It
contains 3,322 life-policy operations at tick 17,774 / 4,443.5 simulated
seconds. The policy history is dominated by `rest / reduce_exposure` (2,159
baseline choices), followed by 570 supply-preparation choices, 261 drinks and
172 eats. This explains the reported stationary period: the current frozen
weather policy treats a completed shelter as a reason to rest, and its default
autonomous mode does not continue general wood/fiber work or animal care.

The native ecology also uses small finite animal reserves and consumes roughly
1,000,000 ug/s food plus 1,500,000 ug/s water. With the default 250,000,000 ug
food and 200,000,000 ug water reserves, an unreachable animal can become
deprived within minutes of simulated time. This is a native new-world profile
issue, not an age rule.

Added without modifying the frozen weather/life source:

- `underworld/fluctlight.py` — private observation-only knowledge, a seven-day
  teacher profile, health-adjusted ordinary lifespan projection, bounded
  survival teaching, and deterministic month/sun/moon/orbital/eclipses data.
- `scripts/fluctlight.py` — `bootstrap`, `observe`, `new`, and `calendar` CLI.
- `tests/test_fluctlight.py` — regression coverage.

Example:
`python scripts/fluctlight.py bootstrap --world data/my-life.sqlite --agent
agent-1 --output data/agent-1-fluctlight.json --role teacher`

The sidecar does not create a native actor or rewrite an existing save. Native
births, ageing, autonomous teaching, revised animal mortality, and lunar
physics still require a separately versioned new-world/runtime implementation.
Do not modify `underworld/weather_policy.py` in place: it is pinned by the
frozen F0-F3 registration and existing weather saves fail closed on source
drift.

Verification for this continuation: `14 passed in 7.39s` for focused policy,
fluctlight and control tests; `npm run lint` passed; py_compile passed;
`git diff --check` passed. The whole-tree pytest command was run with the
required native environment and five-minute limit, reached 47% without a
failure before timeout; the repository's recorded full suite takes about
11–12 minutes.

The control dashboard now also exposes an opt-in `time_dilation` setting with
`normal`, `fast`, and `sao_300y_3w` presets. The Alicization nominal ratio is
`300 * 365 / 21 = 5,214.2857x`. It changes wall-clock pacing only; native
ticks, physics, journals, and resource accounting remain serialized and are
not skipped. Focused time-dilation/control checks passed (`7 passed in 8.17s`),
as did `npm run lint`, py_compile, and `git diff --check`. This is not a claim
that the current computer can execute 300 native years in exactly three weeks.

## Phase 0 — ALICE-LIFE-2 contract freeze

Phase 0 began on 25 October 2026. `underworld/life_contracts.py` now defines
sealed shadow contracts for identity, private observation, memory, body needs
and affect traces. Every record has a profile/version envelope, owner/run/
branch identity, native tick and observation version, source event references,
provenance, privacy scope and canonical SHA-256 checksum. Validation rejects
unknown versions, unknown fields, invalid privacy/provenance combinations,
malformed ranges and checksum tampering.

The records are shadow-only: no existing `ALICE-LIFE-1` database, native
checkpoint, frozen registration or current `data/my-life.sqlite` was changed.
The contract specification is in `docs/PHASE0_CONTRACTS.md`; regression tests
are in `tests/test_phase0_contracts.py`. Focused verification passed:
`16 passed in 22.50s` for Phase 0, life controls and integrated life;
`npm run lint`, py_compile and `git diff --check` passed. The next step is
Phase 1 persistence in a new copy-only destination, after deciding the exact
identity/observation capture boundaries.

## Phase 1 — ALICE-LIFE-2 identity and observation persistence

Phase 1 started on 25 October 2026. `underworld/life_phase1.py` now enrolls a
native weather source or an existing ALICE-LIFE-1 copy into a NEW destination.
The source hash is checked before and after copying; an existing destination or
already-enrolled Phase-1 source is refused. The native world and its journals
remain authoritative and are not rewritten by sidecar capture.

The new destination receives `phase1_meta`, `phase1_identity`,
`phase1_observations` and `phase1_operations` tables. Attach persists one
sealed identity and one private native observation per selected actor. Identity
does not invent names or traits: `public_name` is the explicit native actor ID
and authored/self-model mappings start empty. `capture` persists later private
observations without advancing native time and is idempotent at the same
native state. `identities`, `observations`, `inspect`, `replay` and `save`
provide validated readback, bounded summaries, checksum verification and new
backups. CLI entry point: `scripts/life_phase1.py`.

The contract and boundary are documented in `docs/PHASE1_PERSISTENCE.md`;
regression coverage is in `tests/test_phase1_persistence.py`. Verification
passed: `16 passed in 17.00s` for Phase 0, Phase 1 and integrated-life tests;
`python -m py_compile`, `npm run lint` and `git diff --check` passed. The first
plain full-suite invocation reached `548 passed, 2 environment errors` because
`UNDERWORLD_CORE` was not set. The required native-runtime rerun passed
`550 tests and 355 subtests in 653.48s` with
`export UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe"; python -m pytest -q`.

## Phase 2 — ALICE-LIFE-2 private memory persistence

Phase 2 started on 26 October 2026. `underworld/life_phase2.py` now requires a
Phase-1 destination and creates a NEW copy with private memory sidecar tables.
It never infers memory from an operator projection or invents content. Each
written memory requires an enrolled owner, explicit content/kind/confidence/
salience/provenance and at least one reference to a persisted Phase-1 native
observation or its source event ID. Records use the Phase-0 sealed memory
contract and remain private.

Corrections are append-only: a replacement is a new memory with
`supersedes=<old-id>`, while explicit removal adds an `invalidated` event. The
old payload is never rewritten. `memory()` and `memories()` expose the sealed
record, effective validity and lifecycle event IDs. `replay()` verifies Phase 1,
memory checksums, source references, owners, privacy, correction links and
operation metadata. CLI entry point: `scripts/life_phase2.py`; boundary and
usage are documented in `docs/PHASE2_MEMORY_PERSISTENCE.md`.

Focused verification passed: `20 passed in 20.13s` for Phase 0, Phase 1,
Phase 2 and integrated-life tests. The first Phase-2 test attempt used a
temporary Python 3.14 runtime without the compiled weather extension; the
validated rerun used uv-managed Python 3.12.14, matching the repository native
extension. `python -m py_compile`, `npm run lint` and `git diff --check` passed.
The full native-runtime suite passed `554 tests and 355 subtests in 586.87s`:
`UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe" PYTHONPATH=. uv run --python 3.12.14 --with pytest --with pybind11 pytest -q`.

## Phase 3 — ALICE-LIFE-2 body-need persistence

Phase 3 started on 26 October 2026. `underworld/life_phase3.py` now requires a
Phase-2 destination and creates a NEW copy with native body-need snapshots.
Each sealed private/native `body_need` record stores hunger, thirst, fatigue,
health, alive, exact native tick/observation version and a reference to the
matching Phase-1 private observation. Native state remains authoritative for
action legality, resource transfer, health changes and death; Phase 3 creates
no survival action, mortality rule or inferred cause.

Later captures first append matching Phase-1 observations in the Phase-3 copy,
then append body snapshots without advancing native time. Repeated capture at
the same native state is idempotent. `body_need`, `body_needs`, `inspect`,
`replay` and `save` provide validated readback, bounded summaries, source/body
equality checks, tamper detection and copy-only backups. CLI entry point:
`scripts/life_phase3.py`; documentation is in
`docs/PHASE3_BODY_NEEDS.md`; regression coverage is in
`tests/test_phase3_body_needs.py`.

Focused verification passed: `24 passed in 24.84s` for Phase 0 through Phase 3
and integrated life; the Phase 3-only run passed `4 passed in 5.64s`.
`python -m py_compile`, `npm run lint` and `git diff --check` passed. The exact
plain `python -m pytest -q` command could not start in this Windows session
because the Microsoft Store Python alias returned `Permission denied`; the
repository's uv-managed Python 3.12.14 focused checks are the validated Phase
3 evidence. The prior native full suite remains the Phase 2 baseline; a new
full suite should be run when the system Python launcher is available.

## Phase 4 — ALICE-LIFE-2 affect and mood traces

Phase 4 started on 26 October 2026. `underworld/life_phase4.py` now requires a
Phase-3 destination and creates a NEW copy with private affect-trace records.
It records the integrated runtime's existing body signals, appraisal when
recorded, fast affect, slow mood, emotional-memory references, social changes
and last action influence. Missing appraisal is explicitly marked
`explanation_status=unavailable`; no hidden cause or intention is inferred and
no second affect engine is created.

Every trace is a sealed `affect_trace` with derived/private provenance and an
exact Phase-3 body source at the same native tick. Later captures append the
matching Phase-3 body/Phase-1 observation sidecars first and then append affect
traces without advancing native time. Repeated capture at the same native head
is idempotent. `affect_trace`, `affect_traces`, `inspect`, `replay` and `save`
provide validated readback, bounded summaries, source/tick checks, tamper
detection and copy-only backups. CLI entry point: `scripts/life_phase4.py`;
documentation is in `docs/PHASE4_AFFECT_TRACES.md`; regression coverage is in
`tests/test_phase4_affect_traces.py`.

Focused verification passed: `28 passed in 35.39s` for Phase 0 through Phase 4
and integrated life; the Phase 4-only run passed `4 passed in 8.27s`.
`python -m py_compile`, `npm run lint` and `git diff --check` passed. The exact
plain `python -m pytest -q` command again could not start because the Windows
Microsoft Store Python alias returned `Permission denied`; Phase 4 was
validated with uv-managed Python 3.12.14 matching the native extension. The
last completed native full suite is the Phase 2 baseline (`554 tests and 355
subtests`); no new full suite claim is made for Phase 4 within the five-minute
check limit.

## Phase 5 — ALICE-LIFE-2 unified lineage profile

Phase 5 started on 26 October 2026. In this ALICE-LIFE-2 persistence sequence,
Phase 5 is the unified coordinator rather than the repository's separate
thermal/material-model Phase 5. `underworld/life_phase5.py` requires a Phase-4
destination and creates a NEW copy with per-agent lineage snapshots. Each
snapshot binds, by stable ID and checksum, the Phase 1 identity and exact
private observation, Phase 2 memories sourced from that observation, the Phase
3 body need at the same tick, and the Phase 4 affect trace at the same tick.

The coordinator adds no sixth cognitive subsystem and creates no native truth.
It first runs the Phase 4 → Phase 3 → Phase 1 sidecar capture chain, then
appends a unified snapshot without advancing native time. Repeated capture at
the same native state is idempotent. `snapshot`, `snapshots`, `inspect`,
`replay` and `save` provide validated readback, bounded summaries, exact
cross-record lineage checks, tamper detection and copy-only backups. CLI entry
point: `scripts/life_phase5.py`; documentation is in
`docs/PHASE5_UNIFIED_PROFILE.md`; regression coverage is in
`tests/test_phase5_unified_profile.py`.

Focused verification passed: `32 passed in 46.59s` for Phase 0 through Phase 5
and integrated life; the Phase 5-only run passed `4 passed in 11.89s`.
`python -m py_compile`, `npm run lint` and `git diff --check` passed. The exact
plain `python -m pytest -q` command could not start because the Windows
Microsoft Store Python alias returned `Permission denied`; validated Phase 5
checks used uv-managed Python 3.12.14 matching the native extension. No new
full-suite claim is made within the five-minute check limit.

## Phase 6 — ALICE-LIFE-2 social and cultural provenance

Phase 6 started on 26 October 2026. In this ALICE-LIFE-2 persistence sequence,
`underworld/life_phase6.py` requires a Phase-5 destination and creates a NEW
copy with an append-only ledger for optional social events and explicitly
authored cultural artifacts. Supported event kinds are speech, gift, offer,
response, shared task, artifact read and departure. Events require enrolled
participants and Phase-1 observation/source-event references; no cooperation,
trust, native action or automatic scientific progress is forced.

Artifacts are private by default. `write_artifact` stores a bounded procedure,
book, report or tool with source references. Ordinary listing omits content; a
non-owner receives content only through `read_artifact`, which requires an
enrolled reader, source reference and records an `artifact_read` event. This is
modeled access, not omniscient telemetry. All records are checksummed and
`replay` validates Phase 1–5, source references, owners, participants, artifact
access and operation envelopes. CLI entry point: `scripts/life_phase6.py`;
documentation is in `docs/PHASE6_SOCIAL_CULTURE.md`; regression coverage is in
`tests/test_phase6_social_culture.py`.

Focused verification passed: `35 passed in 59.24s` for Phase 0 through Phase 6
and integrated life; the Phase 6-only run passed `3 passed in 8.75s`.
`python -m py_compile`, `npm run lint` and `git diff --check` passed. The exact
plain `python -m pytest -q` command could not start because the Windows
Microsoft Store Python alias returned `Permission denied`; Phase 6 focused
checks used uv-managed Python 3.12.14 matching the native extension. No full
suite claim is made for Phase 6 within the five-minute check limit.

---

# Active manual session - 23 October 2026

User requested manual control with no overall tick limit. Launcher:
underworld/life_control.py. Running at http://127.0.0.1:8782/, initially paused
at tick 360 (90 simulated seconds). Save: data/manual-control/world.sqlite,
a copy of life-dev61-v2.sqlite. Resume this save; do not reset it or start a
second writer. Run/Pause/Step 1 tick/One inhabitant turn are available.
Resume has no overall horizon; native integrity and journal quotas remain.
One control regression passed; live HTTP/paused status and rejected tokenless
POST verified. See docs/MANUAL_LIFE_CONTROL.md. Registered sources unchanged.

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

## Supplied Alice specifications 01–03 — foundation stages

On October 23, 2026 the first ordered foundations from the supplied
`Prompt/Alice_01_World_Generation_Soil_Minerals_Plants.md`,
`Alice_02_Love_Sex_Reproduction_Inheritance_Lifecycles.md` and
`Alice_03_ALIEN_Inspired_Microorganisms_Ecology.md` were implemented additively.
Alice 01 G0–G3 is `underworld/world_generation_g01.py`; Alice 02 L0–L4 is
`underworld/lifecycle_l02.py`; Alice 03 M0–M3 is
`underworld/micro_ecology_m03.py`. None modifies `storage.py`, native code,
existing worlds or F8–F12/life modules.

The ordered smoke generates a bounded G01 manifest, feeds its plant-litter/soil
data into an M03 microbial habitat, then constructs an L02 species and two
mature individuals. Focused ordered verification is 26 pytest/unittest tests,
plus clean py_compile. `npm run lint` passes. The full repository suite was not
rerun in this stage; prior current validation remains in the sections below.
`git diff --check` still has one unrelated pre-existing whitespace finding in
`tests/test_code_audit.py`. The final repository suite after all three supplied
specification continuations, with the existing native core, passed `512 tests
and 352 subtests in 728.39s`; an earlier run had two transient unrelated
Windows isolation failures, resolved on rerun. Later G4+,
L5+, M4+ and live native integration are not claimed.

Read `docs/ALICE_01_02_03_FOUNDATIONS_REPORT.md` and the three stage reports
before extending these modules. Do not migrate or overwrite existing saves.

Continuation slices are now present as additive modules: G4–G7 in
`underworld/plant_underground_g47.py`, L5–L9 in
`underworld/lifecycle_l59.py`, and M4–M8 in
`underworld/micro_ecology_m48.py`. The extended ordered smoke reaches
G01 → G47 → M03 → M48 → L02 → L59; M7 disease is explicitly disabled. Focused
continuation tests pass and no native/storage/existing-world code was changed.
Native scheduler/viewer coupling, prompt-01 G8–G10 autonomous work, and full
multi-generation/fermentation/disease scientific gates remain unclaimed.

---

Implemented ALICE-LIFE-1 in life_store.py/life_affect.py. It connects UW10W
weather/exposure/shelter, the single F0-F5 mood/memory engine, and F6-F11
private social modules to native execution. Start with docs/LIFE_INTEGRATION_REPORT.md
and the prospectively written docs/LIFE_INTEGRATION_PROTOCOL.md.

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
Full regression: 465 tests and 352 subtests passed in 944.78s; four native
checks passed in 0.38s. See docs/LIFE_VALIDATION.md and the retained raw logs.
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

Read [F12 code review](docs/F12_CODE_REVIEW.md) for fixes, commands, evidence
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

# Alice handoff: F5 completed

22 October 2026. F4 baseline16881c2 was pushed to origin/codex/mood-temperament
BEFORE F5 implementation. F5 branch: codex/emotional-memory. Exact previous F4
handoff: HANDOFF_PRE_F5_ARCHIVE.md. Read the master prompt F5 section, then
MEMORY_F5_REPORT.md, MEMORY_F5_OPERATIONS.md, MEMORY_F5_PROTOCOL.md and
MEMORY_F5_DEVELOPMENT_NOTES.md under docs/.

## Validated result

Five held-out seeds19201/19207/19213/19219/19231 pass every F5 gate; development53.
The59 files in artifacts/memory_f5_registration.json are frozen. Never edit or
re-register them against existing results. Original44 F0-F3/55 F4 source seals and
ten historical G/H/gap/weather/emotion/F4 registrations remain unchanged.

One F4 affect/appraisal update, then a private salience index into the factual
journal. At most32 links, divided among represented contexts; half each quota
retains salient links, half recent links. Retrieval uses exact own-perceived
weather/shelter context, salience, duration and180s simulated-age decay. Safe
experience revises the expectation without rewriting events. Support is a
heuristic, not a calibrated probability. Context classes, weights and routes are
authored; observations and learned values are acquired. No second mood engine.

Connected relevant caution5/5 (completed movement AND actual shelter), unrelated
0/5, corrected0/5 after safe evidence. Expectation-.883944->-.046018; retained
harm and factual journal stay unchanged. Frozen F5 encoding0/5 acquired caution.
Disconnected memory encodes but uses unchanged F4 choices, which perform equally
well on these probes. Frozen means F5 indexing only; the old F4 learner continues.
Do not claim F5 superiority, learned representations or general memory reasoning.

All45 probes and2040 assigned main-arm actions complete;0 native rejection or
failure. Main clock87.75->930.75s,843s conditioning per arm. Actual guided cold/
warm/finite feeding/rest are apparatus, not autonomous regulation. All survive,
paired physical histories match and ledgers close. Confirmation1430.662wall
seconds, at most2 independent seeds; maximum per-seed558.807s<600s. Identical
conditioning explains identical learned values across seeds; probes vary5-9C/rain.

Independent audits verify65 actual F5 saves+5 setup worlds, recompute salience/
retrieval/retention from native own observations, check factual prefixes and all
five fresh-process resumes. Successful audit windows sum334.624s (some overlap),
excluding failed attempt/reconciliation. Peak index17994bytes<24000, max32 links.
See artifacts/memory_f5_audit.json, memory_f5_summary.json and raw confirmation.
memory_f5_negative_audit.json rejects resealed index edits and journal-appraisal
rewrites on disposable copies while preserving the actual source save.

## Compatibility and continuing worlds

Copy-only ALICE-MEMORY-F5-1 enrollment accepts matching weather/F0-F3/F4 saves.
Default all native actors. Preserve bodies, learning, fast affect, mood, immutable
traits, episodes, policies, pending native actions and scheduler origin. F5 index
starts empty, with no fabricated retroactive history. Historical emotion/mood
tables remain inactive evidence. Write F5 through memory_store/memory.py only.
Source drift refuses, never repins/resets. Quotas10000cognitive/25000physical
remain. No UW9/H-language migration or combined H/weather capability is claimed.
Existing H learning/private vocabularies and their worlds remain preserved.

Original data/mood-f4-life.sqlite stays1800s, SHA256:
c3eac345940d52c613fc27003b95da446e0a5dd2bbe5c626a52ba88669b88d29.
Final NEW data/memory-f5-final-life.sqlite progresses1800->2100->2400s, all4health1.
Cursor1080->1490.410 new completed actions:67gather,63move,213rest,30eat,37drink.
409 authored weather choices;1 acquired-memory shelter move using authored routing.
Agent4 enters actual shelter; memory estimate-.333808 versus F4+.183936, which
would not meet the-.102947 caution threshold on that same observation. One
attributable choice is not evidence that the whole life survives because of F5.
Food3.4+ingested4.6=8kg; water9+ingested7=16kg, carried0. No forcing, refill,
material source, failure/fallback, body reset or scheduler restart. Private states
100814canonical bytes. Execution417.007wall seconds excludes post-window replay.

Fresh process continues a COPY of data/memory-f5-final-life-2100-backup.sqlite to
identical2400s native/private/policy hash/cursor1490 (133.451s before replay):
ac469c335b603974a4edc1498f9544d81c370a6a35577e7c529890ea5cb2f0bf.
Resume path:data/memory-f5-final-life-resume-check.sqlite. Independent source,
inherited-state, history-prefix and ledger proof:memory_f5_continuity_proof.json.
No autonomous simulation remains running after these bounded windows.

Read-only127.0.0.1:8780 serves the guided held-out
 data/memory-f5-confirmation/seed-19201/connected-corrected.sqlite.
Its current retrieval includes renewed cold AFTER the probe; use the recorded
pre-action prediction for the correction gate. Original8777/8778/8779 observers
remain untouched. Edge1440x900/390x844 checks pass3D/memory display/no errors or
overflow/paused native hash/POST405. Viewing never advances time.

## Run and check

From repository, matching sources; use unused backup/output paths:

```powershell
.venv/Scripts/python.exe scripts/memory.py inspect --db data/memory-f5-final-life.sqlite
.venv/Scripts/python.exe scripts/memory.py replay --db data/memory-f5-final-life.sqlite
.venv/Scripts/python.exe -m unittest discover -s memory_tests -v
.venv/Scripts/python.exe scripts/memory_audit.py --folder data/memory-f5-confirmation --output artifacts/NEW-memory-audit.json
```

Fresh6 F5+5 F4+7 emotion+28 weather=46 tests pass. Earlier335Python/4native result
is historical, not rerun. Final static inventory parses185Python files, without
claiming exhaustive dynamic coverage. Actual SQLite saves remain local in ignored
data/; exact source ZIPs, audit hashes, raw measurements and failures accompany code.
Native engine/version/dependencies remain unchanged. Phase9 stays failed and its
learner outside all live policies. No LLM fabrication, speech or reproduction.

## Retained failures and next stage

Development1 reporting-path error/partial world remain. Development2 FAILED
relevant caution/correction: support.197586, safe records globally displaced,
expectation stayed-1. Exact source/results and development-only
 data/memory-f5-life.sqlite at2100s remain. Never repin it to final source.
Four-slot retention draft failed a software assertion, not a native trial.
Draft audit136accepted/137completed is invalid; corrected native interception
measures137/137 for that probe. Historical registration-schema and tuple/JSON
reconciliation fixes are disclosed in development notes. None changes a gate.

F6 now includes the additive `underworld/relationship_store_f6.py` overlay and
focused tests. It provides copy-only attachment, directional state for every
actor pair, strict native-shaped social/receipt ingestion, bounded evidence,
idempotent operation hashes, backup/resume/replay, visible-candidate helper
ranking, and public-offer resolution for completed task responses. The full
prospective five-seed F6 gate and scheduler-integrated helper-choice study are
not claimed. Proximity is not trust.

F7 now includes additive `underworld/others_f7.py` and
`underworld/others_store_f7.py` with focused tests. It infers possible target
needs, goals and affect only from strict public cues and witnessed social
reports, with directional uncertainty/provenance and evidence correction. The
durable overlay is copy-only, checks the current native observation, rejects
private target state/operator labels, supports idempotent operations and
fresh-process replay, and does not alter native behavior. Its
`record_current_observation` path derives conservative cues from visible native
geometry/resources/shelters and public social edges rather than accepting an
operator-authored hidden-state claim. The prospective F7 study, scheduler and
viewer integration remain deferred. Current F5 memory
still covers only coarse weather/shelter and a bounded safety choice;
event-granularity invariance, indefinite journals, large populations, learned
regulation/traits, social emotions, emotional language and joint H/weather
integration remain unproven.

F8 now includes additive `underworld/regulation_f8.py` and
`underworld/regulation_store_f8.py`. The pure learner keeps five authored
regulation strategies across five contexts, chooses only caller-provided
feasible proposals, filters unsafe proposals in danger, and learns bounded
context-specific efficacy from own observations plus native-shaped receipts.
Elapsed time, supplied cost, burden change, danger resolution and repeated
failures are retained; completion alone does not zero stress or prove recovery.
The store is copy-only, initializes one state per actor, validates current
native after observations, supports idempotent operations, backup/resume and
fresh-process replay, and leaves native scheduling/action authority untouched.
Focused F8 pure/durable checks pass. The full repository suite also passes with
the existing native-core environment (`UNDERWORLD_CORE=build/underworld_core.exe`):
448 tests and 352 subtests. The prospective F8 held-out regulation gate, native
scheduler integration and viewer panel remain deferred.

F9 adds `underworld/communication_f9.py` with empty private per-agent signal
maps, arbitrary tokens, partner-specific uncertainty, public-feedback learning,
shuffled/unknown-partner controls and proposal-only assistance. F10 adds
`underworld/social_emotions_f10.py` with strict prerequisite gates for
gratitude, pride, guilt, embarrassment, envy and grief. F11 adds
`underworld/identity_values_f11.py` with separate declared values, acquired
preferences, revisable summaries and evidence-backed commitment proposals.
All three are bounded pure slices with focused tests; they do not claim
humanlike language, social morality or a full prospective gate.

F12 adds `underworld/integration_f12.py` and `scripts/integration_f12.py`. It
attaches F8-F11 to a NEW copy of a native SQLite world, initializes independent
per-actor state, validates current native observations, persists one bounded
hash-chained operation journal, supports idempotence and backup/resume/replay,
and returns proposal-only choices without advancing native time. The final F12
smoke exercises F8 outcome learning, F9 send/receive/feedback, F10 gated social
evidence and F11 value/summary revision in one copied world while preserving
source bytes and native tick. Focused F8-F12 checks pass. Native scheduler and
viewer integration, real-world automatic action dispatch, and the scientific
 multi-seed F12 gate remain deferred.

The connected-world survival check is implemented in
`scripts/f12_survival_check.py`. It chains F6 → F7 → F12 on a new copy, keeps a
matched native-only stabilization control, and records F8-F11 sidecar evidence
around actual native receipts without executing sidecar proposals. The October
23, 2026 90-second living-world run kept 4/4 inhabitants alive at health 1.0,
completed 4 survival goals with 0 blocked, matched the control native state
hash, preserved source bytes, and replayed F6 (2), F7 (7) and F12 (71)
operations. F9 feedback, F10 pride prerequisites and F11 acquired survival
preference/summary updates were retained. This demonstrates connected sidecars
and native isolation only; it does not claim survival benefit or native
scheduler use of F8-F11 choices.

Preserve unrelated package.json changes, .env.example, .nvmrc, .opencode/,
docs/OPENCODE.md, opencode.json, package-lock.json and scripts/start-tinyfish-mcp.*.
They are excluded from F5 staging/push; do not install/configure or modify them.
