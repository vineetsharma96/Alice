"""Prospective bounded integration probes; retain every world and failed gate."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from underworld import life_store as store, weather_store as weather
from underworld import weather_tools as tools, weather_policy as policy
from underworld import communication_f9 as communication,relationships_f6 as relations
from underworld import others_f7 as inference
from scripts.life import run

SEEDS=(20301,20309,20317,20323,20333)


def people(path):return store.inspect(path)['people']


def say(path,index):
    state=people(path)['agent-1'];meaning=store.life_affect._meaning(store.JournalWorld(path).observe_batch(['agent-1'])[0])
    if meaning is None:raise ValueError('Ambiguous own bodily state; no fabricated signal meaning')
    token=communication.emit(deepcopy(state['life']['communication']),meaning,'agent-2','preview')['token']
    before=people(path)['agent-2']['life']['communication']
    prediction=communication._interpret(before,'agent-1',token)
    result=store.act(path,'agent-1',policy.option('speak',dict(text=token),duration=1,goal='assigned_context_demonstration'),f'speech-{index}')
    return dict(meaning=meaning,token=token,prior_prediction=prediction,
                completed=result['native']['receipt']['status']=='completed')


def probe(folder,seed):
    start=time.perf_counter();source=folder/f'{seed}-source.sqlite'
    store.initialize_source(source,seed=seed,population=4,guided=True)
    world=tools.JournalWorld(source)
    # Physical apparatus setup. No hidden actor state or supplies are injected.
    tools.walk(world,[3.1,3],agent='agent-2')
    tools.execute(world,'gather','resource-1',dict(mass_kg=.3))
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    branches={}
    for mode in ('connected','disconnected','frozen','relationships_disabled','shuffled'):
        path=folder/f'{seed}-{mode}.sqlite';store.attach(source,path,mode=mode)
        branches[mode]=path
    result=dict(seed=seed,apparatus='native routing/gathering, assigned transfers/speech, logged cold exposure',branches={})
    for mode,path in branches.items():
        store.act(path,'agent-1',policy.option('give',dict(material='food',mass_kg=.15),'agent-2',1,'assigned_help'),'give')
        before=people(path);recipient=before['agent-2']['life']
        trust=recipient['relationships'].get('agent-1',{}).get('trust',0)
        choice=store.commit(path,dict(kind='emotion-policy',agent='agent-2'),'behavior-probe')
        summary=dict(trust=trust,gratitude='gratitude' in recipient['social']['states'],
                     action=choice['native']['request']['action_type'],
                     completed=choice['native']['receipt']['status']=='completed',
                     nonparticipant_relations=before['agent-3']['life']['relationships'])
        if mode in ('connected','shuffled','frozen'):
            # Six actual calm demonstrations and two held-out delivery probes.
            calm=[say(path,f'calm-{i}') for i in range(8)]
            observation=store.JournalWorld(path).observe_batch(['agent-1'])[0]
            store.commit(path,dict(kind='force',parameters=dict(id='cold-probe',observation_version=observation['tick'],duration_s=120,
                temperature_c=-15,rain_mm_h=0,cloud_fraction=0,wind_x_m_s=0,wind_y_m_s=0)),'cold')
            store.commit(path,dict(kind='step',ticks=208),'cold-exposure')
            cold=[say(path,f'cold-{i}') for i in range(8)]
            scored=calm[6:]+cold[6:]
            summary['communication']=dict(trials=calm+cold,accuracy=sum(t['prior_prediction']['meaning']==t['meaning'] for t in scored)/len(scored),
                native_completed=all(t['completed'] for t in calm+cold),
                unfamiliar_prediction=communication._interpret(people(path)['agent-2']['life']['communication'],'agent-3',cold[-1]['token']))
        backup=folder/f'{seed}-{mode}-backup.sqlite';weather.save(path,backup)
        summary['backup_equal']=store.inspect(path)['hash']==store.inspect(backup)['hash']
        summary['replay']=store.replay(path)
        summary['world']=str(path.resolve().relative_to(ROOT))
        result['branches'][mode]=summary
    connected=result['branches']['connected'];disconnected=result['branches']['disconnected']
    # Explicit mechanism-only comparisons do not assert naturally observed tasks.
    ab=relations.initial('agent-1','agent-2');ac=relations.initial('agent-1','agent-3')
    for i in range(3):
        for state,kind in ((ab,'task_completed'),(ac,'task_failed')):
            relations.observe(state,dict(observer='agent-1',other=state['other'],kind=kind,source_event_seq=str(i+1),tick=i+1))
    helper_before=relations.choose_helper({'agent-2':ab,'agent-3':ac},['agent-2','agent-3'])
    for i in range(10):relations.observe(ac,dict(observer='agent-1',other='agent-3',kind='task_completed',source_event_seq=str(20+i),tick=20+i))
    helper_after=relations.choose_helper({'agent-2':ab,'agent-3':ac},['agent-2','agent-3'])
    estimate=inference.initial('agent-1','agent-2')
    def envelope(ident,cue):return dict(observer='agent-1',target='agent-2',visible_cues=[dict(source_event_id=ident,cue=cue,strength=1)],social_reports=[])
    ambiguous=inference.infer(estimate,envelope('ambiguous','ambiguous_stillness'))
    corrected=inference.infer(estimate,envelope('drinking','drinking_observed'))
    result['mechanism_only']=dict(helper_before=helper_before,helper_after=helper_after,
        ambiguity=ambiguous['ambiguities'],corrected=corrected['correction'])
    result['gates']=dict(F6_directional_native_help=connected['trust']>0 and not connected['nonparticipant_relations']
        and helper_before['other']=='agent-2' and helper_after['other']=='agent-3',
        F7_uncertainty_mechanism=bool(ambiguous['ambiguities']) and corrected['correction']['applied'],
        F9_acquired_native_signals=connected['communication']['accuracy']>=.8
          and result['branches']['shuffled']['communication']['accuracy']<=.6
          and result['branches']['frozen']['communication']['accuracy']<=.6
          and connected['communication']['unfamiliar_prediction']['meaning'] is None,
        F10_native_gratitude_behavior=connected['gratitude'] and connected['action']=='give' and disconnected['action']!='give',
        persistence=all(b['backup_equal'] and b['replay']['verified'] for b in result['branches'].values()))
    result['source_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
    result['wall_s']=time.perf_counter()-start
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--development',action='store_true');a=parser.parse_args()
    if a.folder.exists() or a.output.exists():parser.error('Use unused evidence paths')
    a.folder.mkdir(parents=True);a.output.parent.mkdir(parents=True,exist_ok=True)
    manifest=store.sources()
    with zipfile.ZipFile(a.folder/'sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for p in manifest:archive.write(ROOT/p,p)
        archive.write(Path(__file__),'scripts/life_experiment.py')
        archive.write(ROOT/'docs/LIFE_INTEGRATION_PROTOCOL.md','docs/LIFE_INTEGRATION_PROTOCOL.md')
        archive.writestr('manifest.json',json.dumps(manifest,indent=2))
    results=[]
    for seed in ((61,) if a.development else SEEDS):
        try:result=probe(a.folder,seed)
        except Exception as error:
            result=dict(seed=seed,error=repr(error),gates={},failed=True)
        results.append(result)
        a.output.write_text(json.dumps(dict(protocol='docs/LIFE_INTEGRATION_PROTOCOL.md',development=a.development,runs=results),indent=2,allow_nan=False),encoding='utf8')
        print(json.dumps(dict(seed=seed,gates=result.get('gates'),error=result.get('error'))),flush=True)
        if result.get('failed'):break


if __name__=='__main__':main()
