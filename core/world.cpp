#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <numbers>
#include <set>
#include <sstream>
#include <stdexcept>

namespace uw {
namespace {
constexpr std::int64_t kg = 1000000000;
constexpr double actor_radius = .25, cell = 4;
double distance(Point a, Point b) { return std::hypot(a.x-b.x,a.y-b.y); }
bool identifier(const std::string& s) {
    return !s.empty() && s.size()<=128 && std::all_of(s.begin(),s.end(),[](unsigned char c){
        return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-';
    });
}
bool same(const Action& a, const Action& b) {
    return a.request_id==b.request_id && a.agent_id==b.agent_id && a.type==b.type &&
        a.target_id==b.target_id && a.destination_id==b.destination_id && a.material==b.material && a.evidence_seq==b.evidence_seq && a.version==b.version && a.destination.x==b.destination.x &&
        a.destination.y==b.destination.y && a.mass_ug==b.mass_ug && a.duration_s==b.duration_s&&a.text==b.text;
}
void write_action(std::ostream& out,const Action& a) {
    out<<std::quoted(a.request_id)<<' '<<std::quoted(a.agent_id)<<' '<<std::quoted(a.type)<<' '
       <<std::quoted(a.target_id)<<' '<<a.version<<' '<<a.destination.x<<' '<<a.destination.y
       <<' '<<a.mass_ug<<' '<<a.duration_s<<' '<<std::quoted(a.text)<<' '<<a.evidence_seq<<' '<<std::quoted(a.destination_id)<<' '<<std::quoted(a.material)<<' ';
}
void read_action(std::istream& in,Action& a) {
    in>>std::quoted(a.request_id)>>std::quoted(a.agent_id)>>std::quoted(a.type)
      >>std::quoted(a.target_id)>>a.version>>a.destination.x>>a.destination.y>>a.mass_ug>>a.duration_s>>std::quoted(a.text)>>a.evidence_seq>>std::quoted(a.destination_id)>>std::quoted(a.material);
}
}

World::World(U64 seed,unsigned population,double width,double height,double dt,U64 interval,bool scripted,
             bool bodies,double food_kg,double water_kg,double food_regen,double water_regen)
    : seed_(seed), interval_(interval), width_(width), height_(height), dt_(dt), scripted_(scripted),
      bodies_(bodies), food_regen_(food_regen),water_regen_(water_regen),rng_(seed) {
    if(population<1||population>64||!std::isfinite(width)||!std::isfinite(height)||
       width<8||height<8||width>1024||height>1024||!std::isfinite(dt)||dt<.01||dt>1||interval<1||interval>100000)
        throw std::invalid_argument("INVALID_ARGUMENT: invalid world configuration");
    if(!std::isfinite(food_kg)||!std::isfinite(water_kg)||food_kg<0||food_kg>1000||water_kg<0||water_kg>1000||
       !std::isfinite(food_regen)||!std::isfinite(water_regen)||food_regen<0||food_regen>.01||water_regen<0||water_regen>.01)
        throw std::invalid_argument("INVALID_ARGUMENT: invalid resource configuration");
    entities_.push_back({"terrain-1","rock",{width/2,height/2},1,0,{}});
    for(unsigned i=0;i<population;++i) {
        Entity e{"agent-"+std::to_string(i+1),"actor",{},actor_radius,0,{}};
        bool placed=false;
        for(unsigned trial=0;trial<10000&&!placed;++trial) {
            auto coordinate=[this](double extent){return 1+(static_cast<double>(rng_()>>11)/9007199254740992.0)*(extent-2);};
            e.position = (i==0&&trial==0) ? Point{2,3} : Point{coordinate(width),coordinate(height)};
            placed=std::all_of(entities_.begin(),entities_.end(),[&e](const Entity& other){
                return distance(e.position,other.position)>=e.radius+other.radius;
            });
        }
        if(!placed) throw std::invalid_argument("INVALID_ARGUMENT: cannot place population without overlap");
        entities_.push_back(e);
    }
    entities_.push_back({"resource-1","food",{2,2},0,static_cast<std::int64_t>(std::llround(food_kg*kg)),{}});
    entities_.push_back({"resource-2","water",{3,2},0,static_cast<std::int64_t>(std::llround(water_kg*kg)),{}});
    entities_.push_back({"resource-3","inert_material",{4,2},0,32*kg,{}});
    initial_mass_={{"food",entities_[entities_.size()-3].mass_ug},{"water",entities_[entities_.size()-2].mass_ug},{"inert_material",32*kg}};
    source_mass_={{"food",0},{"water",0},{"inert_material",0}};
    for(const auto& kind:{"fuel_X","oxygen","product_P"}){initial_mass_[kind]=0;source_mass_[kind]=0;}
    next_id_=entities_.size()+1;
    rebuild_grid();
    check_invariants();
}
Entity* World::find(const std::string& id) {
    auto it=std::find_if(entities_.begin(),entities_.end(),[&](const Entity& e){return e.id==id;});
    return it==entities_.end()?nullptr:&*it;
}
const Entity* World::find(const std::string& id) const {
    auto it=std::find_if(entities_.begin(),entities_.end(),[&](const Entity& e){return e.id==id;});
    return it==entities_.end()?nullptr:&*it;
}
void World::rebuild_grid() {
    grid_.clear();
    for(std::size_t i=0;i<entities_.size();++i) {
        auto p=entities_[i].position;
        grid_[{static_cast<int>(p.x/cell),static_cast<int>(p.y/cell)}].push_back(i);
    }
}
std::vector<Entity> World::nearby(const std::string& id,double range) const {
    auto actor=find(id);
    if(!actor||actor->kind!="actor"||!std::isfinite(range)||range<0||range>64)
        throw std::invalid_argument("INVALID_ARGUMENT: observation query");
    std::vector<Entity> result;
    if(culture_.departed.contains(id))return result;
    auto p=actor->position;
    for(int x=static_cast<int>(std::floor((p.x-range)/cell));x<=static_cast<int>((p.x+range)/cell);++x)
        for(int y=static_cast<int>(std::floor((p.y-range)/cell));y<=static_cast<int>((p.y+range)/cell);++y) {
            auto found=grid_.find({x,y});
            if(found==grid_.end()) continue;
            for(auto index:found->second) {
                const auto& e=entities_[index];
                if(e.id!=id&&!culture_.departed.contains(e.id)&&distance(p,e.position)<=range&&(!bodies_||visible(id,e.id,std::min(range,8.0)))) {
                    auto projected=e;
                    projected.inventory.clear(); // Never expose another actor's inventory.
                    result.push_back(projected);
                }
            }
        }
    std::sort(result.begin(),result.end(),[](const Entity&a,const Entity&b){return a.id<b.id;});
    return result;
}
bool World::clear_segment(const Entity& actor,Point to) const {
    auto p=actor.position;
    for(int x=static_cast<int>(std::floor((std::min(p.x,to.x)-2)/cell));x<=static_cast<int>((std::max(p.x,to.x)+2)/cell);++x)
        for(int y=static_cast<int>(std::floor((std::min(p.y,to.y)-2)/cell));y<=static_cast<int>((std::max(p.y,to.y)+2)/cell);++y) {
            auto found=grid_.find({x,y});
            if(found==grid_.end()) continue;
            for(auto index:found->second) {
                const auto& other=entities_[index];
                if(other.id==actor.id||other.radius==0||culture_.departed.contains(other.id)) continue;
                double dx=to.x-p.x,dy=to.y-p.y,len=dx*dx+dy*dy;
                double t=len==0?0:std::clamp(((other.position.x-p.x)*dx+(other.position.y-p.y)*dy)/len,0.0,1.0);
                if(distance({p.x+t*dx,p.y+t*dy},other.position)<actor.radius+other.radius-1e-12) return false;
            }
        }
    return true;
}
void World::event(std::string type,std::string agent,std::string request,std::string detail) {
    ++event_counts_[type];
    events_.push_back({++seq_,tick_,std::move(type),std::move(agent),std::move(request),std::move(detail)});
}
Result World::submit(const Action& a) {
    Result r{a.request_id,a.agent_id,"rejected","",tick_,tick_,tick_};
    const std::string key=a.agent_id+":"+a.request_id;
    auto reject=[&](std::string error){r.error=std::move(error);return r;};
    if(!identifier(a.request_id)||!identifier(a.agent_id)) return reject("INVALID_ARGUMENT");
    if(!std::isfinite(a.duration_s)||!std::isfinite(a.destination.x)||!std::isfinite(a.destination.y))
        return reject("INVALID_ARGUMENT");
    if(auto it=requests_.find(key);it!=requests_.end()) {
        if(same(it->second.first,a)) return it->second.second;
        return reject("INVALID_ARGUMENT");
    }
    if(requests_.size()>=10000) return reject("REQUEST_LIMIT");
    const auto record=[&](Result result){ event("action_rejected",a.agent_id,a.request_id,result.error);result.event_refs.push_back(seq_);requests_[key]={a,result};return result; };
    auto actor=find(a.agent_id);
    if(!actor||actor->kind!="actor") return record(reject("UNAUTHORIZED"));
    if(culture_.departed.contains(a.agent_id))return record(reject("ABSENT"));
    if(bodies_&&!actor->body.alive)return record(reject("DEAD"));
    if(a.version!=tick_) return record(reject("STALE_OBSERVATION"));
    if(!std::isfinite(a.duration_s)||a.duration_s<.1||a.duration_s>60||
       !std::isfinite(a.destination.x)||!std::isfinite(a.destination.y)) return record(reject("INVALID_ARGUMENT"));
    if(pending_.contains(a.agent_id)) return record(reject("BUSY"));
    for(const auto& prefix:{std::string("utility-"),std::string("script-")})
        if(a.request_id.starts_with(prefix)&&a.request_id!=prefix+std::to_string(a.version)+"-"+a.agent_id)return record(reject("INVALID_ARGUMENT"));
    if(a.type=="move") {
        if(!a.text.empty()||!a.target_id.empty()||a.mass_ug!=0||a.destination.x<actor_radius||a.destination.y<actor_radius||
           a.destination.x>width_-actor_radius||a.destination.y>height_-actor_radius) return record(reject("INVALID_ARGUMENT"));
    } else if(a.type=="gather"||a.type=="deposit") {
        auto target=find(a.target_id);
        if(!target||target->radius!=0||(target->kind!="food"&&target->kind!="water"&&target->kind!="inert_material")||!visible(a.agent_id,a.target_id)) return record(reject("TARGET_UNAVAILABLE"));
        if(distance(actor->position,target->position)>1.5) return record(reject("OUT_OF_REACH"));
        if(!a.text.empty()||a.mass_ug<=0||a.mass_ug>10*kg||a.destination.x!=0||a.destination.y!=0||
            (bodies_&&a.duration_s<1)) return record(reject("INVALID_ARGUMENT"));
        const auto it=actor->inventory.find(target->kind);
        auto available=a.type=="gather"?target->mass_ug:(it==actor->inventory.end()?0:it->second);
        if(available<a.mass_ug) return record(reject("INSUFFICIENT_RESOURCE"));
        std::int64_t held=0;for(const auto& pair:actor->inventory)held+=pair.second;
        if(bodies_&&a.type=="gather"&&held+a.mass_ug>2*kg)return record(reject("CAPACITY_EXCEEDED"));
    } else {
        auto error=validate_body_action(*actor,a);
        if(!error.empty())return record(reject(error));
    }
    if(a.type!="speak"&&a.type!="write_book"&&a.evidence_seq!=0)return record(reject("INVALID_ARGUMENT"));
    if(a.type!="move_material"&&a.type!="give"&&(!a.destination_id.empty()||!a.material.empty()))return record(reject("INVALID_ARGUMENT"));
    r.status="accepted";
    r.completed=0;
    pending_[a.agent_id]={a,static_cast<U64>(std::ceil(a.duration_s/dt_-1e-12)),tick_};
    event("action_accepted",a.agent_id,a.request_id,a.type);
    r.event_refs.push_back(seq_);requests_[key]={a,r};
    return r;
}
void World::finish(const std::string& id,bool success,const std::string& error) {
    const auto& p=pending_.at(id);
    auto& r=requests_.at(id+":"+p.action.request_id).second;
    r.status=success?"completed":"failed";r.error=error;r.completed=tick_;r.version=tick_;
    event("action_"+r.status,id,p.action.request_id,error);
    r.event_refs.push_back(seq_);
}
void World::scripted_decisions() {
    for(const auto& e:entities_) if(e.kind=="actor"&&!pending_.contains(e.id)) {
        auto coordinate=[this](double extent){return 1+(static_cast<double>(rng_()>>11)/9007199254740992.0)*(extent-2);};
        Action a{"script-"+std::to_string(tick_)+"-"+e.id,e.id,"move","",tick_,{coordinate(width_),coordinate(height_)},0,5};
        submit(a);
    }
    next_script_tick_+=interval_;
}
double World::sunlight_w_m2() const {
    return 100*std::max(0.0,std::sin(2*std::numbers::pi*(static_cast<double>(tick_)*dt_)/86400));
}
std::vector<Event> World::step(unsigned ticks) {
    if(ticks>10000||tick_>std::numeric_limits<U64>::max()-ticks)
        throw std::invalid_argument("INVALID_ARGUMENT: tick batch must be <=10000 without overflow");
    for(unsigned i=0;i<ticks;++i) {
        if(scripted_&&tick_>=next_script_tick_) scripted_decisions();
        replenish();
        const double absorbed=thermal_.enabled&&!thermal_.open_boundaries?0:sunlight_w_m2()*width_*height_*dt_;
        energy_j_+=absorbed;solar_input_j_+=absorbed;
        thermal_.step(dt_,sunlight_w_m2(),energy_j_);
        ++tick_;update_culture();
        for(auto& [id,p]:pending_) {
            auto actor=find(id);
            bool failed=false;
            std::string error;
            if(p.action.type=="move") {
                double d=distance(actor->position,p.action.destination);
                double fraction=d==0?0:std::min(dt_/d,1.0); // Speed 1 m/s.
                Point to{actor->position.x+(p.action.destination.x-actor->position.x)*fraction,
                         actor->position.y+(p.action.destination.y-actor->position.y)*fraction};
                if(clear_segment(*actor,to)) {actor->position=to;rebuild_grid();}
                else {failed=true;error="COLLISION";}
            }
            if(p.action.type=="process_batch")p.exposure_s=process_conditions(id,p.action)?p.exposure_s+dt_:0;
            --p.remaining;
            bool body_completed=false;
            if(!failed&&p.remaining==0&&p.action.type!="move"&&p.action.type!="gather"&&p.action.type!="deposit") {
                complete_body_action(*actor,p.action);body_completed=true;
            }
            if(!failed&&p.remaining==0&&(p.action.type=="gather"||p.action.type=="deposit")) {
                auto target=find(p.action.target_id);
                if(!target||!visible(id,p.action.target_id)||distance(actor->position,target->position)>1.5) {failed=true;error="OUT_OF_REACH";}
                else {
                    const auto it=actor->inventory.find(target->kind);
                    const auto held=it==actor->inventory.end()?0:it->second;
                    auto available=p.action.type=="gather"?target->mass_ug:held;
                    if(available<p.action.mass_ug) {failed=true;error="INSUFFICIENT_RESOURCE";}
                    else {
                        const auto amount=p.action.mass_ug;
                        if(p.action.type=="gather") {target->mass_ug-=amount;actor->inventory[target->kind]+=amount;}
                        else {target->mass_ug+=amount;actor->inventory[target->kind]-=amount;}
                        event("mass_transfer",id,p.action.request_id,p.action.type+":"+std::to_string(amount)+"ug");
                        auto& receipt=requests_.at(id+":"+p.action.request_id).second;
                        receipt.event_refs.push_back(seq_);receipt.effect=p.action.type+":"+std::to_string(amount)+"ug";
                    }
                }
            }
            bool reached=p.action.type=="move"&&distance(actor->position,p.action.destination)<1e-10;
            if(failed||p.remaining==0||reached) {
                if(!failed&&p.action.type=="move"&&!reached) {failed=true;error="DURATION_EXPIRED";}
                if(!body_completed)finish(id,!failed,error);
                p.remaining=0;
            }
        }
        update_bodies();
        std::erase_if(pending_,[](const auto& pair){return pair.second.remaining==0;});
        event("tick");
    }
    auto result=std::move(events_);events_.clear();return result;
}
std::string World::serialize() const {
    std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(17);
    out<<"UW6 "<<UW_BUILD_ID<<' '<<seed_<<' '<<tick_<<' '<<seq_<<' '<<next_id_<<' '<<interval_
       <<' '<<next_script_tick_<<' '<<width_<<' '<<height_<<' '<<dt_<<' '<<energy_j_<<' '<<scripted_<<' '
       <<bodies_<<' '<<food_regen_<<' '<<water_regen_<<' '<<food_remainder_<<' '<<water_remainder_<<'\n';
    for(const auto& kind:{"food","water","inert_material","fuel_X","oxygen","product_P"})out<<initial_mass_.at(kind)<<' '<<source_mass_.at(kind)<<' ';
    out<<'\n'<<rng_<<'\n';
    out<<entities_.size()<<'\n';
    for(const auto&e:entities_) {
        out<<std::quoted(e.id)<<' '<<std::quoted(e.kind)<<' '<<e.position.x<<' '<<e.position.y<<' '
           <<e.radius<<' '<<e.mass_ug<<' '<<e.inventory.size();
        for(const auto& [kind,mass]:e.inventory) out<<' '<<std::quoted(kind)<<' '<<mass;
        out<<' '<<e.body.hunger<<' '<<e.body.thirst<<' '<<e.body.fatigue<<' '<<e.body.health<<' '<<e.body.alive
           <<' '<<e.body.food_ingested_ug<<' '<<e.body.water_ingested_ug<<'\n';
    }
    out<<requests_.size()<<'\n';
    for(const auto&[key,pair]:requests_) {
        out<<std::quoted(key)<<' ';write_action(out,pair.first);const auto&r=pair.second;
        out<<std::quoted(r.status)<<' '<<std::quoted(r.error)<<' '<<r.started<<' '<<r.completed<<' '<<r.version<<' '
           <<std::quoted(r.effect)<<' '<<r.event_refs.size();for(auto ref:r.event_refs)out<<' '<<ref;out<<'\n';
    }
    out<<pending_.size()<<'\n';
    for(const auto&[id,p]:pending_) {out<<std::quoted(id)<<' ';write_action(out,p.action);out<<p.remaining<<' '<<p.started<<' '<<p.exposure_s<<'\n';}
    out<<events_.size()<<'\n';
    for(const auto&e:events_) out<<e.seq<<' '<<e.tick<<' '<<std::quoted(e.type)<<' '<<std::quoted(e.agent_id)<<' '<<std::quoted(e.request_id)<<' '<<std::quoted(e.detail)<<'\n';
    out<<messages_.size()<<'\n';
    for(const auto&[id,queue]:messages_) {
        out<<std::quoted(id)<<' '<<queue.size()<<'\n';
        for(const auto&m:queue)out<<m.seq<<' '<<m.tick<<' '<<std::quoted(m.speaker_id)<<' '<<std::quoted(m.text)<<' '<<m.origin_seq<<' '<<m.parent_seq<<' '<<std::quoted(m.source_id)<<'\n';
    }
    out<<guided_<<' '<<hearing_range_<<' '<<operator_energy_j_<<'\n';
    for(const auto& kind:{"food","water","inert_material","fuel_X","oxygen","product_P"})out<<operator_mass_.at(kind)<<' ';
    out<<'\n'<<books_.size()<<'\n';
    for(const auto&[id,b]:books_)out<<std::quoted(id)<<' '<<b.origin_seq<<' '<<std::quoted(b.text)<<' '<<std::quoted(b.author)<<' '<<b.parent_seq<<'\n';
    out<<readings_.size()<<'\n';
    for(const auto&[id,queue]:readings_) {
        out<<std::quoted(id)<<' '<<queue.size()<<'\n';
        for(const auto&m:queue)out<<m.seq<<' '<<m.tick<<' '<<std::quoted(m.speaker_id)<<' '<<std::quoted(m.text)<<' '<<m.origin_seq<<' '<<m.parent_seq<<' '<<std::quoted(m.source_id)<<'\n';
    }
    out<<interventions_.size()<<'\n';
    for(const auto&[id,p]:interventions_)out<<std::quoted(id)<<' '<<std::quoted(p.first)<<' '<<p.second<<'\n';
    out<<solar_input_j_<<'\n';thermal_.write(out);write_culture(out);
    out<<event_counts_.size()<<'\n';for(const auto& [kind,n]:event_counts_)out<<std::quoted(kind)<<' '<<n<<'\n';
    return out.str();
}
World World::restore(const std::string& state) {
    if(state.size()>8*1024*1024) throw std::invalid_argument("checkpoint too large");
    std::istringstream in(state);in.imbue(std::locale::classic());
    std::string magic,build;in>>magic>>build;
    if(magic!="UW6"||build!=UW_BUILD_ID) throw std::invalid_argument("incompatible checkpoint format/build");
    World w;in>>w.seed_>>w.tick_>>w.seq_>>w.next_id_>>w.interval_>>w.next_script_tick_>>w.width_>>w.height_>>w.dt_>>w.energy_j_>>w.scripted_
      >>w.bodies_>>w.food_regen_>>w.water_regen_>>w.food_remainder_>>w.water_remainder_;
    for(const auto&kind:{"food","water","inert_material","fuel_X","oxygen","product_P"})in>>w.initial_mass_[kind]>>w.source_mass_[kind];
    in>>w.rng_;
    auto count=[&](std::size_t max){std::size_t n=0;in>>n;if(!in||n>max)throw std::invalid_argument("invalid checkpoint count");return n;};
    w.entities_.clear();
    auto n=count(200);
    for(std::size_t i=0;i<n;++i) {
        Entity e;in>>std::quoted(e.id)>>std::quoted(e.kind)>>e.position.x>>e.position.y>>e.radius>>e.mass_ug;
        auto inv=count(3);
        for(std::size_t j=0;j<inv;++j) {std::string kind;std::int64_t mass;in>>std::quoted(kind)>>mass;if(!e.inventory.emplace(kind,mass).second)throw std::invalid_argument("duplicate inventory");}
        in>>e.body.hunger>>e.body.thirst>>e.body.fatigue>>e.body.health>>e.body.alive>>e.body.food_ingested_ug>>e.body.water_ingested_ug;
        w.entities_.push_back(e);
    }
    w.requests_.clear();n=count(10000);
    for(std::size_t i=0;i<n;++i) {
        std::string key;Action a;Result r;
        in>>std::quoted(key);read_action(in,a);r.request_id=a.request_id;r.agent_id=a.agent_id;
        in>>std::quoted(r.status)>>std::quoted(r.error)>>r.started>>r.completed>>r.version;
        in>>std::quoted(r.effect);auto refs=count(8);for(std::size_t k=0;k<refs;++k){U64 ref;in>>ref;r.event_refs.push_back(ref);}
        if(!w.requests_.emplace(key,std::make_pair(a,r)).second) throw std::invalid_argument("duplicate request");
    }
    w.pending_.clear();n=count(64);
    for(std::size_t i=0;i<n;++i) {std::string id;Pending p;in>>std::quoted(id);read_action(in,p.action);in>>p.remaining>>p.started>>p.exposure_s;if(!w.pending_.emplace(id,p).second)throw std::invalid_argument("duplicate pending");}
    w.events_.clear();n=count(50000);
    for(std::size_t i=0;i<n;++i) {Event e;in>>e.seq>>e.tick>>std::quoted(e.type)>>std::quoted(e.agent_id)>>std::quoted(e.request_id)>>std::quoted(e.detail);w.events_.push_back(e);}
    w.messages_.clear();n=count(64);
    for(std::size_t i=0;i<n;++i) {
        std::string id;in>>std::quoted(id);auto messages=count(16);auto& queue=w.messages_[id];
        for(std::size_t k=0;k<messages;++k){Message m;in>>m.seq>>m.tick>>std::quoted(m.speaker_id)>>std::quoted(m.text)>>m.origin_seq>>m.parent_seq>>std::quoted(m.source_id);queue.push_back(m);}
    }
    in>>w.guided_>>w.hearing_range_>>w.operator_energy_j_;
    for(const auto&kind:{"food","water","inert_material","fuel_X","oxygen","product_P"})in>>w.operator_mass_[kind];
    w.books_.clear();n=count(128);
    for(std::size_t i=0;i<n;++i){std::string id;Book b;in>>std::quoted(id)>>b.origin_seq>>std::quoted(b.text)>>std::quoted(b.author)>>b.parent_seq;if(!w.books_.emplace(id,b).second)throw std::invalid_argument("duplicate book");}
    w.readings_.clear();n=count(64);
    for(std::size_t i=0;i<n;++i){std::string id;in>>std::quoted(id);auto size=count(16);auto& q=w.readings_[id];for(std::size_t k=0;k<size;++k){Message m;in>>m.seq>>m.tick>>std::quoted(m.speaker_id)>>std::quoted(m.text)>>m.origin_seq>>m.parent_seq>>std::quoted(m.source_id);q.push_back(m);}}
    w.interventions_.clear();n=count(256);
    for(std::size_t i=0;i<n;++i){std::string id,signature;U64 seq;in>>std::quoted(id)>>std::quoted(signature)>>seq;if(!w.interventions_.emplace(id,std::make_pair(signature,seq)).second)throw std::invalid_argument("duplicate intervention");}
    in>>w.solar_input_j_;w.thermal_.read(in);w.read_culture(in);
    w.event_counts_.clear();n=count(64);
    for(std::size_t i=0;i<n;++i){std::string kind;U64 value;in>>std::quoted(kind)>>value;if(!w.event_counts_.emplace(kind,value).second)throw std::invalid_argument("duplicate event counter");}
    if(!in) throw std::invalid_argument("truncated checkpoint");
    in>>std::ws;if(!in.eof())throw std::invalid_argument("trailing checkpoint data");
    w.check_invariants();w.rebuild_grid();return w;
}
void World::check_invariants() const {
    if(!std::isfinite(width_)||!std::isfinite(height_)||width_<8||height_<8||width_>1024||height_>1024||
       !std::isfinite(dt_)||dt_<.01||dt_>1||!std::isfinite(energy_j_)||energy_j_<0||interval_<1||interval_>100000||
       entities_.size()<5||entities_.size()>200||!std::isfinite(solar_input_j_)||solar_input_j_<0||!std::isfinite(hearing_range_)||hearing_range_<1||hearing_range_>12||
       !std::isfinite(operator_energy_j_)||operator_energy_j_<0||operator_energy_j_>energy_j_) throw std::invalid_argument("invalid world state");
    std::set<std::string> ids;
    std::map<std::string,std::int64_t> total;
    unsigned actors=0;
    for(const auto&e:entities_) {
        if(!identifier(e.id)||!ids.insert(e.id).second||!std::isfinite(e.position.x)||!std::isfinite(e.position.y)||
           !std::isfinite(e.radius)||e.radius<0||e.radius>1||e.position.x<e.radius||e.position.y<e.radius||
           e.position.x>width_-e.radius||e.position.y>height_-e.radius||e.mass_ug<0||e.mass_ug>1000000*kg)
            throw std::invalid_argument("invalid entity state");
        if(e.kind=="actor") {++actors;if(e.radius!=actor_radius||e.mass_ug!=0)throw std::invalid_argument("invalid actor");}
        else if(e.kind=="rock") {if(e.radius!=1||e.mass_ug!=0||!e.inventory.empty())throw std::invalid_argument("invalid rock");}
        else if(e.kind=="food"||e.kind=="water"||e.kind=="inert_material") {if(e.radius!=0||!e.inventory.empty())throw std::invalid_argument("invalid resource");total[e.kind]+=e.mass_ug;}
        else if(e.kind=="book"||e.kind=="object") {if(!e.inventory.empty()||e.radius!=(e.kind=="book"?0:.5)||(e.kind=="book"&&!books_.contains(e.id)))throw std::invalid_argument("invalid introduced object");total["inert_material"]+=e.mass_ug;}
        else if(e.kind=="operator_avatar") {if(e.id!="operator-avatar"||e.radius!=.25||e.mass_ug!=0||!e.inventory.empty())throw std::invalid_argument("invalid avatar");}
        else if(e.kind=="thermal_cell") {if(!thermal_.enabled||e.radius!=0||e.mass_ug!=100000000||!e.inventory.empty())throw std::invalid_argument("invalid thermal vessel");}
        else throw std::invalid_argument("unknown entity kind");
        for(const auto&[kind,mass]:e.inventory) {
            if((kind!="food"&&kind!="water"&&kind!="inert_material")||mass<0||mass>1000000*kg)throw std::invalid_argument("invalid inventory");
            total[kind]+=mass;
        }
        if(e.kind=="actor") {
            const auto& b=e.body;
            for(double need:{b.hunger,b.thirst,b.fatigue,b.health})if(!std::isfinite(need)||need<0||need>1)throw std::invalid_argument("invalid body");
            if(b.alive!=(b.health>0)||b.food_ingested_ug<0||b.water_ingested_ug<0||b.food_ingested_ug>1000000*kg||b.water_ingested_ug>1000000*kg)
                throw std::invalid_argument("invalid ingested reservoir");
            total["food"]+=b.food_ingested_ug;total["water"]+=b.water_ingested_ug;
        }
    }
    if(actors<1||actors>64)throw std::invalid_argument("population invariant failed");
    if(thermal_.enabled) {
        if(!bodies_||width_<12||height_<12)throw std::invalid_argument("invalid thermal world");
        unsigned vessels=0;
        for(const auto& e:entities_)if(e.kind=="thermal_cell")++vessels;
        if(vessels!=4)throw std::invalid_argument("invalid thermal vessel count");
        for(unsigned i=0;i<4;++i){auto e=find("thermal-"+std::to_string(i+1));if(!e||e->kind!="thermal_cell"||e->position.x!=2.+2*(i%2)||e->position.y!=4.+2*(i/2))throw std::invalid_argument("invalid thermal vessel identity");}
    }
    if(thermal_.enabled)for(const auto&[kind,mass]:thermal_.masses())total[kind]+=mass;
    std::map<std::string,std::int64_t> delta{{"fuel_X",-thermal_.burned_fuel},{"oxygen",-2*thermal_.burned_fuel},{"product_P",3*thermal_.burned_fuel},{"water",-thermal_.outflow_water}};
    for(const auto&kind:{"food","water","inert_material","fuel_X","oxygen","product_P"})
        if(initial_mass_.at(kind)<0||source_mass_.at(kind)<0||operator_mass_.at(kind)<0||operator_mass_.at(kind)>source_mass_.at(kind)||total[kind]!=initial_mass_.at(kind)+source_mass_.at(kind)+delta[kind])throw std::invalid_argument("mass/reaction/outflow ledger invariant failed");
    thermal_.check();check_culture();
    U64 counted=0;for(const auto& [kind,n]:event_counts_){if(kind.empty()||kind.size()>64||n>seq_-counted)throw std::invalid_argument("invalid event counter");counted+=n;}
    if(counted!=seq_)throw std::invalid_argument("event counter sum mismatch");
    const double expected=thermal_.initial_energy+solar_input_j_+operator_energy_j_+thermal_.heater_input+thermal_.radiation_in-thermal_.radiation_out-thermal_.outflow_energy;
    if(std::abs(energy_j_+thermal_.stored_energy()-expected)>std::max(1e-5,1e-10*std::abs(expected)))throw std::invalid_argument("world energy balance invariant failed");
    for(const auto&[id,b]:books_)if(!find(id)||find(id)->kind!="book"||b.text.empty()||b.text.size()>1024||b.origin_seq==0||b.origin_seq>seq_)throw std::invalid_argument("invalid book record");
    for(const auto* store:{&messages_,&readings_})for(const auto&[id,queue]:*store) {
        if(!find(id)||find(id)->kind!="actor"||queue.size()>16)throw std::invalid_argument("invalid report owner/count");
        for(const auto&m:queue)if(m.seq==0||m.seq>seq_||m.origin_seq==0||m.origin_seq>m.seq||m.parent_seq>=m.seq||m.tick>tick_||m.text.empty()||m.text.size()>1024)
            throw std::invalid_argument("invalid report provenance");
    }
    for(double value:{food_regen_,water_regen_})if(!std::isfinite(value)||value<0||value>.01)throw std::invalid_argument("invalid boundary rate");
    for(double value:{food_remainder_,water_remainder_})if(!std::isfinite(value)||value<0||value>=1)throw std::invalid_argument("invalid source remainder");
    for(std::size_t i=0;i<entities_.size();++i)for(std::size_t j=i+1;j<entities_.size();++j)
        if(!culture_.departed.contains(entities_[i].id)&&!culture_.departed.contains(entities_[j].id)&&entities_[i].radius>0&&entities_[j].radius>0&&distance(entities_[i].position,entities_[j].position)+1e-10<entities_[i].radius+entities_[j].radius)
            throw std::invalid_argument("overlapping solids");
    for(const auto&[id,p]:pending_) {
        auto e=find(id);auto request=requests_.find(id+":"+p.action.request_id);
        if(!e||e->kind!="actor"||!std::isfinite(p.exposure_s)||p.exposure_s<0||p.exposure_s>60.00000001||p.remaining<1||p.remaining>6001||request==requests_.end()||
           request->second.second.status!="accepted"||!same(request->second.first,p.action))throw std::invalid_argument("invalid pending action");
    }
}
}
