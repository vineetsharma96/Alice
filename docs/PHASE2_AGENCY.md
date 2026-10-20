# Phase 2: bodies, senses and everyday agency

Implemented scope: eight abstract bodies in the supplied survival scene, needs and death, movement/gather/deposit/eat/drink/rest/inspect/speak, deterministic observation-only utility decisions, durable state and a local observer. These are authored engineering abstractions. There is no human biochemistry, language model, identity/episodic-memory system, training, teaching intervention, chemistry or 3D viewer.

## Body rules (authored, not physiological estimates)

Need values and health are dimensionless [0,1]. Higher hunger/thirst/fatigue is worse; higher health is better. Body initial values: hunger .35, thirst .40, fatigue .20, health 1, alive. All rates below apply per simulated second, independently of wall time.

| Process | Rule |
| --- | --- |
| Hunger | +.001/s, capped at 1 |
| Thirst | +.0015/s, capped at 1 |
| Fatigue | +.0008/s idle/other actions, +.0012/s while attempting movement; rest -.015/s, clamped [0,1] |
| Eat | Consume own food inventory at completion; hunger falls by 2 per kg, clamped at zero |
| Drink | Consume own water inventory at completion; thirst falls by 2 per kg, clamped at zero |
| Health damage | -.006/s for hunger >=.95, another -.006/s for thirst >=.95, another -.003/s for fatigue >=.99 |
| Health recovery | +.0005/s when all three needs are <.75 and no damage condition applies; capped at 1 |
| Death | Health reaches 0, alive becomes false, active unfinished action fails DEAD, one death event is recorded. Corpses remain solid, retain inventory/reservoirs and cannot act. No revival. |

Each tick applies environmental replenishment, executes actions, updates bodies, removes completed/failed pending actions and emits the tick event. Consumption takes effect on completion, then that tick's need drift is applied. Rest fatigue recovery applies to every tick of its pending duration, including the final tick. Rejected actions have no body/resource effect. An attempted colliding move still incurs the movement fatigue rate that tick. Health/body needs freeze on death. There is no metabolism, heat/energy coupling, excretion, realistic injury or reproduction model.

## Material accounting and recovery

Native quantities remain exact integer micrograms (1 kg = 1,000,000,000 ug). Food/drink move from own inventory to per-body **abstract ingested reservoirs**; consumption does not delete accounted mass. The ledger invariant per material is:

`initial mass + configured boundary sources = resource piles + inventories + ingested reservoirs`.

Dead actors retain these reservoirs. Ingested material is not claimed to be actual human tissue or biochemical mass. Inert material is never consumed. Bodies have a 2 kg inventory capacity; all gathered materials count. Existing Phase 1 body-disabled mechanics retain their previous transfer behavior.

Optional food and water replenishment are configured boundary sources in kg/s, each in [0,.01]. Each fixed step accumulates micrograms with a persisted fractional remainder, so source mass reconciles exactly on restart. Food growth is an authored source, not photosynthesis; water replenishment is an authored spring/boundary input, not created by a model or crafting action. Default survival runs disable both sources. Initial food/water may each be [0,1000] kg, allowing explicit scarcity controls; initial inert material remains 32 kg.

## Action schema extensions

The existing v1 ActionRequest fields/run/principal/version checks remain. `requested_duration` is seconds, rounded upward to complete physical ticks. One action per living actor. Existing movement, ownership, visibility, reach, stale/dedup checks and completion-time revalidation remain authoritative in C++.

| Type | Targets / parameters | Minimum duration and consequence |
| --- | --- | --- |
| move | No targets, `x_m`, `y_m` | Existing [0.1,60] s request; at most 1 m/s, swept collision/bounds checks |
| gather / deposit | One visible resource, `mass_kg` | >=1 s when bodies enabled; 1.5 m reach, availability checked again on completion; gather respects 2 kg capacity |
| eat | No targets, `mass_kg` in (0,1] | >=2 s; own food inventory only; no direct hidden-pile access |
| drink | No targets, `mass_kg` in (0,1] | >=1 s; own water inventory only |
| rest | No targets, empty parameters | >=1 s; fatigue recovers over actual simulated ticks |
| inspect | One visible entity, empty parameters | >=.2 s; rechecks visibility at completion; returns public ID/kind and exact pile mass in this coarse model, never another actor's needs/inventory |
| speak | No targets, `text` | >=1 s; nonempty UTF-8 text <=512 bytes; recipients are evaluated at completion |

