import copy
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from underworld import storage, culture, cognition
from underworld.config import load,validate
from underworld.native import load_native
from underworld.policy import _waypoint
from underworld.wire import dumps

ROOT=Path(__file__).resolve().parents[1]


def action(w,kind,targets=(),params=None,agent="agent-1",seconds=1):
    o=w.observe_batch([agent])[0]
    return {"schema_version":1,"run_id":o["run_id"],"request_id":f"{kind}-{agent}-{o['tick']}-{w.snapshot()['last_event_seq']}","agent_id":agent,
        "observation_version":o["tick"],"action_type":kind,"target_ids":list(targets),"parameters":params or {},"requested_duration":seconds}


def act(w,kind,targets=(),params=None,agent="agent-1",seconds=1):
    a=action(w,kind,targets,params,agent,seconds)
    r=w.submit(a,agent)
    if r["status"]=="accepted":w.step(math.ceil(seconds/.2-1e-12))
    w.check_invariants()
    return next((r for r in w.observe_batch([agent])[0]["recent_action_results"] if r["request_id"]==a["request_id"]),r)


def navigate(w,agent,goal):
    for _ in range(32):
        o=w.observe_batch([agent])[0];position=o["own_state"]["position_m"]
        if math.dist(position,goal)<.01:return
        point=_waypoint(position,goal,o["visible_entities"],o["world_bounds_m"])
        if point is None:raise AssertionError("navigation failed")
        act(w,"move",params={"x_m":point[0],"y_m":point[1]},agent=agent,seconds=math.ceil(math.dist(position,point)/.2)*.2)
    raise AssertionError("navigation limit")


def fixture(apparatus=7,population=2):
    def build(temperature):
        w=load_native().World(seed=123,population=population,width=16,height=16,dt=.2,bodies=True,scripted=False)
        w.configure_thermal(temperature_k=temperature);w.configure_culture(apparatus);return w
    probe=build(293.15)
    # Privileged test fixture setup only. Experiment policies never read this apparatus answer.
    answer=probe.snapshot()["culture"]["hidden_apparatus"]
    return build(answer["target_k"]),answer


