# Manual integrated-world session

The running session is `data/manual-control/world.sqlite`, copied from the
integrated development world without modifying its source. It starts paused
at tick 360 / 90 simulated seconds. Open http://127.0.0.1:8782/.

- **Step 1 tick** advances one physical tick, updating cognition normally.
- **One inhabitant turn** lets the next scheduled person complete a policy turn.
- **Run / Resume** continues all inhabitants without an overall tick/time horizon.
- **Pause** stops selecting new work; an in-progress transaction finishes first.

Native resources, validation and storage/journal quotas remain active. This is
not infinite storage, automatic replenishment or a passed lifelong research gate.
Pause the session before closing the UI if it should stop advancing.

Restart from the repository with:

```powershell
.venv/Scripts/python.exe -m underworld.life_control --db data/manual-control/world.sqlite --port 8782
```

Restarting resumes the exact save and initially pauses it. No second writer may
own the same world. Stop the server with Ctrl+C in its terminal; it waits for
the active transaction before releasing the writer lease.

The new launcher composes the existing integrated writer and viewer; historical
registered sources are unchanged. Its regression checks paused startup, a single
tick, resume/pause, invalid commands and exact replay. One test passed in 2.18s.
Live HTTP checks confirmed the control page, paused state, no overall tick cap,
and rejection of a tokenless write (403). No experiment world was run unattended.
