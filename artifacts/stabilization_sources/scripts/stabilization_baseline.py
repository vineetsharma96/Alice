"""Reproduce unchanged policies before stabilization implementation."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import storage,cognition
from underworld.policy import choose
from stabilization_common import create,read,write,model_server


def main():
    folder=ROOT/'data/stabilization-baseline';folder.mkdir(exist_ok=False)
    cases=[]
    with model_server(folder) as endpoint:
        for age in (0,160):
            for arm in ('utility','legacy_model'):
                path=create(folder/f'{age}-{arm}.sqlite',population=1,age=age)
                started=time.perf_counter();before=storage.observe(path,['agent-1'])[0]; receipts={}; thoughts=[]; traces=[]; nav={}
                for offset in range(20):
                    o=storage.observe(path,['agent-1'])[0]; decisions=[]
                    if arm=='legacy_model' and offset in (0,10) and not o['own_state']['busy']:
                        thoughts.append(storage.think(path,'agent-1',cognition.LlamaCpp(endpoint)))
                    if arm=='utility':
                        req=choose(o,nav)
                        if req:decisions=[(int(o['tick']),req)]
                    storage.advance(path,1,decisions)
                    after=storage.observe(path,['agent-1'])[0]
                    for r in after['recent_action_results']:receipts[r['request_id']]=r
                    traces.append(dict(offset=offset,before=o,after=after))
                decisions=read(path,'decisions');calls=read(path,'cognition_calls');plans=read(path,'plans')
                for r in calls:r['payload']=json.loads(r['payload'])
                case=dict(arm=arm,age=age,before=before,after=after,simulated_s=20,wall_s=time.perf_counter()-started,
                    thoughts=thoughts,decisions=decisions,receipts=list(receipts.values()),calls=calls,plans=plans,traces=traces,
                    replay=storage.replay(path))
                cases.append(case);write(ROOT/'artifacts/stabilization_baseline.json',dict(cases=cases,native_build_id=storage.load_native().build_id,orchestration_id=storage.orchestration_id()))
                print(age,arm,[(r['status'],r.get('error_code')) for r in receipts.values()],flush=True)


if __name__=='__main__':main()