class CultureNativeTests(unittest.TestCase):
    def test_apparatus_is_seeded_hidden_until_instrument_and_recipe_unknown(self):
        a,_=fixture(7);b,_=fixture(8)
        self.assertNotEqual(a.snapshot()["culture"]["hidden_apparatus"],b.snapshot()["culture"]["hidden_apparatus"])
        obs=a.observe_batch(["agent-1"])[0]
        for hidden in ("hidden_apparatus","target_k","apparatus_seed"):self.assertNotIn(hidden,dumps(obs))
        self.assertNotIn("apparatus_dials",obs["own_state"])
        act(a,"inspect",["thermal-1"],seconds=.2)
        self.assertEqual(len(a.observe_batch(["agent-1"])[0]["own_state"]["apparatus_dials"]),4)
        before=a.checkpoint()
        with self.assertRaises(ValueError):a.configure_culture(8)
        self.assertEqual(before,a.checkpoint())

    def test_only_successful_physical_practice_changes_capped_efficiency(self):
        w,answer=fixture();act(w,"inspect",["thermal-1"],seconds=.2)
        wrong=next(d for d in w.observe_batch(["agent-1"])[0]["own_state"]["apparatus_dials"] if d!=answer["dial"])
        r=act(w,"process_batch",["thermal-1"],{"dial":wrong},seconds=4)
        self.assertEqual(r["error_code"],"PROCESS_CONDITIONS")
        self.assertEqual(w.observe_batch(["agent-1"])[0]["own_state"]["skills"]["water_conditioning"]["level"],0)
        durations=[]
        for _ in range(5):
            skill=w.observe_batch(["agent-1"])[0]["own_state"]["skills"]["water_conditioning"]
            duration=math.ceil(skill["min_duration_s"]/.2-1e-12)*.2;durations.append(duration)
            r=act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},seconds=duration)
            self.assertEqual(r["status"],"completed")
        self.assertEqual([round(d,1) for d in durations],[4,3.2,2.8,2.4,2.4])
        self.assertEqual(w.observe_batch(["agent-1"])[0]["own_state"]["skills"]["water_conditioning"]["level"],3)
        self.assertEqual(len(w.snapshot()["culture"]["validated_batches"]),5)

    def test_shortcut_and_wrong_temperature_cannot_award_skill(self):
        w,answer=fixture()
        r=act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},seconds=1)
        self.assertEqual(r["status"],"rejected")
        w=load_native().World(population=1,dt=.2,bodies=True,scripted=False);w.configure_thermal(temperature_k=260);w.configure_culture(7)
        r=act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},seconds=4)
        self.assertEqual(r["status"],"failed")
        self.assertEqual(w.snapshot()["culture"]["skills"],{})

    def test_hold_conditions_rechecked_when_peer_turns_heat_on(self):
        w,answer=fixture();navigate(w,"agent-1",(3,3));navigate(w,"agent-2",(3,4.2))
        pending=action(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},agent="agent-2",seconds=4)
        w.submit(pending,"agent-2");w.step(5)
        act(w,"operate_heat",["thermal-1"],{"mode":"electric"});w.step(10)
        result=next(r for r in w.observe_batch(["agent-2"])[0]["recent_action_results"] if r["request_id"]==pending["request_id"])
        self.assertEqual(result["error_code"],"PROCESS_CONDITIONS");self.assertEqual(w.snapshot()["culture"]["validated_batches"],[])

    def test_gifts_conserve_mass_and_create_only_observed_edges(self):
        w,_=fixture(population=3)
        act(w,"gather",["resource-1"],{"mass_kg":.2});navigate(w,"agent-1",(3,3));navigate(w,"agent-2",(3,4.2))
        before=w.snapshot()["material_totals_ug"]
        r=act(w,"give",["agent-2"],{"material":"food","mass_kg":.1})
        self.assertEqual(r["status"],"completed")
        self.assertEqual(before,w.snapshot()["material_totals_ug"])
        self.assertEqual(w.observe_batch(["agent-2"])[0]["own_state"]["inventory_ug"]["food"],"100000000")
        self.assertTrue(w.observe_batch(["agent-1"])[0]["social_reports"])
        self.assertEqual(w.observe_batch(["agent-3"])[0]["social_reports"],[])
        r=act(w,"give",["agent-2"],{"material":"food","mass_kg":.2})
        self.assertEqual(r["error_code"],"INSUFFICIENT_RESOURCE")

    def test_optional_agreements_decline_accept_complete_and_expire(self):
        w,answer=fixture();navigate(w,"agent-1",(3,3));navigate(w,"agent-2",(3,4.2))
        proposal=action(w,"offer_task",["agent-2"],{"text":"Condition water together"})
        w.submit(proposal,"agent-1");w.step(5);agreement=proposal["request_id"]
        self.assertEqual(w.snapshot()["culture"]["agreements"][0]["status"],"offered")
        act(w,"respond_task",params={"agreement_id":agreement,"accept":False},agent="agent-2")
        self.assertEqual(w.snapshot()["culture"]["agreements"][0]["status"],"declined")
        proposal=action(w,"offer_task",["agent-2"],{"text":"Condition water together"});w.submit(proposal,"agent-1");w.step(5)
        act(w,"respond_task",params={"agreement_id":proposal["request_id"],"accept":True},agent="agent-2")
        act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},agent="agent-2",seconds=4)
        self.assertEqual(w.snapshot()["culture"]["agreements"][-1]["status"],"completed")
        proposal=action(w,"offer_task",["agent-2"],{"text":"Optional next batch"});w.submit(proposal,"agent-1");w.step(605)
        self.assertEqual(next(g for g in w.snapshot()["culture"]["agreements"] if g["id"]==proposal["request_id"])["status"],"expired")

    def test_agent_written_book_costs_paper_and_survives_author_departure(self):
        w,answer=fixture();navigate(w,"agent-1",(3,3))
        act(w,"gather",["resource-3"],{"mass_kg":.02})
        validation=act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},seconds=4)
        text=culture.procedure_text(answer["dial"],answer["target_k"])
        before=w.snapshot()["material_totals_ug"]
        invalid=act(w,"write_book",params={"text":text,"evidence_ref":"99999"},seconds=5)
        self.assertEqual(invalid["error_code"],"PROVENANCE_UNAVAILABLE")
        receipt=act(w,"write_book",params={"text":text,"evidence_ref":validation["event_refs"][1]},seconds=5)
        book=receipt["observable_effects"]["description"].removeprefix("written:")
        self.assertEqual(before,w.snapshot()["material_totals_ug"])
        self.assertEqual(w.observe_batch(["agent-1"])[0]["own_state"]["inventory_ug"]["inert_material"],"10000000")
        act(w,"depart");navigate(w,"agent-2",(3,3.8))
        self.assertNotIn(text,dumps(w.observe_batch(["agent-2"])))
        act(w,"inspect",[book],agent="agent-2",seconds=.2)
        self.assertNotIn(text,dumps(w.observe_batch(["agent-2"])))
        act(w,"read",[book],agent="agent-2")
        read=w.observe_batch(["agent-2"])[0]["read_reports"][-1]
        self.assertEqual(read["text"],text);self.assertEqual(read["origin_event_seq"],validation["event_refs"][1])
        self.assertEqual(read["speaker_id"],"agent-1");self.assertNotEqual(read["parent_event_seq"],"0")
        self.assertEqual(w.observe_batch(["agent-2"])[0]["own_state"]["skills"]["water_conditioning"]["level"],0)
        self.assertFalse(w.observe_batch(["agent-1"])[0]["own_state"]["present"])
        self.assertNotIn("agent-1",[e["entity_id"] for e in w.observe_batch(["agent-2"])[0]["visible_entities"]])
        self.assertEqual(act(w,"speak",params={"text":"I am absent"})["error_code"],"ABSENT")
        reproduced=act(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},agent="agent-2",seconds=4)
        self.assertEqual(reproduced["status"],"completed")
        w._configure_branch(True,6)
        s=w.snapshot()
        w.intervene({"schema_version":1,"run_id":s["run_id"],"branch_id":s["branch_id"],"intervention_id":"occupy-departed-space",
            "observation_version":s["tick"],"kind":"avatar_message","parameters":{"x_m":3,"y_m":3,"text":"Archived actors no longer collide."}},"operator")
        w.check_invariants()

    def test_native_checkpoint_preserves_exposure_agreements_skills_and_books(self):
        w,answer=fixture();a=action(w,"process_batch",["thermal-1"],{"dial":answer["dial"]},seconds=4)
        w.submit(a,"agent-1");w.step(7)
        restored=load_native().World.restore(w.checkpoint());w.step(25);restored.step(25)
        self.assertEqual(w.checkpoint(),restored.checkpoint())

    def test_social_and_procedure_tool_compiler_rejects_forged_access(self):
        w,answer=fixture();obs=w.observe_batch(["agent-1"])[0]
        def plan(intent,target="",text="",evidence=None):return dumps({"intent":intent,"target":target,"text":text,"evidence":evidence or [],"interpretation":"Tentative procedure"})
        with self.assertRaises(ValueError):cognition.compile_plan(plan("process_batch","thermal-1",answer["dial"]),obs,[],1)
        act(w,"inspect",["thermal-1"],seconds=.2);obs=w.observe_batch(["agent-1"])[0]
        _,a=cognition.compile_plan(plan("process_batch","thermal-1",answer["dial"]),obs,[],2)
        self.assertEqual(a["requested_duration"],4)
        self.assertEqual(w.submit(a,"agent-1")["status"],"accepted")
        with self.assertRaises(ValueError):cognition.compile_plan(plan("write_book",text="PROCEDURE forged"),obs,[],3)
        with self.assertRaises(ValueError):cognition.compile_plan(plan("accept_task","foreign-task"),obs,[],3)


