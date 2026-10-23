# F0-F3 ownership and numerical contract

This is an opt-in, original Python component on the existing offline UW10W
runtime. No external service, model, neural training, shared vocabulary or Phase9
learner. Native bodies, inventory, action validation, climate and time remain
authoritative. Sources are pinned per attached world; mismatches fail closed.

`emotion_store.attach(source,destination)` uses SQLite backup to a NEW path,
then adds ALICE-EMOTION-1 tables. Original bytes are untouched. No in-place
migration and no UW9/H-profile migration. The weather format and physical journal
remain unchanged/replayable with the original controller. Older H worlds retain
their existing private learning and language: this milestone does not yet combine
their tables with weather. Do not claim that preservation is cross-profile integration.

One leased SQLite transaction restores native state, policies and each enrolled
person, consumes only their before/after native observations, executes a proposed
action through native validation, updates cognition, journals both physical and
cognitive changes, and publishes all heads. Failure rolls everything back.
Stable logical IDs deduplicate retry; conflicting reuse refuses. Pending native
actions persist in native checkpoints. There is no half-committed cognitive update.
All enrolled people are updated for every elapsed interval, even when another
person acts, using only their OWN observations and receipts. No goal/lexicon/mood
of another person is supplied. Out-of-band weather writes trigger head-drift
refusal. Observer inspection performs no writes or time advancement.

`emotion.py` owns the only affect pipeline. Body signals are dimensionless native
needs/fatigue, 1-health, wetness and cold burden. Affect valence [-1,1], arousal
and control [0,1]; slow stress [0,1]. Declared initial affect is (0,0,.5), stress0,
all learned cue values0. There is no animal/stranger threat prior. Instantaneous
distress target is maximum of needs, .7fatigue, injury and thermal discomfort.
Exponential tracking tau10s; slow stress tau120s; episode decay tau20s. Exact
constant-input integration is independent of update interval. Evolving conditions
use interval-end samples, a documented approximation, not exact trajectory
integration. Pauses have zero elapsed simulation time and cause no decay.

Appraisal records goal relevance, benefit, harm from new injury/cold change,
surprise, expected value/confidence, controllability and uncertainty about
responsibility. Mixed harm/relief can coexist. Scarcity, approach error,
contention, stale observation and unknown target are distinct. No result proves
malicious intention. Immediate episodes contain cause references, onset, intensity,
confidence and separate harm/relief. Stable injury is current discomfort, not a
new injury counted each tick.

An authored 2x2x2 context distinguishes perceived rain/dry, temperature below10C
or mild, and actual sensed covered/open. Cue harm/safety values [-1,1] learn by
time-weighted delta tau30s from own thermal/injury CHANGE. Harm target is negative
normalized rate (native proxy rates .012cold/s, .0015injury/s), clipped. Safety
target+.3 requires cold<.12 and no new injury; other intervals target0. Confidence
is 1-exp(-experienced_seconds/60), capped sample time1e6s. These are declared
algorithms, not discovered laws, calibrated probabilities or broad generalization.
Only learned mode may select an additional safety move: expectation<-.12,
confidence>=.2, base action rest, needs<.6, uncovered and a locally visible roof
with an own-perception route. Every move is natively validated. Original weather
and urgent survival goals retain priority. Frozen keeps initial values;
Three failed additional safety requests trigger a30 simulated second cooldown;
native rejection reasons remain intact and do not become food/animal threat labels.
disconnected learns but cannot influence; disabled retains exact old behavior.

Each update logs private observation IDs, immutable operation/receipt provenance,
prediction, relevant prior record IDs, appraisal, before/after affect/stress,
learning rule and changed decision. `emotion_operations` is the factual private
episode journal; cognition stores links, not a second narrative event history.
At most16 active episodes,64 recent references,8 cue classes,8 evidence links per
cue. Append-only journal stops explicitly at10000 cognitive/25000 physical ops.
No silent retention reset; indefinite disk boundedness is not established.
No stochastic cognitive transitions, so no additional RNG state is needed.

Directional relationship/regulation dictionaries are reserved empty/unsupported.
Slow stress and episode plumbing are not passed F4/F5 capabilities. Learned
regulation, trust, theory of mind, emotional symbols, morality, identity and
lifelong integration require later sequential experiments.

Run using `.venv/Scripts/python.exe scripts/emotion.py --help` after building the
unchanged weather runtime with `scripts/build_weather.ps1`. Attach a COPY of a
matching weather save, then use only emotion commands for that copy. CLI requires
durable `--id` on mutations; `save` uses a new destination; `replay` verifies both
journals. Source/runtime changes require an explicit later compatibility plan,
never rewriting a source pin to make an old world appear compatible.
