# Weather worlds: build, run, inspect and resume

Weather is an explicit opt-in native runtime. Keep the original `build/living-d`
and existing source checkout for UW9 G/H worlds and research evidence. Weather
requires a NEW world; there is no migration, automatic body reset or replenishment.
The initial implementation uses a 32 m region and the existing 2D physics, with
the existing 3D observer components. No additional weather service is needed.

## Build once

From the project root, with the existing virtual environment, CMake, MinGW and
the project's pinned pybind11 already installed:

```powershell
.\scripts\build_weather.ps1
.venv/Scripts/python.exe -m unittest discover -s weather_tests -v
```

The build reads the original native sources and applies checked, unique hooks
into generated files under `build/weather/generated`; it does not edit the
registered originals. Its source manifest and compiler configuration determine
its own build identity. `_underworld_weather` uses UW10W; the original
`_underworld` module continues to use UW9. `ALICE_WEATHER_BUILD` can select a
matching preserved weather build. `UNDERWORLD_BUILD` selects the original runtime
and does not select weather. DLL lookup uses the existing MinGW toolchain.

Weather SQLite format is `ALICE-WEATHER-2`. Source/build mismatch is an error,
not permission to recreate a database. The source-contracted authored policy
must match too. Development stage saves require their exact source ZIP overlaid
in a separate checkout and their matching `build/weather-w1`, `-w2`, `-w3` or
`-w4` runtime. Preserve them as evidence. Do not overlay historical sources into
an active experiment. The final registration is `artifacts/weather_registration.json`.

## Create and commit time

```powershell
.venv/Scripts/python.exe scripts/weather.py new --db data/my-weather.sqlite --config config/weather-research.toml
.venv/Scripts/python.exe scripts/weather.py inspect --db data/my-weather.sqlite
.venv/Scripts/python.exe scripts/weather.py run --db data/my-weather.sqlite --ticks 40
.venv/Scripts/python.exe scripts/weather.py policy-step --db data/my-weather.sqlite --agent agent-1
```

`new` refuses an existing path. The research year is 2400 simulated seconds,
four 600-second seasons. `config/weather-normal.toml` uses a 31557600-second
fictional year. Both retain the original 86400-second solar day, dt=.25s and
ordinary body/action/animal clocks. Season changes the sunlight amplitude,
temperature/rain distribution and explicitly configured growth inputs. It does
not accelerate other clocks. New ordinary weather worlds retain native initial
food16kg/water64kg; recorded demonstrations and continuous research explicitly
select food8kg/water16kg. Neither profile replenishes them by default.

`run` advances native ticks with no autonomous decisions. `policy-step` performs
one explicitly authored weather-aware decision for the named existing inhabitant.
The survival control is selected with `--policy survival`. Only that person's
observations and private observed-memory state enter its policy. No learned
weather policy or LLM is selected. For assigned execution:

```powershell
.venv/Scripts/python.exe scripts/weather.py policy-step --db data/my-weather.sqlite --agent agent-1 --assign build_simple_shelter
.venv/Scripts/python.exe scripts/weather.py policy-step --db data/my-weather.sqlite --agent agent-1 --assign prepare_supplies
```

These assign goals, not ingredients, finished roofs or skill. A partial roof
provides no protection. Subsequent policy steps handle prerequisites, urgent
needs, existing partial work and bounded failures. `repair_shelter` requires a
real damaged roof, carried wood and native work. Ordinary roof wear is recorded;
no destructive storm system is implemented. Assign a goal once, then continue
without repeatedly replacing it.

## Save and resume the same life

```powershell
.venv/Scripts/python.exe scripts/weather.py save --db data/my-weather.sqlite --destination data/my-weather-backup.sqlite
.venv/Scripts/python.exe scripts/weather.py inspect --db data/my-weather-backup.sqlite
.venv/Scripts/python.exe scripts/weather.py run --db data/my-weather-backup.sqlite --ticks 40
.venv/Scripts/python.exe scripts/weather.py replay --db data/my-weather-backup.sqlite
```

The SQLite backup API preserves the entire journal, in-flight work, weather
transition/PRNG, bodies, ledgers, own memories and scheduler state. Resume means
continuing an existing saved path, not calling `new` again. Backup destinations
must be unused. Native actions and journal/head updates commit atomically under
the existing single-writer lease; competing writers refuse rather than race.
The native replay checks actual request results and final policy state. Existing
finite native request and 25000-operation weather journal limits stop explicitly;
the system does not promise indefinite operation or silently discard evidence.

