#include "world.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <istream>
#include <ostream>
#include <sstream>
#include <stdexcept>

namespace uw {
namespace {
double blend(double a,double b,double t){return a+(b-a)*t;}
Conditions interpolate(const Conditions&a,const Conditions&b,double t){
    return {blend(a.offset,b.offset,t),blend(a.cloud,b.cloud,t),blend(a.rain,b.rain,t),blend(a.wind_x,b.wind_x,t),blend(a.wind_y,b.wind_y,t)};
}
void write(std::ostream&o,const Conditions&c){o<<c.offset<<' '<<c.cloud<<' '<<c.rain<<' '<<c.wind_x<<' '<<c.wind_y<<' ';}
void read(std::istream&i,Conditions&c){i>>c.offset>>c.cloud>>c.rain>>c.wind_x>>c.wind_y;}
bool valid(const Conditions&c){return std::isfinite(c.offset)&&std::abs(c.offset)<=4&&std::isfinite(c.cloud)&&c.cloud>=0&&c.cloud<=1&&std::isfinite(c.rain)&&c.rain>=0&&c.rain<=12&&std::isfinite(c.wind_x)&&std::abs(c.wind_x)<=10&&std::isfinite(c.wind_y)&&std::abs(c.wind_y)<=10;}
}
void ClimateConfig::check() const {
    if(!std::isfinite(year_s)||year_s<240||year_s>315576000||!std::isfinite(transition_s)||transition_s<1||transition_s>600||
       !std::isfinite(change_s)||change_s<transition_s||change_s>3600||!std::isfinite(temperature_bias_c)||std::abs(temperature_bias_c)>30)
        throw std::invalid_argument("INVALID_CLIMATE");
}
void World::configure_climate(const ClimateConfig& c){
    c.check();if(tick_!=0||climate_.enabled)throw std::invalid_argument("CLIMATE_REQUIRES_NEW_WORLD");
    climate_=c;weather_.rng=seed_^0x9e3779b97f4a7c15ULL;
    if(!weather_.rng)weather_.rng=1;
    weather_.next_s=c.change_s;
    if(c.enabled)for(const auto&e:entities_)if(e.kind=="actor")exposures_[e.id]={};
}
SeasonState World::season() const {
    const double years=static_cast<double>(tick_)*dt_/climate_.year_s;
    const double phase=(years-std::floor(years))*4;
    const unsigned index=std::min(3u,static_cast<unsigned>(phase));
    const double fraction=phase-index, t=fraction*fraction*(3-2*fraction);
    constexpr std::array<const char*,4> names{"spring","summer","autumn","winter"};
    constexpr std::array<double,4> temperature{12,24,11,0},daylight{.85,1,.75,.55},growth{1,.8,.35,.05},rain{.35,.15,.45,.4};
    auto value=[&](const auto& a){return blend(a[index],a[(index+1)%4],t);};
    return {names[index],static_cast<std::uint64_t>(std::floor(years)),fraction,value(temperature),value(daylight),value(growth),value(rain)};
}
const Conditions& World::conditions() const {return weather_.forced_until_s>static_cast<double>(tick_)*dt_?weather_.forced_conditions:weather_.current;}
double World::ambient_c() const {return weather_.forced_until_s>static_cast<double>(tick_)*dt_?weather_.forced_temperature_c:season().temperature+climate_.temperature_bias_c+weather_.current.offset;}
std::string World::weather_kind() const {return conditions().rain>.05?"rain":conditions().cloud>.35?"cloudy":"clear";}
void World::update_weather(){
    if(!climate_.enabled)return;
    const double now=static_cast<double>(tick_)*dt_;
    if(now>=weather_.next_s){
        auto random=[&](){auto& n=weather_.rng;n^=n>>12;n^=n<<25;n^=n>>27;return static_cast<double>((n*2685821657736338717ULL)>>11)/9007199254740992.0;};
        weather_.from=weather_.current;
        const bool rainy=random()<season().rain_probability;
        const bool cloudy=rainy||random()<.45;
        weather_.target={8*random()-4,cloudy?.5+.5*random():.25*random(),rainy?2+10*random():0,8*random()-4,8*random()-4};
        weather_.start_s=now;weather_.end_s=now+climate_.transition_s;weather_.next_s=now+climate_.change_s;
        event("weather_transition","","",weather_kind());
    }
    const double t=weather_.end_s>weather_.start_s?std::clamp((now+dt_-weather_.start_s)/(weather_.end_s-weather_.start_s),0.0,1.0):1;
    weather_.current=interpolate(weather_.from,weather_.target,t*t*(3-2*t));
}
void World::write_weather(std::ostream& out) const {
    out<<" WEATHER1 "<<climate_.enabled<<' '<<climate_.year_s<<' '<<climate_.transition_s<<' '<<climate_.change_s<<' '<<climate_.temperature_bias_c<<' ';
    write(out,weather_.from);write(out,weather_.current);write(out,weather_.target);
    out<<weather_.start_s<<' '<<weather_.end_s<<' '<<weather_.next_s<<' '<<weather_.rng<<' ';
    out<<exposures_.size()<<' ';
    for(const auto&[id,e]:exposures_)out<<std::quoted(id)<<' '<<e.wetness<<' '<<e.cold<<' '<<e.fatigue_added<<' '<<e.health_lost<<' '<<std::quoted(e.shelter)<<' ';
    write(out,weather_.forced_conditions);out<<weather_.forced_until_s<<' '<<weather_.forced_temperature_c<<' '<<weather_.forcing_requests.size()<<' ';
    for(const auto&[id,signature]:weather_.forcing_requests)out<<std::quoted(id)<<' '<<std::quoted(signature)<<' ';
}
void World::read_weather(std::istream& in){
    std::string version;in>>version;
    if(version!="WEATHER1")throw std::invalid_argument("INVALID_WEATHER_VERSION");
    in>>climate_.enabled>>climate_.year_s>>climate_.transition_s>>climate_.change_s>>climate_.temperature_bias_c;
    read(in,weather_.from);read(in,weather_.current);read(in,weather_.target);
    in>>weather_.start_s>>weather_.end_s>>weather_.next_s>>weather_.rng;
    std::size_t count=0;in>>count;if(count>64)throw std::invalid_argument("INVALID_EXPOSURE_COUNT");
    exposures_.clear();
    for(std::size_t j=0;j<count;++j){std::string id;LocalExposure e;in>>std::quoted(id)>>e.wetness>>e.cold>>e.fatigue_added>>e.health_lost>>std::quoted(e.shelter);if(!exposures_.emplace(id,e).second)throw std::invalid_argument("DUPLICATE_EXPOSURE");}
    read(in,weather_.forced_conditions);in>>weather_.forced_until_s>>weather_.forced_temperature_c>>count;
    if(count>128)throw std::invalid_argument("FORCING_BUDGET");weather_.forcing_requests.clear();
    for(std::size_t j=0;j<count;++j){std::string id,signature;in>>std::quoted(id)>>std::quoted(signature);if(id.size()>128||signature.size()>512||!weather_.forcing_requests.emplace(id,signature).second)throw std::invalid_argument("INVALID_FORCING_HISTORY");}
}
void World::check_weather() const {
    climate_.check();
    if(!valid(weather_.forced_conditions)||!std::isfinite(weather_.forced_until_s)||weather_.forced_until_s<0||
       !std::isfinite(weather_.forced_temperature_c)||weather_.forced_temperature_c< -40||weather_.forced_temperature_c>50||weather_.forcing_requests.size()>128)
        throw std::invalid_argument("INVALID_FORCING_STATE");
    if(!valid(weather_.from)||!valid(weather_.current)||!valid(weather_.target)||!weather_.rng||
       !std::isfinite(weather_.start_s)||weather_.start_s<0||!std::isfinite(weather_.end_s)||weather_.end_s<weather_.start_s||
       !std::isfinite(weather_.next_s)||weather_.next_s<0)
        throw std::invalid_argument("INVALID_WEATHER_STATE");
    for(const auto&[id,e]:exposures_){
        const auto actor=find(id);
        if(!climate_.enabled||!actor||actor->kind!="actor")throw std::invalid_argument("INVALID_EXPOSURE_OWNER");
        for(double v:{e.wetness,e.cold})if(!std::isfinite(v)||v<0||v>1)throw std::invalid_argument("INVALID_EXPOSURE_PROXY");
        for(double v:{e.fatigue_added,e.health_lost})if(!std::isfinite(v)||v<0)throw std::invalid_argument("INVALID_EXPOSURE_LEDGER");
    }
    if(climate_.enabled)for(const auto&e:entities_)if(e.kind=="actor"&&!exposures_.contains(e.id))throw std::invalid_argument("MISSING_EXPOSURE");
    for(const auto&e:entities_)if(e.kind=="lean_to"){
        auto wood=e.composition.find("wood"),fiber=e.composition.find("fiber");
        if(!climate_.enabled||e.radius!=0||!std::isfinite(e.health)||e.health<0||e.health>1||std::abs(e.work_s-12)>1e-9||e.composition.size()!=2||
           wood==e.composition.end()||wood->second<800000000||fiber==e.composition.end()||fiber->second!=100000000)
            throw std::invalid_argument("INVALID_SHELTER");
    }
}
void World::update_exposure(){
    if(!climate_.enabled||!bodies_)return;
    // Body updates follow ++tick. Apply forcing to the interval that just
    // elapsed, including its final full tick, rather than expiring it early.
    const bool forced=weather_.forced_until_s>static_cast<double>(tick_-1)*dt_;
    const auto&felt=forced?weather_.forced_conditions:weather_.current;
    const double temperature=forced?weather_.forced_temperature_c:ambient_c();
    const double rain=felt.rain/12;
    const double wind=std::min(1.0,std::hypot(felt.wind_x,felt.wind_y)/8);
    for(auto&actor:entities_)if(actor.kind=="actor"&&actor.body.alive&&!culture_.departed.contains(actor.id)){
        auto&e=exposures_.at(actor.id);
        const auto shelter=protective_shelter(actor);const double condition=shelter?shelter->health:0;
        e.shelter=shelter?shelter->id:"";
        const double local_rain=rain*(1-.9*condition),local_wind=wind*(1-.5*condition);
        e.wetness=std::clamp(e.wetness+(.012*local_rain-.004*(1-local_rain))*dt_,0.0,1.0);
        const double drive=std::clamp(std::clamp((10-temperature)/20,0.0,1.0)*(1+.5*e.wetness)*(.8+.2*local_wind)*(1-.3*condition),0.0,1.0);
        e.cold=std::clamp(e.cold+std::clamp(drive-e.cold,-.006*dt_,.012*dt_),0.0,1.0);
        const double fatigue=std::min(1-actor.body.fatigue,.0015*e.cold*dt_);
        actor.body.fatigue+=fatigue;e.fatigue_added+=fatigue;
        const double loss=std::min(actor.body.health,.0015*std::max(0.0,(e.cold-.65)/.35)*dt_);
        actor.body.health-=loss;e.health_lost+=loss;
        if(loss>0)event("environmental_health_loss",actor.id,"",std::to_string(loss));
        if(actor.body.health==0){
            actor.body.alive=false;
            auto pending=pending_.find(actor.id);
            if(pending!=pending_.end()&&pending->second.remaining){finish(actor.id,false,"DEAD");pending->second.remaining=0;}
            event("death",actor.id,"","environmental_exposure");
        }
    }
    for(auto&e:entities_)if(e.kind=="lean_to")e.health=std::max(0.0,e.health-.00002*dt_);
}
bool World::shelter_site_clear(Point p) const {
    constexpr double roof=1.1;
    if(p.x<roof||p.y<roof||p.x>width_-roof||p.y>height_-roof)return false;
    for(const auto&e:entities_){
        const bool site=e.kind=="lean_to"||(e.kind=="construction"&&e.recipe_id=="lean_to");
        const double radius=site?roof:(e.kind=="gate"?.5:e.radius);
        if((radius>0||e.kind=="gate")&&std::hypot(p.x-e.position.x,p.y-e.position.y)<roof+radius-1e-12)return false;
    }
    return true;
}
const Entity* World::protective_shelter(const Entity&actor) const {
    for(const auto&s:entities_)if(s.kind=="lean_to"&&s.health>0&&std::hypot(actor.position.x-s.position.x,actor.position.y-s.position.y)+actor.radius<=1.1+1e-12){
        unsigned rank=0;
        for(const auto&e:entities_)if(e.kind=="actor"&&e.body.alive&&!culture_.departed.contains(e.id)&&e.id<=actor.id&&std::hypot(e.position.x-s.position.x,e.position.y-s.position.y)+e.radius<=1.1+1e-12)++rank;
        if(rank<=4)return &s;
    }
    return nullptr;
}
void World::force_weather(const std::string&id,U64 version,const Conditions&c,double temperature,double duration){
    if(!guided_||!climate_.enabled)throw std::invalid_argument("GUIDED_WEATHER_ONLY");
    if(id.empty()||id.size()>128||!std::all_of(id.begin(),id.end(),[](unsigned char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-';})||
       !valid(c)||!std::isfinite(temperature)||temperature< -40||temperature>50||!std::isfinite(duration)||duration<1||duration>3600)
        throw std::invalid_argument("INVALID_FORCED_WEATHER");
    std::ostringstream signature;signature<<std::setprecision(17)<<version<<' ';write(signature,c);signature<<temperature<<' '<<duration;
    const auto prior=weather_.forcing_requests.find(id);
    if(prior!=weather_.forcing_requests.end()){
        if(prior->second!=signature.str())throw std::invalid_argument("REQUEST_ID_CONFLICT");return;
    }
    if(version!=tick_)throw std::invalid_argument("STALE_OBSERVATION");
    if(weather_.forcing_requests.size()>=128)throw std::invalid_argument("FORCING_BUDGET");
    const double until=static_cast<double>(tick_)*dt_+duration;
    if(until<=static_cast<double>(tick_)*dt_)throw std::invalid_argument("FORCING_TIME_OVERFLOW");
    weather_.forced_conditions=c;weather_.forced_until_s=until;weather_.forced_temperature_c=temperature;
    weather_.forcing_requests.emplace(id,signature.str());
    event("operator_weather_forced","operator",id,signature.str());
}
}
