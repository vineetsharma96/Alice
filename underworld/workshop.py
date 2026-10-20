"""Explicit operator-assigned production demonstration, not autonomous planning.

Every effect is requested through native validation or the durable coordinator.
The fixed 8 m layout and route are a fixture; generalized planning is milestone E.
"""
import math
from . import storage
from .native import load_native

class AssignedProcedure:
    def __init__(self, world=None, db=None):
        self.world = world or load_native().World(seed=21,population=1,width=8,height=8,dt=.2,scripted=False,bodies=True)
        self.db=db
        self.receipts=[]

    def snapshot(self):return storage.inspect(self.db) if self.db else self.world.snapshot()
    def observe(self,agent='agent-1'):return storage.observe(self.db,[agent])[0] if self.db else self.world.observe_batch([agent])[0]
    def step(self,ticks):
        if self.db:storage.advance(self.db,ticks)
        else:self.world.step(ticks)
    def submit(self,kind,targets=(),params=None,duration=1,agent='agent-1'):
        o=self.observe(agent)
        request=dict(schema_version=1,run_id=o['run_id'],agent_id=agent,request_id=f"c-{kind}-{o['tick']}-{len(self.receipts)}",observation_version=o['tick'],action_type=kind,target_ids=list(targets),parameters=params or {},requested_duration=duration)
        if self.db:
            # One coordinator, one lease, real native receipts; never edit database state.
            storage.advance(self.db,1,[(int(o['tick']),request)])
            r=next(r for r in self.observe(agent)['recent_action_results'] if r['request_id']==request['request_id'])
        else:r=self.world.submit(request,agent)
        self.receipts.append(dict(request=request,submitted=r))
        return request,r
    def act(self,kind,targets=(),params=None,duration=1,agent='agent-1'):
        request,r=self.submit(kind,targets,params,duration,agent)
        if r['status']=='rejected':raise AssertionError(r)
        self.step(math.ceil(duration/self.observe(agent)['dt_s']))
        r=next(r for r in self.observe(agent)['recent_action_results'] if r['request_id']==request['request_id'])
        self.receipts[-1]['terminal']=r
        if r['status']!='completed':raise AssertionError(r)
        return r
    def move(self,x,y):
        p=self.observe()['own_state']['position_m'];return self.act('move',params={'x_m':x,'y_m':y},duration=math.dist(p,(x,y))+1)
    def entity(self,kind):
        o=self.observe()
        return next(e for e in [*o['visible_entities'],*o['own_state'].get('tools',[])] if e['kind']==kind)
    def bootstrap(self):
        self.move(2,5)
        self.act('harvest_branch',['tree-1'],{'mass_kg':.5})
        self.move(2.5,4.8)
        self.act('collect_wood',[self.entity('wood')['entity_id']],{'material':'wood','mass_kg':.45})
        self.move(1.2,4.8)
        self.act('collect_wood',[self.entity('fiber')['entity_id']],{'material':'fiber','mass_kg':.05})
        self.move(1.2,2.6)
        self.move(4.5,2.7)
        self.act('collect_wood',['resource-4'],{'material':'stone','mass_kg':.2})
    def axe(self):
        self.bootstrap();self.act('craft',params={'recipe_id':'crude_axe'},duration=4)
        return self.entity('tool')['entity_id']
    def plank_stock(self):
        tool=self.axe();self.move(5.5,3)
        self.act('fell_tree',['tree-2'],{'tool_id':tool},duration=5)
        self.move(5.5,3.7)
        self.move(6.7,3.7)
        self.move(7.2,3.4)
        wood=next(e for e in self.observe()['visible_entities'] if e['kind']=='wood' and int(e['mass_ug'])>=1000000000)
        self.act('collect_wood',[wood['entity_id']],{'material':'wood','mass_kg':1})
        self.act('craft',params={'recipe_id':'planks','tool_id':tool},duration=3)
        return tool
    def site(self,recipe='storage_box',x=6.7,y=4.3):
        self.plank_stock();self.act('begin_construction',params={'recipe_id':recipe,'x_m':x,'y_m':y})
        return self.entity('construction')['entity_id']

