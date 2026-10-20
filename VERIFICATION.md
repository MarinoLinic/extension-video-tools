# Verification — 18 October 2026

## Popup, progress, history and provenance

- X card follow-up: reproduced `Video #1 is unavailable` for post `2105253451446038779/video/1`; the original post resolves to its 21.999-second card video. Scanner now leaves single-player posts unnumbered and preserves explicit indexes. A narrowly guarded fallback repairs older first-attachment requests; it rejects multi-video results and does not mask login errors or change another selected attachment number.
- Against a truly isolated companion with its own embedded interpreter, both metadata inspection and a native-worker retry recovered that exact old indexed request without cookies. A requested 0–2.5-second clip completed as an MP4 of 2.503756 seconds; FFprobe confirmed video and corrected post/source metadata. Page fixtures cover single-player cards, multiple players and explicit mixed-media attachment links. Twelve Python and five JavaScript tests pass.
- QA isolation correction: a junction of the entire runtime can make embedded Python import the development checkout's `host/common.py`. The final companion check uses copied interpreter files and shares only packages/external tools. Browser smoke now requires a QA destination and refuses non-QA saved paths before history clearing.
- Final isolated Brave smoke passed with those guards enabled, including native download continuation, source tags and safe history clearing; its 440 × 600 popup capture was inspected. All three application-specific browser host registrations were restored. Brave can consult Chrome's native-host registration, so a Brave-only registry override is insufficient for isolation.

- Follow-up: the actual toolbar surface exposed a sizing loop from `body { max-height:100vh }`: it settled at 218 CSS pixels, leaving only 20 pixels for the main controls. Removed that viewport-relative cap. A headed Brave toolbar test (`tests/toolbar-popup.cjs`, `viewport:null`, `chrome.action.openPopup`) now verifies 600 pixels overall, 402 pixels for the main panel at the tested scale, scrollable Settings/history, and the complete Download button. Its screenshot was visually inspected. Earlier fixed-viewport screenshots did not cover this auto-sizing behavior.

- Five JavaScript tests and eleven Python host tests pass, along with `npm run check`. Background coverage includes two concurrent jobs, monitoring without a popup, clearing the badge at completion, browser-startup recovery and refusal of web-page helper requests.
- History tests cover completed/failed/cancelled entries, active and queued jobs, unresponsive workers that resume, and preservation of saved files and helper records.
- FFmpeg/FFprobe fixtures confirm that MP4 and MP3 retain author/title tags and embed distinct post, selected-source and video/audio stream URLs. A caption fixture verifies the corresponding Markdown front matter.
- Isolated Brave smoke test passed against a separate QA companion and destination under `C:\Users\marin\agent-files\trash\video-tools-qa-20261018`. The application's Brave native-host registration was restored afterward; real settings, history and saved files were not used for these history-clearing checks.
- The complete Download button fits at 440 × 600, including while Settings is open or the main panel is scrolled. Popup and active-progress screenshots were visually inspected. Chrome's toolbar popup height limit is 600 pixels, so the main panel scrolls and the action stays fixed below it.
- Actual native download completed after the popup closed. The toolbar badge showed `1` while active and cleared at completion. FFprobe confirmed source tags in the downloaded MP4. Clearing history removed the entry after reopening the popup and preserved the media file.
- Page fixtures for YouTube, X attachments, Facebook selected-video matching and generic media passed; generic direct media retained its containing page URL. No new authenticated or live social-provider checks were performed in this update.
- Native companion jobs remain outside the browser's Downloads list. The extension uses its own toolbar badge and popup progress. New `alarms` permission supports progress recovery; no downloads, cookies or persistent site-access permission was added.
- Source links can include expiring signed URLs. Clearing the extension list hides helper records rather than deleting diagnostic folders. Existing media files receive no retroactive metadata changes.

## Recent-download actions

Completed jobs now offer **Open file** (launches the saved file with its Windows-associated application) alongside **Show in folder**. This UI/helper change has not yet been exercised in browser QA.

Windows, Brave, embedded CPython 3.12.10, private Node 26.7.0, FFmpeg/FFprobe 9.0.2 and yt-dlp 2026.08.19. No browser-profile cookies were read or used. QA used an isolated browser profile and files under `C:\Users\marin\agent-files\trash\extension-video-tools-qa-20261017`.

