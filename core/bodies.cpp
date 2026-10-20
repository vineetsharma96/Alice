#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <sstream>

namespace uw {
namespace {
constexpr std::int64_t kg=1000000000;
double separation(Point a,Point b){return std::hypot(a.x-b.x,a.y-b.y);}
}
bool World::unobstructed(Point a,Point b,const std::string& target) const {
    const double dx=b.x-a.x,dy=b.y-a.y,len=dx*dx+dy*dy;
    for(const auto&e:entities_) if((e.kind=="rock"||e.kind=="object")&&e.id!=target) {
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
void World::complete_body_action(Entity& actor,const Action& a) {
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
}
