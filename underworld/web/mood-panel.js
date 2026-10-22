const $=id=>document.getElementById(id);
let busy=false;
async function refresh(){
 if(busy)return;busy=true;
 try{
  const r=await fetch(`/api/mood?agent=${encodeURIComponent($('agent').value)}`,{cache:'no-store'}),p=await r.json();
  if(!r.ok)throw Error(p.error);
  const s=p.person,t=s.temperament;
  $('mood-summary').textContent=`${s.owner} · slow stress ${(s.stress*100).toFixed(1)}% · mood valence ${s.mood.valence.toFixed(3)} · immediate valence ${s.affect.valence.toFixed(3)}`;
  $('mood-meter').value=s.stress;
  $('mood-body').textContent=`Current cold burden ${(s.body.thermal*100).toFixed(1)}% · hunger ${(s.body.hunger*100).toFixed(1)}% · thirst ${(s.body.thirst*100).toFixed(1)}%`;
  $('mood-traits').textContent=`Declared sensitivity ${t.sensitivity}; rise ${t.rise_s}s; recovery ${t.recovery_s}s. ${s.mood_connected?'Bounded mood influence connected.':'Mood influence disconnected.'}`;
  const curve=$('mood-curve');curve.replaceChildren();
  if(p.timeline.length){
   const first=p.timeline[0].seconds,span=Math.max(1,p.timeline.at(-1).seconds-first);
   const line=document.createElementNS('http://www.w3.org/2000/svg','polyline');
   line.setAttribute('points',p.timeline.map(x=>`${5+290*(x.seconds-first)/span},${67-62*x.stress}`).join(' '));
   line.setAttribute('fill','none');line.setAttribute('stroke','#e6bf7c');line.setAttribute('stroke-width','2');curve.append(line);
  }
  $('mood-evidence').textContent=JSON.stringify({profile:s.mode,temperament_origin:s.temperament_origin,last:s.last,source:p.origin},null,2);
  $('mood-source').textContent=`Read-only · native tick ${p.native_tick} · ${p.native_hash.slice(0,16)}. Viewing does not advance time.`;
  window.AliceMood=p;
 }catch(e){$('mood-summary').textContent='Mood evidence unavailable';$('mood-source').textContent=e.message;$('mood-meter').value=0;$('mood-curve').replaceChildren();$('mood-evidence').textContent='';}
 finally{busy=false;}
}
$('agent').addEventListener('change',refresh);$('refresh').addEventListener('click',refresh);refresh();setInterval(refresh,1500);
