import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const [url, output] = process.argv.slice(2);
const browser = await chromium.launch({channel:'msedge',headless:true});
const page = await browser.newPage({viewport:{width:1440,height:900}});
const errors=[];
page.on('pageerror', e=>errors.push(e.message));
try {
  await page.goto(url);
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Read-only snapshot'));
  assert.equal(await page.locator('#person option').count(),4);
  await page.selectOption('#person','agent-2');
  assert.ok((await page.locator('#meanings').innerText()).includes('exposures'));
  assert.ok((await page.locator('#meanings').innerText()).includes('Memory sources'));
  assert.ok((await page.locator('#caution').innerText()).includes('uncertain'));
  assert.ok((await page.locator('#history').innerText()).includes('h5_response'));
  const data = await page.evaluate(async()=>await(await fetch('/api/learning')).json());
  assert.equal(data.operator_only,true);
  const snapshot=JSON.stringify(data);
  await page.getByRole('button',{name:'Refresh evidence'}).click();
  await page.waitForFunction(()=>!document.getElementById('refresh').disabled);
  assert.equal(await page.locator('#person').inputValue(),'agent-2');
  assert.equal(JSON.stringify(await page.evaluate(async()=>await(await fetch('/api/learning')).json())),snapshot);
  assert.equal((await page.request.post(new URL('/api/learning',url).href,{data:{}})).status(),501);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.screenshot({path:output+'-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.locator('#vocab summary').first().click();
  await page.screenshot({path:output+'-mobile.png',fullPage:true});
  // Hostile strings are displayed as text, never interpreted as markup.
  await page.route('**/api/learning',route=>{
    const injected=JSON.parse(snapshot);
    injected.people['agent-2'].hypotheses[0].channel='<img src=x onerror=alert(1)>';
    route.fulfill({json:injected});
  });
  await page.getByRole('button',{name:'Refresh evidence'}).click();
  await page.waitForFunction(()=>document.getElementById('meanings').textContent.includes('<img'));
  assert.equal(await page.locator('#meanings img').count(),0);
  await page.unroute('**/api/learning');
  await page.route('**/api/learning',route=>route.fulfill({status:409,body:'missing source'}));
  await page.getByRole('button',{name:'Refresh evidence'}).click();
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Evidence unavailable'));
  assert.equal(await page.locator('#history details').count(),0);
  assert.deepEqual(errors,[]);
  const report={passed:true,page_errors:errors,read_only:true,inhabitants:4,simulated_s:data.simulated_s,
    desktop:[1440,900],mobile:[390,844],no_horizontal_overflow:true,selection_refresh:true,
    source_ids_visible:true,actual_signals_visible:true,uncertain_glosses:true,
    hostile_text_safe:true,missing_evidence_clears_panel:true,browser:'headless Edge'};
  await fs.writeFile(output+'.json',JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
} finally { await browser.close(); }
