"""Optional public-site probes, using yt-dlp's own published extractor examples."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'host'))
from native_host import inspect_video
for url in ('https://twitter.com/starwars/status/665052190608723968',
            'https://www.facebook.com/radiokicksfm/videos/3676516585958356/'):
    try: print(json.dumps({'ok':True,**inspect_video({'url':url})},ensure_ascii=False),flush=True)
    except Exception as error: print(json.dumps({'url':url,'ok':False,'error':str(error)[:1200]},ensure_ascii=False),flush=True)
