"""Five-seed paired teaching/episodic-ablation evidence with authored observation-only policies."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage,teaching,culture
from underworld.config import load
from underworld.lab_policy import Driver
from underworld.resources import process_memory


def metrics(path):
    s=storage.inspect(path)
    with closing(sqlite3.connect(path)) as db:
        events=[json.loads(r[0]) for r in db.execute("SELECT payload FROM events ORDER BY seq")]
        decisions=[{"tick":r[0],"request":json.loads(r[1]),"result":json.loads(r[2])} for r in db.execute("SELECT tick,request,result FROM decisions ORDER BY id")]
    return {"snapshot":s,"event_counts":dict(Counter(e["type"] for e in events)),"events":events,"decisions":decisions}


def arm(root,directory,seed,name,learned,cooperate_teacher,cooperate_student):
    path=directory/f"{name}.sqlite"
    s=teaching.fork(root,path,episodic_memory=name!="memory_disabled")
    initial=s;teacher=Driver(path,"agent-1");student=Driver(path,"agent-2")
    offer=teacher.act("offer_task",["agent-2"],{"text":"Condition water using the local apparatus"})
    agreement=offer["request_id"]
    student.act("respond_task",parameters={"agreement_id":agreement,"accept":cooperate_student})
    if cooperate_teacher and cooperate_student:teacher.act("give",["agent-2"],{"material":"food","mass_kg":.1})
    else:teacher.act("rest")
    book=None
    if cooperate_teacher and name!="no_teaching":
        r=teacher.act("write_book",parameters={"text":culture.procedure_text(learned["dial"],learned["temperature_k"]),"evidence_ref":learned["validation_event"]},seconds=5)
        book=r["observable_effects"]["description"].removeprefix("written:")
    else:teacher.act("rest",seconds=5)
    teacher.act("depart")
    assert not teacher.observation()["own_state"]["present"]
    level_before=student.observation()["own_state"]["skills"]["water_conditioning"]["level"]
    if book and cooperate_student:student.act("read",[book])
    else:student.act("rest")
    level_after_read=student.observation()["own_state"]["skills"]["water_conditioning"]["level"]
    assert level_before==level_after_read==0
    backup=directory/f"{name}-restarted.sqlite";storage.save(path,"after-study",backup)
    # Fresh process and fresh controller: do not pass the teacher's learned recipe to the learner.
    command=[sys.executable,"-m","underworld","procedure","--db",str(backup),"--agent","agent-2"]
    proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=30)
    if proc.returncode:raise RuntimeError(proc.stderr)
    recalled=json.loads(proc.stdout);student=Driver(backup,"agent-2")
    if recalled["claims"]:
        chosen=recalled["claims"][0]["procedure"];source="own accessed original report"
    else:
        student.measure();choices=student.observation()["own_state"]["apparatus_dials"]
        blind=random.Random(seed^0x51a7)
        chosen={"dial":blind.choice(choices),"temperature_k":blind.choice((310,325,340,355))};source="authored blind one-of-16 fallback"
    before_execution=storage.inspect(backup)
    student.warm(chosen["temperature_k"]);result=student.process(chosen["dial"])
    success=result["status"]=="completed";durations=[float(result["completed_tick"])-float(result["started_tick"])]
    first=storage.inspect(backup)
    practice=[]
    if success:
        for _ in range(3):
            student.warm(chosen["temperature_k"]);receipt=student.process(chosen["dial"])
            practice.append(receipt)
            durations.append((int(receipt["completed_tick"])-int(receipt["started_tick"]))*first["dt_s"])
    durations[0]*=first["dt_s"]
    final=metrics(backup);snapshot=final["snapshot"]
    replay=storage.replay(backup);assert replay["replay_matches"]
    assert "agent-1" not in [e["entity_id"] for e in student.observation()["visible_entities"]]
    assert abs(snapshot["thermal"]["global_balance_error_j"])<=snapshot["thermal"]["energy_tolerance_j"]
    return {"condition":name,"initial_state_hash":initial["state_hash"],"branch_id":initial["branch_id"],
        "teacher_willing":cooperate_teacher,"student_willing":cooperate_student,"teacher_departed_before_read":True,
        "artifact_id":book,"skill_before_read":level_before,"skill_after_read":level_after_read,
        "fresh_process_recall":recalled,"chosen":chosen,"choice_source":source,"success":success,
        "first_result":result,"repeat_practice":practice,"execution_durations_s":durations,
        "first_execution_cost_j":first["thermal"]["heater_input_j"]-before_execution["thermal"]["heater_input_j"],
        "total_arm_heater_j":snapshot["thermal"]["heater_input_j"]-initial["thermal"]["heater_input_j"],
        "arm_simulated_s":snapshot["simulated_time_s"]-initial["simulated_time_s"],
        "first_execution_simulated_s":first["simulated_time_s"]-before_execution["simulated_time_s"],
        "database_bytes":backup.stat().st_size,"database":str(backup),"replay":replay,**final}


def trial(directory,seed):
    directory.mkdir();root=directory/"root.sqlite"
    config=load(ROOT/"config/culture.toml");config["seed"]=seed
    config["culture"]["apparatus_seed"]=random.Random(seed^0x1973).getrandbits(64)
    storage.create(root,config,scripted=False)
    teacher=Driver(root,"agent-1");student=Driver(root,"agent-2")
    teacher.act("gather",["resource-1"],{"mass_kg":.2});teacher.navigate((3,3))
    teacher.act("gather",["resource-3"],{"mass_kg":.02});student.navigate((3,4.2))
    learned=teacher.discover()
    if "error" in learned:return {"seed":seed,"discovery":learned,"failure":"authored search exhausted","arms":[]}
    identities={a:storage.mind(root,a)["identity"] for a in ("agent-1","agent-2")}
    willing={a:culture.willing_to_share(v) for a,v in identities.items()}
    root_bytes=root.read_bytes();root_metrics=metrics(root)
    arms=[]
    for name in ("teaching","no_teaching","memory_disabled"):
        arms.append(arm(root,directory,seed,name,learned,willing["agent-1"],willing["agent-2"]))
        assert root.read_bytes()==root_bytes
    assert len({a["initial_state_hash"] for a in arms})==1
    return {"seed":seed,"apparatus_generated_after_physical_initialization":True,"identities":identities,
        "authored_motive_policy_willingness":willing,"discovery":learned,"root":root_metrics,"arms":arms}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--seeds",nargs="+",type=int,default=[11,22,33,44,55]);parser.add_argument("--output",type=Path,default=ROOT/"artifacts/phase6_culture.json")
    args=parser.parse_args();args.directory.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter();trials=[]
    for seed in args.seeds:
        try:result=trial(args.directory/f"seed-{seed}",seed)
        except Exception as error:result={"seed":seed,"failure":f"{type(error).__name__}: {error}","arms":[]}
        trials.append(result);print(json.dumps({"seed":seed,"failure":result.get("failure"),"outcomes":[(a["condition"],a["success"]) for a in result["arms"]]}),flush=True)
        args.output.parent.mkdir(exist_ok=True,parents=True)
        report={"phase":6,"provider":"authored bounded observation-only controllers; no LLM, neural training or open-ended discovery claim",
            "build_id":storage.load_native().build_id,"orchestration_id":storage.orchestration_id(),"seeds":args.seeds,
            "trials":trials,"wall_time_s":time.perf_counter()-start,"process_memory":process_memory(),
            "limits":"Five small authored tasks; motive rules and search/controller supplied by us. Episodic ablation disables report retention/retrieval; immediate native report caches and physical skills remain. Controls have one blind attempt, not the teacher's full search budget. No causal claim beyond these tested controllers."}
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    if any(t.get("failure") for t in trials):raise SystemExit("Some trials failed; exact failures retained in the report")


if __name__=="__main__":main()
