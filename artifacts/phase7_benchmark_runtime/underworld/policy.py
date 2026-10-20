"""Authored deterministic utility policy. Receives one permitted observation, never a world/DB."""
import heapq
import math


def _distance(a,b):
    return math.dist(a,b)


def _segment_clear(a,b,solids):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=dx*dx+dy*dy
    for e in solids:
        p=e["position_m"]
        t=0 if not length else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length))
        if math.hypot(a[0]+t*dx-p[0],a[1]+t*dy-p[1]) < .25+e["radius_m"]+.04:
            return False
    return True


def _waypoint(start,goal,visible,bounds):
    """Bounded grid planning over perceived solids only. The native kernel still validates movement."""
    solids=[e for e in visible if e["radius_m"]>0]
    def valid(p):
        return .3<=p[0]<=bounds["width"]-.3 and .3<=p[1]<=bounds["height"]-.3
    if valid(goal) and _segment_clear(start,goal,solids):
        distance=_distance(start,goal)
        return tuple(start[i]+(goal[i]-start[i])*min(1,3/max(distance,.001)) for i in (0,1))
    origin=(round(start[0]),round(start[1]))
    queue=[(_distance(start,goal),0,origin)]
    costs={origin:0}
    first={origin:None}
    best=None
    for _ in range(1024):
        if not queue:break
        _,cost,node=heapq.heappop(queue)
        if cost!=costs[node]:continue
        point=start if node==origin else node
        if _distance(point,goal)<1.1 and _segment_clear(point,goal,solids):
            best=first[node] or goal
            break
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,1),(-1,-1),(1,-1)):
            nxt=(node[0]+dx,node[1]+dy)
            if not valid(nxt) or _distance(start,nxt)>12 or not _segment_clear(point,nxt,solids):continue
            new=cost+_distance(point,nxt)
            if new<costs.get(nxt,float("inf")):
                costs[nxt]=new
                first[nxt]=first[node] or nxt
                heapq.heappush(queue,(new+_distance(nxt,goal),new,nxt))
    return best


def choose(observation,navigation):
    """Returns an action or None; navigation is this actor's bounded checkpointed route state."""
    own=observation["own_state"]
    body=own.get("body")
    if not body or not body["alive"] or not own.get("present",True) or own["busy"]:return None
    tick=int(observation["tick"])
    agent=observation["agent_id"]
    index=int(agent.split("-")[-1])-1
    inventory={kind:int(mass)/1e9 for kind,mass in own["inventory_ug"].items()}
    position=own["position_m"]
    visible=observation["visible_entities"]
    bounds=observation["world_bounds_m"]
    def action(kind,parameters=None,target=None,duration=1):
        return {"schema_version":1,"run_id":observation["run_id"],"request_id":f"utility-{tick}-{agent}",
                "agent_id":agent,"observation_version":observation["observation_version"],"action_type":kind,
                "target_ids":[] if target is None else [target],"parameters":parameters or {},"requested_duration":duration}
    # Compare urgent needs; routine actions do not involve inference or hidden state.
    if body["thirst"]>=.5 and inventory.get("water",0)>=.3:
        return action("drink",{"mass_kg":.3},duration=1)
    if body["hunger"]>=.5 and inventory.get("food",0)>=.2:
        return action("eat",{"mass_kg":.2},duration=2)
    if body["fatigue"]>=.55 and max(body["hunger"],body["thirst"])<.85:
        return action("rest",duration=20)
    desired=[]
    if inventory.get("water",0)<.6:desired.append((body["thirst"],"water",.6))
    if inventory.get("food",0)<.4:desired.append((body["hunger"],"food",.4))
    desired.sort(reverse=True)
    for urgency,kind,amount in desired:
        resources=sorted((e for e in visible if e["kind"]==kind and int(e["mass_ug"])>=1000000),
                         key=lambda e:(_distance(position,e["position_m"]),e["entity_id"]))
        for resource in resources:
            if _distance(position,resource["position_m"])<=1.45:
                available=int(resource["mass_ug"])/1e9
                return action("gather",{"mass_kg":min(amount,available)},resource["entity_id"])
            candidates=[]
            for turn in range(16):
                angle=(turn+index)*math.tau/16
                goal=tuple(resource["position_m"][i]+1.1*(math.cos(angle) if i==0 else math.sin(angle)) for i in (0,1))
                if not (.3<=goal[0]<=bounds["width"]-.3 and .3<=goal[1]<=bounds["height"]-.3):continue
                solids=[e for e in visible if e["radius_m"]>0]
                if _segment_clear(goal,goal,solids):candidates.append(goal)
            for goal in sorted(candidates,key=lambda p:_distance(position,p))[:4]:
                point=_waypoint(position,goal,visible,bounds)
                if point is not None:
                    return action("move",{"x_m":point[0],"y_m":point[1]},duration=5)
    if desired:
        # Exploration is an authored search pattern, not knowledge of hidden resource locations.
        current=navigation.setdefault("waypoint",index*5%16)
        for _ in range(16):
            goal=(1+(bounds["width"]-2)*(current%4)/3,1+(bounds["height"]-2)*(current//4)/3)
            if _distance(position,goal)<.8:
                current=(current+1)%16
                continue
            point=_waypoint(position,goal,visible,bounds)
            if point is not None:
                navigation["waypoint"]=current
                return action("move",{"x_m":point[0],"y_m":point[1]},duration=5)
            current=(current+1)%16
        navigation["waypoint"]=current
    if body["fatigue"]>.25:return action("rest",duration=10)
    return None
