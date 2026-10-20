// Existing local Playwright development dependency; no download or CDN.
import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';

const url=process.argv[2]||'http://127.0.0.1:8767/viewer';
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try {
 await page.goto(url);
 await page.waitForFunction(()=>document.getElementById('clock').textContent.includes('simulated s'));
 const evidence=await page.evaluate(async()=>{
  const packet=await(await fetch('/api/viewer')).json();
  const {WorldView}=await import('/scene.js');
  const host=document.createElement('div');host.style.cssText='position:absolute;width:400px;height:300px;left:0;top:0';document.body.append(host);
  const view=new WorldView(host,()=>{},()=>{});
  const tree=packet.snapshot.entities.find(e=>e.entity_id==='tree-2'),snapshot=structuredClone(packet.snapshot);
  const index=snapshot.entities.findIndex(e=>e.entity_id===tree.entity_id);
  snapshot.entities[index].stage='mature';view.update(snapshot,tree.entity_id);
  const before=view.objects.get(tree.entity_id).children.length;
  view.update(packet.snapshot,tree.entity_id);
  const after=view.objects.get(tree.entity_id).children.length;
  view.dispose();host.remove();
  return {controller:packet.controller,tree_stage:tree.stage,mature_children:before,stump_children:after,
   structure:packet.snapshot.entities.find(e=>e.kind==='storage_box'),controls:packet.controls,
   controller_text:document.getElementById('controller-status').textContent,
   render:window.UnderworldViewer.metrics(),tick:packet.snapshot.tick,hash:packet.snapshot.state_hash};
 });
 assert.equal(evidence.controller.active,'stabilization');
 assert.ok(evidence.controller_text.includes('model calls 0/0'));
 assert.equal(evidence.tree_stage,'stump');assert.equal(evidence.mature_children,2);assert.equal(evidence.stump_children,1);
 assert.ok(evidence.structure);assert.equal(evidence.controls.read_only,true);assert.equal(evidence.render.unavailable,undefined);
 assert.equal(errors.length,0);
 await page.screenshot({path:'artifacts/living_world_c_viewer.png',fullPage:true});
 await fs.writeFile('artifacts/living_world_c_viewer.json',JSON.stringify({url,mode:'headless Edge with software rendering; no hardware performance claim',...evidence,page_errors:errors},null,2)+'\n');
 console.log(JSON.stringify({passed:true,tick:evidence.tick,tree_lifecycle_refreshed:true,box:evidence.structure.entity_id,controller:evidence.controller.active}));
} finally {await browser.close();}
