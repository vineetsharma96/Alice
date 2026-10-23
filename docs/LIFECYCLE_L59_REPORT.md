# ALICE 02 L5-L9 lifecycle slice

## Scope

`underworld/lifecycle_l59.py` is a pure, additive JSON sidecar that follows the
L0-L4 lifecycle foundation. It does not import the native engine,
`underworld/storage.py`, existing worlds, or the F8-F12 modules. It has no
action authority: proposals are returned as `execution: "external"` and
`proposal_only: true`; state changes require an explicit receipt or caller
choice.

## Implemented contracts

- **Bounded inheritance variation:** `InheritanceControls` caps mutation and
  per-trait variation, with deterministic seeded recombination. `InheritanceResult`
  records parent IDs, controls, and explicit provenance. Birth lineages state that
  knowledge, lexicon, and relationships come only from developmental experience;
  those fields are always empty on a newborn.
- **Development and care:** `L59LifeStage` declares age ranges, function scale,
  resource needs, deprivation tolerance, and a bounded mortality hazard. Care
  proposals and receipts debit a caregiver's resource ledger, credit a dependent,
  and are idempotent. Missing care increases deprivation steps/score and reduces
  current function rather than being silently repaired.
- **Aging and death:** `advance_time` advances each living individual, computes a
  deterministic hazard, accepts optional explicit rolls for replay/tests, and
  retains death records. Deaths keep reason, hazard, roll, and all positive
  materials in a material ledger; individuals are marked dead rather than removed.
- **Grief evidence:** grief requires an attachment record and a separately
  perceived loss record for the same observer/target. A death by itself does not
  trigger grief, and non-perceived or private/operator/model fields are rejected.
- **Demographics and capacity:** birth, death, lineage, and culling counters are
  explicit. Carrying-capacity reports show live occupancy and overflow while
  retaining every registered individual; no hidden culling occurs.
- **Durability:** canonical JSON dumps/loads, copy restart, and a hash-chained
  replay journal provide save/resume and replay receipts.

## Validation

`tests/test_lifecycle_l59.py` covers inheritance controls, absence of parental
knowledge/lexicon/relationship copying, care/deprivation, deterministic age
hazard, accounted death materials, evidence-gated grief, demographic totals,
capacity overflow, proposal-only actions, privacy rejection, JSON restart, and
replay.

## Explicit limits

This is a bounded sidecar, not a native scheduler, a subjective-consciousness
claim, a population controller, or an external-action executor. Carrying
capacity is reported, not enforced by hidden population deletion. Mortality is a
declared hazard over the sidecar's biological clock; native authority remains
outside this module.
