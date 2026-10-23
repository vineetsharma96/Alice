# F9 emotional communication slice

F9 adds `underworld/communication_f9.py`, a pure bounded learner for discrete
emotional signals. Each agent starts with an empty private production and
comprehension map. Tokens are arbitrary channel identifiers; their meanings are
not shared or preloaded. Associations are learned per speaker/partner only
from explicitly tagged public feedback.

`emit` and `receive` return delivery proposals and interpretations. They do not
execute native speech or actions. Repeated feedback can improve a receiver's
token-to-meaning confidence; shuffled tokens and unfamiliar partners remain
uncertain. Evidence, partner maps and duplicate ledgers are bounded, JSON
copyable, idempotent and reject private, operator, model and foreign fields.

The slice is not a claim of humanlike language, grammar, spontaneous intention,
or a passed multi-seed communication gate. Native delivery, cost, timing and
action authority remain external.
