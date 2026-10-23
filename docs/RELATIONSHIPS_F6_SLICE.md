# F6 relationship slice — started 22 October 2026

F5 is complete and remains frozen. F6 work starts with an additive, directional
relationship estimator in `underworld/relationships_f6.py`.

## Current slice

- Each observer owns a separate estimate of each other inhabitant.
- Witnessed events update familiarity, trust, reliability, attachment and
  uncertainty with finite bounds.
- A single `heard` or `shared_activity` event does not create trust or attachment.
- Positive and negative task evidence can change trust, and later positive evidence
  can repair an earlier negative estimate.
- Helper ranking is deterministic and uses only the observer's relationship state;
  native visibility, reach, resources and action validation remain authoritative.
- Event input is strict and rejects target private mood, goals, memories or other
  unobserved state.

## Not claimed yet

This is an initial F6 implementation slice, not the completed F6 gate. It is not
yet wired into the native scheduler, culture action loop, durable world overlay or
viewer. The required matched-world helper-choice study, five-seed confirmation,
save/resume during a relationship update and full native resource accounting are
still pending. No trust, attachment, social emotion or general understanding claim
is made from the unit fixtures.
