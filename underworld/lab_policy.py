"""Authored bounded experiment controller. Choices use only this actor's permitted observations.

This is a scripted policy, not a model, learned planner, or unrestricted scientific discovery.
"""
import math
import re
from . import storage
from .policy import _waypoint


class Driver:
    def __init__(self,path,agent):self.path,self.agent=path,agent

    def observation(self):return storage.observe(self.path,[self.agent])[0]

    def wait(self,seconds):
        dt=self.observation()["dt_s"]
        storage.advance(self.path,max(1,math.ceil(seconds/dt-1e-12)))

    def act(self,kind,targets=(),parameters=None,seconds=1,allow_failure=False):
        o=self.observation();tick=int(o["tick"]);dt=o["dt_s"]
        request={"schema_version":1,"run_id":o["run_id"],"request_id":f"lab-{self.agent}-{kind}-{tick}",
            "agent_id":self.agent,"observation_version":o["observation_version"],"action_type":kind,
            "target_ids":list(targets),"parameters":parameters or {},"requested_duration":seconds}
        storage.advance(self.path,max(1,math.ceil(seconds/dt-1e-12)),[(tick,request)])
        result=next(r for r in self.observation()["recent_action_results"] if r["request_id"]==request["request_id"])
        if not allow_failure and result["status"]!="completed":raise RuntimeError(f"{kind}: {result}")
        return result

    def navigate(self,goal):
        for _ in range(32):
            o=self.observation();position=o["own_state"]["position_m"]
            if math.dist(position,goal)<.05:return
            point=_waypoint(position,goal,o["visible_entities"],o["world_bounds_m"])
            if point is None:raise RuntimeError("perceived navigation has no route")
            self.act("move",parameters={"x_m":point[0],"y_m":point[1]},seconds=math.ceil(math.dist(position,point)/o["dt_s"])*o["dt_s"],allow_failure=True)
        raise RuntimeError("bounded navigation exhausted")

    def measure(self):
        result=self.act("inspect",["thermal-1"],seconds=.2)
        match=re.search(r"temperature~([0-9]+)K",result["observable_effects"]["description"])
        if not match:raise RuntimeError("thermometer reading unavailable")
        return int(match[1])

    def warm(self,target):
        # Includes one-second physical switch delays. Feedback uses only the 5 K instrument.
        for _ in range(32):
            measured=self.measure()
            if measured>target+5:self.wait(4);continue
            if measured>=target:return
            self.act("operate_heat",["thermal-1"],{"mode":"electric"})
            for _ in range(100):
                if self.measure()>=target-5:break
            else:raise RuntimeError("bounded heating exhausted")
            self.act("operate_heat",["thermal-1"],{"mode":"off"})
            return
        raise RuntimeError("bounded cooling exhausted")

    def process(self,dial):
        o=self.observation();seconds=o["own_state"]["skills"]["water_conditioning"]["min_duration_s"];dt=o["dt_s"]
        return self.act("process_batch",["thermal-1"],{"dial":dial},seconds=math.ceil(seconds/dt-1e-12)*dt,allow_failure=True)

    def discover(self):
        self.measure();dials=self.observation()["own_state"]["apparatus_dials"]
        attempts=[]
        for target in (310,325,340,355):
            for dial in dials:
                self.warm(target);result=self.process(dial)
                attempts.append({"nominal_k":target,"dial":dial,"result":result})
                if result["status"]=="completed":return {"dial":dial,"temperature_k":target,"validation_event":result["event_refs"][1],"attempts":attempts}
        return {"attempts":attempts,"error":"all 16 authored search candidates failed"}
