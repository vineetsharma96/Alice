# H5 operations

H5 is opt-in source research, not a replacement for the G executable or existing
world policies. Do not run training on a scored confirmation database or an old
inhabitant save. Existing G/H0–H4 worlds keep their original runtime contracts.
The sealed failed Phase9 learner remains outside every live policy.

From the repository in PowerShell, use the existing native build:

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe scripts/learner.py sequence-init --db data/my-h5.sqlite --seed 47
.venv/Scripts/python.exe scripts/learner.py sequence-status --db data/my-h5.sqlite
.venv/Scripts/python.exe -m underworld.learning_panel --db data/my-h5.sqlite --port 8775
```

Open http://127.0.0.1:8775/ locally. The panel is an independent, read-only operator
view; the original viewer and continuous world runner are unchanged. A newly
created cohort correctly has no learned meanings. To inspect actual learned
behavior, point the panel at `data/h5-confirmation-20261021/10103-learned.sqlite`.
Never change a scored research save. Source mismatch requires its original source,
not re-pinning or bypassing its contract. No package installation is needed for
the Python panel. Browser verification uses the existing Playwright/Edge setup.

In Git Bash on Windows, the equivalent runtime selection is:

```bash
export PATH="/c/mingw64/bin:$PATH"
export UNDERWORLD_BUILD="$(pwd)/build/living-d"
.venv/Scripts/python.exe -m underworld.learning_panel --db data/my-h5.sqlite --port 8775
```

Channel operations use explicit IDs for recovery:

```powershell
.venv/Scripts/python.exe scripts/learner.py sequence-encode --db data/my-h5.sqlite --agent agent-1 --target resource-1 --coin
.venv/Scripts/python.exe scripts/learner.py sequence-send --db data/my-h5.sqlite --agent agent-1 --message-id example-1 --text 's00 s01'
```

Use the actual privately encoded result for a referential task. The second command
above merely demonstrates the physical channel with operator-supplied IDs; it
does not teach their meanings. Retrying the **same message ID and text** reconciles
the reserved/submitted native action exactly once. A different text with that ID
is refused. If another action changed the head before submission, recovery stops
explicitly. Do not assign a new ID to hide an unknown outcome. Do not blindly
repeat a whole teaching circuit after a crash.

For grounded teaching, first gather real carried material, move the speaker into
deposit reach, and use `sequence-begin --listener agent-2 --attention-id lesson-1
--alternatives ID...`. Make exactly one native .001kg deposit into a visible
alternative, then send the actual encoded message. `sequence-learn --listener
agent-2 --agent agent-1 --attention-id lesson-1` updates private intersections.
Only the recipient's before/after observations and native delivery can ground
the association. The study script contains a complete accounted physical scaffold.

`sequence-reference --listener agent-2 --agent agent-1 --alternatives ID...
--after-seq N` returns a **selection**, not a completed inspection or achieved
goal. Execute and score the native action separately. `--sequence-mode whole`
uses whole-message lookup; `muted` ignores speech. `--coin` is explicit and must
not be used during frozen evaluation. Production, hearing, interpretation,
completed actions and externally scored goals are different evidence layers.

Reproduce in **new, unused** paths; evidence outputs refuse overwrite:

```powershell
.venv/Scripts/python.exe scripts/composition_study.py run --development --directory data/h5-new-development --output artifacts/h5-new-development.json
.venv/Scripts/python.exe scripts/composition_study.py run --directory data/h5-new-confirmation --output artifacts/h5-new-confirmation.json
.venv/Scripts/python.exe scripts/composition_audit.py --study artifacts/h5-new-confirmation.json --output artifacts/h5-new-audit.json
.venv/Scripts/python.exe -m unittest tests.test_composition tests.test_learning_panel tests.test_learner_cli -v
node scripts/verify_learning_panel.mjs http://127.0.0.1:8775/ artifacts/h5-new-browser
```

The existing registration is frozen. `register` is for a separately named future
experiment before measuring its held-out seeds; never overwrite this study's
manifest after a source change. Actual local SQLite worlds are required for the
independent audit. Aggregate traces alone do not prove physical execution.

Save/resume uses the existing `storage.save` backup API; checkpoint names must be
unique. Check `sequence-status` before and after continuation. Primitive native
intents and H5 messages/learning updates have bounded reconciliation. The entire
authored curriculum is not atomic. Finish pending teaching/message work before
archiving with the existing developmental archive command. Epoch verification,
source-retention limits and missing-archive refusal remain active; never delete
archives or reset bodies to make a continuation pass.

The limits are stored in each private H5 contract: max2 tokens, one native second
per token, 16 production factors, 64 partner-token hypotheses, 64 whole-message
pairs, 16 evidence references per association and existing2048 records/person.
Quota exhaustion stops explicitly. Histories are not silently erased. External
operator resource additions, authored teaching, random tie breaks and protective
fallback counters remain separate from learned associations.
