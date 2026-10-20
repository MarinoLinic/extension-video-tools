"""Caption retrieval and Markdown export shipped entirely with this project."""
from __future__ import annotations
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import sys
from common import config,read_json,request_options,youtube_url
from captions import caption_candidates,parse_captions,markdown,matches
from provenance import source_metadata

def fetch_segments(ydl,info,options,cookies):
    from yt_dlp.networking import Request
    attempts={}; errors=[]
    for language,source,track in caption_candidates(info,tuple(options['languages'].split(',')),'prefer-manual'):
        key=(language,source)
        if attempts.get(key,0)>=2: continue
        attempts[key]=attempts.get(key,0)+1
        try:
            with ydl.urlopen(Request(track['url'],headers=info.get('http_headers') or {})) as response:
                raw=response.read(8*1024*1024+1)
            if len(raw)>8*1024*1024: raise ValueError('Caption response is too large.')
            segments=parse_captions(raw.decode('utf-8-sig'),track.get('ext',''))
            if segments: return segments,language,source
        except Exception as error: errors.append(str(error))
    # An independent caption endpoint sometimes works when the first is rate limited.
    # No browser credentials are collected; do not use this endpoint in explicit-cookie mode.
    if youtube_url(options['url']) and not cookies:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            import requests
            class Session(requests.Session):
                def request(self,*args,**kwargs):
                    kwargs.setdefault('timeout',20)
                    return super().request(*args,**kwargs)
            with Session() as session:
                tracks=list(YouTubeTranscriptApi(http_client=session).list(info['id']))
                for language in options['languages'].split(','):
                    for track in sorted(tracks,key=lambda t:t.is_generated):
                        if matches(track.language_code,language):
                            segments=parse_captions(track.fetch().to_raw_data())
                            if segments: return segments,track.language_code,'auto-generated' if track.is_generated else 'manual'
        except Exception as error: errors.append(str(error))
    raise RuntimeError('No usable captions were found for the selected language. Speech recognition was not performed. '+(' '.join(errors[-1:])[:400]))

def export_transcript(options,stage):
    import yt_dlp
    cfg=config()
    settings=dict(quiet=True,no_warnings=True,noplaylist=True,socket_timeout=20,retries=1,
        js_runtimes={name:{'path':shutil.which(name)} for name in ('node','deno') if shutil.which(name)})
    if cfg['cookies']: settings['cookiefile']=cfg['cookies']
    with yt_dlp.YoutubeDL(settings) as ydl:
        info=ydl.extract_info(options['url'],download=False)
        if not info or 'entries' in info: raise RuntimeError('Choose an individual video.')
        if info.get('is_live') or info.get('live_status') in ('is_live','is_upcoming'):
            raise RuntimeError('Live streams can be downloaded after they have finished.')
        segments,language,source=fetch_segments(ydl,info,options,cfg['cookies'])
    segments=[s for s in segments if (s.start+s.duration>options['start'] or s.start>=options['start']) and (options['end'] is None or s.start<options['end'])]
    if not segments: raise RuntimeError('No caption cues overlap the selected time range.')
    meta=dict(title=info.get('title') or 'Transcript',url=options['url'],video_id=info.get('id'),
        uploader=info.get('uploader'),duration_seconds=info.get('duration'),
        downloaded_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        language=language,transcript_source=source,
        selection={'start_seconds':options['start'],'end_seconds':options['end']},
        selection_boundary='Whole overlapping cues; times remain relative to the original video.')
    meta.update(source_metadata(options,info,[info.get('url')]+[f.get('url') for f in info.get('requested_formats') or []]))
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',meta['title'])[:100].rstrip(' .') or 'Transcript'
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',stem): stem='_'+stem
    stage=Path(stage);stage.mkdir(parents=True,exist_ok=True)
    path=stage/(stem+'.md');path.write_text(markdown(meta,segments),encoding='utf-8')
    return path.resolve()

if __name__=='__main__':
    try:
        path=export_transcript(request_options(read_json(sys.argv[1],{})),sys.argv[2])
        print('VIDEO_TOOLS_FILE:'+str(path),flush=True)
    except Exception as error:
        print(str(error),file=sys.stderr,flush=True);raise SystemExit(1)
