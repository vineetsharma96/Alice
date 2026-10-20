import copy
from contextlib import closing
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from underworld.config import load
from underworld.native import load_native
from underworld import storage
from underworld.wire import loads, dumps

ROOT = Path(__file__).resolve().parents[1]


def request(world, kind="gather", target="resource-1", mass=1, duration=1, rid="test", agent="agent-1", **params):
    snapshot = world.snapshot()
    return {"schema_version":1,"run_id":snapshot["run_id"],"request_id":rid,"agent_id":agent,
            "observation_version":snapshot["observation_version"],"action_type":kind,
            "target_ids":[] if kind=="move" else [target],
            "parameters":params if kind=="move" else {"mass_kg":mass},"requested_duration":duration}


class MechanicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = load_native()

    def world(self, **kwargs):
        return self.native.World(scripted=False, **kwargs)

    def test_replay_restart_rng_scheduler_and_inflight_actions(self):
        full = self.native.World(seed=83)
        split = self.native.World(seed=83)
        full.step(543)
        split.step(123)
        self.assertTrue(split.snapshot()["outstanding_actions"])
        split = self.native.World.restore(split.checkpoint())
        split.step(420)
        self.assertEqual(full.checkpoint(), split.checkpoint())
        other = self.native.World(seed=84)
        other.step(543)
        self.assertNotEqual(full.checkpoint(), other.checkpoint())

    def test_gather_deposit_exact_mass_dedup_and_execution_recheck(self):
        world = self.world(population=1)
        initial = world.snapshot()["material_totals_ug"]
        gather = request(world, mass=10)
        self.assertEqual(world.submit(gather,"agent-1")["status"], "accepted")
        world.step(10)
        state = world.checkpoint()
        self.assertEqual(world.submit(gather,"agent-1")["status"], "completed")
        self.assertEqual(world.checkpoint(), state)
        conflict = gather | {"requested_duration":2}
        self.assertEqual(world.submit(conflict,"agent-1")["error_code"], "INVALID_ARGUMENT")
        world = self.native.World.restore(world.checkpoint())
        self.assertEqual(world.submit(gather,"agent-1")["status"],"completed")
        again = request(world,mass=10,rid="overdraw")
        self.assertEqual(world.submit(again,"agent-1")["error_code"],"INSUFFICIENT_RESOURCE")
        deposit = request(world,"deposit",mass=3,rid="return")
        self.assertEqual(world.submit(deposit,"agent-1")["status"],"accepted")
        world.step(10)
        self.assertEqual(world.snapshot()["material_totals_ug"], initial)
        own = world.observe_batch(["agent-1"])[0]["own_state"]
        self.assertEqual(own["inventory_ug"]["food"], "7000000000")
        overdraw = request(world,"deposit",mass=8,rid="inventory-overdraw")
        self.assertEqual(world.submit(overdraw,"agent-1")["error_code"],"INSUFFICIENT_RESOURCE")
        world.check_invariants()

    def test_competing_transfers_cannot_overdraw_at_completion(self):
        world = self.world(seed=3,population=2)
        # Move second actor close to resource; then both request 10kg from 16kg.
        target = request(world,"move",agent="agent-2",rid="approach",duration=60,x_m=3,y_m=2)
        world.submit(target,"agent-2")
        world.step(600)
        position = world.observe_batch(["agent-2"])[0]["own_state"]["position_m"]
        self.assertAlmostEqual(position[0],3)
        self.assertAlmostEqual(position[1],2)
        for agent in ("agent-1","agent-2"):
            self.assertEqual(world.submit(request(world,mass=10,agent=agent,rid="race"),agent)["status"],"accepted")
        world.step(10)
        statuses = [o["recent_action_results"][-1] for o in world.observe_batch(["agent-1","agent-2"])]
        self.assertEqual(sorted(r["status"] for r in statuses),["completed","failed"])
        self.assertIn("INSUFFICIENT_RESOURCE", [r["error_code"] for r in statuses])
        self.assertEqual(world.snapshot()["material_totals_ug"]["food"],"16000000000")
        world.check_invariants()

    def test_swept_obstacle_collision_and_bounds(self):
        world = self.world(population=1,width=8,height=8,dt=1)
        # Path from (2,3) through central rock (4,4) cannot tunnel through it.
        move = request(world,"move",rid="rock",duration=10,x_m=6,y_m=5)
        self.assertEqual(world.submit(move,"agent-1")["status"],"accepted")
        world.step(10)
        recent = world.observe_batch(["agent-1"])[0]["recent_action_results"]
        self.assertEqual(recent[-1]["error_code"],"COLLISION")
        for x,y in ((-.1,2),(0,2),(8,2),(math.inf,2)):
            action = request(world,"move",rid=f"bound-{x}",x_m=x,y_m=y)
            if math.isfinite(x):
                self.assertEqual(world.submit(action,"agent-1")["status"],"rejected")
            else:
                with self.assertRaises(ValueError):world.submit(action,"agent-1")
        world.check_invariants()

    def test_actor_collision(self):
        world = self.world(seed=11,population=2,width=8,height=8,dt=1)
        own = world.observe_batch(["agent-2"])[0]["own_state"]["position_m"]
        # First actor aims at the occupied position of the second actor.
        world.submit(request(world,"move",rid="occupied",duration=60,x_m=own[0],y_m=own[1]),"agent-1")
        world.step(60)
        self.assertEqual(world.observe_batch(["agent-1"])[0]["recent_action_results"][-1]["error_code"],"COLLISION")
        world.check_invariants()

    def test_schema_stale_targets_authorization_and_observation_isolation(self):
        world = self.world(seed=42,population=2)
        action = request(world)
        for modified in (action|{"schema_version":True},action|{"schema_version":2},action|{"extra":"bad"},
                         action|{"target_ids":["a","b"]},action|{"requested_duration":True},
                         action|{"parameters":{"mass_kg":-1}},action|{"parameters":{"mass_kg":0}},
                         action|{"parameters":{"mass_kg":10.1}},
                         action|{"parameters":{"mass_kg":float("nan")}},action|{"parameters":{"mass_kg":1e-12}}):
            with self.subTest(modified=modified), self.assertRaises(ValueError):world.submit(modified,"agent-1")
        with self.assertRaises(ValueError):world.submit(action,"agent-2")
        with self.assertRaises(ValueError):world.submit(action|{"run_id":"wrong"},"agent-1")
        world.step(1)
        self.assertEqual(world.submit(action,"agent-1")["error_code"],"STALE_OBSERVATION")
        hidden = request(world,target="agent-2",rid="private")
        fabricated = request(world,target="nonexistent",rid="fake")
        self.assertEqual(world.submit(hidden,"agent-1")["error_code"],"TARGET_UNAVAILABLE")
        self.assertEqual(world.submit(fabricated,"agent-1")["error_code"],"TARGET_UNAVAILABLE")
        before = world.checkpoint()
        for _ in range(10):
            observations = world.observe_batch(["agent-1","agent-2"])
            for observation in observations:
                for entity in observation["visible_entities"]:
                    self.assertNotIn("inventory_ug",entity)
                    position = entity["position_m"]
                    own = observation["own_state"]["position_m"]
                    self.assertLessEqual(math.dist(position,own),8)
        self.assertEqual(before,world.checkpoint())

    def test_day_night_boundary_energy(self):
        # Explicit 1-second steps from dawn, through noon, into night; no skipped physical updates.
        world = self.world(population=1,width=8,height=8,dt=1)
        for _ in range(3):world.step(7200)
        self.assertAlmostEqual(world.snapshot()["sunlight_w_m2"],100,places=8)
        self.assertGreater(world.snapshot()["solar_input_j"],0)
        for _ in range(6):world.step(7200)
        self.assertEqual(world.snapshot()["sunlight_w_m2"],0)
        before = world.snapshot()["solar_input_j"]
        world.step(1000)
        self.assertEqual(world.snapshot()["solar_input_j"],before)

    def test_checkpoint_corruption_rejected(self):
        world = self.world()
        for state in ("",world.checkpoint()[:100],world.checkpoint()+"garbage",world.checkpoint().replace("UW6","UW99",1)):
            with self.assertRaises(ValueError):self.native.World.restore(state)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="underworld-tests-")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/"run.sqlite"
        self.config = load(ROOT/"config/baseline.toml")
        self.config["logging"]["event_retention_count"] = 20

    def test_save_resume_replay_and_read_only_observer(self):
        storage.create(self.path,self.config)
        partial = storage.advance(self.path,37)
        copied = self.path.with_name("saved.sqlite")
        storage.save(self.path,"mid-action",copied)
        full = storage.advance(self.path,163)
        resumed = storage.advance(copied,163)
        self.assertEqual(full["state_hash"],resumed["state_hash"])
        self.assertTrue(storage.replay(copied)["replay_matches"])
        before = copied.read_bytes()
        for _ in range(4):
            self.assertEqual(storage.inspect(copied)["tick"],"200")
            storage.observe(copied,["agent-1"])
        self.assertEqual(before,copied.read_bytes())
        self.assertLessEqual(full["retained_events"],20)
        self.assertNotEqual(full["state_hash"],partial["state_hash"])
        with self.assertRaises(FileExistsError):storage.create(copied,self.config)
        with self.assertRaises(sqlite3.IntegrityError):storage.save(copied,"mid-action")

    def test_recorded_external_decisions_replay_without_policy(self):
        initial = storage.create(self.path,self.config,scripted=False)
        world = load_native().World.restore(self._state(),initial["run_id"])
        action = request(world)
        final = storage.advance(self.path,20,[(0,action),(12,action)])
        self.assertEqual(final["recorded_decisions"],2)
        self.assertTrue(storage.replay(self.path)["replay_matches"])
        inv = storage.observe(self.path,["agent-1"])[0]["own_state"]["inventory_ug"]
        self.assertEqual(inv["food"],"1000000000")

    def _state(self):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT state FROM run").fetchone()[0]

    def test_rollback_discards_staged_tick_and_decision(self):
        initial = storage.create(self.path,self.config,scripted=False)
        world = load_native().World.restore(self._state(),initial["run_id"])
        def fault(stage,tick):
            if stage=="before_commit":raise RuntimeError("injected transaction failure")
        with self.assertRaises(RuntimeError):storage.advance(self.path,1,[(0,request(world))],fault)
        self.assertEqual(storage.inspect(self.path)["state_hash"],initial["state_hash"])
        self.assertEqual(storage.inspect(self.path)["recorded_decisions"],0)
        self.assertEqual(storage.inspect(self.path)["retained_events"],0)
        self.assertTrue(storage.replay(self.path)["replay_matches"])

    def test_forced_process_exit_recovers_only_committed_ticks(self):
        storage.create(self.path,self.config)
        script = '''
import os,sys
from underworld import storage
def fault(stage,tick):
    if stage==sys.argv[2] and tick==7: os._exit(77)
storage.advance(sys.argv[1],20,fault=fault)
'''
        for stage,expected in (("before_commit",6),("after_commit",7)):
            with self.subTest(stage=stage):
                # Independent copy of the initial run for each forced exit.
                path = self.path.with_name(stage+".sqlite")
                storage.save(self.path,stage,path)
                result = subprocess.run([sys.executable,"-c",script,str(path),stage],cwd=ROOT,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,77,result.stderr)
                storage.recover(path)
                self.assertEqual(storage.inspect(path)["tick"],str(expected))
                self.assertTrue(storage.replay(path)["replay_matches"])
                storage.advance(path,3)
                self.assertEqual(storage.inspect(path)["tick"],str(expected+3))

    def test_metadata_and_state_corruption_fail_closed(self):
        storage.create(self.path,self.config)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE run SET state=state||'x'")
            db.commit()
        with self.assertRaisesRegex(ValueError,"checksum"):storage.inspect(self.path)

    def test_strict_json_and_cli_roundtrip(self):
        for text in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}', '{"a":[[[[[[1]]]]]]}', '['*2000+'0'+']'*2000):
            with self.assertRaises(ValueError):loads(text)
        def cli(*args):
            r = subprocess.run([sys.executable,"-m","underworld",*args],cwd=ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
            return json.loads(r.stdout)
        cli("new","--db",str(self.path),"--manual")
        before=cli("inspect","--db",str(self.path))
        cli("advance","--db",str(self.path),"--ticks","3")
        cli("save","--db",str(self.path),"--name","cli")
        after=cli("resume","--db",str(self.path),"--ticks","2")
        self.assertEqual(before["tick"],"0")
        self.assertEqual(after["tick"],"5")
        self.assertTrue(cli("replay","--db",str(self.path))["replay_matches"])


if __name__=="__main__":unittest.main()
