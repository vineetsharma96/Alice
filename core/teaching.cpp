#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace uw {
namespace {
bool identifier(const std::string& s) {
    return !s.empty()&&s.size()<=64&&std::all_of(s.begin(),s.end(),[](unsigned char c){
        return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-';
    });
}
}
const Message* World::known_report(const std::string& agent,U64 seq) const {
    for(const auto* store:{&readings_,&messages_}) {
        auto it=store->find(agent);
        if(it!=store->end())for(const auto& report:it->second)if(report.seq==seq)return &report;
    }
    return nullptr;
}
void World::configure_branch(bool guided,double hearing_range) {
    if(!std::isfinite(hearing_range)||hearing_range<1||hearing_range>12)
        throw std::invalid_argument("invalid hearing law");
    guided_=guided;hearing_range_=hearing_range;
}
U64 World::intervene(const std::string& id,const std::string& type,const std::string& entity_id,
                     Point position,const std::string& material,std::int64_t mass,double energy,const std::string& text) {
    if(!guided_)throw std::invalid_argument("CLOSED_MODE: operator interventions forbidden");
    if(!identifier(id)||!std::isfinite(position.x)||!std::isfinite(position.y)||!std::isfinite(energy)||
       energy<0||energy>1e9||mass<0||mass>1000LL*1000000000||text.size()>1024)
        throw std::invalid_argument("invalid intervention fields");
    std::ostringstream signature;signature<<std::setprecision(17)<<std::quoted(type)<<std::quoted(entity_id)
        <<position.x<<' '<<position.y<<' '<<std::quoted(material)<<mass<<' '<<energy<<std::quoted(text);
    if(auto old=interventions_.find(id);old!=interventions_.end()) {
        if(old->second.first!=signature.str())throw std::invalid_argument("conflicting intervention id");
        return old->second.second;
    }
    if(interventions_.size()>=256)throw std::invalid_argument("intervention quota reached");
    const bool book=type=="place_book",object=type=="introduce_object",avatar=type=="avatar_message",broadcast=type=="broadcast";
    if(!book&&!object&&!avatar&&!broadcast)throw std::invalid_argument("unknown intervention");
    const auto actors=std::count_if(entities_.begin(),entities_.end(),[](const auto&e){return e.kind=="actor"||e.kind=="operator_avatar"||e.kind=="thermal_cell";});
    if((book||object)&&(!identifier(entity_id)||entity_id=="operator-avatar"||find(entity_id)||entities_.size()-actors-4>=128||entities_.size()>=200||mass==0))
        throw std::invalid_argument("invalid/new entity id or entity quota");
    if((book||object)&&material!="food"&&material!="water"&&material!="inert_material")throw std::invalid_argument("invalid material");
    if(book&&material!="inert_material")throw std::invalid_argument("books require inert material");
    if((book||avatar||broadcast)&&text.empty())throw std::invalid_argument("empty teaching text");
    if(object&&!text.empty())throw std::invalid_argument("ordinary objects have no text");
    if((avatar||broadcast)&&(mass!=0||energy!=0||!material.empty()||!entity_id.empty()))throw std::invalid_argument("messages cannot create resources");
    if(broadcast&&(position.x!=0||position.y!=0))throw std::invalid_argument("broadcast has no position");
    const double radius=avatar?.25:(object&&material=="inert_material"?.5:0);
    if(!broadcast) {
        if(position.x<radius||position.y<radius||position.x>width_-radius||position.y>height_-radius)
            throw std::invalid_argument("intervention out of bounds");
        if(radius>0)for(const auto& e:entities_)if(!culture_.departed.contains(e.id)&&!(avatar&&e.id=="operator-avatar")&&e.radius>0&&
            std::hypot(e.position.x-position.x,e.position.y-position.y)<e.radius+radius)
                throw std::invalid_argument("intervention collision");
    }
    if(avatar&&!find("operator-avatar")&&entities_.size()>=200)throw std::invalid_argument("entity quota reached");
    // Every validation precedes mutation. The coordinator commits this source and its event atomically.
    event("operator_"+type,"operator-avatar",id,book||object?entity_id:"explicit operator communication");
    const U64 origin=seq_;
    if(book||object) {
        const std::string kind=book?"book":(material=="inert_material"?"object":material);
        entities_.push_back({entity_id,kind,position,radius,mass,{}});
        source_mass_[material]+=mass;operator_mass_[material]+=mass;
        energy_j_+=energy;operator_energy_j_+=energy;
        if(book)books_[entity_id]={origin,text};
    } else {
        if(avatar) {
            auto e=find("operator-avatar");
            if(e)e->position=position;
            else entities_.push_back({"operator-avatar","operator_avatar",position,.25,0,{}});
        }
        for(const auto& e:entities_)if(e.kind=="actor"&&e.body.alive&&!culture_.departed.contains(e.id)&&
            (broadcast||(std::hypot(e.position.x-position.x,e.position.y-position.y)<=hearing_range_&&unobstructed(position,e.position)))) {
            auto& queue=messages_[e.id];
            queue.push_back({origin,tick_,"operator-avatar",text,origin,0,"operator:"+id});
            if(queue.size()>16)queue.erase(queue.begin());
        }
    }
    interventions_[id]={signature.str(),origin};rebuild_grid();check_invariants();return origin;
}
}
