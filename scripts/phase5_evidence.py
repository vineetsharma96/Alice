"""Model-off thermal acceptance traces; refuses to overwrite experiment directories."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from underworld import storage
from underworld.config import load
from underworld.native import load_native
from underworld.resources import process_memory


def action(snapshot,kind,targets=(),params=None,duration=1):
    return {"schema_version":1,"run_id":snapshot["run_id"],"agent_id":"agent-1",
        "request_id":f"demo-{kind}-{snapshot['tick']}","observation_version":snapshot["tick"],
        "action_type":kind,"target_ids":list(targets),"parameters":params or {},"requested_duration":duration}


def native_case(name,open_boundaries,mode,oxygen=.04,temperature=293.15,water=.02,seconds=200,dt=.2):
    w=load_native().World(population=1,width=16,height=16,dt=dt,bodies=True,scripted=False)
    w.configure_thermal(open_boundaries,water,.02,oxygen,temperature)
    initial=w.snapshot()
    command=action(initial,"operate_heat",["thermal-1"],{"mode":mode})
    assert w.submit(command,"agent-1")["status"]=="accepted"
    w.step(round(1/dt))
    rows=[];max_error=0;max_thermal_error=0;max_mass_error=0;peak_vapor=0
    for i in range(round(seconds/dt)):
        w.step(1);w.check_invariants();s=w.snapshot();t=s["thermal"];c=t["cells"][0]
        max_error=max(max_error,abs(t["global_balance_error_j"]))
        max_thermal_error=max(max_thermal_error,abs(t["balance_error_j"]))
        total=sum(map(int,s["material_totals_ug"].values()))
        mass_error=total+int(t["outflow_water_ug"])-sum(map(int,initial["material_totals_ug"].values()))
        max_mass_error=max(max_mass_error,abs(mass_error));peak_vapor=max(peak_vapor,int(c["vapor_ug"]))
        assert abs(t["global_balance_error_j"])<=t["energy_tolerance_j"] and mass_error==0
        if i%max(1,round(1/dt))==0 or i==round(seconds/dt)-1:
            rows.append({"time_s":s["simulated_time_s"],"temperature_k":c["temperature_k"],
                "ice_ug":c["ice_ug"],"liquid_ug":c["liquid_ug"],"vapor_ug":c["vapor_ug"],
                "fuel_X_ug":c["fuel_X_ug"],"oxygen_ug":c["oxygen_ug"],"product_P_ug":c["product_P_ug"],
                "stored_energy_j":t["stored_energy_j"],"heater_input_j":t["heater_input_j"],
                "solar_input_j":s["solar_input_j"],"radiation_in_j":t["radiation_in_j"],"radiation_out_j":t["radiation_out_j"],
                "outflow_energy_j":t["outflow_energy_j"],"outflow_water_ug":t["outflow_water_ug"],"global_error_j":t["global_balance_error_j"]})
    trace=ROOT/f"artifacts/phase5_{name}.csv"
    with trace.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    final=w.snapshot();t=final["thermal"]
    return {"name":name,"simulated_seconds":seconds+1,"dt_s":dt,"trace":str(trace.relative_to(ROOT)),
        "max_global_energy_error_j":max_error,"max_thermal_energy_error_j":max_thermal_error,
        "max_mass_error_ug":max_mass_error,"peak_cell1_vapor_ug":peak_vapor,"final":final}


def durable_case(directory):
    path=directory/"lab.sqlite";backup=directory/"inflight.sqlite"
    s=storage.create(path,load(ROOT/"config/thermal-insulated.toml"),scripted=False)
    command=action(s,"operate_heat",["thermal-1"],{"mode":"electric"})
    storage.advance(path,2,[(0,command)]);storage.save(path,"inflight-heat",backup)
    storage.advance(path,1003);storage.advance(backup,1003)
    assert storage.inspect(path)["state_hash"]==storage.inspect(backup)["state_hash"]
    receipts=[]
    def act(kind,targets=(),params=None,duration=1):
        s=storage.inspect(path);command=action(s,kind,targets,params,duration)
        storage.advance(path,round(duration/.2),[(int(s["tick"]),command)])
        receipt=next(r for r in storage.observe(path,["agent-1"])[0]["recent_action_results"] if r["request_id"]==command["request_id"])
        assert receipt["status"]=="completed",receipt
        receipts.append(receipt)
    act("inspect",["thermal-1"])
    act("operate_heat",["thermal-1"],{"mode":"off"})
    act("move",params={"x_m":3,"y_m":4},duration=2)
    act("move_material",["thermal-1","thermal-2"],{"material":"water","mass_kg":.005})
    act("inspect",["thermal-2"])
    replay=storage.replay(path);assert replay["replay_matches"]
    return {"database":str(path),"backup_restart_equal":True,"replay":replay,"receipts":receipts,
        "final":storage.inspect(path),"database_bytes":path.stat().st_size}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--directory",type=Path,default=ROOT/"data/phase5-lab")
    args=parser.parse_args();args.directory.mkdir(parents=True,exist_ok=False)
    (ROOT/"artifacts").mkdir(exist_ok=True);start=time.perf_counter()
    cases=[native_case("closed_burn",False,"burn",oxygen=.01),
           native_case("open_heat",True,"electric"),native_case("oxygen_absent",False,"burn",oxygen=0,seconds=30),
           native_case("ice_heat",False,"electric",temperature=260,seconds=100)]
    assert cases[0]["final"]["thermal"]["burned_fuel_ug"]=="5000000"
    assert cases[1]["peak_cell1_vapor_ug"]>0 and int(cases[1]["final"]["thermal"]["outflow_water_ug"])>0
    assert cases[2]["final"]["thermal"]["burned_fuel_ug"]=="0"
    durable=durable_case(args.directory)
    report={"phase":5,"build_id":load_native().build_id,"orchestration_id":storage.orchestration_id(),
        "provider":"disabled; authored physical actions, no LLM discovery claim","cases":cases,"durable":durable,
        "wall_time_s":time.perf_counter()-start,"process_memory":process_memory(),
        "scope":"Four caloric/enthalpy vessels and one environmental substrate node; fixed 1-atm water thresholds; artificial chemistry; no pressure, flow, PV work or realistic combustion kinetics."}
    output=ROOT/"artifacts/phase5_thermal.json";output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"artifact":str(output),"cases":[{k:c[k] for k in ("name","max_global_energy_error_j","max_mass_error_ug","peak_cell1_vapor_ug")} for c in cases],
        "durable_replay":True,"wall_time_s":report["wall_time_s"]},indent=2))


if __name__=="__main__":main()
