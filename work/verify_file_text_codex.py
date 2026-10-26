import json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import cid,decode,links
from pkst_car import inspect_car
peer=base/'contributions/claude'
summary=json.loads((peer/'file-text-conversion-summary-20261024T085850Z.json').read_text())
rows=[json.loads(s) for s in (peer/'raw/_mac-supplement-capture-20261024T083850Z.jsonl').read_text(encoding='utf-8').splitlines()]
selected=[r for r in rows if r.get('category')=='claude-code-project-memory']
assert len(selected)==16
print(json.dumps({'manifest_keys':list(selected[0])}),flush=True)
def obj(key):
 data=(peer/'objects'/(key+'.cbor')).read_bytes();assert cid(data)==key;return decode(data)
root=obj(summary['snapshot']);assert root['parents']==[{'$link':summary['parent']}]
stack=list(links(root['roots']));seen=set();objects={}
while stack:
 key=stack.pop()
 if key in seen:continue
 seen.add(key)
 if not (peer/'objects'/(key+'.cbor')).exists():continue
 o=obj(key);objects[key]=o;stack.extend(links(o))
events={k:v for k,v in objects.items() if v.get('schema')=='pkst/occurrence@0.1'}
assert len(events)==16
ers={o['occurrence']['$link']:o for o in objects.values() if o.get('schema')=='pkst/extraction-record@0.1'}
actual=set()
for key,event in events.items():
 er=ers[key];loc=event['locator'];raw=loc['raw']['$link'];data=(peer/'raw'/(raw+'.bin')).read_bytes()
 assert cid(data,0x55)==raw
 assert loc=={'raw':{'$link':raw},'coordinate':'file-bytes','start':0,'end':len(data)}
 assert er['coordinate']=='file-bytes' and er['raw']==loc['raw'] and er['start']==0 and er['end']==len(data)
 assert event['event_time']=={'value':None,'format':'unknown','precision':'unknown','zone_known':False,'unit':None}
 assert event['native_id'] is None and event['native_parent_ids'] is None
 assert event['native_role']=='derived-memory:claude-code' and event['actor_kind']==event['process_kind']=='unknown'
 source=obj(event['source']['$link'])
 assert source=={'schema':'pkst/source@0.1','platform':'claude-code-memory','namespace':'owner-claude-account','native_thread_id':'raw:'+raw}
 assert len(event['content'])==1
 content=obj(event['content'][0]['$link']);assert content['schema']=='pkst/content@0.1' and content['text']==data.decode('utf-8','strict')
 actual.add(raw)
expected={r['cid'] for r in selected};assert actual==expected
car=base/summary['car'];assert hashlib.sha256(car.read_bytes()).hexdigest()==summary['car_sha256']
verified=inspect_car(car,peer/'raw');assert verified['blocks']==520 and verified['external_raw_verified']==329
rules=peer/'FILE-TEXT-0.1.md';assert cid(rules.read_bytes(),0x55)==summary['rules_raw_cid']
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'passed','snapshot':summary['snapshot'],
 'files':16,'derived_memory_occurrences':16,'conversation_messages':0,'all_native_text_and_byte_anchors_verified':True,
 'all_event_times_unknown':True,'all_actor_kinds_unknown':True,'raw_set_matches_supplement_manifest':True,'car':verified}
(base/'reports/file-text-independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
