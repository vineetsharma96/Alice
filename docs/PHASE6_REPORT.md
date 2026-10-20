# Phase 6 complete — 2026-10-19

Workspace: `C:\Users\abc\Documents\ChatGPT\UnderWorld`, branch `codex/phase-6`. Phase 5 status is preserved in `PHASE5_REPORT.md`; earlier specifications, reports, artifacts and saved files remain. The repository still has no initial commit; no commit or push is claimed. Phase 7 has not started.

## Delivered

- Optional native resource gifts and shared conditioning agreements, with explicit acceptance, decline, expiry and completion. Cooperation is never mandatory.
- Persistent water-conditioning practice earned only through native physical validation. Practice reduces work time, caps at level 3, and has no effect on heat capacity, energy cost or scientific truth.
- A randomized apparatus: four seed-specific dial labels and one of four temperature bands, chosen after physical world initialization. Ordinary perception/provider context does not reveal the answer.
- An authored bounded teacher controller that uses only its own approximate instruments and native feedback to search at most 16 candidates.
- Inhabitant-written physical books costing 10 g carried inert material and 5 simulated seconds, with own-accessed evidence, source authorship and read-gated text.
- Successful procedure transfer after the teacher voluntarily departs; archived teachers cannot act, receive messages, appear in others' perception or obstruct movement/placement. Their artifacts remain.
- Separate native practice, private episodes, unverified recipe recall, derived beliefs and unchanged neural weights. Books grant no execution skill.
- Event-backed social observations for actual gifts, task interactions, delivered speech and artifact reads. No graph edges from mere proximity; absent authors are not notified by their readers.
- Explicit persistent episodic-memory ablation through a new branch, source-bounded `procedure` CLI, bounded cognitive tool compilation, observer practice/agreements/provenance and durable exposure/skills/artifacts.

[PHASE6_CULTURE.md](PHASE6_CULTURE.md) documents task rules, action fields, costs, caps, access gates, authored assumptions and experimental limits. R7/R8 original author/publisher pages were checked for research context and are listed in [REFERENCES.md](REFERENCES.md); no POET/ASAL replication is claimed. No new dependency or model was installed.

Package **0.7.0**, native **UW5**, SQLite **user_version=6**. Prior data remains historical and requires its original pinned runtime; no automatic migration is provided. Existing configurations keep culture disabled. Native and Python source identities are pinned:

- Native: `e4d689e278e0b91d6be3b90c02f106a85992a86166d49058b02ea43f8da35f4e`.
- Python orchestration/controller: `f10504bfe389e2549f847594618117344b6abf3991aed476813cf373c45391db`.

## Verification

`artifacts/phase6_checks.json`: **86 Python tests + 4 CTest checks passed**, retaining all 74 previous Python cases. The new cases verify randomized hidden apparatus access, rejected shortcuts/wrong conditions, sustained exposure under interference, capped practice and changed work time, exact gift/paper mass, optional task lifecycle, observed-only social evidence, agent-authored provenance, teacher departure/ghost-collision prevention, private book access, native mid-action restart, durable rollback, fresh-process procedure recall, episodic ablation, strict configuration and compiled tool access. Previous heat conservation, oxygen, vapor, bodily needs, cognition quotas, privacy, teaching and HTTP tests still pass.

An initial integration test caught a non-JSON departure set; it was changed to a list. That failure is preserved in `artifacts/phase6_initial_failure.json`. Pre-final-review evidence/checks and the one-seed pilot also remain separately preserved. Final evidence below matches the current native/runtime hashes.

## Five-seed comparison

`artifacts/phase6_culture.json` holds the complete traces, attempts, costs, communication, source references and failures. `phase6_summary.json` / `.csv` provide a compact result table. Each seed first produces a successful teacher procedure through actual search, then forks three arms from the **same physical head**. All teachers leave before reading/execution. Each learner execution uses a saved SQLite backup and a fresh-process own-report recall; the teacher's controller state is not passed to it.

| World seed | Teaching | No teaching | Episodic memory disabled | Interpretation |
|---|---|---|---|---|
| 11 | Failed | Failed | Failed | Student declines cooperative study; blind fallback fails |
| 22 | Completed | Completed | Completed | Teacher withholds sharing; identical blind choice succeeds in every arm |
| 33 | Completed | Failed | Failed | Book-based reproduction after teacher departure/restart |
| 44 | Failed | Failed | Failed | Student declines cooperative study; blind fallback fails |
| 55 | Completed | Failed | Failed | Book-based reproduction after teacher departure/restart |

