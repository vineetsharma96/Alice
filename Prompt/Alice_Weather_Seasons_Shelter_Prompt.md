# Alice — weather, seasons and shelter

Implementation prompt for the next coding agent — 22 October 2026
Repository: https://github.com/vineetsharma96/Alice

## Master instruction

```text
Continue Alice. Implement an opt-in weather, season and shelter-survival system in ordered stages W0–W6 below. Weather must change authoritative world conditions, inhabitants' observations, exposure and useful decisions. Preserve the current simulation and existing experimental evidence.

Start by inspecting actual repository instructions, HANDOFF.md, docs/STATUS.md, current physical/crafting/ecology contracts, current developmental protocols and running-process records. The reviewed handoff marks developmental H0/H1 as work in progress. Verify its current status; do not modify registered sources while a study is actively running. Prepare weather work in an isolated branch/worktree or additive scaffold until integration is appropriate. Never kill an unrelated experiment, rewrite its evidence or silently label intelligence complete.

Execute runnable stages sequentially with appropriate checks, updating a concise HANDOFF.md. Do not stop at a plan. Mark uncompleted stages explicitly if a session/resource blocker prevents continuing. No emotion system is requested in this milestone. Preserve the failed sealed Phase 9 experiment and keep its learner outside live policies.

This is a configurable simulation model, not real-world weather forecasting. Keep the first version lightweight: current authoritative 2D mechanics and a small region, with existing 3D visualization. Do not add a fluid/atmospheric solver, global climate model or heavyweight service.
```

## W0 — contracts, compatibility and safe baseline

```text
Reuse C++ for authoritative environmental state and consequences, Python for scheduling/decisions/storage, and the existing observer for visualization. Establish contracts before editing shared modules.

Define WeatherState, SeasonState, ClimateConfig, LocalExposure, ShelterState and WeatherObservation. Include physical units where meaningful, explicit dimensionless abstractions, version, tick, sources and limits. Separate privileged exact diagnostics from each inhabitant's observations.

Add an opt-in configuration. Existing benchmark, study and default worlds keep their recorded conditions. Preserve prior runtimes before changing source/build identities. Supply an explicitly tested migration only if practical; otherwise require a NEW weather world and explain how to inspect older saves with their matching runtime. Never reset bodies/resources or bypass source checks.

First acceptance: the current model-off baseline still works, existing tests remain green, configuration validation rejects malformed/nonfinite inputs, and weather-disabled worlds do not acquire environmental damage or unexpected stock changes.
```

## W1 — persistent weather and seasonal clock

```text
Implement native weather: clear, cloudy and rain, with bounded precipitation intensity, ambient temperature, cloud cover and wind vector. Cold is a temperature condition, not necessarily a mutually exclusive weather type. Defer snow, floods, lightning, wildfire and destructive storms to later work.

Use a finite seeded weather-transition model. Seasons affect the configured ranges/probabilities for temperature, rainfall and daylight input. Persist current/target conditions, transition progress, PRNG state and next change schedule in checkpoints. Rates and distributions are authored environment rules, not measured predictions for a real location.

Represent spring, summer, autumn and winter as four declared phases. Their names describe the chosen fictional climate, not all Earth climates. Smooth temperature/energy envelopes at phase boundaries; avoid unexplained instant shocks. Weather can vary within a season.

All environmental time derives from committed simulated ticks. Pauses, viewer polling, browser refresh, shutdown and a new chat do not advance the calendar. Resume continues the exact saved weather. Start a season/year only through explicit new-world initialization or a recorded operator branch.

Support configurable simulated year length. A short research profile may use four 600-second seasons for 2400 simulated seconds per year; label this accelerated and do not silently rescale bodies, tool wear, animal aging, crop growth or the existing 86400-second day. Normal and accelerated profiles must state their time assumptions, and may override the illustrative durations before measurement with documentation.

Acceptance: repeated seed/config/actions reproduce weather on the same supported runtime. Mid-transition save/resume matches uninterrupted execution. No conditions change during pause/inspection. Boundaries, long tick counts and fractional transition progress are covered. Document exactly how seasons interact with the existing daylight source.
```

## W2 — environmental effects with explicit accounting

