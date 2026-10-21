"""Build-only, fail-closed hooks; historical registered native files stay unchanged."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = Path(sys.argv[1])
DEST.mkdir(parents=True, exist_ok=True)
sources = {p.name: p.read_text(encoding='utf8') for p in (ROOT / 'core').glob('*') if p.suffix in ('.cpp', '.hpp')}


def patch(name, old, new):
    if sources[name].count(old) != 1:
        raise ValueError(f'weather integration anchor mismatch: {name}: {old[:70]}')
    sources[name] = sources[name].replace(old, new)


patch('world.hpp', '#include "thermal.hpp"', '#include "thermal.hpp"\n#include "weather.hpp"')
patch('world.hpp', '    void configure_ecology(', '''    void configure_climate(const ClimateConfig&);
    const ClimateConfig& climate() const { return climate_; }
    const WeatherState& weather() const { return weather_; }
    SeasonState season() const;
    double ambient_c() const;
    std::string weather_kind() const;
    const Conditions& conditions() const;
    void force_weather(const std::string&, U64, const Conditions&, double, double);
    const std::map<std::string,LocalExposure>& exposures() const { return exposures_; }
    const Entity* protective_shelter(const Entity&) const;
    void configure_ecology(''')
patch('world.hpp', '    Ecology ecology_;', '''    ClimateConfig climate_;
    WeatherState weather_;
    std::map<std::string,LocalExposure> exposures_;
    void update_exposure();
    bool shelter_site_clear(Point) const;
    void update_weather();
    void write_weather(std::ostream&) const;
    void read_weather(std::istream&);
    void check_weather() const;
    Ecology ecology_;''')
patch('world.cpp', '    return 100*std::max', '    return (climate_.enabled?season().daylight*(1-.65*conditions().cloud):1)*100*std::max')
patch('world.cpp', '        replenish();', '        update_weather();\n        replenish();')
patch('world.cpp', '        update_bodies();', '        update_bodies();\n        update_exposure();')
patch('bodies.cpp', 'tree_growth_kg_s_*dt_*kg', 'tree_growth_kg_s_*(climate_.enabled?season().growth:1)*dt_*kg')
patch('ecology.cpp', 'ecology_.forage_rate*dt_*kg', 'ecology_.forage_rate*(climate_.enabled?season().growth:1)*dt_*kg')
# Native construction and its original transfers/reservations remain the authority.
patch('crafting.cpp', '        {"storage_box","structure",', '        {"lean_to","structure",{{"wood",800000000},{"fiber",100000000}},{},12,false,0},\n        {"storage_box","structure",')
patch('crafting.cpp', 'if(!clear_placement(a.destination,.5))return "NO_PLACEMENT";', 'if(!clear_placement(a.destination,.5))return "NO_PLACEMENT";\n            if(r->id=="lean_to"&&(!climate_.enabled||!shelter_site_clear(a.destination)))return "NO_PLACEMENT";')
patch('crafting.cpp', 'target->kind=r->id;++actor.workmanship;', 'target->kind=r->id;if(r->id=="lean_to")target->radius=0;++actor.workmanship;')
patch('world.cpp', '||e.kind=="gate") {', '||e.kind=="gate"||e.kind=="lean_to") {')
patch('world.cpp', '(!empty&&e.composition!=recipe->inputs)', '(!empty&&e.composition!=recipe->inputs&&e.kind!="lean_to")')
patch('crafting.cpp', 'bool crafting_action(const std::string& t){return ', 'bool crafting_action(const std::string& t){return t=="repair_shelter"||')
patch('crafting.cpp', '    if(a.type=="work_construction"||a.type=="cancel_construction") {', '''    if(a.type=="repair_shelter") {
        if(target->kind!="lean_to"||target->health>=1||a.duration_s<3||a.mass_ug||!a.text.empty()||!a.material.empty())return "INVALID_ARGUMENT";
        auto wood=actor.inventory.find("wood");if(wood==actor.inventory.end()||wood->second<100000000)return "INSUFFICIENT_RESOURCE";
        for(const auto&[id,p]:pending_)if(id!=actor.id&&p.remaining&&p.action.target_id==target->id)return "TARGET_BUSY";
        return "";
    }
    if(a.type=="work_construction"||a.type=="cancel_construction") {''')
patch('crafting.cpp', '        if(a.type=="work_construction") {', '''        if(a.type=="repair_shelter") {
            actor.inventory["wood"]-=100000000;target->composition["wood"]+=100000000;target->mass_ug+=100000000;
            target->health=std::min(1.0,target->health+.2);receipt.effect="repaired:"+target->id;
        } else if(a.type=="work_construction") {''')
patch('bindings.cpp', 'a.type=="work_construction"||a.type=="cancel_construction"||a.type=="toggle_gate"', 'a.type=="repair_shelter"||a.type=="work_construction"||a.type=="cancel_construction"||a.type=="toggle_gate"')
patch('world.cpp', '    write_ecology(out);', '    write_ecology(out);write_weather(out);')
patch('world.cpp', '    w.read_ecology(in);', '    w.read_ecology(in);w.read_weather(in);')
patch('world.cpp', 'void World::check_invariants() const {', 'void World::check_invariants() const {\n    check_weather();')
patch('world.cpp', '"UW9 "', '"UW10W "')
patch('world.cpp', 'magic!="UW9"', 'magic!="UW10W"')
patch('bindings.cpp', 'PYBIND11_MODULE(_underworld,m)', 'PYBIND11_MODULE(_underworld_weather,m)')
patch('bindings.cpp', 'm.attr("world_format")="UW9";', 'm.attr("world_format")="UW10W";')
patch('bindings.cpp', 'PYBIND11_MODULE(_underworld_weather,m)', '#include "weather_bindings.inc"\nPYBIND11_MODULE(_underworld_weather,m)')
patch('bindings.cpp', '        .def("step",', '''        .def("configure_climate",[](BoundWorld&w,py::dict p){configure_weather(w,p);})
        .def("weather_snapshot",[](const BoundWorld&w){return weather_snapshot(w);})
        .def("force_weather",[](BoundWorld&w,py::dict p,const std::string&principal){
            if(principal!="operator")throw py::value_error("UNAUTHORIZED");
            keys(p,{"id","observation_version","duration_s","temperature_c","rain_mm_h","cloud_fraction","wind_x_m_s","wind_y_m_s"});
            uw::Conditions c{0,number(p["cloud_fraction"]),number(p["rain_mm_h"]),number(p["wind_x_m_s"]),number(p["wind_y_m_s"])};
            w.core.force_weather(str(p["id"]),counter(p["observation_version"]),c,number(p["temperature_c"]),number(p["duration_s"]));
            return weather_snapshot(w);
        },"parameters"_a,"principal"_a)
        .def("step",''')
patch('bindings.cpp', '                own["tools"]=owned;', '                own["weather"]=weather_observation(w,id);\n                own["tools"]=owned;')

for name, text in sources.items():
    target = DEST / name
    if not target.exists() or target.read_text(encoding='utf8') != text:
        target.write_text(text, encoding='utf8', newline='\n')
manifest = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('core', 'weather_native') for p in sorted((ROOT / folder).glob('*')) if p.is_file()}
(DEST / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
