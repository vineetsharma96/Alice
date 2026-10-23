"""Verify journal rejection of resealed mood/trait edits on disposable copies."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from underworld import mood_store as store,weather_store as weather


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--world',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Refuse replacing evidence')
    store.inspect(a.world);before=hashlib.sha256(a.world.read_bytes()).hexdigest();proof={}
    with tempfile.TemporaryDirectory() as td:
        for attack in ('forged_mood','forged_trait'):
            path=Path(td)/(attack+'.sqlite');weather.save(a.world,path)
            with closing(weather.connect(path,False)) as db:
                w,policies,people,_=store.head(db)
                if attack=='forged_mood':people['agent-1']['stress']=0.;people['agent-1']['mood']['valence']=0.
                else:people['agent-1']['temperament']['sensitivity']=.8
                db.execute('UPDATE mood_head SET people=?,hash=? WHERE id=1',(weather.dumps(people),store.token(w,policies,people)))
            try:store.replay(path)
            except ValueError as error:proof[attack]=dict(rejected=True,reason=str(error),head_checksum_resealed=True)
            else:raise ValueError('Forged state unexpectedly accepted')
    if hashlib.sha256(a.world.read_bytes()).hexdigest()!=before:raise ValueError('Original world changed')
    a.output.write_text(json.dumps(dict(source_preserved=True,cases=proof),indent=2),encoding='utf8')


if __name__=='__main__':main()
