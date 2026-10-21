"""Bounded native counterexample to an externally supplied water-as-food claim."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage,stabilization as stable,planning,teaching,knowledge,care  # noqa: E402
from underworld.config import load  # noqa: E402


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    cfg=load(ROOT/'config/living-world-g.toml');cfg['seed']=21;cfg['world']['population']=1
    stable.initialize(args.db,cfg,call_limit=0);before=storage.inspect(args.db);start=time.perf_counter()
    teaching.intervene(args.db,{'schema_version':1,'run_id':before['run_id'],'branch_id':before['branch_id'],
        'observation_version':before['tick'],'intervention_id':'false-care','kind':'inject_knowledge',
        'parameters':{'recipient':'agent-1','text':care.text('water')}})
    assert storage.inspect(args.db)['state_hash']==before['state_hash']
    ident=knowledge.view(args.db,'agent-1')['records'][0]['episode_id']
    planning.assign(args.db,'agent-1','feed_animal',{'target':'animal-1','lesson_episode_id':ident})
    for _ in range(100):
        stable.step(args.db)
        if not stable.status(args.db)['tasks']['active']:break
    else:raise AssertionError('false-care test exceeded its bound')
    history=stable.status(args.db)['tasks']['history'][-1]
    tests=[r for r in knowledge.view(args.db,'agent-1')['records'] if r['kind']=='knowledge_test']
    assert len(tests)==1 and tests[0]['status']=='rejected' and tests[0]['error_code']=='INVALID_ARGUMENT',tests
    assert history['outcome']=='blocked' and history['executor_goal_credit'] is False
    with closing(storage._connect(args.db,readonly=True)) as db:
        world,_,_,_=storage._head(db);world.check_invariants()
        decisions=[{'request':json.loads(q),'submission':json.loads(r)} for q,r in db.execute('SELECT request,result FROM decisions ORDER BY id')]
    report={'passed':True,'history':history,'tests':tests,'decisions':decisions,
            'snapshot':storage.inspect(args.db),'own':storage.observe(args.db,['agent-1'])[0]['own_state'],
            'wall_s':time.perf_counter()-start,'replay':storage.replay(args.db),'model_calls':0,
            'note':'Accepted external claim is unverified. Real gathering costs time; native offer_feed rejects water without granting feeding success or skill.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'passed':True,'native_error':'INVALID_ARGUMENT'}))


if __name__=='__main__':main()
