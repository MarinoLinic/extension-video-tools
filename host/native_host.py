from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import uuid
from common import ROOT, STATE, JOBS, CONFIG, config, jobs, job_path, read_json, write_json, request_options, validate_url, MAX_JOBS

def inspect_video(data):
    import yt_dlp
    url = validate_url(data.get('url'))
    cfg = config()
    options = dict(quiet=True, no_warnings=True, noplaylist=True, socket_timeout=20,
                   retries=1, extractor_retries=1, skip_download=True,
                   js_runtimes={name:{'path':shutil.which(name)} for name in ('deno','node') if shutil.which(name)})
    if cfg['cookies']:
        options['cookiefile'] = cfg['cookies']
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info or info.get('_type') in ('playlist', 'multi_video') or 'entries' in info:
        raise ValueError('Open the individual video or choose a detected media item.')
    if info.get('is_live') or info.get('live_status') in ('is_live','is_upcoming'):
        raise ValueError('Live streams can be downloaded after they have finished.')
    duration=info.get('duration')
    # Generic direct files often omit duration in extractor metadata. Probe the stream header.
    if not duration and info.get('url') and shutil.which('ffprobe'):
        try:
            probe=subprocess.run([shutil.which('ffprobe'),'-v','error','-rw_timeout','10000000',
                '-show_entries','format=duration','-of','json',info['url']],capture_output=True,
                text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            duration=float(json.loads(probe.stdout).get('format',{}).get('duration',0)) or None
        except (OSError,ValueError,subprocess.TimeoutExpired): pass
    captions = set((info.get('subtitles') or {}).keys()) | set((info.get('automatic_captions') or {}).keys())
    return dict(url=url, title=info.get('title') or 'Video', duration=duration,
                uploader=info.get('uploader') or '', site=info.get('extractor_key') or 'Web video',
                languages=sorted(captions)[:100], captions=bool(captions), live=False)

def picker(kind):
    # Native dialogs are explicit UI actions; no filesystem browsing from page scripts.
    import base64
    powershell=str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe')
    dialog=subprocess.run([powershell,'-NoProfile','-STA','-ExecutionPolicy','Bypass',
        '-File',str(ROOT/'tools'/'pick-path.ps1'),kind],capture_output=True,text=True,
        timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    if dialog.returncode: raise RuntimeError('The file chooser could not be opened.')
    result=base64.b64decode(dialog.stdout.strip()).decode('utf-8') if dialog.stdout.strip() else ''
    if result:
        cfg = config(); cfg['output' if kind == 'folder' else 'cookies'] = str(Path(result).resolve())
        write_json(CONFIG, cfg)
    return health()

def health():
    import yt_dlp.version
    cfg = config()
    return { 'version':'1.1.0', 'output': cfg['output'], 'cookies':bool(cfg['cookies']),
             'youtube': (ROOT/'host'/'transcripts.py').is_file(),
             'portable':Path(sys.executable).is_relative_to(ROOT/'runtime'),
             'ffmpeg':bool(shutil.which('ffmpeg') and shutil.which('ffprobe')),
             'yt_dlp':yt_dlp.version.__version__, 'free_gb':round(shutil.disk_usage(ROOT).free/1024**3,1) }

def dispatch(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid request.')
    action = data.get('action')
    if action == 'health': return health()
    if action == 'inspect': return inspect_video(data)
    if action == 'jobs': return jobs()[:50]
    if action == 'pick_folder': return picker('folder')
    if action == 'pick_cookies': return picker('cookies')
    if action == 'clear_cookies':
        cfg=config(); cfg['cookies']=''; write_json(CONFIG,cfg); return health()
    if action == 'download':
        # The service worker serializes enqueue requests; lock across different browser instances as well.
        import msvcrt
        STATE.mkdir(parents=True,exist_ok=True)
        with (STATE/'enqueue.lock').open('a+b') as lock:
            lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                if sum(j.get('state') in ('running','queued','cancelling') for j in jobs()) >= MAX_JOBS:
                    raise ValueError('Two downloads are already active. Wait or cancel one first.')
                request=request_options(data)
                request['title']=str(data.get('title','Video'))[:300]
                request['created']=time.time()
                job_id=uuid.uuid4().hex[:20]; folder=job_path(job_id); folder.mkdir(parents=True)
                write_json(folder/'request.json',request)
                write_json(folder/'status.json',dict(state='queued',message='Starting download…',updated=time.time(),created=request['created'],files=[]))
                with (folder/'worker.log').open('ab') as output:
                    subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'host'/'worker.py'),job_id],
                        stdin=subprocess.DEVNULL,stdout=output,stderr=output,cwd=ROOT,
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                        close_fds=True)
                return {'id':job_id}
            finally:
                lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    if action == 'cancel':
        folder=job_path(data.get('id'))
        if not folder.is_dir(): raise ValueError('Download was not found.')
        (folder/'cancel').touch(); return {'cancelled':True}
    if action == 'reveal':
        folder=job_path(data.get('id')); state=read_json(folder/'status.json',{})
        files=state.get('files') or []
        if not files or not Path(files[0]).is_file(): raise ValueError('Saved file was not found.')
        subprocess.Popen(['explorer.exe','/select,',str(Path(files[0]).resolve())],creationflags=subprocess.CREATE_NO_WINDOW)
        return {'opened':True}
    if action == 'open_file':
        folder=job_path(data.get('id')); state=read_json(folder/'status.json',{})
        files=state.get('files') or []
        if not files or not Path(files[0]).is_file(): raise ValueError('Saved file was not found.')
        os.startfile(str(Path(files[0]).resolve()))
        return {'opened':True}
    raise ValueError('Unknown helper action.')

def read_exact(stream,count):
    result=b''
    while len(result)<count:
        chunk=stream.read(count-len(result))
        if not chunk: raise EOFError()
        result+=chunk
    return result

def main():
    if os.name=='nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(),os.O_BINARY); msvcrt.setmode(sys.stdout.fileno(),os.O_BINARY)
    while True:
        try:
            size=struct.unpack('=I',read_exact(sys.stdin.buffer,4))[0]
            if size>1024*1024: return
            data=json.loads(read_exact(sys.stdin.buffer,size))
        except (EOFError,ValueError,struct.error): return
        try: result={'id':data.get('_request'),'ok':True,'result':dispatch(data)}
        except Exception as exc: result={'id':data.get('_request') if isinstance(data,dict) else None,'ok':False,'error':str(exc)[:1500]}
        body=json.dumps(result,ensure_ascii=False).encode('utf-8')
        sys.stdout.buffer.write(struct.pack('=I',len(body))+body); sys.stdout.buffer.flush()

if __name__=='__main__': main()
