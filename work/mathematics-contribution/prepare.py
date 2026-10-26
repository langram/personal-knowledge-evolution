"""Freeze one new request and reuse existing source identities; no publication."""
import hashlib, json, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'outputs/personal-thought-archive'
WORK = Path(__file__).resolve().parent
OUT = BASE / 'dossiers/2026-10-26-mathematics-and-contribution'
C = BASE / 'contributions/codex'
ARCHIVE = C / 'mathematics-contribution-20261026'
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, cid_bytes, decode, link

def write_json(path, obj):
    path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def raw(data):
    key = cid(data, 0x55)
    path = ARCHIVE / 'raw' / (key + '.bin')
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    return key

def prepare():
    ARCHIVE.mkdir(exist_ok=True)
    (ARCHIVE/'raw').mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    pointer = json.loads((C/'catalog/current.json').read_bytes())
    prior = C/'new-principles-expanded-20261026'
    old_report = json.loads((prior/'report.json').read_bytes())
    old_path = BASE/'dossiers/2026-10-26-new-principles-expanded/01-manuscript.md'
    baseline = {'pointer':pointer, 'old_document':old_report['document'],
                'old_dossier_root':old_report['snapshot'],
                'old_manuscript':str(old_path.relative_to(BASE)),
                'old_manuscript_sha256':sha(old_path.read_bytes())}
    if (ARCHIVE/'baseline.json').exists():
        assert json.loads((ARCHIVE/'baseline.json').read_bytes()) == baseline
    else:
        write_json(ARCHIVE/'baseline.json',baseline)
    db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    def get(k):
        p,a,n=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
        with (BASE/p).open('rb') as f:
            f.seek(a);b=f.read(n)
        assert cid(b,cid_bytes(k)[1])==k
        return b if cid_bytes(k)[1]==0x55 else decode(b)
    existing=json.loads((prior/'selected-sources.json').read_bytes())
    refs=['R54886','R34488','R46622','R1857','R34511','R34496','R34499','R46621','SEED-R14-0','SEED-R16-0']
    chosen={ref:existing[ref] for ref in refs}
    for r in chosen.values():
        assert get(r['content'])['text']==r['text']
        assert get(r['occurrence'])['content'][0]['$link']==r['content']
        for anchor in r['anchors']:get(anchor)
    reqpath=ARCHIVE/'request-capture.json'
    if reqpath.exists():
        request=json.loads(reqpath.read_bytes())
    else:
        native=Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
        size=native.stat().st_size
        with native.open('rb') as f:prefix=f.read(size)
        assert len(prefix)==size
        matches=[];offset=0
        for line in prefix.splitlines(keepends=True):
            if not line.endswith(b'\n'):break
            r=json.loads(line);p=r.get('payload',{})
            if r.get('type')=='response_item' and p.get('role')=='user':
                for block in p.get('content',[]):
                    if block.get('type')=='input_text' and block['text'].startswith('《知识分子》发布的') and '请按照我之前的推理风格进行创作' in block['text']:
                        matches.append((offset,offset+len(line)-1,r,block['text']))
            offset+=len(line)
        assert len(matches)==1,('request matches',len(matches))
        a,b,r,text=matches[0];rawkey=raw(prefix);store=Store(ARCHIVE)
        source=store.put({'schema':'pkst/source@0.1','platform':'codex-local','namespace':'owner-openai-account','native_thread_id':'01a16c8a-f6e1-7580-b378-b6e49f0be965'})
        content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text})
        p=r['payload'];nativeid=p.get('id')
        t={'value':r['timestamp'],'format':'rfc3339','precision':'millisecond','zone_known':True,'unit':None}
        event=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':nativeid,'locator':None if nativeid else {'raw':link(rawkey),'start':a,'end':b,'coordinate':'decoded-jsonl-utf8-bytes'},'native_role':'user','actor_kind':'unknown','process_kind':'main','content':[link(content)],'native_parent_ids':None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]),'event_time':t})
        anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(rawkey),'occurrence':link(event),'coordinate':'decoded-jsonl-utf8-bytes','start':a,'end':b,'parser':'mathematics-chapter-request-prefix-v1','role_basis':'native user channel; quoted speech summary and own proposal separately assessed'})
        request={'ref':'MATH-REQUEST','occurrence':event,'content':content,'anchors':[anchor],'role':'user','time':r['timestamp'],'time_format':'rfc3339','native_event_time':t,'platform':'codex-local','thread':'01a16c8a-f6e1-7580-b378-b6e49f0be965','text':text,'capture':{'path':str(native),'bytes':size,'complete_line_bytes':offset,'raw':rawkey,'sha256':sha(prefix),'captured_at':datetime.now(timezone.utc).isoformat(),'start':a,'end':b,'scope':'fixed native prefix; only this request newly indexed; no hidden reasoning extracted'}}
        write_json(reqpath,request)
    chosen['MATH-REQUEST']=request
    for ref,r in chosen.items():
        r['ref']=ref;r['text_sha256']=sha(r['text'].encode('utf-8'))
    write_json(ARCHIVE/'selected-sources.json',chosen)
    print(json.dumps({'sources':len(chosen),'request_time':request['time'],'native_prefix_bytes':request['capture']['bytes'],'old_document':baseline['old_document']},ensure_ascii=False))

if __name__=='__main__':prepare()
