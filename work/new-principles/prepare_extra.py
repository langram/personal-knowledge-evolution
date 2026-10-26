import json,hashlib,sys
from pathlib import Path
from datetime import datetime,timezone
W=Path(__file__).resolve().parent;B=W.parents[1]/'outputs/personal-thought-archive';C=B/'contributions/codex';O=C/'new-principles-20261026'
sys.path.insert(0,str(C));from pkst_codec import Store,cid,link,linkset,decode
from export_codex_car import block_object,event_time
S=Store(O);(O/'raw').mkdir(exist_ok=True)
def raw(data):
 k=cid(data,0x55);p=O/'raw'/(k+'.bin')
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
 return k
path=O/'selected-sources.json';sel=json.loads(path.read_text(encoding='utf-8'));R=sel['records']
native=Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
data=native.read_bytes();offset=0;chosen=[];meta=None
for line in data.splitlines(keepends=True):
 x=json.loads(line);p=x.get('payload',{})
 if x.get('type')=='session_meta':meta=p
 if x.get('type')=='response_item' and p.get('role')=='user':
  t=''.join(z.get('text','') for z in p.get('content',[]))
  if t.startswith('19个小时前'):chosen.append(('LATEST-IMPORT',offset,offset+len(line.rstrip(b'\n')),x,t))
  if t.startswith('继续，把 ChatGPT'):chosen.append(('LATEST-WRITING',offset,offset+len(line.rstrip(b'\n')),x,t))
 offset+=len(line)
assert len(chosen)==2
prefix=data[:chosen[-1][2]+1];kraw=raw(prefix)
source=S.put({'schema':'pkst/source@0.1','platform':'codex-local','namespace':'owner-openai-account','native_thread_id':meta['id']})
for ref,start,end,x,t in chosen:
 p=x['payload'];parts=[S.put(block_object(z)) for z in p['content']];nativeid=p.get('id')
 assert len(parts)==1
 occ=S.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':nativeid,'locator':None if nativeid else {'raw':link(kraw),'start':start,'end':end,'coordinate':'decoded-jsonl-utf8-bytes'},'native_role':p['role'],'actor_kind':'unknown','process_kind':'unknown','content':[link(z) for z in parts],'native_parent_ids':None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]),'event_time':event_time(x['timestamp'])})
 er=S.put({'schema':'pkst/extraction-record@0.1','raw':link(kraw),'occurrence':link(occ),'start':start,'end':end,'coordinate':'decoded-jsonl-utf8-bytes','parser':'codex-response-item@0.1.0','role_basis':'native user role, current collection and manuscript request; actor attribution left unknown'})
 R[ref]={'ref':ref,'occurrence':occ,'content':parts[0],'text':t,'role':'user','time':x['timestamp'],'time_format':'rfc3339','platform':'codex-local','thread':meta['id'],'anchors':[er],'source_kind':'native current user instruction','new':True}
libraryraw='bafkreidgldjls7idmuw5acpssxkmf6gk6wf3ebexjivqh57vctvjyejn54';CB=C/'chatgpt';lib=json.loads((CB/'raw'/(libraryraw+'.bin')).read_bytes());lanchors=json.loads((CB/'.private/anchors-v1.json').read_text())['library']
files={
 'ORIGINAL':('新原理_初稿_Gemini.md','mixed or unverified authorship; user-designated earlier manuscript'),
 'META-THEORY':('meta_theory.md','mixed user and AI transcript attachment'),
 'BRAINSTORM':('meta_theory_brainstorm_02.md','mixed user and AI transcript attachment'),
 'REEC':('REEC_meta_theory_stage_v0_3.md','AI stage synthesis; not blanket user adoption'),
 'STRUCTOKEN':('structoken_category_framework_v0.1.md','project synthesis; not native user statement'),
 'HOTPATH-REPORT':('hotpath_project_progress_report_20260518.md','historical static review; runtime not independently confirmed there')}
arts={}
for ref,(name,kind) in files.items():
 pairs=[(i,f) for i,f in enumerate(lib) if f['file_name']==name];assert len(pairs)==1,(ref,pairs)
 i,f=pairs[0];a=next(x for x in lanchors if x['index']==i);assert len(a['candidates'])==1
 k=a['candidates'][0];text=(CB/'raw'/(k+'.bin')).read_bytes().decode('utf-8')
 arts[ref]={'ref':ref,'raw':k,'text':text,'name':name,'source_kind':kind,'writing_time':None,'upload_time':f.get('file_upload_time'),'library_raw':libraryraw,'library_index':i,'file_id':f['file_id'],'thread':f.get('origination_thread_id'),'message':f.get('origination_message_id'),'bytes':len(text.encode('utf-8'))}
for ref,p,kind in [
 ('E002',Path('C:/Users/langr/Dev/civic-neural-commons/reports/E002-REVIEW.md'),'saved research report, synthetic data, read-only capture; no rerun'),
 ('T033',Path('C:/Users/langr/Dev/civic-neural-commons/reports/T033-REVIEW.md'),'saved research report, bounded mathematical comparison, read-only capture; no rerun'),
 ('ARCHIVE',C/'catalog'/sel['baseline']['report'],'prior catalog report; scope limited to pinned collections'),
 ('CONSTRUCTION-INSTRUCTIONS',W.parents[1]/'AGENTS.md','workspace guidance')]:
 if ref=='CONSTRUCTION-INSTRUCTIONS' and not p.is_file():
  # This turn supplied the exact instruction as a message; do not fabricate a native occurrence.
  text='User-supplied instructions in the active turn: Constructed-Code Priority. Public codebases are move records rather than rules; compare common patch-prior, minimal hotpath, and verifier-first candidates. This is an editorial description, not a verbatim quotation.'
  rawbytes=text.encode();origin='active user AGENTS.md instruction, editorial description'
 else:rawbytes=p.read_bytes();text=rawbytes.decode('utf-8');origin=str(p)
 k=raw(rawbytes);arts[ref]={'ref':ref,'raw':k,'text':text,'name':p.name,'source_kind':kind,'writing_time':None,'captured_at':datetime.now(timezone.utc).isoformat(),'origin':origin,'bytes':len(rawbytes)}
sel['artifacts']=arts;sel['native_prefix']={'raw':kraw,'bytes':len(prefix),'end':chosen[-1][2]+1,'cutoff':chosen[-1][3]['timestamp'],'source_path':str(native)}
path.write_text(json.dumps(sel,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'records':len(R),'artifacts':len(arts),'new_events':2,'prefix_bytes':len(prefix)}))
