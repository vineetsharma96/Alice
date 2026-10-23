# Review of the other agent's foundation changes — 23 October 2026

Reviewed the six new G01/G47, L02/L59 and M03/M48 modules, their tests, ordered
smokes, supplied specification scope and current handoff. These are isolated
JSON research models. Their presence does not implement the requested systems
inside the native inhabitants, world scheduler or viewer. No later stages were
started during this review. Unrelated package/OpenCode changes were preserved.

## Reproduced and corrected

The original focused suite passed 47 tests. New regressions nevertheless
reproduced ten distinct failures before their fixes:

1. Soil/excavation density in kg/m³ was divided by 1,000, yielding tonnes in
   fields labeled kg. Corrected both geology and underground mass calculations,
   including the inverse backfill-volume calculation.
2. The minimum supported 0.5 m soil profile could exceed its configured depth
   because of a forced minimum bedrock thickness. Remaining depth is now used.
3. L59 accepted caller-edited negative care amounts, permitting reverse transfers.
   Receipt fields are revalidated against the care-proposal contract.
4. L59 silently accepted conflicting retries of a care receipt. Reused identities
   now require matching participants, amount, resource, step and decision.
5. An adult's initial function scale came from the first, dependent life stage.
   It now comes from the actual current age stage.
6. A failed lifecycle transition could leave a partially modified invalid state.
   Both lifecycle modules roll back failed mutating operations, including nested
   operations and late validation/quota failures. This is in-memory rollback,
   not a claim of a native database transaction or thread-safe access.
7. G01/G47 checkpoint saving unconditionally replaced existing files. All four
   JSON sidecar save functions now create destinations exclusively, also closing
   the M03/M48 check-then-write overwrite race.
8. Plants logged nutrient uptake but never deducted it, allowing growth from an
   exhausted pool. Growth is now limited by available N/P/K and debits persistent
   copied soil pools. Re-supplying the initial source cannot refill spent pools.
   Zero-duration plant steps cannot alter physical plants, seeds or nutrients.
9. Retrying L02 care acceptance reset already applied transfers. Matching retries
   now preserve the existing commitment; conflicting retries fail.
10. The generation-order check merely repeated default generation and ignored
    supplied orders. It now generates through each actual coordinate order,
    requires a complete permutation and compares canonical results.

Evidence before correction is retained in
`artifacts/foundations_review_reproductions.log`,
`foundations_review_nutrient_reproduction.log` and
`foundations_review_additional_reproductions.log`. The original source/test
snapshot and SHA256 manifest are in `artifacts/foundations_review_original.zip`.

## Compatibility and remaining limits

The corrected numeric mechanisms use generator `g01.2` and plant model `g47.2`.
These are internal data identifiers, not a product release or Git tag. Older
sidecar JSON is not silently rescaled: mismatched versions fail validation. Keep
old checkpoints with the original sources in the review archive. No SQLite
world, native kernel, historical source registration or integrated-life
production source was changed by these corrections.

Plant growth still uses authored environmental/biomass abstractions. This fix
establishes finite sidecar nutrients, not native carbon/water conservation or
autonomous cultivation. Lifecycle proposals and care receipts remain external
inputs; schema validation does not authenticate actual inhabitants' intentions,
observations, transfers or births. L59 `replay` checks a journal hash chain and
current state; it does not reconstruct every transition from sufficient original
inputs. The microbial/plant/lifecycle ordered smoke links copied data and does
not prove live coupling or scientific acceptance gates. Disease remains disabled.

Numerical validation helpers recur across distinct schemas. They were retained
where contracts differ; shared rollback behavior was factored into one small
helper rather than duplicating exception-recovery logic across lifecycle APIs.

## Verification

Final checks passed **76 tests and three subtests in 25.36 seconds**, recorded in
`artifacts/foundations_review_verified_checks.log`, covering all six foundation
modules, both ordered smokes, the new regressions, existing integrated-life
checks and code audit. The full slow repository suite was not rerun for this
review; the other agent's reported 512-test result is historical evidence, not
this review's verification.

`artifacts/foundations_review_integrity.json` verifies all 11 historical source
registrations. Prior integrated production hashes were also compared with
`artifacts/life_source_manifest.json` and remain unchanged. No study was repinned
or failed result rewritten.
