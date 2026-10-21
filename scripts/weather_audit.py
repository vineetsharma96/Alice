"""Independently recompute W6 gates from actual saves and native journal replay."""
import argparse
from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import weather_store as store  # noqa: E402
from underworld.weather_runtime import climate,load  # noqa: E402
from scripts.weather_study import HELDOUT,sources,restarts  # noqa: E402


def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def same(a,b):return store.dumps(a)==store.dumps(b)


def world(path,reported=None,initial=None):
    actual=store.inspect(path)
    if reported:
        for key in ('snapshot','climate','policy','state_hash','operation_count'):
            if not same(actual[key],reported[key]):raise ValueError('Native weather final differs: '+key)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=reported['sqlite_sha256']:raise ValueError('Weather SQLite hash differs')
    # Independently replay every committed native operation, reconstructing
    # protection from actual positions, not the policy's goal/choice labels.
    first={};maximum=0;policies={};completed=rejected=accepted=0;inventory_preserved=True
    with closing(store.connect(path)) as db:
        _,meta,_=store.head(db)
        w=load().World.restore(meta['initial'],meta['run_id'])
        for seq,command,before,after,result in db.execute('SELECT seq,command,before_hash,after_hash,result FROM weather_operations ORDER BY seq'):
            command=json.loads(command)
            if store.digest(w.checkpoint())!=before:raise ValueError('Weather before-chain mismatch')
            before_inventory=None
            if command['kind']=='submit' and command['request']['action_type']=='begin_construction':
                before_inventory=w.observe_batch([command['principal']])[0]['own_state']['inventory_ug']
            response=store.apply(w,command,policies)
            if store.dumps(response)!=result or store.digest(w.checkpoint())!=after:raise ValueError('Weather native receipt/replay mismatch')
            if command['kind']=='submit' and response['status']=='accepted':accepted+=1
            if before_inventory is not None and response['status']=='rejected':
                inventory_preserved &= same(before_inventory,w.observe_batch([command['principal']])[0]['own_state']['inventory_ug'])
            if command['kind'] in ('policy','cohort') and 'receipt' in response:
                if response['receipt']['status']=='completed':completed+=1
                else:rejected+=1
            if initial and seq>initial['operation_count'] and command['kind'] in ('policy','cohort'):
                current=w.weather_snapshot();clock=w.snapshot()['simulated_time_s']
                protected=[a for a,e in current['exposure'].items() if e['shelter_id']]
                maximum=max(maximum,len(protected))
                for agent in protected:first.setdefault(agent,clock-initial['snapshot']['simulated_time_s'])
        w.check_invariants()
        if store.digest(w.checkpoint())!=actual['state_hash'] or not same(policies,actual['policy']):raise ValueError('Final weather/private scheduler state mismatch')
    counts=dict(accepted_submissions=accepted,completed_policy_actions=completed,policy_rejections=rejected)
    if reported and counts!=reported['counts']:raise ValueError('Accepted/completed weather requests conflated')
    return actual,dict(first_protection_s=first,max_protected=maximum,counts=counts,refused_inventory_preserved=inventory_preserved)


