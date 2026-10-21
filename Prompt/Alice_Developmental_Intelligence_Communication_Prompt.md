# Alice: developmental learning and invented communication

New-agent implementation specification — 21 October 2026
Repository: https://github.com/vineetsharma96/Alice

## Master prompt

```text
Continue Alice from its actual latest code. Add an opt-in developmental intelligence and emergent-communication track. The user wants inhabitants to learn gradually through experience, remember discoveries, invent words/signals and learn to understand one another. An existing human language is not required.

Implement the staged work below, starting with H0 and H1. Complete a runnable, tested stage before advancing. Maintain a concise HANDOFF.md with actual commands, evidence and next steps. Do not stop at a plan or replace the project with an unrelated language demo. Later stages are conditional on measured success; a failed experiment is a valid result and must not be relabeled as working intelligence.

Baby-like means limited initial practical knowledge plus incremental learning. It is not a claim to model an actual human infant, biological development, consciousness or AGI. Preserve mature existing inhabitants and the established survival baseline. Do not erase memories, remove all survival controls or silently reset a world to create a learner.

Verify the reviewed G baseline locally: C++ physical authority, Python single-writer scheduler, SQLite source-linked memory and protected archives, native UW9/DB10, application 0.14.0/stabilization5. Read current HANDOFF.md, STATUS.md, LIVING_WORLD_G_REPORT.md, memory, planning, knowledge and native speech contracts. Those versions describe the reviewed state, not permission to assume the repository has not changed.

Preserve Phase 9's failed sealed study and keep its learner excluded. This is a separately named and evaluated mechanism; previous failure does not forbid a new learning study, but its evidence cannot be overwritten.
```

## Scientific and implementation boundaries

```text
Separate three capabilities:
1. Remembering an event: the original observation/action/result is retained.
2. Learning: that evidence changes later predictions or action selection.
3. Communication: signals change another person's decisions through learned associations.
Implement and evaluate each separately. A prerecorded vocabulary or a growing skill counter alone does not demonstrate any of the three together.

Primary communication-learning mode must operate without an LLM or pretrained language model. Use a lightweight documented incremental association learner first, with private per-agent state and seeded randomness. A learned symbol protocol is a credible initial target. Humanlike grammar and unrestricted conversation are later research goals, not promised results.

Optional LLM-assisted roleplay can be a separately labeled mode. Never feed it the experimental task or use it to invent a dictionary and then claim language emerged from no knowledge. Do not claim a prompt removes pretrained knowledge. Keep English operator glosses out of learner input.

C++ owns action results, senses, geometry, timing, material changes and message delivery. Python owns private learning state, memory and developmental policy. Persist updates with source receipts, checksums, exactly-once reconciliation and the existing writer lease. Document new schemas/source compatibility; no automatic reset/migration of old saves.
```

## H0 — reproducible learner profile and contracts

```text
Add a developmental profile for explicit NEW experiments or an explicitly selected new learner. Preserve existing saves and mature policies. Keep the same world running across chat sessions/process restarts; a new coding-agent session never means a new inhabitant lifetime.

Define a manifest distinguishing authored priors from learned content:
- Priors: sensory features, motor/action vocabulary, body needs, learning/update algorithm, exploration budget and communication channel constraints.
- Initially absent: task-specific outcome tables, invented-signal meanings, learned partner vocabulary and validated procedure history.
- Existing C++ recipes remain authored laws. Discovery is learning to use an existing law, not inventing a new physical reaction.
- Supervised teaching and operator-injected information are separate external sources.

Create contracts for Experience, Prediction, LearnedAssociation, SignalMessage, PublicFeedback and DevelopmentState. Use per-person/run identifiers, source event references, confidence/counts, update version and random-generator state. Confidence is not automatically a calibrated probability.

Provide a protected baseline and bounded research curriculum. If survival support supplies food, pauses needs or restricts hazards during early training, declare it as scaffolding and account for all inputs. Do not count scaffolded survival as independent survival. Do not change native body laws globally to make learning easy.

Acceptance: default G behavior remains available; new profile contains no predefined lexicon; save/resume preserves learner state; another person's memory or operator map cannot be queried by a policy.
```

## H1 — experience changes future behavior

