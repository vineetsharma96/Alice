> Review update, 23 October 2026: this document retains the original bounded
> implementation result. See [F12 code review](F12_CODE_REVIEW.md) for corrected
> action attribution, retained worlds, current verification and missing gates.
> Full F12 is not established; the F9 handshake is guided feedback.

# F12 connected-world survival check

`scripts/f12_survival_check.py` runs a bounded native survival check with the
copy-only F6, F7 and F12 overlays attached. F12 contains F8 regulation, F9
communication, F10 social emotion and F11 identity/value state. The native
stabilization controller remains the only action executor.

The runner creates one source world and two matched branches:

1. **Integrated branch:** F6 relationship store → F7 understanding store →
   F12 integration store → native stabilization.
2. **Control branch:** native-only copy → native stabilization.

Both branches use the same `config/living-world.toml`, seed, population and
finite material budget. The runner compares native state hashes, records actual
terminal stabilization receipts into the sidecars, performs a bounded F9
send/receive/public-feedback handshake, records public F6/F7 observations,
derives F10 pride prerequisites from completed native actions plus a seeded
standard, and records F11 native outcome/value evidence and summaries.

No sidecar proposal is executed as a native action. Therefore matching native
hashes are an isolation result, not evidence that F8-F11 improved survival.

## Command

```text
python scripts/f12_survival_check.py --seconds 90 --segment-seconds 30 --output artifacts/f12_survival_90s.json
```

## Observed result on October 23, 2026

- Simulated duration: 90 seconds.
- Population: 4.
- Integrated branch alive: 4/4.
- Control branch alive: 4/4.
- Minimum health: 1.0.
- Integrated mean hunger: 0.44.
- Integrated mean thirst: 0.0263.
- Integrated mean fatigue: 0.2736.
- Stabilization goals completed: 4; blocked: 0.
- Integrated/control native state hashes: equal.
- Source world bytes: unchanged.
- F6 replay: matched, 2 operations.
- F7 replay: matched, 7 operations.
- F12 replay: matched, 71 operations.
- F9 public-feedback handshake: changed receiver association successfully.
- F10 gated state: pride became available from recorded achievement/standard
  evidence.
- F11 acquired survival preference and summary revisions were retained.

This is one bounded seed and one finite 90-second run. It does not establish
indefinite survival, scheduler use of F8-F11 proposals, humanlike emotion or
communication, or a multi-seed scientific gate.
