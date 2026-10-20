// Exercise Chromium's real auto-sized toolbar surface, not a tab with a fixed viewport.
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const playwright=require(process.env.VIDEO_TOOLS_PLAYWRIGHT || 'playwright');
const output=process.env.VIDEO_TOOLS_QA_DIR;
if(!output)throw new Error('Set VIDEO_TOOLS_QA_DIR to a dedicated trash folder.');
fs.mkdirSync(output,{recursive:true});
const root=path.resolve(__dirname,'..');
(async()=>{
  const context=await playwright.chromium.launchPersistentContext(path.join(output,'toolbar-profile'),{
    executablePath:'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
    headless:false,viewport:null,
    args:[`--disable-extensions-except=${root}`,`--load-extension=${root}`,
      '--no-first-run','--disable-background-networking','--window-size=1100,900']
  });
  try {
    const worker=context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    const browser=await context.browser().newBrowserCDPSession();
    await worker.evaluate(()=>chrome.action.openPopup());
    const targets=await browser.send('Target.getTargets');
    const target=targets.targetInfos.find(item=>item.url.endsWith('/extension/popup.html'));
    assert.ok(target,'The actual toolbar popup must open.');
    // Playwright does not expose toolbar surfaces as Pages; attach to that exact target.
    const {sessionId}=await browser.send('Target.attachToTarget',{targetId:target.targetId,flatten:false});
    let sequence=0;const pending=new Map();
    browser.on('Target.receivedMessageFromTarget',event=>{
      if(event.sessionId!==sessionId)return;
      const message=JSON.parse(event.message);const waiter=pending.get(message.id);
      if(!waiter)return;pending.delete(message.id);
      clearTimeout(waiter.timeout);
      message.error?waiter.reject(new Error(message.error.message)):waiter.resolve(message.result);
    });
    const send=(method,params={})=>new Promise((resolve,reject)=>{
      const id=++sequence;
      const timeout=setTimeout(()=>{pending.delete(id);reject(new Error(`Timed out: ${method}`));},10000);
      pending.set(id,{resolve,reject,timeout});
      browser.send('Target.sendMessageToTarget',{sessionId,message:JSON.stringify({id,method,params})}).catch(error=>{clearTimeout(timeout);pending.delete(id);reject(error);});
    });
    const evaluate=async expression=>{
      const result=await send('Runtime.evaluate',{expression,returnByValue:true});
      if(result.exceptionDetails)throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    let size;
    const deadline=Date.now()+5000;
    do {
      size=await evaluate('({height:innerHeight,body:document.body.offsetHeight,main:document.querySelector("main").offsetHeight,dpr:devicePixelRatio})');
      if(size.height===600 && size.main>=300)break;
      await new Promise(resolve=>setTimeout(resolve,100));
    }while(Date.now()<deadline);
    const screenshot=await send('Page.captureScreenshot');
    fs.writeFileSync(path.join(output,'toolbar-popup.png'),Buffer.from(screenshot.data,'base64'));
    assert.equal(size.height,600,'The toolbar must grow to 600 CSS pixels without a viewport sizing loop.');
    assert.ok(size.main>=300,'Video controls need usable space above Download.');
    await evaluate('document.querySelector("#settingsToggle").click();document.querySelector("main").scrollTop=99999');
    const controls=await evaluate('(()=>{const main=document.querySelector("main"),button=document.querySelector("#download").getBoundingClientRect();return {scrolled:main.scrollTop>0,top:button.top,bottom:button.bottom,height:innerHeight};})()');
    assert.ok(controls.scrolled,'Settings and recent history must remain scrollable.');
    assert.ok(controls.top>=0 && controls.bottom<=controls.height,'Download must stay fully visible.');
    console.log(JSON.stringify({realToolbar:true,...size,settingsScroll:true,downloadVisible:true,screenshot:path.join(output,'toolbar-popup.png')}));
  }finally{await context.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
