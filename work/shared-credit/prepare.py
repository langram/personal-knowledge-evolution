"""Freeze the author's new reflection and preserve the preceding edition."""
import hashlib, json, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'outputs/personal-thought-archive'
WORK=Path(__file__).resolve().parent
OUT=BASE/'dossiers/2026-10-26-shared-credit'
C=BASE/'contributions/codex'
ARCHIVE=C/'shared-credit-20261026'
PRIOR=C/'public-intelligence-20261026'
OLD=BASE/'dossiers/2026-10-26-public-intelligence'
sys.path.insert(0,str(C))
from pkst_codec import Store,cid,cid_bytes,decode,link
def write_json(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(b):
    k=cid(b,0x55);p=ARCHIVE/'raw'/(k+'.bin')
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    return k
def prepare():
    ARCHIVE.mkdir(exist_ok=True);(ARCHIVE/'raw').mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    report=json.loads((PRIOR/'report.json').read_bytes())
    baseline={'pointer':pointer,'old_document':report['document'],'old_chapter':report['chapter'],
              'old_dossier_root':report['snapshot'],'old_concept':report['concept'],
              'old_manuscript':str((OLD/'02-new-principles.md').relative_to(BASE)),
              'old_chapter_file':str((OLD/'01-chapter.md').relative_to(BASE)),
              'old_manuscript_sha256':sha((OLD/'02-new-principles.md').read_bytes()),
              'old_chapter_sha256':sha((OLD/'01-chapter.md').read_bytes())}
    if (ARCHIVE/'baseline.json').exists():assert json.loads((ARCHIVE/'baseline.json').read_bytes())==baseline
    else:write_json(ARCHIVE/'baseline.json',baseline)
    selected=json.loads((PRIOR/'selected-sources.json').read_bytes())
    db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    for ref,r in selected.items():
        path,a,n=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(r['content'],)).fetchone()
        with (BASE/path).open('rb') as f:f.seek(a);b=f.read(n)
        assert cid(b)==r['content'] and decode(b)['text']==r['text']
    db.close()
    reqfile=ARCHIVE/'request-capture.json'
    if reqfile.exists():request=json.loads(reqfile.read_bytes())
    else:
        native=Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
        size=native.stat().st_size
        with native.open('rb') as f:prefix=f.read(size)
        assert len(prefix)==size
        found=[];offset=0
        for line in prefix.splitlines(keepends=True):
            if not line.endswith(b'\n'):break
            record=json.loads(line);p=record.get('payload',{})
            if record.get('type')=='response_item' and p.get('role')=='user':
                for block in p.get('content',[]):
                    if block.get('type')=='input_text' and block['text'].startswith('关于文章中的第十点，从学生的灵感，到基层的创造') and '不敢提出' in block['text']:
                        found.append((offset,offset+len(line)-1,record,block['text']))
            offset+=len(line)
        assert len(found)==1,('new reflection matches',len(found))
        a,b,r,text=found[0];rawkey=raw(prefix);store=Store(ARCHIVE)
        source=store.put({'schema':'pkst/source@0.1','platform':'codex-local','namespace':'owner-openai-account','native_thread_id':'01a16c8a-f6e1-7580-b378-b6e49f0be965'})
        content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text})
        p=r['payload'];nativeid=p.get('id');t={'value':r['timestamp'],'format':'rfc3339','precision':'millisecond','zone_known':True,'unit':None}
        occurrence=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':nativeid,'locator':None if nativeid else {'raw':link(rawkey),'start':a,'end':b,'coordinate':'decoded-jsonl-utf8-bytes'},'native_role':'user','actor_kind':'unknown','process_kind':'main','content':[link(content)],'native_parent_ids':None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]),'event_time':t})
        anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(rawkey),'occurrence':link(occurrence),'coordinate':'decoded-jsonl-utf8-bytes','start':a,'end':b,'parser':'shared-credit-reflection-prefix-v1','role_basis':'native user channel; supplied quotations distinguished from original argument'})
        request={'ref':'CREDIT-REQUEST','occurrence':occurrence,'content':content,'anchors':[anchor],'role':'user','platform':'codex-local','thread':'01a16c8a-f6e1-7580-b378-b6e49f0be965','time':r['timestamp'],'time_format':'rfc3339','native_event_time':t,'text':text,'text_sha256':sha(text.encode()),'capture':{'path':str(native),'bytes':size,'complete_line_bytes':offset,'start':a,'end':b,'raw':rawkey,'sha256':sha(prefix),'captured_at':datetime.now(timezone.utc).isoformat(),'scope':'fixed prefix; only new reflection indexed; no hidden reasoning extracted'}}
        write_json(reqfile,request)
    selected['CREDIT-REQUEST']=request
    write_json(ARCHIVE/'selected-sources.json',selected)
    paras=[p for p in request['text'].split('\n\n') if p.strip()]
    print(json.dumps({'source_entries':len(selected),'request_time':request['time'],'prefix_bytes':request['capture']['bytes'],'paragraphs':[{'n':i,'chars':len(p),'start':p[:75]} for i,p in enumerate(paras)]},ensure_ascii=False))
if __name__=='__main__':prepare()
