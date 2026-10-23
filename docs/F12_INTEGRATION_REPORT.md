> Review update, 23 October 2026: this document retains the original bounded
> implementation result. See [F12 code review](F12_CODE_REVIEW.md) for corrected
> action attribution, retained worlds, current verification and missing gates.
> Full F12 is not established; the F9 handshake is guided feedback.

# F12 integration implementation report

Implemented as a bounded, copy-only coordinator around the native SQLite
world and the public APIs of F8--F11.

## Delivered

* `underworld/integration_f12.py` with rule ID `alice-integration-f12-1`.
* `scripts/integration_f12.py` with attach, inspect, observation, communication,
  social, identity, choose, save/resume/replay, and manifest commands.
* A single SQLite F12 journal with canonical operation requests, operation IDs,
  before/after overlay hashes, idempotent retry, and a 4096-operation quota.
* Source SHA-256, native schema, native head/tick, and independent per-actor
  F8/F9/F10/F11 initialization in the copied destination.
* `tests/test_integration_f12.py` covering copy-only attachment, current native
  observations, F8 current-snapshot learning, F9 send/receive/feedback, F10
  prerequisites, F11 acquired values and summaries, proposal-only choice,
  idempotence, privacy/foreign rejection, save/resume/replay, and an all-path
  smoke.

## Evaluation interpretation

The `manifest` helper reports the simulated native tick, optional wall time,
operation count, overlay evidence counts, and explicit unverified gates. F12
does not mutate the native world and therefore cannot by itself demonstrate
native action execution or scheduler behavior.

The implementation is intentionally not a full scientific F12 gate. The
following remain explicitly unverified: autonomous scheduler integration,
humanlike emotion or communication, an indefinite lifelong run, and a
scientific multi-seed F12 evaluation.

## Checks

Commands run from the repository root:

```text
python -m py_compile underworld/integration_f12.py scripts/integration_f12.py underworld/regulation_f8.py underworld/communication_f9.py underworld/social_emotions_f10.py underworld/identity_values_f11.py tests/test_integration_f12.py
```

Result: exit code `0`, no output.

```text
python -m pytest -q tests/test_integration_f12.py tests/test_regulation_f8.py tests/test_communication_f9.py tests/test_social_emotions_f10.py tests/test_identity_values_f11.py
```

Result: `39 passed in 4.43s`.

```text
python -m unittest -q tests.test_integration_f12 tests.test_regulation_f8 tests.test_communication_f9 tests.test_social_emotions_f10 tests.test_identity_values_f11
```

Result: `Ran 39 tests in 4.045s`; `OK`.

```text
npm run lint
```

Result: exit code `0`; `node --check server.js` completed without output.

The final repository-wide verification was run with the existing native core
test executable supplied:

```text
UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe" python -m pytest -q
```

Result: `448 passed, 352 subtests passed in 600.73s`.

The first full-suite attempt had two transient Windows isolation failures in the
pre-existing Phase 7 supervision tests. The affected tests passed when rerun
individually; the full suite then passed on the next run. These failures were
outside the F8-F12 files and did not involve the new overlays.
