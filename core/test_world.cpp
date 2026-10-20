#include "world.hpp"
#include <iostream>
#include <stdexcept>

void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
int main() {
    try {
        uw::World a,b;
        a.step(123);b.step(123);
        require(a.serialize()==b.serialize(),"same seed diverged");
        auto resumed=uw::World::restore(a.serialize());
        a.step(321);resumed.step(321);
        require(a.serialize()==resumed.serialize(),"resume diverged");
        a.check_invariants();
        uw::World transfer(1,1,64,64,.1,50,false);
        uw::Action gather{"test","agent-1","gather","resource-1",0,{},1000000000,1};
        require(transfer.submit(gather).status=="accepted","gather rejected");
        transfer.step(10);transfer.check_invariants();
        auto before=transfer.serialize();
        require(transfer.submit(gather).status=="completed","idempotent request lost");
        require(before==transfer.serialize(),"duplicate request mutated state");
        std::cout<<"native deterministic/restart/transfer invariants passed\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
