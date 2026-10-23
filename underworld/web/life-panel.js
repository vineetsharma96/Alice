const summary=document.getElementById('life-summary'),evidence=document.getElementById('life-evidence');
let busy=false;
async function refresh(){
 if(busy)return;busy=true;
 try{
  const response=await fetch(`/api/mood?agent=${encodeURIComponent(document.getElementById('agent').value)}`,{cache:'no-store'});
  const p=await response.json();if(!response.ok)throw Error(p.error);
  const s=p.person,x=s.life;
  summary.textContent=`${s.owner} · stress ${s.stress.toFixed(3)} · mood ${s.mood.valence.toFixed(3)} · ${s.emotional_memory.entries.length} memory links · ${Object.keys(x.relationships).length} relationships · ${x.deliveries} native signals heard`;
  evidence.textContent=JSON.stringify({body:s.body,affect:s.affect,mood:s.mood,episodes:s.episodes,timeline:p.timeline,initial:s.temperament_origin,memories:s.emotional_memory,last_appraisal:s.last,relationships:x.relationships,inferences:x.inferences,regulation:x.regulation,communication:x.communication,social:x.social,values:x.values,last_decision:x.last_decision},null,2);
 }catch(error){summary.textContent=error.message;evidence.textContent='';}
 finally{busy=false;}
}
document.getElementById('agent').addEventListener('change',refresh);
document.getElementById('refresh').addEventListener('click',refresh);
refresh();setInterval(refresh,1500);
