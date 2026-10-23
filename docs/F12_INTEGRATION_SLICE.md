# F12 bounded integrated-world slice

F12 connects the existing native SQLite world to the already implemented F8
regulation, F9 communication, F10 social-emotion, and F11 identity/values
overlays. The coordinator is implemented in `underworld/integration_f12.py`
and its JSON CLI is `scripts/integration_f12.py`.

## Contract

`attach(source, destination, declared_values=None)` makes a SQLite backup into
a **new** destination, verifies the native head, records the source SHA-256 and
native schema, and creates one independent JSON state for every native actor.
The source is opened read-only and its bytes are checked before and after
initialization.

The public operations are:

* `inspect` validates the native head and all four overlay states, then reports
  actor IDs, native tick/hash, overlay hash, operation count, source hash, and
  non-private per-actor overlay summaries.
* `observe_current` returns the current native own observation. With caller-
  supplied `before` and native-shaped `outcome`, it learns one F8 result against
  the current native observation; a strict F10 public/native event can also be
  attached to that current read. `observe_social` is the standalone F10 form.
* `send_signal`, `receive_signal`, and `feedback_signal` delegate to F9. They
  persist only the selected actor's F9 state and return delivery/feedback
  proposals or interpretations; no speech or native action is executed.
* `observe_social` delegates to F10's strict owner/run event API.
* `revise_identity` delegates to F11's strict event API or to
  `revise_summary` with a retained evidence ID.
* `choose` reads the current own native observation and can call any selected
  F8/F9/F10/F11 chooser. Every returned choice is marked `proposal_only`; the
  native tick and overlay state do not change.
* `save`, `resume`, and `replay` provide no-overwrite backup, validation, and
  fresh-process replay of the exact overlay operation chain.

Every mutating operation is in one `f12_operations` journal with a bounded
quota, operation ID, canonical command, before overlay hash, after overlay
hash, and result. Repeating an operation ID with the same request returns the
stored result idempotently. A conflicting request, foreign actor/run, private
or model transport field, malformed native-shaped result, or invalid current
observation fails closed.

## CLI examples

```text
python scripts/integration_f12.py attach SOURCE.sqlite F12.sqlite --declared-value care
python scripts/integration_f12.py inspect F12.sqlite
python scripts/integration_f12.py observe-current F12.sqlite agent-1
python scripts/integration_f12.py manifest F12.sqlite --wall-time-s 0.42
python scripts/integration_f12.py replay F12.sqlite
```

The `manifest` command reports simulated tick, caller-provided wall time,
operation count, overlay evidence counts, and explicit unverified gates.

## Authority and scope boundary

F12 exposes no direct native mutation. Native visibility, identity, time,
resource state, action validation, completion, failure, scheduling, and
physical state remain owned by `underworld.storage` and the native world. F8
receipts and F11 native/public outcomes are caller-supplied evidence; F9
tokens do not acquire inferred meaning without feedback; F10 states appear
only after their authored public prerequisites are linked.

This is an integration slice, not evidence that all F12 gates passed. It does
not claim autonomous scheduler integration, humanlike emotion or
communication, or an indefinite lifelong run. It also does not establish a
scientific multi-seed F12 gate.
