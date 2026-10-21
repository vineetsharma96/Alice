"""Separate prospective development diagnostic; never included in promotion scores."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import developmental as dev, storage  # noqa: E402
from developmental_study import introduce  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();start=time.perf_counter()
    dev.initialize(args.db,seed=41,population=1)
    introduce(args.db,'reachable','food',.05,[1,3])
    introduce(args.db,'ambiguous-range','food',.05,[3.6,3])
    training=[dev.execute(args.db,'agent-1','gather',['reachable'],{'mass_kg':.001},learn_food=True) for _ in range(3)]
    trials=[]
    for _ in range(5):
        if time.perf_counter()-start>60:raise TimeoutError('diagnostic compute cap')
        decision=dev.choose(args.db,'agent-1',['ambiguous-range'])
        result=(dev.execute(args.db,'agent-1','gather',[decision['target']],{'mass_kg':.001},learn_food=True,prediction=decision)
                if decision['target'] else dev.execute(args.db,'agent-1','rest',update_memory=False))
        trials.append({'decision':decision,'experience':result})
    final=dev.choose(args.db,'agent-1',['reachable'])
    authored=dev.execute(args.db,'agent-1','gather',['reachable'],{'mass_kg':.001},update_memory=False)
    missed=final['target'] is None and authored['goal_success']
    report={'seed':41,'split':'separate_online_development_diagnostic','training':training,'trials':trials,
            'final_reachable_decision':final,'authored_feasibility_probe':authored,
            'missed_feasible_opportunity':missed,'wall_s':time.perf_counter()-start,
            'snapshot':storage.inspect(args.db),'replay':storage.replay(args.db),'audit':dev.audit(args.db),
            'interpretation':'Online behavior changes, but coarse feature aliasing can harm feasible choices. Not a general adaptation success or promotion score.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'missed_feasible_opportunity':missed,'wall_s':report['wall_s']}))


if __name__=='__main__':main()
