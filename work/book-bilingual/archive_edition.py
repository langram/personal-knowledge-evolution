"""Append the reviewed bilingual edition; activate a verified catalog copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OUT, PRIOR, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261031-book-bilingual-v1'
COLLECTION='book-bilingual-20261031'
NS={'bb':'urn:pkst:editorial:book-bilingual:1'}
ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'

def archive():
    if (ARCHIVE/'report.json').exists():
        raise RuntimeError('Report exists; reconcile activation before any retry.')
    checks=verify()
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes());pointer=baseline['pointer']
    assert json.loads((C/'catalog/current.json').read_bytes())==pointer
    previous=json.loads((C/'catalog'/pointer['report']).read_bytes())
    prior_report=json.loads((PRIOR/'report.json').read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    historical=json.loads((OUT/'00-historical-sources.json').read_bytes())
    ledger=json.loads((OUT/'translation-ledger.json').read_bytes())
    manifest=json.loads((OUT/'zh-revision-manifest.json').read_bytes())
    now=datetime.now(timezone.utc).isoformat();store=Store(ARCHIVE)
    original_db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    verified_previous=set()
    def prior_object(key):
        row=original_db.execute('SELECT schema,path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        assert row is not None,key
        schema,path,offset,size=row
        with (BASE/path).open('rb') as stream:
            stream.seek(offset);data=stream.read(size)
        assert cid(data,cid_bytes(key)[1])==key
        verified_previous.add(key)
        return None if schema=='raw' else decode(data)
    prior_object(baseline['document'])
    for e in events:
        assert original_db.execute('SELECT 1 FROM occurrences WHERE cid=?',(e['occurrence'],)).fetchone() is None
        assert original_db.execute('''SELECT 1 FROM current_occurrences o JOIN sources s ON s.cid=o.source
          JOIN parts p ON p.occurrence=o.cid WHERE s.native_thread_id=? AND o.role=? AND o.event_time=? AND p.content=?''',
          (e['thread'],e['role'],e['time'],e['content'])).fetchone() is None
    files=[]
    for path in sorted(OUT.iterdir()):
        if path.is_file() and not path.name.startswith('09-'):
            data=path.read_bytes()
            files.append({'path':str(path.relative_to(BASE)),'name':path.name,'raw':link(raw(data)),
                          'bytes':len(data),'sha256':sha(data)})
    filekeys={x['name']:x['raw'] for x in files}
    document=store.put({'schema':'bb/document@1','namespaces':NS,'language':'zh',
        'title':'新原理：现代科学与人类文明的构造','raw':filekeys['01-new-principles.zh.md'],
        'previous':link(baseline['document']),'revision':filekeys['zh-revision-manifest.json'],
        'edition':'13-book-bilingual','authorship':'author-led text with bounded editorial revisions; final wording not individually author-approved'})
    english=store.put({'schema':'bb/document@1','namespaces':NS,'language':'en',
        'title':'New Principles: Modern Science and the Making of Human Civilization',
        'raw':filekeys['02-new-principles.en.md'],'derived_from':link(document),
        'translation_ledger':filekeys['translation-ledger.json'],'edition':'13-book-bilingual',
        'method':'complete idiomatic English adaptation of this Chinese edition; not a new native author utterance',
        'authorship':'Codex-assisted English adaptation; no claim of line-by-line author approval'})
    landing=store.put({'schema':'bb/book-landing@1','namespaces':NS,'raw':filekeys['book-readme.md'],
        'languages':['zh','en'],'editions':[link(document),link(english)],'placement':'book/readme.md'})
    sources={e['ref']:store.put({'schema':'bb/source@1','namespaces':NS,'ref':e['ref'],
        'occurrence':link(e['occurrence']),'content':link(e['content']),'role':e['role'],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'visible native event time; not first invention or endorsement of every derived sentence'}) for e in events}
    for e in historical:
        obj=prior_object(e['source_object'])
        assert obj['role']==e['role'] and obj['occurrence']['$link']==e['occurrence'] and obj['content']['$link']==e['content']
        assert prior_object(e['content'])['text']==e['text']
        assert prior_object(e['occurrence'])['event_time']['value']==e['time']
        sources[e['ref']]=e['source_object']
    quotes={e['ref']:store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':e['text'],'force':'quote',
        'holder':{'kind':'human','id':'archive-owner'} if e['role']=='user' else ACTOR,
        'evidence':linkset([sources[e['ref']]]),'asserted_by':ACTOR,'lineage':None,
        'bb:source_span':{'coordinate':'unicode-scalar-half-open','range':[0,len(e['text'])]}}) for e in historical+events}
    sections=[];translations=[];revision_objects=[]
    for row in ledger['chapters']:
        z=store.put({'schema':'bb/chapter@1','namespaces':NS,'language':'zh','chapter':row['id'],
            'title':row['title_zh'],'document':link(document),'char_span':row['char_span'],
            'raw':link(raw((WORK/row['source_file']).read_bytes())),'sha256':row['sha256'],
            'coordinate':ledger['coordinate'],'review':row['review']})
        t=store.put({'schema':'bb/translation@1','namespaces':NS,'language':'en','chapter':row['id'],
            'title':row['title_en'],'document':link(english),'source_chapter':link(z),'source_document':link(document),
            'char_span':row['english_char_span'],'sha256':row['english_sha256'],'coordinate':ledger['coordinate'],
            'draft_raw':link(raw((WORK/row['english_source_file']).read_bytes())),
            'draft_sha256':row['english_source_sha256'],'section_map':row['section_map'],
            'external_links':row['external_links'],'review':row['review'],'author_wording_approved':False})
        sections.append(z);translations.append(t)
    for row in manifest['changes']:
        revision_objects.append(store.put({'schema':'bb/revision@1','namespaces':NS,**row,
            'previous_document':link(baseline['document']),'document':link(document),
            'evidence':linkset([sources['AUTHOR-REVISION'],sources['BILINGUAL-REQUEST']]),
            'author_wording_approved':False,'recorded_by':ACTOR}))
    definitions=[
        ('分布前提与制度保障分离','能力和需求怎样分布保持经验问题的地位；防止支配要依靠可检验的权重、权限、复核和退出安排。'),
        ('公平发展支持能力互补','改善实际学习、参与、照护和自由探索条件，连接专业深度与跨领域能力，不以相同能力结果为目标。'),
        ('需要的差异与资源用途','区分个人消费的适宜范围、满足不同需要的实际成本、共同生产资源及对这些资源的决策权限。')]
    evidence=[sources['AUTHOR-REVISION'],sources['DEVELOPMENT-GOALS'],sources['BILINGUAL-REQUEST'],document]
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset(evidence),'asserted_by':ACTOR,'lineage':None}) for label,definition in definitions]
    relations=[]
    for old_index,new_index in [(5,0),(4,0),(0,1),(1,1),(2,1)]:
        key=baseline['concepts'][old_index];prior_object(key)
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'explains','from':link(key),'to':link(concepts[new_index]),
            'evidence':linkset(evidence),'asserted_by':ACTOR,'basis':'inferred',
            'scope':'Editorial continuation of the explicitly accepted author emphasis, not an established causal law or newly approved individual wording.'}))
    change=store.put({'schema':'pkst/change@0.1','operation':'revise','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['BILINGUAL-REQUEST'],sources['AUTHOR-REVISION']]),
        'asserted_by':ACTOR,'basis':'explicit','reason':'Apply the latest author-confirmed emphasis consistently across the complete text and final appendix; preserve prior wording and provenance.'})
    prior_object(prior_report['author_revision']);prior_object(prior_report['author_acceptance'])
    continuation=store.put({'schema':'bb/evolution-continuation@1','namespaces':NS,
        'previous_author_revision':link(prior_report['author_revision']),
        'previous_acceptance':link(prior_report['author_acceptance']),
        'timeline':filekeys['07-thought-evolution.json'],'sources':linkset(list(sources.values())),
        'document_change':link(change),'author_wording_approved':False,
        'boundary':'Original author revision retained, not retroactively rewritten; bilingual editing is a derived continuation.'})
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),
        'outputs':linkset([document,english,landing,change,continuation]+sections+translations+revision_objects+
            list(sources.values())+list(quotes.values())+concepts+relations+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'three new visible events; two retained sources; ten reversible Chinese edits; all 31 English chapters; bilingual book landing page',
            'files':files,'implementation_files':implementation,'pending':['author review of new wording and English adaptation'],
            'not_asserted':['normally distributed abilities or needs','distribution implies no domination','validated institutional effectiveness','perfect translation equivalence']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'full-book consistency and complete English adaptation'},'protocol':link(PROTOCOL)})
    pinned=previous['pinned_sources']+[{'collection':COLLECTION,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([x['root'] for x in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'append bilingual edition and retain all prior source collections'}})
    snapshot=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integration]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'federated source and manuscript archive'},'protocol':link(PROTOCOL)})

    new={}
    for path in sorted((ARCHIVE/'objects').glob('*.cbor')):
        data=path.read_bytes(); key=path.stem
        assert cid(data)==key
        obj=decode(data); assert encode(obj)==data
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone(): new[key]=(obj,path,data)
    for path in sorted((ARCHIVE/'raw').glob('*.bin')):
        data=path.read_bytes(); key=path.stem; assert cid(data,0x55)==key
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone(): new[key]=(None,path,data)
    gray,black=set(),set()
    def visit(key):
        if key in black: return
        assert key not in gray,'new object dependency cycle'
        if key not in new:
            prior_object(key); black.add(key); return
        gray.add(key); obj=new[key][0]
        if obj:
            for target in links(obj): visit(target)
        gray.remove(key); black.add(key)
    for key in new: visit(key)
    destination=C/'catalog/.private'/RUN; destination.mkdir(exist_ok=False)
    db=sqlite3.connect(destination/'catalog.sqlite'); original_db.backup(db); original_db.close()
    for key,(obj,path,data) in new.items():
        schema=obj['schema'] if obj else 'raw'
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(key,schema,str(path.relative_to(BASE)),0,len(data)))
        if obj is None: continue
        historical_edges={x['$link'] for x in obj.get('parents',[])} if schema=='pkst/snapshot@0.1' else set()
        db.executemany('INSERT INTO edges VALUES(?,?,?)',[(key,t,int(t in historical_edges)) for t in set(links(obj))])
        if schema=='pkst/source@0.1': db.execute('INSERT INTO sources VALUES(?,?,?,?)',(key,obj['platform'],obj['namespace'],obj['native_thread_id']))
        elif schema=='pkst/content@0.1': db.execute('INSERT INTO content VALUES(?,?)',(key,obj['text']))
        elif schema=='pkst/occurrence@0.1':
            t=obj['event_time']
            db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(key,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)',[(key,i,p['$link']) for i,p in enumerate(obj['content'])])
        elif schema=='pkst/extraction-record@0.1':
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],key,obj['raw']['$link'],
                json.dumps({k:obj[k] for k in ['coordinate','start','end','pointer','parser']},ensure_ascii=False)))
    members,pending=set(),[dossier]
    while pending:
        key=pending.pop()
        if key in members: continue
        members.add(key); pending.extend(t for t, in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(key,)))
    db.executemany('INSERT INTO membership VALUES(?,?)',[(COLLECTION,k) for k in members])
    count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count==previous['unique_current_events']+len(events)
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
    for e in events:
        assert db.execute('SELECT c.text FROM current_content c JOIN parts p ON p.content=c.cid WHERE p.occurrence=?',(e['occurrence'],)).fetchone()[0]==e['text']
    counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',(COLLECTION,)))
    total=db.execute('SELECT count(*) FROM blocks').fetchone()[0]
    db.commit(); assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]; db.close()
    report={'schema':'bb/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
        'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'english_document':english,
        'book_landing':landing,'sections':sections,'translations':translations,'revision_objects':revision_objects,
        'sources':sources,'occurrences':[e['occurrence'] for e in events],'quotes':quotes,
        'concepts':concepts,'relations':relations,'change':change,'evolution_continuation':continuation,
        'prior_author_revision':prior_report['author_revision'],'prior_author_acceptance':prior_report['author_acceptance'],
        'historical_sources':[e['source_object'] for e in historical],
        'files':files,'new_native_events':len(events),'current_events':count,'new_objects':sorted(new),
        'closure_blocks':len(members),'closure_counts':counts,'verified_previous_link_targets':len(verified_previous),
        'full_catalog_blocks':total,'text_verification':checks,
        'verification_scope':'new blocks, direct prior link targets, append graph, SQL links, exact sources, reversible edit replay and bilingual structure; earlier graph verification inherited'}
    write_json(ARCHIVE/'report.json',report)
    pinned[-1]['report_sha256']=sha((ARCHIVE/'report.json').read_bytes())
    catreport={**previous,'run':RUN,'recorded_at':now,'snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],
        'pinned_sources':pinned,'database':str((destination/'catalog.sqlite').relative_to(BASE)),
        'unique_current_events':count,'current_events_with_anchors':count,
        'current_counts_by_collection':{**previous['current_counts_by_collection'],COLLECTION:counts},
        'all_catalog_blocks_including_history_and_federation':total,'freshly_byte_verified_blocks':len(new)+len(verified_previous),
        'status':'verified','verification_scope':report['verification_scope'],'baseline_verification_report':pointer['report']}
    write_json(C/'catalog'/('report-'+RUN+'.json'),catreport)
    assert json.loads((C/'catalog/current.json').read_bytes())==pointer
    tmp=C/'catalog/current.book-bilingual.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
