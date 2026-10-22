# Alice — Developmental Emotions Implementation Master Prompt

You are the implementation agent continuing https://github.com/vineetsharma96/Alice.
Build an integrated, persistent developmental emotion system. Inhabitants should acquire individual preferences, fear associations, expectations and relationships through their own experiences. Their emotions must affect attention, memory, planning and observable action. Deliver runnable code and reproducible evidence, not just architecture or emotional dialogue.

## 1. Inspect before implementing

Read applicable AGENTS.md instructions, README, HANDOFF.md, current status, architecture, contracts, model limits, and the latest reports covering learning, communication, weather, survival and persistence. Locate actual runtime entry points and the viewer. Treat historical phase reports as historical evidence. Do not assume features mentioned in this prompt already work. Record the exact Alice commit and baseline checks.

Preserve existing worlds, resource accounting, native action validation, private observations, learned language and previous failed research results. Opening a coding session must never reset a world or inject knowledge. Do not change release versions or tag a release without instruction.

## 2. Inspect these upstream references

- FAtiMA Toolkit: https://github.com/GAIPS/FAtiMA-Toolkit
- SELAgents: https://github.com/nicolastorresr/SELAgents
- Optional research reference: https://github.com/pedrodbs/SocioEmotionalIMRL

Inspect source, tests, dependencies and licenses, not only READMEs. Pin inspected commit hashes. Identify which mechanisms are implemented, which are authored configuration, and which are merely claims. Check FAtiMA's appraisal, emotional decision making and social importance components. Examine SELAgents' actual learning, memory, social reasoning and relationship updates, including whether observations leak private state or examples rely on random responses.

Produce an upstream audit with file-level evidence, limitations and reuse decisions. Verify license permission before copying or adapting code. If permission is missing or unclear, do not copy that implementation; use published ideas with attribution and write original code. A public repository is not automatically licensed for reuse. Preserve required notices for any reused code.

Choose adaptation or direct integration based on evidence. FAtiMA is a C# toolkit; Alice may benefit more from selected algorithms adapted to its established stack than an additional .NET service. SELAgents' Python code may be suitable, but compatibility must be verified. Do not add a separate service unless its benefit justifies deployment, latency and save/replay complexity. If an upstream cannot be accessed, clearly mark it unverified and continue independently implementable work without inventing findings.

## 3. One authoritative emotional system

Use one state model and update pipeline. Do not run two competing mood engines. Draw appraisal and decision architecture from FAtiMA and evaluate SELAgents for emotional memory, learning and relationships. Do not imply that using these names proves successful integration.

Pipeline:
authoritative world event -> permitted perception -> private belief/prediction -> personal appraisal -> emotion/mood update -> memory/relationship update -> bounded influence on decisions -> native validation/execution -> observed outcome -> learning.

Physical truth remains authoritative in Alice's world engine. Private cognition must never fabricate inventory, successful actions, shelter, injuries or resource transfers. Operator-visible diagnostics are not available to inhabitants.

Use actual simulation time, deterministic update ordering and seeded randomness. Separate initial drives, authored rules, learned associations, model proposals and deterministic fallbacks in code and logs. No external model is required for the emotional core. An optional LLM may express or propose interpretations, but cannot independently assign authoritative state or bypass observations and validation.

## 4. Core state and contracts

Adapt names to the repository. Each inhabitant needs:

- Body-derived signals: hunger, thirst, exhaustion, injury and thermal discomfort from real simulated conditions.
- Core affect: bounded valence, arousal and perceived control; track uncertainty separately if useful.
- Immediate emotional episodes: cause, target, onset, intensity, confidence and decay.
- Slow mood/stress state, distinct from immediate episodes and body values.
- Appraisals: goal relevance, expected benefit/harm, novelty, predictability, controllability and perceived responsibility where the agent has evidence.
- Private learned preferences and threat/safety predictions with confidence and update history.
- Emotional memory links into existing episodic memory rather than a duplicate unbounded memory store.
- Per-person relationship estimates derived from encountered evidence, with uncertainty and separate familiarity, trust and attachment where implemented.
- Regulation attempts, outcomes and bounded learned efficacy estimates.

Do not assume actual intention equals perceived intention. Attribution may be mistaken and must remain revisable. An agent cannot infer malicious intent merely because another action harmed it.

Every update needs provenance: observed event IDs, relevant prior memories, prediction, appraisal, before/after state, learning rule/version and eventual decision effect. Specify finite ranges, rates per simulated second, saturation, recovery, missing-data handling and numerical invariants. Mood dynamics should remain comparable when update frequency changes.

## 5. Development stages and advancement gates

Implement sequentially. Establish and record each evaluation protocol before tuning against its measurements. Advance when its gate passes; continue automatically within the authorized task. If a gate fails, investigate and repair or report it blocked. Do not silently relax thresholds to advance. Later stages may exist as isolated experiments but cannot be represented as completed runtime capabilities.

