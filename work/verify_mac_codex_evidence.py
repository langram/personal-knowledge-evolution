import sys,json,sqlite3,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
from datetime import datetime,timezone
from compression import zstd
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import decode,cid,loads
from index_codex import records
root=base/'contributions/codex/mac'
report=json.loads((root/'.private/mac-evidence.report.json').read_text())
db=sqlite3.connect((root/'.private/mac-evidence.index.sqlite').as_uri()+'?mode=ro',uri=True)
car=(root/'.private/mac-evidence.car').open('rb')
@lru_cache(maxsize=8192)
def obj(key):
 offset,size=db.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
 car.seek(offset);data=car.read(size);assert cid(data)==key;return decode(data)
anchors=defaultdict(dict)
for key, in db.execute("SELECT cid FROM blocks WHERE schema='pkst/extraction-record@0.1'").fetchall():
 er=obj(key);raw=er['raw']['$link'];start=er['start'];assert start not in anchors[raw];anchors[raw][start]=er
manifest=[json.loads(x) for x in (root/'.private/capture-mac-20261024.jsonl').read_text(encoding='utf-8').splitlines()]
verified=Counter();roles=Counter();total=0
for i,row in enumerate(manifest):
 raw=row['raw_cid'];path=root/'raw'/(raw+'.bin');source_id=None;native_source=None
 opener=zstd.open if row['source_suffix'].endswith('.zst') else open
 with opener(path,'rb') as stream:
  for start,end,line,error in records(stream):
   assert error is None
   d=loads(line);p=d.get('payload',{})
   if not isinstance(p,dict):continue
   if d.get('type')=='session_meta':source_id=p.get('id') or p.get('session_id');native_source=p.get('source')
   if d.get('type')!='response_item' or p.get('type')!='message':continue
   er=anchors[raw][start];assert er['end']==end-int(line.endswith(b'\n'))
   event=obj(er['occurrence']['$link']);source=obj(event['source']['$link'])
   assert source['platform']=='codex-local' and source['namespace']=='owner-openai-account'
   assert source['native_thread_id']==str(source_id or 'raw:'+raw)
   native_id=p.get('id') if isinstance(p.get('id'),str) and p.get('id') else None
   assert event['native_id']==native_id and event['native_role']==str(p.get('role','unknown'))
   if native_id is None:
    assert event['locator']=={'raw':{'$link':raw},'start':start,'end':er['end'],'coordinate':'decoded-jsonl-utf8-bytes'}
   else:assert event['locator'] is None
   if isinstance(d.get('timestamp'),str):assert event['event_time']['value']==d['timestamp']
   else:assert event['event_time']['value'] is None
   expected_parent=None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])])
   assert event['native_parent_ids']==expected_parent
   assert event['process_kind']==('sidechain' if isinstance(native_source,dict) and 'subagent' in native_source else 'unknown')
   if event['native_role']=='user':assert event['actor_kind']=='unknown'
   blocks=p.get('content',[]);assert len(blocks)==len(event['content'])
   for original,ref in zip(blocks,event['content']):
    b=obj(ref['$link'])
    if isinstance(original,dict) and original.get('type') in ('input_text','output_text','text') and isinstance(original.get('text'),str):
     assert b=={'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':original['text']}
     verified['native_text_blocks']+=1
    else:
     assert b['schema'] in ('pkst/opaque-block@0.1','pkst/projection@0.1')
     projected=json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
     if b['schema']=='pkst/opaque-block@0.1':assert b['handling']=='raw-only' and b['digest']==hashlib.sha256(projected.encode()).hexdigest()
     else:assert b['text']==projected
     verified['non_text_blocks']+=1
   verified['events']+=1;roles[event['native_role']]+=1;total+=1
 if (i+1)%400==0:print(json.dumps({'files':i+1,'events':total}),flush=True)
assert total==sum(len(v) for v in anchors.values())==62449
assert report['verification']['schemas']['pkst/occurrence@0.1']==total and report['failures']==[]
snapshot=obj(report['root']);assert snapshot['coverage']['host']=='macbook' and snapshot['coverage']['source_files']==936
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'passed','root':report['root'],'source_files':936,
 'verified':dict(verified),'roles':dict(roles),'checks':['all source-selected messages accounted for','source native identity','message native identity or exact fallback','parents','roles and unverified user actor','native event timestamp value','ordered exact native text','non-text digest/projection','byte anchors','Mac host provenance'],
 'limitations':['not every source record type is a message','not semantic truth or authorship verification']}
(base/'reports/mac-codex-evidence-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
