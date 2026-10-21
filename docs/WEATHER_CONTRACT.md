# Opt-in weather contract, fixed before implementation

22 October 2026. W0-W6 are sequential acceptance stages, not intelligence gates.
The current H gap study is complete and there are no active simulation processes.
All historical registered source bytes and `build/living-d` remain unchanged.
The additive `weather_native` build generates a checked integration of the old
native engine and new environmental hooks under `build/weather/generated`.
Generated files are build products, not another maintained copy of the engine.
Its separate module/format/build identity rejects old saves; no migration.

## Units, state and time

`ClimateConfig` v1: opt-in enabled, year_seconds [240,315576000], transition_seconds
[1,600], change_seconds [transition_seconds,3600], temperature_bias_c [-30,30].
All numeric inputs finite; booleans strict. Standard fictional year is31557600s;
research year2400s (four600s seasons). Neither changes dt, body rates, wear,
animal aging, crop clocks nor the existing86400s solar day.

`WeatherState` v1: tick/source, clear/cloudy/rain, from/current/target cloud fraction
[0,1], precipitation mm/hour [0,12], wind x/y m/s [-10,10], temperature offset C
[-4,4], transition start/end seconds, next change and independent seeded PRNG.
`SeasonState` v1: spring/summer/autumn/winter, year index, phase progress; fictional
season centers12/24/11/0 C, rain probabilities.35/.15/.45/.40, daylight factors
.85/1/.75/.55, growth factors1/.8/.35/.05. Cubic interpolation across each phase
has zero slope at boundaries. Weather offsets transition continuously. Simulation
ticks alone advance time; JSON/observer GET/checkpoint do not advance anything.
Daylight retains100max(0,sin(2pi*t/86400))W/m2 multiplied by season envelope and
(1-.65*cloud). This changes actual native solar ledger, not just sky color.

`LocalExposure` v1: per-own-body dimensionless wetness/cold burden [0,1], felt rain
and wind, cumulative environmental fatigue/health loss, actual shelter ID and
tick/source. Proxies are not water mass, temperature or realistic physiology.
`WeatherObservation`: local felt temperature rounded C, visible rain/cloud class,
noticed wind, own exposure and visible native shelters only. Exact future target,
PRNG, global map and another person's body are privileged diagnostics only.

W2 planned rules: wetness increases .012*(rain/12)*rain_factor per second, dries
.004*(1-rain/12) per second; cold drive clamp((10-temp)/20,0,1)*(1+.5*wetness)
times wind factor. Cold approaches drive at .012/s and recovers .006/s. Exposure
fatigue .0015*burden/s; health loss .0015*max(0,(burden-.65)/.35)/s. Ordinary
needs damage remains separate. No actual body heat/rain water reservoir is added.
Rain collection deferred. Seasonal ecological multipliers apply only to configured
native boundary rates, preserving zero regeneration and existing caps/ledgers.

## Shelter blueprint and feasibility (W3)

Open lean-to: .8kg wood + .1kg fiber,0waste,no tool,12s native work plus1s site
transfer. Maximum carried2kg; .9kg ingredients fit alongside .05kg food/.05kg water.
The youngest tree starts2kg: existing native branch conversion yields.9kg wood/.1kg fiber from
1kg tree biomass, enough for one roof with.1kg wood left. Four roofs would need
4kg tree biomass; original total18kg suffices only through actual harvesting.
No materials are granted by a task or recipe. Repair .1kg wood plus3s work, retained
as extra wood composition; ordinary condition wear is .00002 per simulated second,
with no structural collapse. Repair restores up to.2 condition. Storm destruction deferred.

`ShelterState`: stable native entity ID,1.1m circular roof coverage, condition[0,1],
capacity4 physically separated bodies, work[0,12]s, actual composition. Incomplete
sites provide zero protection. Complete roofs are not solid interior discs; an
open structure has no collision walls or closing door. Rain factor.1, wind factor.5,
cold factor.7 at full condition; condition linearly weakens protection. Protection
requires body center plus.25m radius inside roof, inclusive boundary; sorted local
occupants beyond capacity get no protection. Footprints cannot overlap other
sites/obstacles. Reserved construction sites retain existing.5m collision. Stable
material transfer, work, rejection and request-ID semantics reuse native crafting.

## Stage gates and attribution

W0: old model-off regressions green; old format refused by new runtime; weather
disabled matches old body/stocks/actions; malformed/nonfinite climate refused.
W1: deterministic same-runtime seed/actions; fractional transition; fresh-process
mid-transition resume; inspections inert; boundaries/long time/configuration checks.
Only after these pass, implement W2 exposure/accounting, W3 real shelters, W4
own-observation authored decisions, W5 observer/recorded forcing, W6 final matched
evaluation. Failed checks remain recorded; never silently lower thresholds.

W4 priorities: urgent survival before exposure, then sheltered recovery; real
material prerequisites, bounded retries and stable durable goals. Externally assigned
building, authored autonomy and developmental learning are distinct. No developmental
weather policy is claimed. No shared language/forecast is injected.

Development refinement before confirmation: routine half-full needs interrupted
four-person shelter trips. Survival control retains.5 thresholds. Weather policy
starts routine supply at.6, preserves a supply-trip latch until below.5, and
preempts shelter travel or its30s settling interval only for urgent.8 needs.
Protected rest decisions use1s frames so the serial scheduler lets others react;
native body/rest rates do not change. These are authored priorities/hysteresis,
not learned motivations. Three failed sharing development candidates are retained.

W6 prospective evaluation will be frozen after development and before held-out
measurement. Development seeds53/71; reserve held-out13001/13007/13009. Match native
initial conditions and weather schedule across survival-only and weather-aware
arms; report construction execution separately. One finite continuous life through
at least600s if budget permits. Primary compute budget1200wall seconds and
600perseed. No neural training, emotions, reproduction, new speech or true3D.
