# W6 prospective matched evaluation

Declared before final policy measurement, 22 October 2026. Freeze actual sources
after W0-W5 development passes, then evaluate untouched seeds13001/13007/13009.
Development53/71 only. No learned weather-policy arm: H learning gates do not
establish weather integration. Compare survival-only and authored weather-aware
logic with identical initial states and weather schedules; operator-assigned
construction remains a separate execution result. No LLM calls.

Controlled held-out rain/cold conditions are temperature/rain/wind-x:
13001=(-6C,8mm/h,2m/s),13007=(-10C,10mm/h,4m/s),13009=(-14C,12mm/h,6m/s);
wind-y1m/s,cloud.9. Development53=(-10C,12mm/h,4m/s),71=(-6C,8mm/h,2m/s).
These are recorded guided interventions, not spontaneous weather. Natural seeded
weather is retained in the separate continuous life. Native policy actions last
at most5s; matched arms finish at exactly the120s deadline with an explicit idle
tail shorter than5s, avoiding unequal final clocks. Report that tail separately.

Finite budget:1200wall seconds overall,600perseed. Each native batch<=10000ticks,
all clocks in simulated seconds, standard dt.25s. Preserve incomplete/failed
results and never tune sources using held-out outcomes. Any fix after confirmation
requires new seeds and a new registration. Record actual native receipts, health,
wetness/cold, cumulative exposure damage/fatigue, protection time, source/material
balance, work, goal origin, failed/tripped actions, fallback and wall/sim duration.

Cases and thresholds:

1. Mild clear native life,100s, no environmental health loss (>1e-12 fails).
2. Native rain+cold,120s, physically reachable completed lean-to. Identical
   matched policy arms: weather-aware must actually reach protection within60s;
   environmental health loss at least.02 lower than exposed survival control
   and final health no worse. Mean/final proxy burdens reported separately.
3. No existing roof, real reachable tree/pile supplies, sufficient initial needs
   and reaction time: weather-aware must complete real roof work and reach its
   protection within120s. Report authored skill/material/exploration scaffolding,
   not a learned discovery. The baseline is allowed to survive by other means.
4. Depleted material and blocked placement: zero completed roofs and zero lost
   reserved ingredients on refused creation; explicit bounded stop<=96decisions.
   Legitimate scarcity is not a policy failure.
5. Four-person integration under one capacity4 roof: actually protective bodies
   counted natively, no overlap/capacity overcredit, urgent needs may preempt;
   actual protection reached by all feasible actors within120s. An additional
   capacity overflow fixture must leave excess occupants unprotected.
6. Seasonal tree/forage boundary inputs reconcile exactly; zero configured rate
   remains zero. Use identical initial stocks and elapsed time, compare seasonal
   modifiers; no deletion of winter stock. Animal survival not evaluated here.
7. Mid-transition, mid-build and sheltered restart match uninterrupted native
   checkpoints exactly, including PRNG, partial work, bodies and resources.

Software gate requires all relevant native/Python weather checks and preserved
original baseline/source pins. Exposure/construction gate requires cases1-3 and
7 thresholds; scarcity/occupancy/accounting are integrity gates. If any fail,
report the corresponding gate failed even when software tests pass.

Continuity is separately measured, one actual four-person life with finite food
8kg/water16kg, no regeneration/reset/replenishment. Physically executed initial
scaffolding is recorded. Continue same save progressively to300,600,1200 and2400s
as budget permits. At least one600s season boundary desired; a full year is a
separate gate and passes only if actually reached with all4alive/health>=.5,
no state reset, exact native replay and no unauthorized stock inputs. Record
time excluding and including setup where measured. Do not sum separate lives.
Survival failure or budget exhaustion does not erase valid physical evidence.
