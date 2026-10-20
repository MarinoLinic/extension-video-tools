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
from common import jobs,clear_history,write_json
from provenance import source_metadata,media_tags
from captions import Segment
from transcripts import export_transcript
from sources import extract_single_video,x_card_fallback_url
import shutil

class HostTests(unittest.TestCase):
    def test_x_card_fallback_is_limited_to_one_resolved_video(self):
        from unittest.mock import Mock
        url='https://x.com/test/status/123/video/1'
        base='https://x.com/test/status/123'
        missing=RuntimeError('ERROR: [twitter] 123: Video #1 is unavailable')
        ydl=Mock();ydl.extract_info.side_effect=[missing,{'id':'card-video','title':'One video'}]
        info,resolved=extract_single_video(ydl,url)
        self.assertEqual(resolved,base);self.assertEqual(info['id'],'card-video')
        self.assertEqual(ydl.extract_info.call_args.args,(base,))
        for result in ({'_type':'playlist','entries':[{},{}]},{'entries':[{}]},None):
            ydl=Mock();ydl.extract_info.side_effect=[missing,result]
            with self.assertRaises(ValueError):extract_single_video(ydl,url)
        for other,error in ((url.replace('/video/1','/video/2'),missing),
                            (url.replace('x.com','example.com'),missing),
                            (url,RuntimeError('Login required'))):
            self.assertIsNone(x_card_fallback_url(other,error))
            ydl=Mock();ydl.extract_info.side_effect=error
            with self.assertRaises(RuntimeError):extract_single_video(ydl,other)
            self.assertEqual(ydl.extract_info.call_count,1)

    def test_clear_history_keeps_active_jobs_and_files(self):
        folder=ROOT/'.local'/'test-work'/str(time.time_ns());folder.mkdir(parents=True)
        saved=folder/'saved.mp4';saved.write_bytes(b'preserve me')
        states=['completed','failed','cancelled','running','queued','cancelling','running']
        for index,state in enumerate(states):
            job=folder/f'{index:020x}'
            write_json(job/'request.json',{'title':state})
            write_json(job/'status.json',{'state':state,'updated':0 if index==6 else time.time(),'files':[str(saved)]})
        with patch('common.JOBS',folder):
            result=clear_history()
            self.assertEqual(len(result['cleared']),4)
            self.assertEqual(len(jobs()),3)
            self.assertEqual(len(jobs(include_hidden=True)),7)
            self.assertEqual(len(clear_history()['cleared']),4)
            write_json(folder/'00000000000000000006'/'status.json',{'state':'running','updated':time.time()})
            self.assertEqual(len(jobs()),4,'A resumed worker must become visible again.')
        self.assertEqual(saved.read_bytes(),b'preserve me')
        self.assertTrue((folder/'00000000000000000000'/'request.json').is_file())

    def test_source_tags_keep_page_and_stream_urls_separate(self):
        options=request_options({'url':'https://cdn.example.com/v.mp4?sig=123','page_url':'https://example.com/post/4'})
        record=source_metadata(options,{'webpage_url':'https://example.com/video/4'},
            ['https://cdn.example.com/video','https://cdn.example.com/audio','blob:wrong',None])
        self.assertEqual(record['page_url'],'https://example.com/post/4')
        self.assertEqual(len(record['media_urls']),2)
        self.assertIn('Page URL: https://example.com/post/4',media_tags(record)['comment'])
        with self.assertRaises(ValueError):request_options({'url':options['url'],'page_url':'file:///private'})

    def test_mp4_and_mp3_embed_readable_links_and_preserve_author(self):
        stage=Path(r'C:\Users\marin\agent-files\trash')/'video-tools-tag-tests'/str(time.time_ns())
        stage.mkdir(parents=True)
        ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
        for suffix,mode in (('mp4','video'),('mp3','audio')):
            path=stage/f'sample.{suffix}'
            command=[ffmpeg,'-v','error','-f','lavfi','-i','sine=duration=0.4']
            if mode=='video':command+=['-f','lavfi','-i','color=c=black:s=64x64:d=0.4','-c:v','libx264','-c:a','aac']
            command+=['-metadata','artist=Test author','-metadata','title=Test title',str(path)]
            subprocess.run(command,check=True,capture_output=True)
            worker=Worker.__new__(Worker)
            worker.folder=stage;worker.request={};worker.cfg={'cookies':''};worker.lines=[]
            worker.percent=None;worker.files=[];worker.state='running';worker.message='';worker.last_write=0
            worker.options=request_options({'url':'https://example.com/video/4','page_url':'https://example.com/post/4','mode':mode})
            worker.source_info={'webpage_url':'https://example.com/video/4'}
            worker.media_urls=['https://cdn.example.com/video?token=example','https://cdn.example.com/audio']
            tagged=worker.embed_sources(path)
            data=json.loads(subprocess.check_output([ffprobe,'-v','error','-show_entries','format_tags','-of','json',str(tagged)]))
            tags={key.lower():value for key,value in data['format']['tags'].items()}
            self.assertEqual(tags['artist'],'Test author')
            self.assertEqual(tags['title'],'Test title')
            self.assertEqual(tags['page_url'],'https://example.com/post/4')
            self.assertEqual(json.loads(tags['media_urls']),worker.media_urls)
            self.assertIn('Media URL: https://cdn.example.com/audio',tags['comment'])

    def test_transcript_keeps_source_links_in_front_matter(self):
        stage=ROOT/'.local'/'test-work'/str(time.time_ns())
        info={'title':'Caption fixture','id':'fixture','url':'https://cdn.example.com/v.mp4','webpage_url':'https://example.com/video/4'}
        class Extractor:
            def __init__(self,*args,**kwargs):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def extract_info(self,*args,**kwargs):return info
        with patch('yt_dlp.YoutubeDL',Extractor),patch('transcripts.fetch_segments',return_value=([Segment(0,1,'Hello.')],'en','manual')):
            path=export_transcript(request_options({'url':info['webpage_url'],'page_url':'https://example.com/post/4'}),stage)
        text=path.read_text(encoding='utf-8')
        self.assertIn('page_url: "https://example.com/post/4"',text)
        self.assertIn('source_url: "https://example.com/video/4"',text)
        self.assertIn('media_urls: ["https://cdn.example.com/v.mp4"]',text)
        self.assertIn('Hello.',text)

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
