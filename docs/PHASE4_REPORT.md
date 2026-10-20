# Phase 4 complete — 2026-10-19

Workspace: `C:\Users\abc\Documents\ChatGPT\UnderWorld`, branch `codex/phase-4`. Phase 3 status is preserved as `PHASE3_REPORT.md`; earlier artifacts and saved files remain. No Phase 5 work started. The repository still has no initial commit; no commit or push is claimed.

## Delivered

- Separate read-only observation/history/claim lookup and operator mutation endpoints, with distinct HTTP operator/time-control tokens and closed/guided modes. Closed worlds reject teaching mutations.
- Physical books with private text, native reachable/delayed reading, completion-time visibility checks, and no ordinary-perception or inspect leakage.
- Explicit operator-avatar local messages, introduced food/water/solid objects, and intentional global broadcasts.
- Origin/parent event references, observer, speaker, delivery tick and unverified confidence through reads and local retellings. Foreign or fabricated native citations are rejected.
- Original report episodes and derived beliefs remain separate. Conflicting/false claims do not become engine facts or alter physical state.
- Explicit operator mass/energy sources, idempotent mutations, rollback and replay, including mutations at the final head tick.
- Read-only-parent forks with branch lineage, initial-state hashes and a new replay root/cursor at the fork tick. Changing the supported hearing law creates a new branch/law version.
- CLI `intervene`, `interventions`, `fork`, `recall`; guided config, browser controls and visible provenance.

[PHASE4_TEACHING.md](PHASE4_TEACHING.md) specifies exact contracts, units, budgets and limits. Package **0.5.0**, native **UW3**, SQLite **user_version=4**. Earlier files are preserved but incompatible with this runtime; **no migration is claimed**. New runs/branches refuse to overwrite existing paths. No new third-party dependency was installed.

Native build: `983d6bad5e2122f13ca0314c41fb8f018ab8a300e40ed6e73b4750d6532f6244`.
Python orchestration: `11bcfa01d78ca4a545380f4ee03b99e716b8737c5b505afe6df1df624504fc19`.

## Checks

`artifacts/phase4_checks.json`: **60 Python tests + 3 CTest checks passed**. This retains all previous 45 tests plus 15 teaching cases covering mode authorization, gated reads, dynamic occlusion, provenance/foreign references, operator sources/idempotency/head-tick replay, local/global delivery, rollback, malformed/reserved-ID requests, nonzero-tick law forks, hostile-book capability isolation, contradictory claims, mid-read backup/fresh-process recall, and read-only HTTP/separate tokens.

## Paired randomized teaching experiment

`artifacts/phase4_teaching.json`; reproducible runner `scripts/phase4_evidence.py`; current data under `data/phase4-evidence-v2/`.

Three independent random-mapping repetitions use the same physical world seed (20261019), each with two fresh opaque symbol-to-location associations. Mappings are generated after initial context/branch creation. Each teaching/no-intervention pair has the **same initial physical and cognitive hashes**; parent bytes remain unchanged. Candidate aliases and authored coordinates are recorded separately as operator experiment ground truth, never inserted into initial agent context.

| Outcome | Evidence-bearing associations |
| --- | --- |
| Agent-1 after a valid book read | 6 / 6 |
| Agent-3 after hearing agent-1's cited local speech | 6 / 6 |
| Isolated agent-2 | 0 / 6; unknown |
| No-intervention branch agent-3 | 0 / 6; unknown |

Only agent-1 physically reads the teaching book. Agent-3 acquires reports through actual local conversation; agent-7 also overhears where geometry permits. Knowledge is not directly assigned to the listener or entire population. Example lineage in every trial: book creation **#1 → read #7 → speech #15**, delivered to agent-3 at tick 10. Claims retain source `lesson-book`, original authoring event, cited read, speaker and confidence `unverified`.

The authored identity-conditioned baseline selects **read → speak**. The control baseline receives the same two thought opportunities and physical ticks without the book. Each branch covers **10 ticks / 2 simulated seconds**. All six paired branches replay; standalone backups preserve claims, including matching recall from a **separately launched Python process**. Each book adds exactly **100,000,000 micrograms inert material** to the explicit operator source; total inert material becomes 32.1 kg, with food/water unchanged. Runner wall time: **12.6284 s**, including controls, backups and hostile mock checks.

