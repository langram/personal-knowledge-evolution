"""Append the source-linked bilingual edition; activate a verified catalog copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, EDITION, OUT, PRIOR, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261101-institutions-coherence-v1'
COLLECTION='institutions-coherence-20261101'
NS={'ic':'urn:pkst:editorial:institutions-coherence:1'}
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
    historical=[]
    ledger=json.loads((OUT/'translation-ledger.json').read_bytes())
    manifest=json.loads((OUT/'revision-manifest.json').read_bytes())
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
    prior_object(baseline['document']);prior_object(baseline['english_document'])
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
    document=store.put({'schema':'ic/document@1','namespaces':NS,'language':'zh',
        'title':'新原理：现代科学与人类文明的构造','raw':filekeys['01-new-principles.zh.md'],
        'previous':link(baseline['document']),'revision':filekeys['revision-manifest.json'],
        'passage_manifest':filekeys['passage-manifest.json'],'edition':EDITION,
        'authorship':'Author-led additions with attributed editorial explanation; no claim of individual wording approval'})
    english=store.put({'schema':'ic/document@1','namespaces':NS,'language':'en',
        'title':'New Principles: Modern Science and the Making of Human Civilization',
        'raw':filekeys['02-new-principles.en.md'],'previous':link(baseline['english_document']),
        'derived_from':link(document),'translation_ledger':filekeys['translation-ledger.json'],'edition':EDITION,
        'method':'Idiomatic English adaptation of the additions; unchanged edition-14 chapters preserved byte-for-byte',
        'authorship':'Codex-assisted adaptation; not a new native author utterance or line-by-line approval'})
    landing=store.put({'schema':'ic/book-landing@1','namespaces':NS,'raw':filekeys['book-readme.md'],
        'languages':['zh','en'],'editions':[link(document),link(english)],'placement':'book/readme.md'})
    sources={e['ref']:store.put({'schema':'ic/source@1','namespaces':NS,'ref':e['ref'],
        'occurrence':link(e['occurrence']),'content':link(e['content']),'role':e['role'],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'Visible native event time, not first invention; assistant answers are not automatic author endorsement'}) for e in events}
    quotes={e['ref']:store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':e['text'],'force':'quote',
        'holder':{'kind':'human','id':'archive-owner'} if e['role']=='user' else ACTOR,
        'evidence':linkset([sources[e['ref']]]),'asserted_by':ACTOR,'lineage':None,
        'ic:source_span':{'coordinate':'unicode-scalar-half-open','range':[0,len(e['text'])]}}) for e in events}
    sections=[];translations=[];revision_objects=[]
    for row in ledger['chapters']:
        z=store.put({'schema':'ic/chapter@1','namespaces':NS,'language':'zh','chapter':row['id'],
            'title':row['title_zh'],'document':link(document),'char_span':row['char_span'],
            'raw':link(raw((WORK/row['source_file']).read_bytes())),'sha256':row['sha256'],
            'coordinate':ledger['coordinate'],'review':row['review']})
        t=store.put({'schema':'ic/translation@1','namespaces':NS,'language':'en','chapter':row['id'],
            'title':row['title_en'],'document':link(english),'source_chapter':link(z),'source_document':link(document),
            'char_span':row['english_char_span'],'sha256':row['english_sha256'],'coordinate':ledger['coordinate'],
            'draft_raw':link(raw((WORK/row['english_source_file']).read_bytes())),
            'draft_sha256':row['english_source_sha256'],'section_map':row['section_map'],
            'external_links':row['external_links'],'review':row['review'],'author_wording_approved':False})
        sections.append(z);translations.append(t)
    for row in manifest['changes']:
        is_zh=row['language']=='zh'
        revision_objects.append(store.put({'schema':'ic/revision@1','namespaces':NS,**row,
            'previous_document':link(baseline['document'] if is_zh else baseline['english_document']),
            'document':link(document if is_zh else english),
            'evidence':linkset([sources[r] for r in row['source_refs']]),
            'author_wording_approved':False,'recorded_by':ACTOR}))
    definitions=[('技术影响与制度纠错的落差', '技术的影响范围和传播速度，与参与、约束和纠错能力分别考察；不是宣称战后制度从未变化。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']), ('物质条件与主观生活体验', '生活条件的改善不自动等于安心、自主和被尊重；地区与因果差异需要独立研究。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']), ('财富和信任资料的口径', '具体年份、人群、财富份额和调查范围各自保留；编辑核验不覆盖作者原话。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']), ('注意力目标与个人掌控', '预测点击与改善长期生活不同，注意力目标也需要个人参与、解释、调整与退出。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']), ('运行时与授权分层衔接', '个人记忆、MerkleVM、冷热路径、任务注意力、证据权重、基本权利和执行授权协同而不混同。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']), ('制度自我修正的经验检验', '比较影响传播和纠错链条，在反例、不同人群与相同任务中检验新旧安排，允许修正自身优越性的判断。', ['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW'])]
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset([sources[r] for r in refs]+[document]),'asserted_by':ACTOR,'lineage':None})
        for label,definition,refs in definitions]
    relations=[]
    for a,b,predicate in [(0,1,'motivates'),(2,0,'qualifies'),(1,3,'motivates'),(4,3,'supports'),(3,5,'informs'),(5,0,'qualifies')]:
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(concepts[a]),'to':link(concepts[b]),
            'evidence':linkset([document]),'asserted_by':ACTOR,'basis':'inferred',
            'scope':'Editorial map of proposed relationships, not a proved causal law or completed implementation.'}))
    for old in baseline['concepts']:
        prior_object(old)
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'informs','from':link(old),'to':link(concepts[4]),
            'evidence':linkset([document,baseline['document']]),'asserted_by':ACTOR,'basis':'inferred',
            'scope':'Extend the preceding attention, runtime, cooperation, and institutional framework without replacing its earlier source or accepted ability-complementarity revision.'}))
    change=store.put({'schema':'pkst/change@0.1','operation':'revise',
        'from_versions':linkset([baseline['document'],baseline['english_document']]),
        'to_versions':linkset([document,english]),'evidence':linkset([sources['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']]),
        'asserted_by':ACTOR,'basis':'explicit','reason':'Integrate the institutional-gap passage and coherence review; preserve originals and edition-14 text outside bounded edit spans.'})
    prior_object(prior_report['prior_author_revision']);prior_object(prior_report['prior_author_acceptance'])
    continuation=store.put({'schema':'ic/evolution-continuation@1','namespaces':NS,
        'previous_author_revision':link(prior_report['prior_author_revision']),
        'previous_acceptance':link(prior_report['prior_author_acceptance']),
        'previous_continuation':link(prior_report['evolution_continuation']),
        'timeline':filekeys['07-thought-evolution.json'],'sources':linkset(list(sources.values())),
        'document_change':link(change),'author_wording_approved':False,
        'boundary':'Preserve native claims and visible revision chronology; editorial qualifications do not replace author originals.'})
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),
        'outputs':linkset([document,english,landing,change,continuation]+sections+translations+revision_objects+
            list(sources.values())+list(quotes.values())+concepts+relations+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'Two visible events including prior-release context; one author message; 42 reversible bilingual edits; all 32 Chinese chapters read, English changes compared and whole-book structure checked',
            'files':files,'implementation_files':implementation,'pending':['author review of editorial wording and English adaptation'],
            'not_asserted':['unchanged postwar institutions','identical US and China top-0.1 wealth trends','universal youth well-being decline','causal validation of the proposed institutions']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'Institutional gap, distribution and well-being evidence, whole-book coherence and empirical self-correction'},'protocol':link(PROTOCOL)})
    pinned=previous['pinned_sources']+[{'collection':COLLECTION,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([x['root'] for x in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'Append edition 15 and retain all prior source collections'}})
    snapshot=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integration]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'Federated source and manuscript archive'},'protocol':link(PROTOCOL)})

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
    report={'schema':'ic/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
        'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'english_document':english,
        'book_landing':landing,'sections':sections,'translations':translations,'revision_objects':revision_objects,
        'sources':sources,'occurrences':[e['occurrence'] for e in events],'quotes':quotes,
        'concepts':concepts,'relations':relations,'change':change,'evolution_continuation':continuation,
        'prior_author_revision':prior_report['prior_author_revision'],'prior_author_acceptance':prior_report['prior_author_acceptance'],
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
    tmp=C/'catalog/current.institutions-coherence.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