```text
Begin with one small task family supported by real world actions. For example, learn which locally perceived source leads to obtainable food under varying access conditions. Log the decision-time observation, prediction, chosen action, actual terminal result and later update. Never treat every native rejection as evidence of one cause: collision, missing inventory, busy state and absent target are different outcomes.

Implement a bounded tabular/count-based or equivalently small incremental learner with an explicit update rule. Separate object-specific memory from reusable feature/outcome associations. Record uncertainty and allow bounded exploration, while urgent survival can invoke an explicitly attributed protective baseline. Do not give the learner the exact validator predicate as its learned answer.

Persist useful sources and action consequences beyond the latest-64-episode lookup without unbounded scanning. Keep evidence links recoverable under archival. A missing evidence chain is explicit uncertainty, not fabricated memory. Update only from the person's observable feedback. Operator audit labels can score experiments but must not enter the learner through hidden fields.

Preregister a new hypothesis, development seeds, held-out situations, compute cap and comparison thresholds before measuring. Compare learning-enabled, frozen-initial, memory-only and strong authored baselines. Include both successful and unsuccessful opportunities; inactivity must not earn a success score. Freeze learning during scored evaluation; evaluate ongoing online adaptation separately.

Acceptance: show a reproducible change in behavior attributable to experience and improvement over the appropriate nonlearning baseline on held-out situations. Report failure if there is no improvement. Do not require beating a perfect authored controller to demonstrate learning, and do not claim general superiority from beating a weak baseline. Preserve the negative result and stop promotion if the registered gate fails.
```

## H2 — invent and learn names through grounded interaction

```text
Add a bounded channel of discrete symbol IDs, rendered to humans as arbitrary syllables or glyphs. A finite alphabet and maximum utterance length are authored channel constraints; meanings are not preset. Start with one-symbol messages and several locally distinguishable referents before attempting sentences.

Each inhabitant has its own initially empty production/comprehension associations. The same signal may initially mean different things to different inhabitants. No global dictionary, automatic broadcast of learning state or synchronized private mapping is permitted. Coining a signal and updating associations use that agent's saved random state and observations.

Use explicit grounded interactions. A starter naming game may supply an authored joint-attention/pointing action: both can see a demonstrated object and hear a signal. Clearly label that gesture as teaching support. It is allowed to learn from public pointing in training; do not call that evidence that the vocal signal alone carries meaning.

Then evaluate message-only reference: a speaker privately receives/sees a target; the listener sees a shuffled set of alternatives but not the intended answer or speaker's private observation. The speaker sends symbols; the listener selects/approaches an alternative using its learned mapping. Evaluate the actual selected referent/action. Speaker target assignment is an experimental task, not spontaneous intention formation.

Reuse native local hearing/time/occlusion. If extending speak, preserve old text speech separately; do not smuggle English translations through its metadata. Receiving a signal never reveals a target entity ID unless a visible pointing action independently does so. Learned meanings update from observed outcomes/public feedback, not a privileged hidden-target lookup. If both learners receive a public success bit, define the sensor/apparatus generating it and its cost; label it as authored scaffolding. Do not fabricate listener perception to supply training labels.

Freeze protocol, reward/feedback and budgets before confirmation. Compare learned messages against silence, shuffled messages, a frozen random mapping and a declared designed-code upper baseline. Balance target frequencies; randomize positions/IDs and control order, timing, gesture and motion side channels. Record source and timing of every delivered signal. Counterfactual token swaps should affect interpretation when the protocol is functional.

Acceptance: communication improves held-out listener performance over silence/shuffle controls across several independent seeds, and saved vocabularies retain that benefit after restart. A learner succeeds only if the receiver acts correctly, not because the sender's log contains an intended meaning. If learners fail to converge, report failed emergence and investigate in a new study; do not insert a dictionary to pass.
```

## H3 — small community, forgetting and teaching

```text
Expand from two to four agents only after H2 has evidence. Preserve independent vocabularies, exposure histories and partner-specific uncertainty. A newcomer begins without the population's associations and learns through actual interactions. Use a new recruited record only through a declared cohort operation; do not reset an existing person's memories.

Support misunderstandings and repeated attempts. Do not predefine request/answer/negation grammar while calling it emergent grammar. Initially repetition, gesture and observable action can serve as authored repair affordances. Later learned repair signals need a separate test. Two isolated communities may develop distinct conventions; do not merge their mappings when they meet.

Test private exposure, newcomer acquisition, transmission to an agent absent during initial training, ambiguous signals and retention after an interference block. Separate passive memory persistence from resistance to forgetting. Use finite memory/learning budgets and report which associations are protected or archived.

If imitation or teaching is selected by a fixed controller, label it authored teaching. Autonomous teaching would additionally require evidence that an inhabitant decides to communicate because of its own situation/model of another person's need, rather than an operator triggering the exchange.
```

