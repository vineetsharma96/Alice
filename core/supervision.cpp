#include "world.hpp"
namespace uw {
unsigned World::compact_history() {
    unsigned removed=0;
    for(auto it=requests_.begin();it!=requests_.end();) {
        const auto& a=it->second.first;const auto& r=it->second.second;
        const bool canonical=a.request_id=="utility-"+std::to_string(a.version)+"-"+a.agent_id||a.request_id=="script-"+std::to_string(a.version)+"-"+a.agent_id;
        if(canonical&&a.version<tick_&&r.status!="accepted"){it=requests_.erase(it);++removed;}else ++it;
    }
    event("history_compacted","","",std::to_string(removed));return removed;
}
}
