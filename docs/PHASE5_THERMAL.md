# Phase 5: bounded thermal and material model

The authoritative C++ engine now includes an optional four-vessel laboratory and one environmental heat node. It is enabled by `config/thermal-insulated.toml` or `config/thermal-open.toml`. The usual survival configuration keeps this lab disabled. Closed/guided **operator mode** is independent of insulated/open **thermal boundaries**.

## Species and initial conditions

Vessels `thermal-1..4` are fixed at (2,4), (4,4), (2,6), (4,6) metres in worlds at least 12 metres wide/high, with bodies enabled. Each holds up to 50 g of initially configured water, artificial fuel X and oxygen. Defaults are 20 g water, 20 g X, 40 g oxygen per vessel at 293.15 K. Products initially contain zero mass. Initial stock resolution is one microgram in configuration. Each vessel has 100 g inert structure, with heat capacity 50 J/K; the environmental node has 20 kg inert substrate, with heat capacity 10,000 J/K. These are authored surrogate material properties (500 J/kg/K).

Initialization withdraws water from the existing water pile and all 20.4 kg structure/substrate from the existing inert pile. Fuel and oxygen are explicit authored initial stocks. No material is counted twice. Initial thermal/chemical energy is recorded as an initial condition. Food, ordinary resource piles and abstract ingested reservoirs retain their earlier mass bookkeeping; they are outside this thermal network and have no modeled temperature. Resource regeneration and introduced material go to those ordinary piles, not directly into heated vessels. This is a small coupled laboratory, not whole-world thermochemistry.

## Heat and phases

`Q = m c ΔT`, `Q = m L`. The water energy proxy uses an absolute-zero reference: ice `2090 J/kg/K` to `273.15 K`; melting plateau `334000 J/kg`; liquid `4186 J/kg/K` to `373.15 K`; vaporization plateau `2256000 J/kg`; vapor `2020 J/kg/K` above boiling. Thresholds and values are constant approximations at **one atmosphere**. When initializing exactly at a threshold, the higher phase is selected. Enthalpy inversion then derives temperature and mixed phase fractions. Rounded integer phase masses always sum exactly to total water. Latent heat can be released on cooling through the same plateaus.

We call the stored caloric quantity `enthalpy_j`: it is an enthalpy-like bookkeeping proxy, **not a complete internal-energy model of a sealed pressure vessel**. There is no pressure, volume work, gas equation of state, pressure-dependent boiling, expansion, convection, fluid motion, solubility or temperature-dependent heat capacity. A closed-box conservation result establishes conservation of this declared proxy, not real sealed-vessel thermodynamics. Phase fractions are equilibrium closures without nucleation delay. Small vessels and amounts deliberately keep this model cheap.

Thermal state does not cause burns, body temperature changes, smoke exposure or equipment failure. Earlier hunger/thirst/fatigue mechanics remain abstract. Vessels are point apparatus locations for reach/sight, not new rigid-body containers. No practical real-world process safety or chemical handling guidance follows from this model.

Each vessel exchanges `G (T_a - T_b) Δt` with the environment (`G=2 W/K`). Grid neighbours exchange with `G=0.5 W/K`. All pair fluxes are evaluated simultaneously and debited/credited once. Explicit Euler uses substeps **h <= 0.05 s**, splitting each physical tick (0.01–1 s). Vessel heat capacity is at least 50 J/K, with summed conductance <=3 W/K, so `h ΣG/C <=0.003`: the conduction temperature update is a convex combination, with latent heat increasing effective capacity. The environment has C=10,000 J/K. At 1000 K its radiative derivative is about 90.7 W/K, well inside the same explicit stability bound. Tests compare equal 100 s runs at physical ticks 0.1, 0.2 and 1 s, all split to 0.05 s.

`electric` supplies up to 1000 W from an explicit external energy source. Only actually admitted joules enter `heater_input_j`. A 1000 K thermostat limits electrical input and reaction conversion; unused potential power is not charged or silently discarded. `off` stops input/reaction but not conduction. No ignition or controller intelligence is inferred.

## Artificial combustion

The mass-balanced artificial reaction is **1 mass unit fuel X + 2 mass units oxygen -> 3 mass units product P**. Oxygen here is a modeled oxidizer stock, not proof of a molecularly balanced real chemical equation. All three species have authored cp=1000 J/kg/K, so their combined sensible heat capacity is conserved by the reaction. X carries **1,000,000 J/kg** chemical energy. Pilot-enabled `burn` converts at most 0.0005 kg X/s, available X, half the available oxygen, and thermostat headroom. Released chemical energy becomes sensible/latent heat. Products remain in the vessel. Fractional-microgram rate remainders persist; an odd residual oxygen microgram cannot react. No real fuel identity, molar stoichiometry, emissions, kinetics or flame temperature is claimed.

## Boundaries and conservation

Insulated lab: actual sunlight absorption is zero, radiation and vents are disabled. Chemical burning conserves total heat-plus-chemical energy; electrical operation remains an explicitly open energy input even in an insulated apparatus. Potential daylight remains observable as environmental context.

