#pragma once
#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>

namespace uw {
struct ClimateConfig {
    bool enabled{false};
    double year_s{31557600}, transition_s{20}, change_s{90}, temperature_bias_c{0};
    void check() const;
};
struct Conditions {
    double offset{}, cloud{}, rain{}, wind_x{}, wind_y{};
};
struct SeasonState {
    std::string name; std::uint64_t year{}; double progress{}, temperature{}, daylight{}, growth{}, rain_probability{};
};
struct WeatherState {
    Conditions from{}, current{}, target{};
    double start_s{}, end_s{}, next_s{};
    std::uint64_t rng{1};
    Conditions forced_conditions{};
    double forced_until_s{}, forced_temperature_c{20};
    std::map<std::string,std::string> forcing_requests;
};
// These proxies are dimensionless; body loss ledgers are separate from needs.
struct LocalExposure {
    double wetness{}, cold{}, fatigue_added{}, health_lost{};
    std::string shelter;
};
}
