import {WorldView} from './scene.js';
import * as THREE from './vendor/three.module.min.js';
const $=id=>document.getElementById(id),pretty=x=>JSON.stringify(x,null,2);
let current=null,selected='agent-1',view=null,busy=false;
class WeatherView extends WorldView{
 dispose(){this.rain?.geometry.dispose();this.rain?.material.dispose();super.dispose();}
 create(e){
  if(e.kind!=='lean_to'&&!(e.kind==='construction'&&e.recipe_id==='lean_to'))return super.create(e);
  const g=new THREE.Group();g.userData.id=e.entity_id;g.userData.appearance=`${e.kind}/${e.stage??''}`;
  for(const x of [-.8,.8])for(const z of [-.8,.8])this.mesh(g,'box','#9d805a',[x,1,z],[.08,2,.08]);
  if(e.kind==='lean_to')this.mesh(g,'box','#a89c72',[0,2,0],[2.2,.12,2.2]);
  return g;
 }
 weather(c){
  const rain=c.current.rain_mm_h>0.05;
  this.scene.background.set(rain?'#536874':c.current.cloud_fraction>.5?'#7e9291':'#91b5bf');
  this.scene.fog.color.copy(this.scene.background);
  const colors={spring:'#547663',summer:'#698054',autumn:'#8b7850',winter:'#667573'};
  this.floor?.material.color.set(colors[c.season]);
  if(!this.clouds){this.clouds=new THREE.Group();for(let i=0;i<8;i++)this.mesh(this.clouds,'head','#bbc9c8',[3+(i*7)%27,7+(i%2),-3-(i*11)%27],[2.5,.45,1.3]);this.scene.add(this.clouds);}
  this.clouds.visible=c.current.cloud_fraction>.35;
  for(const e of this.snapshot.entities)if(e.kind==='tree'&&e.stage!=='stump'){
   const g=this.objects.get(e.entity_id);if(g?.children[1])g.children[1].material=this.material(colors[c.season]);
  }
  if(!this.rain){
   const positions=new Float32Array(160*6);
   this.rain=new THREE.LineSegments(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:'#b8d8e3',transparent:true,opacity:.5}));
   this.rain.geometry.setAttribute('position',new THREE.BufferAttribute(positions,3));this.scene.add(this.rain);
  }
  const p=this.rain.geometry.attributes.position;
  for(let i=0;i<160;i++){
   const x=(i*7.193)%32,z=-((i*13.317)%32),y=1+((i*.717-Number(c.tick)*.04)%1+1)%1*6;
   p.setXYZ(i*2,x,y,z);p.setXYZ(i*2+1,x+.1,y-.35,z);
  }
  p.needsUpdate=true;this.rain.visible=rain;
 }
}
try{view=new WeatherView($('viewport'),id=>{if(id.startsWith('agent-')){selected=id;refresh();}});$('render-status').textContent='Existing 3D observer / illustrative roof coverage';}
catch(e){$('render-status').textContent=`3D unavailable: ${e.message}. Native evidence remains readable.`;}
function draw(p){
 current=p;const c=p.climate,s=p.snapshot,ids=s.entities.filter(e=>e.kind==='actor').map(e=>e.entity_id);
 $('agent').replaceChildren(...ids.map(id=>new Option(id,id)));$('agent').value=selected;
 $('status').textContent='Read-only / connected';$('error').hidden=true;
 $('season').textContent=`${c.season} · ${c.weather}`;
 $('weather').textContent=`${c.ambient_c.toFixed(1)} °C · rain ${c.current.rain_mm_h.toFixed(2)} mm/hour · wind ${c.current.wind_m_s.map(x=>x.toFixed(1)).join(', ')} m/s`;
 $('calendar').textContent=`${s.simulated_time_s.toFixed(2)} simulated seconds · year ${c.year_index} · phase ${(c.phase_progress*100).toFixed(1)}% · ${c.year_s}s/year · solar day ${c.day_s}s`;
 $('intervention').textContent=c.forced?`FORCED WEATHER / recorded operator intervention until ${c.forced_until_s}s`:`Native seeded climate · ${Object.keys(c.forcing_history).length} recorded weather interventions in history`;
 $('senses').textContent=pretty(p.selected.own_state.weather);
 $('body').textContent=pretty({body:p.selected.own_state.body,exposure:c.exposure[selected],goal:p.selected_policy?.goal??'No authored policy decision yet',last_decision:p.selected_policy?.last??null});
 $('shelters').textContent=pretty(c.shelters);$('diagnostics').textContent=pretty(c);$('source').textContent=`Native state ${p.state_hash.slice(0,16)} · tick ${s.tick}. No viewer clock or GET mutations.`;
 if(view){view.update(s,selected);view.weather(c);}
}
async function refresh(){
 if(busy)return;busy=true;
 try{const response=await fetch(`/api/weather?agent=${encodeURIComponent(selected)}`,{cache:'no-store'});const p=await response.json();if(!response.ok)throw Error(p.error);draw(p);}
 catch(e){$('status').textContent='Disconnected / last scene frozen';$('error').hidden=false;$('error').textContent=e.message;for(const id of ['senses','body','shelters','diagnostics'])$(id).textContent='Evidence unavailable';}
 finally{busy=false;}
}
$('refresh').addEventListener('click',refresh);$('fit').addEventListener('click',()=>view?.fit());$('agent').addEventListener('change',()=>{selected=$('agent').value;refresh();});
window.AliceWeather=Object.freeze({state:()=>current,metrics:()=>view?.metrics()??{unavailable:true}});
addEventListener('pagehide',()=>view?.dispose(),{once:true});refresh();setInterval(refresh,1500);
