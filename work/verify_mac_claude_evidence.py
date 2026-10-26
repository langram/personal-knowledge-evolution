import json,sys,sqlite3,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from functools import lru_cache
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import decode,cid,loads
from pkst_car import inspect_car
peer=base/'contributions/claude';s=json.loads((peer/'mac-main-conversion-summary-20261024T090824Z.json').read_text())
car_path=base/s['car'];index=base/'contributions/codex/.private/mac-claude-audit-20261024.sqlite'
assert hashlib.sha256(car_path.read_bytes()).hexdigest()==s['car_sha256']
verification=inspect_car(car_path,peer/'raw',index)
db=sqlite3.connect(index.as_uri()+'?mode=ro',uri=True);car=car_path.open('rb')
@lru_cache(maxsize=8192)
def obj(key):
 row=db.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone();assert row is not None
 car.seek(row[0]);data=car.read(row[1]);assert cid(data)==key;return decode(data)
raw_rows=[json.loads(l) for l in (base/'coordination/.private/mac-inbox/main/claude-manifest.jsonl').read_text().splitlines()]
raws={r['cidv1_raw']:(peer/'raw'/(r['cidv1_raw']+'.bin')).read_bytes() for r in raw_rows}
assert len(raws)==51
native={};expected=defaultdict(set)
for r in raw_rows:
 raw=r['cidv1_raw'];data=raws[raw];assert cid(data,0x55)==raw and len(data)==r['bytes_copied']
 pos=0
 for line in data.splitlines(keepends=True):
  assert line.endswith(b'\n')
  end=pos+len(line)-1
  if line.strip():
   rec=loads(line);native[(raw,pos)]=rec
   is_event=(isinstance(rec.get('sessionId'),str) and bool(rec['sessionId'])) if r['source_group']=='claude_history' else rec.get('type') in ('user','assistant','system','attachment') and bool(rec.get('uuid'))
   if is_event:expected[raw].add(pos)
  pos+=len(line)
seen=defaultdict(set);events={};counts=Counter();roles=Counter()
for key, in db.execute("SELECT cid FROM blocks WHERE schema='pkst/extraction-record@0.1'").fetchall():
 er=obj(key);raw=er['raw']['$link'];start=er['start'];end=er['end'];data=raws[raw]
 assert er['coordinate']=='decoded-jsonl-utf8-bytes' and data[end:end+1]==b'\n'
 assert start==0 or data[start-1:start]==b'\n'
 rec=native[(raw,start)];assert loads(data[start:end])==rec
 event=obj(er['occurrence']['$link']);source=obj(event['source']['$link']);events[er['occurrence']['$link']]=event
 assert source['platform']=='claude-code' and source['namespace']=='owner-claude-account'
 history=er['parser']=='claude-code-history-jsonl@0.1-n3'
 sid=rec['sessionId']
 if not history and rec.get('agentId'):sid += '/agent-'+rec['agentId']
 assert source['native_thread_id']==sid
 if history:
  assert event['native_id'] is None and event['native_role']=='prompt-history' and event['actor_kind']==event['process_kind']=='unknown'
  assert event['native_parent_ids'] is None
  assert event['locator']=={'raw':er['raw'],'coordinate':er['coordinate'],'start':start,'end':end}
 else:
  assert event['native_id']==rec['uuid'] and event['native_role']==rec['type'] and event['locator'] is None
  assert event['native_parent_ids']==(None if 'parentUuid' not in rec else [] if rec['parentUuid'] is None else [rec['parentUuid']])
 assert event['actor_kind']!='human'
 ts=rec.get('timestamp')
 if ts is None or isinstance(ts,bool):assert event['event_time']['value'] is None
 elif isinstance(ts,int):assert event['event_time']['value']==str(ts) and event['event_time']['unit']=='ms'
 else:assert event['event_time']['value']==str(ts)
 seen[raw].add(start);counts['anchors']+=1;roles[event['native_role']]+=1
assert dict(seen)==dict(expected) and counts['anchors']==26513
def pointer(rec,path):
 for seg in path.split('/')[1:]:
  seg=seg.replace('~1','/').replace('~0','~');rec=rec[int(seg)] if isinstance(rec,list) else rec[seg]
 return rec
for key, in db.execute("SELECT cid FROM blocks WHERE schema='pkst/block-reference@0.1'").fetchall():
 br=obj(key);event=events[br['occurrence']['$link']];original=pointer(native[(br['raw']['$link'],br['start'])],br['pointer'])
 block=obj(event['content'][br['ordinal']]['$link']);kind=block['schema']
 if kind=='pkst/content@0.1':
  expected_text=original['text'] if isinstance(original,dict) else original
  assert isinstance(expected_text,str) and block['text']==expected_text
  counts['native_text_parts']+=1
 else:
  projected=json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
  if kind=='pkst/opaque-block@0.1':assert block['handling']=='raw-only' and block['digest']==hashlib.sha256(projected.encode()).hexdigest()
  else:assert kind=='pkst/projection@0.1' and block['text']==projected
  counts['non_text_parts']+=1
 counts['block_references']+=1
by_path={r['source_path']:r for r in raw_rows}
for key, in db.execute("SELECT cid FROM blocks WHERE schema='pkst/activity@0.1'").fetchall():
 a=obj(key);c=a['coverage'];r=by_path[c['source_path']]
 assert c['host']=='macbook' and c['source_group']==r['source_group'] and c['mac_mtime_ns']==str(r['mtime_before_ns'])
 assert a['inputs']==[{'$link':r['cidv1_raw']}] and c['bytes']==r['bytes_copied']
 counts['provenance_activities']+=1
result={'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'passed','snapshot':s['snapshot'],'source_files':51,
 'unique_events':len(events),'verified':dict(counts),'roles':dict(roles),'car_verification':verification,
 'limits':['1 dangling native parent and 4 missing pasted contents preserved','raw capture does not prove all prior Mac history survived','not theory truth or user authorship verification']}
(base/'reports/mac-claude-evidence-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result),flush=True)
