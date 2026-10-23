# F5: salience, emotional memory and revisable expectations

22 October 2026. **F5 passes its registered bounded gates.** F4 baseline
`16881c2` was pushed to `origin/codex/mood-temperament` before implementation.
F5 uses branch `codex/emotional-memory`. No release version, dependency, native
engine, historical experimental gate or failed learner was changed.

[Prospective protocol](MEMORY_F5_PROTOCOL.md) · [Run and resume](MEMORY_F5_OPERATIONS.md) ·
[Failed development and audit fixes](MEMORY_F5_DEVELOPMENT_NOTES.md).

## Implemented behavior

Each inhabitant has a private, bounded salience index into its existing factual
cognitive journal. Entries retain event and observation references, own perceived
context, simulated interval, appraisal outcome, receipt reference and uncertainty
about cause and intention. They are not invented narratives or copied memories
from other inhabitants. The index starts empty at enrollment; prior F4 learning,
affect, temperament, episodes and memories remain intact rather than being
retroactively relabeled as F5 experience.

The authored salience rule gives harmful, relieving and surprising experiences
greater retention priority. Divide 32 available links among represented context
classes; half each quota retains salient links and half retains recent links.
Retrieval considers only matching perceived weather/shelter context and weights
salience, duration and simulated age. Recent safe evidence can revise an estimate
without modifying old entries. Confidence measures retained support, not a
calibrated probability. Eviction removes an accessible index link; it never
rewrites the authoritative journal.

One existing F4 affect/appraisal update runs per interval, followed by indexing.
Existing cue learning continues and supplies appraisal surprise. Connected F5
retrieval supplies the prediction for the existing bounded safety alternative.
The native weather policy, urgent needs, cooldown, local visibility, routing and
native action validator retain authority. This is acquired experience interpreted
by authored algorithms; it is not learned memory architecture or motor control.

F5 attaches only to a NEW backup with ALICE-MEMORY-F5-1 tables. Original weather,
F0–F3 and F4 runtimes remain byte-identical and their old saves remain runnable.
Inherited scheduler position and pending native actions are preserved. Atomic
commit, rollback, operation deduplication, source pins and native replay remain
active. No direct cognition injection is used in the native study.

## Prospective confirmation

Development used seed 53. After retaining the failed development results and
repairing the mechanism, development 3 passed. Its unchanged implementation,
tests, observer, runner and revised prospective protocol were sealed as **59
files** before confirmation. Seeds 19201, 19207, 19213, 19219 and 19231 all pass
every gate; thresholds were not changed against held-out measurements.

Finite-stock native setup builds a real shelter and gathers/consumes food and
water. Each arm receives 120 seconds of actual cold rain, supplied warm recovery,
then 120 seconds of physically safe experience in the same coarse perceived
context and another warm recovery. Feeding, travel and rest consume actual native
time and finite supplies. These are guided conditioning apparatus, not autonomous
regulation. Probe copies preserve the conditioning world and use varying actual
temperatures of 5–9°C and rain of 8–12 mm/hour.

| Additional caution / native action | Connected memory | Memory disconnected: unchanged F4 choices | Frozen F5 encoding |
| --- | --- | --- | --- |
| Relevant harmful experience | 5/5 move; 5/5 reach actual shelter | 5/5 move; 5/5 reach actual shelter | 0/5; rest |
| Unrelated context | 0/5; rest | 0/5; rest | 0/5; rest |
| After relevant safe evidence | 0/5; rest | 0/5; rest | 0/5; rest |

All 45 probe actions complete natively. All 15 main conditioning arms complete
**2,040 accepted requests and 2,040 completed actions**, excluding setup, probes
and duplicated resume branches. Native audit finds zero rejection or failure.
Acceptance, completed movement and actual shelter entry are measured separately.
All inhabitants survive, material accounting closes and no material refill occurs.
Conditioning physical histories match across all three arms.

F5's pre-decision expectation changes from −0.883944 to −0.046018 after safe
experience, a revision of +0.837926. Twenty negative links remain in the final
main index, and the entire pre-correction journal stays unchanged. Unrelated
context has zero support. Frozen encoding remains empty while the older F4
learner continues; it freezes F5 acquisition specifically. Disconnected memory
encodes the same observations but does not control decisions.

The unchanged F4 baseline succeeds equally on these probes. **This study does
not show superiority over F4.** Identical conditioning histories explain the
identical learned values across seeds. It tests a narrow authored context
representation, not general memory understanding or a varied natural population.

Each main arm ends at 930.75 simulated seconds, starting from the actual 87.75s
setup head: 843 seconds of continuous conditioning. Confirmation costs 1,430.662
wall seconds with at most two independent seeds running together. Per-seed wall
times are 519.190, 528.107, 549.773, 558.807 and 361.070 seconds, all below 600.
These overlap and must not be summed as elapsed confirmation time.

