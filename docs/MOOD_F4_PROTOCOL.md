# F4 prospective mood and temperament protocol

22 October 2026. F0-F3 source/result registrations are immutable. This is a new
opt-in profile, not a retrospective relabeling of those trajectories. Development
seed53; fresh confirmation18101,18121,18127,18143,18149. Freeze new implementation,
tests, runner and this protocol before confirmation. Retain failed runs; no
threshold changes based on held-out measurements. Two independent seeds may run
concurrently on the inspected four-logical-processor/4GB machine.

## Declared mechanisms

One authoritative update pipeline retains the existing fast affect, appraisal,
episodes and learned cues. Replace its stress integration with a temperament-
configured slow component, not an additional competing engine. Initial parameters
are authored, persist per person, and do not change through learning in F4.

Slow stress [0,1] tracks a body-derived target:
clamp(sensitivity * max(0, discomfort-.3)/.7). Discomfort is the existing maximum
of hunger, thirst, .7fatigue, injury and thermal burden. The .3 comfort allowance
is an authored dimensionless threshold, not physiology. Target-dependent rise
and recovery use exact exponential integration with simulated seconds. Mood
valence=clamp(baseline_valence-stress,-1,1); immediate affect remains separate.

Balanced: sensitivity1, rise120s, recovery180s, baseline0. Sensitive: sensitivity
1.25, rise60s, recovery240s, baseline0. Calm: sensitivity.8, rise180s, recovery90s,
baseline0. Configured limits sensitivity[.5,1.5], time constants[30,600]s,
baseline[-.1,.1]; reject booleans/nonfinite/unknown parameters. No random mood.

Mood can shift the existing learned-cue caution threshold from-.12 toward-.08
as stress rises, bounded at.04. This is an AUTHORED influence, conditional on an
already personally learned negative expectation, confidence and feasible observed
roof. Original native feasibility, urgent needs and retry cooldown retain priority.
Mood-disconnected control keeps mood/learning but uses the old-.12 threshold.
No free action clears stress. Disabling emotion must still preserve native policy.

## Native scenarios and thresholds, before measuring

Each seed starts a finite8kg-food/16kg-water native weather world. Actual assigned
gather/ingest supplies establish low needs before copies are made; no direct edits.
Three paired arms: balanced/frozen-learning, sensitive/frozen-learning, emotion
disabled. Same guided actual -10C/rain12/wind4 exposure for120s, followed by24C,
dry, still weather for900s. Assigned native rest and finite-stock feeding keep
needs below approximately.3. These are controlled conditioning apparatus, not
autonomous survival or learned regulation. Save native/cognitive samples and
operation provenance. Native feeding can slightly overshoot sample deadlines;
record actual elapsed simulated seconds instead of assuming an exact deadline.

All five seeds must pass:

1. Slow stress after40s is positive and <.2; after120s >.15. No update of<=10s
   raises stress by>.17. This rules out instantaneous mood jumps.
2. Sensitive stress at120s exceeds balanced by>=.1 on matching physical heads.
   The difference is declared initial temperament, not learned temperament.
3. At210s of actual warmth, thermal burden<.12 and no active harmful episode
   remains, while stress>.05. Slow mood thus outlasts immediate distress.
4. At900s of warmth, stress<.05 and <25% of its exposure peak; no unexplained
   permanent saturation. All values finite/in range throughout, all people alive.
5. Disabled stress remains0, and physical states match across arms. Native stocks,
   ingestion and boundary ledgers close, with zero replenishment/external material.
6. Every world independently replays. Mid-recovery backup resumed in a fresh process
   matches uninterrupted native/private/policy state exactly; inspection/pause does
   not cause decay. Historical source registrations remain unchanged.

Software gates additionally cover constant-input timestep invariance (1s/10s,
error<1e-10), declared parameter validation, mixed-person privacy, atomic retry,
bounded authored mood influence, and inherited learning/history/scheduler.
Seeded cognitive fixtures for the influence check are NOT acquired-learning data.

Record per-seed mood curves, actual body/episode recovery, native receipts/rejections,
survival, material use, cognitive/journal size, decision origins, computation and
simulated duration. Do not claim survival advantage from assigned support or
equate passing F4 with F5 emotional memory, trait learning or human psychology.

## Persistence and continuation

New ALICE-MOOD-F4-1 tables live only on a NEW backup copy. Matching legacy weather
or F0-F3 emotion saves may be attached explicitly. Preserve inherited private
experience, cue values, stress, pending native actions and scheduler cursor.
Record the source hash and authored parameter selection. Original saves and all
F0-F3 code/results remain unchanged. Replay uses the new profile's initial root;
copied old cognitive tables are retained as historical, inactive evidence.

Only F4 is authorized by this continuation request. F5 and later remain deferred.

Pre-measurement design review: the early sample is40s because native cold rises
at.012/s and is still below the declared.3 comfort allowance at10s. Zero stress
at10s would be correct, not a failed gradual-response mechanism. No F4 measurements
were used for this correction.