def audit(study,directory,registration):
    report=read(study);pins=read(registration)
    if report['development'] or [r['seed'] for r in report['runs']]!=HELDOUT:raise ValueError('Untouched weather cohort required')
    if sources()!=pins['files'] or sources()!=report['files'] or pins['native_build_id']!=load().build_id:raise ValueError('Weather source freeze differs')
    old={}
    for name in ('living_world_g_registration','developmental_h1_registration_repaired','developmental_h2_registration','h3_native_registration','h4_registration','h5_registration','gap_registration'):
        manifest=read(ROOT/'artifacts'/f'{name}.json');files=manifest.get('files',manifest.get('source_files'))
        old[name]=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in files.items())
    if not all(old.values()):raise ValueError('Historical registered source changed')
    results=[];inventory=[]
    for run in report['runs']:
        root=directory/str(run['seed']);mild,_=world(root/'mild.sqlite',run['mild'])
        arms={}
        common,_=world(root/'reachable-common.sqlite')
        for mode,record in run['reachable'].items():
            actual,timeline=world(root/f'reachable-{mode}.sqlite',record['final'],record['initial'])
            if not same(common,record['initial']):raise ValueError('Weather arms did not start from common save')
            for key in ('first_protection_s','max_protected'):
                if timeline[key]!=record[key]:raise ValueError('Weather protection credit is not physical')
            arms[mode]=(actual,timeline)
        build,bt=world(root/'build.sqlite',run['build']['final'],run['build']['initial'])
        _,blocked=world(root/'blocked.sqlite',run['scarcity']['final'])
        sharing,st=world(root/'sharing.sqlite',run['sharing']['final'],run['sharing']['initial'])
        if bt['first_protection_s']!=run['build']['first_protection_s'] or st['first_protection_s']!=run['sharing']['first_protection_s']:raise ValueError('Native build/sharing timeline differs')
        scarcity=run['scarcity'];rejections=[]
        if restarts(run['seed'])!=run['restart']:raise ValueError('Fresh-process weather/build/shelter restarts differ')
        with closing(store.connect(root/'blocked.sqlite')) as db:
            for command,response in db.execute('SELECT command,result FROM weather_operations ORDER BY seq'):
                command,response=json.loads(command),json.loads(response)
                if command['kind']=='submit' and response['status']=='rejected':rejections.append(response['error_code'])
        expected_growth={}
        for label,rate in [('grown',.001),('zero',0)]:
            w=load().World(seed=run['seed'],population=1,width=32,height=32,dt=.25,scripted=False,bodies=True,tree_growth_kg_s=rate)
            w.configure_climate(climate());w.configure_ecology(forage_kg=0,regeneration_kg_s=rate);w.step(400);w.check_invariants()
            if not same(w.snapshot(),run['growth'][label]):raise ValueError('Seasonal ledger cannot be recomputed')
            expected_growth[label]=w.snapshot()['boundary_sources_ug']
        dose={m:arms[m][0]['climate']['exposure']['agent-1']['environmental_health_lost'] for m in arms}
        health={m:next(e['body']['health'] for e in arms[m][0]['snapshot']['entities'] if e['entity_id']=='agent-1') for m in arms}
        gates=dict(mild=mild['climate']['exposure']['agent-1']['environmental_health_lost']<=1e-12,
                   reachable=arms['weather'][1]['first_protection_s'].get('agent-1',1e9)<=60 and dose['survival']-dose['weather']>=.02 and health['weather']>=health['survival'],
                   build=any(s['complete'] for s in build['climate']['shelters']) and bool(bt['first_protection_s']),
                   scarcity='NO_PLACEMENT' in rejections and 'INSUFFICIENT_RESOURCE' in rejections and blocked['refused_inventory_preserved'] and scarcity['blocked_inventory_unchanged'],
                   sharing=len(st['first_protection_s'])==4 and st['max_protected']==4,
                   growth=0<expected_growth['grown']['tree']<100000000 and 0<expected_growth['grown']['food']<100000000 and expected_growth['zero']['tree']==0 and expected_growth['zero']['food']==0,
                   restart=all(run['restart'].values()))
        if gates!=run['gates']:raise ValueError('Reported weather gates differ from native evidence')
        results.append(dict(seed=run['seed'],gates=gates,environmental_health_loss=dose,health=health,
                            time_to_protection_s=arms['weather'][1]['first_protection_s'],sharing_first_s=st['first_protection_s'],
                            native_counts={m:arms[m][1]['counts'] for m in arms},simulated_end_s={m:arms[m][0]['snapshot']['simulated_time_s'] for m in arms}))
        for path in sorted(root.glob('*.sqlite')):
            inventory.append(dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return dict(verified=True,all_gates=all(all(r['gates'].values()) for r in results),runs=results,
                native_worlds=inventory,old_registrations=old,model_calls=0,
                limits='authored policy; controlled forcing is an intervention; restart assertions also require retained software checks; SQLite saves remain local')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--registration',type=Path,default=ROOT/'artifacts/weather_registration.json')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=audit(args.study,args.directory,args.registration)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(verified=result['verified'],all_gates=result['all_gates'])))


if __name__=='__main__':main()
