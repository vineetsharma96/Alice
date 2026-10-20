# Phase 0 report

Date: 2026-10-19 (Asia/Calcutta). **Phase 0 complete on the available native Windows host.** No later phase has been implemented. Branch: `codex/phase-0`; source changes are uncommitted for review.

## Completed scope

Read the supplied phased brief and preserved it byte-for-byte as `docs/PROJECT_SPEC.md` (SHA256 `306e5eafba0f7c53b49002ec8fcd276dc736efb791ede1991f64e685773e84d6`). The repository initially contained only `.git`, with no code or applicable AGENTS.md found. Selected a C++20 authoritative simulation / Python cognition architecture, evaluated ALIEN as a separate reference, documented persistence/scheduling boundaries and proposed seven versioned contracts with units, IDs, privacy rules and errors.

Created a runnable CMake executable, local Python venv, strict TOML configuration, Windows bootstrap, documented Linux/MSVC paths, smoke tests, architecture diagram, dependency/license manifest, approximation register and end-to-end milestone checklist. Baseline initializes 8 inert inhabitant records plus food/water/inert-material resources in a 64 x 64 metre region. Seed `20261019`; proposed fixed step 0.1 s; current tick 0. Cognition disabled, no model/provider/API key needed. Inspect is initialization-only and does not run a simulation.

## Actual host and dependencies

Observed execution host only; eventual deployment hardware has not been established. Windows 10 Pro 10.0.19045 x64; i3-6006U, 2 cores/4 threads; 4,082,600 KiB visible RAM (3.89 GiB), 1,219,984 KiB free at saved inspection; Intel HD 520 (driver-reported adapter memory 1 GiB, not measured usable inference VRAM). Saved free C: disk 10,346,659,840 bytes (9.64 GiB). Free memory/disk fluctuate.

Reused `C:\mingw64\bin`: GCC 15.2.0, CMake 4.1.2, GNU Make 4.4.1. Python 3.12.10 x64, stdlib SQLite 3.49.1 available. Created `.venv` without installing third-party Python packages. No model weights, GPU runtime, paid service, distributed database or system-wide dependency installation.

## Commands and observed results

Run from the repository root in PowerShell:

```powershell
python -m venv .venv
$env:PATH = "C:\mingw64\bin;$env:PATH"
cmake -S . -B build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe --ctest 'C:\mingw64\bin\ctest.exe'
.\scripts\bootstrap.ps1
```

All exited 0. Initial configure identified GNU 15.2.0 and took 2.7 s as reported by CMake; Release executable compiled/linked successfully, with no compiler warnings observed. Final bootstrap reconfigured/reused the build and reran all checks successfully. CTest: **2/2 passed**, 0.05 s reported test time. Python unittest: **4/4 passed**, 0.212 s reported test time, including multiple negative-input subcases. Python-to-C++ inspection returned valid initial-scene JSON at tick 0.

Tests cover same-seed repeatability, changed-seed positions, stable unique IDs, bounded coordinates, baseline population/resource count, malformed native arguments, invalid/unknown config and rejection of unimplemented cognition providers. These are scaffold checks, not tests of survival, conservation, perception privacy or crash recovery.

`artifacts/phase0_checks.json` retains commands, exit codes, stdout/stderr, environment versions, measured wall times and hashes. `artifacts/initial_scene.json` is the observed scene, **not a checkpoint**. Its canonical JSON SHA256 is `9e2c08a72fc7af8f99c9ba09ecf0f7a52181d7514c1759307d98274760332868`; baseline TOML SHA256 `1e0d005e27a03d6707a1bafe0cfe00012c5c2e3dcce57bac4516e199a91a0255`. `artifacts/host.json` contains saved hardware/toolchain evidence. No secrets are required or recorded.

## Performance and unresolved limits

CTest, unittest and inspection wall times (including process startup) are measured in the JSON evidence. They are initialization/check costs, not simulation throughput. Simulated time is exactly 0 s. No 10,000-tick benchmark, simulation acceleration, per-process peak RAM, local inference latency, VRAM budget or population scaling was measured; those claims would be premature. No local model feasibility conclusion follows from this smoke pass.

Native Windows/MinGW is the only tested build/runtime. Linux and MSVC are explicitly untested. Later pybind11 integration must verify compatibility between the MinGW toolchain and MSVC-built CPython; subprocess interoperability does not prove extension compatibility. Runtime DLL availability currently relies on the existing MinGW bin directory on PATH. Binary packaging/licenses require review before distribution. No blockers remain for Phase 0.

Snapshots, observations, actions, memories, material laws and interventions are proposed contracts. Bodies, movement, actual fixed-step time, persistence/replay, conservation, model cognition, observer UI, network-enforced closed mode and chemistry remain unimplemented. Config budgets are validated declarations, not enforced runtime scheduling. Future contracts need executable fixtures and integration tests as they are implemented.

## Next phase

Phase 1 only when requested: implement authoritative fixed-step mechanics, bounds/collisions/resources/inventory, batched binding, transactional checkpoint/replay and CLI time advancement; prove save/resume equivalence and measure the configurable 10,000-tick benchmark. Keep the model-off baseline. See `docs/MILESTONES.md` for the later food-to-memory/restart milestone and `docs/MODEL_LIMITS.md` for approximations. Do not advance automatically to model cognition or a decorative viewer.
