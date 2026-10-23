"""Native F8/F11 recovery probes. A failed efficacy gate is retained as failed."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import life_store as store,weather_tools as tools,weather_policy as policy
from underworld import regulation_f8 as regulation
from scripts.life_experiment import SEEDS


def probe(folder,seed):
    started=time.perf_counter();source=folder/f'{seed}-source.sqlite'
    store.initialize_source(source,seed=seed,population=4,guided=True)
    world=tools.JournalWorld(source)
    tools.execute(world,'gather','resource-2',dict(mass_kg=.2))
    tools.execute(world,'drink',parameters=dict(mass_kg=.2))
    result={'seed':seed,'branches':{}}
    for mode in ('connected','frozen','disconnected'):
        path=folder/f'{seed}-{mode}.sqlite';store.attach(source,path,mode=mode)
        store.commit(path,dict(kind='step',ticks=400),'idle')
        before=store.JournalWorld(path).observe_batch(['agent-1'])[0]
        outcome=store.act(path,'agent-1',policy.option(duration=1,goal='assigned_real_recovery'),'recovery')
        after=outcome['native']['after'];state=store.inspect(path)['people']['agent-1']
        candidates=[dict(strategy='rest',action_type='rest',parameters={'seconds':1},requested_duration=1,estimated_cost_s=1),
            dict(strategy='move_to_safety',action_type='move',parameters={'target_position':list(after['own_state']['position_m'])},requested_duration=1,estimated_cost_s=1)]
        choice=regulation.choose(after,state['life']['regulation'],candidates)
        first=store.commit(path,dict(kind='emotion-policy',agent='agent-1'),'value-choice-one')
        now=store.JournalWorld(path).observe_batch(['agent-1'])[0]
        store.commit(path,dict(kind='force',parameters=dict(id='mild-rain',observation_version=now['tick'],duration_s=10,
            temperature_c=20,rain_mm_h=.1,cloud_fraction=.1,wind_x_m_s=0,wind_y_m_s=0)),'rain')
        store.commit(path,dict(kind='step',ticks=4),'new-context')
        second=store.commit(path,dict(kind='emotion-policy',agent='agent-1'),'value-choice-two')
        result['branches'][mode]=dict(before_fatigue=before['own_state']['body']['fatigue'],
            after_fatigue=after['own_state']['body']['fatigue'],
            real_recovery=outcome['native']['receipt']['status']=='completed' and after['own_state']['body']['fatigue']<before['own_state']['body']['fatigue'],
            regulation_selection=choice['strategy'],regulation_evidence=state['life']['regulation']['evidence'],
            values=state['life']['values'],first_choice=first['native']['choice'],second_choice=second['native']['choice'],
            first_influence=first['influence'],second_influence=second['influence'],replay=store.replay(path))
    c=result['branches']['connected'];f=result['branches']['frozen']
    # The production F8 integration currently offers only duration variants of
    # rest; distinct-strategy causal efficacy is not demonstrated by this probe.
    result['gates']=dict(F8_real_time_costed_recovery=c['real_recovery'],F8_improves_recovery_or_decision_quality=False,
        F11_two_context_acquired_choice=c['first_choice']['goal']=='acquired_recovery'
         and c['second_choice']['goal']=='acquired_recovery' and f['first_choice']['goal']!='acquired_recovery',
        persistence=all(b['replay']['verified'] for b in result['branches'].values()))
    result['F8_failure_reason']='Observed fatigue relief is real, but no controlled improvement from learned strategy selection has been established.'
    result['wall_s']=time.perf_counter()-started
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--development',action='store_true');a=p.parse_args()
    if a.folder.exists() or a.output.exists():p.error('Use unused evidence paths')
    a.folder.mkdir(parents=True);results=[]
    for seed in ((61,) if a.development else SEEDS):
        try:r=probe(a.folder,seed)
        except Exception as error:r=dict(seed=seed,error=repr(error),gates={})
        results.append(r);a.output.write_text(json.dumps(dict(protocol='docs/LIFE_INTEGRATION_PROTOCOL.md',development=a.development,runs=results),indent=2),encoding='utf8')
        print(json.dumps(dict(seed=seed,gates=r['gates'],error=r.get('error'))),flush=True)
        if 'error' in r:break


if __name__=='__main__':main()
