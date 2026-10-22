const text=(id,value)=>{document.getElementById(id).textContent=typeof value==='string'?value:JSON.stringify(value,null,2);};
let busy=false;
async function refresh(){
 if(busy)return;busy=true;
 try{
  const agent=document.getElementById('agent').value;
  const r=await fetch(`/api/emotion?agent=${encodeURIComponent(agent)}`,{cache:'no-store'});
  const p=await r.json();if(!r.ok)throw Error(p.error);
  const s=p.person;
  text('affect-state',{owner:s.owner,profile:s.mode,initial_bias:s.initial_bias,body:s.body,affect:s.affect,slow_stress:s.stress});
  text('affect-timeline',p.timeline.map(x=>`${x.tick.split(':').at(-1)} ticks · stress ${x.stress.toFixed(3)} · valence ${x.valence.toFixed(3)}`).join('\n'));
  text('affect-appraisal',{episodes:s.episodes,last_update:s.last});
  text('affect-learning',{learned_expectations:s.associations,decision:p.decision_influence,relationships:s.relationships,regulation:s.regulation});
  text('affect-source',`Read-only private evidence · native tick ${p.native_tick} · ${p.native_hash.slice(0,16)}. Viewing does not advance time.`);
  window.AliceEmotion=p;
 }catch(e){for(const id of ['affect-state','affect-timeline','affect-appraisal','affect-learning'])text(id,'Evidence unavailable');text('affect-source',e.message);}
 finally{busy=false;}
}
document.getElementById('agent').addEventListener('change',refresh);
document.getElementById('refresh').addEventListener('click',refresh);
refresh();setInterval(refresh,1500);