For all four inhabitants in a bounded continuously scheduled life:

```powershell
.venv/Scripts/python.exe scripts/weather_study.py continuity --db data/my-weather.sqlite --until 300 --output artifacts/my-weather-300.json
.venv/Scripts/python.exe scripts/weather_study.py continuity --db data/my-weather.sqlite --until 600 --output artifacts/my-weather-600.json
```

With an existing source-compatible weather database this continues that exact
life. If the specified database is absent, this research driver explicitly
initializes a four-person demonstration and physically builds a starting roof
through operator-assigned setup actions. That scaffold is not an autonomous or
learned construction success. The round-robin cursor persists across windows.
Use unique output names; results are not overwritten. Horizons are absolute
simulated clocks, not a sum of new episodes.

## Inspect through the read-only observer

```powershell
.venv/Scripts/python.exe -m underworld.weather_viewer --db data/my-weather.sqlite --port 8777
```

Open [the weather observer](http://127.0.0.1:8777/). It reuses `WorldView` and
shows native season/weather, °C, precipitation mm/hour, wind m/s, calendar,
selected own senses, exposure, goal/action, shelter condition/materials/work and
privileged climate diagnostics. The exact future target, change schedule and
PRNG are explicitly operator-only. The observer cannot write, advance time or
apply exposure; POST requests refuse. Reconnection reloads the current saved
state. Decorative clouds/rain/posts never cause physical effects. The renderer's
ordinary camera animation does not advance world time.

A prefilled NEW four-person viewer demonstration can be created separately:

```powershell
.venv/Scripts/python.exe scripts/weather_demo.py --db data/my-weather-demo.sqlite --output artifacts/my-weather-demo.json
```

This records assigned walking/harvesting/collecting/building/occupancy and a
guided weather intervention, then stops. It is not an unattended learned life.

## Recorded controlled weather

Use a NEW `--guided` world, or a separately named backup of an already guided
weather life. Closed worlds refuse forcing. Save the following example as a
payload, replacing `observation_version` with the currently inspected native tick:

```json
{
  "id": "rain-experiment-1",
  "observation_version": "0",
  "duration_s": 120,
  "temperature_c": -10,
  "rain_mm_h": 10,
  "cloud_fraction": 0.9,
  "wind_x_m_s": 4,
  "wind_y_m_s": 1
}
```

```powershell
.venv/Scripts/python.exe scripts/weather.py force --db data/my-guided-weather.sqlite --payload data/my-force.json
```

Forcing is native, version-checked, idempotent by matching ID/payload and recorded
in the journal/events/history. It has a bounded duration and is displayed as an
external intervention. Underlying seeded transitions continue and persist;
expiry returns to that natural state, with an explicit forcing boundary rather
than a claim of spontaneous weather. Read-only inspection never repeats it.

## Reproduce research

Read [the fixed protocol](WEATHER_EVALUATION_PROTOCOL.md) first. Use new unused
directories/output paths, retaining the registered sources and matching runtime:

```powershell
.venv/Scripts/python.exe scripts/weather_study.py run --development --directory data/weather-new-dev --output artifacts/weather-new-dev.json
.venv/Scripts/python.exe scripts/weather_study.py run --directory data/weather-new-confirmation --output artifacts/weather-new-confirmation.json
.venv/Scripts/python.exe scripts/weather_audit.py --study artifacts/weather-new-confirmation.json --directory data/weather-new-confirmation --output artifacts/weather-new-audit.json
```

Do not re-register changed sources against the existing held-out results. A new
study requires new held-out conditions after any tuning. The auditor needs actual
native saves; source commits contain exact gzip traces and save hashes, not the
ignored local SQLite databases. For original UW9 saves:

```powershell
$env:UNDERWORLD_BUILD=(Resolve-Path build/living-d).Path
.venv/Scripts/python.exe -m underworld inspect --db data/your-original-world.sqlite
```

Do not open original saves with the weather CLI. See
[WEATHER_SEASONS_REPORT.md](WEATHER_SEASONS_REPORT.md) for actual results and limits.
