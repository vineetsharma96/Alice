#pragma once
#include "thermal.hpp"
#include "culture.hpp"
#include <cstdint>
#include <map>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace uw {
using U64 = std::uint64_t;
struct Point { double x{}, y{}; };
struct Body {
    double hunger{.35}, thirst{.4}, fatigue{.2}, health{1};
    bool alive{true};
    std::int64_t food_ingested_ug{}, water_ingested_ug{};
};
struct Entity {
    std::string id, kind;
    Point position;
    double radius{};
    std::int64_t mass_ug{};
    std::map<std::string, std::int64_t> inventory;
    Body body{};
    // Tree-only state is kept on the authoritative entity so checkpoints and
    // native observers cannot reconstruct biomass from free products.
    std::string stage{"none"};
    double health{1};
    std::int64_t biomass_ug{};
};
struct Action {
    std::string request_id, agent_id, type, target_id;
    U64 version{};
    Point destination;
    std::int64_t mass_ug{};
    double duration_s{1};
    std::string text{};
    U64 evidence_seq{};
    std::string destination_id{}, material{};
};
struct Result {
    std::string request_id, agent_id, status, error;
    U64 started{}, completed{}, version{};
    std::vector<U64> event_refs{};
    std::string effect{};
};
struct Message {
    U64 seq{}, tick{}; std::string speaker_id, text;
    U64 origin_seq{}, parent_seq{}; std::string source_id;
};
struct Book { U64 origin_seq{}; std::string text; std::string author{"book-author"}; U64 parent_seq{}; };
struct Event { U64 seq{}, tick{}; std::string type, agent_id, request_id, detail; };
struct Pending { Action action; U64 remaining{}, started{}; double exposure_s{}; };
class World {
public:
    World(U64 seed=20261019, unsigned population=8, double width=64, double height=64,
           double dt=.1, U64 interval=50, bool scripted=true, bool bodies=false,
           double food_kg=16, double water_kg=64, double food_regen_kg_s=0, double water_regen_kg_s=0,
           double tree_growth_kg_s=0);
    Result submit(const Action& action);
    std::vector<Event> step(unsigned ticks);
    std::vector<Entity> nearby(const std::string& agent_id, double range=8) const;
    std::string serialize() const;
    static World restore(const std::string& state);
    const std::vector<Entity>& entities() const { return entities_; }
    const std::map<std::string, Pending>& pending() const { return pending_; }
    const std::map<std::string, std::pair<Action,Result>>& requests() const { return requests_; }
    U64 tick() const { return tick_; }
    U64 seq() const { return seq_; }
    const std::map<std::string,U64>& event_counts() const { return event_counts_; }
    unsigned compact_history();
    U64 seed() const { return seed_; }
    double dt() const { return dt_; }
    double width() const { return width_; }
    double height() const { return height_; }
    double tree_growth_rate_kg_s() const { return tree_growth_kg_s_; }
    double energy() const { return energy_j_; }
    double solar_input() const { return solar_input_j_; }
    const ThermalModel& thermal() const { return thermal_; }
    const CultureState& culture() const { return culture_; }
    void configure_culture(U64 apparatus_seed);
    double practice_seconds(const std::string& agent) const;
    void configure_thermal(bool open,double water,double fuel,double oxygen,double temperature);
    std::string validate_thermal_action(const Entity& actor,const Action& action) const;
    bool complete_thermal_action(Entity& actor,const Action& action);
    double sunlight_w_m2() const;
    U64 next_script_tick() const { return next_script_tick_; }
    bool scripted() const { return scripted_; }
    bool bodies_enabled() const { return bodies_; }
    const std::map<std::string,std::vector<Message>>& messages() const { return messages_; }
    const std::map<std::string,std::vector<Message>>& readings() const { return readings_; }
    void configure_branch(bool guided, double hearing_range);
    U64 intervene(const std::string& id, const std::string& type, const std::string& entity_id,
                  Point position, const std::string& material, std::int64_t mass, double energy, const std::string& text);
    double hearing_range() const { return hearing_range_; }
    bool guided() const { return guided_; }
    double operator_energy() const { return operator_energy_j_; }
    const std::map<std::string,std::int64_t>& operator_mass() const { return operator_mass_; }
    const std::map<std::string,std::int64_t>& initial_mass() const { return initial_mass_; }
    const std::map<std::string,std::int64_t>& source_mass() const { return source_mass_; }
    bool visible(const std::string& observer,const std::string& target,double range=8) const;
    void check_invariants() const;
private:
    U64 seed_{}, tick_{}, seq_{}, next_id_{}, interval_{50}, next_script_tick_{};
    double width_{}, height_{}, dt_{}, energy_j_{}, solar_input_j_{};
    ThermalModel thermal_;
    CultureState culture_;
    bool scripted_{true};
    bool bodies_{};
    double food_regen_{}, water_regen_{}, food_remainder_{}, water_remainder_{};
    double tree_growth_kg_s_{}, tree_growth_remainder_ug_{};
    std::map<std::string,std::int64_t> initial_mass_, source_mass_;
    std::map<std::string,std::vector<Message>> messages_;
    std::map<std::string,std::vector<Message>> readings_;
    std::map<std::string,Book> books_;
    std::map<std::string,std::pair<std::string,U64>> interventions_;
    std::map<std::string,std::int64_t> operator_mass_{{"food",0},{"water",0},{"inert_material",0},{"fuel_X",0},{"oxygen",0},{"product_P",0},{"stone",0}};
    bool guided_{};
    double hearing_range_{6}, operator_energy_j_{};
    std::mt19937_64 rng_;
    std::vector<Entity> entities_;
    std::map<std::string, Pending> pending_;
    std::map<std::string, std::pair<Action,Result>> requests_;
    std::vector<Event> events_;
    std::map<std::string,U64> event_counts_;
    std::map<std::pair<int,int>, std::vector<std::size_t>> grid_;
    Entity* find(const std::string& id);
    const Entity* find(const std::string& id) const;
    bool clear_segment(const Entity& actor, Point to) const;
    void rebuild_grid();
    void event(std::string type, std::string agent="", std::string request="", std::string detail="");
    void finish(const std::string& agent_id, bool success, const std::string& error);
    void scripted_decisions();
    bool unobstructed(Point a, Point b, const std::string& target="") const;
    void update_bodies();
    void replenish();
    void grow_trees();
    std::string validate_body_action(const Entity& actor,const Action& action) const;
    void complete_body_action(Entity& actor,const Action& action);
    std::string validate_tree_action(const Entity& actor,const Action& action) const;
    void complete_tree_action(Entity& actor,const Action& action);
    const Message* known_report(const std::string& agent, U64 seq) const;
    std::string validate_culture_action(const Entity& actor,const Action& action) const;
    void complete_culture_action(Entity& actor,const Action& action);
    void update_culture();
    bool process_conditions(const std::string& agent,const Action& action) const;
    bool known_experience(const std::string& agent,U64 seq) const;
    void interaction(const std::string& a,const std::string& b,const std::string& kind);
    void write_culture(std::ostream& out) const;
    void read_culture(std::istream& in);
    void check_culture() const;
};
}
