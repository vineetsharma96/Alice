#include "world.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
const uw::Entity& entity(const uw::World& world,const std::string& id) {
    const auto it=std::find_if(world.entities().begin(),world.entities().end(),[&](const auto& e){return e.id==id;});
    if(it==world.entities().end())throw std::runtime_error("missing entity");
    return *it;
}
void move_to(uw::World& world,const std::string& agent,uw::Point destination,const std::string& request_id) {
    const auto& actor=entity(world,agent);
    const double distance=std::hypot(actor.position.x-destination.x,actor.position.y-destination.y);
    uw::Action move{request_id,agent,"move","",world.tick(),destination,0,std::max(1.0,distance+1)};
    const auto result=world.submit(move);
    require(result.status=="accepted","tree test move rejected");
    world.step(static_cast<unsigned>(std::ceil(move.duration_s/world.dt()))+1);
    const auto found=world.requests().find(agent+":"+request_id);
    if(found==world.requests().end()||found->second.second.status!="completed") {
        throw std::runtime_error("tree test move failed: "+(found==world.requests().end()?std::string("missing"):found->second.second.status+":"+found->second.second.error));
    }
}
uw::World relocate_actor(uw::World world,const std::string& id,uw::Point position) {
    std::ostringstream old,new_value;
    old<<std::quoted(id)<<" "<<std::quoted("actor")<<' '<<std::setprecision(17)<<entity(world,id).position.x<<' '<<entity(world,id).position.y<<' ';
    new_value<<std::quoted(id)<<" "<<std::quoted("actor")<<' '<<std::setprecision(17)<<position.x<<' '<<position.y<<' ';
    auto state=world.serialize();const auto offset=state.find(old.str());
    if(offset==std::string::npos)throw std::runtime_error("actor checkpoint relocation failed");
    state.replace(offset,old.str().size(),new_value.str());
    return uw::World::restore(state);
}
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

        uw::World trees(7,1,8,8,1,50,false,false,16,64,0,0,0);
        require(entity(trees,"tree-1").stage=="young","young tree missing");
        require(entity(trees,"tree-2").stage=="mature","mature tree missing");
        move_to(trees,"agent-1",{2,5},"tree-approach");
        uw::Action inspect{"tree-inspect","agent-1","inspect_tree","tree-1",trees.tick(),{},0,.2};
        require(trees.submit(inspect).status=="accepted","tree inspection rejected");trees.step(1);
        require(trees.requests().at("agent-1:tree-inspect").second.effect.find("stage=young")!=std::string::npos,"tree inspection omitted stage");
        const auto before_branch=entity(trees,"tree-1").biomass_ug;
        uw::Action branch{"tree-branch","agent-1","harvest_branch","tree-1",trees.tick(),{1.2,6},1000000000,1};
        require(trees.submit(branch).status=="accepted","branch harvest rejected");trees.step(1);
        require(entity(trees,"tree-1").biomass_ug==before_branch-1000000000,"branch biomass not transferred");
        const auto wood=std::find_if(trees.entities().begin(),trees.entities().end(),[](const auto& e){return e.kind=="wood"&&e.mass_ug>0;});
        const auto fiber=std::find_if(trees.entities().begin(),trees.entities().end(),[](const auto& e){return e.kind=="fiber"&&e.mass_ug>0;});
        require(wood!=trees.entities().end()&&fiber!=trees.entities().end(),"branch products missing");
        require(wood->mass_ug==900000000&&fiber->mass_ug==100000000,"branch split incorrect");
        uw::Action collect{"wood-collect","agent-1","collect_wood",wood->id,trees.tick(),{},wood->mass_ug,1,"",0,"",wood->kind};
        require(trees.submit(collect).status=="accepted","wood collection rejected");
        trees.step(1);
        require(entity(trees,"agent-1").inventory.at("wood")==900000000,"wood collection mass incorrect");
        trees.check_invariants();

        uw::World blocked(8,1,8,8,1,50,false,false,16,64,0,0,0);
        move_to(blocked,"agent-1",{2,5},"blocked-approach");
        const auto blocked_biomass=entity(blocked,"tree-1").biomass_ug;
        uw::Action blocked_harvest{"blocked-harvest","agent-1","harvest_branch","tree-1",blocked.tick(),{2,6},1000000000,1};
        require(blocked.submit(blocked_harvest).status=="accepted","blocked harvest did not queue");blocked.step(1);
        require(blocked.requests().at("agent-1:blocked-harvest").second.status=="failed","occupied pile placement succeeded");
        require(blocked.requests().at("agent-1:blocked-harvest").second.error=="NO_PLACEMENT","wrong occupied placement error");
        require(entity(blocked,"tree-1").biomass_ug==blocked_biomass,"failed harvest changed biomass");
        require(std::none_of(blocked.entities().begin(),blocked.entities().end(),[](const auto& e){return e.kind=="wood"||e.kind=="fiber";}),"failed harvest created free product");

        uw::World capacity(9,1,8,8,1,50,false,false,16,64,0,0,0);
        move_to(capacity,"agent-1",{2,2},"food-approach");
        uw::Action gather_food{"food-load","agent-1","gather","resource-1",capacity.tick(),{},1500000000,1};
        require(capacity.submit(gather_food).status=="accepted","capacity setup gather rejected");capacity.step(1);
        move_to(capacity,"agent-1",{2,5},"capacity-tree-approach");
        uw::Action capacity_branch{"capacity-branch","agent-1","harvest_branch","tree-1",capacity.tick(),{1.2,6},1000000000,1};
        require(capacity.submit(capacity_branch).status=="accepted","capacity branch rejected");capacity.step(1);
        const auto capacity_wood=std::find_if(capacity.entities().begin(),capacity.entities().end(),[](const auto& e){return e.kind=="wood"&&e.mass_ug>0;});
        require(capacity_wood!=capacity.entities().end(),"capacity wood pile missing");
        uw::Action over_capacity{"over-capacity","agent-1","collect_wood",capacity_wood->id,capacity.tick(),{},capacity_wood->mass_ug,1,"",0,"",capacity_wood->kind};
        require(capacity.submit(over_capacity).status=="rejected"&&capacity.submit(over_capacity).error=="CAPACITY_EXCEEDED","inventory capacity not enforced");

        uw::World fell(10,1,8,8,1,50,false,false,16,64,0,0,0);
        move_to(fell,"agent-1",{5,1},"fell-approach");
        uw::Action fell_action{"fell","agent-1","fell_tree","tree-2",fell.tick(),{},0,5};
        require(fell.submit(fell_action).error=="MISSING_TOOL","felling without axe accepted");
        require(entity(fell,"tree-2").biomass_ug==8000000000LL,"rejected felling removed biomass");
        fell.check_invariants();

        uw::World growth(11,1,8,8,1,50,false,false,16,64,0,0,.01);
        const auto initial_tree_mass=growth.initial_mass().at("tree");
        growth.step(600);
        require(entity(growth,"tree-1").stage=="mature","young growth did not mature deterministically");
        require(growth.source_mass().at("tree")==6000000000LL,"growth source ledger incorrect");
        require(growth.initial_mass().at("tree")+growth.source_mass().at("tree")==initial_tree_mass+6000000000LL,"growth ledger changed initial mass");
        const auto source_after_maturity=growth.source_mass().at("tree");growth.step(2);
        require(growth.source_mass().at("tree")==source_after_maturity,"mature tree grew");
        auto resumed_growth=uw::World::restore(growth.serialize());growth.step(4);resumed_growth.step(4);
        require(growth.serialize()==resumed_growth.serialize(),"tree growth restart diverged");

        auto race=relocate_actor(uw::World(12,2,8,8,1,50,false,false,16,64,0,0,0),"agent-1",{2,5});
        race=relocate_actor(std::move(race),"agent-2",{3,5.5});
        uw::Action race_a{"race-a","agent-1","harvest_branch","tree-1",race.tick(),{},2000000000,1};
        uw::Action race_b{"race-b","agent-2","harvest_branch","tree-1",race.tick(),{},2000000000,1};
        require(race.submit(race_a).status=="accepted"&&race.submit(race_b).status=="accepted","competing harvest rejected early");race.step(1);
        const auto& result_a=race.requests().at("agent-1:race-a").second;const auto& result_b=race.requests().at("agent-2:race-b").second;
        require((result_a.status=="completed")!=(result_b.status=="completed"),"competing harvesters both completed");
        require(entity(race,"tree-1").stage=="stump","competing harvest did not deplete once");
        require(std::count_if(race.entities().begin(),race.entities().end(),[](const auto& e){return e.kind=="wood"||e.kind=="fiber";})==2,"competing harvest duplicated products");
        race.check_invariants();

        auto checkpoint=trees.serialize();require(checkpoint.rfind("UW9 ",0)==0,"new checkpoint version missing");
        auto old_checkpoint=checkpoint;old_checkpoint.replace(0,3,"UW7");
        bool rejected_old=false;try {static_cast<void>(uw::World::restore(old_checkpoint));}catch(const std::invalid_argument&){rejected_old=true;}
        require(rejected_old,"old UW7 checkpoint migrated silently");
        std::cout<<"native deterministic/restart/transfer invariants passed\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
