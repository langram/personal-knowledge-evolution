"""Append the reviewed manuscript and bounded semantic interpretation to PKST."""
import argparse,hashlib,json,sqlite3,time
from collections import defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
from pkst_codec import Store,cid,cid_bytes,decode,encode,links,link,linkset,check_sets
B=Path(__file__).resolve().parents[2];C=B/'contributions/codex';O=C/'new-principles-20261026';D=B/'dossiers/2026-10-26-new-principles'
RUN='20261026-new-principles-v1';COL='new-principles-20261026';PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
ACTOR={'kind':'ai','id':'codex'};NS={'np':'urn:pkst:editorial:new-principles:1'}
def main():
 global RUN
 parser=argparse.ArgumentParser();parser.add_argument('--run',default=RUN);args=parser.parse_args();RUN=args.run
 if not RUN.replace('-','').isalnum():raise ValueError('Invalid run name')
 started=time.monotonic();now=datetime.now(timezone.utc).isoformat()
 selection=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'));plan=json.loads((O/'semantic-plan.json').read_text(encoding='utf-8'));man=json.loads((O/'manuscript-manifest.json').read_text(encoding='utf-8'))
 pointer=json.loads((C/'catalog/current.json').read_text());assert pointer==selection['baseline'],'Catalog changed; do not overwrite'
 base=json.loads((C/'catalog'/pointer['report']).read_text());dest=C/'catalog/.private'/RUN;dest.mkdir(exist_ok=False)
 old=sqlite3.connect((B/pointer['database']).as_uri()+'?mode=ro',uri=True);db=sqlite3.connect(dest/'catalog.sqlite');old.backup(db);old.close()
 store=Store(O);catalog=Store(C/'catalog');verified=set();records=selection['records'];artifacts=selection['artifacts'];roots=[]
 def raw(data):
  k=cid(data,0x55);p=O/'raw'/(k+'.bin')
  if p.exists():assert p.read_bytes()==data
  else:p.write_bytes(data)
  return k
 def read(k):
  row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
  if row:
   with (B/row[0]).open('rb') as f:f.seek(row[1]);data=f.read(row[2])
  else:
   israw=cid_bytes(k)[1]==0x55;folder,ext=('raw','.bin') if israw else ('objects','.cbor')
   p=next((r/folder/(k+ext) for r in [O,C/'catalog'] if (r/folder/(k+ext)).is_file()),None)
   if p is None:raise FileNotFoundError(k)
   data=p.read_bytes();row=(str(p.relative_to(B)),0,len(data))
  assert cid(data,cid_bytes(k)[1])==k,k;verified.add(k)
  obj=None if cid_bytes(k)[1]==0x55 else decode(data)
  if obj is not None:check_sets(obj);assert encode(obj)==data
  return obj,row,data
 def get(k):return read(k)[0]
 def load(k):
  if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():return
  obj,row,data=read(k);schema='raw' if obj is None else obj['schema'];db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(k,schema,*row))
  if obj is None:return
  active=set(links({n:v for n,v in obj.items() if n!='parents'})) if schema=='pkst/snapshot@0.1' else set(links(obj))
  db.executemany('INSERT INTO edges VALUES(?,?,?)',[(k,q,int(q not in active)) for q in set(links(obj))])
  if schema=='pkst/source@0.1':db.execute('INSERT INTO sources VALUES(?,?,?,?)',(k,obj['platform'],obj['namespace'],obj['native_thread_id']))
  elif schema=='pkst/content@0.1':db.execute('INSERT INTO content VALUES(?,?)',(k,obj['text']))
  elif schema=='pkst/occurrence@0.1':
   t=obj['event_time'];db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(k,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
   db.executemany('INSERT INTO parts VALUES(?,?,?)',[(k,i,p['$link']) for i,p in enumerate(obj['content'])])
  elif schema=='pkst/extraction-record@0.1':db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],k,obj['raw']['$link'],json.dumps({n:obj[n] for n in ['coordinate','start','end','pointer','parser'] if n in obj},ensure_ascii=False)))
 evidence={};file_sources={}
 for ref,r in records.items():
  evidence[ref]=[r['occurrence']]+r['anchors'];roots.extend(evidence[ref])
 for ref,r in artifacts.items():
  fe=store.put({'schema':'np/file-evidence@1','namespaces':NS,'ref':ref,'raw':link(r['raw']),'source_kind':r['source_kind'],'writing_time':None,'upload_time':r.get('upload_time'),'capture_time':r.get('captured_at'),'library_raw':link(r['library_raw']) if r.get('library_raw') else None,'library_index':r.get('library_index'),'origin':r.get('origin') or r['name']})
  evidence[ref]=[fe];file_sources[ref]=fe;roots.append(fe)
 files=[]
 for p in sorted(D.iterdir()):
  if not p.is_file() or p.name.startswith('09-'):continue
  data=p.read_bytes();k=raw(data);files.append({'path':str(p.relative_to(B)),'raw':link(k),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'authorship':'Codex editorial artifact or exact source projection; see per-file/source manifest'})
 mainraw=next(x['raw']['$link'] for x in files if x['path'].endswith('/01-new-principles.md') or x['path'].endswith('\\01-new-principles.md'))
 document=store.put({'schema':'np/document@1','namespaces':NS,'title':'新原理：从数学与科学的共同结构，到人类社会的新组织机制','raw':link(mainraw),'edition':'2026-10-26 editorial v1','authorship':'Codex first-person synthesis based on owner materials; not author-adopted final'});roots.append(document)
 quotes=[]
 for q in man['quotations']:
  ref=q['source_ref'];r=records.get(ref) or artifacts[ref];t=r['text'];assert t[q['source_start']:q['source_end']]==q['text']
  coord={'source_ref':ref,'start':q['source_start'],'end':q['source_end'],'coordinate':'unicode-scalar-half-open'}
  coord['content' if 'content' in r else 'raw']=link(r.get('content') or r['raw'])
  k=store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':q['text'],'force':'quote','holder':{'kind':'unknown','id':'source-authorship-not-inferred'},'evidence':linkset(evidence[ref]),'asserted_by':ACTOR,'lineage':None,'np:quotation':coord,'np:document_span':{'document':link(document),'start':q['document_start'],'end':q['document_end'],'coordinate':'unicode-scalar-half-open'}})
  quotes.append({**q,'statement':k});roots.append(k)
 concepts={}
 for n in plan['nodes']:
  ev=[k for ref in n['sources'] for k in evidence[ref]]
  concepts[n['id']]=store.put({'schema':'pkst/concept@0.1','namespaces':NS,'label':n['label'],'definition':n['definition'],'evidence':linkset(ev),'asserted_by':ACTOR,'lineage':None,'np:chapters':n['chapters'],'np:source_refs':n['sources'],'np:status':'editorial interpretation; user adoption not asserted'})
 roots.extend(concepts.values());relkeys=[]
 nmap={n['id']:n for n in plan['nodes']}
 for r in plan['relations']:
  refs=list(dict.fromkeys(nmap[r['from']]['sources']+nmap[r['to']]['sources']));pred={'contrasts-with':'np:in-tension-with','constrains':'np:constrains'}.get(r['predicate'],r['predicate'])
  k=store.put({'schema':'pkst/relation@0.1','namespaces':NS,'predicate':pred,'from':link(concepts[r['from']]),'to':link(concepts[r['to']]),'evidence':linkset([k for ref in refs for k in evidence[ref]]),'asserted_by':ACTOR,'basis':'inferred','scope':r['scope']+'；编辑关系，不代表因果效应已证实或用户采纳。'})
  relkeys.append(k);roots.append(k)
 changes=[]
 for p in plan['prior_concept_map']:
  k=store.put({'schema':'pkst/change@0.1','operation':'editorial-consolidate','from_versions':linkset([p['cid']]),'to_versions':linkset([concepts[p['to']]]),'evidence':linkset(evidence['LATEST-WRITING']),'asserted_by':ACTOR,'basis':'inferred','reason':'本轮章节主题归类，保留原概念和原话；不是用户思想撤回、合并采纳或物理身份等价。'})
  roots.append(k);changes.append(k)
 roots.append(store.put({'schema':'pkst/change@0.1','operation':'editorial-consolidate','from_versions':linkset([file_sources['ORIGINAL']]),'to_versions':linkset([document]),'evidence':linkset(evidence['LATEST-WRITING']),'asserted_by':ACTOR,'basis':'explicit','reason':'用户明确要求按旧稿结构重写扩展；具体技术校订为 Codex 编辑，未经用户逐句审定。'}))
 timeline=[]
 for t in plan['timeline']:
  r=records[t['source']];o=get(r['occurrence'])
  k=store.put({'schema':'np/evolution-entry@1','namespaces':NS,'source_ref':t['source'],'occurrence':link(r['occurrence']),'event_time':o['event_time'],'display_utc':t['display_utc'],'description':t['event'],'interpretation_boundary':t['boundary'],'asserted_by':ACTOR})
  timeline.append(k);roots.append(k)
 impl=raw(Path(__file__).read_bytes());profile=raw((O/'PROFILE.md').read_bytes());selectionraw=raw((O/'selected-sources.json').read_bytes());planraw=raw((O/'semantic-plan.json').read_bytes());manraw=raw((O/'manuscript-manifest.json').read_bytes())
 activity=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset([selectionraw,planraw,profile,manraw]),'outputs':linkset(roots+[x['raw']['$link'] for x in files]),'implementation':link(impl),'coverage':{'scope':plan['coverage'],'selected_text_parts':len(records),'artifact_sources':len(artifacts),'files':files,'review':'Codex source review and editorial synthesis; no new Claude or author acceptance','privacy':'local-only'}})
 dossier=store.put({'schema':'pkst/snapshot@0.1','parents':[],'roots':linkset([activity]),'coverage':{'recorded_cutoff':now,'event_cutoff':selection['native_prefix']['cutoff'],'scope':'bounded major-theory dossier, all prior 21 concepts mapped; not exhaustive per-event semantic extraction','not_done':['publication','author adoption','new experiments or service deployment']},'protocol':link(PROTOCOL)})
 members=set();stack=[dossier]
 while stack:
  k=stack.pop()
  if k in members:continue
  members.add(k);load(k);stack.extend(x[0] for x in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(k,)))
 for k in members:read(k)
 db.executemany('INSERT INTO membership VALUES(?,?)',[(COL,k) for k in members])
 count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0];assert count==base['unique_current_events']+2
 pinned=base['pinned_sources']+[{'collection':COL,'root':dossier,'report':str((O/'report.json').relative_to(B))}]
 integr=catalog.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset([p['root'] for p in pinned]),'outputs':[],'implementation':link(impl),'coverage':{'scope':'prior collections unchanged plus new manuscript dossier','baseline_snapshot':pointer['snapshot'],'current_events':count,'verification':'dossier closure bytes and full reference graph; baseline byte verification reused'}})
 snapshot=catalog.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integr]),'protocol':link(PROTOCOL),'coverage':{'recorded_cutoff':now,'local_only':True,'scope':'pinned corpus plus major-theory manuscript v1','pending':['author manuscript review','exhaustive semantic extraction beyond selected major themes','publication or service deployment']}})
 stack=[snapshot]
 while stack:
  k=stack.pop()
  if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():continue
  load(k);stack.extend(x[0] for x in db.execute('SELECT dst FROM edges WHERE src=?',(k,)))
 assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
 indegree={k:0 for k, in db.execute('SELECT cid FROM blocks')};children=defaultdict(list)
 for a,b in db.execute('SELECT DISTINCT src,dst FROM edges'):children[a].append(b);indegree[b]+=1
 queue=deque(k for k,v in indegree.items() if not v);visited=0
 while queue:
  a=queue.popleft();visited+=1
  for b in children[a]:
   indegree[b]-=1
   if not indegree[b]:queue.append(b)
 assert visited==len(indegree),'CID reference cycle'
 assert db.execute('SELECT count(*) FROM current_occurrences o WHERE NOT EXISTS(SELECT 1 FROM anchors a WHERE a.occurrence=o.cid)').fetchone()[0]==0
 db.commit();assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',(COL,)))
 report={'schema':'pkst.new-principles-report@1','recorded_at':now,'snapshot':dossier,'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'source_parts':len(records),'unique_selected_occurrences':len({r['occurrence'] for r in records.values()}),'new_native_events':2,'verbatim_quotes':len(quotes),'concepts':concepts,'relations':relkeys,'prior_concept_editorial_changes':changes,'timeline_entries':timeline,'document':document,'file_evidence':file_sources,'quotes':quotes,'files':files,'closure_blocks':len(members),'closure_counts':counts,'freshly_byte_verified_blocks':len(verified),'full_reference_graph_nodes':visited,'current_events':count,'elapsed_seconds':round(time.monotonic()-started,3),'status':'staged; requires source and manuscript verification'}
 (O/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');pinned[-1]['report_sha256']=hashlib.sha256((O/'report.json').read_bytes()).hexdigest()
 catalogreport={**base,'schema':'pkst.federated-catalog-report@0.1','run':RUN,'recorded_at':now,'snapshot':snapshot,'pinned_sources':pinned,'database':str((dest/'catalog.sqlite').relative_to(B)),'unique_current_events':count,'current_events_with_anchors':count,'current_counts_by_collection':{**base['current_counts_by_collection'],COL:counts},'all_catalog_blocks_including_history_and_federation':visited,'verification_scope':'New dossier closure; baseline receipts reused; full references and DAG checked. Source and span verification pending.','baseline_verification_report':pointer['report'],'freshly_byte_verified_blocks':len(verified),'candidate_scan_scope':'prior exact-copy candidate groups retained; not rescanned in this editorial addition','status':'staged'}
 (C/'catalog'/('report-'+RUN+'.json')).write_text(json.dumps(catalogreport,ensure_ascii=False,indent=2),encoding='utf-8')
 (O/'staged-pointer.json').write_text(json.dumps({'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catalogreport['database']},indent=2),encoding='utf-8')
 print(json.dumps({k:report[k] for k in ['snapshot','federated_snapshot','new_native_events','verbatim_quotes','closure_blocks','full_reference_graph_nodes','current_events','elapsed_seconds','status']},ensure_ascii=False))
if __name__=='__main__':main()
