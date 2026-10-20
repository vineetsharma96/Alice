# Food execution repair protocol — 21 October 2026

Written before measuring the modified executor. This is authored prerequisite
execution, not learned planning or a replacement Phase 9 experiment.

Development seed 21; separate confirmation seeds 515 and 626. Use new native
worlds and new SQLite saves. Do not modify historical studies or replenish a
running world. Only permitted own inventory, freshness, ingestion counters and
visible resources may select actions. Native validation stays authoritative.

Cases: carried plant food; carried eggs below the usual 0.2 kg meal size;
mixed carried food; reachable forage requiring gathering; absent/depleted forage;
food expiring between selection and completion; interrupted consumption and
save/resume. Include a second inhabitant in the assigned-procedure helper check.

Thresholds: every feasible consumption request must complete and increase the
native food-ingested reservoir by exactly its mass. Gather then eat must use real
native transfers. No request may target already observed empty forage or request
unavailable carried food. Legitimate expiry after reservation must retain its
native failure, without overdraft, and recover within the existing retry bound.
Interrupted persistent execution must preserve native head, memories, controller
and scheduler through save/resume, with exact replay. All integer ecology balances
must remain zero. Existing full Python and native regression suites must pass.

Record successful actions separately from goal completion: a partial meal helps
the body but does not satisfy the unchanged 0.2 kg ingestion goal. Report model
calls (zero in these checks), action rejections/failures, elapsed simulated and
wall time. No claim of general husbandry, long-term survival or model improvement.

Fixture amendment before a separate final measurement: the first evaluation's
egg fixture left legacy food within reach. Both arms legitimately gathered it,
so the assertion that only 0.06 kg was available was false. Preserve that failed
evaluation at data/food-repair-eval-20261021. Move the same legacy stock outside
the initial local test area, without deleting mass. Seeds 515/626 are now
development evidence; final confirmation uses fresh 717/818. Policy and outcome
thresholds remain unchanged. These seed variants test receipts and accounting,
not broad geometry generalization.
