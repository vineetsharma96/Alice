# H3 registration details: small community, newcomer acquisition, interference and repair

Conditional on the verified H0, H1 and H2 gates. Development seed 41; held-out
confirmation seeds 8101, 8111, 8123, 8147, 8161. World dimensions are 32.0 x 32.0 m
with 4 inhabitants (`agent-1..agent-4`) and 6 animals (`animal-1..animal-6`).
All native UW9/DB10 physical laws, zero-LLM constraints and no-shared-dictionary
boundaries inherit `DEVELOPMENTAL_PROTOCOL.md` and `DEVELOPMENTAL_H2_PROTOCOL.md`.

## 1. Four-Agent Community & Isolated Sub-Communities

The 32x32 m world contains two spatially separated initial dyads:
- **Community A (`agent-1`, `agent-2`)** near `(2.0, 3.0)`–`(3.0, 3.0)` (within the
  10.0 m native `speak` hearing radius).
- **Community B (`agent-3`, `agent-4`)** near `(22.0, 24.0)`–`(25.0, 22.0)` (more
  than 25.0 m away from Community A, strictly outside the 10.0 m native hearing
  radius).

During Community A's initial training, `agent-3` and `agent-4` receive zero native
`audible_reports` from `agent-1` (`private_exposure_isolation`). When Community B
independently coins symbols for the same three sensory classes (small food, larger
food, small water), `agent-3` uses its own private PRNG seed (`seed:agent-3`),
producing a distinct convention from `agent-1`. When inhabitants from Community A
and Community B meet, their private production and partner-specific comprehension
tables are never merged or overwritten.

## 2. Declared Cohort Recruitment for Newcomers (No Memory Reset)

Recruiting or activating a newcomer (`recruit_newcomer`) records an explicit
`cohort_recruitment` entry in `development_records` for the newcomer with empty
initial task/symbol associations and its own seeded PRNG. Recruiting a newcomer
never resets, edits or re-initializes the private state or `vocabulary_hash` of
existing inhabitants (`agent-1`, `agent-2`).

## 3. Authored Teaching Transmission to Absent Inhabitants

An inhabitant absent during initial training (`agent-3`) begins with zero
comprehension of `agent-1`'s convention. Transmission occurs only through actual
physical interactions after moving within native visual and hearing range:
`agent-1` (or trained peer `agent-2`) executes grounded deposit-and-speak
demonstrations (`origin: 'authored_teaching_controller'`). No autonomous teaching
claim is made because the exchange is scheduled by the experimental controller
rather than spontaneous model-of-need inference.

## 4. Finite Memory Budget, Interference Block & Resistance to Forgetting

Each listener maintains a finite active comprehension budget per speaker channel
(`active_budget = 6` active `(token, percept)` slots, `protection_threshold = 3`
grounded confirmations):
- **Passive memory persistence**: Without competing interference, saved
  associations remain intact across ticks and fresh-process restarts.
- **Resistance to forgetting under interference**: During an interference block,
  12 transient single-exposure distractor pairings (`n = 1`) are introduced.
  Consolidated associations (`n >= 3`) are marked `protected: True` and resist
  eviction; excess low-count distractors are evicted from active comprehension
  into `archived_comprehension` while preserving their underlying
  `development_records` evidence links.

## 5. Ambiguous Signals, Misunderstandings & Authored Repair Affordances

When a listener encounters an ambiguous signal (homonymous token mapped equally
to two candidate percepts, or an unfamiliar speaker convention with tied zero
scores), `select_with_repair` detects `ambiguous: True` (or initial inspection
mismatch). Rather than predefining request/negation grammar and calling it
emergent syntax, H3 provides an **authored repair affordance**
(`origin: 'authored_repair_affordance'`): the speaker repeats the signal with an
observable `0.001 kg` physical deposit demonstration, allowing the listener to
update partner-specific comprehension and resolve the reference on retry.

## 6. Confirmation Gate

Across the 5 confirmation seeds (`8101, 8111, 8123, 8147, 8161`), 12 scored trials
per arm/seed:
- **Newcomer acquired (`newcomer_learned`)**: mean >= 0.75 and >= 0.20 above
  `untrained_newcomer` (before exposure), with >= 4/5 seeds improving.
- **Post-interference retention (`post_interference_retained`)**: mean >= 0.75,
  all 3 consolidated target classes retained as `protected`, and evicted
  distractors recorded in `archived_comprehension`.
- **Ambiguity repair (`ambiguous_repaired` vs `ambiguous_unrepaired`)**: mean
  improvement >= 0.20 across ambiguous reference trials.
- **Zero-leak private exposure & non-merged community conventions**: verified on
  all 5 seeds with 0 model calls and full source-hash verification.
