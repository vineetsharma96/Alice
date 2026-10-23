# F6–F12 implementation review — 23 October 2026

The other agent's additions provide bounded, opt-in SQLite overlays. They do
**not establish completion of the master prompt's F6–F12 acceptance gates**.
This review fixes executable defects and evidence attribution while preserving
the earlier research registrations, worlds and failed Phase 9 result.

## Scope and preserved baseline

The reviewed additions cover relationships (F6), public inference (F7),
regulation (F8), private signal associations (F9), social appraisal (F10),
values/preferences (F11), and the F12 coordinator and survival runner.
Original pre-review bytes are retained in
`artifacts/f12_review_baseline_20261023.zip`, with SHA256 inventory in the
matching JSON file. The original `f12_survival_90s.json` and smoke results
remain historical evidence. Original focused tests passed 67 checks despite
the defects below; six added regression cases reproduced failures before fixes.

## Corrections

| Problem | Correction and check |
| --- | --- |
| Reusing an operation ID across different APIs could return an unrelated cached result. | Idempotence now checks both operation kind and request; cross-kind retries fail. |
| F12 attachment discarded existing durable F8 learning. | Copy-only attachment inherits and validates the enrolled F8 states and actor set. |
| Nested private states could name a different owner or run. | Validate F8–F11 owners/runs and bind persisted state to the F12 metadata. |
| F7 rejected valid JSON-round-tripped native observations because tuples became lists. | Compare canonical JSON; actual stale or altered observations still fail. |
| Malformed F8 receipts could raise an incidental KeyError. | Require every mandatory receipt field and return a validation error. |
| Nonfinite numbers inside nested candidate parameters escaped validation. | Validate nested values, finite numbers and bounded lists before scoring. |
| A receipt was scored against a whole survival segment, repeating the same needs change and elapsed time across multiple actions. | Reconstruct each owner's exact pre-submit and first terminal observations from the native journal; verify native receipts and final physical checkpoint. |
| A wall-limit stop was treated as completing the requested simulated duration. | Derive progress from actual native clocks and stop on incomplete segments; expose `duration_completed`. |
| Temporary survival worlds disappeared after measurement; existing results could be overwritten. | Retain source/control/overlay databases and manifest in a new folder; refuse existing result paths and folders. |
| Broad ValueError handling concealed invalid identity evidence. | Propagate validation failures; count actual successful/idempotent operations. |
| The communication fixture could be mistaken for real delivery or language emergence. | Label it guided authored feedback and explicitly report both native delivery and language gates as unverified. |
| A native-path convenience fix changed an earlier registered source file. | Restore `underworld/native.py` byte-for-byte; put optional path normalization in `underworld/native_paths.py`. All 11 historical registrations match. |

These changes preserve native action validation and rejection semantics.
They do not add a new policy or silently replenish bodies or resources.

## Verified native outcomes versus supplied evidence

For new UW9 regulation evidence, use:

```powershell
.venv/Scripts/python.exe scripts/integration_f12.py record-native NEW_F12.sqlite agent-1 REQUEST_ID --operation-id UNIQUE_ID
.venv/Scripts/python.exe scripts/integration_f12.py replay NEW_F12.sqlite
```

`record-native` only accepts an owner's recorded terminal native action. It
reconstructs its actual interval, records `native_journal_verified` provenance,
and verifies that interval again during F12 replay. Unknown/foreign requests,
altered recorded receipts, or a mismatched physical head fail. Reconstruction
is read-only and currently replays the native history; its cost grows with the
length of that history. It is not an indefinitely scalable telemetry service.

The older `observe-current --before/--outcome` API remains a guided input path
for replay compatibility. Its supplied historical evidence is not independently
authenticated. F9 feedback and F10/F11 social/value inputs likewise require
external grounding; schema validation alone does not prove an event occurred.

For a custom build directory, explicitly call
`underworld.native_paths.configure_build()` before loading the native module.
Relative `UNDERWORLD_BUILD` paths then resolve from the checkout without
modifying the historically registered loader.

