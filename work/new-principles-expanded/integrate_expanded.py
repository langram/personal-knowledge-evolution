"""Stage an immutable expanded edition; activation is a separate verification."""
import hashlib,json,sqlite3,sys,time
from datetime import datetime,timezone
from collections import defaultdict,deque
from pathlib import Path
from sources import BASE,WORK,ROOT
sys.path.insert(0,str(BASE/'contributions/codex'))
from pkst_codec import Store,cid,cid_bytes,encode,decode,check_sets,link,linkset,links
C=BASE/'contributions/codex';O=C/'new-principles-expanded-20261026';D=BASE/'dossiers/2026-10-26-new-principles-expanded'
RUN='20261026-new-principles-expanded-v1';COL='new-principles-expanded-20261026'
NS={'np2':'urn:pkst:editorial:new-principles-expanded:1'};ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
started=time.monotonic();now=datetime.now(timezone.utc).isoformat()
baseline=json.loads((O/'baseline.json').read_text());pointer=baseline['pointer']
assert json.loads((C/'catalog/current.json').read_text())==pointer
check=json.loads((O/'source-verification.json').read_text());assert check['status']=='pass'
selected=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'));man=json.loads((D/'source-manifest.json').read_text(encoding='utf-8'));state=json.loads((D/'edition-state.json').read_text(encoding='utf-8'))
assert hashlib.sha256((D/'01-manuscript.md').read_bytes()).hexdigest()==check['manuscript_sha256']==state['manuscript_sha256']
oldreport=json.loads((C/'new-principles-20261026/report.json').read_text());mapping=json.loads((O/'chapter-concept-map.json').read_text());base=json.loads((C/'catalog'/pointer['report']).read_text())
dest=C/'catalog/.private'/RUN;dest.mkdir(exist_ok=False)
old=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True);db=sqlite3.connect(dest/'catalog.sqlite');old.backup(db);old.close()
store=Store(O);cat=Store(C/'catalog');verified=set();newblocks=[]
def raw(data):
 k=cid(data,0x55);p=O/'raw'/(k+'.bin')
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
 return k
def read(k):
 row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
 if row:
  with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
 else:
  folder,ext=('raw','.bin') if cid_bytes(k)[1]==0x55 else ('objects','.cbor')
  p=next((root/folder/(k+ext) for root in [O,C/'catalog'] if (root/folder/(k+ext)).is_file()),None);assert p is not None,k
  b=p.read_bytes();row=(str(p.relative_to(BASE)),0,len(b))
 assert cid(b,cid_bytes(k)[1])==k;verified.add(k)
 obj=None if cid_bytes(k)[1]==0x55 else decode(b)
 if obj is not None:check_sets(obj);assert encode(obj)==b
 return obj,row,b
def load(k):
 if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():return
 obj,row,b=read(k);newblocks.append(k);schema='raw' if obj is None else obj['schema'];db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(k,schema,*row))
 if obj is None:return
 active=set(links({n:v for n,v in obj.items() if n!='parents'})) if schema=='pkst/snapshot@0.1' else set(links(obj))
 db.executemany('INSERT INTO edges VALUES(?,?,?)',[(k,q,int(q not in active)) for q in set(links(obj))])
 if schema=='pkst/source@0.1':db.execute('INSERT INTO sources VALUES(?,?,?,?)',(k,obj['platform'],obj['namespace'],obj['native_thread_id']))
 elif schema=='pkst/content@0.1':db.execute('INSERT INTO content VALUES(?,?)',(k,obj['text']))
 elif schema=='pkst/occurrence@0.1':
  t=obj['event_time'];db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(k,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
  db.executemany('INSERT INTO parts VALUES(?,?,?)',[(k,i,p['$link']) for i,p in enumerate(obj['content'])])
 elif schema=='pkst/extraction-record@0.1':db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],k,obj['raw']['$link'],json.dumps({n:obj[n] for n in ['coordinate','start','end','pointer','parser'] if n in obj},ensure_ascii=False)))

