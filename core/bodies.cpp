#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <sstream>

namespace uw {
namespace {
constexpr std::int64_t kg=1000000000;
constexpr double pile_radius=.15;
constexpr std::int64_t inventory_capacity=2*kg;
double separation(Point a,Point b){return std::hypot(a.x-b.x,a.y-b.y);}
bool pile_kind(const std::string& kind) {
    return kind=="wood"||kind=="fiber"||kind=="wood_offcut"||kind=="stone";
}
}
bool World::unobstructed(Point a,Point b,const std::string& target) const {
    const double dx=b.x-a.x,dy=b.y-a.y,len=dx*dx+dy*dy;
    for(const auto&e:entities_) if((e.kind=="rock"||e.kind=="object"||e.kind=="tree")&&e.id!=target) {
        const double t=len==0?0:std::clamp(((e.position.x-a.x)*dx+(e.position.y-a.y)*dy)/len,0.0,1.0);
        if(separation({a.x+t*dx,a.y+t*dy},e.position)<e.radius) return false;
    }
    return true;
}
bool World::visible(const std::string& observer,const std::string& target,double range) const {
    auto a=find(observer),b=find(target);
    return a&&b&&!culture_.departed.contains(observer)&&!culture_.departed.contains(target)&&a->kind=="actor"&&(!bodies_||a->body.alive)&&
        separation(a->position,b->position)<=range&&(!bodies_||unobstructed(a->position,b->position,target));
}
std::string World::validate_body_action(const Entity& actor,const Action& a) const {
    if(a.type=="inspect_tree"||a.type=="harvest_branch"||a.type=="fell_tree"||a.type=="collect_wood")
        return validate_tree_action(actor,a);
    if(!bodies_)return "UNKNOWN_ACTION";
    if(a.type=="operate_heat"||a.type=="move_material")return validate_thermal_action(actor,a);
    if(a.type=="give"||a.type=="offer_task"||a.type=="respond_task"||a.type=="process_batch"||a.type=="write_book"||a.type=="depart")return validate_culture_action(actor,a);
    if(a.type=="eat"||a.type=="drink") {
        const auto kind=a.type=="eat"?"food":"water";
        if(!a.target_id.empty()||a.mass_ug<=0||a.mass_ug>kg||a.destination.x!=0||a.destination.y!=0||!a.text.empty())return "INVALID_ARGUMENT";
        if(a.duration_s<(a.type=="eat"?2.0:1.0))return "INVALID_ARGUMENT";
        auto it=actor.inventory.find(kind);
        return it==actor.inventory.end()||it->second<a.mass_ug?"INSUFFICIENT_RESOURCE":"";
    }
    if(a.mass_ug!=0||a.destination.x!=0||a.destination.y!=0)return "INVALID_ARGUMENT";
    if(a.type=="rest")return a.target_id.empty()&&a.text.empty()&&a.duration_s>=1?"":"INVALID_ARGUMENT";
    if(a.type=="speak") {
        if(!a.target_id.empty()||a.text.empty()||a.text.size()>512||a.duration_s<1)return "INVALID_ARGUMENT";
        return a.evidence_seq!=0&&!known_report(actor.id,a.evidence_seq)?"PROVENANCE_UNAVAILABLE":"";
    }
    if(a.type=="read") {
        auto target=find(a.target_id);
        if(!a.text.empty()||a.duration_s<1)return "INVALID_ARGUMENT";
        if(!target||target->kind!="book"||!visible(actor.id,a.target_id))return "TARGET_UNAVAILABLE";
        return separation(actor.position,target->position)<=1.5?"":"OUT_OF_REACH";
    }
    if(a.type=="inspect") {
        if(!a.text.empty()||a.duration_s<.2)return "INVALID_ARGUMENT";
        auto target=find(a.target_id);
        if(target&&target->kind=="thermal_cell"&&separation(actor.position,target->position)>1.5)return "OUT_OF_REACH";
        return visible(actor.id,a.target_id)?"":"TARGET_UNAVAILABLE";
    }
    return "UNKNOWN_ACTION";
}
std::string World::validate_tree_action(const Entity& actor,const Action& a) const {
    auto target=find(a.target_id);
    const bool inspect=a.type=="inspect_tree";
    const bool harvest=a.type=="harvest_branch";
    const bool fell=a.type=="fell_tree";
    const bool collect=a.type=="collect_wood";
    if(!inspect&&!harvest&&!fell&&!collect)return "UNKNOWN_ACTION";
    if(!target||!visible(actor.id,a.target_id))return "TARGET_UNAVAILABLE";
    if(inspect) {
        if(target->kind!="tree")return "TARGET_UNAVAILABLE";
        if(!a.text.empty()||a.mass_ug!=0||a.destination.x!=0||a.destination.y!=0||!a.destination_id.empty()||!a.material.empty()||a.duration_s<.2)
            return "INVALID_ARGUMENT";
        return "";
    }
    if(collect) {
        if(!pile_kind(target->kind)||target->radius!=pile_radius||!a.text.empty()||a.mass_ug<=0||a.mass_ug>10*kg||
           a.destination.x!=0||a.destination.y!=0||!a.destination_id.empty()||a.material!=target->kind||separation(actor.position,target->position)>1.5)
            return "INVALID_ARGUMENT";
        if(target->mass_ug<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        std::int64_t held=0;for(const auto& [kind,mass]:actor.inventory)held+=mass;
        return held>inventory_capacity-a.mass_ug?"CAPACITY_EXCEEDED":"";
    }
    if(target->kind!="tree")return "TARGET_UNAVAILABLE";
    if(!a.text.empty()||a.mass_ug<0||a.destination_id.size()!=0||!a.material.empty()||separation(actor.position,target->position)>1.5)
        return "INVALID_ARGUMENT";
    if(target->stage=="stump"||target->biomass_ug==0||target->mass_ug==0)return "TREE_DEPLETED";
    if(harvest) {
        if(a.mass_ug<=0||a.duration_s<1)return "INVALID_ARGUMENT";
        return a.mass_ug>target->biomass_ug?"INSUFFICIENT_RESOURCE":"";
    }
    if(fell) return a.mass_ug==0&&a.duration_s>=5?"":"INVALID_ARGUMENT";
    return "UNKNOWN_ACTION";
}
void World::complete_body_action(Entity& actor,const Action& a) {
    if(a.type=="inspect_tree"||a.type=="harvest_branch"||a.type=="fell_tree"||a.type=="collect_wood") {
        complete_tree_action(actor,a);return;
    }
    auto& receipt=requests_.at(actor.id+":"+a.request_id).second;
    if(a.type=="operate_heat"||a.type=="move_material") {complete_thermal_action(actor,a);return;}
    if(a.type=="give"||a.type=="offer_task"||a.type=="respond_task"||a.type=="process_batch"||a.type=="write_book"||a.type=="depart") {complete_culture_action(actor,a);return;}
    if(a.type=="eat"||a.type=="drink") {
        const auto kind=a.type=="eat"?"food":"water";
        auto it=actor.inventory.find(kind);
        if(it==actor.inventory.end()||it->second<a.mass_ug) {finish(actor.id,false,"INSUFFICIENT_RESOURCE");return;}
        it->second-=a.mass_ug;
        auto& ingested=a.type=="eat"?actor.body.food_ingested_ug:actor.body.water_ingested_ug;
        auto& need=a.type=="eat"?actor.body.hunger:actor.body.thirst;
        ingested+=a.mass_ug;
        need=std::max(0.0,need-2*static_cast<double>(a.mass_ug)/kg);
        event("consumption",actor.id,a.request_id,a.type+":"+std::to_string(a.mass_ug)+"ug");
        receipt.event_refs.push_back(seq_);
        receipt.effect="ingested_ug="+std::to_string(a.mass_ug);
    } else if(a.type=="inspect") {
        auto error=validate_body_action(actor,a);
        if(!error.empty()) {finish(actor.id,false,error);return;}
        auto target=find(a.target_id);
        // Only public resource measurements; no other actor's body or inventory.
        receipt.effect=target->id+":"+target->kind;
        if(target->kind=="thermal_cell") {
            const auto index=static_cast<unsigned>(target->id.back()-'1');const auto& c=thermal_.cells.at(index);
            auto masses=c.phase_masses();
            receipt.effect+=":temperature~"+std::to_string(static_cast<int>(std::round(c.phase().temperature/5)*5))+"K";
            for(unsigned i=0;i<3;++i)receipt.effect+=std::string(":")+std::array{"ice","liquid","vapor"}[i]+"~"+std::to_string(static_cast<int>(std::round(masses[i]/5000000.))*5)+"g";
            receipt.effect+=":heater="+c.heater;
            if(culture_.enabled&&index==0){receipt.effect+=":conditioning dials=";for(const auto& dial:culture_.dials)receipt.effect+=dial+",";receipt.effect+=":authored task: hold >=5g liquid with heater off, then validate";}
        } else if(target->radius==0)receipt.effect+=":mass_ug="+std::to_string(target->mass_ug);
        event("inspection",actor.id,a.request_id,receipt.effect);
        receipt.event_refs.push_back(seq_);
    } else if(a.type=="read") {
        if(!validate_body_action(actor,a).empty()) {finish(actor.id,false,"OUT_OF_REACH");return;}
        const auto& book=books_.at(a.target_id);
        event("book_read",actor.id,a.request_id,a.target_id);
        receipt.event_refs.push_back(seq_);
        auto& queue=readings_[actor.id];
        queue.push_back({seq_,tick_,book.author,book.text,book.origin_seq,book.parent_seq,a.target_id});
        if(culture_.enabled&&book.author!="book-author"&&book.author!=actor.id)interaction(actor.id,book.author,"read_artifact");
        if(queue.size()>16)queue.erase(queue.begin());
        receipt.effect="read:"+a.target_id;
    } else if(a.type=="speak") {
        const auto* source=a.evidence_seq?known_report(actor.id,a.evidence_seq):nullptr;
        if(a.evidence_seq&&!source) {finish(actor.id,false,"PROVENANCE_UNAVAILABLE");return;}
        // Copy before queue mutations, which may invalidate a source pointer.
        const U64 origin=source?source->origin_seq:seq_+1,parent=source?source->seq:0;
        const std::string source_id=source?source->source_id:actor.id;
        event("speech",actor.id,a.request_id,a.text);
        receipt.event_refs.push_back(seq_);
        for(const auto& other:entities_) if(other.kind=="actor"&&other.id!=actor.id&&other.body.alive&&!culture_.departed.contains(other.id)&&
            separation(actor.position,other.position)<=hearing_range_&&unobstructed(actor.position,other.position)) {
            auto& queue=messages_[other.id];
            queue.push_back({seq_,tick_,actor.id,a.text,origin,parent,source_id});
            if(queue.size()>16)queue.erase(queue.begin());
        }
        receipt.effect="spoken_locally";
    } else if(a.type=="rest")receipt.effect="rested";
    finish(actor.id,true,"");
}
void World::complete_tree_action(Entity& actor,const Action& a) {
    const std::string actor_id=actor.id;
    auto& receipt=requests_.at(actor_id+":"+a.request_id).second;
    auto fail=[&](const std::string& error){finish(actor_id,false,error);};
    if(bodies_&&!actor.body.alive){fail("DEAD");return;}
    auto target=find(a.target_id);
    auto error=validate_tree_action(actor,a);
    if(!target||!error.empty()){fail(error.empty()?"TARGET_UNAVAILABLE":error);return;}
    if(a.type=="inspect_tree") {
        std::ostringstream description;description<<target->id<<":stage="<<target->stage<<":health="<<target->health
            <<":biomass_ug="<<target->biomass_ug<<":radius_m="<<target->radius;
        receipt.effect=description.str();event("inspection",actor_id,a.request_id,receipt.effect);receipt.event_refs.push_back(seq_);
        finish(actor_id,true,"");return;
    }
    if(a.type=="collect_wood") {
        const auto amount=a.mass_ug;
        if(target->mass_ug<amount){fail("INSUFFICIENT_RESOURCE");return;}
        std::int64_t held=0;for(const auto& [kind,mass]:actor.inventory)held+=mass;
        if(held>inventory_capacity-amount){fail("CAPACITY_EXCEEDED");return;}
        target->mass_ug-=amount;actor.inventory[target->kind]+=amount;
        event("mass_transfer",actor_id,a.request_id,"collect_wood:"+target->kind+":"+std::to_string(amount)+"ug");
        receipt.event_refs.push_back(seq_);receipt.effect="collected:"+target->kind+":"+std::to_string(amount)+"ug";
        finish(actor_id,true,"");return;
    }

    target=find(a.target_id);
    if(!target||target->kind!="tree"||target->stage=="stump"||target->biomass_ug==0||target->mass_ug==0) {
        fail("TREE_DEPLETED");return;
    }
    const std::int64_t original=target->biomass_ug;
    std::int64_t wood=0,fiber=0,removed=0,stump=0;
    if(a.type=="harvest_branch") {
        if(a.mass_ug<=0||a.mass_ug>target->biomass_ug){fail("INSUFFICIENT_RESOURCE");return;}
        removed=a.mass_ug;wood=removed*9/10;fiber=removed-wood;stump=target->biomass_ug-removed;
    } else {
        // Authored bootstrap rule: felling is a slow no-tool action. Native
        // validation remains authoritative, so bindings cannot bypass reach,
        // stage, biomass, placement, or the five-second minimum.
        if(a.duration_s<5){fail("INVALID_ARGUMENT");return;}
        wood=target->biomass_ug*8/10;fiber=target->biomass_ug/10;removed=wood+fiber;stump=target->biomass_ug-removed;
    }

    const Point anchor=a.destination.x==0&&a.destination.y==0?Point{}:a.destination;
    std::vector<std::pair<std::string,std::int64_t>> products;
    if(wood>0)products.emplace_back("wood",wood);
    if(fiber>0)products.emplace_back("fiber",fiber);
    std::vector<Point> positions;
    auto clear_for_pile=[&](Point p) {
        if(!std::isfinite(p.x)||!std::isfinite(p.y)||p.x<pile_radius||p.y<pile_radius||p.x>width_-pile_radius||p.y>height_-pile_radius)return false;
        for(const auto& e:entities_)if(!culture_.departed.contains(e.id)&&e.radius>0&&separation(p,e.position)<pile_radius+e.radius-1e-12)return false;
        for(const auto& q:positions)if(separation(p,q)<2*pile_radius-1e-12)return false;
        return true;
    };
    auto choose_position=[&](Point wanted,Point base,Point& result) {
        std::vector<Point> candidates;
        if(positions.empty()&&(wanted.x!=0||wanted.y!=0)) {
            // A caller-supplied placement is an explicit occupied-geometry
            // claim; reject it rather than silently relocating the pile.
            if(!clear_for_pile(wanted))return false;
            candidates.push_back(wanted);
        }
        const double offsets[][2]={{1.2,0},{-1.2,0},{0,1.2},{0,-1.2},{.9,.9},{-.9,.9},{.9,-.9},{-.9,-.9},{1.8,0},{0,1.8}};
        for(const auto& offset:offsets)candidates.push_back({base.x+offset[0],base.y+offset[1]});
        for(const auto& candidate:candidates)if(clear_for_pile(candidate)){result=candidate;return true;}
        return false;
    };
    for(std::size_t i=0;i<products.size();++i) {
        Point placement{};
        if(!choose_position(anchor,target->position,placement)){fail("NO_PLACEMENT");return;}
        positions.push_back(placement);
    }
    if(removed>target->biomass_ug){fail("INSUFFICIENT_RESOURCE");return;}
    target->mass_ug-=removed;target->biomass_ug=target->mass_ug;
    target->health=std::max(0.0,target->health-.1*static_cast<double>(removed)/std::max<std::int64_t>(original,1));
    if(a.type=="fell_tree"||target->mass_ug==0||stump==0) {target->stage="stump";target->health=target->mass_ug==0?0:.1;}
    for(std::size_t i=0;i<products.size();++i) {
        const auto& [kind,mass]=products[i];
        entities_.push_back({"pile-"+std::to_string(next_id_++),kind,positions[i],pile_radius,mass,{},{},"none",1,0});
    }
    rebuild_grid();
    event("mass_transfer",actor_id,a.request_id,a.type+":wood="+std::to_string(wood)+":fiber="+std::to_string(fiber));
    receipt.event_refs.push_back(seq_);receipt.effect="wood_ug="+std::to_string(wood)+":fiber_ug="+std::to_string(fiber);
    finish(actor_id,true,"");
}
void World::update_bodies() {
    if(!bodies_)return;
    for(auto& e:entities_)if(e.kind=="actor"&&e.body.alive&&!culture_.departed.contains(e.id)) {
        auto& b=e.body;
        auto pending=pending_.find(e.id);
        const bool resting=pending!=pending_.end()&&pending->second.action.type=="rest";
        const bool moving=pending!=pending_.end()&&pending->second.action.type=="move";
        b.hunger=std::min(1.0,b.hunger+.001*dt_);
        b.thirst=std::min(1.0,b.thirst+.0015*dt_);
        b.fatigue=std::clamp(b.fatigue+(resting?-.015:(moving?.0012:.0008))*dt_,0.0,1.0);
        const double stress=(b.hunger>=.95?1.0:0)+(b.thirst>=.95?1.0:0)+(b.fatigue>=.99?.5:0);
        if(stress>0)b.health=std::max(0.0,b.health-.006*stress*dt_);
        else if(std::max({b.hunger,b.thirst,b.fatigue})<.75)b.health=std::min(1.0,b.health+.0005*dt_);
        if(b.health==0) {
            b.alive=false;
            if(pending!=pending_.end()&&pending->second.remaining>0) {
                finish(e.id,false,"DEAD");pending->second.remaining=0;
            }
            event("death",e.id,"","abstract_needs_failure");
        }
    }
}
void World::replenish() {
    for(const auto& kind:{std::string("food"),std::string("water")}) {
        const double rate=kind=="food"?food_regen_:water_regen_;
        auto& remainder=kind=="food"?food_remainder_:water_remainder_;
        remainder+=rate*dt_*kg;
        const auto mass=static_cast<std::int64_t>(std::floor(remainder));
        remainder-=static_cast<double>(mass);
        if(mass>0) {
            find(kind=="food"?"resource-1":"resource-2")->mass_ug+=mass;
            source_mass_[kind]+=mass;
            // The explicit boundary ledger reconciles the source; no magic crafting.
        }
    }
}
void World::grow_trees() {
    if(tree_growth_kg_s_==0)return;
    for(auto& tree:entities_) {
        if(tree.kind!="tree"||tree.stage!="young")continue;
        tree_growth_remainder_ug_+=tree_growth_kg_s_*dt_*kg;
        const auto amount=static_cast<std::int64_t>(std::floor(tree_growth_remainder_ug_));
        tree_growth_remainder_ug_-=static_cast<double>(amount);
        if(amount<=0)continue;
        if(tree.mass_ug>std::numeric_limits<std::int64_t>::max()-amount)throw std::invalid_argument("tree biomass overflow");
        tree.mass_ug+=amount;tree.biomass_ug=tree.mass_ug;source_mass_.at("tree")+=amount;
        if(tree.mass_ug>=8*kg)tree.stage="mature";
    }
}
}
