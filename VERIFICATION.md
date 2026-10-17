# Verification — 17 October 2026

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