## H4 — communicate useful world information

```text
Connect the validated channel to one bounded real-world cooperation task: a scout observes an accessible resource, returns into hearing range and communicates information that helps another inhabitant acquire it. Use the recipient's own permitted perception/memory plus learned signals; no hidden scout state is copied.

First distinguish identifying a resource from giving its location. Learn/test those separately. A shared object-word does not tell a receiver where an unseen object is. If the first version uses a finite landmark set, label the abstraction and learn associations through actual observation. Messages referring to absent targets may be unverified reports; confirmation requires physical observation/outcome.

Extend independent goal selection from needs plus learned predictions: repeated water checks, revisiting observed sources, inspecting uncertainty and requesting/using information. Curiosity is an explicitly bounded engineered preference, not biological desire. Protective survival overrides remain visible in metrics. No automatic animal survival claim: recurring husbandry must be evaluated independently against the G failures.

Score goal success, acquisition cost, avoidable failures, communication effect, scaffolding/fallback dependence and learning retention. Compare identical worlds with communication enabled, muted and scrambled. Do not count assigned goals as autonomous goal formation. If a scripted scout circuit provides all decisions, report integration only rather than independent intelligence.
```

## H5 — sequence meanings and observer explanations

```text
Only after useful single signals work, allow short sequences with an explicit cost/length cap. Study whether parts are reused across object, attribute or location combinations. Do not hardcode a word order or meanings and claim the agents invented syntax. Hold out combinations to distinguish reuse from memorizing a separate code for every case.

Display an operator-only learning panel: current observed behavior, memory sources, updated associations, confidence/counts, utterances, recipient response, learned vocabulary differences and experimentally inferred glosses. Every gloss is an inference with uncertainty, not a guaranteed translation. The actual signal remains visible. Show separate counters for external teaching, learned associations, authored decisions and protective fallbacks.

Two-word gibberish is not sufficient evidence of a language. Successful task communication can still be a narrow protocol with no humanlike grammar. No spontaneous composition outcome is guaranteed; failed combination transfer must remain reported.

Retain checkpoint/epoch protection for learning sources and pending updates. Verify fresh-process continuation, exactly-once message/update reconciliation, bounded history and missing-archive refusal. Keep models off in the primary emergence experiment. Make optional model-assisted runs and their costs visibly separate.
```

## Deliverables and completion gates

- Runnable opt-in developmental configuration and one documented CLI path.
- H0–H5 status reported separately; never use one overall completed checkbox to hide failed learning/communication gates.
- Explicit observation/channel/update contracts and authored-prior manifest.
- Frozen protocols, baseline comparisons, seeds, raw outcomes, actual simulated/wall durations and uncertainty. Five confirmation seeds are a proposed starting budget; revise transparently before measurement if compute prevents them.
- Native/Python regression checks for physical accounting, memory isolation, bounded delivery, source retention and crash recovery, plus real browser checks for changed panels.
- A compact HANDOFF.md and updated current overview docs. Preserve historical reports, G negatives and sealed Phase 9 evidence.
- No package/application/release number is chosen automatically: document the capability before the user assigns the release label.

## Primary references

1. Havrylov & Titov, NeurIPS 2017, **Emergence of Language with Multi-agent Games: Learning to Communicate with Sequences of Symbols**. https://proceedings.neurips.cc/paper/2017/hash/70222949cc0db89ab32c9969754d4758-Abstract.html — demonstrates learned discrete communication in a constrained referential setting; it does not guarantee Alice will develop humanlike language.
2. Kottur et al., EMNLP 2017, **Natural Language Does Not Emerge 'Naturally' in Multi-Agent Dialog**. https://aclanthology.org/D17-1321/ — effective task protocols need not be interpretable or compositional; evaluate semantics/combinations rather than assuming them.
3. Existing Alice source contracts and reports. https://github.com/vineetsharma96/Alice/tree/main/docs — reuse physical senses/actions, private memory, operator provenance and archive boundaries. The new learning/channel algorithm is our design, not a replication of either paper.

## First instruction for the next agent

```text
Read Alice_Developmental_Intelligence_Communication_Prompt.md, current HANDOFF.md
and docs/STATUS.md. Inspect the actual code. Execute H0 and H1 first, preserving
the current world and existing survival modes. Establish a measured learning
baseline before claiming emergent language. Continue H2 only after its learning
prerequisites have evidence. Do not invent a shared dictionary or use a pretrained
LLM in the primary communication-learning experiment. Keep all results honest,
including failed gates, and leave a concise runnable handoff.
```
