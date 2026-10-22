import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const [url,output]=process.argv.slice(2),errors=[];
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.AliceMood?.person&&window.AliceWeather?.state());
 const before=await page.evaluate(()=>window.AliceMood);
 assert.equal(before.read_only,true);assert.ok(before.person.stress>0);assert.ok(before.person.body.thermal<.12);
 assert.match(await page.locator('#mood-traits').innerText(),/Declared sensitivity/);
 assert.equal(await page.locator('#mood-curve polyline').count(),1);
 assert.equal(await page.locator('#mood-evidence').isVisible(),false);
 await page.getByRole('button',{name:'Refresh',exact:true}).click();await page.waitForTimeout(1800);
 const after=await page.evaluate(()=>window.AliceMood);assert.equal(before.native_hash,after.native_hash);
 assert.equal(after.native_hash,await page.evaluate(()=>window.AliceWeather.state().state_hash));
 const metrics=await page.evaluate(()=>window.AliceWeather.metrics());assert.ok(metrics.draw_calls>0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:output+'-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
 await page.screenshot({path:output+'-mobile.png',fullPage:true});
 assert.equal((await page.request.post(new URL('/api/mood',url).href,{data:{}})).status(),405);assert.deepEqual(errors,[]);
 await fs.writeFile(output+'.json',JSON.stringify({passed:true,browser:'headless Edge',desktop:[1440,900],mobile:[390,844],errors,
  metrics,paused:true,same_native_head:true,read_only:true,slow_mood_visible_after_thermal_recovery:true,stress:after.person.stress},null,2));
}finally{await browser.close();}
