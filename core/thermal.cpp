#include "thermal.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <istream>
#include <ostream>
#include <stdexcept>

namespace uw {
namespace {
constexpr double kg=1e9, ci=2090, cl=4186, cv=2020, tm=273.15, tb=373.15,
                 fusion=334000, vaporization=2256000, sigma=5.67e-8;
constexpr std::int64_t structure=100000000; // .1 kg fixed inert vessel, cp=500 J/kg/K.
double water_energy(double t) {
    if(t<tm)return ci*t;
    if(t<tb)return ci*tm+fusion+cl*(t-tm);
    return ci*tm+fusion+cl*(tb-tm)+vaporization+cv*(t-tb);
}
std::int64_t micrograms(double value) {
    if(!std::isfinite(value)||value<0||value>.05)throw std::invalid_argument("thermal stock must be 0..0.05 kg per cell");
    return static_cast<std::int64_t>(std::llround(value*kg));
}
}
double ThermalCell::dry_capacity() const {return 50+(fuel+oxygen+product)/kg*1000;}
double ThermalCell::energy_at(double t) const {return dry_capacity()*t+water/kg*water_energy(t);}
PhaseState ThermalCell::phase() const {
    const double c=dry_capacity(),m=water/kg;
    if(m==0)return {enthalpy/c,0,0,0};
    const double melt=(c+m*ci)*tm,melted=melt+m*fusion;
    const double boil=melted+(c+m*cl)*(tb-tm),boiled=boil+m*vaporization;
    if(enthalpy<melt)return {enthalpy/(c+m*ci),1,0,0};
    if(enthalpy<melted){double f=(enthalpy-melt)/(m*fusion);return {tm,1-f,f,0};}
    if(enthalpy<boil)return {tm+(enthalpy-melted)/(c+m*cl),0,1,0};
    if(enthalpy<boiled){double f=(enthalpy-boil)/(m*vaporization);return {tb,0,1-f,f};}
    return {tb+(enthalpy-boiled)/(c+m*cv),0,0,1};
}
std::array<std::int64_t,3> ThermalCell::phase_masses() const {
    const auto p=phase();
    const auto ice=std::clamp(static_cast<std::int64_t>(std::llround(water*p.ice_fraction)),std::int64_t{0},water);
    const auto vapor=std::clamp(static_cast<std::int64_t>(std::llround(water*p.vapor_fraction)),std::int64_t{0},water-ice);
    return {ice,water-ice-vapor,vapor};
}
void ThermalModel::initialize(bool open,double water,double fuel,double oxygen,double temperature) {
    if(enabled||!std::isfinite(temperature)||temperature<250||temperature>500)throw std::invalid_argument("invalid thermal initialization");
    // Validate all initial quantities before mutating state.
    const auto w=micrograms(water),f=micrograms(fuel),o=micrograms(oxygen);
    enabled=true;open_boundaries=open;ambient_enthalpy=ambient_capacity*temperature;
    for(auto& c:cells){c.water=w;c.fuel=f;c.oxygen=o;c.enthalpy=c.energy_at(temperature);}
    initial_energy=stored_energy();check();
}
std::map<std::string,std::int64_t> ThermalModel::masses() const {
    std::map<std::string,std::int64_t> m{{"water",0},{"inert_material",0},{"fuel_X",0},{"oxygen",0},{"product_P",0}};
    if(!enabled)return m;
    m["inert_material"]=20000000000LL+4*structure; // 20 kg environmental substrate + vessels.
    for(const auto& c:cells){m["water"]+=c.water;m["fuel_X"]+=c.fuel;m["oxygen"]+=c.oxygen;m["product_P"]+=c.product;}
    return m;
}
double ThermalModel::stored_energy() const {
    if(!enabled)return 0;
    double e=ambient_enthalpy;
    for(const auto& c:cells)e+=c.enthalpy+c.fuel/kg*chemical_j_kg;
    return e;
}
double ThermalModel::balance_error() const {
    return stored_energy()-(initial_energy+heater_input+radiation_in-radiation_out-outflow_energy+solar_transferred);
}
void ThermalModel::step(double dt,double sunlight_w,double& background) {
    if(!enabled)return;
    if(!std::isfinite(dt)||dt<=0||dt>1||!std::isfinite(sunlight_w)||sunlight_w<0)throw std::invalid_argument("invalid thermal timestep/input");
    const unsigned count=static_cast<unsigned>(std::ceil(dt/.05-1e-12));
    const double h=dt/count;
    for(unsigned step=0;step<count;++step) {
        for(auto& c:cells) {
            if(c.heater=="electric") {
                double q=std::min(1000*h,std::max(0.,c.energy_at(max_temperature)-c.enthalpy));
                c.enthalpy+=q;heater_input+=q;
            } else if(c.heater=="burn") {
                c.burn_remainder+=500000*h; // Artificial pilot-enabled burn, .0005 kg/s.
                auto quota=static_cast<std::int64_t>(std::floor(c.burn_remainder));
                c.burn_remainder-=quota;
                auto room=static_cast<std::int64_t>(std::floor(std::max(0.,c.energy_at(max_temperature)-c.enthalpy)/chemical_j_kg*kg));
                auto amount=std::min({quota,c.fuel,c.oxygen/2,room});
                c.fuel-=amount;c.oxygen-=2*amount;c.product+=3*amount;burned_fuel+=amount;
                c.enthalpy+=amount/kg*chemical_j_kg;
            }
        }
        // Simultaneous pair fluxes: each internal joule is debited and credited once.
        std::array<double,5> t{},delta{};
        for(unsigned i=0;i<4;++i)t[i]=cells[i].phase().temperature;
        t[4]=ambient_enthalpy/ambient_capacity;
        auto exchange=[&](unsigned a,unsigned b,double conductance){double q=conductance*(t[a]-t[b])*h;delta[a]-=q;delta[b]+=q;};
        for(unsigned i=0;i<4;++i)exchange(i,4,2);
        for(auto edge:{std::pair{0u,1u},std::pair{0u,2u},std::pair{1u,3u},std::pair{2u,3u}})exchange(edge.first,edge.second,.5);
        for(unsigned i=0;i<4;++i)cells[i].enthalpy+=delta[i];
        ambient_enthalpy+=delta[4];
        if(open_boundaries) {
            // A one-square-metre collector moves already-accounted world sunlight, never duplicates it.
            double solar=std::min({sunlight_w*h,background,std::max(0.,ambient_capacity*max_temperature-ambient_enthalpy)});
            background-=solar;ambient_enthalpy+=solar;solar_transferred+=solar;
            const double ambient=ambient_enthalpy/ambient_capacity;
            double radiation=.8*.5*sigma*(std::pow(ambient,4)-std::pow(293.15,4))*h;
            if(radiation>=0){radiation=std::min(radiation,ambient_enthalpy);ambient_enthalpy-=radiation;radiation_out+=radiation;}
            else {double q=std::min(-radiation,std::max(0.,ambient_capacity*max_temperature-ambient_enthalpy));ambient_enthalpy+=q;radiation_in+=q;}
            for(auto& c:cells) {
                c.vent_remainder+=100000*h; // .0001 kg/s per outlet, vapor only.
                auto quota=static_cast<std::int64_t>(std::floor(c.vent_remainder));c.vent_remainder-=quota;
                const auto p=c.phase();auto vapor=c.phase_masses()[2];auto amount=std::min(vapor,quota);
                double q=std::min(c.enthalpy,amount/kg*water_energy(std::max(tb,p.temperature)));
                c.water-=amount;c.enthalpy-=q;outflow_water+=amount;outflow_energy+=q;
            }
        }
    }
    check();
}
std::int64_t ThermalModel::available(unsigned cell,const std::string& material) const {
    if(!enabled||cell>=4)return -1;
    const auto& c=cells[cell];
    if(material=="water")return c.water;
    if(material=="fuel_X")return c.fuel;
    if(material=="oxygen")return c.oxygen;
    if(material=="product_P")return c.product;
    return -1;
}
void ThermalModel::transfer(unsigned source,unsigned destination,const std::string& material,std::int64_t amount) {
    if(source==destination||destination>=4||amount<=0||available(source,material)<amount)throw std::invalid_argument("invalid thermal material transfer");
    auto& a=cells[source];auto& b=cells[destination];const auto phase=a.phase();
    double specific=material=="water"?(a.enthalpy-a.dry_capacity()*phase.temperature)/(a.water/kg):1000*phase.temperature;
    double q=std::clamp(amount/kg*specific,0.,a.enthalpy);
    auto field=[&](ThermalCell& c)->std::int64_t&{if(material=="water")return c.water;if(material=="fuel_X")return c.fuel;if(material=="oxygen")return c.oxygen;return c.product;};
    field(a)-=amount;field(b)+=amount;a.enthalpy-=q;b.enthalpy+=q;check();
}
void ThermalModel::check() const {
    if(!enabled) {
        if(open_boundaries||ambient_enthalpy||initial_energy||heater_input||radiation_in||radiation_out||outflow_energy||solar_transferred||burned_fuel||outflow_water)
            throw std::invalid_argument("inactive thermal ledger is not empty");
        for(const auto& c:cells)if(c.water||c.fuel||c.oxygen||c.product||c.enthalpy||c.burn_remainder||c.vent_remainder||c.heater!="off")
            throw std::invalid_argument("inactive thermal cell is not empty");
        return;
    }
    for(double v:{ambient_enthalpy,initial_energy,heater_input,radiation_in,radiation_out,outflow_energy,solar_transferred})
        if(!std::isfinite(v)||v<0)throw std::invalid_argument("invalid thermal energy ledger");
    if(ambient_enthalpy/ambient_capacity>max_temperature+1e-8||burned_fuel<0||outflow_water<0)throw std::invalid_argument("invalid thermal environment");
    for(const auto& c:cells) {
        for(auto m:{c.water,c.fuel,c.oxygen,c.product})if(m<0||m>1000000000LL)throw std::invalid_argument("invalid thermal species mass");
        if(!std::isfinite(c.enthalpy)||c.enthalpy<0||!std::isfinite(c.phase().temperature)||c.phase().temperature>max_temperature+1e-8||
           !std::isfinite(c.burn_remainder)||c.burn_remainder<0||c.burn_remainder>=1||!std::isfinite(c.vent_remainder)||c.vent_remainder<0||c.vent_remainder>=1||
           (c.heater!="off"&&c.heater!="electric"&&c.heater!="burn"))throw std::invalid_argument("invalid thermal cell");
    }
    if(std::abs(balance_error())>std::max(1e-5,1e-10*(initial_energy+heater_input+solar_transferred+radiation_in)))
        throw std::invalid_argument("thermal energy balance invariant failed");
}
void ThermalModel::write(std::ostream& out) const {
    out<<enabled<<' '<<open_boundaries<<' '<<ambient_enthalpy<<' '<<initial_energy<<' '<<heater_input<<' '<<radiation_in<<' '<<radiation_out<<' '
       <<outflow_energy<<' '<<solar_transferred<<' '<<burned_fuel<<' '<<outflow_water<<'\n';
    for(const auto& c:cells)out<<c.water<<' '<<c.fuel<<' '<<c.oxygen<<' '<<c.product<<' '<<c.enthalpy<<' '<<c.burn_remainder<<' '<<c.vent_remainder<<' '<<std::quoted(c.heater)<<'\n';
}
void ThermalModel::read(std::istream& in) {
    in>>enabled>>open_boundaries>>ambient_enthalpy>>initial_energy>>heater_input>>radiation_in>>radiation_out>>outflow_energy>>solar_transferred>>burned_fuel>>outflow_water;
    for(auto& c:cells)in>>c.water>>c.fuel>>c.oxygen>>c.product>>c.enthalpy>>c.burn_remainder>>c.vent_remainder>>std::quoted(c.heater);
    if(!in)throw std::invalid_argument("truncated thermal checkpoint");
    check();
}
}
