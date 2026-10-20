# Stabilization amendment 2 — observed approach-point defect

Recorded before measuring controller version 2, 2026-10-20. Preserve the original protocol and both prior attempts.

In the valid amended seed-202 unavailable-food scenario, controller version 1 missed water despite available supply. The model selected eat, the food search ended at (1,1), and subsequent drink goals repeatedly reported no_perceived_route. The executor considered only the radial approach point to water. That point was blocked by the visible competitor at (2,1), although other points within gathering reach were accessible. There was no native rejection, timeout or missing inventory observation explaining this water failure. It is a planner geometry defect and a failed feasible-goal requirement.

Stop and retain this failed partial v2 evaluation, including raw transitions and source. Do not relabel it as a pass. Add development regressions for a blocked first approach direction and model-selected unavailable food followed by feasible crowded water.

Repair: controller version 2 considers bounded alternative approach directions using only perceived geometry and the existing waypoint/clearance helpers. The unchanged deterministic utility baseline already uses a ring of approach candidates. This is an authored navigation repair, not learning or a change to the native validator.

Before new policy measurements, freeze version 2's source hash and validate the development regressions. Use a new untouched cohort: seeds **808,909,1001**, with the same five scenario categories, four arms, finite quantities, call budgets, 90-second windows and all original thresholds. Keep the corrected, asserted competitor setup from amendment 1. Development remains seed 101. No acceptance gate is relaxed.

This is a new evaluation after a disclosed repair prompted by a failed earlier evaluation. Report the failed v1 controller and its exposed seeds separately from the fresh-cohort results. Do not combine them into a favorable aggregate or claim that the earlier hold-out remained untouched.
