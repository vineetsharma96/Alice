# Phase 6: practical skills and cultural transfer

This phase adds optional native social actions, validated practice and physical procedure books to the Phase 5 laboratory. Enable `config/culture.toml`; existing configurations leave these features disabled. All cognition/model weights remain unchanged. The comparison policy is explicitly authored and uses each inhabitant's permitted observation and own report recall.

## Authored task and randomized apparatus

The small task is **conditioning at least 5 g of liquid water in thermal-1**. The actor must choose the correct fixture dial and hold the water within the apparatus temperature band, with the heater off, for its required work duration. The native solver checks conditions every physical tick; interrupted conditions reset consecutive exposure. Failure consumes elapsed time and prior heater energy, produces no skill and no successful batch record. Holding a batch creates a durable validation record; it does not manufacture a new chemical species or consume water. Repeated conditioning is repeated practice on the same material, with the skill benefit capped.

After physical/thermal world construction, a separate seeded native generator chooses one of four target temperatures (310, 325, 340, 355 K) and one of four random dial labels. The valid band is target ±7.5 K. The engine checkpoint retains the answer; ordinary perception and provider context do not expose it. A completed nearby inspection reveals the four dial labels and the existing 5 K thermometer. The labels are apparatus-specific, so pretrained knowledge cannot identify the correct choice. All bands, the four-candidate search space and the recipe's existence are authored.

The experiment teacher searches up to 16 temperature/dial combinations using its approximate instruments, timed heater controls and actual native task attempts. It never reads the privileged apparatus answer. It records its successful nominal setting. This is bounded enumeration with a supplied feedback controller, not spontaneous science or open-ended learning. Recipes are unverified reports when read; they must still work physically to award practice.

## Procedural practice, episodes and beliefs

| Mechanism | Source | Effect | Limit |
|---|---|---|---|
| Native water-conditioning practice | Successful sustained physical task | Minimum work = `4 / (1 + 0.25 * level)` seconds | Level 0–3; physical ticks round duration upward |
| Episodic memory | Own actions, accessed books/reports, observed interactions | Bounded private retrieval and source history | Existing 10,000 episode cap; no silent deletion |
| Procedure recall | Original own read/heard episodes in authored `PROCEDURE` syntax | Returns reported recipe candidates and provenance | Newest 64 own episodes, at most 8 matching reports |
| Belief updates | Existing bounded cognition interpretations | Unverified inference records | Cannot change physical rules or native skill |
| Neural training | None | None | Model weights are unchanged |

A successful task increments the actor's practice level, capped at 3, with the native validation event attached. Reading, speech, offer acceptance and book writing grant no execution skill. Typical work times with dt=0.2 s are 4.0, 3.2, 2.8, then 2.4 s; the exact minimum at level 3 is approximately 2.286 s. Heat still costs the same admitted electrical energy: practice speeds the validated work stage only. More than three successful episodes can be recorded, but efficiency stops improving. Per run: at most 256 successful batch records, 64 agreements, and the existing 128 introduced artifacts/resources and 10,000 decision caps.

`culture.episodic_memory=false` disables acquisition and retrieval of episodic reports and derived-belief episodes from that point. It preserves physical practice, native short report caches, agreements and observed social evidence. A new branch can explicitly disable it without rewriting the parent. Existing archived parent episodes remain on disk; the disabled branch's `mind`/procedure/provider projections omit them. This is a **persistent episodic-memory ablation**, not total amnesia. The benchmark execution stage uses fresh-process own-report recall and does not reread the available book or consult native short report caches. An alternate controller could reread and use immediate information; the comparison does not establish that memoryless agents can never succeed.

## Optional social actions

All actions pass the existing strict ActionRequest boundary, principal check, observation version, timed native completion, deduplication and durable journal. No agreement forces an agent to act. The author-supplied benchmark policy withholds sharing or declines participation for the `preserve supplies` motivation; other motivations permit it. These are transparent policy rules, not inferred psychological traits.

| Action | Targets | Parameters | Minimum time |
|---|---|---|---|
| `give` | one other living, present actor | `material`: food/water/inert_material; positive microgram-resolved `mass_kg` <=1 | 1 s |
| `offer_task` | one other actor | bounded `text` describing the conditioning task | 1 s |
| `respond_task` | none | `agreement_id`, boolean `accept` | 1 s |
| `process_batch` | thermal-1 | `dial` | Actor's validated practice minimum |
| `write_book` | none | `text`, own `evidence_ref` | 5 s |
| `depart` | none | `{}` | 1 s |

