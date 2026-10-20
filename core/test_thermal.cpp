#include "thermal.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
void require(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
void near(double a,double b,double tolerance=1e-6){require(std::abs(a-b)<=tolerance,"thermal analytical mismatch");}
int main(){try {
    uw::ThermalCell c;c.water=20000000;
    c.enthalpy=c.energy_at(260);near(c.phase().temperature,260);near(c.phase().ice_fraction,1);
    const double melt=(c.dry_capacity()+.02*2090)*273.15;
    c.enthalpy=melt+.02*334000*.4;near(c.phase().temperature,273.15);near(c.phase().liquid_fraction,.4);
    c.enthalpy=melt+.02*334000+(c.dry_capacity()+.02*4186)*100+.02*2256000*.6;
    near(c.phase().temperature,373.15);near(c.phase().vapor_fraction,.6);
    require(c.phase_masses()[1]+c.phase_masses()[2]==c.water,"phase mass partition");
    c.enthalpy=c.energy_at(450);near(c.phase().temperature,450);near(c.phase().vapor_fraction,1);
    uw::ThermalModel box;box.initialize(false,.02,.02,.01,293.15);box.cells[0].heater="burn";
    double background=0;for(unsigned i=0;i<2000;++i)box.step(.1,0,background);
    require(box.burned_fuel==5000000&&box.cells[0].oxygen==0&&box.cells[0].product==15000000,"oxygen/stoichiometry");
    near(box.stored_energy(),box.initial_energy,1e-5);require(box.cells[1].phase().temperature>293.15,"neighbor heat transfer");
    const double before=box.stored_energy();box.transfer(0,1,"water",10000000);near(before,box.stored_energy());box.check();
    uw::ThermalModel cap;cap.initialize(false,0,0,0,293.15);cap.cells[0].heater="electric";
    for(unsigned i=0;i<5000;++i)cap.step(1,0,background);
    require(cap.cells[0].phase().temperature<=1000.00000001,"thermostat runaway");cap.check();
    std::cout<<"analytical phases, latent heat, oxygen, conduction, transfer and thermostat passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
