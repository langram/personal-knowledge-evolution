import json,sys,sqlite3,hashlib
from pathlib import Path
from datetime import datetime,timezone
W=Path(__file__).resolve().parent
B=W.parents[1]/'outputs/personal-thought-archive'
O=B/'contributions/codex/new-principles-20261026'
P=json.loads((B/'contributions/codex/catalog/current.json').read_text())
D=sqlite3.connect((B/P['database']).as_uri()+'?mode=ro',uri=True)
sys.path.insert(0,str(B/'contributions/codex'))
from pkst_codec import decode,cid,cid_bytes
def obj(k):
 r=D.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
 if not r:raise KeyError(k)
 with (B/r[0]).open('rb') as f:f.seek(r[1]);data=f.read(r[2])
 assert cid(data,cid_bytes(k)[1])==k
 return decode(data)
selected={48861,48731,49135,49196,49083,54910,55042,55647,54886,54800,55084,55370,55469,55180,54803,48623,54629,54733,54949,54477,55207,55111,49500,48849,49033,49383,48751,48527,48523,48641,48755,48840,48769,34498,54225,54228,54235,54935,49188,49228,49067,49560,36081,49423,49234}
records={}
for i,line in enumerate((W/'retrieval.jsonl').open(encoding='utf-8')):
 if i in selected:
  r=json.loads(line);r['ref']='R'+str(i);r['row']=i
  r['anchors']=[a[0] for a in D.execute('SELECT extraction_record FROM anchors WHERE occurrence=?',(r['occurrence'],))]
  for a in r['anchors']:obj(a)
  r['source_kind']='native-user-channel; authorship of embedded quotations not inferred'
  r['editorial_selection']=True
  records[r['ref']]=r
# Reuse exact prior selected events, including the network-AGI clarification.
seed=json.loads((B/'contributions/codex/civilization-seed-20261025/capture.json').read_text(encoding='utf-8'))
for r in seed['recent']+seed['history']:
 if r['ref'] not in ['R10','R14','R16','R18','H1','H2','H3','H4','H5']:continue
 o=obj(r['occurrence']);s=obj(o['source']['$link'])
 for n,c in enumerate(o['content']):
  x=obj(c['$link'])
  if x['schema']!='pkst/content@0.1':continue
  key='SEED-'+r['ref']+'-'+str(n)
  records[key]={'ref':key,'occurrence':r['occurrence'],'content':c['$link'],'text':x['text'],'role':o['native_role'],'time':o['event_time']['value'],'time_format':o['event_time']['format'],'platform':s['platform'],'thread':s['native_thread_id'],'anchors':r['anchors'],'source_kind':'native-user-channel; preserve embedded authorship boundaries'}
for r in json.loads((W/'meta-theory-user-messages.json').read_text(encoding='utf-8')):
 k,role,t,c,txt=r
 if len(txt)>4000:continue
 o=obj(k);s=obj(o['source']['$link']);ref='META-'+k[-6:]
 records[ref]={'ref':ref,'occurrence':k,'content':c,'text':txt,'role':role,'time':t,'time_format':o['event_time']['format'],'platform':s['platform'],'thread':s['native_thread_id'],'anchors':[a[0] for a in D.execute('SELECT extraction_record FROM anchors WHERE occurrence=?',(k,))],'source_kind':'native-user-channel; preserve embedded authorship boundaries'}
k='bafyreifwgt6q4jjb3nopwoger3e4baglyfk47zpceggvyo4xhix5d44csu';o=obj(k);c=o['content'][0]['$link'];s=obj(o['source']['$link'])
records['PREFACE-2024']={'ref':'PREFACE-2024','occurrence':k,'content':c,'text':obj(c)['text'],'role':o['native_role'],'time':o['event_time']['value'],'time_format':o['event_time']['format'],'platform':s['platform'],'thread':s['native_thread_id'],'anchors':[a[0] for a in D.execute('SELECT extraction_record FROM anchors WHERE occurrence=?',(k,))],'source_kind':'native early preface; user-channel'}
out={'baseline':P,'recorded_at':datetime.now(timezone.utc).isoformat(),'records':records}
(O/'selected-sources.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'selected_parts':len(records),'platforms':sorted({r['platform'] for r in records.values()})}))
