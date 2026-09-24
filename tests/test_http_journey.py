"""Exercise the complete HTTP workflow and request security boundaries."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from unittest.mock import patch
from server import make_server

class HTTPJourney(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.server=make_server(0,Path(self.temp.name)/'db.sqlite3')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_address[1]}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path='/api/state',actor='ops',data=None,headers=None):
        req=urllib.request.Request(self.url+path, data=json.dumps(data).encode() if data is not None else None,
            headers={'X-Demo-Actor':actor,'X-Demo-Token':self.server.token,'Content-Type':'application/json'}|(headers or {}))
        with urllib.request.urlopen(req) as r:return json.load(r)
    def test_complete_journey_replay_and_persistence(self):
        r=self.request('/api/command',data={'key':str(uuid.uuid4()),'action':'create','name':'Fictional HTTP Hire','department':'Engineering','starts_on':'2026-10-05'})
        case_id=r['id']
        for action,actor in [('approve','manager-jordan'),('deliver','ops'),('retry','ops'),('acknowledge','employee-'+case_id)]:
            body={'key':str(uuid.uuid4()),'action':action,'id':case_id,'version':r['version']}
            r=self.request('/api/command',actor,data=body)
            duplicate=self.request('/api/command',actor,data=body)
            self.assertTrue(duplicate['replayed']);self.assertEqual(duplicate['version'],r['version'])
        self.assertEqual(r['status'],'Complete')
        state=self.request(actor='employee-'+case_id)
        self.assertEqual(len(state['cases']),1);self.assertEqual(state['cases'][0]['attempts'],2)
        from core import Store
        self.assertEqual(Store(self.server.store.path).snapshot('employee-'+case_id)['cases'][0]['status'],'Complete')
    def test_path_traversal_and_unknown_actor(self):
        for path,actor,status in [('/../config.json','ops',404),('/.data/demo.sqlite3','ops',404),('/api/state','unknown',403)]:
            with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as caught:self.request(path,actor)
            self.assertEqual(caught.exception.code,status);caught.exception.close()
    def test_unicode_token_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/ask',data={'question':'workspace'},headers={'X-Demo-Token':'é'})
        self.assertEqual(caught.exception.code,403);caught.exception.close()
    def test_unexpected_get_error_is_generic(self):
        with patch.object(self.server.store,'snapshot',side_effect=RuntimeError('sensitive diagnostic')):
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request()
            self.assertEqual(caught.exception.code,500)
            self.assertNotIn(b'sensitive diagnostic',caught.exception.read());caught.exception.close()
    def test_oversized_request_and_nonobject(self):
        for body in ({'question':'x'*33000},[]):
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/ask',data=body)
            self.assertEqual(caught.exception.code,400);caught.exception.close()
    def test_invalid_content_type(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/ask',data={'question':'workspace'},headers={'Content-Type':'text/plain'})
        self.assertEqual(caught.exception.code,400);caught.exception.close()

if __name__=='__main__':unittest.main()
