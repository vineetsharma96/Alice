"""Check original-world preservation, inherited cognition and exact F5 continuation."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from underworld import memory_store as store,mood_store,weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--world',type=Path,required=True)
    p.add_argument('--resume',type=Path,required=True);p.add_argument('--first',type=Path,required=True)
    p.add_argument('--last',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing proof')
    first=json.loads(a.first.read_text(encoding='utf8'));last=json.loads(a.last.read_text(encoding='utf8'))
    digest=hashlib.sha256(a.source.read_bytes()).hexdigest();assert digest==first['source_sha256']
    original=mood_store.inspect(a.source);final=store.inspect(a.world);resumed=store.inspect(a.resume)
    assert final['hash']==resumed['hash'] and final['snapshot']==resumed['snapshot'] and final['policies']==resumed['policies']
    with closing(weather.connect(a.source)) as old,closing(weather.connect(a.world)) as new:
        _,_,_,meta=store.head(new);initial=json.loads(meta['people'])
        assert json.loads(meta['policies'])==original['policies']
        for agent,person in original['people'].items():
            assert all(initial[agent][key]==value for key,value in person.items())
            assert initial[agent]['emotional_memory']['entries']==[]
        assert meta['initial']==mood_store.head(old)[0].checkpoint()
        for table in ('mood_meta','mood_head','mood_operations'):
            assert list(old.execute(f'SELECT * FROM {table}'))==list(new.execute(f'SELECT * FROM {table}'))
        prefix=list(old.execute('SELECT * FROM weather_operations ORDER BY seq'))
        assert prefix==list(new.execute('SELECT * FROM weather_operations ORDER BY seq'))[:len(prefix)]
        origin=json.loads(meta['origin']);cursor=origin['scheduler_cursor']+new.execute("SELECT COUNT(*) FROM memory_operations WHERE json_extract(command,'$.kind')='emotion-policy'").fetchone()[0]
    assert not final['climate']['forcing_history'] and not final['climate']['forced']
    snapshot=final['snapshot'];assert not any(snapshot['operator_sources_ug'].values()) and not any(snapshot['boundary_sources_ug'].values())
    for kind in ('food','water'):assert int(snapshot['material_totals_ug'][kind])==snapshot['initial_mass_ug'][kind]
    assert all(e['alive'] for e in snapshot['entities'] if e['kind']=='actor')
    proof=dict(verified=True,source_sha256=digest,original_simulated_s=original['snapshot']['simulated_time_s'],
               final_simulated_s=snapshot['simulated_time_s'],source_preserved=True,initial_cognitive_fields_preserved=True,
               initial_native_and_policy_exact=True,inactive_f4_history_exact=True,native_history_prefix_exact=True,
               inherited_cursor=origin['scheduler_cursor'],final_cursor=cursor,fresh_resume_matches=True,hash=final['hash'],
               health={e['entity_id']:e['body']['health'] for e in snapshot['entities'] if e['kind']=='actor'},
               no_weather_forcing=True,material_totals_ug=snapshot['material_totals_ug'],initial_mass_ug=snapshot['initial_mass_ug'],
               remaining=[e for e in snapshot['entities'] if e['kind'] in ('food','water')],
               index_bytes={a:len(weather.dumps(s['emotional_memory']).encode()) for a,s in final['people'].items()},
               window_wall_s=first['wall_s']+last['wall_s'],replay=store.replay(a.world))
    a.output.write_text(json.dumps(proof,indent=2),encoding='utf8')


if __name__=='__main__':main()