Overall completion: **3/5 teaching, 1/5 no teaching, 1/5 episodic-memory disabled**. Only **2 teaching successes** have accessed-report provenance; seed 22's success is explicitly a chance/independent fallback success and is not counted as transmitted knowledge. Both participants permit cooperative study in seeds 33 and 55: **2/2 source-backed reproduction versus 0/2 in either matched control**. Reading leaves native skill at level 0; actual successful work then raises it. No result was removed because it contradicted the expected teaching advantage.

The teacher makes **35 total task attempts** across five seeds (9, 14, 5, 2, 5), including **30 failed attempts** retained in the traces. After forking, the 15 arms record 15 offers, 6 acceptances, 9 declines, 2 agreement completions, 6 resource gifts, 8 written books, 4 actual book reads and 15 departures. These counts exclude the shared root histories. The motivation rule is authored: `preserve supplies` withholds sharing/cooperative study, while individuals may still try the task independently. This is optional cooperation, not a required society.

For successful reproduction, measured processing work falls **4.0 -> 3.2 -> 2.8 -> 2.4 s** with dt=0.2 s. The native minimum at level 3 is 2.286 s; the tick rounds execution upward. Efficiency caps there. Repeating the task is practice on the same water, not manufacturing more matter or a new species.

First learner-attempt heater costs across teaching arms are **5400, 2600, 1200, 9400, 1200 J**; matched no-teaching/memory-disabled arms cost **5400, 2600, 1200, 9400, 0 J**. First-attempt simulated time includes heating/inspection/work: 6.4–14.6 s in teaching and 4.2–14.6 s in controls. The longer teacher searches and communication/paper costs are also recorded. A control failure is not free, and a blind success can earn the same physically validated practice as a taught success.

All **15 post-fork branch replays** and **5 teacher-root replays** match their native state hashes (`phase6_root_replays.json`). Final species mass residual is **0 µg** in every arm; maximum final global modeled-energy residual is **1.8626e-09 J**, below the approximately 0.00032 J tolerance. This retains Phase 5's caloric/enthalpy approximation; it is not real process validation.

Final simulated horizons range **50–136 s per arm**, including the root discovery time. Final standalone database sizes are 307,200–618,496 bytes. The five-seed evidence run took **120.613 wall seconds**; peak measured process working set was **68.84 MiB**, excluding other processes/whole-machine RAM. The final verification suite ran alongside part of this measurement, so wall time is host/load-specific. No local-model server was running.

## Concrete provenance and observer

The seed-33 artifact path is teacher validation **#296 -> book writing #348 -> learner reading #364**. The learner's first validated reproduction is **#411**; later practice ends at level 3 / event **#495**. Source book `artifact-348` remains after the author departs. The final demonstration `data/phase6-final/seed-33/teaching-restarted.sqlite` is at tick **319**, **63.8 simulated seconds**; the teacher is archived and one inhabitant remains present.

The [local observer](http://127.0.0.1:8765) is running **paused**. The observer shows learner practice, its accessed source chain, completed agreement and observed social evidence. Browser checks at **1440×1000** and **390×844** show no horizontal overflow or console errors; archived teacher selection says Departed. Paused polling leaves the tick and authoritative head hash unchanged. Evidence: `artifacts/phase6_browser.json`, desktop/mobile PNGs and console log. Native tests and browser evidence are separate checks.

Stop the observer before rebuilding the extension or advancing the same database from a terminal. Reproduction commands use a fresh directory in `PHASE6_CULTURE.md`; new runs/branches/backups refuse overwrites.

## Validity and uncertainty

The apparatus, four nominal target settings, bands, validation predicate, practice formula, motive rules, finite search, feedback controller and procedure syntax are **authored**. The experiment demonstrates access-controlled use/transmission under those controllers. It does not demonstrate spontaneous LLM teaching, semantic understanding, a learned planner, neural training, general society formation or open-ended cultural evolution.

Five seeds are a small sample. Motive choices and blind successes materially affect aggregate completion. The teacher can search up to 16 candidates; a learner without a retained report gets one blind attempt, so these controls do not show that independent rediscovery is impossible with a larger budget. The episodic ablation disables retained report access, not immediate native report caches, physical skills or every possible alternative strategy; the execution-stage controller does not reread the available book. Conditions are checked at physical tick boundaries, not continuously in the real world. A conditioning success logs validated work on existing water and does not create a new chemical species. Phase 5 pressure/PV/flow/kinetics limitations still apply.

Phase 7 unattended operation, longer multi-seed horizons and later 3D work remain deferred. The supplied specification remains unchanged, SHA-256 `306e5eafba0f7c53b49002ec8fcd276dc736efb791ede1991f64e685773e84d6`.
