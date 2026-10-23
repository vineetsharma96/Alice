# ALICE 02 L0-L4 lifecycle foundation

## Scope

`underworld/lifecycle_l02.py` is a pure, additive JSON-copyable sidecar. It does
not import the native engine, `underworld/storage.py`, existing world files, or
the frozen F8-F12 modules. Native execution remains external: relationship,
partnership, conception, care, and birth functions return proposals or apply
only explicit receipts/results to a caller-owned copied state.

## Contracts and invariants

The module versions these contracts at schema version 1:

- `SpeciesLifecycle` and `ReproductiveProfile` use one declared biological
  step scale per species and explicit age stages.
- `LifeStage` separates newborn/dependent stages from mature adults.
- `RelationshipEvidence` stores directional observer→target evidence, including
  affection, trust, attraction, attachment, reliability and invitation outcomes.
  A declined invitation creates a declined decision/evidence record; it does not
  create reciprocal affection or a partnership.
- `Lineage` records bounded parent IDs, inherited trait values and mutations. It
  explicitly records that knowledge, lexicon and relationships require
  developmental experience.
- `PregnancyOrIncubation` records elapsed biological time, per-step resource
  costs, conception identity and exactly-once birth application.
- `CareCommitment` records accepted caregiver decisions, per-step resource
  spending and idempotent applied steps.

Biological reproductive role/compatibility and gender identity are separate
fields. Conception requires mature living individuals, matching species,
compatible profiles, current intentions for both participants, proximity,
ready/available conditions, a bounded probability roll and one active pregnancy
per carrier/conception step. Gestation consumes the carrier's actual resource
ledger; insufficient resources fail the pregnancy explicitly. Birth IDs are
deterministic and retained in a birth-event ledger so retry/save/resume cannot
create a second child.

Inheritance is intentionally small: body-size potential, metabolic efficiency,
maturation tendency and sensory sensitivity are recombined with bounded
mutations. Newborn knowledge, lexicon and relationship IDs are empty.

## Tests and limitations

`tests/test_lifecycle_l02.py` covers invalid immature/incompatible pairs,
directional one-way affection, declined invitations, two-sided partnerships,
conception prerequisites, gestation cost, exactly-once birth, bounded trait
variation, no knowledge copying, care accounting and JSON copy/restart.

This is the first bounded L0-L4 foundation. It does not claim native scheduler
integration, species-specific animal/plant/microbial execution, mortality,
multi-generation population studies, subjective love, or autonomous action
authority. Those remain outside this additive slice.
