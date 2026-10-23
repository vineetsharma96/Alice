# F8 emotional-regulation slice — 22 October 2026

F8 adds a small, bounded emotional-regulation overlay for one inhabitant's
proposals and outcome learning. The pure rules live in
`underworld/regulation_f8.py`; the copy-only SQLite coordinator is
`underworld/regulation_store_f8.py`; source-only JSON and durable-store CLIs
are `scripts/regulation_f8.py` and `scripts/regulation_store_f8.py`.

## Scope

The public API has three operations:

- `initial(owner, run_id)` creates an empty learner with five authored
  strategies (`rest`, `move_to_safety`, `request_help`, `reconsider`, and
  `switch_plan`) across five authored contexts (`calm`, `strained`, `danger`,
  `depleted`, and `uncertain`).
- `choose(observation, state, candidates)` classifies the inhabitant's own
  observation, rejects malformed/private inputs, filters unsafe proposals in
  danger, and returns one deterministic candidate or `None`. It does not
  change the state or observation.
- `observe_outcome(state, before, after, outcome)` learns one idempotent result
  from two own observations and a native-shaped receipt/result. It returns the
  retained evidence record, or `None` for a duplicate request ID.

The learner is bounded: five strategies, five contexts, at most 32 retained
evidence records, at most 32 candidates per choice, bounded IDs and bounded
durations/costs. State is ordinary copy-friendly Python data and can be
serialized as JSON.

The durable overlay initializes one independent learner per native actor in a
new copied SQLite world. It records only F8 state, operation IDs, before/after
state hashes and the own-observation/result command envelope. It supports
idempotent retry, no-overwrite backup, resume and fresh-process replay. The
source world is never modified.

## Authored priors versus learned efficacy

The finite strategy list, context thresholds, action contracts, danger safety
filter, initial efficacy value (`0.5`), initial uncertainty (`1.0`), scoring
weights, and outcome target formula are authored policy. They are not learned
personality, discovered goals, or a claim that regulation has emerged.

Only the per-strategy/per-context efficacy values, uncertainty, counters,
failure streaks, elapsed time, cost totals, and retained evidence change after
an accepted outcome. Efficacy updates are gradual: each new result has a
shrinking update rate, and a completed receipt alone is not enough to imply
success. Observed burden relief and danger resolution are included; observed
harm and unresolved danger reduce the score. Repeated failures affect later
selection through the learned value and uncertainty, but do not rewrite the
authored strategy set.

## Privacy and native authority

Inputs are limited to the inhabitant's own observation (`agent_id`, `run_id`,
time, and `own_state`) plus bounded candidate/action data and a native-shaped
result. Recursive validation rejects common private-state and transport escape
hatches such as other-agent state, target state, hidden/private fields, model
prompts, and secrets. A foreign owner or run is rejected.

Candidates are proposals, not executed actions. The CLI never owns a world,
database, scheduler, model, other-agent state, or native mutation capability.
Native visibility, reachability, resources, action validation, completion and
failure remain authoritative. A receipt/result is evidence supplied by the
caller; this slice does not fabricate one.

## Costs, time, and stress limits

Candidate `requested_duration` and `estimated_cost_s` are bounded proposal
metadata. Outcome `estimated_cost_s` is retained as the action cost. Elapsed
time is computed from the tick difference multiplied by the *before*
observation's `dt_s`, then accumulated in the matching strategy/context record.
Evidence records retain `elapsed_s`, `cost_s`, burden before/after, outcome
score, status, and failure streak.

F8 does not directly reset stress, fear, fatigue, injury, health, hunger,
thirst, or any other body/affect value. It cannot make an action happen and it
cannot declare a successful recovery. A later observation must contain the
actual changed own state, and the native-shaped receipt must report what the
authoritative action path returned.

## CLI

The CLI uses only JSON files for compound inputs and prints compact,
lexicographically sorted JSON. It does not write a state file; callers may
capture the output and pass the returned `state` object to a later command.

```text
python scripts/regulation_f8.py initial OWNER RUN_ID
python scripts/regulation_f8.py choose OBSERVATION.json STATE.json CANDIDATES.json
python scripts/regulation_f8.py outcome STATE.json BEFORE.json AFTER.json OUTCOME.json
```

`initial` prints the complete initial state. `choose` prints one candidate or
JSON `null`. `outcome` prints an object with `evidence` and the updated `state`;
`evidence` is JSON `null` when the request ID was already retained.

## Non-claims and deferred integration

This is the first bounded F8 implementation slice. It is durable and
copy-only, but it is not native scheduler integration, a viewer panel, or
automatic action dispatch. The durable CLI can choose from caller-provided
feasible proposals and record a caller-provided native result; it cannot make
an action happen. No claim is made about consciousness, general emotional
intelligence, autonomous therapy, clinical efficacy, or indefinite survival.
The prospective F8 gate still needs controlled regulation scenarios,
held-out comparisons, and explicit scheduler/viewer integration.
