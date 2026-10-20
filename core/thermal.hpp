#pragma once
#include <array>
#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>

namespace uw {
struct PhaseState { double temperature{}, ice_fraction{}, liquid_fraction{}, vapor_fraction{}; };
struct ThermalCell {
    std::int64_t water{}, fuel{}, oxygen{}, product{};
    double enthalpy{}, burn_remainder{}, vent_remainder{};
    std::string heater{"off"};
    double dry_capacity() const;
    double energy_at(double temperature) const;
    PhaseState phase() const;
    std::array<std::int64_t,3> phase_masses() const;
};
class ThermalModel {
public:
    static constexpr double max_temperature=1000, chemical_j_kg=1e6, ambient_capacity=10000;
    bool enabled{}, open_boundaries{};
    std::array<ThermalCell,4> cells{};
    double ambient_enthalpy{}, initial_energy{}, heater_input{}, radiation_in{}, radiation_out{},
           outflow_energy{}, solar_transferred{};
    std::int64_t burned_fuel{}, outflow_water{};
    void initialize(bool open,double water_kg,double fuel_kg,double oxygen_kg,double temperature);
    void step(double dt,double sunlight_w,double& background_energy);
    void transfer(unsigned source,unsigned destination,const std::string& material,std::int64_t amount);
    std::int64_t available(unsigned cell,const std::string& material) const;
    std::map<std::string,std::int64_t> masses() const;
    double stored_energy() const;
    double balance_error() const;
    void check() const;
    void write(std::ostream& out) const;
    void read(std::istream& in);
};
}