### F0 — Audit, contracts and persistence
Document upstream decisions, state schema, ownership, event flow, feature flags and evaluation plan. Integrate a minimal observable state into the actual runtime. Provide safe migration or explicit compatibility handling for existing saves; back up before migrations.
Gate: emotional state round-trips, numerical bounds hold, replay/update semantics are defined, and emotion-disabled behavior preserves the baseline.

### F1 — Bodily wellbeing
Derive discomfort and recovery from real needs, injury, rest and exposure. Avoid repeatedly counting the same condition as both a new injury event and full accumulated pain each tick. Use rate-aware integration and distinguish current state from change in state.
Gate: matched agents respond differently when their bodily conditions differ, then recover appropriately when conditions improve. Emotion cannot create food or remove injury.

### F2 — Personal appraisal
Interpret perceived outcomes relative to active goals and private expectations. Support mixed emotions and uncertainty without forcing every event into one named label. Failures under uncontrollable scarcity must be distinguished from avoidable planning mistakes.
Gate: a common event produces explainable different appraisals for different goals or histories; inaccessible facts never affect appraisal.

### F3 — Learned preferences and fear
Start with declared drives and a minimal bias configuration. Learn which observable cues predict benefit, harm or safety from experience. Do not pre-label all animals, storms or strangers as feared. Support uncertainty, limited context generalization, safe-experience updates and reversal when conditions change. Use the existing learner if suitable; do not re-enable any failed learner without fresh evidence.
Gate: experience changes held-out choices compared with a frozen-learning baseline; reversal is possible; histories survive restart. Distinguish inherited/initial biases from learned associations.

### F4 — Mood and temperament
Implement slow accumulation and recovery with declared initial temperament parameters. Only add experience-dependent temperament change when bounded and testable. Include rest and safe, adequately supplied conditions as recovery opportunities. Do not create random mood changes to simulate depth.
Gate: mood persists beyond a single event, reacts gradually and recovers; long runs remain finite and avoid unexplained permanent saturation.

### F5 — Emotional memory
Use salience to influence encoding and retrieval while preserving timestamps, context, uncertainty and factual provenance. Balance recent distress against relevant safe evidence. Memory consolidation or reconstruction must not rewrite authoritative events.
Gate: relevant experiences influence decisions more than unrelated episodes; corrected beliefs can coexist with an unchanged factual record. Retention remains bounded.

### F6 — Relationships and attachment
Learn individual-specific expectations from witnessed help, failed assistance, reliability, repeated familiarity and shared activity. Avoid one universal friendship score. Mere proximity is not automatically evidence of trust. Respect directional relationships: A trusts B does not imply B trusts A.
Gate: matched agents with different interaction histories choose helpers differently; one interaction does not update everyone; relationships persist and can be repaired through subsequent evidence.

### F7 — Understanding others
Infer another inhabitant's possible needs, goals and affect from visible cues and learned signals. Store probability/confidence or an equivalent uncertainty representation. Do not access the target's private mood, goals, lexicon or memories.
Gate: inference helps in appropriate scenarios, makes understandable errors under ambiguity and updates after new evidence. Include an explicit test against private-state leakage.

### F8 — Emotional regulation
Allow feasible strategies such as resting, moving to safety, requesting help, reconsidering an uncertain interpretation or switching a repeatedly failing plan. Learn their context-dependent efficacy from observed outcomes. No free action may simply zero fear or stress.
Gate: regulation improves recovery or decision quality under declared scenarios while retaining useful danger avoidance; costs and time are accounted for.

### F9 — Emotional communication
Use Alice's actual gestures and learned communication channel. Emotional expression can be a bodily cue with declared mechanics; learned emotional symbols must acquire associations individually. Do not insert a shared vocabulary or instantly transmit state. Observer labels such as 'fear' need not be inhabitants' words.
Gate: receivers improve predictions or assistance through acquired signals; shuffled signals and unfamiliar partners provide controls; misunderstandings remain possible. Do not claim humanlike grammar from successful signaling.

### F10 — Social and self-evaluative emotions
Investigate gratitude-like responses, pride, guilt-like responses, embarrassment, envy and grief only when their prerequisites exist. A guilt-like state needs perceived responsibility, a represented violated expectation and possible repair; grief-like dynamics require an established attachment and evidence of loss. Norms must be identified as seeded, taught or learned. Do not manufacture moral knowledge or relationship history to complete this stage.
Gate: the relevant beliefs, history and relationships change behavior in controlled comparisons. A label or emotional sentence is insufficient. Unavailable prerequisites must be reported as deferred.

### F11 — Developing identity and values
Build revisable personal summaries and commitments grounded in retained events. Keep declared initial values distinct from acquired preferences. Avoid circular rewards where an agent produces an emotional label merely to reward itself. Long-term commitments must influence feasible choices and remain open to revision.
Gate: continuity survives restart and varied contexts; meaningful experience produces explainable change without arbitrary personality replacement.

