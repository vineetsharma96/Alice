# Alice specifications 01–03: ordered foundation report

Implemented the first bounded slices from the three supplied specifications in
order, while preserving native authority, existing SQLite worlds and the
current F8–F12/life work.

## Stage 1 — Alice 01, G0–G3

`underworld/world_generation_g01.py` provides a versioned, deterministic,
bounded JSON world manifest with three climate presets, layered substrate/soil,
finite material/deposit stocks, coordinate-stable generation, extraction and
excavation accounting, and soil-water ledgers. It is an additive sidecar; it
does not replace the native world or weather scheduler. G4+ plant life cycles,
native viewer integration and deep underground mechanics remain deferred.

## Stage 2 — Alice 02, L0–L4

`underworld/lifecycle_l02.py` provides versioned lifecycle/reproductive
contracts, separate reproductive biology and gender identity, directional
relationship evidence, two-party partnerships, guarded conception,
resource-costed gestation, exactly-once births, bounded inheritance and care
commitments. Actions are proposals or explicit copied-state applications; no
native action is executed. Mortality, animal/plant-specific runtime,
multi-generation population studies and native integration remain deferred.

## Stage 3 — Alice 03, M0–M3

`underworld/micro_ecology_m03.py` provides a CPU-first aggregate microbial
sidecar with finite habitats/substrates, four functional guilds, inoculum
tracking, substrate-limited growth/maintenance/mortality/division,
decomposition, nutrient return, transfer, positivity and tracked-mass
validation. No ALIEN source code is copied. M4+ dispersal adaptation, M5
fermentation, M6 detailed microcosm, M7 disease and M8 native integration are
deferred.

## Ordered cross-stage smoke

`tests/test_alice_foundations_integration.py` generates a G01 world, uses its
soil/plant-litter data to initialize M03, advances the microbial ecology, then
registers a lifecycle species and two mature individuals under L02. This proves
the three foundational contracts can be exercised in order without changing an
existing native save. It is not whole-world runtime integration.

## Verification

Focused ordered checks:

```text
python -m pytest -q tests/test_world_generation_g01.py tests/test_lifecycle_l02.py tests/test_micro_ecology_m03.py tests/test_alice_foundations_integration.py
```

Result: 26 passed for the three initial groups, plus the ordered cross-stage
smoke.

The extended continuation slices are also covered by focused tests: G4–G7 has
14 pytest cases, L5–L9 has 7 pytest cases, and M4–M8 has 8 pytest cases. The
full ordered cross-stage smoke in `tests/test_alice_full_ordered_foundations.py`
passes through G01 → G47 → M03 → M48 → L02 → L59, with disease explicitly
disabled.

The corresponding unittest modules pass 26 tests. The three implementation and
test groups compile with `python -m py_compile`. `npm run lint` remains the
repository JavaScript syntax check. `git diff --check` still reports one
pre-existing trailing-whitespace line in `tests/test_code_audit.py`, unrelated
to these new stages; it was not changed.

The repository-wide verification was then run with the existing native core
environment:

```text
UNDERWORLD_CORE="C:/Users/abc/Documents/ChatGPT/UnderWorld/build/underworld_core.exe" python -m pytest -q
```

Final result after the G4–G7, L5–L9 and M4–M8 continuation slices:
`512 passed, 352 subtests passed in 728.39s`.

An earlier full run showed two transient Windows isolation failures in unrelated
Phase 7 supervision tests. The affected tests passed on individual reruns (the
parallel case required one retry); the final full run passed.
