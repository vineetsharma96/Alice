"""One constrained durable survival run and a resource-free native control; retain failures."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage
from underworld.config import load
from underworld.native import load_native
from underworld.policy import choose

parser=argparse.ArgumentParser()
parser.add_argument("--ticks",type=int,default=4500)
parser.add_argument("--config",type=Path,default=ROOT/"config/survival.toml")
parser.add_argument("--output",type=Path,default=ROOT/"artifacts/phase2_survival.json")
args=parser.parse_args()
if not 1<=args.ticks<=100000:parser.error("ticks must be [1,100000]")
config=load(args.config)
report={"phase":2,"seed":config["seed"],"build_id":load_native().build_id,"config":config,"runs":[]}
with tempfile.TemporaryDirectory(prefix="underworld-survival-") as directory:
    path=Path(directory)/"survival.sqlite"
    initial=storage.create(path,config)
    print(f"Durable survival: {args.ticks} ticks, {config['world']['population']} bodies",file=sys.stderr,flush=True)
    start=time.perf_counter()
    final=storage.advance(path,args.ticks)
    elapsed=time.perf_counter()-start
    db=sqlite3.connect(path)
    try:
        actions=Counter(json.loads(row[0])["action_type"] for row in db.execute("SELECT request FROM decisions"))
        events=Counter()
        failures=Counter()
        for text, in db.execute("SELECT payload FROM events"):
            event=json.loads(text)
            events[event["type"]]+=1
            if event["type"] in ("action_failed","action_rejected"):failures[event["detail"]]+=1
    finally:db.close()
    report["runs"].append({"condition":"resources_available","execution":"durable_one_tick_transactions",
        "ticks":args.ticks,"simulated_time_s":final["simulated_time_s"],"wall_time_s":elapsed,
        "ticks_per_wall_s":args.ticks/elapsed,"population":config["world"]["population"],
        "alive":sum(e["kind"]=="actor" and e["alive"] for e in final["entities"]),
        "action_requests":dict(actions),"retained_event_counts":dict(events),"observed_failures":dict(failures),
        "initial_material_totals_ug":initial["material_totals_ug"],"final_snapshot":final,
        "database_bytes":path.stat().st_size,"replay":storage.replay(path)})
scarce=copy.deepcopy(config)
scarce["agency"].update(food_kg=0,water_kg=0,food_regen_kg_s=0,water_regen_kg_s=0)
a=scarce["agency"];w=scarce["world"]
world=load_native().World(seed=scarce["seed"],population=w["population"],width=w["width_m"],height=w["height_m"],
                         dt=w["dt_s"],scripted=False,bodies=True,food_kg=0,water_kg=0)
navigation={};actions=Counter();events=Counter();failures=Counter();start=time.perf_counter()
for tick in range(args.ticks):
    if tick%a["interval_ticks"]==0:
        for observation in world.observe_batch([f"agent-{i+1}" for i in range(w["population"])]):
            agent=observation["agent_id"]
            request=choose(observation,navigation.setdefault(agent,{}))
            if request:
                actions[request["action_type"]]+=1
                world.submit(request,agent)
    for event in world.step(1):
        events[event["type"]]+=1
        if event["type"] in ("action_failed","action_rejected"):failures[event["detail"]]+=1
elapsed=time.perf_counter()-start
world.check_invariants()
final=world.snapshot()
report["runs"].append({"condition":"no_food_or_water","execution":"native_with_same_observation_only_policy",
    "config":scarce,"ticks":args.ticks,"simulated_time_s":final["simulated_time_s"],"wall_time_s":elapsed,
    "population":w["population"],"alive":sum(e["kind"]=="actor" and e["alive"] for e in final["entities"]),
    "action_requests":dict(actions),"event_counts":dict(events),"observed_failures":dict(failures),
    "final_snapshot":final,"state_hash":storage.head_hash(world.checkpoint(),navigation)})
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"artifact":str(args.output),"runs":[{k:r[k] for k in ("condition","ticks","simulated_time_s","wall_time_s","alive","observed_failures")} for r in report["runs"]]},indent=2))
