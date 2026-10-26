import argparse
from contextlib import contextmanager
import datetime as dt
from decimal import Decimal
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import parse_qs, urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'archive/contributions/codex'))
from pkst_codec import cid,encode
DB=ROOT/'.cache/catalog.sqlite'

def lines(folder):
    for path in sorted((ROOT/folder).glob('*.jsonl')):
        with path.open(encoding='utf-8') as stream:
            for line in stream:yield json.loads(line)

def order_time(value,fmt):
    if value is None:return '1:'
    if fmt=='epoch-decimal':seconds=Decimal(value)
    elif fmt=='rfc3339':
        when=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if when.tzinfo is None:return '1:'
        delta=when-dt.datetime(1970,1,1,tzinfo=dt.timezone.utc)
        seconds=Decimal(delta.days*86400+delta.seconds)+Decimal(delta.microseconds)/1000000
    else:return '1:'
    # Sortable nonnegative offset; preserve the original timestamp separately.
    return '0:'+format(seconds+Decimal('1000000000000000'),'050.20f')

def build():
    DB.parent.mkdir(exist_ok=True)
    target=DB.with_suffix('.building.sqlite')
    if target.exists():raise RuntimeError('An unfinished index exists: inspect .cache/catalog.building.sqlite before retrying.')
    db=sqlite3.connect(target)
    db.executescript('''CREATE TABLE objects(cid TEXT PRIMARY KEY, schema TEXT, body TEXT);
      CREATE TABLE events(cid TEXT PRIMARY KEY, original TEXT UNIQUE, source TEXT, platform TEXT,
        thread TEXT, role TEXT, time TEXT, time_format TEXT, sort_time TEXT, record_kind TEXT, text TEXT);
      CREATE TABLE parts(event TEXT, ordinal INTEGER, content TEXT, PRIMARY KEY(event,ordinal));
      CREATE INDEX by_thread ON events(source,sort_time,cid);
      CREATE INDEX by_platform ON events(platform,role);
      CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);''')
    object_count=0
    for row in lines('corpus/objects'):
        if cid(encode(row['object']))!=row['cid']:raise ValueError('Object identity mismatch: '+row['cid'])
        db.execute('INSERT INTO objects VALUES(?,?,?)',(row['cid'],row['object']['schema'],json.dumps(row['object'],ensure_ascii=False)))
        object_count+=1
    event_count=0
    for row in lines('corpus/events'):
        result=db.execute('SELECT body FROM objects WHERE cid=?',(row['cid'],)).fetchone()
        if result is None:raise ValueError('Missing event object')
        obj=json.loads(result[0])
        if [part['$link'] for part in obj['content']]!=row['content']:raise ValueError('Event contents differ')
        if obj['original_occurrence_cid']!=row['original_occurrence']:raise ValueError('Event provenance differs')
        text=[]
        for i,key in enumerate(row['content']):
            stored=db.execute('SELECT body FROM objects WHERE cid=?',(key,)).fetchone()
            if stored is None:raise ValueError('Missing public content')
            content=json.loads(stored[0]);text.append(content['text'])
            db.execute('INSERT INTO parts VALUES(?,?,?)',(row['cid'],i,key))
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)',(
            row['cid'],row['original_occurrence'],row['source'],row['platform'],row['thread'],row['role'],
            row['time'],row['time_format'],order_time(row['time'],row['time_format']),row.get('record_kind','conversation'),'\n\n'.join(text)))
        event_count+=1
    coverage=json.loads((ROOT/'publication/coverage.json').read_bytes())
    if event_count!=coverage['published_events'] or object_count!=coverage['public_objects']:raise ValueError('Coverage counts differ')
    db.execute('INSERT INTO metadata VALUES(?,?)',('coverage',json.dumps(coverage,ensure_ascii=False)))
    db.commit()
    if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise ValueError('Index integrity failed')
    db.close();target.replace(DB)
    return {'events':event_count,'objects':object_count,'database':'.cache/catalog.sqlite','status':'verified-and-built'}

@contextmanager
def connect():
    if not DB.exists():raise RuntimeError('Run python -m pkst_public build first.')
    connection=sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    try:yield connection
    finally:connection.close()

def limited(value):
    value=int(value)
    if not 1<=value<=100:raise ValueError('limit must be 1..100')
    return value

def search(db,q,limit=20,platform=None,role=None):
    if not isinstance(q,str) or not 1<=len(q)<=512:raise ValueError('q must contain 1..512 characters')
    conditions=['instr(text,?)>0'];values=[q]
    if platform:conditions.append('platform=?');values.append(platform)
    if role:conditions.append('role=?');values.append(role)
    sql='SELECT cid,original,source,platform,thread,role,time,time_format,record_kind,text FROM events WHERE '+' AND '.join(conditions)+' ORDER BY sort_time,cid LIMIT ?'
    result=[]
    for row in db.execute(sql,values+[limited(limit)]):
        item=dict(row);text=item.pop('text');offset=max(0,text.index(q)-100)
        item.update(excerpt=text[offset:offset+700],excerpt_start=offset);result.append(item)
    return {'query':q,'results':result,'limit':limit,'order':'known native time then CID; unknown times last; no inferred reply order'}

