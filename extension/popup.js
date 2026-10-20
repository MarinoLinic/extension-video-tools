import {DEFAULTS,parseTime,formatTime,validRange,isWebUrl,canonicalVideoUrl,clipRequest} from './core.js';
import {scanMedia,controlMedia} from './page-media.js';
const $=id=>document.getElementById(id);
let settings={...DEFAULTS}; let source=null; let sources=[]; let range={start:0,end:null};
let scale={start:0,end:100}; let helper=null; let revision=0; let starting=false;
let jobCache=''; let polling=false;
async function rpc(action,payload={}) {
  const response=await chrome.runtime.sendMessage({action,payload});
  if (!response?.ok) throw new Error(response?.error || 'Could not reach the local helper.');
  return response.result;
}
function error(message='') { $('error').textContent=message; $('error').hidden=!message; }
function safe(action) { return (...args)=>Promise.resolve().then(()=>action(...args)).catch(e=>error(e.message)); }
function canDownload() { return helper && source && validRange(range.start,range.end,source.duration) && !starting; }
function updateDownload() { $('download').disabled=!canDownload(); }
function renderMode() {
  $('downloadLabel').textContent=`Download ${settings.mode}`;
  for (const item of document.querySelectorAll('[data-mode]')) item.setAttribute('aria-checked',String(item.dataset.mode===settings.mode));
  $('downloadHint').textContent=settings.mode==='transcript' ? 'Existing captions only. Selected ranges keep whole overlapping cues.' : 'Saved on your PC. You can close this popup after starting.';
}
async function saveSettings() {
  settings.height=Number($('height').value); settings.languages=$('languages').value.trim(); settings.accurate=$('accurate').checked;
  await chrome.storage.local.set({settings}); renderMode();
}
function rememberDraft() {
  if (!source) return;
  // Send the storage write immediately: a toolbar popup may disappear on the next click.
  chrome.storage.session.set({[`draft:${source.url}`]:{...range}}).catch(()=>{});
}
function renderRange(updateInputs=true) {
  const duration=Number.isFinite(source?.duration)?source.duration:null;
  const end=range.end??duration;
  if (updateInputs) { $('startTime').value=formatTime(range.start); $('endTime').value=range.end===null?'':formatTime(range.end); }
  $('rangeStart').disabled=!duration; $('rangeEnd').disabled=!duration;
  for (const name of ['rangeStart','rangeEnd']) { $(name).min=scale.start; $(name).max=scale.end; }
  $('rangeStart').value=Math.min(scale.end,Math.max(scale.start,range.start));
  $('rangeEnd').value=Math.min(scale.end,Math.max(scale.start,end??scale.end));
  $('rangeStart').setAttribute('aria-valuetext',formatTime(range.start));
  $('rangeEnd').setAttribute('aria-valuetext',formatTime(end));
  const span=scale.end-scale.start;
  const left=Math.max(0,Math.min(100,(range.start-scale.start)/span*100));
  const right=Math.max(0,Math.min(100,((end??scale.end)-scale.start)/span*100));
  $('selectedTrack').style.left=`${left}%`; $('selectedTrack').style.width=`${Math.max(0,right-left)}%`;
  $('scaleStart').textContent=formatTime(scale.start,false); $('scaleEnd').textContent=duration?formatTime(scale.end,false):'Unknown length';
  const full=range.start===0 && (range.end===null || (duration!==null && Math.abs(range.end-duration)<.001));
  $('clipLength').textContent=full?'Full video':end!==null?formatTime(end-range.start):`From ${formatTime(range.start)}`;
  $('clipLabel').textContent=full?'Everything, or just the good part.':'Selected duration';
  $('zoomIn').disabled=!duration; $('zoomOut').hidden=scale.start===0 && scale.end===(duration??100);
  $('preview').disabled=!source?.tabId || source.index<0;
  for (const button of document.querySelectorAll('[data-current]')) button.disabled=!source?.tabId || source.index<0;
  const valid=validRange(range.start,range.end,duration);
  $('startTime').setAttribute('aria-invalid',String(!valid)); $('endTime').setAttribute('aria-invalid',String(!valid));
  updateDownload();
}
function resetScale() { scale={start:0,end:source?.duration || 100}; }
function changed() { error(); renderRange(); rememberDraft(); }
function readFields() {
  range={start:parseTime($('startTime').value),end:$('endTime').value.trim()?parseTime($('endTime').value):null};
  renderRange(false); rememberDraft();
}
function renderSource() {
  $('sourceTitle').textContent=source?.title || 'Choose a video to save';
  $('sourceSite').textContent=source?.site || (source ? new URL(source.url).hostname.replace(/^www\./,'') : 'FROM YOUR BROWSER');
  $('sourceMeta').textContent=source ? [source.uploader,Number.isFinite(source.duration)?`${formatTime(source.duration,false)} total`:'Length not available yet'].filter(Boolean).join(' · ') : 'Open a video, or paste a link below.';
  $('urlInput').value=source?.url || '';
  renderRange();
}
async function setSource(item,{inspect=true}={}) {
  const marker=++revision;
  source={...item,url:canonicalVideoUrl(item.url)};
  const key=`draft:${source.url}`;
  const saved=await chrome.storage.session.get(key);
  if (marker!==revision) return;
  range=saved[key] || {start:0,end:source.duration || null};
  resetScale(); error(); renderSource();
  await chrome.storage.session.set({windowSource:source});
  if (helper && inspect) await inspectSource(marker);
}
async function inspectSource(marker=revision) {
  if (!source || !helper) return;
  const url=source.url;
  $('loading').hidden=false;
  // A single metadata request per selected source. Late results cannot replace a newer video.
  try {
    const metadata=await rpc('inspect',{url});
    if (marker!==revision || url!==source?.url) return;
    const oldDuration=source.duration;
    const wasFull=range.start===0 && (range.end===null || range.end===oldDuration);
    source={...source,...metadata};
    if (wasFull) range.end=source.duration || null;
    else if (Number.isFinite(source.duration) && range.end>source.duration) range.end=source.duration;
    resetScale(); renderSource(); rememberDraft();
    await chrome.storage.session.set({windowSource:source});
  } catch(e) {
    if (marker===revision) error(`${e.message}\nYou can still try a download, choose another detected video, or paste its direct link.`);
  } finally { if (marker===revision) $('loading').hidden=true; }
}
async function scan() {
  error(); const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  if (!tab?.id || !isWebUrl(tab.url)) {
    const {windowSource}=await chrome.storage.session.get('windowSource');
    if (new URLSearchParams(location.search).has('window') && windowSource) { await setSource(windowSource); return; }
    if (!source) {source=null;renderSource();} return;
  }
  let frames=[];
  try { frames=await chrome.scripting.executeScript({target:{tabId:tab.id,allFrames:true},func:scanMedia}); }
  catch { frames=[]; }
  sources=frames.flatMap(frame=>(frame.result || []).map(item=>({...item,
    pageUrl:frame.frameId!==0?tab.url:item.pageUrl || item.url,tabId:tab.id,frameId:frame.frameId})));
  // Favor the playing video and named media over a generic page fallback from an iframe.
  sources.sort((a,b)=>Number(b.playing)-Number(a.playing) || Number(b.index>=0)-Number(a.index>=0));
  const unique=new Map(); for (const item of sources) if (!unique.has(item.url)) unique.set(item.url,item);
  sources=[...unique.values()];
  if (!sources.length) sources=[{url:tab.url,title:tab.title || 'Video',duration:null,index:-1,tabId:tab.id,frameId:0}];
  const select=$('sourceSelect'); select.replaceChildren(); select.hidden=sources.length<2;
  for (const [i,item] of sources.entries()) { const option=document.createElement('option');option.value=i;option.textContent=`${i+1}. ${item.title || item.url}`;select.append(option); }
  await setSource(sources[0]);
}
async function player(time,play=false) {
  if (!source?.tabId || source.index<0) throw new Error('The player is not accessible. Use the time fields instead.');
  const result=await chrome.scripting.executeScript({target:{tabId:source.tabId,frameIds:[source.frameId??0]},func:controlMedia,args:[source.index,time,play]});
  if (!result[0]?.result?.found) throw new Error('The player has changed. Refresh the page selection.');
  return result[0].result;
}
function renderHelper(value) {
  helper=value; $('helperBanner').hidden=!!helper;
  $('connection').textContent=helper?`Local helper connected · ${helper.free_gb} GB free`:'Local helper not connected';
  $('connection').classList.toggle('ready',!!helper);
  $('outputPath').textContent=helper?.output || 'Run Setup.cmd to connect.';
  $('cookiesState').textContent=helper?.cookies?'Cookies file connected.':'No cookies file selected.';
  $('clearCookies').hidden=!helper?.cookies;
  for (const id of ['chooseFolder','chooseCookies','clearCookies']) $(id).disabled=!helper;
  updateDownload();
}
async function connect() {
  try { renderHelper(await rpc('health')); if (!helper.ffmpeg) error('FFmpeg and FFprobe are required for media downloads. See Help.'); }
  catch {renderHelper(null);}
}
function element(tag,className,text) { const node=document.createElement(tag); if(className)node.className=className;if(text!==undefined)node.textContent=text;return node; }
function renderJobs(items) {
  const serialized=JSON.stringify(items); if (serialized===jobCache) return;jobCache=serialized;
  const root=$('jobs');root.replaceChildren();
  $('jobCount').textContent=items.length?String(items.length):'';
  const activeItems=items.filter(job=>['queued','running','cancelling'].includes(job.state));
  $('clearHistory').disabled=!items.some(job=>!activeItems.includes(job));
  const summary=$('activeDownloads'); summary.hidden=!activeItems.length; summary.replaceChildren();
  for(const job of activeItems) {
    const percent=Number.isFinite(job.percent)?` · ${Math.round(job.percent)}%`:'';
    summary.append(element('p','',`${job.title || 'Video'} · ${job.message || job.state}${percent}`));
    const progress=element('progress');progress.max=100;
    if(Number.isFinite(job.percent))progress.value=job.percent;
    progress.setAttribute('aria-label',`Download progress for ${job.title || 'Video'}`);summary.append(progress);
  }
  if (!items.length) {root.append(element('p','empty','Your downloads will appear here.'));return;}
  for (const job of [...activeItems,...items.filter(job=>!activeItems.includes(job))].slice(0,8)) {
    const card=element('div',`job ${job.state}`);card.dataset.job=job.id;const title=element('div','job-title');
    title.append(element('strong','',job.title || 'Video'),element('span','',job.state));card.append(title);
    const active=['queued','running','cancelling'].includes(job.state);
    const detail=element('p','',job.message || ''); card.append(detail);
    if(active) {const progress=element('progress');progress.max=100;if(Number.isFinite(job.percent))progress.value=job.percent;progress.setAttribute('aria-label',`Download progress for ${job.title}`);card.append(progress);}
    const actions=element('div','job-actions');
    const addAction=(label,run)=>{
      const button=element('button','',label);button.addEventListener('click',safe(async()=>{
        button.disabled=true;
        try { await run(); await refreshJobs(true); }
        finally { button.disabled=false; }
      }));actions.append(button);
    };
    if(active) addAction('Cancel',()=>rpc('cancel',{id:job.id}));
    else if(job.state==='completed') {
      addAction('Open file',()=>rpc('open_file',{id:job.id}));
      addAction('Show in folder',()=>rpc('reveal',{id:job.id}));
    } else addAction('Retry',async()=>{
        // Retry uses a fresh deliberate click with this video's current options; don't silently retry a different URL.
        const saved=await chrome.storage.local.get(`request:${job.id}`);
        if (!saved[`request:${job.id}`]) throw new Error('Open the source video and start another download.');
        const request=saved[`request:${job.id}`];const next=await rpc('download',request);
        await chrome.storage.local.set({[`request:${next.id}`]:request});
      });
    card.append(actions);
    if (job.log?.length) {const details=element('details');details.append(element('summary','','Details'),element('pre','',job.log.join('\n')));card.append(details);}
    root.append(card);
  }
}
async function refreshJobs(force=false) {
  if (!helper || (polling && !force)) return;
  polling=true;try {renderJobs(await rpc('jobs'));}catch(e){if(force)throw e;}finally{polling=false;}
}
$('settingsToggle').addEventListener('click',()=>{const visible=$('settingsPanel').hidden;$('settingsPanel').hidden=!visible;$('settingsToggle').setAttribute('aria-expanded',String(visible));});
$('formatToggle').addEventListener('click',()=>{const visible=$('formatMenu').hidden;$('formatMenu').hidden=!visible;$('formatToggle').setAttribute('aria-expanded',String(visible));if(visible)$('formatMenu').querySelector('[aria-checked=true]').focus();});
function closeMenu() {$('formatMenu').hidden=true;$('formatToggle').setAttribute('aria-expanded','false');}
document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeMenu();$('formatToggle').focus();}if(! $('formatMenu').hidden && ['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();const choices=[...$('formatMenu').querySelectorAll('button')];const index=choices.indexOf(document.activeElement);choices[(index+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length].focus();}});
document.addEventListener('click',event=>{if(!event.target.closest('.download-area'))closeMenu();});
for(const item of document.querySelectorAll('[data-mode]')) item.addEventListener('click',safe(async()=>{settings.mode=item.dataset.mode;await saveSettings();closeMenu();$('formatToggle').focus();}));
for(const id of ['height','languages','accurate']) $(id).addEventListener('change',safe(saveSettings));
$('reconnect').addEventListener('click',safe(async()=>{await connect();if(helper){await inspectSource();await refreshJobs(true);}}));
$('chooseFolder').addEventListener('click',safe(async()=>renderHelper(await rpc('pick_folder'))));
$('chooseCookies').addEventListener('click',safe(async()=>renderHelper(await rpc('pick_cookies'))));
$('clearCookies').addEventListener('click',safe(async()=>renderHelper(await rpc('clear_cookies'))));
$('clearHistory').addEventListener('click',safe(async()=>{
  $('clearHistory').disabled=true;
  try {await rpc('clear_history');await refreshJobs(true);}
  finally {if(jobCache){const items=JSON.parse(jobCache);jobCache='';renderJobs(items);}}
}));
$('rescan').addEventListener('click',safe(scan));
$('sourceSelect').addEventListener('change',safe(()=>setSource(sources[Number($('sourceSelect').value)])));
$('urlForm').addEventListener('submit',event=>{event.preventDefault();safe(async()=>{const url=$('urlInput').value.trim();if(!isWebUrl(url))throw new Error('Paste a complete HTTP or HTTPS video link.');await setSource({url,title:new URL(url).hostname,duration:null,index:-1});})();});
for(const id of ['startTime','endTime']) {$(id).addEventListener('input',readFields);$(id).addEventListener('blur',()=>{if(validRange(range.start,range.end,source?.duration))renderRange();});}
for(const [id,key] of [['rangeStart','start'],['rangeEnd','end']]) $(id).addEventListener('input',()=>{
  const value=Number($(id).value);
  if(key==='start')range.start=Math.max(0,Math.min(value,(range.end??source.duration)-.1));
  else range.end=Math.min(source.duration,Math.max(value,range.start+.1));changed();
});
for(const button of document.querySelectorAll('[data-nudge]')) button.addEventListener('click',event=>{
  const [key,sign]=button.dataset.nudge.split(':');
  const step=(event.altKey?.1:event.shiftKey?10:1)*Number(sign);
  const value=(range[key]??source?.duration??0)+step;
  if(!Number.isFinite(value))return;
  range[key]=Math.round(Math.max(0,Math.min(source?.duration??604800,value))*1000)/1000;changed();
});
for(const button of document.querySelectorAll('[data-current]'))button.addEventListener('click',safe(async()=>{const result=await player(null);range[button.dataset.current]=Math.round(result.currentTime*1000)/1000;changed();}));
$('reset').addEventListener('click',()=>{range={start:0,end:source?.duration||null};resetScale();changed();});
$('zoomIn').addEventListener('click',()=>{
  const end=range.end??source.duration;const selection=end-range.start;
  const width=Math.max(10,Math.min((scale.end-scale.start)/2,selection*1.2));
  const center=(range.start+end)/2;
  const low=Math.max(0,Math.min(source.duration-width,center-width/2));
  scale={start:low,end:Math.min(source.duration,low+width)};renderRange();
});
$('zoomOut').addEventListener('click',()=>{resetScale();renderRange();});
$('preview').addEventListener('click',safe(()=>player(range.start,true)));
$('expand').addEventListener('click',safe(async()=>{
  if(source)await chrome.storage.session.set({windowSource:source});
  await chrome.windows.create({url:chrome.runtime.getURL('extension/popup.html?window=1'),type:'popup',width:620,height:880});
}));
$('download').addEventListener('click',safe(async()=>{
  error();readFields();const request=clipRequest(source,range,settings);starting=true;updateDownload();
  try {const job=await rpc('download',request);await chrome.storage.local.set({[`request:${job.id}`]:request});await refreshJobs(true);}
  finally{starting=false;updateDownload();}
}));
async function init() {
  const stored=await chrome.storage.local.get('settings');settings={...DEFAULTS,...stored.settings};
  if(!['video','audio','transcript'].includes(settings.mode))settings.mode='video';
  $('height').value=settings.height;$('languages').value=settings.languages;$('accurate').checked=settings.accurate;renderMode();
  const params=new URLSearchParams(location.search);
  if(params.has('settings')){$('settingsPanel').hidden=false;$('settingsToggle').setAttribute('aria-expanded','true');}
  await connect();
  await refreshJobs();
  const {pendingUrl,pendingPageUrl}=await chrome.storage.session.get(['pendingUrl','pendingPageUrl']);
  if(pendingUrl){await chrome.storage.session.remove(['pendingUrl','pendingPageUrl']);await setSource({url:pendingUrl,pageUrl:pendingPageUrl,title:new URL(pendingUrl).hostname,duration:null,index:-1});}
  else await scan();
  await refreshJobs();setInterval(()=>{if(!document.hidden)refreshJobs();},1800);
}
init().catch(e=>error(e.message));