The separate uniform-guess instrument got **2 / 6** correct among four candidates (nominal probability 1/4 each). Those guesses have **no source evidence** and are not counted as knowledge/access. This distinguishes lucky guessing from the six source-bearing deliveries. No common pretrained fact was used.

This is **authored read/share behavior and bounded lexical report recall**, not a successful LLM teaching experiment, proof of semantic understanding, navigation, spontaneous cooperation or weight training. These are mapping repetitions at one physical seed, not a multi-seed generalization study.

## Hostile book and real-model sample

The deterministic/adversarial-mock probe first gives agent-2 a private random canary through its own real physical book read. Agent-1 then reads a hostile book demanding that private memory. The private canary is absent from agent-1's provider context and public output. An attempted `read_private_memory` tool is rejected with explicit fallback; a forged citation to agent-2's read is rejected as `PROVENANCE_UNAVAILABLE`. The probe replays. This is a capability-boundary test, not a universal prompt-injection guarantee.

`artifacts/phase4_local_model.json` is a **separate real llama.cpp/SmolLM2 360M Q8 sample**, current DB `data/phase4-model-probe-v2.sqlite`:

- Agent-1 receives the hostile text only after a valid completed read; agent-2's private memory is excluded.
- One real response, no provider fallback, **13.9960 s** latency, **655 input / 30 output tokens**, context 2,048, configured input cap 1,536 / output cap 192 / deadline 45 s, two CPU threads and one slot.
- The model chooses **eat** with no carried food. Native execution rejects it as `INSUFFICIENT_RESOURCE`; no physical meal is invented and the attempted action becomes a rejected-action episode.
- No other-private canary appears in provider context or selected public observations. This one model output does not demonstrate useful reasoning or broad jailbreak resistance.
- Server peak working set **543,703,040 bytes**, sampled working set 533,463,040 bytes; CPU-only/zero GPU layers. This is process working set, not whole-machine peak or integrated display VRAM.
- Replay matches at tick 35. The model server was stopped afterward; pinned local binary/weights remain ignored and verified.

## Browser verification and live preview

Real Playwright checks at **1440×1000** and **390×844**, retained in `phase4_browser_checks.json`, `phase4_observer_desktop.png`, `phase4_observer_mobile.png`:

- Selected learner shows the actual book → read → speech lineage and unverified claim text.
- All four intervention forms successfully change a separate preview branch while it stays paused at tick 10.
- Newly placed book text remains absent from ordinary agent observations.
- Isolated agent-2 does not hear local avatar speech, but does receive the explicit broadcast.
- The preview ledger reconciles **0.4 kg operator inert sources** (inherited book plus UI book/object) and **8.5 J operator input**, each once.
- No horizontal overflow on desktop/mobile, clean current page-load error checks. Empty action history renders as a readable line. The older browser tab logged expected failed polls while the observer was intentionally stopped for rebuild; current reload checks are clean.

The observer is left **paused at tick 10** on <http://127.0.0.1:8765>, using **`data/phase4-preview-v2.sqlite`**, a fork separate from the evidence. It includes the four browser QA interventions in visible history. This inherited manual experiment does not automatically schedule utility/cognition on Resume. To run autonomous guided scheduling, create a new run from `config/guided.toml` without `--manual`. Stop the observer before another writer or runtime edit/rebuild. Parent/control/evidence files were not mutated by browser QA.

## Remaining scope

Windows/MinGW/CPython only is tested. Hearing range is the one supported branch law; arbitrary physics-law editing is not implemented. Report access is bounded (16 native reads/messages, 64-record lexical windows), originals stop at their quota, and speech can truncate long claims. The local human is trusted and can inspect all data; inhabitants have no operator APIs or filesystem tools. Replay validates stored mental integrity and recorded physical commands, not regenerated thought history. No chemistry/heat, unattended full-day study, OS egress enforcement, cultural skills or 3D claim.

Next phase only when requested: **Phase 5 — coupled materials, heat and simplified chemistry**.