```text
Introduce local rain exposure, wind exposure, cold burden, wetness and drying using documented bounded rules. Start with dimensionless wetness/cold-burden proxies if that is the feasible model. Do not label those as kilograms of body water or a realistic thermoregulation model.

Rain/wind/cold can increase exposure; dry protected conditions reduce it. Sustained severe exposure can increase fatigue and eventually reduce health through explicit native rates. Keep hunger/thirst mechanics and health effects individually observable and explainable. Select parameters so the small region allows time to react; never award shelter success merely by making weather harmless.

If implementing actual body heat or water reservoirs instead of proxies, track exchanged energy and water with stated boundary sources/sinks and units. Couple to the existing thermal network only through implemented exchanges; its four vessels do not already provide a whole-world atmosphere.

Seasonal tree/forage growth modifiers must act on explicit configured ecological boundary sources and capacities. The current biomass model is an authored input, not photosynthesis. Zero-regeneration conservation fixtures remain zero. Winter must not delete standing wood or magically turn food into another material. Scarcity emerges from supply/consumption under declared rules.

Optional rain collection is a separate bounded feature: native catchment area, actual elapsed rain and explicit weather-boundary water input. Conversion and vessel overflow need tests. Never credit the same catchment twice, refill all troughs automatically or claim a closed water cycle without implementing one. Defer it if W1–W4 are already at resource limits.

Acceptance: weather affects exposed inhabitants according to actual ticks; recovery occurs under the declared conditions; multiple damage channels are not double counted. No negative stocks or unauthorized resource creation. Record body outcomes and all environmental ledger changes in evidence.
```

## W3 — useful shelters built from real materials

```text
Extend current native crafting/construction with a small, fixed shelter blueprint first. Declare inputs and work before coding: wood/planks, fiber if used, waste, tool use and repair costs. Choose exact quantities that fit the region's finite stocks and carrying limits. Supply a feasibility calculation before starting an integration run.

A shelter has a stable ID, footprint, roof coverage, condition, capacity and construction progress. Materials are reserved/consumed through existing validated transfers and native work; no free completion when a goal is assigned. Interrupted work persists. Define construction-stage protection explicitly, defaulting to no roof protection until the required stage is complete.

The current physics is 2D. Represent roofs as native coverage regions with illustrative vertical geometry; keep wall collision, door access and roof coverage distinct. Do not make the entire interior an impassable solid circle. Reuse existing placement rules, clearances and construction reservations. Several people may share a shelter only where physical space permits. Doors/gates must not seal a worker inside without an exit path.

Rain protection depends on actual position under coverage; wind protection depends on declared wall/roof design and may initially be a simple factor. A roof can reduce rain while providing limited cold protection. Report those coefficients and their approximation. A nearby shelter gives no remote protection. Reading a shelter recipe gives no material, condition, skill or physical coverage.

Scope repair through real material/work if condition is used. Do not add structural storm destruction before ordinary construction/occupancy works.

Acceptance: an identical exposed and sheltered body receives different measured exposure; outside/edge/inside classification works; construction consumes real stock; mid-work restart matches; occupied/blocked sites fail without losses; completed geometry permits entry/exit; multiple builders cannot duplicate work/materials.
```

## W4 — inhabitants respond through their own senses

```text
Add permitted observations: locally felt cold/wetness, visible rain/cloud conditions, noticed wind and observed shelters. Any remembered shelter/resource coordinate must originate from that person's actual observation. An exact global forecast, hidden shelter map, another person's exposure or future weather RNG must never enter a policy context.

Implement model-off baseline goals: seek_observed_shelter, reduce_exposure, build_simple_shelter, repair_shelter and prepare_supplies. Decompose construction using existing real actions and prerequisite handling. Define priorities so urgent thirst/food and environmental exposure can preempt safely between actions. Prevent oscillation between two urgent goals using bounded hysteresis and resumable state.

Separate demonstrations:
- Operator-assigned: the user explicitly requests a shelter task. This proves execution.
- Authored autonomous baseline: exposure/observed conditions trigger a programmed goal. This proves reactive autonomy under authored rules.
- Developmental policy: use only if H learning gates actually pass and integration is separately evaluated. Do not represent hand-coded shelter logic as baby-like discovery or general intelligence.

Preparation for seasonal risk can initially use an externally taught schedule or learned own-experience estimate. Record the source; nobody automatically knows the true future weather. No automatic shared knowledge. Existing invented-language work must not be assumed complete; retain text communication or no communication until that channel has evidence.

Acceptance: a sheltered destination is physically reached, not credited from a plan; hidden shelters remain unknown until observed; blocked paths/depleted materials/timeouts produce bounded recovery; no indefinite life-threatening build loop. Log decision origin, preemption, actual effects and remaining needs.
```

## W5 — observer and operator experiments

