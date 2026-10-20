# Living-world expansion plan

Prepared 20 October 2026 from `Prompt/Alice_Living_World_New_Agent_Prompt.md`.

## Current baseline

- The authoritative simulation is C++20; Python owns scheduling, cognition, persistence and the observer.
- Native/runtime compatibility is now UW7 / SQLite DB8 for new living-world runs. Existing UW6/DB7 worlds fail closed; no silent migration is provided.
- `underworld.stabilization` is the only prerequisite-aware survival executor. It owns an explicit handoff and a separate checksummed controller journal.
- Phase 9 learning is a failed, sealed experiment and remains outside live policies.
- The legacy observer and Phase 7 supervisor do not drive stabilization worlds.

## Milestone order

1. **A — Runtime consolidation (complete within measured scope):** add a documented living-world configuration and one CLI entry point; surface the active controller, goal attribution and model budget in observer state; preserve the legacy benchmark path; verify model-off save/resume.
2. **B — Trees and materials (current):** add authoritative tree lifecycle, finite harvest transfers, placement/collision rules and ledger tests.
3. **C — Crafting/construction:** add data-driven recipes, reservations, partial work and storage/pen construction.
4. **D — Animals/food ecology:** add bounded animal behavior, forage, troughs, eggs and validated food production.
5. **E — Planning/learning:** generalize prerequisite planning over real actions and measure adaptation with controls.
6. **F — Knowledge initialization/teaching:** distinguish new-world profiles, embodied teaching and direct operator injection.
7. **G — Integrated demonstration:** run a new four-inhabitant scenario with event-backed evidence and honest attribution.

## Milestone A contracts

- `config/living-world.toml` is an opt-in four-human development configuration; it does not change `config/survival.toml` or archived fixtures.
- `python -m underworld living-world init|attach|run|status` delegates to the existing stabilization controller. `init` creates a fresh world, while `attach` requires an explicit compatible backup.
- Model calls remain optional. The controller records per-agent calls, eligibility interval, fallback/model goal origin and bounded call allowance. Execution remains authored and native validation remains authoritative.
- Observer `/api/state` reports `controller.active`, selected-agent goal and controller budget. Read-only attachment remains read-only.

## Acceptance checks

- Existing Python/native regression suite remains green.
- New config validates and can initialize in model-off mode.
- New CLI can initialize, run a short bounded horizon, report controller state, save a backup and resume without resetting the world.
- Legacy `new`, `advance`, `run` and benchmark settings remain unchanged.

## Explicit non-goals for A

Trees, animals, crafting, breeding, cooking, neural training and true 3D mechanics are deferred to their listed milestones. No AGI, consciousness or endogenous model-improvement claim is made.

## Milestone B contracts

- New trees are `tree-1` (young, 2 kg), `tree-2` and `tree-3` (mature, 8 kg) in the small 2D region. Each has a stable identity, occupied radius, stage, health and tracked biomass.
- `harvest_branch` removes finite biomass and creates 90% wood / 10% fiber. `fell_tree` is an authored five-second no-tool bootstrap action that removes 90% of harvestable biomass as 80% wood / 10% fiber and leaves a 10% stump. `collect_wood` transfers an existing wood/fiber/wood-offcut/stone pile into carried inventory under the existing 2 kg capacity.
- Young-tree growth is an explicit configured boundary source, capped at 0.01 kg/s; mature trees and stumps do not grow. Tree-derived material totals close exactly; placement rejects occupied geometry instead of relocating an explicit requested pile.
- Native checkpoints are `UW7` and durable databases are `user_version=8` / checkpoint schema 7. Old formats remain historical and require their original runtime.
