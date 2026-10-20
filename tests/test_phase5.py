import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from underworld import cognition, storage, teaching
from underworld.config import load, validate
from underworld.native import load_native
from underworld.wire import dumps

ROOT=Path(__file__).resolve().parents[1]


def request(world,kind,targets=(),params=None,duration=1,agent="agent-1",rid=None):
    s=world.snapshot() if hasattr(world,"snapshot") else world
    return {"schema_version":1,"run_id":s["run_id"],"agent_id":agent,"request_id":rid or f"{kind}-{s['tick']}",
            "observation_version":s["tick"],"action_type":kind,"target_ids":list(targets),
            "parameters":params or {},"requested_duration":duration}


class ThermalTests(unittest.TestCase):
    def world(self,**kwargs):
        world=load_native().World(population=1,width=16,height=16,dt=.2,bodies=True,scripted=False)
        world.configure_thermal(**kwargs)
        return world

    def act(self,world,kind,targets=(),params=None,duration=1):
        action=request(world,kind,targets,params,duration)
        self.assertEqual(world.submit(action,"agent-1")["status"],"accepted")
        world.step(round(duration/.2))
        results=world.observe_batch(["agent-1"])[0]["recent_action_results"]
        return next(r for r in results if r["request_id"]==action["request_id"])

    def test_initial_stocks_are_counted_once_and_hidden(self):
        w=self.world();s=w.snapshot();w.check_invariants()
        self.assertEqual({k:int(v) for k,v in s["material_totals_ug"].items()},s["initial_mass_ug"])
        obs=dumps(w.observe_batch(["agent-1"]))
        for hidden in ("temperature_k","enthalpy_j","fuel_X_ug","oxygen_ug","heater_input_j"):
            self.assertNotIn(hidden,obs)
        self.assertEqual(len(s["thermal"]["cells"]),4)
        before=w.checkpoint()
        with self.assertRaises(ValueError):w.configure_thermal()
        self.assertEqual(before,w.checkpoint())

    def test_heat_is_timed_energy_costed_and_makes_vapor(self):
        w=self.world(fuel_kg=0,oxygen_kg=0)
        a=request(w,"operate_heat",["thermal-1"],{"mode":"electric"})
        self.assertEqual(w.submit(a,"agent-1")["status"],"accepted")
        w.step(4);self.assertEqual(w.snapshot()["thermal"]["heater_input_j"],0)
        w.step(1);self.assertEqual(w.snapshot()["thermal"]["heater_input_j"],0)
        w.step(1000);s=w.snapshot();t=s["thermal"]
        self.assertAlmostEqual(t["heater_input_j"],200000,places=5)
        self.assertGreater(int(t["cells"][0]["vapor_ug"]),0)
        self.assertGreater(t["cells"][1]["temperature_k"],293.15)
        self.assertEqual(s["solar_input_j"],0)
        self.assertLess(abs(t["global_balance_error_j"]),t["energy_tolerance_j"])
        self.act(w,"operate_heat",["thermal-1"],{"mode":"off"});before=w.snapshot()["thermal"]["heater_input_j"]
        w.step(10);self.assertEqual(before,w.snapshot()["thermal"]["heater_input_j"])

    def test_oxygen_limits_burning_and_closed_energy_is_conserved(self):
        w=self.world(oxygen_kg=.01)
        self.act(w,"operate_heat",["thermal-1"],{"mode":"burn"});w.step(300)
        s=w.snapshot();t=s["thermal"];c=t["cells"][0]
        self.assertEqual((c["fuel_X_ug"],c["oxygen_ug"],c["product_P_ug"]),("15000000","0","15000000"))
        self.assertEqual(t["burned_fuel_ug"],"5000000")
        self.assertAlmostEqual(t["stored_energy_j"],t["initial_energy_j"],places=5)
        self.assertEqual(sum(map(int,s["material_totals_ug"].values())),sum(map(int,s["initial_mass_ug"].values())))
        w.step(100);self.assertEqual(w.snapshot()["thermal"]["burned_fuel_ug"],"5000000")

    def test_zero_oxygen_and_zero_fuel_do_not_burn(self):
        for kwargs in ({"oxygen_kg":0},{"fuel_kg":0}):
            w=self.world(**kwargs);self.act(w,"operate_heat",["thermal-1"],{"mode":"burn"});w.step(100)
            self.assertEqual(w.snapshot()["thermal"]["burned_fuel_ug"],"0")

    def test_open_box_reconciles_vapor_radiation_and_solar(self):
        w=self.world(open_boundaries=True,temperature_k=450)
        w.step(500);s=w.snapshot();t=s["thermal"]
        self.assertGreater(t["radiation_out_j"],0);self.assertGreater(t["outflow_energy_j"],0)
        self.assertGreater(t["solar_transferred_j"],0)
        self.assertEqual(int(s["initial_mass_ug"]["water"])-int(s["material_totals_ug"]["water"]),int(t["outflow_water_ug"]))
        self.assertLess(abs(t["global_balance_error_j"]),t["energy_tolerance_j"])
        cold=self.world(open_boundaries=True,temperature_k=250);cold.step(100)
        self.assertGreater(cold.snapshot()["thermal"]["radiation_in_j"],0)

    def test_transfer_moves_mass_and_heat_and_rechecks_availability(self):
        w=self.world(temperature_k=450)
        self.act(w,"move",params={"x_m":3,"y_m":4},duration=2)
        before=w.snapshot()["thermal"]
        self.act(w,"move_material",["thermal-1","thermal-2"],{"material":"water","mass_kg":.02})
        after=w.snapshot()["thermal"]
        self.assertEqual(after["cells"][0]["water_ug"],"0")
        self.assertEqual(after["cells"][1]["water_ug"],"40000000")
        self.assertAlmostEqual(before["stored_energy_j"],after["stored_energy_j"],places=6)
        self.assertLess(after["cells"][0]["enthalpy_j"],before["cells"][0]["enthalpy_j"])
        a=request(w,"move_material",["thermal-1","thermal-2"],{"material":"water","mass_kg":.001})
        self.assertEqual(w.submit(a,"agent-1")["error_code"],"INSUFFICIENT_RESOURCE")
        w.check_invariants()

    def test_thermal_validation_and_approximate_instrument(self):
        w=self.world()
        for kind,targets,params in (("operate_heat",["thermal-4"],{"mode":"electric"}),
                ("operate_heat",["thermal-1"],{"mode":"magic"}),
                ("move_material",["thermal-1","thermal-2"],{"material":"inert_material","mass_kg":.01})):
            a=request(w,kind,targets,params,rid=str(len(w.checkpoint())))
            self.assertEqual(w.submit(a,"agent-1")["status"],"rejected")
        a=request(w,"operate_heat",["thermal-1"],{"mode":"electric","energy_j":0})
        with self.assertRaises(ValueError):w.submit(a,"agent-1")
        r=self.act(w,"inspect",["thermal-1"])
        self.assertIn("temperature~295K",r["observable_effects"]["description"])
        self.assertIn("liquid~20g",r["observable_effects"]["description"])
        self.assertTrue(r["event_refs"])

    def test_transfer_rechecks_after_vapor_has_left_the_source(self):
        w=self.world(open_boundaries=True,temperature_k=450)
        self.act(w,"move",params={"x_m":3,"y_m":4},duration=2)
        a=request(w,"move_material",["thermal-1","thermal-2"],{"material":"water","mass_kg":.019},duration=60)
        self.assertEqual(w.submit(a,"agent-1")["status"],"accepted")
        w.step(300);w.check_invariants()
        receipt=next(r for r in w.observe_batch(["agent-1"])[0]["recent_action_results"] if r["request_id"]==a["request_id"])
        self.assertEqual(receipt["status"],"failed")
        self.assertEqual(receipt["error_code"],"INSUFFICIENT_RESOURCE")

    def test_wrong_scientific_speech_does_not_change_physics(self):
        a=self.world();b=self.world()
        self.act(a,"speak",params={"text":"Water boils for free and oxygen appears from nothing."})
        b.step(5)
        for w in (a,b):self.act(w,"operate_heat",["thermal-1"],{"mode":"burn"})
        a.step(1000);b.step(1000)
        self.assertEqual(a.snapshot()["thermal"],b.snapshot()["thermal"])
        self.assertEqual(a.snapshot()["material_totals_ug"],b.snapshot()["material_totals_ug"])

    def test_checkpoint_preserves_inflight_transfer_and_heat_remainders(self):
        w=self.world(open_boundaries=True)
        self.act(w,"operate_heat",["thermal-1"],{"mode":"burn"})
        self.act(w,"move",params={"x_m":3,"y_m":4},duration=2)
        action=request(w,"move_material",["thermal-1","thermal-2"],{"material":"fuel_X","mass_kg":.005},duration=2)
        w.submit(action,"agent-1");w.step(3)
        restored=load_native().World.restore(w.checkpoint())
        w.step(200);restored.step(200)
        self.assertEqual(w.checkpoint(),restored.checkpoint())

    def test_compiler_allows_only_reachable_heat_and_water_tools(self):
        w=self.world();obs=w.observe_batch(["agent-1"])[0]
        def plan(intent,target="thermal-1",text=""):
            return dumps({"intent":intent,"target":target,"text":text,"interpretation":"Possibly useful, unverified.","evidence":[]})
        _,action=cognition.compile_plan(plan("heat_burn"),obs,[],1)
        self.assertEqual(action["parameters"],{"mode":"burn"})
        self.assertEqual(w.submit(action,"agent-1")["status"],"accepted")
        with self.assertRaises(ValueError):cognition.compile_plan(plan("heat_burn","thermal-4"),obs,[],2)
        w.step(5);self.act(w,"move",params={"x_m":3,"y_m":4},duration=2)
        obs=w.observe_batch(["agent-1"])[0]
        _,action=cognition.compile_plan(plan("transfer_water",text="thermal-2"),obs,[],3)
        self.assertEqual(action["parameters"],{"material":"water","mass_kg":.005})
        self.assertEqual(w.submit(action,"agent-1")["status"],"accepted")

    def test_timestep_refinement(self):
        values=[]
        for dt in (.1,.2,1):
            w=load_native().World(population=1,width=16,height=16,dt=dt,bodies=True,scripted=False)
            w.configure_thermal()
            a=request(w,"operate_heat",["thermal-1"],{"mode":"electric"})
            w.submit(a,"agent-1");w.step(round(1/dt));w.step(round(100/dt))
            w.check_invariants();values.append(w.snapshot()["thermal"]["cells"][0]["temperature_k"])
        self.assertLess(max(values)-min(values),1e-7)

    def test_config_bounds_and_initialization_fail_without_mutation(self):
        c=load(ROOT/"config/thermal-insulated.toml")
        for field,value in (("water_kg",-.1),("temperature_k",1001),("enabled",1),("oxygen_kg",.0000000001)):
            bad=copy.deepcopy(c);bad["thermal"][field]=value
            with self.assertRaises(ValueError):validate(bad)
        w=load_native().World(bodies=True,scripted=False);before=w.checkpoint()
        with self.assertRaises(ValueError):w.configure_thermal(fuel_kg=-1)
        self.assertEqual(w.checkpoint(),before)


