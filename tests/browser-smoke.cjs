// A fresh Brave profile, never the user's browsing profile. Requires Playwright from the runtime bundle.
const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {execFileSync}=require('node:child_process');
const playwright=require(process.env.VIDEO_TOOLS_PLAYWRIGHT || 'playwright');
const root=path.resolve(__dirname,'..');
const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json')));
const id=[...createHash('sha256').update(Buffer.from(manifest.key,'base64')).digest().subarray(0,16)].map(x=>String.fromCharCode(97+(x>>4),97+(x&15))).join('');
const output=process.env.VIDEO_TOOLS_QA_DIR;if(!output)throw new Error('Set VIDEO_TOOLS_QA_DIR to a dedicated trash folder.');fs.mkdirSync(output,{recursive:true});
const qaRoot=path.resolve(output,'..');
const insideQA=file=>{const relative=path.relative(qaRoot,path.resolve(file));return relative!=='' && !relative.startsWith('..') && !path.isAbsolute(relative);};
(async()=>{
 const extension=root;
 const context=await playwright.chromium.launchPersistentContext(path.join(output,'browser-profile'),{
  executablePath:'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',headless:true,
  args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`,'--no-first-run','--disable-background-networking'],viewport:{width:650,height:1000}});
 const errors=[];
 try{
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`chrome-extension://${id}/extension/popup.html`);
  await page.waitForFunction(()=>document.querySelector('#connection').classList.contains('ready'),undefined,{timeout:30000});
  assert.match(await page.locator('#connection').innerText(),/connected/);
  const health=await page.evaluate(()=>chrome.runtime.sendMessage({action:'health',payload:{}}));
  assert.ok(health.ok && insideQA(health.result.output),'Native helper must save inside this QA folder before any download/history test.');
  assert.equal(health.result.cookies,false,'Browser QA must not use a cookies file.');
  await page.locator('#urlInput').fill('https://www.w3schools.com/html/mov_bbb.mp4');
  await page.locator('#inspect').click();
  await page.waitForFunction(()=>!document.querySelector('#loading').hidden,undefined,{timeout:5000});
  await page.waitForFunction(()=>document.querySelector('#loading').hidden,undefined,{timeout:90000});
  assert.equal(await page.locator('#error').isVisible(),false,await page.locator('#error').innerText());
  assert.equal(await page.locator('#rangeStart').isDisabled(),false,'Direct video duration should enable timeline');
  await page.locator('#startTime').fill('0:01.25');await page.locator('#endTime').fill('0:03.75');
  await page.locator('#endTime').blur();assert.equal(await page.locator('#clipLength').innerText(),'0:02.5');
  await page.locator('[data-nudge="start:1"]').click({modifiers:['Alt']});assert.equal(await page.locator('#startTime').inputValue(),'0:01.35');
  await page.locator('[data-nudge="start:-1"]').click({modifiers:['Alt']});
  await page.locator('#zoomIn').click();assert.equal(await page.locator('#zoomOut').isVisible(),true);await page.locator('#zoomOut').click();
  await page.locator('#formatToggle').click();await page.locator('[data-mode="audio"]').click();
  await page.reload();await page.waitForFunction(()=>document.querySelector('#downloadLabel').textContent==='Download audio');
  // A reload retains the selected mode. A pasted source can be reopened with its per-video trim.
  await page.locator('#urlInput').fill('https://www.w3schools.com/html/mov_bbb.mp4');await page.locator('#inspect').click();
  await page.waitForFunction(()=>document.querySelector('#loading').hidden && !document.querySelector('#download').disabled,undefined,{timeout:90000});
  assert.equal(await page.locator('#startTime').inputValue(),'0:01.25');
  await page.locator('#formatToggle').click();await page.locator('[data-mode="video"]').click();
  await page.setViewportSize({width:440,height:1000});
  await page.screenshot({path:path.join(output,'popup.png'),fullPage:true});
  await page.locator('#settingsToggle').click();await page.screenshot({path:path.join(output,'settings.png'),fullPage:true});await page.locator('#settingsToggle').click();
  await page.setViewportSize({width:440,height:600});
  await page.screenshot({path:path.join(output,'popup-600.png')});
  const visible=async()=>{const box=await page.locator('#download').boundingBox();assert.ok(box.y>=0 && box.y+box.height<=600,'Entire Download button must fit the popup.');};
  await visible();
  await page.locator('#settingsToggle').click();await visible();
  await page.locator('main').evaluate(main=>main.scrollTop=main.scrollHeight);await visible();
  await page.locator('#settingsToggle').click();
  await page.locator('main').evaluate(main=>main.scrollTop=0);
  if(process.argv.includes('--visual-only')){console.log('Popup controls reviewed at 440 × 600.');return;}
  await page.locator('#startTime').fill('0:09');await page.locator('#endTime').fill('0:02');assert.equal(await page.locator('#download').isDisabled(),true);
  await page.locator('#reset').click();assert.equal(await page.locator('#download').isDisabled(),false);
  await page.locator('#startTime').fill('0:01.25');await page.locator('#endTime').fill('0:03.75');
  const previousJobs=await page.locator('.job').evaluateAll(items=>items.map(item=>item.dataset.job));
  await page.locator('#download').click();
  await page.waitForFunction(ids=>[...document.querySelectorAll('.job')].some(item=>!ids.includes(item.dataset.job)),previousJobs,{timeout:15000});
  const targetJob=await page.locator('.job').evaluateAll((items,ids)=>items.find(item=>!ids.includes(item.dataset.job)).dataset.job,previousJobs);
  assert.equal(await page.locator('#activeDownloads').isVisible(),true);
  const service=context.serviceWorkers()[0];
  assert.equal(await service.evaluate(()=>chrome.action.getBadgeText({})),'1');
  await page.screenshot({path:path.join(output,'active-600.png')});
  // Close the popup during download; worker must continue.
  await page.close();
  const next=await context.newPage();await next.goto(`chrome-extension://${id}/extension/popup.html?window=1`);
  await next.waitForFunction(id=>{const item=document.querySelector(`[data-job="${id}"]`);return item?.classList.contains('completed') || item?.classList.contains('failed');},targetJob,{timeout:120000});
  assert.ok(await next.locator(`[data-job="${targetJob}"]`).evaluate(item=>item.classList.contains('completed')),await next.locator('#jobs').innerText());
  await next.screenshot({path:path.join(output,'completed.png'),fullPage:true});
  await next.waitForFunction(async()=>await chrome.action.getBadgeText({})==='');
  const reply=await next.evaluate(()=>chrome.runtime.sendMessage({action:'jobs',payload:{}}));
  const saved=reply.result.find(job=>job.id===targetJob).files[0];
  assert.ok(insideQA(saved),'Downloaded test media must stay inside QA.');
  assert.ok(reply.result.every(job=>(job.files || []).every(insideQA)),'Refuse to clear history containing non-QA files.');
  const probe=JSON.parse(execFileSync(path.join(root,'runtime/ffmpeg/bin/ffprobe.exe'),['-v','error','-show_entries','format_tags','-of','json',saved],{encoding:'utf8'}));
  assert.equal(probe.format.tags.page_url,'https://www.w3schools.com/html/mov_bbb.mp4');
  assert.ok(JSON.parse(probe.format.tags.media_urls).includes('https://www.w3schools.com/html/mov_bbb.mp4'));
  await next.locator('#clearHistory').click();
  await next.waitForFunction(()=>document.querySelectorAll('.job').length===0);
  assert.ok(fs.existsSync(saved),'Clearing extension history must preserve the downloaded video.');
  await next.reload();await next.waitForFunction(()=>document.querySelector('#connection').classList.contains('ready'));
  assert.equal(await next.locator('.job').count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({id,helper:true,popup:true,settings:true,timeControls:true,persistedMode:true,persistedTrim:true,downloadAfterPopupClose:true,screenshots:output,errors}));
 }catch(error){
  for(const page of context.pages())try{console.error((await page.locator('body').innerText()).slice(0,2500));console.error(await page.evaluate(()=>Promise.race([chrome.runtime.sendMessage({action:'health',payload:{}}),new Promise(resolve=>setTimeout(()=>resolve('Native helper timed out'),3000))])));}catch{}
  console.error('Page errors:',errors);throw error;
 }finally{await context.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
