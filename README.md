# Video Tools

A private browser extension for saving videos, MP3 audio and Markdown transcripts, with the clip selected **before** the download starts.

Works with Brave, Chrome and Edge on Windows. YouTube uses the existing `projects-python/youtube_tools` engine. X, Facebook and other supported sites use yt-dlp. The extension also detects ordinary media URLs in the current page, and can offer progressive Facebook files exposed in the page’s JSON.

## Get started

1. Double-click **Setup.cmd**. It creates an isolated Python environment and registers the native helper for your Windows account. No administrator access is needed.
2. Open `brave://extensions`, `chrome://extensions` or `edge://extensions` and enable **Developer mode**.
3. Choose **Load unpacked**, then select this repository’s **extension** folder. Do not select the repository root.
4. Pin **Video Tools** from the browser’s extensions menu.

The helper is already set up on the original development machine. Loading the extension in your normal browser is the remaining installation step.

Requirements: Windows, Python 3.10 or later with Tkinter, FFmpeg and FFprobe on PATH, and the sibling YouTube Tools project. Node.js or Deno is recommended for YouTube’s JavaScript challenges. Setup installs dependencies only into this repository’s `.local/runtime`; it does not modify the existing YouTube Tools environment, global Python, PATH, browser policies or browser profiles.

## Save a video or a clip

Open a video and click the pinned extension. If a feed has several videos, choose the item from the selector. You can also paste a video link, or right-click a video or link and choose **Download with Video Tools**.

Use the arrow beside Download to choose **Video**, **Audio** or **Transcript**. Your choice is remembered, along with quality, caption languages and the precise-cut setting. Downloads default to `~/Videos/Video Tools`; Settings has a native folder picker.

- Drag the two timeline handles to select a range. **Full video** resets it.
- Type seconds, `2:50`, or `1:02:50.250` into either time field. A blank end means the end of the video.
- The ± buttons change a boundary by one second. Hold **Alt** for 0.1 seconds or **Shift** for 10 seconds. Native slider arrow keys move by 0.1 seconds.
- **Zoom in** changes the timeline scale for finer dragging; **Show all** restores the complete timeline.
- **Use player time** copies the current position of the selected player. **Preview** seeks and plays that page’s player from the selected start. Preview does not automatically stop at the selected end.
- Clip boundaries are kept per video for the current browser session. They do not carry over to unrelated videos.

The ↗ button opens a larger window. A download continues after the popup or browser closes. Recent downloads show progress, cancellation, errors, retry and **Show in folder**. At most two jobs run at once.

## Output and limits

Video output is MP4; audio output is MP3. Video quality is a ceiling, not an upscaler. A source with no audio remains silent. Precise video cuts are enabled by default and re-encode the selected section. Frame rate and audio packet boundaries can make the resulting duration differ slightly from the entered interval. Turning precise cuts off allows faster cuts near keyframes.

Transcripts use existing captions in the requested languages, with manual captions preferred. There is no speech recognition. Missing captions are an error, never an empty successful transcript. A selected transcript retains whole overlapping cues and the original-video timing.

YouTube video links are treated as one video even if the URL includes a playlist. URL timestamp hints do not silently change your explicit clip selection. Live and upcoming broadcasts are unsupported.

Support depends on the particular source and the current site. DRM, inaccessible/private videos, expired links, some blob streams and provider restrictions can prevent downloads. A Facebook feed item may work through its permalink, an exposed progressive file, or a manually pasted direct link. Signed media URLs can expire; refresh the page before retrying. Cross-origin iframe players may be inaccessible under the extension’s limited permissions; open the embedded video’s own page or paste its link.

Existing output files are preserved. Each job receives a unique filename suffix. Files are staged in the destination’s `.video-tools-work/<job-id>` and published after validation; media must pass FFprobe checks. Failed or cancelled partial files stay there for inspection. The extension does not clean or delete your files.

## Privacy and installation effects

There is no analytics service, hosted backend or automatic browser-cookie reading. The extension requests temporary access to the active tab when invoked, and reads the selected page’s media information. It has no persistent access to every site and does not scan browsing history.

The browser communicates with the helper through native messaging, restricted to the extension’s stable ID. No HTTP listener is opened. The idle helper exits about 15 seconds after the popup stops making requests; active download workers finish independently. Requests still go to the original media providers.

Settings can explicitly connect an exported Netscape cookies file for authenticated downloads. **yt-dlp may refresh the selected file.** Cookies are not copied into the repository, sent to GitHub or read from browser profiles. Disconnect the file when finished. Native file dialogs can close a toolbar popup when they take focus; reopen the popup after choosing a folder or cookies file.

Runtime files, selected-folder configuration and local job history live under ignored `.local`. Output defaults to Videos, outside the repository. This repository itself is in OneDrive on the original machine: `.gitignore` excludes files from Git, but does **not** exclude them from OneDrive. Do not place cookie files in a synced project folder if you want them to stay off that sync service.

Setup writes only this application’s native-host entries under:

```text
HKCU\Software\Google\Chrome\NativeMessagingHosts\com.marin.video_tools
HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.marin.video_tools
HKCU\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.marin.video_tools
```

The extension ID is `mhjikjpcejlbldbjckejfdjbomcodkon`. The manifest contains only a public key so moving the unpacked folder does not change that ID. There is no stored private signing key. If you move the project, rerun setup to update the helper path. Removing or disabling the extension stops browser access; the per-user native-host registrations are inert without a caller.

## Maintenance and verification

**Update Tools.cmd** updates only this extension’s download dependencies. Default setup uses `host/requirements.lock.txt`, the verified baseline; the update launcher uses the allowed ranges in `host/requirements.txt`. Actual installed versions are recorded in `.local/installed-versions.txt`. Close Video Tools windows and wait for the idle helper to exit before rebuilding its executable.

```powershell
npm test
npm run check
.local\runtime\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_host.py -v
```

Browser tests use Playwright and a fresh isolated Brave profile. Set `VIDEO_TOOLS_PLAYWRIGHT` to a Playwright package path and `VIDEO_TOOLS_QA_DIR` to a dedicated folder under the machine’s designated trash/work location. Then run `node tests/page-media.cjs` and `node tests/browser-smoke.cjs`. The latter starts a real download: first configure the helper’s output to the QA folder and restore it afterwards. Network checks in `tests/live-media.py`, `tests/generic-media.py` and `tests/site-probes.py` are opt-in; they never use real browser cookies automatically.

`npm run package` creates a ZIP containing **only** the browser extension under `.local/packages`. Install the helper from this repository separately; do not package runtime/config/job folders. See [VERIFICATION.md](VERIFICATION.md) for the tested cases and [AGENTS.md](AGENTS.md) for maintenance boundaries.

Implementation references: [Chrome native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging), [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp), and [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md). A listed site does not guarantee every video is accessible.
