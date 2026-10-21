import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const [url,output]=process.argv.slice(2);
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(url);await page.waitForFunction(()=>document.getElementById('clock').textContent.includes('simulated s'));
 const packet=await page.evaluate(async()=>(await(await fetch('/api/viewer')).json()));
 assert.equal(packet.controls.read_only,true);
 assert.ok(packet.integration.archive_epoch>0);
 assert.ok((await page.locator('#integration-state').innerText()).includes('History epoch'));
 assert.ok((await page.locator('#integration-details').textContent()).includes('Operator diagnostics'));
 assert.equal(JSON.stringify(packet.selected).includes('operator_diagnostics'),false);
 assert.equal(packet.knowledge.agent,packet.selected.agent_id);
 assert.equal(await page.locator('#play').isDisabled(),true);
 await page.selectOption('#agent','agent-2');
 await page.waitForFunction(()=>document.getElementById('identity').textContent.includes('agent-2'));
 await page.waitForFunction(()=>document.getElementById('integration-state').textContent.includes('operator:g-care'));
 await page.screenshot({path:output+'.png',fullPage:true});
 await page.goto(new URL('/',url).href);
 await page.waitForFunction(()=>document.getElementById('time').textContent.includes('Tick'));
 await page.selectOption('#agent','agent-2');
 await page.waitForFunction(()=>document.getElementById('integration-state').textContent.includes('operator:g-care'));
 assert.equal(await page.locator('#pause').isDisabled(),true);
 assert.equal(await page.locator('#apply-intervention').isDisabled(),true);
 await page.screenshot({path:output+'-2d.png',fullPage:true});
 assert.deepEqual(errors,[]);
 const report={passed:true,page_errors:errors,epoch:packet.integration.archive_epoch,
  tools:packet.integration.tools,pen_components:packet.snapshot.entities.filter(e=>['fence','gate'].includes(e.kind)).map(e=>({id:e.entity_id,kind:e.kind,position:e.position_m})),
  native_build_id:packet.snapshot.build_id,private_observation_has_operator_diagnostics:false,
  source_shown:'operator:g-care',read_only:true,render:'headless Edge/software; no hardware FPS claim'};
 await fs.writeFile(output+'.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:true,page_errors:errors}));
}finally{await browser.close();}
