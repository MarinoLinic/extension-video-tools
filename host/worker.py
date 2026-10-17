"""One owned worker per download. Popup/browser closure does not interrupt it."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from common import ROOT, config, job_path, read_json, write_json, request_options, youtube_url

class Cancelled(Exception): pass

class Worker:
    def __init__(self, job_id):
        self.folder=job_path(job_id)
        self.request=read_json(self.folder/'request.json',{})
        self.options=request_options(self.request)
        self.cfg=config(); self.lines=[]; self.percent=None; self.files=[]
        self.state='running'; self.message='Reading video information…'; self.last_write=0

    def status(self, message=None, force=False):
        if message: self.message=message
        if not force and time.monotonic()-self.last_write<.5: return
        write_json(self.folder/'status.json',dict(state=self.state,message=self.message,
            percent=self.percent,files=self.files,log=self.lines[-8:],updated=time.time(),
            created=self.request.get('created',time.time())))
        self.last_write=time.monotonic()

    def check_cancel(self):
        if (self.folder/'cancel').exists(): raise Cancelled()

    def run_process(self, command, timeout=21600, capture_only=False):
        self.check_cancel()
        proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,text=True,encoding='utf-8',errors='replace',
            cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        messages=queue.Queue()
        def read():
            for line in proc.stdout: messages.put(line)
            messages.put(None)
        threading.Thread(target=read,daemon=True).start()
        output=[]; length=0; deadline=time.monotonic()+timeout; done=False
        try:
            while not done or proc.poll() is None:
                self.check_cancel()
                if time.monotonic()>deadline: raise RuntimeError('The operation timed out. Partial files were kept.')
                try: line=messages.get(timeout=.2)
                except queue.Empty:
                    self.status(); continue
                if line is None: done=True; continue
                line=line.strip()
                if line:
                    # Bound retained output; do not expose signed media links in the popup.
                    if length<4*1024*1024: output.append(line); length+=len(line)
                    if capture_only or line.startswith('{"exit_code"'): continue
                    safe=re.sub(r'https?://\S+','[media link]',line)
                    if self.cfg.get('cookies'): safe=safe.replace(self.cfg['cookies'],'[cookies file]')
                    self.lines.append(safe[:500]); self.lines=self.lines[-30:]
                    match=re.search(r'(\d+(?:\.\d+)?)%',line)
                    if match: self.percent=min(99,float(match[1])); self.message='Downloading…'
                    if any(x in line for x in ('[Merger]','[ExtractAudio]','[VideoConvertor]','[VideoRemuxer]','[Metadata]')):
                        self.message='Processing media…'; self.percent=None
                    self.status()
            code=proc.wait(timeout=10)
            if code: raise RuntimeError('\n'.join(self.lines[-4:]) or f'Download tool exited with code {code}.')
            return '\n'.join(output)
        except BaseException:
            if proc.poll() is None:
                if os.name=='nt':
                    # This PID belongs to the child we just launched, never a searched process.
                    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,timeout=15)
                else: proc.terminate()
                proc.wait(timeout=15)
            raise
        finally:
            proc.stdout.close()

    def youtube(self, stage):
        script=Path(self.cfg['youtube_root'])/'yt.py'
        if not script.is_file(): raise RuntimeError('YouTube Tools was not found. Run Setup.cmd after placing it in projects-python/youtube_tools.')
        opts=self.options
        cmd=[sys.executable,'-X','utf8',str(script),opts['mode'],opts['url'],'-o',str(stage),
             '--playlist','no','--print-json','--languages',opts['languages']]
        if self.cfg['cookies']: cmd+=['--cookies',self.cfg['cookies']]
        if opts['start'] or opts['end'] is not None:
            cmd+=['--start',str(opts['start'])]
            if opts['end'] is not None: cmd+=['--end',str(opts['end'])]
        if opts['mode']=='video':
            cmd+=['--max-height',str(opts['height']),'--codec','best']
            if opts['accurate']: cmd+=['--accurate-cuts']
        elif opts['mode']=='audio': cmd+=['--no-embed-thumbnail']
        output=self.run_process(cmd)
        summary=next((json.loads(line) for line in reversed(output.splitlines()) if line.startswith('{"exit_code"')),None)
        if not summary: raise RuntimeError('YouTube Tools returned no download summary.')
        results=summary.get('results',[])
        if summary.get('exit_code') or not results: raise RuntimeError(str(results[-1].get('error','Download failed.')) if results else 'No video returned.')
        return [Path(p) for item in results for p in item.get('files',[])]

    def generic_transcript(self, stage):
        # Reuse the maintained caption parser; only metadata/URL formatting differs for other sites.
        sys.path.insert(0,self.cfg['youtube_root'])
        from youtube_tools.captions import caption_candidates, parse_captions, markdown
        import yt_dlp
        opts=self.options
        settings=dict(quiet=True,no_warnings=True,noplaylist=True,socket_timeout=20,retries=1)
        if self.cfg['cookies']: settings['cookiefile']=self.cfg['cookies']
        with yt_dlp.YoutubeDL(settings) as ydl:
            info=ydl.extract_info(opts['url'],download=False)
            if not info or 'entries' in info: raise RuntimeError('Choose an individual video.')
            for language,source,track in caption_candidates(info,tuple(opts['languages'].split(',')),'prefer-manual'):
                self.check_cancel()
                with ydl.urlopen(track['url']) as response:
                    raw=response.read(8*1024*1024+1)
                if len(raw)>8*1024*1024: continue
                segments=parse_captions(raw.decode('utf-8-sig'),track.get('ext',''))
                segments=[s for s in segments if (s.start+s.duration>opts['start'] or s.start>=opts['start']) and (opts['end'] is None or s.start<opts['end'])]
                if not segments: continue
                meta=dict(title=info.get('title') or 'Transcript',url=opts['url'],language=language,
                    transcript_source=source,selection={'start':opts['start'],'end':opts['end']},
                    selection_boundary='Whole overlapping cues; times remain relative to the original video.')
                stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',meta['title'])[:100].rstrip(' .') or 'Transcript'
                path=stage/(stem+'.md'); path.write_text(markdown(meta,segments),encoding='utf-8')
                return [path]
        raise RuntimeError('No usable captions were found for the selected language and time range. Speech recognition was not performed.')

    def generic(self, stage):
        opts=self.options
        if opts['mode']=='transcript': return self.generic_transcript(stage)
        selection=''
        if opts['start'] or opts['end'] is not None:
            end=f"{opts['end']:g}s" if opts['end'] is not None else 'end'
            selection=f" [{opts['start']:g}s-{end}]"
        cmd=[sys.executable,'-X','utf8','-m','yt_dlp','--ignore-config','--no-playlist','--no-overwrites',
             '--windows-filenames','--newline','--progress','--socket-timeout','20','--retries','2',
             '--match-filter','!is_live',
             '-o',str(stage/('%(title).100B [%(id).60B]'+selection+'.%(ext)s')), '--print','after_move:VIDEO_TOOLS_FILE:%(filepath)s']
        if self.cfg['cookies']: cmd+=['--cookies',self.cfg['cookies']]
        if opts['mode']=='audio': cmd+=['-f','bestaudio/best','-x','--audio-format','mp3','--audio-quality','0']
        else:
            ceiling=f"[height<=?{opts['height']}]"
            cmd+=['-f',f'bv*{ceiling}+ba/b{ceiling}','-S','vcodec:h264,acodec:aac',
                  '--merge-output-format','mp4','--remux-video','mp4']
        if opts['start'] or opts['end'] is not None:
            end=opts['end'] if opts['end'] is not None else 'inf'
            cmd+=['--download-sections',f"*{opts['start']}-{end}"]
            if opts['mode']=='video' and opts['accurate']: cmd+=['--force-keyframes-at-cuts']
        cmd+=['--',opts['url']]
        output=self.run_process(cmd)
        return [Path(line.split('VIDEO_TOOLS_FILE:',1)[1]) for line in output.splitlines() if line.startswith('VIDEO_TOOLS_FILE:')]

    def validate_media(self, path):
        output=self.run_process([shutil.which('ffprobe'),'-v','error','-show_entries',
            'format=duration:stream=codec_type','-of','json',str(path)],timeout=30,capture_only=True)
        data=json.loads(output)
        duration=float(data.get('format',{}).get('duration',0))
        if not math.isfinite(duration) or duration<=0: raise RuntimeError('The saved file has no valid media duration.')
        streams={s.get('codec_type') for s in data.get('streams',[])}
        if self.options['mode']=='video' and 'video' not in streams: raise RuntimeError('The result has no video stream.')
        if self.options['mode']=='audio' and 'audio' not in streams: raise RuntimeError('The result has no audio stream.')
        if self.options['end'] is not None and (self.options['mode']=='audio' or self.options['accurate']):
            expected=self.options['end']-self.options['start']
            if abs(duration-expected)>max(1.0,expected*.01):
                raise RuntimeError(f'Clip duration was {duration:.2f}s; expected {expected:.2f}s. Staged file kept for inspection.')

    def run(self):
        self.status(force=True)
        # Generic caption fetching can block on the network; keep a heartbeat and check cancellation.
        stop=threading.Event()
        def heartbeat():
            while not stop.wait(10):
                if (self.folder/'cancel').exists():
                    # Network requests have bounded timeouts; media subprocess loop handles cancellation immediately.
                    continue
                self.status(force=True)
        thread=threading.Thread(target=heartbeat,daemon=True); thread.start()
        try:
            self.check_cancel()
            dest=Path(self.cfg['output']).expanduser().resolve(); dest.mkdir(parents=True,exist_ok=True)
            if shutil.disk_usage(dest).free<512*1024*1024: raise RuntimeError('Less than 512 MB is free on the destination drive. Choose another folder.')
            stage=dest/'.video-tools-work'/self.folder.name; stage.mkdir(parents=True,exist_ok=True)
            files=self.youtube(stage) if youtube_url(self.options['url']) else self.generic(stage)
            self.check_cancel()
            if not files: raise RuntimeError('The downloader produced no files.')
            for path in files:
                path=path.resolve()
                if not path.is_relative_to(stage) or not path.is_file() or path.stat().st_size==0:
                    raise RuntimeError('The downloader did not produce a valid staged file.')
                self.message='Checking saved file…'; self.percent=None; self.status(force=True)
                if path.suffix.lower()!='.md': self.validate_media(path)
            self.check_cancel()
            for path in files:
                # Unique suffix plus Windows exclusive rename preserves every existing output.
                target=dest/(path.stem+f' [{self.folder.name[:8]}]'+path.suffix)
                path.rename(target); self.files.append(str(target))
            self.state='completed'; self.percent=100; self.message='Saved to your folder.'
        except Cancelled:
            self.state='cancelled'; self.message='Cancelled. Partial files were kept.'; self.percent=None
        except Exception as exc:
            self.state='failed'; self.message=str(exc)[:1800]; self.percent=None
        finally:
            stop.set(); thread.join(timeout=1); self.status(force=True)

if __name__=='__main__': Worker(sys.argv[1]).run()
