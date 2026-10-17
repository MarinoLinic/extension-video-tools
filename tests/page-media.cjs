const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const path=require('node:path');
const playwright=require(process.env.VIDEO_TOOLS_PLAYWRIGHT || 'playwright');
(async()=>{
 const {scanMedia,controlMedia}=await import(pathToFileURL(path.resolve(__dirname,'../extension/page-media.js')).href);
 const browser=await playwright.chromium.launch({headless:true,executablePath:'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'});
 try{
  const page=await browser.newPage();
  await page.route('https://x.com/test/status/123',route=>route.fulfill({body:'<title>X</title><article><a href="/test/status/123"><time>now</time></a><div data-testid="tweetText">Two test clips</div><video></video><video></video></article>',contentType:'text/html'}));
  await page.goto('https://x.com/test/status/123');
  let items=await page.evaluate(scanMedia);assert.equal(items.length,2);assert.equal(items[0].url,'https://x.com/test/status/123/video/1');assert.equal(items[1].url,'https://x.com/test/status/123/video/2');assert.equal(items[0].title,'Two test clips');
  await page.route('https://www.facebook.com/test/videos/123/',route=>route.fulfill({body:'<title>Facebook test</title><div role="article"><a href="/test/videos/123/">Video</a><video></video></div><script type="application/json">{"video":{"id":"123","__typename":"Video","browser_native_hd_url":"https://video.test.fbcdn.net/video.mp4"},"recommendation":{"id":"456","__typename":"Video","browser_native_hd_url":"https://video.test.fbcdn.net/wrong.mp4"}}</script>',contentType:'text/html'}));
  await page.goto('https://www.facebook.com/test/videos/123/');items=await page.evaluate(scanMedia);assert.equal(items[0].url,'https://www.facebook.com/test/videos/123/');assert.equal(items[0].index,0);assert.ok(items.some(x=>x.url==='https://video.test.fbcdn.net/video.mp4'));assert.ok(!items.some(x=>x.url.includes('wrong.mp4')));
  await page.route('https://www.youtube.com/watch?v=test123',route=>route.fulfill({body:'<title>YouTube</title><h1>A YouTube video</h1><video></video>',contentType:'text/html'}));
  await page.goto('https://www.youtube.com/watch?v=test123');
  await page.evaluate(()=>{Object.defineProperty(document.querySelector('video'),'duration',{value:7200});document.querySelector('video').currentTime=170.25;});
  items=await page.evaluate(scanMedia);assert.equal(items.length,1);assert.equal(items[0].duration,7200);assert.equal(items[0].currentTime,170.25);
  const state=await page.evaluate(controlMedia,0);assert.equal(state.found,true);
  await page.route('https://example.com/test',route=>route.fulfill({body:'<title>Generic page</title><video src="https://example.com/test.mp4"></video>',contentType:'text/html'}));
  await page.goto('https://example.com/test');items=await page.evaluate(scanMedia);assert.equal(items[0].url,'https://example.com/test.mp4');assert.equal(items[0].kind,'media');
  console.log('YouTube, X multiple attachments, Facebook permalink and generic media detection passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
