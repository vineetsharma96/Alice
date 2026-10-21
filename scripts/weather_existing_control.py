"""Supplement: run the unchanged existing utility policy on matched W6 saves."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld.policy import choose  # noqa: E402
from underworld import weather_store as store  # noqa: E402
from underworld.weather_tools import JournalWorld  # noqa: E402
from scripts.weather_study import HELDOUT  # noqa: E402


def main():
    output=ROOT/'artifacts/weather_existing_control.json'
    if output.exists():raise ValueError('Do not overwrite existing-policy control evidence')
    directory=ROOT/'data/weather-existing-control-20261022';directory.mkdir(exist_ok=False)
    runs=[]
    for seed in HELDOUT:
        source=ROOT/f'data/weather-confirmation-20261022/{seed}/reachable-common.sqlite'
        path=directory/f'{seed}.sqlite';store.save(source,path);w=JournalWorld(path)
        initial=store.inspect(path);until=initial['snapshot']['simulated_time_s']+120
        navigation={};trace=[];start=time.perf_counter();tail=0
        while w.snapshot()['simulated_time_s']<until:
            if time.perf_counter()-start>120:raise TimeoutError('Existing control compute cap')
            o=w.observe_batch(['agent-1'])[0]
            action=choose(o,navigation)
            remaining=until-w.snapshot()['simulated_time_s']
            if action is None or action['requested_duration']>remaining:
                tail=remaining;w.step(round(remaining/o['dt_s']));break
            result=store.commit(path,dict(kind='submit',request=action,principal='agent-1',origin='unchanged_existing_utility_policy'))
            if result['status']=='accepted':
                w.step(round(action['requested_duration']/o['dt_s']))
                result=next(r for r in w.observe_batch(['agent-1'])[0]['recent_action_results'] if r['request_id']==action['request_id'])
            else:w.step(1)
            trace.append(dict(observation=o,request=action,receipt=result))
        final=store.inspect(path);replay=store.replay(path)
        runs.append(dict(seed=seed,initial=initial,final=final,decisions=trace,final_navigation=navigation,
                         idle_tail_s=tail,wall_s=time.perf_counter()-start,replay=replay,
                         native_save_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        print(json.dumps(dict(seed=seed,environmental_health_lost=final['climate']['exposure']['agent-1']['environmental_health_lost'],decisions=len(trace))),flush=True)
    result=dict(runs=runs,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                existing_policy_sha256=hashlib.sha256((ROOT/'underworld/policy.py').read_bytes()).hexdigest(),
                scope='post-registration supplementary control; unchanged legacy utility policy, same actual common native heads and120s clocks; no change to primary gates; controller resume not measured')
    output.write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