Connected relevant/unrelated/corrected probe commits average 0.139/0.133/0.228
wall seconds. Disconnected averages 0.171/0.174/0.154; frozen 0.142/0.134/0.175.
These include native execution, storage and concurrent-machine contention; they
are not isolated CPU benchmarks. Final main index sizes are 17,943/17,946/165
canonical bytes for connected/disconnected/frozen. Audited peak is 17,994 bytes,
below the prospective 24,000-byte limit, and retention never exceeds 32 links.
SQLite sizes and all per-run measurements are retained in the raw result.

## Independent verification

The independent auditor verifies **65 actual F5 SQLite saves plus five setup
worlds**. It replays native commands, records actual submit acceptance and terminal
completion separately, independently recomputes salience and retrieval from own
native observations, reconstructs retention, verifies immutable factual links,
and checks every probe's history against its parent. All five fresh-process
mid-conditioning resumes match exactly. A separate reconciliation binds raw
results to actual saves, source seal, physical history and behavioral gates.
Disposable-copy checks also reject a resealed altered memory outcome and a
rewritten journal appraisal; the original evidence save remains byte-identical.

Successful independent audit windows total 334.624 wall seconds; some overlap.
That sum excludes reconciliation and the retained failed audit attempt. Ten older
G/H/gap/weather/emotion/F4 source registrations remain unchanged. Phase9's failed
result and evidence remain preserved; its learner is outside every live policy.

Fresh **6 F5 + 5 F4 + 7 emotion + 28 weather = 46 tests** pass, including privacy,
correction, retention, inherited state, native pending-action resume, atomic
rollback and retry, disabled native equivalence and observer read-only behavior.
The older 335 Python/4 native result remains historical; that complete suite was
not rerun for this additive Python profile. Final static inspection parses 185
Python production/test files; it is not exhaustive dynamic branch coverage.

Headless Edge desktop 1440×900 and mobile 390×844 checks pass: actual 3D rendering,
readable memory diagnostics, collapsed private evidence, no overflow/page errors,
unchanged paused native hash and POST refusal. The observer at
http://127.0.0.1:8780 displays a labeled guided held-out probe. Its current
expectation includes any renewed cold experienced during the probe; the gate
uses the separately recorded prediction before that action.

## Existing-world continuity

`data/mood-f4-life.sqlite` remains unchanged at 1,800 simulated seconds, SHA256
`c3eac345940d52c613fc27003b95da446e0a5dd2bbe5c626a52ba88669b88d29`.
The final-profile NEW copy `data/memory-f5-final-life.sqlite` progresses through
2,100 to **2,400 seconds**, with inherited bodies, learning, temperament, policies,
historical tables and scheduler. The earlier failed-profile development copy is
retained separately with its exact archived source; it was never repinned/reset.

All four inhabitants finish at health 1. Scheduler cursor advances 1,080→1,490.
The 410 new completed actions are 67 gathers, 63 moves, 213 rests, 30 eats and
37 drinks, with zero failure or fallback. There are 409 authored weather choices
and one acquired-memory caution choice using authored routing. Agent 4 completes
that move and enters a native shelter. Its retrieved expectation is −0.333808;
the old F4 cue estimate on that same observation is +0.183936 and would not meet
the −0.102947 caution threshold. This is an attributable decision change, not a
controlled claim that the whole life survived because of memory.

Food remaining 3.4 kg + ingested 4.6 kg = initial 8 kg; water remaining 9 kg +
ingested 7 kg = initial 16 kg. Carried balances are zero. No weather forcing,
material source, refill, body reset or scheduler restart occurs. Four private
states occupy 100,814 canonical bytes; individual memory indexes are 16,561–16,663.
The two execution windows cost 417.007 wall seconds, excluding post-window replay.

A fresh process continues a separate copy of the untouched 2,100s backup to the
same exact 2,400s native/private/policy hash and cursor, costing another 133.451
wall seconds before its replay. Final hash:
`ac469c335b603974a4edc1498f9544d81c370a6a35577e7c529890ea5cb2f0bf`.
The continuity proof independently checks inherited cognition, original source
hash, historical table equality, native journal prefix, ledgers and resume.
No autonomous simulation is left running after these bounded windows.

## Failed experiments and remaining limits

Development 2 FAILED: support decayed too far and global salience retention
displaced relevant safe evidence. Its negative expectation did not correct even
though caution stopped through uncertainty. Exact sources, native saves and raw
failure remain. A reporting-path error, an unsuccessful retention draft and
supplemental audit integration errors are documented separately in development
notes, including the invalid initial acceptance counter. None is relabeled a pass.

F5 covers coarse personal weather/shelter experience and one bounded safety
alternative. It does not provide general episodic reasoning, learned context
representations, calibrated confidence, helper selection, emotional language,
trait learning or improved natural survival. Memory sampling/retention depends
on event granularity; full trajectory-rate invariance is not established. F4's
existing constant-input mood-rate checks remain unchanged. Cognitive/physical
journals still stop at 10,000/25,000 operations; indefinite disk operation and
large-population scalability are unproven. Actual SQLite evidence stays local
under ignored data paths; source archives and audit inventories support reproduction.

F6 and later have not been started. Existing H learning/private vocabularies and
weather saves remain preserved in their respective profiles; full combined
H/weather/communication integration is still a later gate. No consciousness,
general intelligence or civilization-emergence claim is made.
