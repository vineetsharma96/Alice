'use strict';
let data;
const get=id=>document.getElementById(id);
function node(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
function render(){
 const id=get('person').value,p=data.people[id],o=p.observation;
 get('status').textContent=`Read-only · ${data.simulated_s} simulated seconds · ${id}`;
 get('current').textContent=[`${id} · tick ${o.tick} · ${o.own_state.busy?'busy':'idle'}`,
  `Health ${o.own_state.body.health.toFixed(3)} · hunger ${o.own_state.body.hunger.toFixed(3)} · thirst ${o.own_state.body.thirst.toFixed(3)}`,
  `Plan: ${p.plan?`${p.plan.goal.action} / ${p.plan.phase} / ${p.plan.steps} steps`:'none'}`,
  `Pending action: ${p.pending?.id??'none'}`,...o.recent_action_results.slice(-3).map(r=>`${r.request_id}: ${r.status} · ${r.observable_effects?.description??''}`)].join('\n');
 get('observation').textContent=JSON.stringify(o,null,2);
 get('counts').replaceChildren(...Object.entries(p.counters).map(([key,value])=>{const n=node('div',key.replaceAll('_',' '));n.className='count';n.append(node('strong',String(value)));return n;}));
 get('meanings').replaceChildren(...(p.glosses.length?p.glosses.map(g=>{const n=node('div');n.className='meaning';n.append(node('code',g.signal),node('p',`${g.possible.join(' or ')||'unknown'} · ${g.uncertainty}`),node('small',`${g.count} exposures · sources: ${g.evidence.join(', ')}`));return n;}):[node('p','No location meanings learned yet.')]));
 get('sources').textContent=Object.values(p.sources).map(s=>`${s.entity_id} · ${s.kind} · ${s.depleted?'insufficient observed stock':'observed stock'} · last seen tick ${s.tick}\nSource: ${s.evidence}`).join('\n\n')||'No sources observed.';
 get('predictions').textContent=JSON.stringify({quality:p.quality,range_evidence:p.range_evidence},null,2);
 get('vocab').replaceChildren(...Object.entries(data.people).map(([name,person])=>{const n=node('details');n.append(node('summary',`${name} · ${Object.keys(person.production).length} private coined factors`),node('pre',JSON.stringify(person.production,null,2)));return n;}));
 get('history').replaceChildren(...p.records.map(r=>{const n=node('details');n.append(node('summary',`${r.kind} · ${r.payload.message?.text??r.payload.role??r.id}`),node('pre',JSON.stringify(r.payload,null,2)));return n;}));
}
async function refresh(){get('refresh').disabled=true;try{const r=await fetch('/api/adaptive',{cache:'no-store'});if(!r.ok)throw new Error('Verified evidence unavailable. No inferred data substituted.');data=await r.json();const selected=get('person').value;get('person').replaceChildren(...Object.keys(data.people).map(id=>{const n=node('option',id);n.value=id;return n;}));if(data.people[selected])get('person').value=selected;render();}catch(e){data=undefined;get('status').textContent=e.message;for(const id of ['current','observation','counts','meanings','sources','predictions','vocab','history'])get(id).replaceChildren();}finally{get('refresh').disabled=false;}}
get('person').addEventListener('change',()=>{if(data)render();});get('refresh').addEventListener('click',refresh);refresh();
