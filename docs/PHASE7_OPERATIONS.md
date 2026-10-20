# Bounded unattended operation

Phase 7 adds an operational supervisor, not a new agent intelligence model. Long multi-seed horizons and Phase 8/3D remain deferred. The original proposed 24 simulated hours are not an achieved result.

## Run, stop and resume

From the workspace in PowerShell, after building the native module:

```powershell
.venv/Scripts/python.exe -m underworld new --config config/unattended.toml --db data/my-experiment/run.sqlite
.venv/Scripts/python.exe -m underworld run --db data/my-experiment/run.sqlite --simulated-seconds 300 --wall-seconds 30
.venv/Scripts/python.exe -m underworld run-status --db data/my-experiment/run.sqlite
# From a second terminal while the run is active:
.venv/Scripts/python.exe -m underworld stop --db data/my-experiment/run.sqlite
# The same run command resumes from the last committed head, adding this duration:
.venv/Scripts/python.exe -m underworld run --db data/my-experiment/run.sqlite --simulated-seconds 60 --wall-seconds 20
.venv/Scripts/python.exe -m underworld replay --db data/my-experiment/run.sqlite
```

The output database needs a dedicated folder inside this workspace. `run` supports closed mode on Windows with AppContainer available. Maximum requested duration per invocation is 86,400 simulated seconds and 3,600 wall seconds. These are validation bounds, not an instruction to perform long experiments. The existing lifetime limit is 1,000,000 physical ticks. `advance` remains a manual development command without the unattended isolation guarantee. A failed run returns a structured status; inspect that status, not just the launcher's exit code.

`run-status` includes durable control state, backlog, epoch count, heartbeat timestamp and age. Heartbeats are atomically replaced approximately once per wall second, independently of inference. A stale heartbeat indicates an absent or unresponsive process, not population extinction. No automatic restart or scheduler is installed. Explicit re-launch performs SQLite hot-journal recovery. A session-specific stop file cannot stop a later unrelated session. Parent Ctrl+C requests graceful stop, then the watchdog terminates the job if it exceeds the grace period.

## Network and process boundary

Each invocation creates a current-user AppContainer profile with **zero network capabilities**, starts the worker with its actual restricted token, and places it in a kill-on-close Windows Job Object with a 512 MiB committed-memory ceiling. A token query and public/private TCP denial probes are required before running. No firewall rules, administrator privileges or loopback exemptions are used. Temporary ACLs name only this profile's SID: runtime/source/build/config read access and the selected case directory write access. Normal cleanup removes those SID-specific grants and the profile; `isolation-profile.json` records cleanup errors. An abruptly killed host may leave this manifest/profile for explicit inspection; no claim of guaranteed cleanup after host death is made.

This Windows Store Python installation's venv launcher cannot run inside AppContainer. The launcher copies the **already installed** CPython interpreter, pure standard library and necessary runtime DLLs into ignored `.tools/isolated-python`, keeping license files. It downloads nothing and changes no global Python installation. The fixed runtime is shared. Setup and SID-specific ACL changes use a process-safe lock; existing loaded DLLs are verified rather than overwritten. Run performance measurements serially on this small host.

Direct loopback HTTP was also denied in the measured container. Model configurations must explicitly select `llama.cpp` and pass `--local-model`; the default endpoint is `http://127.0.0.1:8081`. Start the already pinned server separately with `scripts/local-model.ps1 -Start` if desired. The worker passes only bounded JSON through an inherited pipe. A host-side adapter accepts only the configured cognition budget and agent context, pins server build/model identity, forbids proxies/redirects and permits a literal loopback origin. No arbitrary URL, tool, filesystem or shell action is provided to the model. The host supervisor is outside AppContainer; its only model request path is this restricted adapter. This is worker network isolation, not an assertion that every process on Windows lacks network access.

Python multiprocessing spawn cannot duplicate the parent process handle inside this container. Two trusted adapters therefore run inline there: finite authored baseline code and the deadline-bounded pipe adapter. Other provider classes retain the existing killable inference process path. The pipe polls its deadline; the outer job watchdog also bounds stalls. Public model calls remain forbidden in closed runs.

## Transactions and recovery

The OS-released `.lease` sidecar excludes another process/thread from mutating a supervised database, while read-only observers remain usable. Each physical tick uses one SQLite transaction with `synchronous=FULL`. Action validation, physical state, event counters, private episode updates and policy state commit together. A forced exit before commit discards that staged tick; a forced exit after commit preserves it. The wall deadline is cooperative: an in-flight tick, bounded inference or maintenance operation and final reporting can finish after the requested time. The host watchdog allows one cognition timeout plus 15 seconds beyond its budget before terminating the job. Logical time pauses during cognition, backup and maintenance; all inhabitants still receive every physical tick. Batching reduces Python orchestration overhead and controls dispatch frequency; it does not skip physical updates.

Inference reserves quota durably before calling a provider. A crash can leave an `interrupted_or_in_progress` record; recovery consumes that attempt and does not repeat the same queued inference at the same physical tick. Completion, queue removal and retention each have explicit transactions. A crash between them may leave a recoverable intermediate receipt. Checkpoint publication uses a temporary SQLite backup, integrity check, fsync and atomic no-overwrite link. Rotation retries a matching receipt when killed before or after publication. This is process-crash evidence, not a guarantee against power failure, defective storage or OS failure.

