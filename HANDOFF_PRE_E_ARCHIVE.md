# Food execution repair handoff - 21 October 2026

Current controller source now supports carried plant food/eggs, partial meals,
and visible-forage gather/eat sequences. Read docs/FOOD_EXECUTION_REPAIR.md and
docs/FOOD_EXECUTION_PROTOCOL.md for measured results and remaining gaps.
The current executable is dist/UnderworldLab.exe; packaging evidence is now
artifacts/food_repair_package.json, not the historical code_audit package report.
For pre-repair saves use build/runtime-before-food-fix-20261021/UnderworldLab.exe.
That archived executable was verified against the prior 120-second audit world.
Do not silently migrate/reset controller-pinned saves. Phase 9 remains sealed.
The previous audit handoff below describes its archived runtime and evidence.

---

# Underworld Lab � code audit and desktop launcher handoff

Current application **0.11.1**, native **UW9 / DB10 / checkpoint 9**, native build unchanged at `832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896`. Read [README](README.md) for detailed launch/build/save instructions and [audit report](docs/CODE_AUDIT_REPORT.md) for fixes and verification. D's original handoff is [archived](HANDOFF_D_ARCHIVE.md).

## Launch

- Double-click run.cmd, execute `bash run.sh` in Git Bash, or run dist/UnderworldLab.exe.
- Default: model-off D profile, persistent user-local UnderworldLab/world.sqlite, 30 simulated seconds bounded by 240 wall seconds, read-only viewer on 127.0.0.1:8768. It stays available after the run; Ctrl+C closes it.
- `--db PATH --seconds N --port 0 --no-browser --exit-after-run` provides a bounded headless invocation.
- `UNDERWORLD_SOURCE=1` forces the source launcher. Direct source commands need UNDERWORLD_BUILD=build/living-d.

## Important compatibility

This audit changes Python orchestration/controller source pins. Do not run new code against old D evidence expecting migration. The previous exact project runtime is preserved in build/runtime-before-code-audit-20261020 (SHA manifest included), and its CLI was verified against the original D database. README has commands to use it. Current executable/source saves interoperate when source/native identities match. No resets or resource refill occur on resume.

## Maintenance scope

Fixed generator action loss, multi-transaction observer state, read-only 2D controls, partial invalid initialization, working-directory config defaults, historical-build/evidence bootstrap hazards and frozen source checksums. Consolidated viewer/state projection, culture recall, stabilization initialization, journal checking, checkpoint/package constants and C/D continuity drivers. Native physics/action validation was not weakened. Models stay off; failed Phase 9 learner remains excluded.

Executable: dist/UnderworldLab.exe (unsigned Windows x64; not committed). Build recipe: requirements-build.txt + scripts/package_app.py. It bundles runtime DLLs and local assets, not saved worlds/models/environment files. Packaged AppContainer --cli run is explicitly unsupported; use original source isolation workflow.

Audit evidence is under artifacts/code_audit_*. Prior C/D/Phase 9 evidence is retained. Keep the existing unrelated OpenCode/npm work. No push is authorized by this audit request.

## Verification

Final verification: **183 Python tests** (229.709 s inside unittest) and **four native checks** pass. Static checks are clean. The standalone executable reaches **120 continuous simulated seconds / 169.582 wall seconds**, completes four human drink goals through 15 native actions, retains all six bodies alive at health 1.0, and passes replay. Its complete native head equals the original final D 120-second head (`da68713042375015e7fc88ba50f863072b4da1416620232215b3ada187837c90`), demonstrating unchanged native behavior for this case. Separate reduced-PATH smoke checks prove executable/source/executable save continuation and packaged backup/replay. Both packaged UI pages pass read-only/asset/privacy checks with no JavaScript errors.

The verifier-owned port 8769 viewer has been stopped; no model server was started. Existing user viewers were not controlled. The source bootstrap and source/packaged Bash/CMD launch paths were exercised.

## Remaining milestones

E general prerequisite planning/recovery and measured adaptation remains next only when requested. F knowledge/teaching and G integration remain later. Breeding/cooking, true 3D, speech and new neural training are not implemented here. A's recurring/fair/global model-budget gate remains incomplete, along with extended supervisor/isolation/archival and long-horizon claims. Care still has recorded failures; do not reinterpret bounded survival as reliable husbandry.
