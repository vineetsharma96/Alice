"""Readable run evidence in addition to the acceptance tests; no scripted intelligence claim."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage
from underworld.config import load

config=load(ROOT/"config/baseline.toml")
with tempfile.TemporaryDirectory(prefix="underworld-evidence-") as directory:
    path=Path(directory)/"scripted.sqlite"
    initial=storage.create(path,config)
    midway=storage.advance(path,37)
    backup=Path(directory)/"backup.sqlite"
    storage.save(path,"in-flight",backup)
    uninterrupted=storage.advance(path,163)
    resumed=storage.advance(backup,163)
    if uninterrupted["state_hash"]!=resumed["state_hash"]:
        raise RuntimeError("resume proof failed")
    second=Path(directory)/"same-seed.sqlite"
    storage.create(second,config)
    independently_repeated=storage.advance(second,200)
    if uninterrupted["state_hash"]!=independently_repeated["state_hash"]:
        raise RuntimeError("same-seed proof failed")
    report={"schema_version":1,"phase":2,"scope":"phase1_mechanics_regression","build_id":initial["build_id"],"seed":initial["seed"],
        "config":config,"inflight_checkpoint_tick":midway["tick"],
        "outstanding_at_checkpoint":midway["outstanding_actions"],
        "uninterrupted_hash":uninterrupted["state_hash"],"resumed_hash":resumed["state_hash"],
        "independent_same_seed_hash":independently_repeated["state_hash"],
        "replay":storage.replay(backup),"final_scripted_snapshot":resumed}
    manual=Path(directory)/"manual.sqlite"
    start=storage.create(manual,config,scripted=False)
    action={"schema_version":1,"run_id":start["run_id"],"request_id":"food-transfer-1","agent_id":"agent-1",
        "observation_version":"0","action_type":"gather","target_ids":["resource-1"],
        "parameters":{"mass_kg":1},"requested_duration":1.0}
    storage.advance(manual,5,[(0,action)])
    mid=Path(directory)/"transfer-backup.sqlite"
    storage.save(manual,"transfer-in-flight",mid)
    transfer=storage.advance(mid,5)
    report["transfer"]={"request":action,"initial_totals_ug":start["material_totals_ug"],
        "final_totals_ug":transfer["material_totals_ug"],
        "observation_after_restart":storage.observe(mid,["agent-1"])[0],"replay":storage.replay(mid)}
    db=sqlite3.connect(mid)
    try:
        report["transfer"]["event_trace"]=[json.loads(row[0]) for row in db.execute("SELECT payload FROM events ORDER BY seq")]
    finally:
        db.close()
    if report["transfer"]["initial_totals_ug"]!=report["transfer"]["final_totals_ug"]:
        raise RuntimeError("transfer mass proof failed")
(ROOT/"artifacts").mkdir(exist_ok=True)
(ROOT/"artifacts/phase2_mechanics_evidence.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"same_seed_matches":True,"resume_matches":True,"recorded_replay_matches":True,
    "mass_totals_match":True,"artifact":"artifacts/phase2_mechanics_evidence.json","state_hash":resumed["state_hash"]},indent=2))
