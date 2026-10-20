#include <charconv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <locale>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {
constexpr unsigned population_ceiling = 64; // Allocation guard, not a performance claim.
template <typename T> T number(std::string_view value) {
    T result{};
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), result);
    if (error != std::errc{} || end != value.data() + value.size())
        throw std::invalid_argument("invalid numeric argument");
    return result;
}
}

int main(int argc, char** argv) {
    try {
        std::uint64_t seed = 20261019;
        unsigned population = 8;
        double width = 64.0, height = 64.0, dt = 0.1;
        for (int i = 1; i < argc; i += 2) {
            if (i + 1 >= argc) throw std::invalid_argument("option requires a value");
            const std::string_view option{argv[i]}, value{argv[i + 1]};
            if (option == "--seed") seed = number<std::uint64_t>(value);
            else if (option == "--population") population = number<unsigned>(value);
            else if (option == "--width-m") width = number<double>(value);
            else if (option == "--height-m") height = number<double>(value);
            else if (option == "--dt-s") dt = number<double>(value);
            else throw std::invalid_argument("unknown option");
        }
        if (population == 0 || population > population_ceiling)
            throw std::invalid_argument("population must be in [1,64]");
        if (!std::isfinite(width) || !std::isfinite(height) || width < 8 || height < 8 || width > 1024 || height > 1024)
            throw std::invalid_argument("world dimensions must be finite and in [8,1024] metres");
        if (!std::isfinite(dt) || dt < 0.01 || dt > 1)
            throw std::invalid_argument("dt must be finite and in [0.01,1] seconds");
        std::mt19937_64 rng(seed);
        const auto coordinate = [&rng](double extent) {
            return 1.0 + static_cast<double>(rng() >> 11) * (1.0 / 9007199254740992.0) * (extent - 2.0);
        };
        std::cout.imbue(std::locale::classic());
        std::cout << std::setprecision(17)
                  << "{\"schema_version\":1,\"kind\":\"initial_scene\",\"phase\":0,"
                  << "\"seed\":\"" << seed << "\",\"tick\":0,\"observation_version\":0,"
                  << "\"simulated_time_s\":0,\"dt_s\":" << dt
                  << ",\"world_bounds_m\":{\"width\":" << width << ",\"height\":" << height << "},"
                  << "\"entities\":[";
        for (unsigned i = 0; i < population; ++i) {
            if (i) std::cout << ',';
            std::cout << "{\"entity_id\":\"agent-" << (i + 1)
                      << "\",\"kind\":\"inhabitant_seed\",\"position_m\":["
                      << coordinate(width) << ',' << coordinate(height) << "]}";
        }
        std::cout << ",{\"entity_id\":\"resource-1\",\"kind\":\"food\",\"position_m\":[2,2],\"mass_kg\":16},"
                  << "{\"entity_id\":\"resource-2\",\"kind\":\"water\",\"position_m\":[3,2],\"mass_kg\":64},"
                  << "{\"entity_id\":\"resource-3\",\"kind\":\"inert_material\",\"position_m\":[4,2],\"mass_kg\":32}],"
                  << "\"capabilities\":[\"scene_initialization\"],\"cognition\":\"not_implemented\"}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "INVALID_ARGUMENT: " << error.what() << '\n';
        return 2;
    }
}
