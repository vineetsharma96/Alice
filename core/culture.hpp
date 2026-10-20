#pragma once
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>
namespace uw {
struct Practice { unsigned successes{}; std::uint64_t last_event{}; };
struct Agreement {
    std::string id,proposer,partner,text,status{"offered"};
    std::uint64_t offered_event{},accepted_event{},completed_event{},expires_tick{};
};
struct Interaction {std::uint64_t seq{},tick{};std::string other,kind;};
struct Batch {std::uint64_t seq{},tick{};std::string agent,dial;double measured_k{},work_s{};};
struct CultureState {
    bool enabled{};std::uint64_t apparatus_seed{};double target_k{};unsigned correct_dial{};
    std::vector<std::string> dials;
    std::map<std::string,Practice> practice;
    std::map<std::string,Agreement> agreements;
    std::map<std::string,std::vector<Interaction>> interactions;
    std::vector<Batch> batches;
    std::set<std::string> departed;
};
}
