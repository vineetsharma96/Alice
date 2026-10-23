# F10 social and self-evaluative emotion slice

F10 adds `underworld/social_emotions_f10.py` with prerequisite-gated,
owner-scoped states for gratitude-like response, pride, guilt-like response,
embarrassment, envy and grief. A state appears only when its authored public
evidence gates are linked: for example, guilt requires responsibility, a
violated expectation and feasible repair; grief requires an established
attachment and observed loss.

Evidence is directional, provenance-tagged (`seeded`, `taught` or `learned`),
bounded and idempotent. Influence returns only proposal-only repair,
gratitude, concealment-avoidance or connection actions. It never executes a
native action and never accesses private target state.

This is an implementation slice, not evidence of moral knowledge, humanlike
emotion, autonomous norms or a passed prospective F10 gate. Missing
prerequisites remain explicitly deferred.
