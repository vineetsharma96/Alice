import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const [url,output]=process.argv.slice(2),errors=[];
const browser=await chromium.launch({channel:'msedge',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.AliceEmotion?.person?.owner==='agent-1'&&window.AliceWeather?.state());
 assert.match(await page.locator('#affect-state').innerText(),/learned/);
 assert.match(await page.locator('#affect-learning').innerText(),/rain\/chilly\/open/);
 assert.match(await page.locator('#affect-appraisal').innerText(),/observation_refs/);
 const before=await page.evaluate(()=>({emotion:window.AliceEmotion.native_hash,weather:window.AliceWeather.state().state_hash}));
 await page.getByRole('button',{name:'Refresh',exact:true}).click();
 await page.waitForTimeout(1800);
 const after=await page.evaluate(()=>({emotion:window.AliceEmotion.native_hash,weather:window.AliceWeather.state().state_hash}));
 assert.deepEqual(before,after);assert.equal(before.emotion,before.weather);
 const metrics=await page.evaluate(()=>window.AliceWeather.metrics());assert.ok(metrics.draw_calls>0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:output+'-desktop.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.waitForFunction(()=>document.documentElement.scrollWidth<=innerWidth);
 await page.screenshot({path:output+'-mobile.png',fullPage:true});
 assert.equal((await page.request.post(new URL('/api/emotion',url).href,{data:{}})).status(),405);
 assert.deepEqual(errors,[]);
 await fs.writeFile(output+'.json',JSON.stringify({passed:true,browser:'headless Edge',desktop:[1440,900],mobile:[390,844],
  errors,metrics,paused:true,same_native_head:true,read_only:true,appraisal_and_learning_panel:true},null,2));
}finally{await browser.close();}
