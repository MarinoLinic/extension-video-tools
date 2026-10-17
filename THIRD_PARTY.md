# Included components

Video Tools uses third-party open-source tools inside its private `runtime/` directory. They retain their original licenses and copyright notices.

| Component | Pinned runtime | Source and notices |
| --- | --- | --- |
| CPython | 3.12.10, Windows x64 embeddable distribution | [Python release](https://www.python.org/downloads/release/python-31210/); `runtime/python/LICENSE.txt` |
| Node.js | 26.7.0, Windows x64 | [Node distribution](https://nodejs.org/dist/v26.7.0/); `runtime/node/LICENSE` |
| FFmpeg and FFprobe | Gyan essentials 9.0.2 | [Build provider and source links](https://www.gyan.dev/ffmpeg/builds/), [FFmpeg source revision](https://github.com/FFmpeg/FFmpeg/commit/946fcce07b); `runtime/ffmpeg/LICENSE` and included documentation. This build is GPLv3. |
| pip and Python download packages | See installed metadata and `host/requirements.lock.txt` | Package licenses and notices are included under `runtime/python/Lib/site-packages`, including each package's `.dist-info` directory. |

Runtime archive URLs and expected SHA-256 hashes are recorded in `tools/runtime-manifest.json`. The setup script checks those hashes before extracting or executing downloaded tools. Python dependencies install only into the embedded interpreter. The runtime package does not include personal configuration or credentials.
