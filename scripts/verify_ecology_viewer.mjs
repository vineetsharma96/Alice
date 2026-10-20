// Functional presentation check using existing local Playwright, no downloads.
import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const url=process.argv[2]||'http://127.0.0.1:8767/viewer';
const output=process.argv[3]||'artifacts/living_world_d_viewer';
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(url);await page.waitForFunction(()=>document.getElementById('clock').textContent.includes('simulated s'));
 const evidence=await page.evaluate(async()=>{
  const packet=await(await fetch('/api/viewer')).json();const {WorldView}=await import('/scene.js');
  const host=document.createElement('div');host.style.cssText='position:absolute;width:400px;height:300px;left:0;top:0';document.body.append(host);
  const view=new WorldView(host,()=>{},()=>{});view.update(packet.snapshot,'animal-1');
  const animals=packet.snapshot.entities.filter(e=>e.kind==='animal').map(e=>({id:e.entity_id,children:view.objects.get(e.entity_id).children.length,position:view.objects.get(e.entity_id).position.toArray()}));
  const changed=structuredClone(packet.snapshot),animal=changed.entities.find(e=>e.entity_id==='animal-1');animal.position_m=[5,7];animal.alive=false;
  view.update(changed,'animal-1');const dead_rotation=view.objects.get('animal-1').rotation.z,moved=view.objects.get('animal-1').position.toArray();
  const forage=changed.entities.find(e=>e.kind==='forage');forage.mass_ug='0';view.update(changed,'animal-1');const depleted_scale=view.objects.get(forage.entity_id).scale.x;
  view.dispose();host.remove();
  return {native_build_id:packet.snapshot.build_id,controller:packet.controller.active,read_only:packet.controls.read_only,animals,dead_rotation,moved,depleted_scale,
    private_animal_fields_leaked:packet.selected.visible_entities.some(e=>e.kind==='animal'&&('body' in e||'inventory_ug' in e||'familiarity' in e)),
    render:window.UnderworldViewer.metrics(),tick:packet.snapshot.tick,hash:packet.snapshot.state_hash};
 });
 assert.equal(evidence.controller,'stabilization');assert.equal(evidence.read_only,true);assert.equal(evidence.animals.length,2);
 assert.notEqual(evidence.animals[0].children,evidence.animals[1].children);assert.equal(evidence.dead_rotation,Math.PI/2);assert.deepEqual(evidence.moved,[5,0,-7]);
 assert.equal(evidence.depleted_scale,.05);assert.equal(evidence.private_animal_fields_leaked,false);assert.equal(errors.length,0);
 await page.screenshot({path:`${output}.png`,fullPage:true});
 await page.goto(new URL('/',url).href);await page.waitForFunction(()=>document.getElementById('time').textContent.includes('Tick'));
 const observer=await page.evaluate(()=>({read_only:document.getElementById('status').textContent,pause_disabled:document.getElementById('pause').disabled,step_disabled:document.getElementById('step').disabled,speed_disabled:document.getElementById('speed').disabled}));
 assert.equal(observer.pause_disabled,true);assert.equal(observer.step_disabled,true);assert.equal(observer.speed_disabled,true);assert.equal(errors.length,0);
 await page.screenshot({path:`${output}-2d.png`,fullPage:true});
 await fs.writeFile(`${output}.json`,JSON.stringify({passed:true,url,mode:'headless Edge/software rendering; no hardware performance claim',...evidence,observer,page_errors:errors},null,2)+'\n');
 console.log(JSON.stringify({passed:true,animals:evidence.animals,private_animal_fields_leaked:false,page_errors:errors}));
}finally{await browser.close();}
