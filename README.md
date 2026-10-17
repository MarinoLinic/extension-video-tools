# Video Tools

A self-contained Windows browser extension for saving videos, MP3 audio and Markdown transcripts. Select the start and end before downloading.

## Install

1. Extract the **Windows portable bundle** to any writable folder, or download this repository.
2. Run **Setup.cmd** once on that computer. The portable bundle already includes its tools and can be set up offline. A source checkout downloads private copies automatically the first time.
3. Open `brave://extensions`, `chrome://extensions` or `edge://extensions`, and enable **Developer mode**.
4. Choose **Load unpacked** and select the **project folder containing manifest.json**.
5. Pin **Video Tools** from the browser's extensions menu.

Supported systems: **64-bit Windows 10 and 11**, with Brave, Chrome or Edge. You do not need Python, Node, FFmpeg, npm or another application installed separately. Everything used for downloading lives in this folder. Setup does not require administrator rights or modify global PATH or Python installations.

A browser extension needs a registered native companion to run video conversion. That companion ships in this project. Setup registers its current location for your Windows account; **rerun Setup.cmd after moving the folder or copying it to another computer**. Loading only the browser files without setup does not enable downloads.

The small browser-only ZIP is for browser installation when the companion is already installed. For transferring the complete application, use the **Windows portable ZIP** or copy the whole initialized project, including `runtime/`.

## Download

Open a video and click Video Tools. Choose the desired video if a page has several, paste a link, or right-click a video/link and choose **Download with Video Tools**.

The arrow beside Download chooses **Video**, **Audio** or **Transcript**. Your choice is remembered. Settings also remember the quality ceiling, caption languages and precise-cut preference. Downloads default to `Videos/Video Tools`; choose a different destination in Settings.

- Drag both timeline handles, or type seconds, `2:50`, or `1:02:50.250` for exact boundaries.
- The +/- buttons move by 1 second. Hold **Alt** for 0.1 seconds or **Shift** for 10 seconds.
- **Full video** resets the selection. A blank end means the end of the video.
- **Zoom in** narrows the timeline scale. **Show all** restores it.
- **Use player time** copies the selected player's position. Preview seeks and plays from the start; it does not automatically stop at the selected end.
- Each video keeps its own selection during the browser session.

The larger window is available from the arrow in the header. Downloads continue after the popup or browser closes. Recent jobs show progress, cancel, retry and Show in folder. Up to two jobs run at once.

## Formats and limits

Video is saved as MP4 and audio as MP3. Precise video cuts re-encode by default; disabling them allows faster cuts near keyframes. Frame rate and audio packet boundaries can make the saved duration slightly different from the entered decimal value. Quality settings are ceilings, not upscaling.

Transcripts come from available captions, with manual captions preferred. They are Markdown, not generated summaries or speech recognition. Missing captions cause an error. A selected transcript keeps whole overlapping cues and original-video timing.

YouTube, X, Facebook and many other sources are handled by the included yt-dlp package. The page scanner can also find ordinary media URLs and identity-matched Facebook progressive files. Support depends on the video, site behavior and access restrictions. DRM, unavailable/private content, live broadcasts, expired links and some blob streams are unsupported. Refresh a page before retrying an expired direct link. Open cross-origin embedded players on their own page if they cannot be detected.

Video links do not expand into playlists, and URL timestamp hints do not silently replace your chosen boundaries. Existing files are preserved. Downloads are staged under `.video-tools-work` in the destination, validated with FFprobe and published with unique names. Partial files remain after failure or cancellation; no automatic deletion is performed.

## Privacy and local setup

There is no hosted backend or analytics. Page access is temporary and requested when you invoke the extension. Browsing history and browser cookies are not collected automatically. Provider requests still go to the original video sites.

Settings can connect an exported Netscape cookies file explicitly. yt-dlp may refresh that selected file. The extension does not copy it into the project or GitHub. Disconnect it when finished. Folder/cookie dialogs may close the toolbar popup when they take focus; reopen it after making the selection.

`runtime/` contains private tools. Ignored `.local/` contains configuration, jobs, build outputs and download caches. Neither is committed to Git. If you put this folder in a synced location, its contents follow that sync service's settings; Git ignore does not disable cloud sync.

The companion uses native messaging, restricted to extension ID `mhjikjpcejlbldbjckejfdjbomcodkon`. No HTTP listener is opened. It exits after about 15 idle seconds; active workers continue independently. Setup writes this application's `com.marin.video_tools` entry under the current user's Chrome, Edge and Brave `NativeMessagingHosts` registry locations. Moving to another computer requires registration there as well.

## Maintenance

**Update Tools.cmd** updates this folder's download packages. Runtime archives are pinned with SHA-256 checksums in `tools/runtime-manifest.json`; Python package versions are pinned in `host/requirements.lock.txt`. Runtime licenses are included in the portable bundle; see [THIRD_PARTY.md](THIRD_PARTY.md).

**Build Portable.cmd** produces a complete Windows ZIP under `.local/packages`, including the private runtimes and compiled companion. It excludes personal configuration, cookie files, job history, exports, Git data and download caches. `npm run package` creates only the browser ZIP, with manifest.json at its ZIP root.

Development checks can use the included tools directly:

```powershell
runtime\node\node.exe --test tests/*.test.mjs
runtime\node\node.exe scripts/check.mjs
runtime\python\python.exe -X utf8 -m unittest discover -s tests -p test_host.py -v
```

Browser tests use an isolated Brave profile, Playwright and a dedicated QA destination. Network media tests are opt-in. [AGENTS.md](AGENTS.md) records maintenance boundaries; [VERIFICATION.md](VERIFICATION.md) records the checks and known limits.