## Retention and disk bounds

`config/unattended.toml` demonstrates explicit `[execution]` settings. Defaults: batch 50 ticks, epoch 500 ticks, 3 archives, 32 MiB database, 128 MiB archive budget, 128 epoch summaries, 16 recent ordinary episodes per inhabitant, queue 64, one cognition dispatch per batch, 128 lifetime cognition attempts. These bounds are configurable within validated finite ranges. Model timeout, token, daily-call and single-concurrency limits remain separate. A global 1-second tick is selected for these short operational experiments; previous 0.2-second cultural/thermal experiments retain their own configurations.

At each epoch, a standalone pre-compaction database is published and the oldest managed archive expires within the configured ring. The active replay root moves to that epoch. Completed canonical utility/script action receipts are retired; pending requests, arbitrary external request IDs and cognitive receipts survive. Canonical generated IDs encode their observation tick: replaying a retired old request is stale, and changing its tick without changing its ID is invalid. Arbitrary external IDs retain deduplication until their existing finite request limit is reached. `auto_epoch_` is a reserved checkpoint namespace.

Recent ordinary episodes are pruned, while original book reads, unverified reports, validated practice and pending-plan evidence remain. Knowledge originals can eventually reach their finite quota, at which point execution stops explicitly instead of silently deleting them. Event rows are a configured rolling window; native counters retain exact lifetime event totals across checkpoints. Epoch summaries have checked hash links, before/after state hashes, archived-file hashes, cumulative counters and pruning counts. Hashes detect accidental corruption; they are not signatures against an adversary able to replace all files.

The active root and **retained** archives can be replayed. Expired epochs are deliberately unavailable for full lifetime reconstruction. Outcome explanations use retained action/provenance windows and cumulative metrics; do not claim a complete lifetime journal. Database page caps enforce SQLite FULL rollback. Archive publication reserves room for a temporary copy; quota exhaustion stops at a valid committed head. The database cap excludes its transient rollback journal/VACUUM work; reserve additional disk space. Logs, heartbeat and reports are overwritten per invocation, and fixed runtime/model assets are separate from per-case DB/archive quotas. Creating an unlimited number of distinct experiments is not bounded by one run's quota.

## Metrics and interpretation

Each report records simulated time advanced, worker wall time, host wall time including profile setup, speed, per-provider latency p50/p95 using nearest rank, fallback/interrupted counts, maximum/current queue backlog, dropped admissions, invalid/failed actions, working set/peak/private commit, database growth, archive bytes and native/runtime identities. With no inference calls latency is null, not zero. Model server memory is measured separately. Successful-run memory is sampled in the worker; if a worker exits before its report, the supervisor recovery report samples its own process instead, and the worker peak is unavailable. A bounded FIFO queue orders due tick then agent ID; admission drops are counted when the configured cap is smaller than the eligible population. No fairness claim is made for agents repeatedly excluded by that cap.

Statuses distinguish `target_reached`, `wall_limit`, `stopped`, `quota_reached`, `population_extinct` and `system_failure`. Population extinction means no alive, present inhabitants; departure may also leave none present. Fallbacks are counted provider failures using the authored baseline, never counted as successful model cognition. Physical action rejection and action failure are separate. `invalid_actions` counts native `action_rejected` events, including missing-resource preconditions. A cognition record marked `planned` confirms structured-plan validation and storage, not successful physical execution. A short replenished-resource survival run is not evidence of sustainable society, long-term stability, teaching improvement or artificial-life emergence.

`scripts/phase7_evidence.py --model` runs the short declared seed set and owns/stops its pinned CPU model server. It refuses an existing output directory or occupied server port. `artifacts/phase7_summary.json` contains raw case reports/configurations; CSV is a compact comparison. Operational tests include forced exits at tick and checkpoint boundaries, explicit stop, full-disk rollback, quota and actual AppContainer denial/IPC integration. See `STATUS.md` for measured outcomes and limits.

Package 0.8.0 uses native UW6 and SQLite user_version 7. Older saved experiments remain historical and need their original pinned runtime; no automatic migration is offered. Native physics laws are unchanged by this phase; the format adds exact event totals and bounded receipt maintenance.


## Captured benchmark runtime

The five-seed matrix pins its exact pre-review Python runtime in `artifacts/phase7_benchmark_runtime`, including per-file checksums and native/runtime identities. Final review fixed shared-runtime DLL/setup concurrency, narrowed the reserved checkpoint-name match and checked archive-directory containment. These changes have a distinct runtime hash. The matrix is not relabeled as having run the revised code. Fresh-process replay of its databases uses the captured source without rewriting their identities:

```powershell
.venv/Scripts/python.exe scripts/replay_phase7_benchmark.py --db data/phase7-final/population-8/run.sqlite
```

`artifacts/phase7_final_validation.json` separately records serial population checks and a real-model check on the reviewed runtime, with current hashes. `artifacts/phase7_checks.json` records the full test suite. The initial population matrix overlapped verification on a shared CPU; its speed numbers are indicative, while the final population checks run without that overlap. Tiny model latency samples and different horizon lengths do not establish comparative behavioral quality.
