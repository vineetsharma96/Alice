#include "world.hpp"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <charconv>
#include <algorithm>
#include <cmath>
#include <set>

namespace py=pybind11;
using namespace pybind11::literals;
namespace {
struct BoundWorld {
    uw::World core;
    std::string run_id;
    BoundWorld(uw::U64 seed,unsigned population,double width,double height,double dt,
               uw::U64 interval,bool scripted,std::string run,bool bodies,double food,double water,double food_regen,double water_regen,bool guided,double hearing,double tree_growth)
        :core(seed,population,width,height,dt,interval,scripted,bodies,food,water,food_regen,water_regen,tree_growth),run_id(std::move(run)){core.configure_branch(guided,hearing);}
};
void keys(py::dict d,std::set<std::string> expected) {
    std::set<std::string> actual;
    for(auto item:d) {
        if(!py::isinstance<py::str>(item.first))throw py::value_error("INVALID_ARGUMENT: non-string key");
        actual.insert(py::cast<std::string>(item.first));
    }
    if(actual!=expected)throw py::value_error("INVALID_ARGUMENT: unknown or missing fields");
}
std::string str(py::handle h) {
    if(!py::isinstance<py::str>(h))throw py::value_error("INVALID_ARGUMENT: expected string");
    auto s=py::cast<std::string>(h);
    if(s.size()>128)throw py::value_error("PAYLOAD_TOO_LARGE");
    return s;
}
uw::U64 counter(py::handle h) {
    auto s=str(h);uw::U64 n{};
    auto [p,e]=std::from_chars(s.data(),s.data()+s.size(),n);
    if(s.empty()||e!=std::errc{}||p!=s.data()+s.size()||(s.size()>1&&s[0]=='0'))
        throw py::value_error("INVALID_ARGUMENT: expected canonical uint64 string");
    return n;
}
double number(py::handle h) {
    if(py::isinstance<py::bool_>(h)||(!py::isinstance<py::int_>(h)&&!py::isinstance<py::float_>(h)))
        throw py::value_error("INVALID_ARGUMENT: expected numeric value");
    double n=py::cast<double>(h);
    if(!std::isfinite(n))throw py::value_error("INVALID_ARGUMENT: nonfinite number");
    return n;
}
py::dict entity(const uw::Entity& e,bool inventory=true,bool bodies=false) {
    py::dict d("entity_id"_a=e.id,"kind"_a=e.kind,"position_m"_a=py::make_tuple(e.position.x,e.position.y),
               "radius_m"_a=e.radius,"mass_kg"_a=static_cast<double>(e.mass_ug)/1e9,
               "mass_ug"_a=std::to_string(e.mass_ug));
    if(e.kind=="tree")d["stage"]=e.stage,d["health"]=e.health,d["biomass_ug"]=std::to_string(e.biomass_ug);
    if(inventory) {py::dict inv;for(auto&[kind,mass]:e.inventory)inv[py::str(kind)]=std::to_string(mass);d["inventory_ug"]=inv;}
    if(bodies&&e.kind=="actor") {
        d["alive"]=e.body.alive;
        if(inventory)d["body"]=py::dict("hunger"_a=e.body.hunger,"thirst"_a=e.body.thirst,
            "fatigue"_a=e.body.fatigue,"health"_a=e.body.health,"alive"_a=e.body.alive,
            "food_ingested_ug"_a=std::to_string(e.body.food_ingested_ug),"water_ingested_ug"_a=std::to_string(e.body.water_ingested_ug));
    }
    return d;
}
py::dict result(const uw::Result& r) {
    py::list refs;for(auto ref:r.event_refs)refs.append(std::to_string(ref));
    return py::dict("schema_version"_a=1,"request_id"_a=r.request_id,"agent_id"_a=r.agent_id,
        "status"_a=r.status,"error_code"_a=r.error,"reason"_a=r.error,
        "started_tick"_a=std::to_string(r.started),"completed_tick"_a=std::to_string(r.completed),
        "observation_version"_a=std::to_string(r.version),"event_refs"_a=refs,
        "observable_effects"_a=py::dict("description"_a=r.effect));
}
}
PYBIND11_MODULE(_underworld,m) {
    m.attr("build_id")=UW_BUILD_ID;
    py::class_<BoundWorld>(m,"World")
        .def(py::init<uw::U64,unsigned,double,double,double,uw::U64,bool,std::string,bool,double,double,double,double,bool,double,double>(),
             "seed"_a=20261019,"population"_a=8,"width"_a=64,"height"_a=64,"dt"_a=.1,
             "interval"_a=50,"scripted"_a=true,"run_id"_a="test","bodies"_a=false,
             "food_kg"_a=16,"water_kg"_a=64,"food_regen_kg_s"_a=0,"water_regen_kg_s"_a=0,"guided"_a=false,"hearing_range_m"_a=6,"tree_growth_kg_s"_a=0)
        .def("checkpoint",[](const BoundWorld&w){return w.core.serialize();})
        .def_static("restore",[](const std::string&state,const std::string&run_id){
             BoundWorld w(1,1,64,64,.1,50,false,run_id,false,16,64,0,0,false,6,0);w.core=uw::World::restore(state);return w;
        },"state"_a,"run_id"_a="test")
        .def("_configure_branch",[](BoundWorld&w,bool guided,double hearing){w.core.configure_branch(guided,hearing);})
        .def("configure_thermal",[](BoundWorld&w,bool open,double water,double fuel,double oxygen,double temperature){w.core.configure_thermal(open,water,fuel,oxygen,temperature);},
             "open_boundaries"_a=false,"water_kg"_a=.02,"fuel_kg"_a=.02,"oxygen_kg"_a=.04,"temperature_k"_a=293.15)
        .def("configure_culture",[](BoundWorld&w,uw::U64 seed){w.core.configure_culture(seed);},"apparatus_seed"_a)
        .def("intervene",[](BoundWorld&w,py::dict d,const std::string& principal){
            if(principal!="operator")throw py::value_error("UNAUTHORIZED: operator channel required");
            keys(d,{"schema_version","run_id","branch_id","intervention_id","observation_version","kind","parameters"});
            if(py::isinstance<py::bool_>(d["schema_version"])||!py::isinstance<py::int_>(d["schema_version"])||py::cast<int>(d["schema_version"])!=1)throw py::value_error("UNSUPPORTED_SCHEMA");
            if(str(d["run_id"])!=w.run_id)throw py::value_error("UNAUTHORIZED");
            str(d["branch_id"]);
            if(counter(d["observation_version"])!=w.core.tick())throw py::value_error("STALE_OBSERVATION");
            if(!py::isinstance<py::dict>(d["parameters"]))throw py::value_error("INVALID_ARGUMENT");
            auto p=py::cast<py::dict>(d["parameters"]);auto kind=str(d["kind"]),id=str(d["intervention_id"]);
            std::string entity_id,material,text;uw::Point position{};std::int64_t mass=0;double energy=0;
            auto content=[&](){if(!py::isinstance<py::str>(p["text"]))throw py::value_error("INVALID_ARGUMENT");text=py::cast<std::string>(p["text"]);if(text.size()>1024)throw py::value_error("PAYLOAD_TOO_LARGE");};
            if(kind=="place_book"||kind=="introduce_object") {
                if(kind=="place_book")keys(p,{"entity_id","x_m","y_m","mass_kg","energy_j","text"});
                else keys(p,{"entity_id","x_m","y_m","mass_kg","energy_j","material"});
                entity_id=str(p["entity_id"]);position={number(p["x_m"]),number(p["y_m"])};energy=number(p["energy_j"]);
                const double amount=number(p["mass_kg"]);
                if(amount<=0||amount>1000||std::abs(amount*1e9-std::round(amount*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution");
                mass=static_cast<std::int64_t>(std::llround(amount*1e9));
                if(kind=="place_book"){material="inert_material";content();}else material=str(p["material"]);
            } else if(kind=="avatar_message"||kind=="broadcast") {
                if(kind=="avatar_message"){keys(p,{"x_m","y_m","text"});position={number(p["x_m"]),number(p["y_m"])};}
                else keys(p,{"text"});content();
            } else throw py::value_error("UNKNOWN_INTERVENTION");
            auto seq=w.core.intervene(id,kind,entity_id,position,material,mass,energy,text);
            return py::dict("schema_version"_a=1,"intervention_id"_a=id,"status"_a="applied","event_refs"_a=std::vector<std::string>{std::to_string(seq)});
        },"request"_a,"principal"_a)
        .def("check_invariants",[](const BoundWorld&w){w.core.check_invariants();})
        .def("_compact_history",[](BoundWorld&w){return w.core.compact_history();})
        .def("snapshot",[](const BoundWorld&w){
            py::list entities,pending;py::dict totals;
            std::map<std::string,std::int64_t> masses;
            for(const auto&e:w.core.entities()) {
                auto projected=entity(e,true,w.core.bodies_enabled());
                if(e.kind=="actor")projected["present"]=!w.core.culture().departed.contains(e.id);
                entities.append(projected);
                if(e.kind!="actor"&&e.kind!="rock"&&e.kind!="operator_avatar"&&e.kind!="thermal_cell")masses[e.kind=="book"||e.kind=="object"?"inert_material":e.kind]+=e.mass_ug;
                for(const auto&[kind,mass]:e.inventory)masses[kind]+=mass;
                if(e.kind=="actor") {masses["food"]+=e.body.food_ingested_ug;masses["water"]+=e.body.water_ingested_ug;}
            }
            for(const auto&[id,p]:w.core.pending())pending.append(py::dict("agent_id"_a=id,"request_id"_a=p.action.request_id,"remaining_ticks"_a=std::to_string(p.remaining)));
            const auto& thermal=w.core.thermal();
            for(const auto&[kind,mass]:thermal.masses())masses[kind]+=mass;
            for(const auto&[kind,mass]:masses)totals[py::str(kind)]=std::to_string(mass);
            py::list cells;
            if(thermal.enabled)for(unsigned i=0;i<4;++i) {
                const auto& c=thermal.cells[i];auto phases=c.phase_masses();
                cells.append(py::dict("entity_id"_a="thermal-"+std::to_string(i+1),"temperature_k"_a=c.phase().temperature,
                    "enthalpy_j"_a=c.enthalpy,"heater"_a=c.heater,"water_ug"_a=std::to_string(c.water),
                    "ice_ug"_a=std::to_string(phases[0]),"liquid_ug"_a=std::to_string(phases[1]),"vapor_ug"_a=std::to_string(phases[2]),
                    "fuel_X_ug"_a=std::to_string(c.fuel),"oxygen_ug"_a=std::to_string(c.oxygen),"product_P_ug"_a=std::to_string(c.product)));
            }
            const double expected=thermal.initial_energy+w.core.solar_input()+w.core.operator_energy()+thermal.heater_input+thermal.radiation_in-thermal.radiation_out-thermal.outflow_energy;
            py::dict heat("enabled"_a=thermal.enabled,"open_boundaries"_a=thermal.open_boundaries,"cells"_a=cells,
                "ambient_temperature_k"_a=thermal.enabled?thermal.ambient_enthalpy/uw::ThermalModel::ambient_capacity:0,
                "stored_energy_j"_a=thermal.stored_energy(),"initial_energy_j"_a=thermal.initial_energy,
                "heater_input_j"_a=thermal.heater_input,"radiation_in_j"_a=thermal.radiation_in,"radiation_out_j"_a=thermal.radiation_out,
                "outflow_energy_j"_a=thermal.outflow_energy,"solar_transferred_j"_a=thermal.solar_transferred,
                "burned_fuel_ug"_a=std::to_string(thermal.burned_fuel),"outflow_water_ug"_a=std::to_string(thermal.outflow_water),
                "balance_error_j"_a=thermal.balance_error(),"global_balance_error_j"_a=w.core.energy()+thermal.stored_energy()-expected,
                "energy_tolerance_j"_a=std::max(1e-5,1e-10*expected));
            const auto& culture=w.core.culture();py::list agreements,batches,artifacts;py::dict skills;
            for(const auto& [id,p]:culture.practice)skills[py::str(id)]=py::dict("level"_a=p.successes,"min_duration_s"_a=w.core.practice_seconds(id),"last_event"_a=std::to_string(p.last_event));
            for(const auto& [id,g]:culture.agreements)agreements.append(py::dict("id"_a=id,"proposer"_a=g.proposer,"partner"_a=g.partner,"text"_a=g.text,"status"_a=g.status,"offered_event"_a=std::to_string(g.offered_event),"accepted_event"_a=std::to_string(g.accepted_event),"completed_event"_a=std::to_string(g.completed_event),"expires_tick"_a=std::to_string(g.expires_tick)));
            for(const auto& b:culture.batches)batches.append(py::dict("event_seq"_a=std::to_string(b.seq),"tick"_a=std::to_string(b.tick),"agent"_a=b.agent,"dial"_a=b.dial,"measured_k"_a=b.measured_k,"work_s"_a=b.work_s));
            py::dict cultural("enabled"_a=culture.enabled,"skills"_a=skills,"agreements"_a=agreements,"validated_batches"_a=batches,"departed"_a=std::vector<std::string>(culture.departed.begin(),culture.departed.end()));
            if(culture.enabled)cultural["hidden_apparatus"]=py::dict("seed"_a=std::to_string(culture.apparatus_seed),"target_k"_a=culture.target_k,"dial"_a=culture.dials.at(culture.correct_dial));
            return py::dict("schema_version"_a=1,"kind"_a="world_snapshot","run_id"_a=w.run_id,"culture"_a=cultural,
                "branch_id"_a=w.run_id,"tick"_a=std::to_string(w.core.tick()),
                "observation_version"_a=std::to_string(w.core.tick()),"last_event_seq"_a=std::to_string(w.core.seq()),
                "seed"_a=std::to_string(w.core.seed()),"dt_s"_a=w.core.dt(),
                "simulated_time_s"_a=w.core.tick()*w.core.dt(),"laws_version"_a="culture-6","thermal"_a=heat,
                "build_id"_a=UW_BUILD_ID,"world_bounds_m"_a=py::dict("width"_a=w.core.width(),"height"_a=w.core.height()),
                "entities"_a=entities,"outstanding_actions"_a=pending,"material_totals_ug"_a=totals,"event_counts"_a=w.core.event_counts(),
                "solar_input_j"_a=w.core.solar_input(),"environment_energy_j"_a=w.core.energy(),
                "operator_energy_input_j"_a=w.core.operator_energy(),"operator_sources_ug"_a=w.core.operator_mass(),
                "mode"_a=(w.core.guided()?"guided":"closed"),"hearing_range_m"_a=w.core.hearing_range(),
                "sunlight_w_m2"_a=w.core.sunlight_w_m2(),"scripted"_a=w.core.scripted(),
                "next_script_tick"_a=std::to_string(w.core.next_script_tick()),"bodies_enabled"_a=w.core.bodies_enabled(),
                "initial_mass_ug"_a=w.core.initial_mass(),"boundary_sources_ug"_a=w.core.source_mass());
        })
        .def("observe_batch",[](const BoundWorld&w,const std::vector<std::string>&ids){
            if(ids.size()>64)throw py::value_error("PAYLOAD_TOO_LARGE");
            py::list observations;
            for(const auto&id:ids) {
                auto nearby=w.core.nearby(id);py::list visible,results;
                for(const auto&e:nearby)visible.append(entity(e,false,w.core.bodies_enabled()));
                py::dict own;
                for(const auto&e:w.core.entities())if(e.id==id)own=entity(e,true,w.core.bodies_enabled());
                own["busy"]=w.core.pending().contains(id);
                py::list social,offers;
                const auto& culture=w.core.culture();
                if(culture.enabled) {
                    auto p=culture.practice.find(id);const auto level=p==culture.practice.end()?0:p->second.successes;
                    own["present"]=!culture.departed.contains(id);
                    own["skills"]=py::dict("water_conditioning"_a=py::dict("level"_a=level,"min_duration_s"_a=w.core.practice_seconds(id),"last_event"_a=p==culture.practice.end()?"0":std::to_string(p->second.last_event)));
                    for(const auto& [key,pair]:w.core.requests())if(pair.first.agent_id==id&&pair.first.type=="inspect"&&pair.first.target_id=="thermal-1"&&pair.second.status=="completed") {own["apparatus_dials"]=culture.dials;break;}
                    auto found=culture.interactions.find(id);
                    if(found!=culture.interactions.end())for(const auto& i:found->second)social.append(py::dict("source_event_seq"_a=std::to_string(i.seq),"tick"_a=std::to_string(i.tick),"other"_a=i.other,"kind"_a=i.kind));
                    for(const auto& [key,g]:culture.agreements)if((g.proposer==id||g.partner==id)&&(w.core.visible(id,"thermal-1",1.5)||w.core.visible(id,g.proposer==id?g.partner:g.proposer,w.core.hearing_range())))offers.append(py::dict("id"_a=key,"proposer"_a=g.proposer,"partner"_a=g.partner,"text"_a=g.text,"status"_a=g.status,"expires_tick"_a=std::to_string(g.expires_tick)));
                }
                py::list shared;
                for(const auto&[key,pair]:w.core.requests())if(pair.first.agent_id==id&&pair.first.type=="speak"&&pair.first.evidence_seq&&pair.second.status=="completed")shared.append(std::to_string(pair.first.evidence_seq));
                while(py::len(shared)>16)shared.attr("pop")(0);
                own["shared_event_refs"]=shared;
                if(w.core.pending().contains(id))own["action_type"]=w.core.pending().at(id).action.type;
                py::list heard,readings;
                auto report=[&](const uw::Message& message,const char* kind){return py::dict(
                    "source_event_seq"_a=std::to_string(message.seq),"delivery_tick"_a=std::to_string(message.tick),
                    "speaker_id"_a=message.speaker_id,"text"_a=message.text,"kind"_a=kind,
                    "origin_event_seq"_a=std::to_string(message.origin_seq),"parent_event_seq"_a=std::to_string(message.parent_seq),
                    "source_id"_a=message.source_id,"observer_id"_a=id,"confidence"_a="unverified");};
                auto messages=w.core.messages().find(id);
                if(messages!=w.core.messages().end())for(const auto&message:messages->second)heard.append(report(message,"unverified_report"));
                auto reads=w.core.readings().find(id);
                if(reads!=w.core.readings().end())for(const auto& message:reads->second)readings.append(report(message,"book_read"));
                // Only this agent's action history, bounded to the newest 16 results.
                std::vector<uw::Result> recent;
                for(const auto&[key,pair]:w.core.requests())if(pair.second.agent_id==id)recent.push_back(pair.second);
                std::sort(recent.begin(),recent.end(),[](const auto&a,const auto&b){return a.started==b.started?a.request_id<b.request_id:a.started<b.started;});
                for(std::size_t i=recent.size()>16?recent.size()-16:0;i<recent.size();++i)results.append(result(recent[i]));
                observations.append(py::dict("schema_version"_a=1,"run_id"_a=w.run_id,"agent_id"_a=id,
                    "tick"_a=std::to_string(w.core.tick()),"observation_version"_a=std::to_string(w.core.tick()),
                    "own_state"_a=own,"visible_entities"_a=visible,"audible_reports"_a=heard,"read_reports"_a=readings,"social_reports"_a=social,"task_offers"_a=offers,
                    "world_bounds_m"_a=py::dict("width"_a=w.core.width(),"height"_a=w.core.height()),
                    "sight_range_m"_a=8,"hearing_range_m"_a=w.core.hearing_range(),
                    "dt_s"_a=w.core.dt(),
                    "recent_action_results"_a=results,"omissions"_a=py::dict("older_results"_a=(recent.size()>16?recent.size()-16:0))));
            }return observations;
        })
        .def("submit",[](BoundWorld&w,py::dict d,const std::string&principal){
            keys(d,{"schema_version","run_id","request_id","agent_id","observation_version","action_type","target_ids","parameters","requested_duration"});
            if(!py::isinstance<py::int_>(d["schema_version"])||py::isinstance<py::bool_>(d["schema_version"])||py::cast<int>(d["schema_version"])!=1)
                throw py::value_error("UNSUPPORTED_SCHEMA");
            if(str(d["run_id"])!=w.run_id||str(d["agent_id"])!=principal)throw py::value_error("UNAUTHORIZED");
            uw::Action a;a.agent_id=str(d["agent_id"]);a.request_id=str(d["request_id"]);
            a.version=counter(d["observation_version"]);a.type=str(d["action_type"]);a.duration_s=number(d["requested_duration"]);
            if(!py::isinstance<py::list>(d["target_ids"])||!py::isinstance<py::dict>(d["parameters"]))throw py::value_error("INVALID_ARGUMENT");
            auto targets=py::cast<py::list>(d["target_ids"]);auto params=py::cast<py::dict>(d["parameters"]);
            if(a.type=="move") {
                if(!targets.empty())throw py::value_error("INVALID_ARGUMENT");
                keys(params,{"x_m","y_m"});a.destination={number(params["x_m"]),number(params["y_m"])};
            } else if(a.type=="gather"||a.type=="deposit"||a.type=="eat"||a.type=="drink") {
                const bool consumption=a.type=="eat"||a.type=="drink";
                if(targets.size()!=(consumption?0:1))throw py::value_error("INVALID_ARGUMENT");
                if(!consumption)a.target_id=str(targets[0]);keys(params,{"mass_kg"});double mass=number(params["mass_kg"]);
                if(mass<=0||mass>10||std::abs(mass*1e9-std::round(mass*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution is 1 microgram");
                a.mass_ug=static_cast<std::int64_t>(std::llround(mass*1e9));
            } else if(a.type=="inspect_tree") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);keys(params,{});
            } else if(a.type=="harvest_branch") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);
                if(params.contains("x_m")||params.contains("y_m")) {
                    keys(params,{"mass_kg","x_m","y_m"});a.destination={number(params["x_m"]),number(params["y_m"])};
                } else keys(params,{"mass_kg"});
                const double mass=number(params["mass_kg"]);
                if(mass<=0||mass>10||std::abs(mass*1e9-std::round(mass*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution is 1 microgram");
                a.mass_ug=static_cast<std::int64_t>(std::llround(mass*1e9));
            } else if(a.type=="fell_tree") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);
                if(params.contains("x_m")||params.contains("y_m")) {keys(params,{"x_m","y_m"});a.destination={number(params["x_m"]),number(params["y_m"])};}
                else keys(params,{});
            } else if(a.type=="collect_wood") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);keys(params,{"material","mass_kg"});a.material=str(params["material"]);
                const double mass=number(params["mass_kg"]);
                if(mass<=0||mass>10||std::abs(mass*1e9-std::round(mass*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution is 1 microgram");
                a.mass_ug=static_cast<std::int64_t>(std::llround(mass*1e9));
            } else if(a.type=="give") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                keys(params,{"material","mass_kg"});a.target_id=str(targets[0]);a.material=str(params["material"]);const double mass=number(params["mass_kg"]);
                if(mass<=0||mass>1||std::abs(mass*1e9-std::round(mass*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution");
                a.mass_ug=static_cast<std::int64_t>(std::llround(mass*1e9));
            } else if(a.type=="offer_task"||a.type=="process_batch") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);const auto field=a.type=="offer_task"?"text":"dial";keys(params,{field});
                if(!py::isinstance<py::str>(params[field]))throw py::value_error("INVALID_ARGUMENT");a.text=py::cast<std::string>(params[field]);
                if(a.text.size()>160)throw py::value_error("PAYLOAD_TOO_LARGE");
            } else if(a.type=="respond_task") {
                if(!targets.empty())throw py::value_error("INVALID_ARGUMENT");
                keys(params,{"agreement_id","accept"});a.target_id=str(params["agreement_id"]);
                if(!py::isinstance<py::bool_>(params["accept"]))throw py::value_error("INVALID_ARGUMENT");a.text=py::cast<bool>(params["accept"])?"accept":"decline";
            } else if(a.type=="write_book") {
                if(!targets.empty())throw py::value_error("INVALID_ARGUMENT");
                keys(params,{"text","evidence_ref"});a.evidence_seq=counter(params["evidence_ref"]);
                if(!py::isinstance<py::str>(params["text"]))throw py::value_error("INVALID_ARGUMENT");a.text=py::cast<std::string>(params["text"]);
                if(a.text.size()>512)throw py::value_error("PAYLOAD_TOO_LARGE");
            } else if(a.type=="depart") {
                if(!targets.empty())throw py::value_error("INVALID_ARGUMENT");keys(params,{});
            } else if(a.type=="operate_heat") {
                if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);keys(params,{"mode"});a.text=str(params["mode"]);
            } else if(a.type=="move_material") {
                if(targets.size()!=2)throw py::value_error("INVALID_ARGUMENT");
                a.target_id=str(targets[0]);a.destination_id=str(targets[1]);keys(params,{"mass_kg","material"});a.material=str(params["material"]);
                const double mass=number(params["mass_kg"]);
                if(mass<=0||mass>1||std::abs(mass*1e9-std::round(mass*1e9))>1e-5)throw py::value_error("INVALID_ARGUMENT: mass resolution");
                a.mass_ug=static_cast<std::int64_t>(std::llround(mass*1e9));
            } else if(a.type=="rest"||a.type=="inspect"||a.type=="speak"||a.type=="read") {
                if(a.type=="inspect"||a.type=="read") {
                    if(targets.size()!=1)throw py::value_error("INVALID_ARGUMENT");
                    a.target_id=str(targets[0]);keys(params,{});
                } else {
                    if(!targets.empty())throw py::value_error("INVALID_ARGUMENT");
                    if(a.type=="speak") {
                        if(params.contains("evidence_ref")){keys(params,{"text","evidence_ref"});a.evidence_seq=counter(params["evidence_ref"]);}
                        else keys(params,{"text"});
                        if(!py::isinstance<py::str>(params["text"]))throw py::value_error("INVALID_ARGUMENT");
                        a.text=py::cast<std::string>(params["text"]);
                        if(a.text.empty()||a.text.size()>512)throw py::value_error("PAYLOAD_TOO_LARGE");
                    } else keys(params,{});
                }
            } else throw py::value_error("UNKNOWN_ACTION");
            auto r=result(w.core.submit(a));r["run_id"]=w.run_id;return r;
        },"request"_a,"principal_agent"_a)
        .def("step",[](BoundWorld&w,unsigned ticks){
            std::vector<uw::Event> events;
            {py::gil_scoped_release release;events=w.core.step(ticks);}
            py::list out;
            for(const auto&e:events)out.append(py::dict("schema_version"_a=1,"seq"_a=std::to_string(e.seq),
                "tick"_a=std::to_string(e.tick),"type"_a=e.type,"agent_id"_a=e.agent_id,
                "request_id"_a=e.request_id,"detail"_a=e.detail));
            return out;
        },"ticks"_a=1);
}
