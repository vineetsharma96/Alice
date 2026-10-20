import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const [url,output]=process.argv.slice(2);
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));
try{
 await page.goto(url);await page.waitForFunction(()=>document.getElementById('clock').textContent.includes('simulated s'));
 const before=await page.evaluate(async()=>(await(await fetch('/api/viewer')).json()).snapshot.state_hash);
 await page.selectOption('#agent','agent-2');
 await page.waitForFunction(()=>document.getElementById('identity').textContent.includes('agent-2'));
 await page.selectOption('#kind','inject_knowledge');
 assert.equal(await page.locator('#position-fields').isVisible(),false);
 await page.fill('#text','<script>throw new Error("must remain inert")</script>');
 await page.click('#apply');
 await page.waitForFunction(()=>document.getElementById('knowledge-sources').textContent.includes('operator_injection: 1'));
 await page.screenshot({path:output+'.png',fullPage:true});
 await page.goto(new URL('/',url).href);
 await page.waitForFunction(()=>document.getElementById('time').textContent.includes('Tick'));
 await page.selectOption('#agent','agent-1');
 await page.selectOption('#intervention-kind','inject_knowledge');
 assert.equal(await page.locator('#position-fields').isVisible(),false);
 await page.fill('#operator-text','Second explicit UI injection, not a read.');
 await page.click('#apply-intervention');
 await page.waitForFunction(()=>document.getElementById('knowledge-sources').textContent.includes('operator_injection: 3'));
 assert.equal((await page.locator('#procedure').innerText()).includes('undefined'),false);
 assert.ok((await page.locator('#procedure').innerText()).includes('external record; no read event'));
 const final=await page.evaluate(async()=>{
  const packets=await Promise.all(['agent-1','agent-2','agent-3'].map(async a=>(await fetch('/api/viewer?agent='+a)).json()));
  return packets.map(p=>({agent:p.selected.agent_id,counts:p.knowledge.counts,hash:p.snapshot.state_hash,tick:p.snapshot.tick}));
 });
 assert.equal(final[2].counts.operator_injection,0);
 assert.ok(final.every(p=>p.hash===before));assert.deepEqual(errors,[]);
 await page.screenshot({path:output+'-2d.png',fullPage:true});
 await fs.writeFile(output+'.json',JSON.stringify({passed:true,native_hash_unchanged:true,packets:final,page_errors:errors,render:'headless Edge/software'},null,2)+'\n');
 console.log(JSON.stringify({passed:true,page_errors:errors}));
}finally{await browser.close();}
