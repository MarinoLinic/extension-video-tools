// This function is serialized by scripting.executeScript. Keep it self-contained.
export function scanMedia() {
  const elements = [...document.querySelectorAll('video,audio')];
  const result = [];
  const og = document.querySelector('meta[property="og:title"]')?.content;
  const site = location.hostname;
  const youtube = /(^|\.)youtube\.com$/.test(site) || site === 'youtu.be';
  if (youtube && /\/(watch|shorts\/|live\/)/.test(location.pathname)) {
    const video = document.querySelector('video');
    result.push({url: location.href, title: document.querySelector('h1 yt-formatted-string,h1')?.textContent?.trim() || og || document.title,
      duration: Number.isFinite(video?.duration) ? video.duration : null,
      currentTime: video?.currentTime || 0, index: elements.indexOf(video), kind: 'page', playing: video ? !video.paused : false});
    return result;
  }
  for (const [index, video] of elements.entries()) {
    let url = null;
    const article = video.closest('article,[role="article"]');
    if (/(^|\.)(x|twitter)\.com$/.test(site)) {
      url = article?.querySelector('a[href*="/status/"] time')?.closest('a')?.href || article?.querySelector('a[href*="/status/"]')?.href;
      // A single player may be an X card, which has no /video/1 attachment.
      // Preserve explicit attachment links; synthesize indexes only for multiple players.
      if (url && article) {
        const post=new URL(url);post.pathname=post.pathname.replace(/\/(?:video|photo)\/\d+\/?$/,'');post.search='';post.hash='';
        const players=[...article.querySelectorAll('video')];
        const attachment=video.closest('a[href*="/video/"]');
        const explicit=attachment && new URL(attachment.href);
        if(explicit && explicit.origin===post.origin && explicit.pathname.startsWith(post.pathname+'/video/'))url=explicit.href;
        else url=post.href+(players.length>1?`/video/${players.indexOf(video)+1}`:'');
      }
    } else if (/(^|\.)(facebook\.com|fb\.watch)$/.test(site)) {
      url = article?.querySelector('a[href*="/videos/"],a[href*="/reel/"],a[href*="watch?v="],a[href*="story_fbid="]')?.href;
      if (!url && /\/videos\/|\/reel\/|[?&]v=/.test(location.href)) url=location.href;
    }
    const src = video.currentSrc || video.src || video.querySelector('source')?.src;
    if (!url && /^https?:/.test(src || '')) url=src;
    const title = article?.querySelector('[data-testid="tweetText"]')?.textContent?.trim().slice(0,160) || video.getAttribute('aria-label') || og || document.title;
    if (url) result.push({url,title,duration:Number.isFinite(video.duration) ? video.duration : null,
      currentTime:video.currentTime || 0,index,kind:url===src ? 'media':'page',playing:!video.paused});
    if (url && url!==src && /^https?:/.test(src || '')) result.push({url:src,pageUrl:url,title:`${title} · direct media`,
      duration:Number.isFinite(video.duration)?video.duration:null,currentTime:video.currentTime || 0,index,kind:'media',playing:!video.paused});
  }
  // Facebook can expose progressive files in its rendered JSON even when the player uses a blob.
  // Match only video identities already found on this page; never mix in recommendations/comments.
  if (/(^|\.)facebook\.com$/.test(site)) {
    const videoId=url=>{try{const u=new URL(url);return u.searchParams.get('v') || u.pathname.match(/\/(?:videos|reel)\/(\d+)/)?.[1];}catch{return null;}};
    const wanted=new Map(result.map(item=>[videoId(item.url),item]).filter(([id])=>id));
    let budget=100000,bytes=0;const seen=new Set();
    const mediaUrl=value=>{try{const u=new URL(value);return u.protocol==='https:' && /(^|\.)fbcdn\.net$/.test(u.hostname)?u.href:null;}catch{return null;}};
    for (const script of document.querySelectorAll('script[type="application/json"]')) {
      if (!wanted.size || budget<=0 || bytes>12000000) break;
      if(script.textContent.length>4000000)continue;bytes+=script.textContent.length;
      let json;try{json=JSON.parse(script.textContent);}catch{continue;}
      const stack=[{node:json,match:null}];
      while(stack.length && budget-->0){
        const {node,match}=stack.pop();if(!node || typeof node!=='object')continue;
        const id=String(node.id || node.videoId || '');
        const isVideo=/Video/.test(node.__typename || '') || node.browser_native_hd_url || node.browser_native_sd_url || node.videoDeliveryResponseFragment;
        const selected=wanted.get(id) || (isVideo && id && !wanted.has(id)?null:match);
        if(selected){
          for(const [field,label] of [['browser_native_hd_url','direct HD'],['browser_native_sd_url','direct SD'],['playable_url_quality_hd','direct HD'],['playable_url','direct SD'],['progressive_url','direct MP4']]){
            const url=mediaUrl(node[field]);if(url && !seen.has(url)){seen.add(url);result.push({...selected,pageUrl:selected.url,url,title:`${selected.title} · ${label}`,kind:'media'});}
          }
        }
        for(const [key,value] of Object.entries(node))if(value && typeof value==='object' && !['feedback','comments','replies','recommended_videos'].includes(key))stack.push({node:value,match:selected});
      }
    }
  }
  if (!result.length && /^https?:/.test(location.href)) {
    const video=elements.find(item=>!item.paused) || elements[0];
    result.push({url:location.href,title:og || document.title,duration:Number.isFinite(video?.duration)?video.duration:null,
      currentTime:video?.currentTime || 0,index:elements.indexOf(video),kind:'page',playing:video?!video.paused:false});
  }
  return result.slice(0,30).map(item=>({...item,pageUrl:item.pageUrl || (item.kind==='page'?item.url:location.href)}));
}

export function controlMedia(index, time, play = false) {
  const video=[...document.querySelectorAll('video,audio')][index];
  if (!video) return {found:false};
  if (Number.isFinite(time)) video.currentTime=Math.max(0,time);
  if (play) video.play().catch(()=>{});
  return {found:true,currentTime:video.currentTime,duration:Number.isFinite(video.duration)?video.duration:null};
}
