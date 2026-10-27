import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from http.server import ThreadingHTTPServer
from pkst_public import __main__ as api

class PublicArchiveTests(unittest.TestCase):
    def test_author_source_and_provenance_roundtrip(self):
        with api.connect() as db:
            hits=api.search(db,'关于文章中的第十点，从学生的灵感',10,role='user')['results']
            self.assertTrue(hits)
            row=next(x for x in hits if x['time']=='2026-10-26T14:37:45.185Z')
            original=api.event(db,row['original']);public=api.event(db,row['cid'])
            self.assertEqual(original,public)
            self.assertIn('第一时间就分享新想法',public['text'])
            obj=api.object_value(db,row['cid'])['object']
            self.assertEqual(obj['original_occurrence_cid'],row['original'])

    def test_parameter_boundaries(self):
        with api.connect() as db:
            for bad in ['', 'x'*513]:
                with self.assertRaises(ValueError):api.search(db,bad)
            for bad in [0,-1,101]:
                with self.assertRaises(ValueError):api.search(db,'知识',bad)
            self.assertEqual(api.search(db,"' OR 1=1 --",1,platform="' OR 1=1 --")['results'],[])
            with self.assertRaises(KeyError):api.object_value(db,'../../README.md')

    def test_no_internal_envelopes_or_secret_only_hashes(self):
        with api.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE role IN ('system','developer','tool')").fetchone()[0],0)
        rows=json.loads((api.ROOT/'publication/redactions.json').read_bytes())
        self.assertTrue(rows)
        for row in rows:
            for finding in row['findings']:self.assertNotIn('sha256',finding)
        self.assertEqual(api.order_time(None,'unknown'),'1:')
        self.assertLess(api.order_time('2000-01-01T00:00:00Z','rfc3339'),api.order_time('1000000000','epoch-decimal'))

    def test_http_read_only_and_errors(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),api.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            with urlopen(base+'/v1/stats') as response:
                self.assertEqual(response.status,200)
                self.assertGreater(json.load(response)['published_events'],100000)
            with urlopen(base+'/v1/search?'+urlencode({'q':'动态权重','limit':2})) as response:
                result=json.load(response);self.assertTrue(result['results']);self.assertLessEqual(len(result['results']),2)
            with urlopen(base+'/v1/editions') as response:
                self.assertEqual(json.load(response),json.loads((api.ROOT/'history/editions.json').read_bytes()))
            for path,status in [('/v1/search?limit=999',400),('/v1/objects/not-a-cid',404),('/../../README.md',404)]:
                with self.assertRaises(HTTPError) as caught:urlopen(base+path)
                self.assertEqual(caught.exception.code,status)
                caught.exception.close()
            with self.assertRaises(HTTPError) as caught:urlopen(Request(base+'/v1/stats',data=b'{}',method='POST'))
            self.assertEqual(caught.exception.code,501)
            caught.exception.close()
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
