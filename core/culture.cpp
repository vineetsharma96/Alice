#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace uw {
namespace {
constexpr std::int64_t kg=1000000000;
bool social_action(const std::string& t){return t=="give"||t=="offer_task"||t=="respond_task";}
std::vector<std::string> labels(U64 seed,double& target,unsigned& correct) {
    std::mt19937_64 random(seed);target=310+15*(random()%4);correct=static_cast<unsigned>(random()%4);
    std::vector<std::string> out;
    for(unsigned i=0;i<4;++i){std::ostringstream s;s<<"dial-"<<i<<'-'<<std::hex<<(random()&0xffffffff);out.push_back(s.str());}
    return out;
}
}
void World::configure_culture(U64 seed) {
    if(tick_||seq_||culture_.enabled||!thermal_.enabled||!bodies_)throw std::invalid_argument("culture requires a fresh thermal world");
    culture_.enabled=true;culture_.apparatus_seed=seed;
    culture_.dials=labels(seed,culture_.target_k,culture_.correct_dial);check_invariants();
}
double World::practice_seconds(const std::string& agent) const {
    auto p=culture_.practice.find(agent);return 4./(1+.25*(p==culture_.practice.end()?0:p->second.successes));
}
bool World::known_experience(const std::string& agent,U64 seq) const {
    return std::any_of(culture_.batches.begin(),culture_.batches.end(),[&](const auto& b){return b.agent==agent&&b.seq==seq;});
}
std::string World::validate_culture_action(const Entity& actor,const Action& a) const {
    if(!culture_.enabled)return "UNKNOWN_ACTION";
    if(a.destination.x||a.destination.y||!a.destination_id.empty())return "INVALID_ARGUMENT";
    if(a.type!="give"&&(a.mass_ug||!a.material.empty()))return "INVALID_ARGUMENT";
    if(a.type!="write_book"&&a.evidence_seq)return "INVALID_ARGUMENT";
    if(a.type=="depart")return a.target_id.empty()&&a.text.empty()&&a.duration_s>=1?"":"INVALID_ARGUMENT";
    if(a.type=="write_book") {
        if(!a.target_id.empty()||a.text.empty()||a.text.size()>512||a.duration_s<5)return "INVALID_ARGUMENT";
        if(!a.evidence_seq||(!known_experience(actor.id,a.evidence_seq)&&!known_report(actor.id,a.evidence_seq)))return "PROVENANCE_UNAVAILABLE";
        auto stock=actor.inventory.find("inert_material");
        if(stock==actor.inventory.end()||stock->second<10000000)return "INSUFFICIENT_RESOURCE";
        unsigned introduced=0;for(const auto& e:entities_)if(e.kind=="book"||e.kind=="object"||(e.kind=="food"&&e.id!="resource-1")||(e.kind=="water"&&e.id!="resource-2"))++introduced;
        return introduced>=128||entities_.size()>=200||find("artifact-"+std::to_string(seq_+1))?"ARTIFACT_LIMIT":"";
    }
    if(a.type=="process_batch") {
        if(a.target_id!="thermal-1"||std::find(culture_.dials.begin(),culture_.dials.end(),a.text)==culture_.dials.end()||a.duration_s+1e-10<practice_seconds(actor.id))return "INVALID_ARGUMENT";
        if(culture_.batches.size()>=256)return "BATCH_LIMIT";
        if(!visible(actor.id,a.target_id))return "TARGET_UNAVAILABLE";
        const auto p=find(a.target_id)->position;
        return std::hypot(actor.position.x-p.x,actor.position.y-p.y)<=1.5?"":"OUT_OF_REACH";
    }
    if(!social_action(a.type)||a.duration_s<1)return "INVALID_ARGUMENT";
    const Entity* peer=nullptr;
    if(a.type=="respond_task") {
        auto agreement=culture_.agreements.find(a.target_id);
        if(agreement==culture_.agreements.end()||agreement->second.partner!=actor.id||agreement->second.status!="offered"||tick_>=agreement->second.expires_tick)return "AGREEMENT_UNAVAILABLE";
        if(a.text!="accept"&&a.text!="decline")return "INVALID_ARGUMENT";
        peer=find(agreement->second.proposer);
    } else peer=find(a.target_id);
    if(!peer||peer->kind!="actor"||peer->id==actor.id||!peer->body.alive||!visible(actor.id,peer->id))return "TARGET_UNAVAILABLE";
    const double reach=a.type=="give"?1.5:hearing_range_;
    if(std::hypot(actor.position.x-peer->position.x,actor.position.y-peer->position.y)>reach)return "OUT_OF_REACH";
    if(a.type=="give") {
        if(!a.text.empty()||a.mass_ug<=0||a.mass_ug>kg||(a.material!="food"&&a.material!="water"&&a.material!="inert_material"))return "INVALID_ARGUMENT";
        auto stock=actor.inventory.find(a.material);
        if(stock==actor.inventory.end()||stock->second<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        const auto held=carried_mass(*peer);
        return held+a.mass_ug>2*kg?"CAPACITY_EXCEEDED":"";
    }
    if(a.type=="offer_task"&&(a.text.empty()||a.text.size()>160||culture_.agreements.size()>=64||culture_.agreements.contains(a.request_id)))return "INVALID_ARGUMENT";
    return "";
}
bool World::process_conditions(const std::string& agent,const Action& a) const {
    if(!culture_.enabled||!visible(agent,"thermal-1"))return false;
    const auto& c=thermal_.cells[0];
    return a.text==culture_.dials[culture_.correct_dial]&&c.heater=="off"&&c.phase_masses()[1]>=5000000&&std::abs(c.phase().temperature-culture_.target_k)<=7.5;
}
void World::interaction(const std::string& a,const std::string& b,const std::string& kind) {
    auto add=[&](const std::string& owner,const std::string& other){auto& q=culture_.interactions[owner];q.push_back({seq_,tick_,other,kind});if(q.size()>16)q.erase(q.begin());};
    add(a,b);if(kind!="read_artifact")add(b,a);
}
void World::complete_culture_action(Entity& actor,const Action& a) {
    const auto id=actor.id;
    auto error=validate_culture_action(actor,a);
    if(!error.empty()){finish(id,false,error);return;}
    auto& receipt=requests_.at(id+":"+a.request_id).second;
    if(a.type=="process_batch") {
        const double needed=practice_seconds(id);
        if(!process_conditions(id,a)||pending_.at(id).exposure_s+1e-8<needed){finish(id,false,"PROCESS_CONDITIONS");return;}
        event("batch_validated",id,a.request_id,"conditioned >=5g water; sustained temperature/dial/heat-off conditions");
        const auto measured=std::round(thermal_.cells[0].phase().temperature/5)*5;
        culture_.batches.push_back({seq_,tick_,id,a.text,measured,needed});
        auto& skill=culture_.practice[id];skill.successes=std::min(3u,skill.successes+1);skill.last_event=seq_;
        receipt.effect="conditioned_water:dial="+a.text+":temperature~"+std::to_string(static_cast<int>(measured))+"K:practice="+std::to_string(skill.successes);
        receipt.event_refs.push_back(seq_);
        for(auto& [key,g]:culture_.agreements)if(g.partner==id&&g.status=="accepted"&&tick_<g.expires_tick) {
            g.status="completed";event("agreement_completed",id,a.request_id,key);g.completed_event=seq_;interaction(id,g.proposer,"task_completed");receipt.event_refs.push_back(seq_);
        }
    } else if(a.type=="write_book") {
        const auto position=actor.position;const auto book_id="artifact-"+std::to_string(seq_+1);
        const auto* source=known_report(id,a.evidence_seq);const auto origin=source?source->origin_seq:a.evidence_seq;
        actor.inventory["inert_material"]-=10000000;
        event("artifact_written",id,a.request_id,book_id);const auto written=seq_;
        books_[book_id]={origin,a.text,id,written};
        entities_.push_back({book_id,"book",position,0,10000000,{}});rebuild_grid();
        receipt.effect="written:"+book_id;receipt.event_refs.push_back(written);
    } else if(a.type=="depart") {
        event("departure",id,a.request_id,"voluntary departure; artifacts remain");culture_.departed.insert(id);
        receipt.effect="departed";receipt.event_refs.push_back(seq_);
    } else if(a.type=="give") {
        auto peer=find(a.target_id);actor.inventory[a.material]-=a.mass_ug;peer->inventory[a.material]+=a.mass_ug;
        event("resource_given",id,a.request_id,a.target_id+":"+a.material+":"+std::to_string(a.mass_ug)+"ug");interaction(id,a.target_id,"resource_given");
        receipt.effect="gave:"+a.target_id+":"+a.material+":"+std::to_string(a.mass_ug)+"ug";receipt.event_refs.push_back(seq_);
    } else if(a.type=="offer_task") {
        event("agreement_offered",id,a.request_id,a.target_id+":"+a.text);
        Agreement agreement;agreement.id=a.request_id;agreement.proposer=id;agreement.partner=a.target_id;agreement.text=a.text;agreement.offered_event=seq_;agreement.expires_tick=tick_+static_cast<U64>(std::ceil(120/dt_));
        culture_.agreements[a.request_id]=agreement;interaction(id,a.target_id,"task_offered");
        receipt.effect="offered:"+a.request_id;receipt.event_refs.push_back(seq_);
    } else {
        auto& g=culture_.agreements.at(a.target_id);g.status=a.text=="accept"?"accepted":"declined";
        event("agreement_"+g.status,id,a.request_id,g.id);g.accepted_event=seq_;interaction(id,g.proposer,"task_"+g.status);
        receipt.effect=g.status+":"+g.id;receipt.event_refs.push_back(seq_);
    }
    finish(id,true,"");
}
void World::update_culture() {
    if(!culture_.enabled)return;
    for(auto& [id,g]:culture_.agreements)if((g.status=="offered"||g.status=="accepted")&&tick_>=g.expires_tick){g.status="expired";event("agreement_expired",g.proposer,"",id);}
}
void World::write_culture(std::ostream& out) const {
    out<<culture_.enabled<<' '<<culture_.apparatus_seed<<' '<<culture_.target_k<<' '<<culture_.correct_dial<<' '<<culture_.dials.size()<<'\n';
    for(const auto& d:culture_.dials)out<<std::quoted(d)<<' ';
    out<<'\n'<<culture_.practice.size()<<'\n';
    for(const auto& [id,p]:culture_.practice)out<<std::quoted(id)<<' '<<p.successes<<' '<<p.last_event<<'\n';
    out<<culture_.agreements.size()<<'\n';for(const auto& [id,g]:culture_.agreements)out<<std::quoted(id)<<' '<<std::quoted(g.proposer)<<' '<<std::quoted(g.partner)<<' '<<std::quoted(g.text)<<' '<<std::quoted(g.status)<<' '<<g.offered_event<<' '<<g.accepted_event<<' '<<g.completed_event<<' '<<g.expires_tick<<'\n';
    out<<culture_.interactions.size()<<'\n';for(const auto& [id,q]:culture_.interactions){out<<std::quoted(id)<<' '<<q.size()<<'\n';for(const auto& i:q)out<<i.seq<<' '<<i.tick<<' '<<std::quoted(i.other)<<' '<<std::quoted(i.kind)<<'\n';}
    out<<culture_.batches.size()<<'\n';for(const auto& b:culture_.batches)out<<b.seq<<' '<<b.tick<<' '<<std::quoted(b.agent)<<' '<<std::quoted(b.dial)<<' '<<b.measured_k<<' '<<b.work_s<<'\n';
    out<<culture_.departed.size()<<'\n';for(const auto& id:culture_.departed)out<<std::quoted(id)<<' ';out<<'\n';
}
void World::read_culture(std::istream& in) {
    auto count=[&](unsigned cap){unsigned n{};in>>n;if(!in||n>cap)throw std::invalid_argument("culture checkpoint count");return n;};
    in>>culture_.enabled>>culture_.apparatus_seed>>culture_.target_k>>culture_.correct_dial;
    auto n=count(4);for(unsigned i=0;i<n;++i){std::string d;in>>std::quoted(d);culture_.dials.push_back(d);}
    n=count(64);for(unsigned i=0;i<n;++i){std::string id;Practice p;in>>std::quoted(id)>>p.successes>>p.last_event;if(!culture_.practice.emplace(id,p).second)throw std::invalid_argument("duplicate practice");}
    n=count(64);for(unsigned i=0;i<n;++i){Agreement g;in>>std::quoted(g.id)>>std::quoted(g.proposer)>>std::quoted(g.partner)>>std::quoted(g.text)>>std::quoted(g.status)>>g.offered_event>>g.accepted_event>>g.completed_event>>g.expires_tick;if(!culture_.agreements.emplace(g.id,g).second)throw std::invalid_argument("duplicate agreement");}
    n=count(64);for(unsigned i=0;i<n;++i){std::string id;in>>std::quoted(id);if(culture_.interactions.contains(id))throw std::invalid_argument("duplicate interaction owner");auto size=count(16);auto& q=culture_.interactions[id];for(unsigned k=0;k<size;++k){Interaction x;in>>x.seq>>x.tick>>std::quoted(x.other)>>std::quoted(x.kind);q.push_back(x);}}
    n=count(256);for(unsigned i=0;i<n;++i){Batch b;in>>b.seq>>b.tick>>std::quoted(b.agent)>>std::quoted(b.dial)>>b.measured_k>>b.work_s;culture_.batches.push_back(b);}
    n=count(64);for(unsigned i=0;i<n;++i){std::string id;in>>std::quoted(id);if(!culture_.departed.insert(id).second)throw std::invalid_argument("duplicate departure");}
    if(!in)throw std::invalid_argument("truncated culture checkpoint");
}
void World::check_culture() const {
    if(!culture_.enabled){if(culture_.apparatus_seed||culture_.target_k||culture_.correct_dial||!culture_.dials.empty()||!culture_.practice.empty()||!culture_.agreements.empty()||!culture_.interactions.empty()||!culture_.batches.empty()||!culture_.departed.empty())throw std::invalid_argument("inactive culture state");return;}
    double target{};unsigned correct{};
    if(!bodies_||!thermal_.enabled||labels(culture_.apparatus_seed,target,correct)!=culture_.dials||target!=culture_.target_k||correct!=culture_.correct_dial||culture_.agreements.size()>64||culture_.batches.size()>256)throw std::invalid_argument("invalid cultural apparatus");
    auto actor=[&](const std::string& id){auto e=find(id);return e&&e->kind=="actor";};
    for(const auto& id:culture_.departed)if(!actor(id))throw std::invalid_argument("invalid departed actor");
    for(const auto& [id,p]:culture_.practice)if(!actor(id)||p.successes>3||!known_experience(id,p.last_event)||p.successes!=std::min(3u,static_cast<unsigned>(std::count_if(culture_.batches.begin(),culture_.batches.end(),[&](const auto& b){return b.agent==id;}))))throw std::invalid_argument("unvalidated practice");
    U64 previous=0;for(const auto& b:culture_.batches){if(!actor(b.agent)||b.seq<=previous||b.seq>seq_||b.tick>tick_||b.dial!=culture_.dials[correct]||!std::isfinite(b.measured_k)||std::abs(b.measured_k-target)>10||!std::isfinite(b.work_s)||b.work_s<4/1.75-1e-9||b.work_s>4)throw std::invalid_argument("invalid batch evidence");previous=b.seq;}
    for(const auto& [id,g]:culture_.agreements)if(id!=g.id||!actor(g.proposer)||!actor(g.partner)||g.proposer==g.partner||g.text.empty()||g.text.size()>160||g.offered_event==0||g.offered_event>seq_||g.accepted_event>seq_||g.completed_event>seq_||(g.status!="offered"&&g.status!="accepted"&&g.status!="declined"&&g.status!="completed"&&g.status!="expired"))throw std::invalid_argument("invalid agreement");
    for(const auto& [id,q]:culture_.interactions){if(!actor(id)||q.size()>16)throw std::invalid_argument("invalid interaction owner");U64 prior=0;for(const auto& i:q){if(!actor(i.other)||id==i.other||i.seq<prior||!i.seq||i.seq>seq_||i.tick>tick_||i.kind.empty()||i.kind.size()>32)throw std::invalid_argument("invalid interaction evidence");prior=i.seq;}}
}
}
