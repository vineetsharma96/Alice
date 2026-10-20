# E evaluation fixture correction — 21 October 2026

The initial 929/1049 comparison used an inactive utility arm. The fixture set
agency.policy=utility but called storage.create(scripted=False), whose legacy
contract deliberately disables the Python utility scheduler. Those twelve
reference cases submitted zero actions. Keep the complete original evaluation
at artifacts/living_world_e_evaluation.json / data/living-world-e-confirmation-20261021.
Its successful E task receipts remain real; its utility comparison is invalid.
The report's original gates did not check baseline activation, so its passed=true
must not be interpreted as validating that comparison.

Fix fixture initialization to request the existing utility scheduler explicitly;
native scripted movement still stays disabled for body-enabled worlds. Add a
regression and a gate requiring active utility policy plus actual submissions
in every utility case. Neither the utility policy nor E planner is modified.

Use fresh confirmation seeds **1329/1449**, with the previously declared two
layout variants, unchanged 60-simulated/180-wall bounds and outcome thresholds.
Preserve the previous registration; create a separate final registration with
the current fixture/evaluator hashes before measuring. The E controller digest
must remain 2ba240466a8bb0850837af0fc7d3d842df305f99b61be4eaf9122c088a9ccb1c.
The added desktop model-off guard and its test do not affect benchmark policies.
Broken-tool comparison uses its separate prospective supplement.

Warm animal needs for 80 simulated seconds with native stepping before publishing
the NEW fixture checkpoint; all human policies remain inactive during that
preparation. Begin both utility and E measurement from identical physical needs,
inventories and animals. Record the actual starting tick instead of resetting
the body. Add a gate comparing initial native checkpoint hashes across every arm
for each seed/case. This prevents active utility warmup from changing only that
arm's starting body. Preparation time is separate from the 60-second comparison.