files=[];fileraw={}
for p in sorted(D.rglob('*')):
 if not p.is_file() or p.name.startswith('09-'):continue
 b=p.read_bytes();k=raw(b);fileraw[str(p.relative_to(D)).replace('\\','/')]=k
 files.append({'path':str(p.relative_to(BASE)),'raw':link(k),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
document=store.put({'schema':'np2/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造','raw':link(fileraw['01-manuscript.md']),'edition':'2026-10-26 expanded editorial 1','authorship':'source-led editorial draft, exact/adapted/additional passages distinguished; author acceptance not asserted','previous':link(baseline['old_document'])})
roots=[document];sourcenodes={}
for ref,r in selected.items():
 evidence=[r['occurrence']]+r['anchors'] if r.get('occurrence') else [r['raw']]
 key=store.put({'schema':'np2/source@1','namespaces':NS,'ref':ref,'kind':'native-message' if r.get('occurrence') else 'artifact','target':link(r.get('content') or r['raw']),'occurrence':link(r['occurrence']) if r.get('occurrence') else None,'evidence':linkset(evidence),'event_time':r.get('native_event_time') or ({'value':r['time'],'format':r['time_format']} if r.get('time') else {'writing_time':None,'upload_time':r.get('upload_time'),'observed_at':r.get('captured_at')}),'source_kind':r.get('source_kind','native channel; embedded authorship separately assessed'),'library_raw':link(r['library_raw']) if r.get('library_raw') else None})
 sourcenodes[ref]=key;roots.append(key)

passages=[];chapters={};quotes=[]
for ch in man['chapters']:
 key=ch['chapter'];pcs=[]
 for i,x in enumerate(ch['items']):
  quote=None
  if x.get('ref'):
   ref=x['ref'];r=selected[ref];a,b=x['source_span'];text=r['text'][a:b]
   quote=store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':text,'force':'quote','holder':{'kind':'unknown','id':'source-authorship-not-inferred'},'evidence':linkset([sourcenodes[ref]]),'asserted_by':ACTOR,'lineage':None,'np2:source_span':{'source':link(sourcenodes[ref]),'start':a,'end':b,'coordinate':'unicode-scalar-half-open'}});quotes.append(quote)
  p=store.put({'schema':'np2/passage@1','namespaces':NS,'document':link(document),'chapter':key,'ordinal':i,'kind':x['kind'],'text':x['text'],'document_span':x['document_span'],'chapter_span':x['chapter_span'],'quotation':link(quote) if quote else None,'source':link(sourcenodes[x['ref']]) if x.get('ref') else None,'source_span':x.get('source_span'),'source_sha256':x.get('source_sha256'),'edits':x.get('edits',[]),'author_assessment':x.get('author_assessment'),'editorial_reason':x.get('reason')})
  pcs.append(link(p));passages.append(p)
 review=state['chapters'][int(key)]['review']
 chapters[key]=store.put({'schema':'np2/chapter@1','namespaces':NS,'document':link(document),'key':key,'title':state['chapters'][int(key)]['title'],'raw':link(fileraw[f'chapters/{key}.md']),'passages':pcs,'review':review});roots.append(chapters[key])
topiclinks=[]
for concept,keys in mapping.items():
 for key in keys:
  k=store.put({'schema':'np2/chapter-topic@1','namespaces':NS,'chapter':link(chapters[key]),'concept':link(oldreport['concepts'][concept]),'asserted_by':ACTOR,'basis':'inferred','scope':'editorial reading map; no automatic adoption or truth propagation from older concept to every new passage'});topiclinks.append(k);roots.append(k)
change=store.put({'schema':'pkst/change@0.1','operation':'extend','from_versions':linkset([baseline['old_document']]),'to_versions':linkset([document]),'evidence':linkset([sourcenodes['AUTHOR-FEEDBACK']]),'asserted_by':ACTOR,'basis':'explicit','reason':'用户四点反馈要求全文扩充、原话优先、补足论证、独立成篇并逐章完善。记录编辑版本扩充，不宣称用户逐句采纳技术校订。'});roots.append(change)
implementation=[]
for p in sorted(WORK.glob('*.py')):
 b=p.read_bytes();implementation.append({'path':str(p.relative_to(ROOT)),'raw':link(raw(b)),'sha256':hashlib.sha256(b).hexdigest()})
inputs=[raw((O/name).read_bytes()) for name in ['PROFILE.md','baseline.json','selected-sources.json','semantic-plan.json','chapter-concept-map.json','source-verification.json','feedback-capture.json']]
activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset(roots+[x['raw']['$link'] for x in files]+[x['raw']['$link'] for x in implementation]),'implementation':link(raw(Path(__file__).read_bytes())),'coverage':{'scope':'expanded 24-part manuscript; selected source passages and historical timeline; not exhaustive corpus semantics','source_entries':len(selected),'new_native_events':1,'authorship':'Codex editorial judgments; owner adoption not asserted','privacy':'local-only','files':files,'implementation_files':implementation}})
dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['old_dossier_root']]),'roots':linkset([activity]),'coverage':{'recorded_cutoff':now,'scope':'source-led expanded edition and four-point revision request','pending':['author review','exhaustive per-event semantic extraction'],'not_performed':['publication','new research experiments','service deployment']},'protocol':link(PROTOCOL)})
members=set();stack=[dossier]
while stack:
 k=stack.pop()
 if k in members:continue
 members.add(k);load(k);stack.extend(x[0] for x in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(k,)))
