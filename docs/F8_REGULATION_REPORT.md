# F8 regulation implementation report

Implemented on October 22, 2026 as an additive pure-state and copy-only durable
overlay around `underworld/regulation_f8.py`.

## Delivered

- `scripts/regulation_f8.py` exposes `initial`, `choose`, and `outcome`.
- `initial OWNER RUN_ID` prints a deterministic JSON learner state.
- `choose OBSERVATION.json STATE.json CANDIDATES.json` loads three JSON files,
  calls `regulation.choose`, and prints the selected candidate or `null`.
- `outcome STATE.json BEFORE.json AFTER.json OUTCOME.json` loads four JSON
  files, calls `regulation.observe_outcome`, and prints deterministic JSON with
  both `evidence` and the updated `state`.
- `docs/F8_REGULATION_SLICE.md` documents the bounded scope, authored priors,
  learned efficacy, privacy/native-authority boundary, time/cost accounting,
  no-direct-stress-reset rule, and deferred native scheduler work.
- `underworld/regulation_store_f8.py` attaches only to a new copied SQLite
  world, keeps one state per actor, validates current native after snapshots,
  and supports operation idempotence, no-overwrite backups, resume and replay.
- `scripts/regulation_store_f8.py` exposes `attach`, `inspect`, `choose`,
  `record-current`, `record-outcome`, `save`, `resume`, and `replay`.

The pure CLI does not modify its input files or silently persist state. The
durable CLI writes only the explicitly supplied new F8 destination or copied
world and does not mutate the source world, native scheduler, or action state.

## Verification

Commands run from the repository root:

```text
python -m py_compile underworld/regulation_f8.py underworld/regulation_store_f8.py scripts/regulation_f8.py scripts/regulation_store_f8.py
```

Result: exit code `0`, no output.

A temporary-JSON smoke test was then run with an inline Python command that
created observation, state, candidates, before, after, and outcome files in a
temporary directory and invoked all three CLI commands. The command was:

```text
python scripts/regulation_f8.py initial alice run-1
python scripts/regulation_f8.py choose <observation.json> <state.json> <candidates.json>
python - <<'PY'
import json, subprocess, sys, tempfile
from pathlib import Path
root = Path.cwd()
cli = root / "scripts" / "regulation_f8.py"
def run(*args):
    result = subprocess.run([sys.executable, str(cli), *map(str, args)], cwd=root,
                            check=True, text=True, capture_output=True)
    return json.loads(result.stdout)
with tempfile.TemporaryDirectory() as raw:
    temp = Path(raw)
    state = run("initial", "alice", "run-1")
    before = {"agent_id":"alice","run_id":"run-1","tick":0,"dt_s":2.0,
              "own_state":{"alive":True,"present":True,
              "affect":{"stress":0.7,"fear":0.1},
              "body":{"health":1.0,"injury":0.0,"hunger":0.1,
                      "thirst":0.1,"fatigue":0.1},
              "weather":{"cold_burden":0.0,"wetness":0.0}}}
    after = json.loads(json.dumps(before))
    after["tick"] = 5
    after["own_state"]["affect"]["stress"] = 0.2
    candidates = [{"strategy":"rest","action_type":"rest",
                   "parameters":{"seconds":2.0},
                   "requested_duration":2.0,"estimated_cost_s":1.0}]
    outcome = {"request_id":"r1","status":"completed","action_type":"rest",
               "strategy":"rest","result":{},"estimated_cost_s":3.0}
    for name, value in {"state.json":state,"before.json":before,
                        "after.json":after,"candidates.json":candidates,
                        "outcome.json":outcome}.items():
        (temp / name).write_text(json.dumps(value), encoding="utf-8")
    selected = run("choose", temp/"before.json", temp/"state.json",
                   temp/"candidates.json")
    learned = run("outcome", temp/"state.json", temp/"before.json",
                   temp/"after.json", temp/"outcome.json")
    print({"initial_revision":state["revision"],
           "selected_strategy":selected["strategy"],
           "request_id":learned["evidence"]["request_id"],
           "elapsed_s":learned["evidence"]["elapsed_s"],
           "cost_s":learned["evidence"]["cost_s"],
           "final_revision":learned["state"]["revision"]})
PY
```

Observed result: `{'initial_revision': 0, 'selected_strategy': 'rest',
'request_id': 'r1', 'elapsed_s': 10.0, 'cost_s': 3.0, 'final_revision': 1}`.
The smoke process exited with code `0`; the updated state contained one
retained evidence record.

The focused pure-module regression command was:

```text
python -m pytest -q tests/test_regulation_f8.py
```

Result: `7 passed`.

The focused pure-plus-durable regression command was:

```text
python -m pytest -q tests/test_regulation_f8.py tests/test_regulation_store_f8.py
```

Result: `11 passed in 2.35s`.

The equivalent focused unittest command was:

```text
python -m unittest -q tests.test_regulation_f8 tests.test_regulation_store_f8
```

Result: `Ran 11 tests ... OK`.

The repository lint command was:

```text
npm run lint
```

Result: exit code `0`; `node --check server.js` completed without output.

The full repository suite was then run with the existing native-core test
environment supplied explicitly:

```text
UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe" python -m pytest -q
```

Result: `416 passed, 352 subtests passed in 601.85s`.

An initial unconfigured full-suite attempt stopped at the pre-existing
`tests/test_scaffold.py` setup because `UNDERWORLD_CORE` was absent; the
scaffold group passed independently once pointed at the existing
`build/underworld_core.exe` (`4 passed, 21 subtests`).

This report records pure and durable overlay checks. Native scheduler wiring,
viewer integration, automatic action dispatch, and the prospective multi-seed
F8 regulation gate are intentionally outside this slice.
