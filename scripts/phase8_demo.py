"""Create an explicitly authored guided lab fixture; no prewritten agent success."""
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import storage,teaching
from underworld.config import load


def create(path):
    config=load(ROOT/'config/culture.toml');config['mode']='guided';config['world']['population']=8
    config['agency'].update(policy='utility',interval_ticks=5)
    storage.create(path,config)
    def intervention(kind,parameters,identifier):
        s=storage.inspect(path)
        return teaching.intervene(path,{'schema_version':1,'run_id':s['run_id'],'branch_id':s['branch_id'],
            'intervention_id':identifier,'observation_version':s['tick'],'kind':kind,'parameters':parameters})
    intervention('place_book',{'entity_id':'book-field-notes','x_m':3.4,'y_m':3,'mass_kg':.01,'energy_j':0,
        'text':'Field note: inspect the nearby vessels before choosing a heater. This is an unverified operator suggestion, not an engine law.'},'phase8-authored-book')
    entities=storage.inspect(path)['entities']
    spot=next((p for p in [(1,6),(1,1),(14,14),(14,1)] if all(math.dist(p,e['position_m'])>=e['radius_m']+.25 for e in entities if e['radius_m']>0)),None)
    if spot is None:raise ValueError('no free authored avatar position')
    intervention('avatar_message',{'x_m':spot[0],'y_m':spot[1],'text':'I am observing the lab. Source reports remain unverified.'},'phase8-authored-avatar')
    # Access is earned by a real native read action, retained in the event trace.
    s=storage.inspect(path);request={'schema_version':1,'run_id':s['run_id'],'request_id':'phase8-fixture-read','agent_id':'agent-1',
        'observation_version':s['tick'],'action_type':'read','target_ids':['book-field-notes'],'parameters':{},'requested_duration':1}
    storage._advance(path,5,[(int(s['tick']),request)])
    (Path(path).parent/'fixture.json').write_text(json.dumps({'authored_fixture':True,'config':config,'read_action':request,
        'note':'Operator book/avatar and the initial read are authored setup, not spontaneous learning. Later movement follows the existing utility policy.'},indent=2),encoding='utf-8')
    return storage.inspect(path)


if __name__=='__main__':
    path=ROOT/'data/phase8-demo/run.sqlite';create(path);print(path)
