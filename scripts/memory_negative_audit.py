"""Reject resealed index tampering and factual-result rewriting on disposable copies."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from underworld import memory_store as store,weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--world',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    store.inspect(a.world);before=hashlib.sha256(a.world.read_bytes()).hexdigest();cases={}
    with tempfile.TemporaryDirectory() as folder:
        for attack in ('resealed_index','rewritten_appraisal'):
            copy=Path(folder)/(attack+'.sqlite');weather.save(a.world,copy)
            with closing(weather.connect(copy,False)) as db:
                if attack=='resealed_index':
                    w,policies,people,_=store.head(db);entry=people['agent-1']['emotional_memory']['entries'][0]
                    entry['outcome']=.123456
                    db.execute('UPDATE memory_head SET people=?,hash=? WHERE id=1',(weather.dumps(people),store.token(w,policies,people)))
                else:
                    seq,raw=db.execute("SELECT seq,result FROM memory_operations WHERE json_extract(result,'$.updates.agent-1.emotional_memory.encoded') IS NOT NULL ORDER BY seq LIMIT 1").fetchone()
                    r=json.loads(raw);r['updates']['agent-1']['appraisal']['outcome']=.123456
                    db.execute('UPDATE memory_operations SET result=? WHERE seq=?',(weather.dumps(r),seq))
            try:store.replay(copy)
            except ValueError as error:cases[attack]=dict(rejected=True,reason=str(error))
            else:raise ValueError('Tampered evidence accepted')
    assert hashlib.sha256(a.world.read_bytes()).hexdigest()==before
    a.output.write_text(json.dumps(dict(source_preserved=True,cases=cases,source_sha256=before,
                                      verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding='utf8')


if __name__=='__main__':main()