CAPACITY_EXCEEDED and DEAD extend the existing error list. Results now carry actual `event_refs` and `observable_effects.description`. Inspection/transfer/consumption/speech references point to emitted engine events. Effects are receipts for this actor's own action; narrative content never edits physical state. The local observer resolves human-readable action types from that actor's actual decision journal. Material quantities are deliberately exposed as coarse resource measurements in Phase 2; instrument uncertainty is a later materials concern.

## Perception, audibility and privacy

Each observation is built natively from spatial cells, with 8 m Euclidean sight range. The central rock occludes a centre-to-centre line segment; the rock itself is visible as a target. Other actors do not occlude sight. There is no lighting-dependent visibility, field-of-view cone, partial silhouette visibility or diffraction model. These limits are explicit.

Own body values, position, inventory and pending-action status are available. Nearby actors expose public position/radius/alive state, **not** body needs, health amounts, inventories or ingested quantities. Operator snapshots are privileged and show all bodies; they are never input to the utility policy.

Speech is unverified data, not an engine fact. Living recipients within 6 m and an unobstructed rock segment receive text, speaker ID, delivery tick and the actual speech event sequence. Queues retain at most 16 reports per recipient and survive restart. Nothing is broadcast globally. Text is never parsed as executable code, a system role or a privileged command. A hostile spoken request for private memories remains plain report text. Private episodic memories do not exist until Phase 3; Phase 2 proves body/inventory redaction and rejection of invented privileged request fields, not a nonexistent memory implementation.

## Deterministic policy and persistence

`underworld/policy.py` receives **one Observation and that actor's bounded navigation dictionary**. It receives no World object, SQL connection, operator snapshot, other actor's private state or model tool. Its authored utility order consumes carried water/food when needs cross .5, rests for fatigue, maintains small carried supplies, and otherwise searches the public region. Movement planning uses only perceived solid geometry, with bounded grid search (1,024 expansions, local 12 m search) and a deterministic 16-waypoint exploration pattern. No hidden resource coordinates are supplied. It may collide or fail; failures are retained.

Policy cadence is 25 ticks (5 s in the default .2 s survival scene). It makes no LLM calls. Navigation waypoints are transient procedural state, not episodic memory, beliefs or learning. The controller owns separate dictionaries by agent ID. The policy never reads a report as a host instruction.

SQLite schema is now user_version=2; native checkpoint magic UW2, laws bodies-2. Existing build-specific UW1 databases cannot be silently loaded/migrated; preserve them and their original build. New Phase 1 body-disabled regression runs remain supported under the current build. No existing user database was overwritten in this work.

Each one-tick transaction commits the complete native body/action/message/reservoir state, updated per-agent navigation state, decisions/results, events and policy-frame journal together. The complete head hash includes the native checkpoint and nonempty policy state. Named checkpoints/backups include both. Replay restores initial state and applies **recorded actions and navigation frames**, without running the policy again. Tests patch the policy to fail if called during replay and still reproduce the state hash. This establishes replay of engine outcomes, not model cognition.

The writer rejects a checkpoint exceeding the native restore limit (8 MiB of UTF-8 data) before committing, preserving the previous readable head and its matching journal. The size-failure rollback is tested. Existing action/journal/population/checkpoint quotas still make this a bounded prototype; speech-heavy and long unattended operation are not benchmarked.

## Local observer

```powershell
.\.venv\Scripts\python.exe -m underworld new --db data\survival.sqlite --config config\survival.toml
.\.venv\Scripts\python.exe -m underworld observe --db data\survival.sqlite --port 8765
```

Open http://127.0.0.1:8765. The server binds loopback only and starts paused. GET routes use query-only database connections and cannot advance time. Pause/resume/one-tick-step/target-speed changes require explicit POST controls with a per-session token, exact Host and same-origin checks. No arbitrary run paths or code-execution endpoint is exposed. It is a local operator tool, not a remote authenticated service.

The map shows privileged authoritative positions; selected-agent needs, inventory and recent real action history are visible. Target speeds 1x/5x/20x are requested simulated seconds per wall second, limited by real work. No physical ticks are skipped to meet the target. Paused time is not accumulated for catch-up. Controls serialize through one writer lock, and writer failure pauses the observer with an error. Closing the server stops its worker. Other CLI writers are detected by committed-head hashes; run one writer at a time. Native World objects retain single-thread ownership.

Native HTML/CSS/JavaScript and stdlib HTTP serving add no packages or external assets. Desktop 1440px and mobile 390px were checked in a real browser; screenshots and control/read-only evidence are in artifacts. The sight circle is a range guide, not a rendering of the rock-occlusion mask. This observer is intentionally an inspection tool, not a decorative site or 3D world.
