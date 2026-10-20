# Running Milestone E tasks

Use the current source build or a rebuilt executable. Native laws remain
UW9/DB10/checkpoint 9, but E controller source/version pins differ. Start an
explicitly NEW database; previous saves require their archived full runtime.
This interface assigns an authored procedure to one recipient. It is neither an
embodied teaching event nor an automatic grant of all recipes to everyone.

```powershell
$env:PATH='C:\mingw64\bin;'+$env:PATH
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe -m underworld living-world init --db data/e-manual/run.sqlite --config config/living-world-e.toml --calls 0
.venv/Scripts/python.exe -m underworld living-world task --db data/e-manual/run.sqlite --agent agent-1 --goal craft_tool
.venv/Scripts/python.exe -m underworld living-world run --db data/e-manual/run.sqlite --seconds 60 --wall-seconds 240
.venv/Scripts/python.exe -m underworld living-world status --db data/e-manual/run.sqlite
.venv/Scripts/python.exe -m underworld observe --db data/e-manual/run.sqlite --read-only
```

The E profile retains four humans and two animals in a finite 16 m region. Task
confirmation uses smaller one-human fixtures; arbitrary crowd/region success is
not guaranteed. Status reports actual task stage, origin, pending operator,
failures and final reason. If no supply or route is observed within bounds, a
task can block. No stock, tools or bodies are silently reset to make it pass.
Routine survival uses the unchanged authored executor and preempts between
native actions. There is only one writer, never a concurrent viewer scheduler.

Goals: `obtain_food`, `obtain_wood`, `craft_tool`, `make_planks`, `build_trough`,
`provide_water`, `tend_animal`, `inspect_problem`, `rest`. `build_pen` and
`teach_procedure` deliberately report unsupported rather than claiming success.

`--params` accepts a JSON object with only `target`, `mass_kg`, `position_m`.
Animal care and inspection require a target ID. Wood/food/water quantities are
bounded; trough construction can take an explicit visible/reachable position.
An omitted water target can trigger trough construction as a prerequisite.
Using Python avoids platform-specific command-line JSON quoting:

```python
from underworld.planning import assign
assign('data/e-manual/run.sqlite', 'agent-1', 'tend_animal', {'target':'animal-1'})
```

`living-world cancel-task --db PATH --agent agent-1` records cancellation. An
in-flight primitive still reaches its real native terminal receipt before task
cancellation is finalized. Completed physical effects are retained. A new task
cannot replace an active one. Save with the normal `save --name NAME --output
NEW_PATH` command; resume using `living-world run` on that compatible backup.

Modes: `--task-mode authored` supplies the authored decomposition without
experience bias; `episodic_only` retains episodes but disables source preference;
`adaptive` (default) uses own native failure evidence to rank sources and records
verified own procedures; `model_assisted` optionally chooses an authored next
operator. Primitive execution remains authored in every mode. The latter is an
explicit bounded inference opt-in, not a recurring autonomous model service.

For model assistance the installed pinned local server must be running at the
literal loopback endpoint. Pass `living-world run --task-model --endpoint
http://127.0.0.1:PORT ...`. Invalid replies, timeout and exhausted eligibility
fall back explicitly. Task attempts are limited to one per task, four per agent
for the save, and 60 simulated seconds between reservations. The global recurring
fairness gate from A is still open. Logical simulation time pauses during the
bounded call. E does not inherit AppContainer security claims.

The read-only 2D/3D viewers display the selected inhabitant's task, pending stage,
origin and last failure/outcome. Detailed status also exposes hypotheses,
procedure episode references, call counters and model latency as operator data.
Other agents' private records are not sent to the planner or model.

Reproduce bounded comparisons with `scripts/phase_e_eval.py --split development
--output NEW_DIRECTORY --evidence NEW_JSON`. `--split confirmation` uses the
registered confirmation seeds; historical reports must never be overwritten to
reinterpret a tuned result. `--local-model --arms authored adaptive
model_assisted` starts/stops an owned pinned server without downloads. Read
[the protocol](PHASE_E_PLANNING.md) before interpreting scores.
