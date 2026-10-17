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
const actions=new Set(['health','inspect','download','jobs','cancel','pick_folder','pick_cookies','clear_cookies','reveal']);
chrome.runtime.onMessage.addListener((message,sender,respond)=>{
  // Page scripts and content scripts cannot call the helper, even from an allowed site.
  if (sender.id!==chrome.runtime.id || !sender.url?.startsWith(chrome.runtime.getURL('')) || !actions.has(message?.action)) return false;
  native(message.action,message.payload).then(result=>respond({ok:true,result}),error=>respond({ok:false,error:error.message}));
  return true;
});
chrome.runtime.onInstalled.addListener(()=>{
  chrome.contextMenus.removeAll(()=>chrome.contextMenus.create({id:'video-tools',title:'Download with Video Tools',contexts:['video','audio','link','page']}));
});
chrome.contextMenus.onClicked.addListener(async(info)=>{
  const url=info.linkUrl || (isWebUrl(info.srcUrl) ? info.srcUrl : info.pageUrl);
  if (!isWebUrl(url)) return;
  await chrome.storage.session.set({pendingUrl:url});
  await chrome.windows.create({url:chrome.runtime.getURL('popup.html?window=1'),type:'popup',width:480,height:800});
});