### F12 — Integrated lifelong evaluation
Run with survival, animals, crafting, weather, shelter, learning and communication where those systems actually exist. Increase population and duration progressively within hardware limits. Verify scheduling, bounded memory, journal retention and checkpoint recovery. Report simulated duration and wall time separately.
Gate: reproducible evidence across multiple seeds and held-out scenarios, with explicit limits. No hidden refills, resets, rescues or unexplained cognitive-state edits.

## 6. Behavior must change through bounded influence

Connect affect to attention, risk estimates, goal urgency, exploration, persistence, help-seeking and memory retrieval. Log its contribution to decisions. Avoid unrestricted multipliers that trap an inhabitant in panic or inactivity. Emotion must coexist with feasibility checks and resource constraints. Do not optimize solely for pleasantness; temporary discomfort may be accepted to meet needs or help someone.

Use existing planner interfaces, preserving native action authority. A displayed emotion without an actual decision effect is visualization only. An intervention that injects feelings must be an explicit logged guided-experiment action and excluded from evidence of naturally developed affect.

## 7. Evaluation protocol

Keep separate development and held-out worlds/seeds. Use at least five held-out seeds for lightweight scenarios where feasible; explain any smaller sample. Use paired initial conditions for comparisons and retain per-run results, not just averages. Declare exact quantitative thresholds before the evaluated run, based on scenario mechanics and baseline variation. If tuning uses held-out data, replace that held-out set and disclose it.

Controls should include emotions disabled, affect present but disconnected from decisions, learning frozen, relationships disabled, and communication shuffled where relevant. Use only the controls relevant to the current stage. Keep policies and resources comparable.

Required scenario families:
- Injurious encounter followed by repeated safe encounters; test acquired caution and revision.
- A genuinely dangerous situation versus a harmless superficially similar situation.
- Hunger or cold followed by real recovery and slower mood recovery.
- A blocked task, a feasible alternative and a legitimate no-solution case.
- Reliable and unreliable helpers with asymmetric observed histories.
- Ambiguous social cues requiring uncertainty and belief correction.
- Save/resume mid-emotion, mid-plan and mid-relationship update.
- Long exposure followed by safety; test boundedness and recovery.
- Manipulation of observer-only labels; verify it cannot alter agents' hidden knowledge.

Measure survival, goal completion, avoidance accuracy, unnecessary avoidance, exploration, recovery time, trust prediction quality, help-seeking, false social inferences, adaptation after reversal, resource cost, latency and memory growth as relevant. Emotion is not required to improve every metric; document tradeoffs and failed hypotheses. Avoid claims about human psychological equivalence without supporting data.

## 8. Persistence, UI and operations

Persist state, learned parameters, relationship evidence, pending cognitive updates, random generator state and schema/rule versions as needed for the existing replay contract. Ensure replay does not apply learning twice. Use isolated writable state per world and transactional updates. Test old-save behavior without overwriting originals. Pausing must not cause wall-clock emotional decay unless explicitly part of the existing declared time model.

Add an observer panel in the existing viewer: body signals, mood timeline, active episodes, appraisal explanation, confidence, relevant memory links, directional relationship changes and decision influence. Label initial/authored/learned/model-derived values. Keep it performant and separate from inhabitants' observations. Use available browser tooling to inspect it; if visual verification is unavailable, record exactly what remains unverified.

Keep the core offline and avoid mandatory paid APIs. Inspect actual hardware before selecting budgets. Pin dependencies; install missing project dependencies in an isolated environment where permitted. Avoid unnecessary new infrastructure or neural training. Never claim a command, browser inspection or experiment that was not executed.

## 9. Deliverables and handoff

Deliver runnable integrated changes, appropriate regression tests, a reproducible scenario runner, structured raw results, and concise current documentation. Suggested documents: EMOTION_UPSTREAM_AUDIT.md, EMOTION_ARCHITECTURE.md, EMOTION_EVALUATION_PROTOCOL.md and EMOTION_REPORT.md. Fit the repository's conventions rather than duplicating existing documents. Update STATUS and HANDOFF with implemented stages, exact commands/results, source revisions, migrations, known failures, next actions and any license obligations.

Record each stage as implemented, experimentally passed, failed or deferred. Do not equate implemented code with validated capability. Do not erase failed Phase 9 evidence or other historical results. Do not claim AGI, consciousness, real pain, guaranteed emergent morality or a completed civilization.

Begin now with repository inspection and F0, then complete F1-F3 as the first integrated milestone. Continue through later stages in order when their gates pass and execution capacity permits. At a session boundary leave the project runnable and a precise handoff. Do not stop after a plan, require approval for routine authorized implementation, or portray future stages as completed.
