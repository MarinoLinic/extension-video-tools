"""Opt-in network verification. Leaves artifacts in the configured QA destination."""
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'host'))
from common import job_path,read_json
from native_host import dispatch
url='https://www.youtube.com/watch?v=dmoaGcylPf0'
requests=[{'url':url,'title':'QA YouTube precise clip','mode':'video','height':480,'start':15.125,'end':18.875,'accurate':True},
          {'url':url,'title':'QA YouTube selected transcript','mode':'transcript','start':170.25,'end':180.75,'languages':'en'}]
ids=[]
for request in requests:
    result=dispatch({'action':'download',**request});ids.append(result['id']);print('Started',result['id'],request['mode'],flush=True)
deadline=time.monotonic()+240
while time.monotonic()<deadline:
    states=[read_json(job_path(job)/'status.json',{}) for job in ids]
    if all(state.get('state') in ('completed','failed','cancelled') for state in states):
        for job,state in zip(ids,states):print(json.dumps({'id':job,**state},ensure_ascii=False),flush=True)
        if not all(s.get('state')=='completed' for s in states):raise SystemExit(1)
        break
    time.sleep(1)
else:raise SystemExit('Live verification timed out; workers and partial files preserved.')
