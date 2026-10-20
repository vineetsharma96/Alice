# Code connections, duplication and executable audit

20 October 2026. Application 0.11.1; native authority remains Milestone D's UW9 build `832c4a705a7ceecd85d8befb3d84f4dff0d4730f024c395eba12985f0d8bd896`, DB10/checkpoint 9. This is maintenance/packaging, not Milestone E or a new scientific learning claim. Phase 9's failed gate and sealed files remain unchanged.

## Concrete fixes

| Finding | Consequence | Fix and evidence |
|---|---|---|
| Cognition-enabled advance validated an external action iterable before reusing it | A generator could be exhausted and its valid requests never execute | Materialize once before validation/dispatch. Regression uses a generator and verifies actual native gathering, carried mass and replay; inference itself is mocked |
| 2D observer opened separate reads for world, perception, memory and history | An external writer could advance between them, presenting mixed ticks | Both UIs use the same validated SQLite read transaction through viewer.packet/snapshot_projection; selected tick and snapshot stay consistent |
| Viewer/state repeated snapshot enrichment, receipt annotations and journal validation | Implementations could drift; 2D/3D history shapes differ | Shared snapshot projection, culture recall projection and event-chain validator. Preserve 2D history's branch/interventions envelope and 3D history list |
| 2D read-only controls remained clickable | UI offered operations its server correctly rejected | Disable pause/step/speed/interventions and display read-only status; packaged browser check covers both pages |
| Initialization created a native save before validating handoff options | Invalid call limits/body profiles left unintended files | Shared initialize validates options/config before creation; native initialization failure no longer publishes an empty file |
| CLI default config paths depended on working directory | A copied executable or source invocation outside the checkout could not initialize | Resolve bundled/source defaults relative to the package; tests run from an unrelated directory and packaged CLI initializes there |
| Windows bootstrap targeted historical build/ and invoked a verifier writing phase9_checks.json | Routine setup could overwrite historical binaries/evidence | Build only build/living-d; current verifier uses a new timestamp/UUID report, and legacy verify.py delegates to it |
| Checkpoint/package versions repeated across create/save/rotation/branch | Future version drift could create inconsistent checkpoints | One storage.CHECKPOINT_SCHEMA constant, one package __version__, and DB_VERSION for schema creation |
| C/D continuity drivers duplicated their entire control flow | Corrections required two edits | Shared scripts/living_continuity.py with explicit profile wrappers |
| Runner read its starting tick before acquiring the writer lease | Another writer could change the head before duration targeting | Read the initial head under the lease; add cooperative cancellation only between committed ticks |
| Frozen Python modules point at bytecode paths | Controller source checksum could differ between executable/source or separate unpack directories | Hash the bundled .py source explicitly; include exact source files in the package. Executable/source/executable save interoperability passes |
| Unused imports and an implicit loop-carried transaction hash | Noise obscured real connection issues; static checker could not establish initialization | Remove unused imports without changing assertions or scientific controls; initialize expected state hash from the validated head |

The implicit hash was normally assigned by the first committed loop iteration; it is not reported as a reproduced runtime crash. Small math helpers and independent research-control implementations are intentionally retained; scientific controls were not merged into live policies merely to reduce lines.

## Coverage and boundaries

The static inventory parses 76 Python files, records 219 local import edges, checks 14 native local-header edges and local JavaScript module assets. No unresolved relative modules/header/assets or repeated substantial whole production functions were found after refactoring. The whole-function scan excludes small helpers and does not establish an absence of every form of duplication. Pyflakes reports no findings across underworld/scripts/tests. JavaScript entry points pass Node syntax checks.

Manual review focused on native bindings/action dispatch, native delayed completion/invariants, persistence/leases/replay, scheduler ownership, CLI/config paths, viewer projections and packaging. Runtime regressions cover those connections. This is not an exhaustive proof of every branch, layout, platform or external service. Core physical laws were not changed; model inference, neural training, breeding, cooking, speech and true 3D were not added.

## Executable and launchers