for k in members:read(k)
db.executemany('INSERT INTO membership VALUES(?,?)',[(COL,k) for k in members])
count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0];assert count==base['unique_current_events']+1
pinned=base['pinned_sources']+[{'collection':COL,'root':dossier,'report':str((O/'report.json').relative_to(BASE))}]
integration=cat.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset([p['root'] for p in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),'coverage':{'scope':'previous source collections preserved; expanded edition appended','baseline_snapshot':pointer['snapshot'],'current_events':count}})
snapshot=cat.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integration]),'coverage':{'recorded_cutoff':now,'scope':'federated corpus plus expanded editorial edition','local_only':True,'pending':['owner manuscript review','exhaustive corpus semantic interpretation']},'protocol':link(PROTOCOL)})
stack=[snapshot]
while stack:
 k=stack.pop()
 if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():continue
 load(k);stack.extend(x[0] for x in db.execute('SELECT dst FROM edges WHERE src=?',(k,)))
assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
indegree={k:0 for k, in db.execute('SELECT cid FROM blocks')};children=defaultdict(list)
for a,b in db.execute('SELECT DISTINCT src,dst FROM edges'):children[a].append(b);indegree[b]+=1
q=deque(k for k,v in indegree.items() if not v);visited=0
while q:
 a=q.popleft();visited+=1
 for b in children[a]:
  indegree[b]-=1
  if not indegree[b]:q.append(b)
assert visited==len(indegree),'reference cycle'
assert db.execute('SELECT count(*) FROM current_occurrences o WHERE NOT EXISTS(SELECT 1 FROM anchors a WHERE a.occurrence=o.cid)').fetchone()[0]==0
db.commit();assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',(COL,)))
report={'schema':'np2.archive-report@1','status':'staged','recorded_at':now,'snapshot':dossier,'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'old_dossier_root':baseline['old_dossier_root'],'document':document,'source_nodes':sourcenodes,'chapters':chapters,'passages':passages,'quotes':quotes,'topic_links':topiclinks,'change':change,'activity':activity,'files':files,'source_verification_sha256':hashlib.sha256((O/'source-verification.json').read_bytes()).hexdigest(),'new_native_events':1,'current_events':count,'closure_blocks':len(members),'closure_counts':counts,'new_catalog_blocks':newblocks,'freshly_byte_verified_blocks':len(verified),'full_reference_graph_nodes':visited,'elapsed_seconds':round(time.monotonic()-started,3)}
(O/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');pinned[-1]['report_sha256']=hashlib.sha256((O/'report.json').read_bytes()).hexdigest()
catreport={**base,'run':RUN,'recorded_at':now,'snapshot':snapshot,'pinned_sources':pinned,'database':str((dest/'catalog.sqlite').relative_to(BASE)),'unique_current_events':count,'current_events_with_anchors':count,'current_counts_by_collection':{**base['current_counts_by_collection'],COL:counts},'all_catalog_blocks_including_history_and_federation':visited,'freshly_byte_verified_blocks':len(verified),'verification_scope':'Selected native source reparsing and editorial replay passed; new closure bytes and full reference DAG checked; archive projection activation pending','baseline_verification_report':pointer['report'],'status':'staged'}
(C/'catalog'/f'report-{RUN}.json').write_text(json.dumps(catreport,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'staged-pointer.json').write_text(json.dumps({'report':f'report-{RUN}.json','snapshot':snapshot,'database':catreport['database']},indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['snapshot','federated_snapshot','current_events','closure_blocks','freshly_byte_verified_blocks','full_reference_graph_nodes','elapsed_seconds','status']}))
