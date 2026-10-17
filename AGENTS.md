# Project instructions

- This repository is `extension-video-tools`. Keep changes isolated from the existing scraper extensions and `projects-python/youtube_tools`. Reuse YouTube Tools through its CLI; do not fork its engine into this project.
- Windows entry point: `Setup.cmd`. Browser files live only in `extension/`; native helper source is in `host/`. Python dependencies belong in `.local/runtime`. Do not change global Python, PATH, unrelated browser settings or assistant configuration.
- Keep the public key in `extension/manifest.json` stable. Native-host `allowed_origins` must remain restricted to the derived extension ID. Never store a private signing key.
- Preserve on-demand `activeTab` access. No automatic browser-cookie reading, broad persistent host permissions, HTTP listener or arbitrary shell/command RPC. Helper actions are an explicit allowlist; content scripts cannot invoke them.
- Native protocol stdout is binary framed JSON only. The C# launcher must flush each input frame immediately while stdin stays open. Test this before claiming browser connectivity works.
- Clip boundaries belong to each source URL. Save edits immediately because a toolbar popup may close on the next click. Keep exact timestamp entry and subsecond controls accessible for long videos.
- At most two jobs run at once. Each owns its child process tree. Cancellation must stop those children and must not publish partial output. Closing a popup or browser must not kill a download.
- Stage under the chosen destination, verify output with FFprobe, and publish without overwriting completed files. Keep partial artifacts. Do not add broad cleanup or deletion.
- Transcripts come from captions; do not invent text, silently invoke speech recognition or claim success for an empty file. Preserve whole overlapping cues for selected ranges.
- Facebook JSON fallback must match the selected video identity, validate CDN URLs and bound traversal. Never mix recommendations or comments into a selected item.
- Keep runtime config, job history, signed URLs, cookies and QA artifacts out of Git and packages. QA profiles and downloaded samples go under `C:\Users\marin\agent-files\trash`, never the user's real browser profile. Git ignore does not exclude OneDrive sync.
- Check `npm test`, `npm run check`, and the Python host tests. Browser/native changes also need the isolated Brave smoke test and visual inspection at 440 × 600. Provider failures must be reported honestly; no authenticated tests without explicit authorization.
- Update README and VERIFICATION for material behavior changes. The dependency lock is a verified baseline; do not claim untested future versions work.