`run.sh` provides one Bash entry point; `run.cmd` provides a Windows double-click/terminal entry point. They prefer the packaged executable and can fall back to the source environment. `UNDERWORLD_SOURCE=1` forces source execution. The Windows bootstrap installs only pinned source-build dependencies and selects the separate current build.

The unsigned Windows x64 executable is `dist/UnderworldLab.exe` (12578263 bytes; SHA-256 `29abd8e1553571f07116c0e9cdf8ba69b06db3f4cbfc9a50524cd809c183a0e2`), built using pinned PyInstaller tooling. It bundles Python/native runtime DLLs, source files required by provenance checksums, configurations and locally vendored viewer assets/license. It excludes user saves, environment files and downloaded models. Default application state is outside the executable/extraction directory in the user's local application-data folder.

Desktop execution starts one model-off bounded writer plus a read-only loopback viewer. Default duration is 30 simulated seconds with a 240-second wall budget. Existing compatible saves are validated/resumed, never attached/reset/refilled. Completion leaves an inspector; Ctrl+C stops the server and lets an active writer stop between committed ticks. The Phase 7 AppContainer entry point requires source Python and is explicitly unavailable through packaged --cli run.

Both Git Bash run.sh and Windows run.cmd were executed through actual initialization/advancement, not only syntax checked. The executable was launched with PATH limited to Windows System32 and an intentionally absent external toolchain directory. Executable -> source -> executable continuation reached ticks 2/4/6 on the same save. Packaged save/backup/replay and default-config CLI initialization from an unrelated working directory pass. This establishes independence from Python/compiler PATH on this host, not certification on another Windows installation.

## Preserved histories and compatibility

Before source edits, the previous project's Python/native sources, configs and exact native extension were copied to build/runtime-before-code-audit-20261020 with a SHA manifest. Its archived CLI successfully reads the original 120-second D database. Current source changes intentionally produce new orchestration/controller hashes. Old saves fail closed under mismatched source rather than being silently migrated. The README includes archive launch commands.

All prior D/C reports and native worlds are retained. Root historical binaries and the sealed Phase 9 study are not rewritten. The existing unrelated OpenCode/npm files remain untouched by this audit. New evidence uses code_audit_* filenames. The earlier D scores remain historical; maintenance checks do not turn a failed learning gate into a pass.

## Verification evidence

Final verification: **183 Python tests** (229.709 s inside unittest) and **four native checks** pass. Static checks are clean. The standalone executable reaches **120 continuous simulated seconds / 169.582 wall seconds**, completes four human drink goals through 15 native actions, retains all six bodies alive at health 1.0, and passes replay. Its complete native head equals the original final D 120-second head (`da68713042375015e7fc88ba50f863072b4da1416620232215b3ada187837c90`), demonstrating unchanged native behavior for this case. Separate reduced-PATH smoke checks prove executable/source/executable save continuation and packaged backup/replay. Both packaged UI pages pass read-only/asset/privacy checks with no JavaScript errors.


- artifacts/code_audit_regressions.json: full current Python/native regression output and protected Phase 9 source hashes.
- tests/test_code_audit.py: generator dispatch, transaction-consistent UI, invalid initialization, interruption, package-relative CLI configs, source launcher resume and checkpoint-schema integration.
- artifacts/code_audit_connections.json and code_audit_pyflakes_final.txt: static inventory and clean Python diagnostics.
- artifacts/code_audit_package.json: executable size, hash, native build and exact build command.
- artifacts/code_audit_package_smoke.json: reduced-PATH executable, source/executable resume, backup/replay and copied-context CLI initialization.
- artifacts/code_audit_packaged_viewer.json/png and -2d.png: actual packaged HTTP/assets, both UIs, disabled read-only controls, no JavaScript errors/private observation leakage.
- artifacts/code_audit_desktop_120.log: separate 120-second packaged-app run; simulated/wall duration and native replay are reported directly.
- artifacts/code_audit_phase9_audit.json: independent unchanged-study file/metric verification.

Current limitations remain: unsigned local build; no independent clean-machine or Linux/macOS/MSVC certification; incomplete A model budgeting/isolation; finite journal quotas; imperfect general navigation/care; deferred breeding/cooking and later research milestones. Changes are local and have not been pushed.
