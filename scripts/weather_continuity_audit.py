"""Supplement: verify the same measured weather life, accounting and scheduler."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.weather_audit import read,same,world  # noqa: E402


def main():
    previous=None;windows=[];run_id=None;cursor=0
    for horizon in (300,600,1200,2400):
        r=read(ROOT/f'artifacts/weather_continuity_{horizon}.json')
        if previous:
            for k in ('snapshot','climate','policy','state_hash','operation_count'):
                if not same(r['initial'][k],previous[k]):raise ValueError('Continuous weather window reset: '+k)
        a,b=r['initial']['snapshot'],r['final']['snapshot']
        if run_id is None:run_id=a['run_id']
        assert a['run_id']==b['run_id']==run_id
        assert r['stop_reason']=='horizon_reached' and b['simulated_time_s']==horizon
        assert all(v==0 for v in b['boundary_sources_ug'].values())
        assert all(v==0 for v in b['operator_sources_ug'].values())
        # Raw native snapshots do not include the UW9 storage adapter's
        # synthetic intervention-count field. The replayed journal and native
        # forcing/material ledgers are the authorities for this new schema.
        assert b['ecology']['forage_regeneration_kg_s']==0
        assert r['final']['climate']['forcing_history']=={}
        people=[e for e in b['entities'] if e['kind']=='actor']
        assert len(people)==4 and all(e['alive'] and e['body']['health']>=.5 for e in people)
        accounts={}
        for material,total in [('food',8000000000),('water',16000000000)]:
            stock=sum(int(e['mass_ug']) for e in b['entities'] if e['kind']==material)
            held=sum(int(e['inventory_ug'].get(material,0)) for e in people)
            ingested=sum(int(e['body'][material+'_ingested_ug']) for e in people)
            assert stock+held+ingested==total
            accounts[material]=dict(stock_ug=stock,carried_ug=held,ingested_ug=ingested)
        cursor+=r['steps']
        assert r['final']['policy']['_scheduler']['cursor']==cursor
        windows.append(dict(start_sim_s=a['simulated_time_s'],end_sim_s=b['simulated_time_s'],
                            wall_s=r['wall_s'],frames=r['steps'],accounts=accounts,
                            season=r['final']['climate']['season'],health={e['entity_id']:e['body']['health'] for e in people}))
        previous=r['final']
    actual,_=world(ROOT/'data/weather-life-20261022.sqlite',previous)
    assert actual['climate']['year_index']=='1' and actual['climate']['season']=='spring'
    total=read(ROOT/'artifacts/weather_continuity_300_total_wall.json')['wall_including_setup_s']
    result=dict(verified=True,full_accelerated_year=True,run_id=run_id,windows=windows,cursor=cursor,
                continuation_wall_s=sum(w['wall_s'] for w in windows),
                wall_including_setup_s=total+sum(w['wall_s'] for w in windows[1:]),
                model_calls=0,scope='one finite scaffolded development life; not indefinite or multi-seed survival',
                supplemental_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (ROOT/'artifacts/weather_continuity_audit.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':main()
