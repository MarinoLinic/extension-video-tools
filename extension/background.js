import {isWebUrl} from './core.js';
const HOST = 'com.marin.video_tools';
let port; let sequence=0; let idleTimer;
const pending=new Map();
function releaseWhenIdle() {
  clearTimeout(idleTimer);
  if(pending.size || !port)return;
  const connection=port;
  idleTimer=setTimeout(()=>{if(port===connection && !pending.size){port=null;connection.disconnect();}},15000);
}
function native(action, payload={}) {
  clearTimeout(idleTimer);
  if (!port) {
    port=chrome.runtime.connectNative(HOST);
    const connection=port;
    port.onMessage.addListener(message=>{
      const waiter=pending.get(message.id); if (!waiter) return;
      pending.delete(message.id); clearTimeout(waiter.timer);
      message.ok ? waiter.resolve(message.result) : waiter.reject(new Error(message.error));
      releaseWhenIdle();
    });
    port.onDisconnect.addListener(()=>{
      if(port!==connection)return;
      const error=chrome.runtime.lastError?.message || 'The helper disconnected.';
      port=null;
      for (const waiter of pending.values()) { clearTimeout(waiter.timer); waiter.reject(new Error(error)); }
      pending.clear();
    });
  }
  return new Promise((resolve,reject)=>{
    const id=++sequence;
    const timer=setTimeout(()=>{pending.delete(id);releaseWhenIdle();reject(new Error('The helper took too long. Try again.'));},180000);
    pending.set(id,{resolve,reject,timer}); port.postMessage({...payload,action,_request:id});
  });
}
const actions=new Set(['health','inspect','download','jobs','cancel','clear_history','pick_folder','pick_cookies','clear_cookies','reveal','open_file']);
const MONITOR='video-tools-progress';
let monitorTimer; let monitoring=false;
async function showProgress(items) {
  const active=items.filter(job=>['queued','running','cancelling'].includes(job.state));
  await chrome.action.setBadgeBackgroundColor({color:'#3e7950'});
  await chrome.action.setBadgeText({text:active.length?String(active.length):''});
  await chrome.action.setTitle({title:active.length?`Video Tools · ${active.length} active\n`+active.map(job=>`${job.title}: ${job.message}${Number.isFinite(job.percent)?` (${Math.round(job.percent)}%)`:''}`).join('\n'):'Video Tools'});
  if(active.length) {
    await chrome.storage.local.set({monitorDownloads:true});
    if(!monitorTimer)monitorTimer=setInterval(()=>pollProgress().catch(()=>{}),2000);
    if(!await chrome.alarms.get(MONITOR))await chrome.alarms.create(MONITOR,{periodInMinutes:.5});
  } else {
    clearInterval(monitorTimer);monitorTimer=null;
    await chrome.alarms.clear(MONITOR);
    await chrome.storage.local.remove('monitorDownloads');
  }
}
async function pollProgress() {
  if(monitoring)return;
  monitoring=true;
  try {await showProgress(await native('jobs'));}
  catch {
    await chrome.action.setBadgeText({text:'!'});
    await chrome.action.setTitle({title:'Video Tools · Could not check downloads. Open to reconnect.'});
  } finally {monitoring=false;}
}
async function handle(action,payload) {
  const result=await native(action,payload);
  if(action==='clear_history')await chrome.storage.local.remove(result.cleared.map(id=>`request:${id}`));
  if(action==='jobs')await showProgress(result);
  else if(['download','cancel','clear_history'].includes(action))await pollProgress();
  return result;
}
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name===MONITOR)pollProgress().catch(()=>{});});
chrome.runtime.onStartup.addListener(()=>pollProgress().catch(()=>{}));
chrome.storage.local.get('monitorDownloads').then(saved=>{if(saved.monitorDownloads)pollProgress().catch(()=>{});});
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
  // Page scripts and content scripts cannot call the helper, even from an allowed site.
  if (sender.id!==chrome.runtime.id || !sender.url?.startsWith(chrome.runtime.getURL('')) || !actions.has(message?.action)) return false;
  handle(message.action,message.payload).then(result=>respond({ok:true,result}),error=>respond({ok:false,error:error.message}));
  return true;
});
chrome.runtime.onInstalled.addListener(()=>{
  chrome.contextMenus.removeAll(()=>chrome.contextMenus.create({id:'video-tools',title:'Download with Video Tools',contexts:['video','audio','link','page']}));
});
chrome.contextMenus.onClicked.addListener(async(info)=>{
  const url=info.linkUrl || (isWebUrl(info.srcUrl) ? info.srcUrl : info.pageUrl);
  if (!isWebUrl(url)) return;
  await chrome.storage.session.set({pendingUrl:url,pendingPageUrl:info.pageUrl || url});
  await chrome.windows.create({url:chrome.runtime.getURL('extension/popup.html?window=1'),type:'popup',width:480,height:800});
});
