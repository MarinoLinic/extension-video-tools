"""Local state and validated requests. Never accept arbitrary commands from the browser."""
from __future__ import annotations
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import time
import threading
import socket
from urllib.parse import urlsplit, urlunsplit, parse_qs, urlencode

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / '.local'
JOBS = STATE / 'jobs'
CONFIG = STATE / 'config.json'
HOST = 'com.marin.video_tools'
MAX_JOBS = 2
RUNTIME = ROOT / 'runtime'
os.environ['PATH'] = os.pathsep.join(str(p) for p in (RUNTIME/'ffmpeg'/'bin', RUNTIME/'node', RUNTIME/'python')) + os.pathsep + os.environ.get('PATH','')

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.{threading.get_ident()}.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    # Status readers may briefly hold a file on Windows.
    for attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(.02 * (attempt + 1))
    tmp.replace(path)

def config():
    saved=read_json(CONFIG,{}) or {}
    machine=socket.gethostname()+'|'+str(Path.home())
    if saved.get('machine',machine)!=machine: saved={}
    return {'output':saved.get('output',str(Path.home()/'Videos'/'Video Tools')),
            'cookies':saved.get('cookies',''),'machine':machine}

def validate_url(value):
    if not isinstance(value, str) or len(value) > 12000 or re.search(r'[\x00-\x20]', value):
        raise ValueError('Enter a complete HTTP or HTTPS video URL.')
    p = urlsplit(value)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password:
        raise ValueError('Only public HTTP and HTTPS video links are supported.')
    hostname = p.hostname.lower().rstrip('.')
    if hostname == 'localhost' or hostname.endswith(('.localhost', '.local', '.internal')) or '.' not in hostname:
        raise ValueError('Local network links are not supported.')
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError('Local network addresses are not supported.')
    # Never accidentally expand a YouTube video into its playlist.
    if hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        query = parse_qs(p.query)
        if query.get('v'):
            return 'https://www.youtube.com/watch?' + urlencode({'v': query['v'][0]})
        if p.path == '/playlist':
            raise ValueError('Open an individual video, rather than a playlist.')
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))

def youtube_url(url):
    return urlsplit(url).hostname.lower() in ('youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be','www.youtu.be')

def request_options(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid download request.')
    url = validate_url(data.get('url'))
    mode = data.get('mode', 'video')
    if mode not in ('video', 'audio', 'transcript'):
        raise ValueError('Choose video, audio or transcript.')
    def seconds(key, fallback):
        raw = data.get(key, fallback)
        if raw is None:
            return None
        if isinstance(raw, bool):
            raise ValueError('Times must be numbers.')
        value = float(raw)
        if not math.isfinite(value) or value < 0 or value > 604800:
            raise ValueError('Times must be between zero and seven days.')
        return round(value, 3)
    start, end = seconds('start', 0), seconds('end', None)
    if start is None or (end is not None and end <= start):
        raise ValueError('End must be later than start.')
    height = int(data.get('height', 1080))
    if height not in (480,720,1080,1440,2160,4320):
        raise ValueError('Unsupported resolution.')
    languages = data.get('languages', 'en')
    if not isinstance(languages, str) or not re.fullmatch(r'[A-Za-z0-9,*_-]{1,100}', languages):
        raise ValueError('Use language codes such as en or hr,en.')
    return dict(url=url, mode=mode, start=start, end=end, height=height,
                languages=languages, accurate=data.get('accurate', True) is True)

def job_path(job_id):
    if not isinstance(job_id, str) or not re.fullmatch(r'[a-f0-9]{20}', job_id):
        raise ValueError('Invalid job ID.')
    return JOBS / job_id

def public_job(folder):
    state = read_json(folder / 'status.json', {}) or {}
    request = read_json(folder / 'request.json', {}) or {}
    # A crashed or interrupted worker must not look permanently active.
    if state.get('state') in ('queued', 'running', 'cancelling') and time.time() - state.get('updated', 0) > 120:
        state = {**state, 'state': 'failed', 'message': 'Worker stopped responding. Partial files were kept; retry the download.'}
    return {**state, 'id': folder.name, 'mode': request.get('mode'),
            'title': request.get('title', 'Video'), 'start': request.get('start',0), 'end': request.get('end')}

def jobs():
    JOBS.mkdir(parents=True, exist_ok=True)
    items=[public_job(p) for p in JOBS.iterdir() if p.is_dir() and re.fullmatch(r'[a-f0-9]{20}',p.name)]
    return sorted(items,key=lambda item:item.get('created',0),reverse=True)
