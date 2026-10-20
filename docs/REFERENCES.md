# References checked for Phase 0

Current implementation updates appear in the phase-specific sections below; earlier candidate-only descriptions are preserved as history.

Accessed 2026-10-19 via TinyFish search/fetch. Read relevant abstract/README/documentation sections only. Sources inform proposed designs; they are not evidence of implemented capabilities. No external code copied.

| Ref | Official source | Use and limits |
| --- | --- | --- |
| R1 | [Generative Agents, arXiv 2304.03442](https://arxiv.org/abs/2304.03442) | Abstract describes memory, reflection and planning built around an LLM. Supports a conceptual cognition route, not consciousness or evolution from first principles. |
| R2 | [ALIEN repository](https://github.com/chrxh/alien) | README describes GPU particle-based organisms, genomes and neural controllers, supported GPU requirements and BSD-3-Clause license. Separate artificial-life baseline; not our engine dependency. |
| R3 | [pybind11 repository](https://github.com/pybind/pybind11) | Header-only C++/Python interoperability and BSD-style license. Binding postponed until Phase 1; exact release not selected. |
| R4 | [llama.cpp repository](https://github.com/ggml-org/llama.cpp) | CPU inference, quantization, server and backend options; MIT license. Candidate only, with separate model-license verification later. No remembered API version is hardcoded. |
| R5a | [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) | Rollback-journal atomic transaction design and storage assumptions. Our transaction proposal needs crash tests before claims. |
| R5b | [SQLite online backup](https://www.sqlite.org/backup.html) | Snapshot backup API rather than raw copying a live database. No backup/recovery implementation in Phase 0. |
| T1 | [CMake CXX_STANDARD](https://cmake.org/cmake/help/latest/prop_tgt/CXX_STANDARD.html) | C++20 target setting; require standard to prevent silent fallback. Latest online documentation is not the installed version pin. |
| T2 | [CMake overview](https://cmake.org/about/) and [maintainer PyPI distribution](https://pypi.org/project/cmake/) | Native cross-platform build design and CMake BSD-3-Clause license. Existing 4.1.2 reused; fetched current PyPI release not installed. |
| T3 | [Python venv](https://docs.python.org/3/library/venv.html) | Isolated project environment using the installed interpreter; no global package install. |
| T4 | [libstdc++ license and runtime exception](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html) | Runtime exception scope; do not conflate compiler license with required project license. |

Python/SQLite license labels in the manifest identify the existing distributions; check bundled notices before redistribution. R6-R11 in the preserved source brief remain future-phase references and have not been used to claim mechanics, thermodynamics, 3D or learning results. No scientific thermodynamic equations have been selected in Phase 0.

## Phase 1 references checked 2026-10-19

- [pybind11 CMake/build systems](https://pybind11.readthedocs.io/en/stable/compiling.html) and [official PyPI release](https://pypi.org/project/pybind11/): selected/pinned 3.0.4 (BSD-3-Clause); `find_package(Python ... Development.Module)`, `PYBIND11_FINDPYTHON` and `pybind11_add_module`. Actual import test is the evidence for this host's compiler/interpreter combination; MinGW LTO is explicitly disabled by the dependency's CMake helpers.
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html), [locking and hot journals](https://www.sqlite.org/lockingv3.html), [synchronous PRAGMA](https://www.sqlite.org/pragma.html#pragma_synchronous) and [online backup](https://www.sqlite.org/backup.html): rollback/FULL transaction design, recovery and live backups. Process-exit tests do not prove hardware/power-loss behavior.
- R6: [Box2D simulation documentation](https://box2d.org/documentation/md_simulation.html): fixed-step mechanics reference only. We implemented a smaller explicit swept-circle model, not Box2D and not its recommended solver timestep/impulse mechanics. No Box2D dependency or chemistry claim.
- [Microsoft GetProcessMemoryInfo](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getprocessmemoryinfo) and [PROCESS_MEMORY_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters): `PeakWorkingSetSize` measured in bytes for each benchmark worker process. Includes interpreter, extension and worker activity; it is not total machine RAM or model VRAM.

## Phase 2 reference check, 2026-10-19

- [Generative Agents abstract](https://arxiv.org/abs/2304.03442) revisited for the perception/agent architecture context. Current utility policy is our authored baseline; no paper-level model/memory behavior is claimed.
- [Python 3.12 http.server documentation](https://docs.python.org/3.12/library/http.server.html): stdlib HTTPServer/ThreadingHTTPServer/BaseHTTPRequestHandler for the loopback observer. It is a local inspection tool, not a production internet service.
- [SQLite JSON functions](https://www.sqlite.org/json1.html): selected-agent history annotations use `json_extract` on validated decision JSON, tested with installed SQLite 3.49.1. Persistence continues using the atomic-commit/backup sources already checked for Phase 1.
- Body/need rates, resource recovery and the utility policy are explicitly authored assumptions, not medical/biochemical estimates drawn from a source. No real-human survival claim is made.

## Phase 3 sources checked 2026-10-19

- R4: [pinned llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/b11721/tools/server/README.md), [b11721 release](https://github.com/ggml-org/llama.cpp/releases/tag/b11721) and [official release metadata](https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11721). Verified CPU Windows archive/version, loopback/thread/context/parallel options, `/props`, `/tokenize` and `/completion` with `json_schema`, `n_predict` and seed/temperature. Actual binary import/server requests and SHA-256 pins provide host-specific evidence.
- [Official SmolLM2 360M Instruct model card](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct), [publisher GGUF](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF) and [publisher API metadata](https://huggingface.co/api/models/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF). Checked Apache-2.0 metadata, publisher revision/file and small-model selection for the measured 4 GiB host. ChatML/native completion behavior was tested against this actual Q8 model; no Transformers install was needed.
- R1 remains conceptual context for private episodes, reflection and planning, not a claim to reproduce that paper's capabilities. R5's already-checked atomic commit, backup and SQLite query contracts remain the storage basis. Lexical matching over a bounded parameterized own-agent query is our explicit small retrieval implementation, not an embedding result.
- Microsoft PSAPI references from Phase 1 remain the basis for server/worker/parent working-set measurements; dedicated GPU inference is disabled. Measurements are not total system peak RAM.

## Phase 4 reference scope

R1 (Generative Agents) remains conceptual context for memory and communication, as already reviewed in earlier phases. Operator books, access gates, explicit source ledgers, provenance records, conditional branches and the randomized mapping experiment here are our proposed extension, not a replication or capability claim from that paper. Existing SQLite transaction/backup and pinned llama.cpp references remain applicable. No new external code or scientific physical equations were imported; thermodynamics is deferred to Phase 5.

## Phase 5 equations verified before implementation, 2026-10-19

- OpenStax, *University Physics Volume 2*, [1.4 Heat Transfer, Specific Heat, and Calorimetry](https://openstax.org/books/university-physics-volume-2/pages/1-4-heat-transfer-specific-heat-and-calorimetry): Q=mcΔT; Table 1.3 ice 2090, liquid water 4186, steam at constant pressure 2020 J/kg/K. These are approximate constant capacities, not a closed-gas internal-energy law.
- Same publisher textbook, [1.5 Phase Changes](https://openstax.org/books/university-physics-volume-2/pages/1-5-phase-changes): Q=mL, phase plateaus; Table 1.4 water melting 0°C, boiling 100°C at 1 atm, fusion 334 kJ/kg and vaporization 2256 kJ/kg. The engine uses the table's 334 kJ/kg fusion value (some surrounding worked text uses 333).
- Same publisher textbook, [1.6 Mechanisms of Heat Transfer](https://openstax.org/books/university-physics-volume-2/pages/1-6-mechanisms-of-heat-transfer): conduction rate kA/d times temperature difference, Stefan–Boltzmann net radiation and σ=5.67e-8 W/m²/K⁴. Effective conductances, emissivity, areas and environment temperature are our authored apparatus parameters.

These primary educational pages were searched and fetched before the thermal implementation. They justify the selected equations and water approximations; they do not validate our artificial reaction or the full apparatus. Inert/species capacities, artificial X + 2 oxidizer -> 3 P mass reaction, chemical energy, pilot rate, outlet rule and thermostat are explicitly authored. R6 remains a mechanics reference only: our C++ thermal solver is separate from collision handling. No third-party thermodynamics code was copied and no new dependency was installed. See `PHASE5_THERMAL.md` for the enthalpy-like proxy, pressure/PV exclusions, integration bound and measured-evidence contracts.

## Phase 6 research context checked 2026-10-19

- R7: Wang et al., [Enhanced POET: Open-ended Reinforcement Learning through Unbounded Invention of Learning Challenges and their Solutions](https://proceedings.mlr.press/v119/wang20l.html), ICML 2020, PMLR 119:9940–9951. Checked the original abstract for challenge generation, transfer between challenges and limitations. Our four-temperature/four-dial task and capped practice counter do not implement POET, reinforcement learning or an unbounded curriculum.
- R8: Sakana AI, [Automating the Search for Artificial Life with Foundation Models](https://sakana.ai/asal/), 2024-12-24. Checked the author's description of supervised-target, open-endedness and illumination searches. Our supplied apparatus, finite enumeration and two-inhabitant transfer experiment do not implement ASAL, vision-language search or artificial-life emergence.
- R1 remains the previously checked conceptual context for episodes and source-bounded communication. Existing SQLite durability/backup references and Phase 5 OpenStax equations remain applicable. Social protocols, procedure syntax, work validation, practice efficiency, motives and controls are our authored engineering choices. No new external code, model, neural-weight update or dependency was introduced.


## Phase 7 implementation references checked 2026-10-19

- Microsoft [Implementing an AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer), [CreateAppContainerProfile](https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-createappcontainerprofile) and [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute): current-user profiles, zero capabilities, restricted startup and inherited-handle allowlist. Actual token queries and WSAEACCES probes provide host evidence; no network exemption is configured.
- SQLite [max_page_count](https://www.sqlite.org/pragma.html#pragma_max_page_count), plus R5 atomic commit/backup references above: finite page quota, rollback after FULL, transactional backup and crash-recovery boundaries. Process-termination tests do not claim power-loss guarantees.
- R4 pinned llama.cpp/SmolLM2 adapter and prior Windows PSAPI profiling references remain applicable. This phase adds no external inference service or downloaded dependency. Benchmark settings, admission policy, finite retention and short horizons are authored engineering choices.


## Phase 8 references checked 2026-10-19; handoff 2026-10-20

- R9: Epic [Programming with C++](https://dev.epicgames.com/documentation/en-us/unreal-engine/programming-with-cplusplus-in-unreal-engine) and [hardware/software specifications](https://dev.epicgames.com/documentation/en-us/unreal-engine/hardware-and-software-specifications-for-unreal-engine). The recommended 32 GB RAM / 8 GB graphics RAM informed choosing a lighter renderer for this 4 GiB Intel HD 520 host. Unreal was not installed or benchmarked.
- Three.js official [WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html), [OrbitControls](https://threejs.org/docs/pages/OrbitControls.html), [pinned r180 source](https://github.com/mrdoob/three.js/tree/r180) and [MIT license](https://github.com/mrdoob/three.js/blob/r180/LICENSE). Browser modules are locally vendored with original/distributed checksums and the license; OrbitControls has only its module import redirected locally. No latest-version or WebGL1 compatibility claim is made.
- Existing R5 SQLite transaction/backup references support the single-transaction read feed and unchanged durable authority. Prior Windows PSAPI references support process measurements; venv-launcher samples are explicitly distinguished from actual Python-worker memory. The authored protocol, glyph heights, scene palette, camera behavior and projection are engineering choices, not physical laws from these sources.

## Phase 9 research context checked 2026-10-20

- R7: [Enhanced POET](https://proceedings.mlr.press/v119/wang20l.html), Wang et al., ICML 2020, PMLR 119:9940-9951. Challenge generation and transfer motivate a distinct open-ended research direction; the fixed curriculum here is not POET.
- R8: Sakana AI [Automating the Search for Artificial Life with Foundation Models](https://sakana.ai/asal/). Foundation-model search over artificial-life systems is separate from our own-inventory linear-policy experiment. No ASAL replication or emergence evidence is claimed.
- R10: [PyTorch documentation](https://docs.pytorch.org/). Neural tooling was considered unnecessary for three non-neural weights; PyTorch was not installed and no neural-model improvement is claimed.
- R11: Google DeepMind [Flow-Lenia: Emergent evolutionary dynamics in mass conservative continuous cellular automata](https://deepmind.google/research/publications/106327/), published 2025-04-28. Its mass-conservative cellular-automata track remains separate from humanlike/pretrained-agent research and was not implemented here.

These primary sources were searched and fetched before the study. The normalized perceptron, receipt journal, fixed grids, controls, budgets and advancement thresholds are explicitly authored engineering choices, not results imported from those papers. No external implementation or new dependency was copied into the experiment.
