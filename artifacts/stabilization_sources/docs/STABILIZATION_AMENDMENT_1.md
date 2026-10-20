# Stabilization amendment 1 — fixture validity repair

Recorded after stopping the first partial held-out run and before corrected policy measurements, 2026-10-20.

The first held-out depletion case exposed a setup error: actor 2 has a seeded random initial position. The competitor request at relative tick 2 was rejected as TARGET_UNAVAILABLE in seed 202; the expected food depletion did not happen. The evaluator did not check the competitor's terminal receipt. Therefore the original run cannot establish depleted-target performance. Preserve its partial artifact, databases, freeze manifest and evaluator source; do not count it as a passed evaluation.

Repair the fixture by moving actor 2 through recorded native navigation to (2,1), within reach of food, in every scenario before evaluation. Keep actual setup time/body aging and movement costs; do not teleport or reset actors. Assert fixture reach/visibility and the competitor's completed receipt and food depletion. Validate setup/drain behavior separately before rerunning policy comparisons.

The controller remains exactly frozen at source ID d7ffabd1c487e9b2c8b335cd15efb1230c3be18c139be055d74d60a13ab6a23f. No policy update, prompt tuning, threshold relaxation, new seed selection or resource increase is permitted. Keep seeds 202/303/404, five scenarios, four arms, one inference call per model arm and 90 evaluation seconds. Use new v2 directories/artifacts. Original successful-looking depletion outcomes are invalid fixture evidence, not learner/controller successes.

This is a repair after observing held-out data, so the corrected run is an amended evaluation, not a pristine untouched hold-out. Disclose that limitation and retain all first-attempt outcomes. The amendment corrects test construction; it does not use outcomes to tune the policy.
