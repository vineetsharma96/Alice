import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const [url,output]=process.argv.slice(2),errors=[];
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.AliceWeather?.state()?.climate?.forced);
 assert.match(await page.locator('#status').innerText(),/Read-only/);
 assert.match(await page.locator('#intervention').innerText(),/FORCED WEATHER/);
 assert.equal(await page.locator('#agent option').count(),4);
 const before=await page.evaluate(()=>window.AliceWeather.state());
 await page.selectOption('#agent','agent-2');await page.waitForFunction(()=>window.AliceWeather.state().selected.agent_id==='agent-2');
 assert.match(await page.locator('#senses').innerText(),/own_native_senses/);
 assert.match(await page.locator('#shelters').innerText(),/coverage_radius_m/);
 await page.getByRole('button',{name:'Refresh',exact:true}).click();
 await page.waitForTimeout(2000);
 const after=await page.evaluate(()=>window.AliceWeather.state());
 assert.equal(before.state_hash,after.state_hash);assert.equal(before.snapshot.tick,after.snapshot.tick);
 const metrics=await page.evaluate(()=>window.AliceWeather.metrics());
 assert.equal(metrics.unavailable,undefined);assert.equal(metrics.context_lost,false);
 assert.ok(metrics.draw_calls>0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:output+'-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:output+'-mobile.png',fullPage:true});
 assert.equal((await page.request.post(new URL('/api/weather',url).href,{data:{}})).status(),405);
 assert.deepEqual(errors,[]);
 await fs.writeFile(output+'.json',JSON.stringify({passed:true,browser:'headless Edge',desktop:[1440,900],mobile:[390,844],
  page_errors:errors,actual_3d:metrics,paused_hash_unchanged:true,selected_agent:true,forcing_label:true,read_only:true},null,2));
}finally{await browser.close();}