class CulturePersistenceTests(unittest.TestCase):
    def test_episodic_ablation_does_not_erase_physical_practice_or_social_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            config=load(ROOT/"config/culture.toml");config["culture"]["episodic_memory"]=False
            path=Path(folder)/"disabled.sqlite";storage.create(path,config,scripted=False)
            # Actual report acquisition is still modeled; episodic retention/recall is disabled.
            config_read=storage.observe(path,["agent-1"])[0]
            a={"schema_version":1,"run_id":config_read["run_id"],"agent_id":"agent-1","request_id":"speech","observation_version":"0","action_type":"speak","target_ids":[],"parameters":{"text":"Report"},"requested_duration":1}
            storage.advance(path,5,[(0,a)])
            self.assertEqual(storage.mind(path,"agent-1")["episodes"],[])
            self.assertEqual(culture.recall(path,"agent-1")["status"],"unknown")
            with closing(sqlite3.connect(path)) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],0)
            self.assertTrue(storage.replay(path)["replay_matches"])

    def test_persisted_procedure_private_recall_restart_and_replay(self):
        from underworld.lab_policy import Driver
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"culture.sqlite";backup=Path(folder)/"saved.sqlite"
            config=load(ROOT/"config/culture.toml");storage.create(path,config,scripted=False)
            teacher=Driver(path,"agent-1");teacher.navigate((3,3));teacher.act("gather",["resource-3"],{"mass_kg":.02})
            learned=teacher.discover();self.assertNotIn("error",learned)
            text=culture.procedure_text(learned["dial"],learned["temperature_k"])
            r=teacher.act("write_book",parameters={"text":text,"evidence_ref":learned["validation_event"]},seconds=5)
            book=r["observable_effects"]["description"].removeprefix("written:")
            teacher.act("depart");student=Driver(path,"agent-2");student.navigate((3,3.8));student.act("read",[book])
            own=culture.recall(path,"agent-2");self.assertEqual(own["status"],"reported")
            self.assertEqual(culture.recall(path,"agent-1")["status"],"unknown")
            storage.save(path,"cultural-artifact",backup)
            result=subprocess.run([sys.executable,"-m","underworld","procedure","--db",str(backup),"--agent","agent-2"],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),own)
            before=path.read_bytes()
            def fault(stage,tick):
                if stage=="before_commit":raise RuntimeError("rollback culture")
            with self.assertRaises(RuntimeError):storage.advance(path,1,fault=fault)
            self.assertEqual(before,path.read_bytes())
            student.warm(own["claims"][0]["procedure"]["temperature_k"])
            self.assertEqual(student.process(own["claims"][0]["procedure"]["dial"])["status"],"completed")
            self.assertTrue(storage.replay(path)["replay_matches"])

    def test_invalid_configuration_and_procedure_syntax_and_optional_motives(self):
        config=load(ROOT/"config/culture.toml")
        for key,value in (("apparatus_seed",True),("apparatus_seed",-1),("episodic_memory",0),("extra",True)):
            bad=copy.deepcopy(config);bad["culture"][key]=value
            with self.assertRaises(ValueError):validate(bad)
        for text in ('PROCEDURE {"execute":"anything"}','not a procedure','PROCEDURE {"task":NaN}'):
            self.assertIsNone(culture.parse_procedure(text))
        self.assertFalse(culture.willing_to_share({"motivations":["preserve supplies"]}))
        self.assertTrue(culture.willing_to_share({"motivations":["share useful observations"]}))


if __name__=="__main__":unittest.main()