Open lab: existing world sunlight `100 max(0,sin(2π t/86400)) W/m²` is accumulated over world area. A 1 m² collector transfers already-recorded sunlight from background energy to the environment; it does not create a second input. Ambient radiation uses `ε A σ (T⁴ - 293.15⁴)`, ε=0.8, A=0.5 m², σ=5.67e-8 W/m²/K⁴. Radiation entering/leaving is recorded separately. Each vessel vents at most 0.0001 kg/s of available vapor, removing its mass and corresponding vapor caloric energy. This is an authored outlet rule, not simulated pressure-driven flow. Integer phase/outlet rounding can affect transition timing at microgram scale.

Every checked state requires:

- Species masses = initial + recorded boundary sources + reaction deltas - outflow. X delta is `-burned`, oxygen `-2*burned`, product `+3*burned`; only water vents. All masses are nonnegative integers in micrograms, with exact mass closure.
- Global energy = background + vessel caloric energy + environmental caloric energy + remaining chemical energy.
- Expected global energy = initial thermal/chemical energy + actual world sunlight + operator energy + electrical heater input + incoming radiation - outgoing radiation - outflow caloric energy. Internal conduction and collector transfer cancel globally.
- Allowed energy residual is `max(1e-5 J, 1e-10 * expected energy)`. The 10 µJ floor and relative double-precision allowance accommodate accumulated floating arithmetic; neither mass nor reaction imbalance is forgiven. The subsystem separately checks its own flux balance. Measured errors are published in `artifacts/phase5_thermal.json` and CSV traces.

## Inhabitant actions and instruments

All use the existing ActionRequest envelope, current observation version, principal matching, idempotent request ID, delayed completion, native validation, durable decision journal and event receipts. Capability does not imply an inhabitant will spontaneously use it. A heat source stays set until another valid action switches it off, even if its operator leaves or dies.

| Action | target_ids | parameters | Minimum duration |
|---|---|---|---|
| `operate_heat` | one vessel | `{"mode":"off"}` / `electric` / `burn` | 1 s |
| `move_material` | source vessel, destination vessel | `{"material":"water","mass_kg":0.005}` | 1 s |
| `inspect` | one vessel | `{}` | 0.2 s |

Heat control/inspection require a visible vessel within 1.5 m. Transfer requires both distinct vessels visible and within 1.5 m, positive microgram-resolved mass <=1 kg and sufficient stock; accepted transfers recheck availability at completion. Allowed species: water, fuel_X, oxygen, product_P. Structure is fixed. Water transfer is a bulk aliquot of its current phase mix; it carries proportional caloric energy. Chemical species carry sensible heat and fuel carries its chemical potential. No exact hidden energy need be supplied by an agent, and no transfer creates free heat.

Ordinary visible entities expose the fixed vessel identity/structure only. Completed vessel inspection reports temperature rounded to 5 K and ice/liquid/vapor masses rounded to 5 g, plus heater setting. These are explicit modeled approximate instruments; rounded phase readings need not sum to rounded total. Results/event references are captured into the inhabitant's private memory. Exact thermal/chemical values are available only in the **privileged operator snapshot** and labeled observer panel. Provider context uses ordinary perception and own episodes, never privileged thermal state.

The bounded cognitive compiler adds `heat_electric`, `heat_burn`, `heat_off` (target vessel, empty text) and `transfer_water` (target source, text destination, authored fixed 5 g aliquot). Native rules still decide success. Grammar alternatives are offered only for reachable vessels. No new trained policy, chemistry understanding, autonomous scientific discovery or model-weight training was tested. Incorrect scientific speech changes report/memory records but leaves the physical model unchanged under identical physical actions.

## Reproduce

From the repository root, with the built extension:

```powershell
$env:PATH = "C:\mingw64\bin;$env:PATH"
.\.venv\Scripts\python.exe scripts\verify.py --core build\underworld_core.exe
.\.venv\Scripts\python.exe scripts\phase5_evidence.py --directory data\fresh-thermal-evidence
.\.venv\Scripts\python.exe -m underworld observe --db data\fresh-thermal-evidence\lab.sqlite --port 8765
```

The evidence runner refuses existing directories and records model-off physical traces, a durable heating/inspection/transfer demonstration, mid-action backup/resume and replay. The observer starts paused. For a separate fresh experiment use `new --manual --config config/thermal-open.toml --db data/my-lab.sqlite`; external JSONL decisions retain the Phase 2 envelope. Do not advance the same database concurrently with its observer writer.

Native format **UW4**, SQLite **user_version=5**, package **0.6.0**. Thermal masses, energy, controls, rate remainders and pending actions survive checkpoints. Native and runtime hashes pin the experiment. Prior saved runs/reports remain historical; no automatic migration exists. Thermal settings are fixed at creation; the existing mode/hearing fork preserves thermal state and configuration. Phase 6 remains deferred.