## Standalone and relocation checks (1.1.0)

- The browser manifest is at the project root; every declared UI/script/icon path resolves from that root. Actual Brave loading was tested from the root.
- Downloading and caption parsing use only code in `host/` and packages in the private embedded interpreter. No external source checkout or global tool installation is used.
- Vendor archives passed their pinned SHA-256 checks. The portable ZIP includes CPython, Node, FFmpeg/FFprobe, packages, licenses and the compiled native launcher; its manifest is at the ZIP root.
- Extracted the bundle to a different directory containing a space, outside the repository. Removed Python, Node and FFmpeg from the test process's PATH, leaving Windows system paths only.
- `tools/setup.ps1 -Offline` succeeded in that relocated copy without downloads, pip installation or a Python installation on PATH. The interpreter and all three external tools resolved inside the relocated folder.
- All seven Python host tests and the manifest/assets check passed from that copy.
- The complete isolated Brave smoke test passed against the relocated companion, including a download after closing the popup, with no page exceptions.
- Live YouTube clip/transcript, X clip, Facebook clip, generic MP4/MP3, captionless failure and cancellation checks passed from the relocated runtime. FFprobe verified the media streams and durations listed below.
- Config and job history are excluded from the portable ZIP. Generated console wrappers and bytecode caches are excluded as well. Per-file checksums are included.
- This was a relocated-copy test on the development PC, not a test on separate physical hardware. The supported target is Windows x64.

## Automated checks

- Three JavaScript tests: subsecond/time parsing, invalid ranges, full-video semantics, playlist/timestamp URL normalization and request construction.
- Seven Python tests: URL restrictions, options validation, job path restrictions, framed native messages, streaming replies before stdin closes, cancellation of an already running process plus its descendant, and resetting copied settings for a different computer/user.
- Manifest/assets/syntax check: stable ID, all declared files, no persistent host permissions, no automatic content scripts or cookies permission.
- Browser DOM fixtures: YouTube duration/current time, X multiple video attachment selection, Facebook permalink and identity-matched progressive JSON, exclusion of another video's URLs, and generic media discovery.
- Actual Brave extension: native connection, metadata loading, exact boundaries, Alt adjustments, timeline zoom, saved output mode, per-video trim persistence, invalid-range blocking, download continuation after closing the popup, recent status and no page exceptions.
- Popup and Settings screenshots reviewed. The download button fits a 440 × 600 viewport. A separate pass verified the final compact layout and immediate trim persistence.

## Live output checks

| Source | Requested interval | Result |
| --- | --- | --- |
| YouTube `dmoaGcylPf0` | 15.125–18.875 s | MP4, H.264 + AAC, 3.800 s; requested 3.750 s |
| Same YouTube video | 170.25–180.75 s | Nonempty Markdown transcript; selection metadata and whole overlapping English caption text checked |
| X `captainamerica/status/719944021058060289` | 0.25–1.75 s | MP4, H.264 + AAC, 1.5015 s |
| Facebook `100033620354545/videos/106560053808006` | 0.25–1.75 s | MP4, H.264 + AAC, 1.5333 s |
| W3Schools `html/mov_bbb.mp4` | 1.25–3.75 s | MP4, H.264 + AAC, 2.560 s; completed after popup closed |
| Same direct file | 1.25–3.75 s | MP3 audio, 2.5047 s |
| Same direct file, transcript mode | Full video | Correctly failed for missing captions; no empty transcript published |
| Cancelled generic download | Before processing | Cancelled with no output publication; separate automated test covers an active child process tree |

Every media result passed FFprobe stream/duration checks. Exact cuts are limited by video frames and audio packets; entering milliseconds does not guarantee a container duration identical to that decimal value.

Provider variability was also observed: yt-dlp's old `BaW_jenozKc` YouTube example was unavailable, one old X amplify example returned a provider error, and one old Facebook example failed extraction. Other public examples above worked. These checks establish working paths, not universal support for every post, privacy setting or future site version. Authenticated downloads and native folder/cookies dialogs were not exercised with real user data.

Setup created this application's three per-user native-host registrations and an isolated local Python environment. All download and transcript code is shipped in this project. Default output is restored to `~/Videos/Video Tools`; QA jobs are archived in the QA folder rather than shown as the user's download history.
