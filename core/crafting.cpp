#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace uw {
namespace {
constexpr std::int64_t kg=1000000000;
double distance(Point a,Point b){return std::hypot(a.x-b.x,a.y-b.y);}
std::int64_t sum(const std::map<std::string,std::int64_t>& m){std::int64_t n=0;for(const auto& [k,v]:m)n+=v;return n;}
const Recipe* recipe(const std::string& id){for(const auto& r:recipes())if(r.id==id)return &r;return nullptr;}
bool material(const std::string& k){return k=="plant_food"||k=="eggs"||k=="food"||k=="water"||k=="wood"||k=="fiber"||k=="stone"||k=="plank"||k=="wood_offcut"||k=="inert_material";}
}
const std::vector<Recipe>& recipes(){
    static const std::vector<Recipe> table={
        {"crude_axe","tool",{{"wood",450000000},{"fiber",50000000},{"stone",200000000}},{},4,false,0},
        {"planks","carried",{{"wood",kg}},{{"plank",800000000},{"wood_offcut",200000000}},3,true,0},
        {"storage_box","structure",{{"plank",800000000}},{},8,false,0},
        {"trough","structure",{{"plank",800000000}},{},8,false,0},
        {"fence","structure",{{"plank",400000000}},{},4,false,0},
        {"gate","structure",{{"plank",400000000}},{},4,false,0}
    };return table;
}
bool crafting_action(const std::string& t){return t=="craft"||t=="begin_construction"||t=="work_construction"||t=="cancel_construction"||t=="store_item"||t=="take_item"||t=="fill_trough"||t=="toggle_gate";}
std::int64_t World::carried_mass(const Entity& actor) const {
    auto n=sum(actor.inventory);for(const auto& e:entities_)if(e.kind=="tool"&&e.owner_id==actor.id)n+=e.mass_ug;return n;
}
bool World::clear_placement(Point p,double radius,const std::string& ignore) const {
    if(!std::isfinite(p.x)||!std::isfinite(p.y)||p.x<radius||p.y<radius||p.x>width_-radius||p.y>height_-radius)return false;
    for(const auto& e:entities_)if(e.id!=ignore&&!culture_.departed.contains(e.id)&&(e.radius>0||e.kind=="gate")&&distance(p,e.position)<radius+(e.kind=="gate"?.5:e.radius)-1e-12)return false;
    return true;
}
std::string World::validate_crafting_action(const Entity& actor,const Action& a) const {
    if(!bodies_)return "UNKNOWN_ACTION";
    if(a.evidence_seq)return "INVALID_ARGUMENT";
    if(a.type=="craft"||a.type=="begin_construction") {
        const auto r=recipe(a.text);
        if(!r)return "UNKNOWN_RECIPE";
        if(a.mass_ug||!a.material.empty()||!a.target_id.empty()||(a.type=="craft"&&(a.destination.x||a.destination.y)))return "INVALID_ARGUMENT";
        if((a.type=="begin_construction")!=(r->kind=="structure"))return "INVALID_ARGUMENT";
        if(actor.workmanship<r->skill)return "INSUFFICIENT_SKILL";
        if(a.duration_s<(a.type=="craft"?r->work_s:1))return "INSUFFICIENT_WORK";
        if(r->axe){auto tool=find(a.destination_id);if(!tool||tool->kind!="tool"||tool->owner_id!=actor.id||tool->recipe_id!="crude_axe"||!tool->durability)return "MISSING_TOOL";}
        else if(!a.destination_id.empty())return "INVALID_ARGUMENT";
        for(const auto& [k,v]:r->inputs){auto it=actor.inventory.find(k);if(it==actor.inventory.end()||it->second<v)return "INSUFFICIENT_RESOURCE";}
        if(a.type=="begin_construction") {
            if(distance(actor.position,a.destination)>1.5)return "OUT_OF_REACH";
            if(!unobstructed(actor.position,a.destination))return "TARGET_UNAVAILABLE";
            if(!clear_placement(a.destination,.5))return "NO_PLACEMENT";
        }
        if((r->kind=="tool"||r->kind=="structure")&&entities_.size()>=200)return "ENTITY_LIMIT";
        if(carried_mass(actor)>2*kg)return "CAPACITY_EXCEEDED";
        return "";
    }
    if(a.destination.x||a.destination.y||!a.destination_id.empty())return "INVALID_ARGUMENT";
    const auto target=find(a.target_id);
    if(!target||!visible(actor.id,target->id))return "TARGET_UNAVAILABLE";
    if(distance(actor.position,target->position)>1.5)return "OUT_OF_REACH";
    if(a.type=="work_construction"||a.type=="cancel_construction") {
        if(target->kind!="construction"||!recipe(target->recipe_id))return "TARGET_UNAVAILABLE";
        if(a.mass_ug||!a.text.empty()||!a.material.empty()||a.duration_s<1)return "INVALID_ARGUMENT";
        if(a.type=="cancel_construction") {
            if(target->owner_id!=actor.id)return "UNAUTHORIZED";
            if(carried_mass(actor)+target->mass_ug>2*kg)return "CAPACITY_EXCEEDED";
        }
        for(const auto& [id,p]:pending_)if(id!=actor.id&&p.remaining&&p.action.target_id==target->id&&(p.action.type=="work_construction"||p.action.type=="cancel_construction"))return "TARGET_BUSY";
        if(a.type=="work_construction"&&actor.workmanship<recipe(target->recipe_id)->skill)return "INSUFFICIENT_SKILL";
        return "";
    }
    if(a.type=="toggle_gate") {
        if(target->kind!="gate"||a.mass_ug||!a.text.empty()||!a.material.empty()||a.duration_s<1)return "INVALID_ARGUMENT";
        return target->radius==0&&!clear_placement(target->position,.5,target->id)?"NO_PLACEMENT":"";
    }
    if(a.type=="store_item"||a.type=="take_item"||a.type=="fill_trough") {
        if(!a.text.empty()||!material(a.material)||a.mass_ug<=0||a.mass_ug>2*kg||a.duration_s<1)return "INVALID_ARGUMENT";
        if(a.type=="fill_trough"?(target->kind!="trough"||a.material!="water"):target->kind!="storage_box")return "TARGET_UNAVAILABLE";
        const bool take=a.type=="take_item";
        const auto& source=take?target->inventory:actor.inventory;auto it=source.find(a.material);
        if(it==source.end()||it->second<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        if(take?carried_mass(actor)+a.mass_ug>2*kg:sum(target->inventory)+a.mass_ug>4*kg)return "CAPACITY_EXCEEDED";
        return "";
    }
    return "UNKNOWN_ACTION";
}
void World::use_axe(Entity& actor,const std::string& id,const std::string& request_id) {
    auto tool=find(id);if(!tool||!tool->durability)return;
    --tool->durability;
    event("tool_wear",actor.id,request_id,id+":"+std::to_string(tool->durability));
    if(!tool->durability) {
        for(const auto& [k,v]:tool->composition)actor.inventory[k]+=v;
        tool->mass_ug=0;tool->composition.clear();tool->kind="spent_tool";tool->owner_id.clear();
        event("tool_breakage",actor.id,request_id,id+":original_constituents_returned_as_scrap");
    }
}
void World::work_construction(Entity& actor,const Action& a) {
    auto site=find(a.target_id);if(!site)return;
    site->work_s=std::min(recipe(site->recipe_id)->work_s,site->work_s+dt_);
    if(site->work_s+1e-9>=recipe(site->recipe_id)->work_s)pending_.at(actor.id).remaining=1;
}
void World::complete_crafting_action(Entity& actor,const Action& a) {
    const auto id=actor.id;
    auto& receipt=requests_.at(id+":"+a.request_id).second;
    const auto error=validate_crafting_action(actor,a);
    if(!error.empty()){finish(id,false,error);return;}
    if(!actor.body.alive){finish(id,false,"DEAD");return;}
    if(a.type=="craft"||a.type=="begin_construction") {
        const auto r=recipe(a.text);
        for(const auto& [k,v]:r->inputs)actor.inventory[k]-=v;
        if(r->axe)use_axe(actor,a.destination_id,a.request_id);
        if(r->kind=="carried")for(const auto& [k,v]:r->outputs)actor.inventory[k]+=v;
        const auto product_id="crafted-"+std::to_string(next_id_++);
        if(r->kind=="carried"){++actor.workmanship;receipt.effect="recipe="+r->id+":carried_outputs_and_waste";}
        else {
            Entity product;product.id=product_id;product.kind=r->kind=="tool"?"tool":"construction";
            product.position=r->kind=="tool"?actor.position:a.destination;product.radius=r->kind=="tool"?0:.5;
            product.mass_ug=sum(r->inputs);product.composition=r->inputs;product.recipe_id=r->id;product.owner_id=id;
            if(r->kind=="tool"){product.durability=8;++actor.workmanship;}
            receipt.effect="recipe="+r->id+":entity="+product_id;
            entities_.push_back(product);rebuild_grid();
        }
    } else {
        auto target=find(a.target_id);
        if(a.type=="work_construction") {
            const auto r=recipe(target->recipe_id);
            receipt.effect="site="+target->id+":work_s="+std::to_string(target->work_s);
            if(target->work_s+1e-9>=r->work_s){target->kind=r->id;++actor.workmanship;receipt.effect+=":built="+r->id;}
        } else if(a.type=="cancel_construction") {
            for(const auto& [k,v]:target->composition)actor.inventory[k]+=v;
            target->mass_ug=0;target->composition.clear();target->kind="cancelled_site";target->radius=0;
            receipt.effect="returned_site_material:"+target->id;rebuild_grid();
        } else if(a.type=="toggle_gate") {
            target->radius=target->radius==0?.5:0;receipt.effect=target->radius?"gate_closed":"gate_open";rebuild_grid();
        } else {
            auto& source=a.type=="take_item"?target->inventory:actor.inventory;
            auto& dest=a.type=="take_item"?actor.inventory:target->inventory;
            source[a.material]-=a.mass_ug;dest[a.material]+=a.mass_ug;
            transfer_freshness(a.type=="take_item"?target->id:actor.id,a.type=="take_item"?actor.id:target->id,a.material);
            receipt.effect=a.material+":"+std::to_string(a.mass_ug)+"ug:"+a.type;
        }
    }
    event("crafting_effect",id,a.request_id,receipt.effect);receipt.event_refs.push_back(seq_);finish(id,true,"");
}
}