```text
Show current season, weather, temperature/units, rain, wind, simulated calendar and actual exposure. Add lightweight cloud/sky/rain presentation and seasonal ground/tree appearance based on native state. Rendering must not generate a separate weather clock. Decorative leaves/particles never provide collision, moisture or resource effects.

Selected-agent panels show wetness/cold burden, actual protective shelter, active goal and last observed environmental evidence. Separate privileged climate diagnostics from inhabitant knowledge. Show shelter coverage/work/materials/condition and safe entry points. Follow existing read-only viewer/single-writer semantics.

For controlled experiments, allow recorded operator weather forcing only in guided mode or an explicit branch, with duration and native state/version checks. Display forced weather as an external intervention; do not count it as a spontaneous weather outcome. Never mutate hidden state through a viewer GET or unlogged admin shortcut.

Acceptance: headless and viewer-driven recorded actions produce the same native results. Paused rain animation cannot advance world weather. Reconnection reloads current state without reapplying damage or repeating interventions. Test desktop/mobile layout and actual browser errors; report visual checks not performed as unverified.
```

## W6 — survival and continuity evidence

```text
Preregister a bounded evaluation before measuring the final policy. Keep development seeds separate from held-out conditions, preserve failures and use the same initial states/weather schedules across matched comparisons.

Cases:
1. Mild clear weather: no unnecessary environmental damage.
2. Rain plus cold with reachable shelter: compare protection against exposed control.
3. Rain with no existing shelter but feasible construction materials and sufficient warning/reaction time.
4. Depleted material or blocked site: failure remains explicit; no invented building.
5. Several inhabitants sharing limited shelter capacity and competing needs.
6. Seasonal resource changes with explicitly accounted inputs.
7. Mid-weather-transition, mid-build and in-shelter fresh-process restart.

Compare current survival-only policy, authored weather-aware policy, and any experimental learned policy separately. Report actual health/exposure, time to protection, goal completion, material/work cost, wasted trips, policy/fallback origin, native failures, resource balances, simulated/wall duration and retained replay scope. Do not assume every fearful-looking animation or completed roof means successful survival.

Begin small: one inhabitant for physics/coverage checks, then four for integrated behavior. Use finite stocks and a declared computational budget. Run progressive continuous horizons through at least one seasonal boundary if affordable; if a full accelerated year cannot complete, report the reached horizon rather than summing separate lives. Do not reset resources/bodies between continuity segments.

Passing software checks and successful survival are separate gates. Do not weaken thresholds after observing results. Keep active source pins stable during registered measurement. Final report must say which of weather physics, construction, authored response, learning integration and long-horizon survival actually have evidence.
```

## Required delivery

- Native weather/calendar, environment and shelter contracts with units and validity limits.
- One opt-in weather profile and documented new/run/save/resume/inspect commands.
- Runnable baseline, implementation checks and a bounded integrated demonstration.
- Weather/season/exposure/shelter information in existing viewers.
- Version/source compatibility notes and preserved earlier worlds/studies.
- A concise HANDOFF.md, updated STATUS.md and a WEATHER_SEASONS_REPORT.md with observed results, failed cases and remaining stages.
- No automatic release number or claim of consciousness/general intelligence.

## Repository references

These are project integration references; read their current versions before implementation:

- https://github.com/vineetsharma96/Alice/blob/main/HANDOFF.md
- https://github.com/vineetsharma96/Alice/blob/main/docs/STATUS.md
- https://github.com/vineetsharma96/Alice/blob/main/docs/PHASE_C_CRAFTING.md
- https://github.com/vineetsharma96/Alice/blob/main/docs/PHASE_D_ECOLOGY.md
- https://github.com/vineetsharma96/Alice/blob/main/docs/PHASE5_THERMAL.md
- https://github.com/vineetsharma96/Alice/blob/main/docs/LIVING_WORLD_G_REPORT.md

If adopting physical heat/radiation equations, verify the primary educational sources already listed in docs/REFERENCES.md and document their actual assumptions. Weather transitions, season lengths, exposure proxies, protective coefficients and body-response rates in this milestone are authored choices; do not present them as validated meteorology or human physiology.

## First task to paste

```text
Read Alice_Weather_Seasons_Shelter_Prompt.md and the repository's actual current
handoff. Start W0 and W1, then continue sequentially through validated stages.
Check active developmental studies before editing shared/registered sources.
Implement real weather/season state and shelter effects with persistent saves.
Keep a runnable baseline, record actual evidence and failures, and leave a
concise handoff. Do not substitute visual effects for physical consequences.
```
