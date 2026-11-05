"""Append the source-linked bilingual edition; activate a verified catalog copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, EDITION, OUT, PRIOR, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261105-relativity-alignment-v1'
COLLECTION='relativity-alignment-20261105'
NS={'ra':'urn:pkst:editorial:relativity-alignment:1'}
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
    document=store.put({'schema':'ra/document@1','namespaces':NS,'language':'zh',
        'title':'新原理：社会科学的数学原理','raw':filekeys['01-new-principles.zh.md'],
        'previous':link(baseline['document']),'revision':filekeys['revision-manifest.json'],
        'passage_manifest':filekeys['passage-manifest.json'],'edition':EDITION,
        'authorship':'Author-led additions with attributed editorial explanation; no claim of individual wording approval'})
    english=store.put({'schema':'ra/document@1','namespaces':NS,'language':'en',
        'title':'Nova Principia: Mathematical Principles of Social Science',
        'raw':filekeys['02-new-principles.en.md'],'previous':link(baseline['english_document']),
        'derived_from':link(document),'translation_ledger':filekeys['translation-ledger.json'],'edition':EDITION,
        'method':'Idiomatic English adaptation of the additions; unchanged edition-17 chapters preserved byte-for-byte',
        'authorship':'Codex-assisted adaptation; not a new native author utterance or line-by-line approval'})
    landing=store.put({'schema':'ra/book-landing@1','namespaces':NS,'raw':filekeys['book-readme.md'],
        'languages':['zh','en'],'editions':[link(document),link(english)],'placement':'book/readme.md'})
    sources={e['ref']:store.put({'schema':'ra/source@1','namespaces':NS,'ref':e['ref'],
        'occurrence':link(e['occurrence']),'content':link(e['content']),'role':e['role'],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'Visible source event, not first invention. Gemini export user times lack timezone and reply times are missing; native Codex times are UTC. AI answers are not author endorsement.'}) for e in events}
    quotes={e['ref']:store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':e['text'],'force':'quote',
        'holder':{'kind':'human','id':'archive-owner'} if e['role']=='user' else {'kind':'ai','id':'gemini' if e['platform']=='gemini' else 'codex'},
        'evidence':linkset([sources[e['ref']]]),'asserted_by':ACTOR,'lineage':None,
        'ra:source_span':{'coordinate':'unicode-scalar-half-open','range':[0,len(e['text'])]}}) for e in events}
    sections=[];translations=[];revision_objects=[]
    for row in ledger['chapters']:
        z=store.put({'schema':'ra/chapter@1','namespaces':NS,'language':'zh','chapter':row['id'],
            'title':row['title_zh'],'document':link(document),'char_span':row['char_span'],
            'raw':link(raw((WORK/row['source_file']).read_bytes())),'sha256':row['sha256'],
            'coordinate':ledger['coordinate'],'review':row['review']})
        t=store.put({'schema':'ra/translation@1','namespaces':NS,'language':'en','chapter':row['id'],
            'title':row['title_en'],'document':link(english),'source_chapter':link(z),'source_document':link(document),
            'char_span':row['english_char_span'],'sha256':row['english_sha256'],'coordinate':ledger['coordinate'],
            'draft_raw':link(raw((WORK/row['english_source_file']).read_bytes())),
            'draft_sha256':row['english_source_sha256'],'section_map':row['section_map'],
            'external_links':row['external_links'],'review':row['review'],'author_wording_approved':False})
        sections.append(z);translations.append(t)
    for row in manifest['changes']:
        is_zh=row['language']=='zh'
        revision_objects.append(store.put({'schema':'ra/revision@1','namespaces':NS,**row,
            'previous_document':link(baseline['document'] if is_zh else baseline['english_document']),
            'document':link(document if is_zh else english),
            'evidence':linkset([sources[r] for r in row['source_refs']]),
            'author_wording_approved':False,'recorded_by':ACTOR}))
    definitions=[
        ('认知参考系与相对性', '作者从物理参考系追问认知坐标与社会涌现；正文将描述变换、处境变化和价值判断分别讨论。', ['GEMINI-01-AUTHOR','GEMINI-04-AUTHOR','GEMINI-05-AUTHOR','AUTHOR-RELATIVITY-ALIGNMENT']),
        ('语义表示与意识测量的边界', '大模型提供部分可计算的语义表示；不是意识的完整测量，也不是认知数学建模的起点。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('社会科学与自然科学的共同底座', '作者主张采用自然主义与可检验机制连接社会科学和自然科学；不以此抹去既有社会科学或宣称已完成统一理论。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('不绝对化自我与保留事实责任', '认知有形成条件，拒绝神圣化和妖魔化；理解条件不等于取消事实真假、伤害责任或基本权利。', ['GEMINI-04-AUTHOR','AUTHOR-RELATIVITY-ALIGNMENT']),
        ('局部对齐的外部代价', '对某一控制者有用的AI仍可能损害其他参与者；目标、授权和受影响者权利需要共同检查。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('优势集中与力量对峙的风险路径', '能力差距可能扩大支配风险，对峙可能放大误判；两者是有条件的场景，不是必然结局或固定倍数预测。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('人际制度与人机对齐共同迭代', '人类之间的合作元规则为AI对齐提供制度基础；技术安全仍需独立验证，两者并行改进。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('对齐作为更新算子的不动点', '以自映射F_e(z)或评价函数空间更新U(R)提出固定点模型；存在、收敛、公平与开放演化分别检验。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('文明与生态的协调', '将能源、物质循环、生态承受能力、其他生命与未来世代纳入反馈；不假定宇宙具有统一意志或给定回报函数。', ['AUTHOR-RELATIVITY-ALIGNMENT']),
        ('认知模型的来源与授权', 'Merkle-DAG保留原话、解释、模型版本和修改关系；内容身份不授予读取、推断或行动权限。', ['GEMINI-05-AUTHOR','AUTHOR-RELATIVITY-ALIGNMENT']),
    ]
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset([sources[r] for r in refs]+[document]),'asserted_by':ACTOR,'lineage':None})
        for label,definition,refs in definitions]
    relations=[]
    for a,b,predicate in [(1,0,'qualifies'),(2,0,'supports'),(0,3,'informs'),(3,6,'supports'),(4,6,'motivates'),(5,4,'qualifies'),(7,6,'models'),(8,6,'extends'),(9,0,'supports'),(9,6,'supports')]:
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(concepts[a]),'to':link(concepts[b]),
            'evidence':linkset([document]),'asserted_by':ACTOR,'basis':'inferred',
            'scope':'Editorial map of proposed relationships, not a proved causal law or completed implementation.'}))
    for index,target in [(0,6),(1,4),(2,5),(3,7),(4,4),(5,6)]:
        old=baseline['concepts'][index]
        prior_object(old)
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'informs','from':link(old),'to':link(concepts[target]),
            'evidence':linkset([document,baseline['document']]),'asserted_by':ACTOR,'basis':'inferred',
            'scope':'Connect prior peaceful persuasion, total costs, goal conditions and correction with multilevel alignment; inherited ability-complementarity revision retained.'}))
    change=store.put({'schema':'pkst/change@0.1','operation':'revise',
        'from_versions':linkset([baseline['document'],baseline['english_document']]),
        'to_versions':linkset([document,english]),'evidence':linkset([sources['AUTHOR-RELATIVITY-ALIGNMENT']]),
        'asserted_by':ACTOR,'basis':'explicit','reason':'Adopt the requested title, integrate reference frames and multilevel alignment, and append self-reflection; preserve author originals, Gemini discussion and editorial distinctions.'})
    prior_object(prior_report['prior_author_revision']);prior_object(prior_report['prior_author_acceptance'])
    continuation=store.put({'schema':'ra/evolution-continuation@1','namespaces':NS,
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
        'coverage':{'scope':'15 visible source events: 10 Gemini export blocks and 5 native Codex events; 8 human messages and 7 AI replies. Seven bounded edits per language, 33 chapter pairs and 29 inherited byte-identical pairs. Partial source chronology and targeted semantic review, not a complete new archive collection or full-book reread.',
            'files':files,'implementation_files':implementation,'pending':['author review of editorial wording and English adaptation'],
            'not_asserted':['semantic embeddings measure all consciousness','relativity abolishes facts or responsibility','fixed points guarantee fairness or convergence','human coordination solves all technical AI alignment','cosmic utility function is established','Gemini reply timestamps or timezone are known']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'Reference frames, social-science foundations, multilevel alignment and conditional fixed-point modeling; native cutoff UTC, attached export clocks unresolved'},'protocol':link(PROTOCOL)})
    pinned=previous['pinned_sources']+[{'collection':COLLECTION,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([x['root'] for x in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'Append edition 18 and retain all prior source collections'}})
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
    report={'schema':'ra/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
        'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'english_document':english,
        'book_landing':landing,'sections':sections,'translations':translations,'revision_objects':revision_objects,
        'sources':sources,'occurrences':[e['occurrence'] for e in events],'quotes':quotes,
        'concepts':concepts,'relations':relations,'change':change,'evolution_continuation':continuation,
        'prior_author_revision':prior_report['prior_author_revision'],'prior_author_acceptance':prior_report['prior_author_acceptance'],
        'historical_sources':[e['source_object'] for e in historical],
        'files':files,'new_native_events':5,'new_markdown_export_events':10,'new_visible_events':len(events),'current_events':count,'new_objects':sorted(new),
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
    tmp=C/'catalog/current.relativity-alignment.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
