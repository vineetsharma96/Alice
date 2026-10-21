#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <stdexcept>

namespace uw {
namespace {
constexpr std::int64_t kg=1000000000;
double dist(Point a,Point b){return std::hypot(a.x-b.x,a.y-b.y);}
bool food(const std::string& k){return k=="food"||k=="plant_food"||k=="eggs";}
bool perishable(const std::string& k){return k=="plant_food"||k=="eggs";}
std::int64_t held(const Entity& e,const std::string& k){auto i=e.inventory.find(k);return i==e.inventory.end()?0:i->second;}
}
bool ecology_action(const std::string& t){return t=="observe_animal"||t=="offer_feed"||t=="guide_or_lure"||t=="collect_eggs"||t=="gather_plant";}
void World::configure_ecology(double forage,double rate){
    if(tick_||ecology_.enabled||!bodies_||!std::isfinite(forage)||forage<0||forage>2||!std::isfinite(rate)||rate<0||rate>.01||entities_.size()>197)
        throw std::invalid_argument("INVALID_ARGUMENT: new-world ecology only");
    // Stage placement before mutating the world: failed initialization grants nothing.
    std::vector<Entity> added;
    for(unsigned i=0;i<6;++i){
        Entity e;e.id="animal-"+std::to_string(i+1);e.kind="animal";e.radius=.2;e.mass_ug=(i%2)?800000000:2*kg;e.stage="wild";
        std::vector<Point> positions={{4,3.8},{3.7,4.6},{8.5,6.2},{12.4,9.8},{18.2,14.5},{22.6,19.4}};
        for(double y=1;y<height_-1;y+=.6)for(double x=1;x<width_-1;x+=.6)positions.push_back({x,y});
        bool placed=false;
        for(const auto p:positions)if(clear_placement(p,.2)&&std::all_of(added.begin(),added.end(),[&](const auto& o){return dist(p,o.position)>=.4;})){e.position=p;placed=true;break;}
        if(!placed)throw std::invalid_argument("NO_PLACEMENT: ecology");
        added.push_back(e);
    }
    Point forage_position{};bool forage_placed=false;
    for(double y=4.5;y<height_-1&&!forage_placed;y+=.6)for(double x=4;x<width_-1;x+=.6){
        const Point p{x,y};
        if(clear_placement(p,0)&&std::all_of(added.begin(),added.end(),[&](const auto& e){return dist(p,e.position)>=e.radius;})){forage_position=p;forage_placed=true;break;}
    }
    if(!forage_placed)throw std::invalid_argument("NO_PLACEMENT: forage");
    ecology_.enabled=true;ecology_.forage_rate=rate;ecology_.body_initial=8400000000;
    for(unsigned i=0;i<added.size();++i){Animal a;a.species=(i%2)?"reedhen":"mossgrazer";ecology_.animals.emplace(added[i].id,a);entities_.push_back(added[i]);}
    Entity patch;patch.id="forage-1";patch.kind="forage";patch.position=forage_position;patch.mass_ug=std::llround(forage*kg);entities_.push_back(patch);
    initial_mass_["food"]+=patch.mass_ug+1500000000;initial_mass_["water"]+=1200000000;
    event("ecology_initialized","","","authored_v1:declared_initial_body_food_water_and_forage");rebuild_grid();check_invariants();
}
void World::transfer_freshness(const std::string& source,const std::string& destination,const std::string& material,double initial){
    if(!perishable(material))return;
    const auto src=std::make_pair(source,material),dst=std::make_pair(destination,material);
    double life=initial;
    if(!source.empty()){
        auto it=ecology_.freshness.find(src);
        if(it==ecology_.freshness.end())throw std::logic_error("missing food freshness");
        life=it->second;
    }
    auto [it,inserted]=ecology_.freshness.emplace(dst,life);
    if(!inserted)it->second=std::min(it->second,life);
    if(!source.empty()&&held(*find(source),material)==0)ecology_.freshness.erase(src);
}
void World::age_food(){
    for(auto it=ecology_.freshness.begin();it!=ecology_.freshness.end();){
        auto e=find(it->first.first);const auto material=it->first.second;
        if(!e||held(*e,material)==0){it=ecology_.freshness.erase(it);continue;}
        it->second-=dt_*(e->kind=="storage_box"?.5:1);
        if(it->second<=1e-9){
            const auto amount=e->inventory[material];e->inventory[material]=0;ecology_.food_residue+=amount;
            event("food_spoiled",e->id,"",material+":"+std::to_string(amount)+"ug:retained_residue");it=ecology_.freshness.erase(it);
        }else ++it;
    }
}
std::string World::validate_ecology_action(const Entity& actor,const Action& a) const {
    if(!ecology_.enabled||!bodies_)return "UNKNOWN_ACTION";
    if(a.evidence_seq||!a.text.empty()||!a.destination_id.empty()||a.destination.x||a.destination.y)return "INVALID_ARGUMENT";
    auto target=find(a.target_id);
    if(!target||!visible(actor.id,a.target_id,4))return "TARGET_UNAVAILABLE";
    if(a.type=="observe_animal")return target->kind=="animal"&&a.mass_ug==0&&a.material.empty()&&a.duration_s>=.2?"":"INVALID_ARGUMENT";
    if(dist(actor.position,target->position)>1.5)return "OUT_OF_REACH";
    if(a.duration_s<1)return "INVALID_ARGUMENT";
    if(a.type=="gather_plant"){
        if(target->kind!="forage"||!a.material.empty()||a.mass_ug<=0||a.mass_ug>kg)return "INVALID_ARGUMENT";
        if(target->mass_ug<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        return carried_mass(actor)+a.mass_ug>2*kg?"CAPACITY_EXCEEDED":"";
    }
    if(target->kind!="animal")return "TARGET_UNAVAILABLE";
    const auto& animal=ecology_.animals.at(target->id);
    if(!target->body.alive)return "DEAD_TARGET";
    if(a.type=="offer_feed"){
        if(!food(a.material)||a.mass_ug<=0||a.mass_ug>400000000)return "INVALID_ARGUMENT";
        if(held(actor,a.material)<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        return animal.food+a.mass_ug>400000000?"CAPACITY_EXCEEDED":"";
    }
    if(a.type=="collect_eggs"){
        if(a.material!="eggs"||a.mass_ug<=0||a.mass_ug>300000000)return "INVALID_ARGUMENT";
        if(held(*target,"eggs")<a.mass_ug)return "INSUFFICIENT_RESOURCE";
        return carried_mass(actor)+a.mass_ug>2*kg?"CAPACITY_EXCEEDED":"";
    }
    if(a.type=="guide_or_lure"){
        if(a.mass_ug||!a.material.empty())return "INVALID_ARGUMENT";
        auto f=animal.familiarity.find(actor.id);
        return f==animal.familiarity.end()||f->second<2?"UNFAMILIAR":"";
    }
    return "UNKNOWN_ACTION";
}
void World::complete_ecology_action(Entity& actor,const Action& a){
    const auto error=validate_ecology_action(actor,a);
    if(!error.empty()){finish(actor.id,false,error);return;}
    auto target=find(a.target_id);auto& receipt=requests_.at(actor.id+":"+a.request_id).second;
    if(a.type=="gather_plant"){
        target->mass_ug-=a.mass_ug;actor.inventory["plant_food"]+=a.mass_ug;transfer_freshness("",actor.id,"plant_food",120);
        receipt.effect="forage_to_plant_food_ug="+std::to_string(a.mass_ug);
    }else{
        auto& animal=ecology_.animals.at(target->id);
        if(a.type=="offer_feed"){
            actor.inventory[a.material]-=a.mass_ug;animal.food+=a.mass_ug;
            if(!animal.last_feed.contains(actor.id)||(tick_-animal.last_feed.at(actor.id))*dt_>=10-1e-9){
                animal.familiarity[actor.id]=std::min(5u,animal.familiarity[actor.id]+1);animal.last_feed[actor.id]=tick_;
                if(animal.familiarity[actor.id]>=3)target->stage="domestic";
            }
            receipt.effect="fed_ug="+std::to_string(a.mass_ug)+":authored_familiarity="+std::to_string(animal.familiarity[actor.id]);
        }else if(a.type=="collect_eggs"){
            target->inventory["eggs"]-=a.mass_ug;actor.inventory["eggs"]+=a.mass_ug;transfer_freshness(target->id,actor.id,"eggs");
            receipt.effect="collected_eggs_ug="+std::to_string(a.mass_ug);
        }else if(a.type=="guide_or_lure"){
            animal.handler=actor.id;animal.guide_until=tick_+static_cast<U64>(std::ceil(20/dt_));receipt.effect="authored_handling_until_tick="+std::to_string(animal.guide_until);
        }else{
            const auto f=animal.familiarity.find(actor.id);
            receipt.effect=animal.species+":condition="+(target->body.health>.7?"good":"poor")+":hunger="+(target->body.hunger>.7?"high":"low")+":thirst="+(target->body.thirst>.7?"high":"low")+":own_familiarity="+std::to_string(f==animal.familiarity.end()?0:f->second)+":eggs_ug="+std::to_string(held(*target,"eggs"));
        }
    }
    event("animal_care",actor.id,a.request_id,receipt.effect);receipt.event_refs.push_back(seq_);finish(actor.id,true,"");
}
void World::update_ecology(){
    if(!ecology_.enabled)return;
    auto patch=find("forage-1");
    ecology_.forage_remainder+=ecology_.forage_rate*dt_*kg;
    const auto grant=static_cast<std::int64_t>(std::floor(ecology_.forage_remainder));ecology_.forage_remainder-=grant;
    const auto added=std::min(grant,2*kg-patch->mass_ug);patch->mass_ug+=added;source_mass_["food"]+=added;
    for(auto& [id,a]:ecology_.animals){
        auto e=find(id);a.age_s+=dt_;if(!e->body.alive){a.mode="dead";continue;}
        a.food_remainder+=1000000*dt_;a.water_remainder+=1500000*dt_;
        auto debit=[&](std::int64_t& reserve,double& remainder,std::int64_t& waste,std::int64_t& total){auto n=static_cast<std::int64_t>(std::floor(remainder));remainder-=n;n=std::min(n,reserve);reserve-=n;waste+=n;total+=n;};
        debit(a.food,a.food_remainder,ecology_.food_residue,a.metabolized_food);debit(a.water,a.water_remainder,ecology_.water_waste,a.metabolized_water);
        const Entity* target=nullptr;std::string purpose;
        auto sense=[&](const Entity& other){return other.id!=id&&dist(e->position,other.position)<=4&&unobstructed(e->position,other.position,other.id);};
        // Distinct enter/leave thresholds prevent alternating one sip with a
        // short forage approach, which can strand hungry animals at water.
        const bool thirsty=a.water<150000000||(a.mode=="seek_water"&&a.water<250000000);
        const bool hungry=a.food<200000000||(a.mode=="seek_forage"&&a.food<350000000);
        for(const auto& other:entities_){
            bool candidate=thirsty&&((other.kind=="water"&&other.mass_ug>0)||(other.kind=="trough"&&held(other,"water")>0));
            if(!thirsty&&hungry)candidate=other.kind=="forage"&&other.mass_ug>0;
            if(candidate&&sense(other)&&(!target||dist(e->position,other.position)<dist(e->position,target->position)))target=&other;
        }
        if(target)purpose=thirsty?"seek_water":"seek_forage";
        if(!target&&!thirsty&&!hungry&&tick_<=a.guide_until&&!a.handler.empty()){
            auto handler=find(a.handler);if(handler&&handler->body.alive&&!culture_.departed.contains(handler->id)&&sense(*handler)){target=handler;purpose="follow_familiar";}
        }
        Point destination=e->position;
        if(target){
            destination=target->position;a.mode=purpose;
            if(dist(e->position,destination)<=e->radius+target->radius+.2){
                auto stock=find(target->id);const auto bite=static_cast<std::int64_t>(std::llround(20000000*dt_));
                if(purpose=="seek_forage"){
                    auto n=std::min({bite,stock->mass_ug,400000000-a.food});stock->mass_ug-=n;a.food+=n;
                    if(n)event("animal_foraged",id,"",std::to_string(n)+"ug:authored");
                }else if(purpose=="seek_water"){
                    auto& source=stock->kind=="water"?stock->mass_ug:stock->inventory["water"];
                    auto n=std::min({bite,source,300000000-a.water});source-=n;a.water+=n;
                    if(n)event("animal_drank",id,"",stock->id+":"+std::to_string(n)+"ug:authored");
                }
                destination=e->position;
            }
        }else{
            a.mode=e->body.fatigue>.6?"rest":"wander";
            const double angle=static_cast<double>((tick_/25+(id=="animal-1"?3:11))*37%360)*3.141592653589793/180;
            if(a.mode!="rest")destination={e->position.x+std::cos(angle),e->position.y+std::sin(angle)};
        }
        // Threat avoidance is local and familiarity-specific, never a global owner flag.
        for(const auto& other:entities_)if(other.kind=="actor"&&other.body.alive&&!culture_.departed.contains(other.id)&&sense(other)&&dist(e->position,other.position)<.9&&(!a.familiarity.contains(other.id)||a.familiarity.at(other.id)<2)){
            destination={2*e->position.x-other.position.x,2*e->position.y-other.position.y};a.mode="avoid_unfamiliar";break;
        }
        const auto d=dist(e->position,destination);bool moved=false;
        if(d>1e-12){
            const double angle=std::atan2(destination.y-e->position.y,destination.x-e->position.x),length=std::min(.4*dt_,d);
            for(double turn:{0.,.6,-.6,1.2,-1.2}){
                Point to{e->position.x+length*std::cos(angle+turn),e->position.y+length*std::sin(angle+turn)};
                if(to.x>=e->radius&&to.y>=e->radius&&to.x<=width_-e->radius&&to.y<=height_-e->radius&&clear_segment(*e,to)){e->position=to;moved=true;break;}
            }
        }
        auto& b=e->body;b.fatigue=std::clamp(b.fatigue+(moved?.004:-.012)*dt_,0.,1.);
        b.hunger=std::clamp(1-static_cast<double>(a.food)/400000000,0.,1.);b.thirst=std::clamp(1-static_cast<double>(a.water)/300000000,0.,1.);
        if(b.hunger>.95||b.thirst>.95)b.health=std::max(0.,b.health-.01*dt_);
        else if(b.hunger<.8&&b.thirst<.8)b.health=std::min(1.,b.health+.002*dt_);
        b.alive=b.health>0;
        if(!b.alive){a.mode="dead";event("animal_death",id,"","authored_needs_failure:body_and_reserves_retained");continue;}
        if(a.species=="reedhen"){
            a.laying_s=std::min(30.,a.laying_s+dt_);
            if(a.age_s>=60&&a.laying_s>=30-1e-9&&a.food>=80000000&&b.hunger<.7&&b.thirst<.7&&b.health>=.7&&held(*e,"eggs")<=240000000){
                a.food-=80000000;a.laying_s=0;a.laid+=60000000;ecology_.egg_input+=80000000;ecology_.eggs_produced+=60000000;ecology_.food_residue+=20000000;
                e->inventory["eggs"]+=60000000;transfer_freshness("",id,"eggs",180);
                event("egg_laid",id,"","80000000ug_reserve=60000000ug_eggs+20000000ug_residue:authored");
            }
        }
    }
    rebuild_grid();
}
void World::write_ecology(std::ostream& out) const {
    const auto& c=ecology_;
    out<<c.enabled<<' '<<c.forage_rate<<' '<<c.forage_remainder<<' '<<c.body_initial<<' '<<c.food_residue<<' '<<c.water_waste<<' '<<c.egg_input<<' '<<c.eggs_produced<<' '<<c.animals.size()<<'\n';
    for(const auto& [id,a]:c.animals){
        out<<std::quoted(id)<<' '<<std::quoted(a.species)<<' '<<std::quoted(a.mode)<<' '<<std::quoted(a.handler)<<' '<<a.age_s<<' '<<a.laying_s<<' '<<a.guide_until<<' '<<a.food<<' '<<a.water<<' '<<a.metabolized_food<<' '<<a.metabolized_water<<' '<<a.laid<<' '<<a.food_remainder<<' '<<a.water_remainder<<' '<<a.familiarity.size();
        for(const auto& [person,n]:a.familiarity)out<<' '<<std::quoted(person)<<' '<<n<<' '<<a.last_feed.at(person);
        out<<'\n';
    }
    out<<c.freshness.size()<<'\n';for(const auto& [key,life]:c.freshness)out<<std::quoted(key.first)<<' '<<std::quoted(key.second)<<' '<<life<<'\n';
}
void World::read_ecology(std::istream& in){
    auto& c=ecology_;std::size_t n{};
    in>>c.enabled>>c.forage_rate>>c.forage_remainder>>c.body_initial>>c.food_residue>>c.water_waste>>c.egg_input>>c.eggs_produced>>n;
    if(!in||n>16)throw std::invalid_argument("invalid animal count");
    c.animals.clear();
    for(std::size_t i=0;i<n;++i){
        std::string id;Animal a;std::size_t m{};
        in>>std::quoted(id)>>std::quoted(a.species)>>std::quoted(a.mode)>>std::quoted(a.handler)>>a.age_s>>a.laying_s>>a.guide_until>>a.food>>a.water>>a.metabolized_food>>a.metabolized_water>>a.laid>>a.food_remainder>>a.water_remainder>>m;
        if(!in||m>64)throw std::invalid_argument("invalid familiarity count");
        for(std::size_t j=0;j<m;++j){std::string person;unsigned value{};U64 tick{};in>>std::quoted(person)>>value>>tick;if(!in||!a.familiarity.emplace(person,value).second)throw std::invalid_argument("invalid/duplicate familiarity");a.last_feed[person]=tick;}
        if(!c.animals.emplace(id,a).second)throw std::invalid_argument("duplicate animal");
    }
    in>>n;if(!in||n>400)throw std::invalid_argument("invalid freshness count");c.freshness.clear();
    for(std::size_t i=0;i<n;++i){std::string id,k;double life{};in>>std::quoted(id)>>std::quoted(k)>>life;if(!in||!c.freshness.emplace(std::make_pair(id,k),life).second)throw std::invalid_argument("invalid/duplicate freshness");}
}
void World::check_ecology(std::map<std::string,std::int64_t>& total) const {
    const auto& c=ecology_;
    auto fail=[](){throw std::invalid_argument("ecology ledger/state invariant failed");};
    if(!std::isfinite(c.forage_rate)||c.forage_rate<0||c.forage_rate>.01||!std::isfinite(c.forage_remainder)||c.forage_remainder<0||c.forage_remainder>=1||c.food_residue<0||c.water_waste<0||c.egg_input<0||c.eggs_produced<0||c.egg_input>1000000*kg||c.eggs_produced>1000000*kg)fail();
    if(c.enabled){if(!bodies_||c.animals.size()!=2||c.body_initial!=2800000000||!find("forage-1")||find("forage-1")->kind!="forage")fail();}
    else if(!c.animals.empty()||!c.freshness.empty()||c.body_initial||c.food_residue||c.water_waste||c.egg_input||c.eggs_produced||total["animal_body"]||total["forage"]||total["plant_food"]||total["eggs"])fail();
    std::int64_t laid=0,metabolized_food=0,metabolized_water=0;
    for(const auto& [id,a]:c.animals){
        auto e=find(id);if(!e||e->kind!="animal"||e->radius!=.2||e->mass_ug!=(a.species=="mossgrazer"?2*kg:800000000)||(a.species!="mossgrazer"&&a.species!="reedhen")||(e->stage!="wild"&&e->stage!="domestic"))fail();
        if(a.food<0||a.food>400000000||a.water<0||a.water>300000000||a.metabolized_food<0||a.metabolized_water<0||a.metabolized_food>1000000*kg||a.metabolized_water>1000000*kg||a.laid<0||a.laid>1000000*kg||a.familiarity.size()!=a.last_feed.size())fail();
        if(!e->composition.empty()||!e->recipe_id.empty()||!e->owner_id.empty()||e->body.food_ingested_ug||e->body.water_ingested_ug)fail();
        if(a.mode!="rest"&&a.mode!="wander"&&a.mode!="seek_water"&&a.mode!="seek_forage"&&a.mode!="follow_familiar"&&a.mode!="avoid_unfamiliar"&&a.mode!="dead")fail();
        for(const auto x:{a.age_s,a.laying_s,a.food_remainder,a.water_remainder})if(!std::isfinite(x)||x<0)fail();
        if(a.laying_s>30||a.food_remainder>=1||a.water_remainder>=1||held(*e,"eggs")>300000000||e->body.alive!=(e->body.health>0))fail();
        for(double v:{e->body.hunger,e->body.thirst,e->body.fatigue,e->body.health})if(!std::isfinite(v)||v<0||v>1)fail();
        if(!a.handler.empty()&&(!find(a.handler)||find(a.handler)->kind!="actor"))fail();
        for(const auto& [person,n]:a.familiarity)if(!find(person)||find(person)->kind!="actor"||n<1||n>5||!a.last_feed.contains(person)||a.last_feed.at(person)>tick_)fail();
        for(const auto& [k,v]:e->inventory)if(k!="eggs")fail();
        total["food"]+=a.food;total["water"]+=a.water;laid+=a.laid;metabolized_food+=a.metabolized_food;metabolized_water+=a.metabolized_water;
    }
    for(const auto& e:entities_){
        if(e.kind=="animal"&&!c.animals.contains(e.id))fail();
        if(e.kind=="forage"&&(e.id!="forage-1"||e.radius||e.mass_ug>2*kg||!e.inventory.empty()))fail();
        for(const auto& [k,v]:e.inventory)if(perishable(k)&&v>0&&!c.freshness.contains({e.id,k}))fail();
    }
    for(const auto& [key,life]:c.freshness)if(!find(key.first)||!perishable(key.second)||!std::isfinite(life)||life<=0||life>(key.second=="eggs"?180:120)||held(*find(key.first),key.second)<=0)fail();
    if(total["animal_body"]!=c.body_initial||laid!=c.eggs_produced||c.egg_input/4*3!=c.eggs_produced||c.egg_input%80000000||c.eggs_produced%60000000||metabolized_water!=c.water_waste||c.food_residue<metabolized_food+c.egg_input-c.eggs_produced)fail();
    total["food"]+=total["forage"]+total["plant_food"]+total["eggs"]+c.food_residue;total["water"]+=c.water_waste;
}
}
