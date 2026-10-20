#include "world.hpp"
#include <cmath>
#include <stdexcept>

namespace uw {
namespace {
unsigned cell_index(const std::string& id) {return static_cast<unsigned>(id.back()-'1');}
}
void World::configure_thermal(bool open,double water,double fuel,double oxygen,double temperature) {
    if(tick_||seq_||thermal_.enabled||!bodies_||width_<12||height_<12)
        throw std::invalid_argument("thermal initialization requires a fresh body-enabled world >=12m");
    ThermalModel model;model.initialize(open,water,fuel,oxygen,temperature);
    const auto masses=model.masses();
    auto water_pile=find("resource-2"),inert=find("resource-3");
    if(water_pile->mass_ug<masses.at("water")||inert->mass_ug<masses.at("inert_material"))
        throw std::invalid_argument("insufficient initial thermal feedstock");
    water_pile->mass_ug-=masses.at("water");inert->mass_ug-=masses.at("inert_material");
    for(unsigned i=0;i<4;++i)entities_.push_back({"thermal-"+std::to_string(i+1),"thermal_cell",{2.+2*(i%2),4.+2*(i/2)},0,100000000,{}});
    initial_mass_["fuel_X"]=masses.at("fuel_X");initial_mass_["oxygen"]=masses.at("oxygen");
    thermal_=model;rebuild_grid();check_invariants();
}
std::string World::validate_thermal_action(const Entity& actor,const Action& a) const {
    if(!thermal_.enabled)return "UNKNOWN_ACTION";
    if(a.duration_s<1||a.evidence_seq||a.destination.x!=0||a.destination.y!=0)return "INVALID_ARGUMENT";
    auto source=find(a.target_id);
    if(!source||source->kind!="thermal_cell"||!visible(actor.id,source->id))return "TARGET_UNAVAILABLE";
    auto reachable=[&](const Entity& target){return std::hypot(actor.position.x-target.position.x,actor.position.y-target.position.y)<=1.5;};
    if(!reachable(*source))return "OUT_OF_REACH";
    if(a.type=="operate_heat")return a.mass_ug==0&&a.destination_id.empty()&&a.material.empty()&&
        (a.text=="off"||a.text=="electric"||a.text=="burn")?"":"INVALID_ARGUMENT";
    if(a.type!="move_material"||!a.text.empty()||a.mass_ug<=0||a.mass_ug>1000000000LL)return "INVALID_ARGUMENT";
    auto destination=find(a.destination_id);
    if(!destination||destination==source||destination->kind!="thermal_cell"||!visible(actor.id,destination->id))return "TARGET_UNAVAILABLE";
    if(!reachable(*destination))return "OUT_OF_REACH";
    auto amount=thermal_.available(cell_index(source->id),a.material);
    if(amount<0)return "INVALID_ARGUMENT";
    return amount<a.mass_ug?"INSUFFICIENT_RESOURCE":"";
}
bool World::complete_thermal_action(Entity& actor,const Action& a) {
    auto error=validate_thermal_action(actor,a);
    if(!error.empty()){finish(actor.id,false,error);return false;}
    auto& receipt=requests_.at(actor.id+":"+a.request_id).second;
    if(a.type=="operate_heat") {
        thermal_.cells[cell_index(a.target_id)].heater=a.text;
        receipt.effect=a.target_id+":heater="+a.text;
        event("heat_control",actor.id,a.request_id,receipt.effect);
    } else {
        thermal_.transfer(cell_index(a.target_id),cell_index(a.destination_id),a.material,a.mass_ug);
        receipt.effect=a.target_id+"->"+a.destination_id+":"+a.material+":"+std::to_string(a.mass_ug)+"ug";
        event("thermal_material_transfer",actor.id,a.request_id,receipt.effect);
    }
    receipt.event_refs.push_back(seq_);finish(actor.id,true,"");return true;
}
}
