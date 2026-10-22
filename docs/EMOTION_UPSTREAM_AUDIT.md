# Upstream source audit - 22 October 2026

Alice baseline inspected: `8160e64389c086bd1049faad5a9a18a9ef4e242a` on
codex/weather-seasons. Remote fetched and inspected: origin/main
`d54a007151bee6a3a29aea6cb1137d4709610857`, an ancestor with earlier H3 work and
different ecology defaults. Local H4/H5/gap/weather evidence is retained.
Current work branch: codex/developmental-emotion. Unrelated OpenCode/package
working changes are preserved. Hardware:4 logical processors,4180582400 RAM bytes.
The read-only weather demo on8777 was active; no autonomous study was found.
Baseline rerun:28 weather tests pass (3.978s); older335+4 result is historical
until independently rerun. Architecture/contract/model-limit documents contain
historical sections; latest handoff/weather/gap reports take precedence.

## FAtiMA Toolkit

Inspected actual shallow checkout of
[GAIPS/FAtiMA-Toolkit](https://github.com/GAIPS/FAtiMA-Toolkit/tree/56b7cbd992f953cfe21a7b12cb1a0e6cdf6ccf9f),
commit `56b7cbd992f953cfe21a7b12cb1a0e6cdf6ccf9f`.

- `Assets/EmotionalAppraisal/EmotionalAppraisalAsset.cs` AppraiseEvents builds
  appraisal frames via registered derivation rules and personal goal/KB inputs.
  `OCCModel/OCCAffectDerivationComponent.cs` and `OCCAppraisalVariables.cs`
  implement a named appraisal model. Registering authored rules is different
  from learning them from physical experience.
- `Assets/EmotionalAppraisal/Mood.cs`: bounded [-10,10] mood and exponential
  simulated-tick decay, configured half-life and emotion contribution. Adopt the
  idea of rate-aware separate affect/stress, not its code or psychological claims.
- `Assets/EmotionalDecisionMaking/EmotionalDecisionMakingAsset.cs` Decide unifies
  registered action activation conditions against a KB and returns proposals;
  application executes. Add/update action rules are explicit authoring APIs.
  This is a useful authority separation, not native Alice feasibility learning.
- `Assets/SocialImportance/SocialImportanceAsset.cs`: attribution rules,
  perspective-specific KB lookup, cached dynamic SI properties. These are authored
  valuations and symbolic perspective operations, not evidence of acquired trust.
- `Tests/Tests.EmotionalAppraisal/EAAssetTests.cs` constructs explicit Feed events
  and emotional dispositions. EmotionalDecisionMaking/EDMTests.cs and
  SocialImportance/SIAssetTests.cs cover authored rule behavior; serialization
  tests exist. These are upstream software checks, not Alice developmental data.
- `Assets/EmotionalAppraisal/EmotionalAppraisal.csproj`: netstandard2.0 with project
  references to AutobiographicMemory, Conditions, GAIPS.Rage, WellFormedNames and
  serialization utilities. NUnit is used by tests. No .NET integration installed.
- `License.txt` is Apache2.0. Source adaptation would require the applicable
  license/notices/change attribution. **No source was copied or adapted**; Alice
  implements its own small equations and contracts. No upstream runtime dependency.

## SELAgents

Inspected actual shallow checkout of
[nicolastorresr/SELAgents](https://github.com/nicolastorresr/SELAgents/tree/c32e55b415ab9751090102c07e6dbcb320eee4eb),
commit `c32e55b415ab9751090102c07e6dbcb320eee4eb`.

- `selagents/models/emotional_memory.py`: bounded memory collections, strength
  updates, similarity indices, JSON/model save/load and actual PyTorch Adam/MSE
  `learn_patterns`/backward. This is real neural optimization code, not validated
  useful learning in Alice. Experience IDs, retrieval and consolidation use
  `time.time()`, incompatible with Alice pause/simulation-time contracts.
- `selagents/core/agent.py` interact computes emotional distance directly from
  `other_agent.emotional_state`; success=trust*(1-distance), then updates trust.
  This is a synthetic interaction outcome, not physical help/transfer evidence.
  `learn_from_interaction` has gradient updates but calls memory
  `update_from_interaction`; that method is absent from emotional_memory.py.
- `models/theory_of_mind.py` predict_state accepts a target agent object;
  `_extract_agent_features` reads its emotional_state.to_vector. That is private
  state access, unsuitable as Alice observer inference. `learn` has optimization
  code; no guarantee of learned accuracy follows from its existence.
- `core/social_network.py` relationship updates clamp trust from interaction
  outcomes and decay with supplied elapsed time. Community detection uses
  random.random() as a timestamp. Proximity and these scores are not attachment.
- `core/emotion_engine.py` stimulus mapping injects NumPy normal noise;
  simulated emotion generation samples random transitions. Do not import this
  to create apparently deep but ungrounded mood changes.
- `examples/basic_simulation.py` samples capacities/partners and calls
  agent.interact(partner), omitting required interaction_type. Its social API
  calls also differ from the inspected source. It is not reproducible Alice
  integration evidence.
- `tests/test_emotion_engine.py` expects n_emotions/current_state and
  store_experience; `tests/test_theory_of_mind.py` expects predict_mental_state,
  get_belief_state and a graph; these do not match the source APIs inspected.
  Tests were inspected, not represented as passed.
- `setup.py` requires numpy,torch,pandas,networkx,matplotlib,seaborn,scipy,
  scikit-learn with broad lower bounds, plus optional pytest tooling. No such
  stack is needed for the bounded offline Alice implementation.
- setup metadata claims MIT, but the inspected tree has **no LICENSE/COPYING
  file** establishing a complete grant/notice. Treat permission as unclear.
  **No code copied/adapted**, no dependency added. Consider source reuse only
  after license clarification and a separate compatibility/privacy review.

## Decision and evidence limits

Original Python implementation, attribution to the inspected appraisal, separate
memory/expectation and proposal/authority ideas. No .NET service or second mood
engine. No neural training, synthetic social success or private target access.
Upstream tests/dependencies are not executed here; this audit is source-level
evidence with pinned revisions, not a successful upstream build claim. Optional
SocioEmotionalIMRL was not required or inspected. Actual Alice behavior is tested
by a separate prospective protocol, not inferred from upstream READMEs.
