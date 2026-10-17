import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'host'))
from common import validate_url,request_options,job_path,config
from native_host import read_exact
from worker import Worker,Cancelled

class HostTests(unittest.TestCase):
    def test_settings_use_this_computer(self):
        with patch('common.read_json',return_value={'output':'C:/another-user/private','cookies':'C:/another-user/session.txt','machine':'another-computer'}):
            cfg=config()
        self.assertEqual(cfg['output'],str(Path.home()/'Videos'/'Video Tools'))
        self.assertEqual(cfg['cookies'],'')
        self.assertNotIn('engine_root',cfg)

    def test_url_boundary(self):
        for url in ('file:///C:/secret','http://localhost/video','http://127.0.0.1/x','http://192.168.1.1/x','https://user:pass@example.com/v','https://example.com/\n--exec','http://[::1]/x'):
            with self.subTest(url=url),self.assertRaises(ValueError): validate_url(url)
        self.assertEqual(validate_url('https://www.youtube.com/watch?v=BaW_jenozKc&list=PLfoo&t=20'),'https://www.youtube.com/watch?v=BaW_jenozKc')
        self.assertEqual(validate_url('https://video.example.com/movie.mp4?sig=abc#time'),'https://video.example.com/movie.mp4?sig=abc')

    def test_ranges(self):
        base={'url':'https://example.com/video'}
        for extra in ({'start':-1},{'end':0},{'start':float('nan')},{'end':float('inf')},{'mode':'--exec'},{'languages':'en;calc'},{'height':123}):
            with self.subTest(extra=extra),self.assertRaises((ValueError,TypeError)): request_options({**base,**extra})
        self.assertEqual(request_options({**base,'start':170.25,'end':180.75})['start'],170.25)

    def test_job_path_boundary(self):
        for value in ('../config','foo',None,'C:\\Windows'):
            with self.assertRaises(ValueError): job_path(value)

    def test_framing_and_launcher(self):
        with self.assertRaises(EOFError): read_exact(io.BytesIO(b'abc'),4)
        launcher=ROOT/'.local'/'VideoToolsHost.exe'
        self.assertTrue(launcher.is_file(),'Run Setup.cmd before the native integration tests.')
        requests=[{'action':'health','_request':1},{'action':'inspect','url':'file:///secret','_request':2}]
        raw=b''
        for request in requests:
            body=json.dumps(request).encode();raw+=struct.pack('=I',len(body))+body
        child=subprocess.run([str(launcher)],input=raw,capture_output=True,timeout=30)
        self.assertEqual(child.returncode,0,child.stderr.decode(errors='replace'))
        stream=io.BytesIO(child.stdout); replies=[]
        while header:=stream.read(4): replies.append(json.loads(read_exact(stream,struct.unpack('=I',header)[0])))
        self.assertEqual(len(replies),2);self.assertEqual(replies[0]['id'],1)
        self.assertTrue(replies[0]['result']['youtube']);self.assertTrue(replies[0]['result']['ffmpeg'])
        self.assertFalse(replies[1]['ok']);self.assertEqual(replies[1]['id'],2)

    def test_launcher_flushes_before_stdin_closes(self):
        proc=subprocess.Popen([str(ROOT/'.local'/'VideoToolsHost.exe')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        body=json.dumps({'action':'health','_request':42}).encode()
        replies=[]
        def receive():
            size=struct.unpack('=I',read_exact(proc.stdout,4))[0]
            replies.append(json.loads(read_exact(proc.stdout,size)))
        reader=threading.Thread(target=receive,daemon=True)
        try:
            reader.start();proc.stdin.write(struct.pack('=I',len(body))+body);proc.stdin.flush()
            reader.join(timeout=10)
            self.assertFalse(reader.is_alive(),'Native messaging must flush each frame while the port stays open.')
            self.assertEqual(replies[0]['id'],42)
        finally:
            proc.stdin.close()
            if reader.is_alive():proc.kill()
            proc.wait(timeout=10);proc.stdout.close();proc.stderr.close()

    def test_cancel_running_owned_process_tree(self):
        folder=ROOT/'.local'/'test-work'/str(time.time_ns());folder.mkdir(parents=True)
        worker=Worker.__new__(Worker)
        worker.folder=folder;worker.request={};worker.cfg={'cookies':''};worker.lines=[]
        worker.percent=None;worker.files=[];worker.state='running';worker.message='';worker.last_write=0
        pidfile=folder/'descendant.txt'
        child_code='import time;time.sleep(60)'
        code=f"import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',{child_code!r}]);Path({str(pidfile)!r}).write_text(str(p.pid));print('ready',flush=True);time.sleep(60)"
        def cancel():
            deadline=time.monotonic()+10
            while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.03)
            (folder/'cancel').touch()
        watcher=threading.Thread(target=cancel,daemon=True);watcher.start()
        with self.assertRaises(Cancelled):worker.run_process([sys.executable,'-u','-c',code],timeout=15)
        watcher.join(timeout=1)
        self.assertTrue(pidfile.exists(),'The test cancelled an already running process.')
        import ctypes
        handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,int(pidfile.read_text()))
        if handle:
            try:
                exit_code=ctypes.c_ulong();ctypes.windll.kernel32.GetExitCodeProcess(handle,ctypes.byref(exit_code))
                self.assertNotEqual(exit_code.value,259,'The owned descendant must also stop.')
            finally:ctypes.windll.kernel32.CloseHandle(handle)

if __name__=='__main__':unittest.main()
