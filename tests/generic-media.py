"""Opt-in network checks for audio, missing captions, and worker cancellation."""
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'host'))
from common import job_path,read_json
from native_host import dispatch
url='https://www.w3schools.com/html/mov_bbb.mp4'
audio=dispatch({'action':'download','url':url,'title':'QA generic audio','mode':'audio','start':1.25,'end':3.75})['id']
deadline=time.monotonic()+90
while time.monotonic()<deadline:
    state=read_json(job_path(audio)/'status.json',{})
    if state.get('state') in ('completed','failed'): break
    time.sleep(.5)
assert state.get('state')=='completed',state
print(json.dumps({'test':'audio',**state}),flush=True)
missing=dispatch({'action':'download','url':url,'title':'QA no captions','mode':'transcript'})['id']
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    state=read_json(job_path(missing)/'status.json',{})
    if state.get('state') in ('completed','failed'): break
    time.sleep(.5)
assert state.get('state')=='failed' and not state.get('files'),state
assert 'captions' in state.get('message',''),state
print('Missing captions correctly fail without creating a transcript.',flush=True)
cancel=dispatch({'action':'download','url':url,'title':'QA cancel','mode':'video','start':0,'end':5})['id']
dispatch({'action':'cancel','id':cancel})
deadline=time.monotonic()+30
while time.monotonic()<deadline:
    state=read_json(job_path(cancel)/'status.json',{})
    if state.get('state') in ('completed','failed','cancelled'): break
    time.sleep(.2)
assert state.get('state')=='cancelled' and not state.get('files'),state
print('Cancellation stops the owned worker without publishing a file.',flush=True)