class ThermalPersistenceTests(unittest.TestCase):
    def test_durable_heat_receipts_rollback_save_replay_and_fork(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"lab.sqlite";backup=Path(folder)/"saved.sqlite";branch=Path(folder)/"fork.sqlite"
            config=load(ROOT/"config/thermal-insulated.toml")
            s=storage.create(path,config,scripted=False)
            action=request(s,"operate_heat",["thermal-1"],{"mode":"electric"})
            storage.advance(path,3,[(0,action)]);storage.save(path,"inflight",backup)
            storage.advance(path,20);storage.advance(backup,20)
            self.assertEqual(storage.inspect(path)["state_hash"],storage.inspect(backup)["state_hash"])
            self.assertTrue(storage.replay(path)["replay_matches"])
            before=path.read_bytes()
            def fail(stage,tick):
                if stage=="before_commit":raise RuntimeError("staged heat rollback")
            with self.assertRaises(RuntimeError):storage.advance(path,1,fault=fail)
            self.assertEqual(before,path.read_bytes())
            s=storage.inspect(path);action=request(s,"inspect",["thermal-1"])
            storage.advance(path,5,[(int(s["tick"]),action)])
            with closing(sqlite3.connect(path)) as db:
                records=" ".join(row[0] for row in db.execute("SELECT payload FROM episodes"))
                self.assertIn("temperature~",records)
            teaching.fork(path,branch,mode="guided")
            self.assertEqual(storage.inspect(path)["thermal"],storage.inspect(branch)["thermal"])
            self.assertTrue(storage.replay(branch)["replay_matches"])


if __name__=="__main__":unittest.main()