Gifts require visibility and reach <=1.5 m, debit only the giver's carried inventory, and enforce the recipient's 2 kg capacity. Availability and capacity are checked again at completion. No resource appears from an agreement or report.

Offers/responses require visible, present participants within the hearing range. Offers expire after 120 simulated seconds; participants can decline, accept or let them expire. This phase supports one shared task type: an accepted partner's subsequent valid conditioning episode fulfills the agreement. The bounded text is descriptive, not an executable contract language. Current task-board state is accessible to a participant only at the local apparatus or through modeled contact with the other participant. Observer snapshots are privileged and show all agreements.

Writing consumes **10 g of carried inert material** to create a fixed physical book at the author's position; total mass is unchanged. Evidence must be the writer's own native successful task event or an original report it has accessed. This verifies access, not the truth of arbitrary book text. Content remains hidden until a successful nearby one-second `read`. Book origin, writing event, author, read event and subsequent report origins remain attached. Ordinary inspect does not reveal the text. A reader can use a recipe after its author has departed.

Departure is voluntary removal from active interaction: the archived entity remains in privileged history with `present=false`, but is omitted from others' perception and collision tests and cannot submit actions or receive new messages. Its body stops updating. This is distinct from death and does not model migration to another active world. Its books and validation history remain.

Social edges require actual delivered speech, completed gifts, offers/responses, completed shared tasks or an actual artifact read. Seeing two entities together is insufficient. Records carry source event IDs. Reading a departed author's artifact creates a reader-to-author provenance edge; it does not notify the absent author. The graph describes observed contact, not trust or a required society.

## Procedure format and tools

The read-only `procedure` command recognizes a bounded authored format, for example:

```text
PROCEDURE {"dial":"dial-0-24cb434c","station":"thermal-1","task":"condition-water-v1","temperature_k":325}
```

This example label is from an experiment; it is not a universal recipe. Recall examines only the requesting inhabitant's original book/heard episodes, reports conflicting recipes without adjudicating them and returns `engine_fact=false`. Physical success remains authoritative.

The existing bounded cognition compiler adds `process_batch`, `write_book`, `give_food`, `give_water`, `offer_task`, `accept_task`, `decline_task` and `depart`. Tool alternatives depend on current permitted targets/own skills/accessible apparatus labels. A process plan puts its dial in `text`; a write/offer plan puts its bounded content there; gift/response/departure use empty text. Writing requires an own-memory evidence reference. The experiment itself uses `underworld/lab_policy.py`, an explicitly authored observation-only controller, and does not test spontaneous local-LLM cooperation.

## Reproduction and evidence

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe
.\.venv\Scripts\python.exe scripts\phase6_evidence.py --directory data\fresh-culture-evidence
.\.venv\Scripts\python.exe -m underworld procedure --db data\fresh-culture-evidence\seed-33\teaching-restarted.sqlite --agent agent-2
.\.venv\Scripts\python.exe -m underworld observe --db data\fresh-culture-evidence\seed-33\teaching-restarted.sqlite --port 8765
```

The evidence script refuses existing directories. It uses five world/apparatus seeds and forks three arms from each identical physical head after teacher search: teaching, no teaching and persistent episodic memory disabled. All arms have matched offer/response/gift-or-rest/write-or-rest timing before the teacher leaves. Artifacts are read only when present and the student's policy participates. A saved SQLite backup is reopened through a fresh-process CLI before learner execution. When recall is unknown, the learner makes one seeded blind choice among the 16 nominal recipes. Repeat practice is measured only after successful reproduction. The report preserves every attempted recipe, failed result, declined/withheld case, communication event, validation reference, cost, elapsed time, database size and replay result.

`artifacts/phase6_culture.json` contains measured outcomes; `docs/STATUS.md` summarizes them. The teacher's search budget exceeds the learner controls' single blind attempt. This compares transmission under the stated execution budget; it does not prove that controls could never rediscover the task with more time. Five small seeds and authored preferences/controllers cannot establish general social intelligence, autonomous cultural evolution or real-world process validity. Existing Phase 5 thermal assumptions remain in force.

Package 0.7.0, native UW5, SQLite user_version=6. Culture state, exposure accumulated during an in-flight action, practice evidence, books, agreements, departures and social observations persist. Native/Python source hashes remain pinned. Earlier-phase data is retained but no automatic migration is provided. Phase 7 unattended-operation work has not started.
