"""Append this chapter to a new catalog view. Never activate before replay."""
import json, sqlite3, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from prepare import ROOT, BASE, WORK, OUT, ARCHIVE, C, write_json, sha, raw
from pkst_codec import Store, cid, cid_bytes, encode, decode, check_sets, link, linkset, links

RUN='20261026-mathematics-contribution-v1'
COL='mathematics-contribution-20261026'
NS={'math':'urn:pkst:editorial:mathematics-contribution:1'}
ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'

def stage():
    started=time.monotonic();now=datetime.now(timezone.utc).isoformat()
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes());pointer=baseline['pointer']
    assert json.loads((C/'catalog/current.json').read_bytes())==pointer
    checks=json.loads((ARCHIVE/'text-verification.json').read_bytes());assert checks['status']=='pass'
    assert sha((OUT/'01-chapter.md').read_bytes())==checks['chapter_sha256']
    assert sha((OUT/'02-new-principles.md').read_bytes())==checks['combined_sha256']
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    plan=json.loads((ARCHIVE/'semantic-plan.json').read_bytes())
    previous_concepts=json.loads((C/'new-principles-20261026/report.json').read_bytes())['concepts']
    base=json.loads((C/'catalog'/pointer['report']).read_bytes())
    destination=C/'catalog/.private'/RUN;destination.mkdir(exist_ok=False)
    old=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    db=sqlite3.connect(destination/'catalog.sqlite');old.backup(db);old.close()
    store=Store(ARCHIVE);cat=Store(C/'catalog');verified=set();newblocks=[]
    def read(key):
        row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        if row:
            with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
        else:
            folder,ext=('raw','.bin') if cid_bytes(key)[1]==0x55 else ('objects','.cbor')
            path=next((root/folder/(key+ext) for root in (ARCHIVE,C/'catalog') if (root/folder/(key+ext)).is_file()),None)
            assert path is not None,key
            b=path.read_bytes();row=(str(path.relative_to(BASE)),0,len(b))
        assert cid(b,cid_bytes(key)[1])==key;verified.add(key)
        obj=None if cid_bytes(key)[1]==0x55 else decode(b)
        if obj is not None:check_sets(obj);assert encode(obj)==b
        return obj,row,b
    def load(key):
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone():return
        obj,row,b=read(key);newblocks.append(key)
        schema='raw' if obj is None else obj['schema']
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(key,schema,*row))
        if obj is None:return
        active=set(links({k:v for k,v in obj.items() if k!='parents'})) if schema=='pkst/snapshot@0.1' else set(links(obj))
        db.executemany('INSERT INTO edges VALUES(?,?,?)',[(key,x,int(x not in active)) for x in set(links(obj))])
        if schema=='pkst/source@0.1':db.execute('INSERT INTO sources VALUES(?,?,?,?)',(key,obj['platform'],obj['namespace'],obj['native_thread_id']))
        elif schema=='pkst/content@0.1':db.execute('INSERT INTO content VALUES(?,?)',(key,obj['text']))
        elif schema=='pkst/occurrence@0.1':
            t=obj['event_time']
            db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(key,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)',[(key,i,x['$link']) for i,x in enumerate(obj['content'])])
        elif schema=='pkst/extraction-record@0.1':
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],key,obj['raw']['$link'],json.dumps({k:obj[k] for k in ['coordinate','start','end','pointer','parser'] if k in obj},ensure_ascii=False)))
    files=[];filekeys={}
    for p in sorted(OUT.rglob('*')):
        if not p.is_file() or p.name.startswith('09-'):continue
        b=p.read_bytes();k=raw(b);rel=p.relative_to(OUT).as_posix();filekeys[rel]=k
        files.append({'path':str(p.relative_to(BASE)),'raw':link(k),'bytes':len(b),'sha256':sha(b)})
    document=store.put({'schema':'math/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造','raw':link(filekeys['02-new-principles.md']),'previous':link(baseline['old_document']),'insertion':link(filekeys['insertion-manifest.json']),'edition':'2026-10-26 mathematical contribution chapter','authorship':'source-led editorial proposal; author adoption not asserted'})
    sources={};roots=[document];timepoints=[]
    for ref,r in selected.items():
        sources[ref]=store.put({'schema':'math/source@1','namespaces':NS,'ref':ref,'occurrence':link(r['occurrence']),'content':link(r['content']),'evidence':linkset([r['occurrence']]+r['anchors']),'event_time':r['native_event_time'],'boundary':'native role is not proof of personal authorship; selected spans separately assessed'})
        timepoints.append(store.put({'schema':'math/source-timepoint@1','namespaces':NS,'source':link(sources[ref]),'event_time':r['native_event_time'],'relation_to_chapter':'selected prior discussion or new writing request','boundary':'observed message time, not first invention or automatic supersession'}))
    passages=[];quotes=[]
    for x in manifest['items']:
        quote=None
        if x.get('ref'):
            ref=x['ref'];a,b=x['source_span'];r=selected[ref]
            quote=store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':r['text'][a:b],'force':'quote','holder':{'kind':'unknown','id':'source-authorship-not-inferred'},'evidence':linkset([sources[ref]]),'asserted_by':ACTOR,'lineage':None,'math:source_span':{'source':link(sources[ref]),'start':a,'end':b,'coordinate':'unicode-scalar-half-open'}})
            quotes.append(quote)
        passages.append(store.put({'schema':'math/passage@1','namespaces':NS,'document':link(document),'ordinal':x['ordinal'],'kind':x['kind'],'text':x['text'],'chapter_span':x['chapter_span'],'document_span':x['document_span'],'quote':link(quote) if quote else None,'source':link(sources[x['ref']]) if x.get('ref') else None,'source_span':x.get('source_span'),'source_sha256':x.get('source_sha256'),'edits':x.get('edits',[]),'author_assessment':x.get('author_assessment'),'editorial_reason':x.get('reason')}))
    chapter=store.put({'schema':'math/chapter@1','namespaces':NS,'document':link(document),'title':manifest['title'],'raw':link(filekeys['01-chapter.md']),'passages':[link(p) for p in passages],'placement':'after 科学、教育与文明的持续创造; before 后记','author_acceptance':False})
    concept=store.put({'schema':'pkst/concept@0.1','label':plan['new_concept']['label'],'definition':plan['new_concept']['definition'],'evidence':linkset([chapter,sources['MATH-REQUEST']]),'asserted_by':ACTOR,'lineage':None})
    relations=[]
    for r in plan['relations']:
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'applies-to','from':link(previous_concepts[r['concept']]),'to':link(concept),'evidence':linkset([sources['MATH-REQUEST']]+[sources[ref] for ref in r['refs']]),'asserted_by':ACTOR,'basis':'inferred','scope':r['scope']+'；本次编辑解释，不是制度效果验证或作者采纳。'}))
    webnodes=[]
    for r in json.loads((ARCHIVE/'external-sources.json').read_bytes()):
        payload={'schema':'math/web-evidence@1','namespaces':NS,**r}
        if r['id']=='speech':
            b=(WORK/r['html_file']).read_bytes();assert sha(b)==r['capture']['sha256']
            payload['html_raw']=link(raw(b));payload['reading_projection_raw']=link(raw((WORK/r['reading_projection']).read_bytes()))
        webnodes.append(store.put(payload))
    change=store.put({'schema':'pkst/change@0.1','operation':'extend','from_versions':linkset([baseline['old_document']]),'to_versions':linkset([document]),'evidence':linkset([sources['MATH-REQUEST']]),'asserted_by':ACTOR,'basis':'explicit','reason':'Requested new case chapter inserted; previous manuscript body byte-preserved. Editorial extension is not owner adoption of every formulation.'})
    roots.extend([chapter,concept,change]+list(sources.values())+timepoints+relations+webnodes)
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['PROFILE.md','baseline.json','selected-sources.json','semantic-plan.json','text-verification.json','request-capture.json','external-sources.json']]
    implementation=[{'path':str(p.relative_to(ROOT)),'raw':link(raw(p.read_bytes())),'sha256':sha(p.read_bytes())} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset(roots+[f['raw']['$link'] for f in files]+[f['raw']['$link'] for f in implementation]),'implementation':link(raw(Path(__file__).read_bytes())),'coverage':{'scope':'one mathematical contribution chapter and exact insertion into expanded manuscript','source_entries':len(selected),'new_native_events':1,'local_only':True,'files':files,'implementation_files':implementation,'external_source_boundary':'limited factual notes; public speech HTML and derived text stored internally, not republished as reader text'}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['old_dossier_root']]),'roots':linkset([activity]),'coverage':{'recorded_cutoff':now,'scope':'requested mathematics case chapter','pending':['author review'],'not_performed':['publication','institutional experiment','exhaustive semantic review of corpus']},'protocol':link(PROTOCOL)})
    members=set();stack=[dossier]
    while stack:
        k=stack.pop()
        if k in members:continue
        members.add(k);load(k)
        stack.extend(row[0] for row in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(k,)))
    for k in members:read(k)
    db.executemany('INSERT INTO membership VALUES(?,?)',[(COL,k) for k in members])
    count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count==base['unique_current_events']+1
    pinned=base['pinned_sources']+[{'collection':COL,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=cat.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,'inputs':linkset([p['root'] for p in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),'coverage':{'scope':'preserve existing collections; append mathematical case chapter','baseline_snapshot':pointer['snapshot'],'current_events':count}})
    snapshot=cat.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integration]),'coverage':{'recorded_cutoff':now,'scope':'federated corpus and appended case chapter','local_only':True,'pending':['author manuscript review','exhaustive corpus interpretation']},'protocol':link(PROTOCOL)})
    stack=[snapshot]
    while stack:
        k=stack.pop()
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():continue
        load(k);stack.extend(row[0] for row in db.execute('SELECT dst FROM edges WHERE src=?',(k,)))
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
    degree={k:0 for k, in db.execute('SELECT cid FROM blocks')};children=defaultdict(list)
    for a,b in db.execute('SELECT DISTINCT src,dst FROM edges'):children[a].append(b);degree[b]+=1
    queue=deque(k for k,n in degree.items() if n==0);visited=0
    while queue:
        a=queue.popleft();visited+=1
        for b in children[a]:
            degree[b]-=1
            if degree[b]==0:queue.append(b)
    assert visited==len(degree),'object dependency cycle'
    assert db.execute('SELECT count(*) FROM current_occurrences o WHERE NOT EXISTS(SELECT 1 FROM anchors a WHERE a.occurrence=o.cid)').fetchone()[0]==0
    db.commit();assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',(COL,)))
    report={'schema':'math/archive-report@1','status':'staged','recorded_at':now,'snapshot':dossier,'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'chapter':chapter,'concept':concept,'change':change,'sources':sources,'quotes':quotes,'passages':passages,'relations':relations,'timepoints':timepoints,'web_evidence':webnodes,'activity':activity,'files':files,'current_events':count,'new_native_events':1,'closure_blocks':len(members),'closure_counts':counts,'freshly_byte_verified_blocks':len(verified),'new_catalog_blocks':newblocks,'full_reference_graph_nodes':visited,'elapsed_seconds':round(time.monotonic()-started,3)}
    write_json(ARCHIVE/'report.json',report);pinned[-1]['report_sha256']=sha((ARCHIVE/'report.json').read_bytes())
    catreport={**base,'run':RUN,'recorded_at':now,'snapshot':snapshot,'pinned_sources':pinned,'database':str((destination/'catalog.sqlite').relative_to(BASE)),'unique_current_events':count,'current_events_with_anchors':count,'current_counts_by_collection':{**base['current_counts_by_collection'],COL:counts},'all_catalog_blocks_including_history_and_federation':visited,'freshly_byte_verified_blocks':len(verified),'verification_scope':'Text replay and exact insertion verified; new closure bytes and full reference DAG checked; activation awaits independent replay','baseline_verification_report':pointer['report'],'status':'staged'}
    write_json(C/'catalog'/f'report-{RUN}.json',catreport)
    write_json(ARCHIVE/'staged-pointer.json',{'report':f'report-{RUN}.json','snapshot':snapshot,'database':catreport['database']})
    db.close()
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','closure_blocks','full_reference_graph_nodes','elapsed_seconds']},ensure_ascii=False))

if __name__=='__main__':stage()
