# F6 relationships durable slice

Implemented on October 22, 2026 as an additive overlay in
`underworld/relationship_store_f6.py`.

## Durable behavior

- `attach(source, destination)` copies an existing general-storage SQLite world
  to a new destination before adding `f6_meta`, `f6_relationships`, and
  `f6_operations`. The source is opened read-only and its bytes are checked
  before and after attach.
- Every ordered pair of native actor IDs receives an independent directional
  relationship state from `underworld.relationships_f6`.
- Updates accept only native-shaped `social_reports` and completed own native
  receipts for `give`, `offer_task`, and `respond_task`. The target's private
  state is never read or stored. Extra social-report fields, private target
  fields, unknown actors, and malformed ticks are rejected.
- Each operation has an idempotent operation ID, canonical command, before
  hash, after hash, bounded evidence, and a result. Retrying the same operation
  ID with the same command returns the durable result without applying it twice.
- `save` makes a no-overwrite SQLite backup, `resume` validates and replays the
  overlay, and `replay` verifies the complete F6 journal in a fresh process.
- `choose_helper` filters to currently visible actor candidates, uses only the
  observer's directional estimate, returns `None` for an empty visible set, and
  explicitly leaves native action validation authoritative.

## Verification scope

The additive unit/integration study covers directional histories, reverse-edge
isolation, negative-to-positive trust repair, strict input rejection, source
immutability, idempotent retry, save/resume, replay, fresh-process backup, and
matched helper ranking. This slice does **not** claim the full prospective
five-seed F6 gate.
