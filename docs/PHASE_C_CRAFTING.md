# Milestone C — crafting and construction contract

Authored contract fixed before implementation, 20 October 2026. C++ is the authority; no model or Phase 9 learner is part of this milestone. This work follows an independent review of Milestone B, whose original reports remain historical.

## Quantities and work

All masses are integer micrograms (1 kg = 1,000,000,000 ug). Recipes are native data records, not agent knowledge.

| Recipe ID | Carried ingredients | Product | Waste | Work | Required tool |
|---|---|---|---|---|---|
| crude_axe | 0.45 kg wood + 0.05 kg fiber + 0.20 kg stone | 0.70 kg owned axe, durability 8 | none | 4 s | none |
| planks | 1.00 kg wood | 0.80 kg carried plank | 0.20 kg carried wood_offcut | 3 s | usable owned axe, 1 use |
| storage_box | 0.80 kg plank | 0.80 kg box, 4 kg contents capacity | none | 8 s | none |
| trough | 0.80 kg plank | 0.80 kg trough, 4 kg water capacity | none | 8 s | none |
| fence | 0.40 kg plank | 0.40 kg solid fence post/segment | none | 4 s | none |
| gate | 0.40 kg plank | 0.40 kg gate, closed initially | none | 4 s | none |

The existing finite B wood stack represents branches/log stock; it is not relabeled inert material. Branch harvest remains a slow tool-free bootstrap. Felling now requires the owned usable axe and spends one use. Breaking converts the whole axe's original wood/fiber/stone composition into carried scrap constituents; no matter disappears. Skill is an authored successful-work counter, distinct from procedural knowledge; initial recipes require skill zero. Future contracts can require a higher counter.

## Actions, reservation and restart

`craft` takes recipe_id and optional tool_id; inputs stay carried and locked only by the actor's existing single pending action until terminal completion. They are revalidated and atomically transformed only at completion. Cancellation or death before completion consumes nothing. Outputs must fit the combined 2 kg carrying capacity, including owned tools.

`begin_construction` takes recipe_id and explicit x_m/y_m. On terminal completion it transfers ingredients from the actor into a stable construction site and reserves a circular footprint of radius 0.5 m. It creates no completed object. `work_construction` adds actual fixed-step work to that site; work survives cancellation, death, checkpoint and process restart. A site can have only one worker at a time. Further requests reject with TARGET_BUSY. Completion changes the site into the chosen object without creating matter. Cancellation through `cancel_construction` returns composition to the creator's inventory only if capacity allows; otherwise the site remains. Starting sites count against the finite 200-entity quota.

`store_item`/`take_item` transfer an exact material mass between carried inventory and a completed box, rechecking access, capacity and availability on completion. `fill_trough` accepts real carried water only. `toggle_gate` changes its authoritative collision radius between 0.5 m and zero; closing rejects occupied space. A fence is a circular solid segment, and a pen must be formed by overlapping collision exclusion zones with gap-free spacing; no decorative ownership/containment claim is made. Animal behavior is Milestone D.

Site/output placement must be visible, within 1.5 m, inside bounds, and clear of bodies, trees, piles and other structures. Output footprints and completed closed fences/gates block native movement and sight. A site consumes no new work when access, tool/skill or life prerequisites fail. Stable IDs and reservations persist natively. Idempotent request IDs retain existing semantics.

## Knowledge and evidence boundaries

The registry is exposed only through an explicitly privileged operator API. Agent observations do not enumerate recipes. The production demonstration uses an explicitly operator-assigned procedure, stores its source separately from the authored skill counter, and executes through the existing coordinator and lease. It is not autonomous discovery or learned planning. General task planning and teaching remain milestones E/F.

## Acceptance checks fixed before measurement

Require: native and Python regressions pass; exact material and waste closure through the full branch/stone/fiber → axe → felled wood → plank → usable box chain; interrupted/resumed craft and construction match uninterrupted native state; storage transfer round-trip cannot duplicate; missing/broken tools, insufficient/full inventory, hidden/unreachable/blocked placement and competing site requests reject without losses; partial work and cancellation persist; closed fence/gate block actual movement and an opened gate allows passage. Retain raw terminal receipts and simulated/wall time. Old UW7/DB8 worlds must fail closed under the new UW8/DB9 runtime; no migration or change to sealed Phase 9 evidence.

Milestone A's model pacing/global-budget acceptance remains incomplete in the prior handoff. This milestone uses model-off operation and does not claim to complete that missing model-enabled gate or the isolated supervisor integration.

## B review corrections applied before final C validation

Initial actor placement reserves the stone pile footprint; a 300-case sweep over seeds 0-99, 4/8 inhabitants and 8/16 m layouts is a regression gate. Explicit branch/felling pile anchors are limited to 1.8 m from the source tree, preventing remote product placement. Initial failures and superseded candidate checks remain separate evidence; these corrections do not change the recipe quantities or acceptance thresholds above.

Target selection in the assigned production driver is restricted to fresh permitted observations and own tools. Full snapshots used to verify contents and ledgers are operator diagnostics only. Construction/storage contents are not silently granted to the planner.
