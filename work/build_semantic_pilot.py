"""A bounded, reviewable integration of the two source versions of this request."""
import json,sqlite3,sys,hashlib,difflib,html
from pathlib import Path
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
codex=base/'contributions/codex';peer=base/'contributions/claude'
sys.path.insert(0,str(codex))
from pkst_codec import Store,decode,encode,cid,link,linkset,links,cid_bytes
pilot=Store(codex/'pilot');now=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
previous_root='bafyreigfiuuqfqqkbouoawujokw7ecduh53ap63otad4mij7t4v7ovf34e'
before_objects={p.stem for p in pilot.objects.glob('*.cbor')}
old_report=codex/'pilot/report.json'
archive_report=codex/'pilot/report-v1.json'
if not archive_report.exists():archive_report.write_bytes(old_report.read_bytes())
sample=json.loads((codex/'.private/pilot-candidates.json').read_text(encoding='utf-8'))[0]
manifest={r['raw_cid']:r for r in [json.loads(l) for l in (codex/'.private/capture-20261024T070147Z-4f83698c.jsonl').read_text(encoding='utf-8').splitlines()]}
codex_content=cid(encode({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':sample['text']}))
claude_content='bafyreiej32suifkvf3xbnmodwb5qvjusx3eyvs2pbizlzpp4jsfoiob5va'
db=sqlite3.connect((codex/'.private/windows-evidence.index.sqlite').as_uri()+'?mode=ro',uri=True)
car=(codex/'.private/windows-evidence.car').open('rb')
def get(key):
    local=pilot.objects/(key+'.cbor')
    cp=peer/'objects'/(key+'.cbor')
    if local.exists():data=local.read_bytes()
    elif cp.exists():data=cp.read_bytes()
    else:
        row=db.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        if not row:raise KeyError(key)
        car.seek(row[0]);data=car.read(row[1])
    assert cid(data)==key
    return decode(data)
events={};ers=[]
for key,offset,size in db.execute("SELECT cid,offset,size FROM blocks WHERE schema='pkst/occurrence@0.1'"):
    car.seek(offset);o=decode(car.read(size))
    if o.get('native_id')==sample['native_id']:events['codex']=(key,o)
for p in (peer/'objects').glob('*.cbor'):
    o=decode(p.read_bytes())
    if o.get('schema')=='pkst/occurrence@0.1' and link(claude_content) in o['content']:
        assert 'claude' not in events;events['claude']=(p.stem,o)
assert len(events)==2
assert link(codex_content) in events['codex'][1]['content']
for key,offset,size in db.execute("SELECT cid,offset,size FROM blocks WHERE schema='pkst/extraction-record@0.1'"):
    car.seek(offset);o=decode(car.read(size))
    if o['occurrence']['$link']==events['codex'][0]:ers.append(key)
for p in (peer/'objects').glob('*.cbor'):
    o=decode(p.read_bytes())
    if o.get('schema')=='pkst/extraction-record@0.1' and o['occurrence']['$link']==events['claude'][0]:ers.append(p.stem)
assert len(ers)==2
texts={name:get(content)['text'] for name,content in [('codex',codex_content),('claude',claude_content)]}
for erkey in ers:
    er=get(erkey);rawkey=er['raw']['$link']
    if er['occurrence']['$link']==events['codex'][0]:
        from compression import zstd
        opener=zstd.open if manifest[rawkey]['source_suffix'].endswith('.zst') else open
        with opener(codex/'raw'/(rawkey+'.bin'),'rb') as f:
            f.seek(er['start']);record=json.loads(f.read(er['end']-er['start']))
        assert record['payload']['content'][0]['text']==texts['codex']
    else:
        with (peer/'raw'/(rawkey+'.bin')).open('rb') as f:
            f.seek(er['start']);record=json.loads(f.read(er['end']-er['start']))
        c=record['message']['content'];actual=c if isinstance(c,str) else ''.join(x['text'] for x in c if x.get('type')=='text')
        assert actual==texts['claude']
evidence=linkset([key for key,o in events.values()]+ers)
actor={'kind':'ai','id':'codex'}
assert all('个人知识发展的时空记录' in t for t in texts.values())
concept=pilot.put({'schema':'pkst/concept@0.1','label':'个人知识发展的时空记录',
    'definition':'逐字保留来源中的术语；Codex 原整理标签“个人知识发展的语义与时间记录”仅作解释。',
    'evidence':evidence,'asserted_by':actor,'lineage':None})
quotes=[
 ('语义关系','按照语义空间的逻辑和因果链条以及从属关系'),
 ('思想时间线','具有想法的变迁，进化继承的迭代的过程时间线'),
 ('统一保存标准','经过讨论达成共识后，按统一的格式进行保存'),
 ('跨 AI 整合','我们还需要对各个AI的讨论内容进行一下整合')]
statements=[];relations=[]
for label,quote in quotes:
    assert all(quote in t for t in texts.values())
    key=pilot.put({'schema':'pkst/statement@0.1','text':quote,'force':'directive',
       'holder':{'kind':'unknown','id':'source-speaker-unverified'},'evidence':evidence,
       'asserted_by':actor,'lineage':None})
    statements.append({'label':label,'cid':key,'quote':quote})
    relations.append(pilot.put({'schema':'pkst/relation@0.1','predicate':'about','from':link(key),'to':link(concept),
       'evidence':evidence,'asserted_by':actor,'basis':'inferred','scope':'This paired request only; semantic classification by Codex'}))
pair=sorted([key for key,o in events.values()],key=cid_bytes)
propagation=pilot.put({'schema':'pkst/relation@0.1','predicate':'propagation-candidate','from':link(pair[0]),'to':link(pair[1]),
    'evidence':evidence,'asserted_by':actor,'basis':'inferred',
    'scope':'Unordered pair sorted by CID; only the name in 我让 X 也来做一份 differs, while earlier Claude/Codex assignments are unchanged. Final newline may be a client transformation, not a user edit. No copy direction, original author or endorsement asserted.'})
outputs=[concept]+[x['cid'] for x in statements]+relations+[propagation]
activity=pilot.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':actor,
    'inputs':evidence,'outputs':linkset(outputs),'implementation':{'method':'bounded manual exact-quote extraction plus difflib comparison','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
    'coverage':{'source_occurrences':2,'statements':4,'status':'R1-R3-corrected-after-Claude-review',
      'selection':'bounded sample, non-exhaustive',
      'recognized_but_not_extracted':['Merkle-DAG format','tree mind-map view','Git-like chronology','GitHub publishing','multi-party responsibility','self-report of copying and multi-AI brainstorming'],
      'limitations':['Directives are requests, not beliefs','Holder remains unknown','No change/revise edge: textual differences do not establish intellectual evolution']}})
protocol='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
snapshot=pilot.put({'schema':'pkst/snapshot@0.1','parents':linkset([previous_root]),'roots':linkset([activity]+ers),
    'coverage':{'scope':'two versions of this archive request','status':'corrected-candidate',
      'selection':'bounded sample, non-exhaustive','event_cutoff':'2026-10-24T06:29:26.223Z',
      'event_cutoff_basis':'latest of the two included source events; not either repository capture completion time',
      'source_event_cutoffs':{name:o['event_time']['value'] for name,(_,o) in events.items()},
      'recorded_cutoff':now,'store_dependencies':['Codex Windows CAR and raw','Claude Windows objects and raw']},'protocol':link(protocol)})
visited=set();stack=[snapshot];raws=set()
while stack:
    key=stack.pop()
    if key in visited:continue
    visited.add(key)
    if cid_bytes(key)[1]==0x55:
        paths=[r/'raw'/(key+'.bin') for r in (codex,peer)];p=next(p for p in paths if p.exists())
        assert cid(p.read_bytes(),0x55)==key;raws.add(key)
    else:stack.extend(links(get(key)))
matcher=difflib.SequenceMatcher(None,texts['claude'],texts['codex'],autojunk=False)
diff=[{'operation':tag,'claude':texts['claude'][i:j],'codex':texts['codex'][k:l]} for tag,i,j,k,l in matcher.get_opcodes() if tag!='equal']
result={'schema':'pkst.semantic-pilot-report@0.1','recorded_at':now,'snapshot':snapshot,'previous_snapshot':previous_root,'status':'R1-R3-corrected-after-Claude-review',
    'review':'contributions/claude/REVIEW-PILOT-1.md','selection':'bounded sample, non-exhaustive',
    'concept':concept,'statements':statements,'propagation_candidate':propagation,
    'sources':{name:{'occurrence':key,'event_time':o['event_time'],'native_role':o['native_role'],'actor_kind':o['actor_kind']} for name,(key,o) in events.items()},
    'similarity':matcher.ratio(),'differences':diff,'new_objects':len({p.stem for p in pilot.objects.glob('*.cbor')}-before_objects),'stored_objects':len(list(pilot.objects.glob('*.cbor'))),'closure_objects_and_raw':len(visited),'raw_anchors_verified':2,
    'interpretation':'Same project request in two AI contexts. Differences are not evidence of a theory revision. No user adoption or original author asserted.'}
(codex/'pilot/report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
private=codex/'pilot/.private';private.mkdir(exist_ok=True)
(private/'paired-texts.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ['snapshot','similarity','differences','new_objects','closure_objects_and_raw','raw_anchors_verified']},ensure_ascii=False))
