"""Registered, model-off authored teaching experiment; never a live autonomous policy."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage, teaching, culture, knowledge, memory  # noqa: E402
from underworld.config import load  # noqa: E402
from underworld.lab_policy import Driver  # noqa: E402


def inject(path,text,ident):
    snap=storage.inspect(path)
    result=teaching.intervene(path,{'schema_version':1,'run_id':snap['run_id'],
        'branch_id':snap['branch_id'],'intervention_id':ident,'observation_version':snap['tick'],
        'kind':'inject_knowledge','parameters':{'recipient':'agent-1','text':text}})
    records=knowledge.view(path,'agent-1')['records']
    return next(r['episode_id'] for r in records if r.get('source_id')==result['source_id'])


def state(path):
    with closing(storage._connect(path,readonly=True)) as db:
        db.execute('BEGIN');world,_,_,_=storage._head(db)
        return {'native':hashlib.sha256(world.checkpoint().encode()).hexdigest(),
                'cognitive':memory.checksum(db),
                'records':{a:knowledge.projection(db,a) for a in ('agent-1','agent-2','agent-3')}}


def run_case(folder,seed):
    start=time.perf_counter();path=folder/f'seed-{seed}.sqlite'
    cfg=load(ROOT/'config/culture.toml');cfg['mode']='guided';cfg['world']['population']=3
    cfg['culture']['apparatus_seed']=seed
    storage.create(path,cfg,scripted=False)
    # Operator-only randomized answer, explicitly supplied by the experiment author.
    # It is never passed to Driver; test_procedure obtains its dial from OWN episode.
    answer=storage.inspect(path)['culture']['hidden_apparatus']
    teacher=Driver(path,'agent-1');teacher.navigate((3,3));teacher.measure()
    dials=teacher.observation()['own_state']['apparatus_dials']
    wrong=next(d for d in dials if d!=answer['dial'])
    teacher.warm(answer['target_k'])
    false_id=inject(path,culture.procedure_text(wrong,answer['target_k']),'false-lesson')
    wrong_receipt=knowledge.test_procedure(path,'agent-1',false_id)
    assert wrong_receipt['error_code']=='PROCESS_CONDITIONS'
    assert teacher.observation()['own_state']['skills']['water_conditioning']['level']==0
    true_id=inject(path,culture.procedure_text(answer['dial'],answer['target_k']),'true-lesson')
    assert knowledge.view(path,'agent-2')['counts']['operator_injection']==0
    assert culture.recall(path,'agent-2')['status']=='unknown'
    assert culture.recall(path,'agent-3')['status']=='unknown'
    teacher.warm(answer['target_k'])
    tested=knowledge.test_procedure(path,'agent-1',true_id)
    assert tested['status']=='completed',tested
    # Writing uses text recalled from teacher's own episode, not the answer object.
    claim=next(c for c in culture.recall(path,'agent-1')['claims'] if c['episode_id']==true_id)
    text=culture.procedure_text(claim['procedure']['dial'],claim['procedure']['temperature_k'])
    teacher.act('gather',['resource-3'],{'mass_kg':.02})
    before=teacher.observation()['own_state']['inventory_ug']['inert_material']
    written=teacher.act('write_book',parameters={'text':text,'evidence_ref':tested['event_refs'][1]},seconds=5)
    book=written['observable_effects']['description'].removeprefix('written:')
    after=teacher.observation()['own_state']['inventory_ug']['inert_material']
    assert int(before)-int(after)==10000000
    teacher.navigate((2,3))
    student=Driver(path,'agent-2');student.navigate((3,3.8))
    assert culture.recall(path,'agent-2')['status']=='unknown'
    read=student.act('read',[book])
    own=culture.recall(path,'agent-2');assert own['status']=='reported'
    assert student.observation()['own_state']['skills']['water_conditioning']['level']==0
    assert own['claims'][0]['origin_event_seq']==tested['event_refs'][1]
    student.warm(own['claims'][0]['procedure']['temperature_k'])
    reproduced=knowledge.test_procedure(path,'agent-2',own['claims'][0]['episode_id'])
    assert reproduced['status']=='completed',reproduced
    assert culture.recall(path,'agent-3')['status']=='unknown'
    assert knowledge.view(path,'agent-3')['counts']['operator_injection']==0
    assert storage.observe(path,['agent-3'])[0]['own_state']['skills']['water_conditioning']['level']==0
    backup=folder/f'seed-{seed}-resumed.sqlite'
    storage.save(path,'after-learning',backup)
    before_restart=state(path)
    # Fresh Python process must retain all identity, memory, native and scheduler data.
    check=subprocess.run([sys.executable,'-m','underworld','knowledge','--db',str(backup),'--agent','agent-2'],capture_output=True,text=True,timeout=30)
    assert check.returncode==0,check.stderr
    assert json.loads(check.stdout)==knowledge.view(path,'agent-2')
    storage.advance(path,10)
    advance=subprocess.run([sys.executable,'-m','underworld','advance','--db',str(backup),'--ticks','10'],capture_output=True,text=True,timeout=30)
    assert advance.returncode==0,advance.stderr
    assert state(path)==state(backup)
    assert storage.replay(path)['replay_matches'] and storage.replay(backup)['replay_matches']
    snap=storage.inspect(path)
    with closing(storage._connect(path,readonly=True)) as db:
        decisions=[{'tick':r[0],'request':json.loads(r[1]),'result':json.loads(r[2]),'source':r[3]}
                   for r in db.execute('SELECT tick,request,result,source FROM decisions ORDER BY id')]
    return {'seed':seed,'passed':True,'path':str(path),'simulated_s':snap['simulated_time_s'],
            'wall_s':time.perf_counter()-start,'execution':'authored bounded lab driver',
            'model_calls':0,'deterministic_fallback_calls':0,'false_test':wrong_receipt,
            'teacher_test':tested,'writing':written,'reading':read,'student_test':reproduced,
            'book_claim':own['claims'][0],'initial_source':knowledge.view(path,'agent-1')['records'],
            'isolated_control':culture.recall(path,'agent-3'),'before_restart':before_restart,
            'resume_equal':True,'native_replay':True,'decisions':decisions}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--split',choices=['development','confirmation'],required=True)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.directory.mkdir(parents=True,exist_ok=False)
    seeds=[7] if args.split=='development' else [9187,11939]
    started=time.perf_counter();results=[]
    for seed in seeds:
        results.append(run_case(args.directory,seed))
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps({'split':args.split,'passed':True,'wall_s':time.perf_counter()-started,'cases':results},indent=2)+'\n')
        print(json.dumps({k:v for k,v in results[-1].items() if k in ('seed','passed','wall_s','simulated_s')}),flush=True)


if __name__=='__main__':main()
