import test from 'node:test';
import assert from 'node:assert/strict';

test('toolbar tracks two jobs with the popup closed and clears itself on completion',async()=>{
  const original={chrome:globalThis.chrome,setInterval:globalThis.setInterval,clearInterval:globalThis.clearInterval,setTimeout:globalThis.setTimeout};
  let listener,tick,nativeReply,badge='',title='',jobs=[],startup;
  const saved={monitorDownloads:true}; const alarms=new Map();
  const event=()=>({addListener(){}});
  globalThis.setInterval=fn=>{tick=fn;return 1;};
  globalThis.clearInterval=()=>{tick=null;};
  globalThis.setTimeout=(...args)=>original.setTimeout(...args).unref();
  globalThis.chrome={
    runtime:{id:'test',getURL:path=>`chrome-extension://test/${path}`,
      connectNative:()=>({onMessage:{addListener:fn=>nativeReply=fn},onDisconnect:event(),disconnect(){},
        postMessage:request=>queueMicrotask(()=>nativeReply({id:request._request,ok:true,result:jobs}))}),
      onMessage:{addListener:fn=>listener=fn},onStartup:{addListener:fn=>startup=fn},onInstalled:event()},
    action:{setBadgeBackgroundColor:async()=>{},setBadgeText:async value=>{badge=value.text;},setTitle:async value=>{title=value.title;}},
    storage:{local:{get:async()=>({...saved}),set:async value=>Object.assign(saved,value),remove:async keys=>{for(const key of [keys].flat())delete saved[key];}}},
    alarms:{get:async name=>alarms.get(name),create:async(name,value)=>alarms.set(name,value),clear:async name=>alarms.delete(name),onAlarm:event()},
    contextMenus:{onClicked:event()}
  };
  const settle=async()=>{for(let i=0;i<12;i++)await new Promise(resolve=>setImmediate(resolve));};
  try {
    jobs=[{state:'running',title:'One',message:'Downloading',percent:42},{state:'queued',title:'Two',message:'Starting'}];
    await import(`../extension/background.js?test=${Date.now()}`);await settle();
    assert.equal(badge,'2');assert.match(title,/42%/);assert.ok(tick);assert.equal(alarms.size,1);
    assert.equal(listener({action:'clear_history'},{id:'test',url:'https://example.com'},()=>{}),false,'Web pages cannot invoke helper actions.');
    // No popup calls: only the background timer observes completion.
    jobs=[{state:'completed'},{state:'failed'}];await tick();await settle();
    assert.equal(badge,'');assert.equal(title,'Video Tools');assert.equal(tick,null);assert.equal(alarms.size,0);assert.equal(saved.monitorDownloads,undefined);
    // Browser startup discovers a native worker that continued while the browser was closed.
    jobs=[{state:'running',title:'Still running',message:'Processing'}];startup();await settle();assert.equal(badge,'1');
    jobs=[];await tick();await settle();assert.equal(badge,'');
  } finally {Object.assign(globalThis,original);}
});
