import {WorldView} from './scene.js';
const $=id=>document.getElementById(id),json=value=>JSON.stringify(value,null,2);
let view=null,state=null,selected='agent-1',agent='agent-1',cursor='0',stream='',session=null,busy=false,polling=false,online=false,pending=null;
const traces=new Map();let lastSample=null,observedRate=0,commandError='';
function error(message=''){$('error').textContent=message;$('error').hidden=!message;}
async function request(url,options={}){const abort=new AbortController(),timeout=setTimeout(()=>abort.abort(),8000);try{const response=await fetch(url,{...options,signal:abort.signal});const value=await response.json();if(!response.ok){const e=Error(value.error||response.statusText);e.status=response.status;throw e;}return value;}finally{clearTimeout(timeout);}}
async function authorize(){session=await request('/api/session');}
function item(title,body){const li=document.createElement('li'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=title;small.textContent=body;li.append(strong,small);return li;}
function select(id){selected=id;const e=state?.snapshot.entities.find(e=>e.entity_id===id);if(e?.kind==='actor')agent=id;view?.select(id);if(state&&state.selected.agent_id===agent)inspect();refresh();}
function inspect(){
 if(!state)return;const s=state.snapshot,e=s.entities.find(e=>e.entity_id===selected);if(!e)return;
 $('entities').value=selected;$('entity-title').textContent=e.entity_id;$('entity-kind').textContent=e.kind.replaceAll('_',' ');
 const cell=s.thermal?.cells.find(c=>c.entity_id===selected);const fields=[['Position',`${e.position_m[0].toFixed(2)}, ${e.position_m[1].toFixed(2)} m`],['Mass',`${(e.mass_kg??0).toFixed(3)} kg`],['Physical radius',`${e.radius_m?.toFixed(2)??'0'} m`]];
  if(cell)fields.push(['Temperature',`${cell.temperature_k.toFixed(2)} K`],['Heater',cell.heater],['Water',`${(Number(cell.water_ug)/1e6).toFixed(2)} g`]);
  if(e.kind==='tree')fields.push(['Stage',e.stage||'unknown'],['Health',`${Math.round((e.health??0)*100)}%`],['Tracked biomass',`${(Number(e.biomass_ug||0)/1e9).toFixed(3)} kg`]);
 if(e.kind==='animal'){
   const animal=s.ecology?.animals?.[selected];
   fields.push(['Handling state',e.stage],['Condition',e.condition],['Controller','Authored native rules']);
   if(animal)fields.push(['Species',animal.species],['Age',`${animal.age_s.toFixed(1)} s`],['Activity',animal.mode],['Food reserve',`${(Number(animal.food_reserve_ug)/1e9).toFixed(3)} kg`],['Water reserve',`${(Number(animal.water_reserve_ug)/1e9).toFixed(3)} kg`]);
  }
 if(e.recipe_id)fields.push(['Recipe',e.recipe_id],['Work',`${e.work_s.toFixed(1)} s`],['Durability',String(e.durability)],['Owner',e.owner_id]);
 if(e.kind==='actor')fields.push(['State',e.present===false?'Departed':e.alive===false?'Dead':'Alive']);
 $('entity-facts').replaceChildren(...fields.flatMap(([key,value])=>{const a=document.createElement('dt'),b=document.createElement('dd');a.textContent=key;b.textContent=value;return[a,b];}));
 $('entity-record').textContent=json(cell?{entity:e,thermal:cell}:e);
 const own=state.selected.own_state,isOwn=selected===state.selected.agent_id;
 $('activity').textContent=e.kind==='actor'?(isOwn?(own.busy?`Action: ${own.action_type}`:'Idle'):(s.outstanding_actions.some(a=>a.agent_id===selected)?'Action in progress':'Idle')):e.kind==='operator_avatar'?'Positioned through the validated operator channel':'';
 $('needs').replaceChildren();if(isOwn&&own.body)for(const key of ['hunger','thirst','fatigue','health']){const row=document.createElement('div');row.className='need';const label=document.createElement('span'),meter=document.createElement('meter'),value=document.createElement('span');label.textContent=key;meter.min=0;meter.max=1;meter.value=own.body[key];meter.setAttribute('aria-label',`${key} for ${agent}`);value.textContent=`${Math.round(own.body[key]*100)}%`;row.append(label,meter,value);$('needs').append(row);}
 $('book-report').hidden=e.kind!=='book';if(e.kind==='book'){const report=state.selected.read_reports?.find(r=>r.source_id===selected);$('book-report').textContent=report?`${report.text}\n\nUnverified accessed report. Source event ${report.source_event_seq}; origin ${report.origin_event_seq??report.source_event_seq}.`:`${agent} has not read this book. Its text is not part of this inhabitant's accessed memory.`;}
}
function draw(packet){
 state=packet;const s=packet.snapshot;const now=performance.now();if(lastSample){const elapsed=(now-lastSample.time)/1000,dt=s.simulated_time_s-lastSample.sim;observedRate=dt>=0?dt/elapsed:0;}lastSample={time:now,sim:s.simulated_time_s};
 if(stream&&stream!==packet.stream_id){traces.clear();cursor='0';selected=agent;}$('trace-status').textContent=packet.event_window.gap?'Retention gap; full snapshot loaded':packet.event_window.more?'Catching up with retained events':'Live retained event window';stream=packet.stream_id;
 for(const e of packet.events)traces.set(e.seq,e);while(traces.size>96)traces.delete(traces.keys().next().value);cursor=packet.event_window.cursor;
 $('events').replaceChildren(...[...traces.values()].reverse().slice(0,32).map(e=>{const li=document.createElement('li');li.textContent=`#${e.seq}  t${e.tick}  ${e.type}  ${e.agent_id||''}  ${e.detail||''}`;return li;}));
 const actors=s.entities.filter(e=>e.kind==='actor');$('population').textContent=`${actors.filter(e=>e.alive!==false&&e.present!==false).length}/${actors.length}`;
 const signature=s.entities.map(e=>e.entity_id).join('|');if($('entities').dataset.signature!==signature){$('entities').dataset.signature=signature;$('entities').replaceChildren(...s.entities.map(e=>new Option(`${e.entity_id} / ${e.kind.replaceAll('_',' ')}`,e.entity_id)));$('agent').replaceChildren(...actors.map(e=>new Option(e.entity_id,e.entity_id)));}
 if(!s.entities.some(e=>e.entity_id===selected))selected=agent;$('agent').value=agent;
 const ctl=packet.controller,cs=ctl?.stabilization,g=cs?.goal;$('controller-status').textContent=ctl?`Controller: ${ctl.active}${cs?` / ${g?`${g.kind} / ${g.phase} / ${g.origin}`:'idle'} / model calls ${cs.calls}/${cs.call_limit} / fallback goals ${cs.fallback_goals} / authored steps ${cs.authored_steps}`:''}`:'';
 $('clock').textContent=`Tick ${s.tick} / ${s.simulated_time_s.toFixed(1)} simulated s`;$('mode').textContent=`${s.mode} mode`;$('branch').textContent=`Branch ${s.branch_id.slice(0,10)}`;
 $('world-size').textContent=`Region / ${s.world_bounds_m.width} x ${s.world_bounds_m.height} m`;
 $('source').textContent=`Snapshot ${s.state_hash.slice(0,12)} / event ${s.last_event_seq}`;
 $('play').textContent=packet.controls.paused?'Resume':'Pause';$('play').disabled=busy||packet.controls.read_only;$('step').disabled=busy||!packet.controls.paused||packet.controls.read_only;$('speed').disabled=busy||packet.controls.read_only;$('speed').value=String(packet.controls.speed);
 $('connection').textContent=packet.controls.read_only?'Read-only attached':packet.controls.paused?'Connected / paused':'Connected / running';error(packet.controls.error||commandError);
 $('identity').textContent=`${packet.mind.identity.name} / ${agent}. ${packet.mind.identity.motivations.join('; ')}.`;
 $('memories').replaceChildren(...packet.mind.episodes.map(e=>item(`${e.kind.replaceAll('_',' ')} / tick ${e.tick}`,`${e.record.text??json(e.record)}${e.record.source_event_seq?` | source #${e.record.source_event_seq}, origin #${e.record.origin_event_seq??e.record.source_event_seq}`:''}`)));
 if(!packet.mind.episodes.length)$('memories').append(item('No accessed episodes','Nothing is invented to fill this view.'));
 $('receipts').textContent=json(packet.selected.recent_action_results);
 const editable=s.mode==='guided'&&packet.controls.paused&&!packet.controls.read_only;
 $('operator-help').textContent=packet.controls.read_only?'Read-only attachment. Use the runner controls separately.':s.mode!=='guided'?'Closed mode. Operator world changes require an explicit guided branch.':!packet.controls.paused?'Pause before applying an intervention.':'Commands are validated and recorded by the engine. Avatar positioning also delivers your text.';
 $('operator-form').querySelectorAll('input,textarea,select,button').forEach(e=>e.disabled=!editable||busy);
 $('history').replaceChildren(...packet.operator_history.slice(0,8).map(h=>item(`${h.request.kind} / tick ${h.tick}`,`id ${h.request.intervention_id} / ${h.result.status} / event ${h.result.event_refs?.join(',')??'see trace'}${h.request.parameters.text?' / operator text: '+h.request.parameters.text:''}`)));
 view?.update(s,selected);inspect();
}
async function refresh(){if(polling)return;polling=true;try{if(!session)await authorize();const requested=agent,packet=await request(`/api/viewer?agent=${encodeURIComponent(agent)}&after=${cursor}`);if(packet.protocol!=='underworld.viewer/1')throw Error('Unsupported viewer protocol');if(requested!==agent)return;if(!online)await authorize();online=true;draw(packet);}catch(e){online=false;$('connection').textContent='Disconnected / retrying';error(`Connection unavailable: ${e.message}. The last snapshot is frozen; no world changes are queued.`);}finally{polling=false;}}
async function poll(){await refresh();setTimeout(poll,state?.event_window.more?100:900);}
async function control(command,value){if(busy||!state)return;busy=true;commandError='';try{await request('/api/control',{method:'POST',headers:{'Content-Type':'application/json','X-Observer-Token':session.token},body:JSON.stringify(value===undefined?{command}:{command,value})});await refresh();}catch(e){if(e.status===403)await authorize();commandError=e.message;error(commandError);}finally{busy=false;await refresh();}}
function fields(){const kind=$('kind').value;$('position-fields').hidden=kind==='broadcast';$('choose-position').hidden=kind==='broadcast';$('material-fields').hidden=!['place_book','introduce_object'].includes(kind);$('material-label').hidden=kind!=='introduce_object';$('text-label').hidden=kind==='introduce_object';}
try{view=new WorldView($('viewport'),select,position=>{$('x').value=position[0].toFixed(2);$('y').value=position[1].toFixed(2);view.groundPicking=false;$('choose-position').setAttribute('aria-pressed','false');});view.onContext=lost=>{$('render-error').hidden=!lost;$('render-reason').textContent=lost?'The graphics context was lost. Restoring graphics never advances the simulation.':'';};}catch(e){$('render-error').hidden=false;$('fps').textContent='3D unavailable';$('render-reason').textContent=`WebGL2 could not start: ${e.message}. Inspection and validated controls remain available below.`;}
function mobile(){ $('entities').size=innerWidth<=800?1:14;}mobile();addEventListener('resize',mobile);
$('entities').addEventListener('change',()=>select($('entities').value));$('agent').addEventListener('change',()=>select($('agent').value));$('focus').addEventListener('click',()=>view?.focus(selected));$('home').addEventListener('click',()=>view?.fit());$('quality').addEventListener('change',()=>view?.setQuality($('quality').value));
$('play').addEventListener('click',()=>control(state.controls.paused?'resume':'pause'));$('step').addEventListener('click',()=>control('step'));$('speed').addEventListener('change',()=>control('speed',Number($('speed').value)));$('kind').addEventListener('change',fields);fields();
$('choose-position').addEventListener('click',()=>{if(!view)return;view.groundPicking=!view.groundPicking;$('choose-position').setAttribute('aria-pressed',String(view.groundPicking));});
$('operator-form').addEventListener('submit',async event=>{event.preventDefault();if(busy||!state)return;busy=true;commandError='';try{
 const kind=$('kind').value,id=crypto.randomUUID().replaceAll('-','');const parameters={};
 if(kind!=='broadcast')Object.assign(parameters,{x_m:Number($('x').value),y_m:Number($('y').value)});
 if(['place_book','introduce_object'].includes(kind))Object.assign(parameters,{entity_id:`${kind==='place_book'?'book':'object'}-${id.slice(0,12)}`,mass_kg:Number($('mass').value),energy_j:Number($('energy').value)});
 if(kind==='introduce_object')parameters.material=$('material').value;else parameters.text=$('text').value;
 if(pending){commandError='An earlier command has an unknown response. Inspect its intervention id in history before sending another command.';error(commandError);return;}
 const payload={schema_version:1,run_id:state.snapshot.run_id,branch_id:state.snapshot.branch_id,intervention_id:id,observation_version:state.snapshot.tick,kind,parameters};pending=payload;
 await request('/api/interventions',{method:'POST',headers:{'Content-Type':'application/json','X-Operator-Token':session.operator_token},body:JSON.stringify(payload)});pending=null;
 }catch(e){if(e.status){pending=null;if(e.status===403)await authorize();}commandError=`${e.message}${pending?` / unknown command response, id ${pending.intervention_id}; inspect history before retrying`:''}`;error(commandError);}finally{busy=false;await refresh();}});
setInterval(()=>{if(view){const m=view.metrics();$('fps').textContent=`${m.fps.toFixed(1)} render fps / ${m.draw_calls} draws`;}const work=state?.performance.simulation_work_s_per_wall_s;$('sim-rate').textContent=`${observedRate.toFixed(2)} observed sim s/wall s${work!==null&&work!==undefined?` / ${work.toFixed(1)} work rate`:''}`;if(pending&&state?.operator_history.some(h=>h.request.intervention_id===pending.intervention_id))pending=null;},1000);
window.UnderworldViewer=Object.freeze({metrics:()=>view?.metrics()??{unavailable:true},projectEntity:id=>view?.project(id),source:()=>({stream,hash:state?.snapshot.state_hash,tick:state?.snapshot.tick,selected,agent,online,cursor,protocol:state?.protocol}),camera:()=>view?view.camera.position.toArray():null});
addEventListener('pagehide',()=>view?.dispose(),{once:true});poll();
