# F7 understanding slice — 22 October 2026

F7 starts with an additive, bounded estimator for what one inhabitant might
need, be trying to do, or be experiencing from another inhabitant's permitted
public observations.  It is directional: `agent-1`'s estimate of `agent-2`
does not change `agent-2`'s estimate of `agent-1`.

## Contract

`underworld/others_f7.py` accepts one strict observation envelope:

- `observer` and `target` identity;
- visible cue records with `source_event_id`, an authored public cue name, and
  bounded strength;
- witnessed social reports with `source_event_id`, an authored report kind, and
  bounded strength.

The estimator rejects extra fields.  Target private mood, goals, memories,
lexicon, inventory, and operator labels are not observation inputs.  The
optional `operator_label` argument is explicitly ignored transport metadata;
changing it cannot alter the result.

Each output hypothesis contains a signed bounded `belief`, explicit
`confidence` and `uncertainty`, a status (`possible` or `less_likely`), and the
source event IDs that contributed to it.  Ambiguous cues are represented by
multiple low-confidence alternatives and retained ambiguity IDs rather than a
single fabricated label.  Evidence is deterministic, source-ID ordered,
idempotence is guarded by duplicate-ID rejection, and the retained evidence
bound is 32 events.

New public evidence recomputes the directional estimate from retained evidence.
This allows a later observation such as `drinking_observed` to reduce or
reverse an earlier water-need belief while preserving provenance and reporting a
correction update.

## Scope and non-claims

This is the first F7 implementation slice, not the completed F7 gate. The pure
Python estimator now has a copy-only durable overlay in
`underworld/others_store_f7.py`, including strict current-native observation
checks and fresh-process replay. It is not registered in historical registries,
does not modify `storage.py`, F5, or F6 files, and is not wired into native
behavior, scheduler decisions, or the viewer. No general understanding claim
is made.

## Checks

The focused checks are:

```text
python -m unittest tests.test_others_f7
python -m py_compile underworld/others_f7.py tests/test_others_f7.py
```
