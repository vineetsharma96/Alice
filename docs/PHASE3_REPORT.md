# Phase 3 complete — 2026-10-19

Implemented in `C:\Users\abc\Documents\ChatGPT\UnderWorld`, branch `codex/phase-3`. Earlier status is archived as `PHASE2_REPORT.md`; earlier artifacts and saved databases remain preserved. No Phase 4 work started. The repository still has no initial commit; no commit or push is claimed.

## Delivered

- Seeded identity/motivations, separate private original episodes, observed hearing relationships, unverified derived beliefs, durable one-step plans.
- Bounded SQLite lexical retrieval (latest 64 own episodes); no embeddings or model training. Originals are preserved until a hard quota stops growth.
- Provider interface: authored deterministic baseline, mocked-provider tests and functioning pinned llama.cpp CPU adapter. Model-off utility remains the default.
- Independent plan compiler/native validation; fabricated targets, foreign memory references, unknown tools and malformed JSON cannot become authoritative state.
- Shared logical pause, killable timeout/fallback, bounded input/output/context, one inference slot, no retries, shared daily/run quotas, durable attempt reservations, stale-completion checks.
- Atomic physical/mental tick updates, separate mental integrity checks, SQLite backup/restart, recorded physical replay without inference.
- CLI `think`/`mind`, cognition configs, verified download/start script, selected identity/plan/memory in the existing observer.

Detailed contracts and limits: [PHASE3_COGNITION.md](PHASE3_COGNITION.md). Native laws/checkpoints remain **bodies-2 / UW2**. SQLite schema is **3**, package **0.4.0**. Old runtime-pinned saves deliberately fail compatibility checks; there is no automatic migration or overwriting.

## Verification

`artifacts/phase3_checks.json`: **45 Python tests + 3 CTest checks passed**. All 31 previous tests plus 14 cognition cases cover meal/memory/retrieval/restart, malformed JSON, fake target, unavailable tool, foreign memory, actual killable timeout, input-token rejection, adapter protocol/metadata, private retrieval, local speech relationships, tampering, stale inference, concurrency/quotas, model-off scheduling and transaction rollback. Replay does not invoke providers. The real evidence also verifies identity/memory in a **separately launched Python process** after backup.

## Real local-model run

`artifacts/phase3_local_model.json`; private run `data/phase3-final.sqlite`, backup `data/phase3-final-resume.sqlite`:

| Measurement | Observed |
| --- | --- |
| Model | Official SmolLM2-360M-Instruct Q8_0; 386,404,992-byte weights |
| Runtime | llama.cpp b11721 / ff5a23376725e5a889fa0bfb987b7541dc304da0; Windows CPU, 2 threads, 1 slot |
| Context / client limits | 2,048 context; 1,024 input / 192 output; 30 s deadline |
| Calls | 3 real responses, all planned; zero fallback in final trace |
| End-to-end call latency | 9.7854 s, 18.1954 s, 27.7028 s, including worker startup/tokenization |
| Input/output tokens | 505/31, 802/46, 872/31 |
| Server peak working set | 566,956,032 bytes (~540.7 MiB); includes mapped pages and earlier probes |
| Server working set at sample | 457,621,504 bytes |
| Worker peak working set | ~25.9 MB each, reported separately |
| GPU | 0 GPU layers, 0 dedicated model VRAM allocation; integrated display memory unprofiled |
| Horizon | 80 ticks × .2 s = 16 simulated seconds; eight bodies, agent-1 receives the calls |
| Wall time | 56.6507 s for thoughts plus 75 ticks; initial gathering separate |
| Calls per simulated day | Actual day-0 bucket = 3; experimental shared cap = 3; next agent returns quota |
| DB size | 139,264 bytes before named evidence checkpoint |
| Restart/replay | Identity/memory equal after backup and separate process; replay matches at tick 80 |

Setup is explicitly authored: agent-1 gathers .4 kg food. The real model then chooses **eat → speak → eat**. Native actions ingest .2 kg twice, reduce hunger, preserve the 16 kg food / 64 kg water / 32 kg inert material totals, deliver speech locally, and create original result/report episodes. Later lexical retrieval finds `ingested_ug=200000000` with actual native event references. Resumed replay hash: `16ce84f4e93b6dce7b379128f32059e3124e87261a74447969a6f23ada038b82`.

The utterance was literally “speech or empty”; interpretations and evidence citations were weak. This proves working inference/action/persistence plumbing, not strong dialogue, reasoning or human equivalence. The model received retrieved memories but did not produce useful cited reflection in this sample. This is a **partial day**, with no full-day extrapolation. General regression verification overlapped these calls on the constrained host: latency is measured under host load, not isolated throughput. Independent memory peaks must not be summed as simultaneous machine usage.

Negative evidence is retained: `phase3_initial_probe.json` records an invented target rejected before execution; `phase3_adapter_regression.json` records an intermediate metadata bug causing explicit fallback. The bug was fixed and regression-tested before the successful trace. Earlier probe DBs retain their old runtime fingerprints and are not current resumable runs. Exact model revisions/SHA-256 pins are in `phase3_model_pins.json`. Public artifacts exclude full prompts/context; private cognition logs remain in ignored SQLite data.

## Model-off control

`artifacts/phase3_baseline.json`: **1,500 ticks / 300 simulated seconds**, **8/8 alive**, **zero model calls**, 185 utility decisions and original result episodes. Wall **18.2827 s**, **16.409 simulated s per wall s**, peak process working set 31,903,744 bytes; DB 602,112 bytes. The model server was stopped for this repeat. Exact material totals and replay match: `4b8c38b6a2ae253f03b347bbabf6eb5313c9499e26ad0bbf712ec271f293565e`. This shorter regression supplements the archived Phase 2 900 s survival/resource-free control.

## Observer and current local state

Real Playwright checks at **1440×1000** and **390×844**: identity/motivations, private episodes and actual action receipts render; selecting agent-3 shows its delivered unverified report. No horizontal overflow or browser errors. Evidence: `phase3_browser_checks.json`, `phase3_observer_desktop.png`, `phase3_observer_mobile.png`.

The observer remains **paused at tick 80** on <http://127.0.0.1:8765>, showing the real model evidence. This is a **manual experiment**: resuming advances physics without automatic utility/cognition scheduling. Create a fresh `config/cognition.toml` run for autonomous deterministic cognition; default `config/survival.toml` retains utility survival. Stop the observer before another writer or runtime edit/rebuild. The model server was stopped to release RAM; ignored weights/binary remain verified. `scripts/local-model.ps1 -Start` starts it again.

## Limits and next phase

Only this Windows/MinGW/CPython host is tested. No OS-enforced egress test, full-day multi-seed run, unattended rotation, model training, operator teaching, chemistry, scientific discovery, civilization or 3D claim. Physical replay validates mental-store integrity and recorded actions; it does not regenerate mental history. The inference lock is per process, not a distributed multi-coordinator scheduler. A stronger pretrained model would be an external upgrade.

Next phase, only when requested: **Phase 4 — operator teaching and knowledge provenance**.
