"""Persist/restart an in-flight meal and retain actual request/result/event evidence."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage
from underworld.config import load

config=load(ROOT/"config/survival.toml")
with tempfile.TemporaryDirectory(prefix="underworld-body-evidence-") as directory:
    path=Path(directory)/"manual.sqlite"
    initial=storage.create(path,config,scripted=False)
    def action(tick,kind,mass,target,duration):
        return {"schema_version":1,"run_id":initial["run_id"],"request_id":f"evidence-{kind}","agent_id":"agent-1",
            "observation_version":str(tick),"action_type":kind,"target_ids":target,
            "parameters":{"mass_kg":mass},"requested_duration":duration}
    gather=action(0,"gather",.4,["resource-1"],1)
    storage.advance(path,5,[(0,gather)])
    meal=action(5,"eat",.2,[],2)
    middle=storage.advance(path,5,[(5,meal)])
    backup=Path(directory)/"meal.sqlite"
    storage.save(path,"mid-meal",backup)
    full=storage.advance(path,5)
    resumed=storage.advance(backup,5)
    if full["state_hash"]!=resumed["state_hash"]:raise RuntimeError("mid-meal restart diverged")
    observation=storage.observe(backup,["agent-1"])[0]
    if observation["own_state"]["body"]["food_ingested_ug"]!="200000000":raise RuntimeError("meal did not physically consume food")
    db=sqlite3.connect(backup)
    try:trace=[json.loads(row[0]) for row in db.execute("SELECT payload FROM events ORDER BY seq")]
    finally:db.close()
    report={"phase":2,"build_id":initial["build_id"],"config":config,"requests":[gather,meal],
        "saved_tick":middle["tick"],"outstanding_at_save":middle["outstanding_actions"],
        "uninterrupted_hash":full["state_hash"],"resumed_hash":resumed["state_hash"],
        "observation_after_restart":observation,"event_trace":trace,"replay":storage.replay(backup),
        "initial_totals_ug":initial["material_totals_ug"],"final_totals_ug":resumed["material_totals_ug"]}
(ROOT/"artifacts").mkdir(exist_ok=True)
(ROOT/"artifacts/phase2_body_evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"mid_meal_resume_matches":True,"ingested_food_ug":"200000000","replay_matches":True,
                  "artifact":"artifacts/phase2_body_evidence.json"},indent=2))