def event(db,key):
    row=db.execute('SELECT * FROM events WHERE cid=? OR original=?',(key,key)).fetchone()
    if row is None:raise KeyError('Event not in public release')
    result=dict(row);result.pop('sort_time')
    result['parts']=[r[0] for r in db.execute('SELECT content FROM parts WHERE event=? ORDER BY ordinal',(row['cid'],))]
    return result

def object_value(db,key):
    row=db.execute('SELECT body FROM objects WHERE cid=?',(key,)).fetchone()
    if row is None:raise KeyError('Object not in public release')
    return {'cid':key,'object':json.loads(row[0])}

def thread(db,key,limit=20,offset=0):
    if not 0<=offset<=1000000:raise ValueError('offset must be 0..1000000')
    rows=db.execute('SELECT cid,original,role,time,time_format,record_kind,text FROM events WHERE source=? ORDER BY sort_time,cid LIMIT ? OFFSET ?',(key,limited(limit),offset)).fetchall()
    return {'source':key,'offset':offset,'events':[dict(r) for r in rows],
      'order':'known native time then CID; unknown times last; native_parent_ids in event objects preserve available branch references'}

def stats(db):return json.loads(db.execute('SELECT value FROM metadata WHERE key=?',('coverage',)).fetchone()[0])

def verify_files():
    manifest=json.loads((ROOT/'publication/files.json').read_bytes())
    leaves=[]
    if [item['path'] for item in manifest['files']]!=sorted(set(item['path'] for item in manifest['files'])):
        raise ValueError('Manifest paths are not sorted and unique')
    for item in manifest['files']:
        path=(ROOT/item['path']).resolve()
        if not path.is_relative_to(ROOT.resolve()):raise ValueError('Manifest path leaves repository')
        if not path.is_file():raise ValueError('Missing file: '+item['path'])
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        if digest.hexdigest()!=item['sha256']:raise ValueError('Changed file: '+item['path'])
        leaves.append(hashlib.sha256(b'\x00'+item['path'].encode()+b'\x00'+digest.digest()).digest())
    if not leaves:raise ValueError('Empty file manifest')
    while len(leaves)>1:
        if len(leaves)%2:leaves.append(leaves[-1])
        leaves=[hashlib.sha256(b'\x01'+leaves[i]+leaves[i+1]).digest() for i in range(0,len(leaves),2)]
    if leaves[0].hex()!=manifest['merkle_root']:raise ValueError('File Merkle root differs')
    return {'status':'pass','files':len(manifest['files']),'merkle_root':manifest['merkle_root']}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlsplit(self.path);args=parse_qs(parsed.query)
        def param(name,default=None):return args.get(name,[default])[0]
        try:
            with connect() as db:
                if parsed.path=='/v1/stats':result=stats(db)
                elif parsed.path=='/v1/search':result=search(db,param('q'),limited(param('limit',20)),param('platform'),param('role'))
                elif parsed.path.startswith('/v1/events/'):result=event(db,parsed.path[len('/v1/events/'):])
                elif parsed.path.startswith('/v1/objects/'):result=object_value(db,parsed.path[len('/v1/objects/'):])
                elif parsed.path.startswith('/v1/threads/'):result=thread(db,parsed.path[len('/v1/threads/'):],limited(param('limit',20)),int(param('offset',0)))
                elif parsed.path=='/v1/editions':result=json.loads((ROOT/'history/editions.json').read_bytes())
                else:raise KeyError('Unknown endpoint')
            status=200
        except (ValueError,TypeError) as error:result={'error':str(error)};status=400
        except KeyError as error:result={'error':str(error)};status=404
        except RuntimeError as error:result={'error':str(error)};status=503
        body=json.dumps(result,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)

def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    for name in ['build','verify','stats']:sub.add_parser(name)
    query=sub.add_parser('search');query.add_argument('q');query.add_argument('--limit',type=int,default=20);query.add_argument('--platform');query.add_argument('--role')
    for name in ['event','object']:
        parser=sub.add_parser(name);parser.add_argument('cid')
    serve=sub.add_parser('serve');serve.add_argument('--host',default='127.0.0.1');serve.add_argument('--port',type=int,default=8765)
    args=ap.parse_args()
    if args.command=='build':result=build()
    elif args.command=='verify':result=verify_files()
    elif args.command=='serve':
        if not DB.exists():raise RuntimeError('Run python -m pkst_public build first.')
        server=ThreadingHTTPServer((args.host,args.port),Handler)
        print(f'Read-only API: http://{args.host}:{server.server_port}/v1/stats',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
        return
    else:
        with connect() as db:
            if args.command=='stats':result=stats(db)
            elif args.command=='search':result=search(db,args.q,args.limit,args.platform,args.role)
            elif args.command=='event':result=event(db,args.cid)
            else:result=object_value(db,args.cid)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
