# Confirmation compute allocation, before held-out runs

Development shows that 300 four-person simulated seconds cost roughly 200 wall
seconds on this host. Keep the declared physical/source/retention gates intact.

Run both declared seeds (2521/2549), with matched unassigned and assigned arms,
through checkpoints at 60 and300 simulated seconds. Allow240 wall seconds per
segment. Then attempt to extend the existing2521 assigned world to900 simulated
seconds with one additional240-wall-second budget. Other900-second cohort
targets are deferred for compute cost, not labelled as achieved or failed.
Report the actual reached duration and each world separately.

Also run an independent four-person120-second in-flight save/restart check
across a100-second archive boundary. Compare native, cognitive, identity and
controller tables exactly. SQLite backup files may have different page layouts;
their file SHA and derived archive-chain hashes are verified individually, not
required to be byte-identical across two different files. Compare logical epoch
and scheduler state while excluding those derived file-hash fields only.

The planned900-second extension is not an equal-horizon comparison against the
300-second baseline. It supplies continuity and scarcity evidence only. Primary
confirmation completes before regression/package work so timing is not blended
with those tests. Models remain off; no threshold is relaxed based on results.