## Actual bounded survival result

The corrected run used the existing four-inhabitant `living-world.toml`
configuration, two matched branches and three continuous 30-second segments.
It reached **90 simulated seconds in 162.978 wall-clock seconds**. Both branches
finished with **4/4 alive**, minimum health **1.0**, four completed survival
goals, zero blocked goals, 15 submitted/authored steps and zero fallback goals.
Their final native hashes match. The source stayed unchanged; native, F6, F7
and F12 replay checks passed, including a separate-process F12 replay.

Seven native action intervals were recorded by F8. Final mean hunger was 0.44,
thirst 0.02625 and fatigue 0.27356. These are remaining needs, not proof of
indefinite survival. Food/water regeneration is disabled; configured tree
growth remains enabled. No hidden reset or refill was introduced.

Evidence: `artifacts/f12_review_90s.json`, `f12_review_90s.log`, and
`f12_review_fresh_replay.json`. Actual SQLite worlds and a manifest remain in
`data/f12-review-20261023-90s/`. Reproduce in **new unused** paths:

```powershell
.venv/Scripts/python.exe scripts/f12_survival_check.py --seconds 90 --segment-seconds 30 --folder data/f12-review-new --output artifacts/f12-review-new.json
```

The unchanged stabilization executor performed every survival action. Matching
control trajectories establish native isolation, **not benefit from F12**.

## Validation and remaining work

The focused F6–F12 review suite passed **75 tests in 16.78 seconds**. The final
native-receipt tampering regression also passed after strengthening journal
validation. Earlier test-fixture setup failures and an interrupted full-suite
attempt remain in the logs; they are not counted as successful runs.
The full suite recorded **456 passed and 343 subtests passed in 544.15 seconds**.
Its 10 failures were the standalone native executable failing to load MinGW
runtime libraries (Windows status 3221225781 / 0xC0000135): one scene test and
nine invalid-argument subtests. That invocation set `UNDERWORLD_CORE` but omitted
the already documented toolchain PATH. The unchanged executable checks plus
all F6–F12 and code-audit checks then passed with the documented environment:
**87 tests and 21 subtests passed in 18.22 seconds**. The complete suite was not
rerun after correcting PATH; do not describe the first full run as green.

```powershell
$env:UNDERWORLD_CORE=(Resolve-Path build/underworld_core.exe).Path
$env:PATH='C:\mingw64\bin;'+$env:PATH
.venv/Scripts/python.exe -m pytest -q
```

Logs: `artifacts/f12_review_full_suite_final.log` and
`artifacts/f12_review_final_followup.log`. Final fresh-process F12 replay also
passes with native receipt validation enabled:
`artifacts/f12_review_final_fresh_replay.json`. The archive, original survival
artifacts, all 11 registrations and retained world hashes are checked in
`artifacts/f12_review_final_integrity.json`.

Static inspection parsed 215 Python files without syntax errors and found no
identical substantial production functions under the audit's comparison rule
(`artifacts/f12_review_connections.json`). This is not proof of absence of all
semantic duplication or every runtime defect.

The following remain open:

- F12 currently uses UW9. UW10W weather and the F0–F5 affect/mood/memory profile
  are not integrated; H-series private communication is not connected.
- F6/F7 stores can accompany F12 but are not causal inputs to its choice.
  `choose` produces proposals; the live scheduler does not execute them.
- F9's runner handshake supplies an authored meaning and feedback. It verifies
  private association updates, not native signal delivery or invented language.
- F6–F11 prospective development/held-out acceptance gates have not been
  established. The master prompt's full F12 integrated gate is therefore pending.
- Ninety seconds is a bounded continuity/isolation check. Long-horizon benefit,
  resource scarcity behavior, overhead scaling and causal ablations remain open.
- Viewer integration and independently grounded social/value evidence remain
  unfinished. Unrelated OpenCode/package setup changes were left untouched.

Next work should register the missing integration and evaluation protocol,
connect compatible profiles without rewriting old worlds, and establish each
stage's acceptance evidence before claiming full F12 completion.
