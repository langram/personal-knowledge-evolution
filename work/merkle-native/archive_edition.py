"""Append recent conversations and a source-led chapter to an immutable catalog copy."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OLD, OUT, WORK, raw, sha, write_json
from verify import verify as verify_text
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset

RUN='20261029-merkle-native-v1'
COLLECTION='merkle-native-20261029'
ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
NS={'mn':'urn:pkst:merkle-native:1'}

def archive():
    if (ARCHIVE/'report.json').exists():
        raise RuntimeError('Report exists. Reconcile saved catalog before retrying.')
    checks=verify_text()
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes()); pointer=baseline['pointer']
    assert json.loads((C/'catalog/current.json').read_bytes())==pointer
    previous=json.loads((C/'catalog'/pointer['report']).read_bytes())
    events=json.loads((ARCHIVE/'events.json').read_bytes())
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    capture=json.loads((ARCHIVE/'capture.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    now=datetime.now(timezone.utc).isoformat(); store=Store(ARCHIVE)
    original_db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    verified_previous=set(); cached_previous={}

    def previous_object(key):
        if key in cached_previous:return cached_previous[key]
        schema,path,offset,size=original_db.execute('SELECT schema,path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        with (BASE/path).open('rb') as stream:stream.seek(offset); data=stream.read(size)
        assert cid(data,cid_bytes(key)[1])==key
        verified_previous.add(key)
        cached_previous[key]=None if schema=='raw' else decode(data)
        return cached_previous[key]

    previous_object(baseline['document'])
    files=[]
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path.name.startswith('09-'):continue
        data=path.read_bytes()
        files.append({'path':str(path.relative_to(BASE)),'name':path.name,'raw':link(raw(data)),'bytes':len(data),'sha256':sha(data)})
    file_keys={x['name']:x['raw'] for x in files}
    document=store.put({'schema':'mn/document@1','namespaces':NS,
        'title':'新原理：现代科学与人类文明的构造','raw':file_keys['02-new-principles.md'],
        'previous':link(baseline['document']),'insertion':file_keys['insertion-manifest.json'],
        'edition':'2026-10-29 Merkle-native language and software ecosystem',
        'authorship':'Source-led editorial proposal; specific revisions not automatically author-adopted.'})
    sources={ref:store.put({'schema':'mn/source@1','namespaces':NS,'ref':ref,
        'occurrence':link(e['occurrence']),'content':[link(k) for k in e['content']],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'Native message time, not date of first invention. Embedded AI quotations do not imply author originality.'}) for ref,e in selected.items()}
    quotes=[]; passages=[]
    for item in manifest['items']:
        quote=None; ref=item.get('ref')
        if ref:
            quote=store.put({'schema':'pkst/statement@0.1','namespaces':NS,
                'text':selected[ref]['text'][slice(*item['source_span'])],'force':'quote',
                'holder':{'kind':'human','id':'archive-owner'},'evidence':linkset([sources[ref]]),
                'asserted_by':ACTOR,'lineage':None,
                'mn:source_span':{'coordinate':'unicode-scalar-half-open','range':item['source_span']}})
            quotes.append(quote)
        passages.append(store.put({'schema':'mn/passage@1','namespaces':NS,'document':link(document),
            **{k:v for k,v in item.items() if k!='ref'},'source':link(sources[ref]) if ref else None,'quote':link(quote) if quote else None}))
    chapter=store.put({'schema':'mn/chapter@1','namespaces':NS,'title':manifest['title'],
        'document':link(document),'raw':file_keys['01-chapter.md'],'passages':[link(k) for k in passages],
        'placement':'after MerkleVM software seed, before human and AI collaborative construction','author_acceptance':False})
    definitions=[
        ('先兼容再替代的软件种子','从可核验的功能描述、映射与替换开始，使旧生态兼容成为新生态独立运行的生长路径。',['PLAN-03','PLAN-04','PLAN-05']),
        ('共同结构中的多样性实现','共同表示与精确约定支持不同设备、算法与实现，不强制抹平真实行为差异。',['PLAN-07','PLAN-09','PLAN-11']),
        ('从品牌组合到能力组合','把应用与平台中的功能拆成有条件、可组合的能力，降低数据和能力被整套服务锁定的程度。',['PLAN-08','PLAN-09']),
        ('模型与执行环境的可替换性','语言模型和harness也是被封装和描述的能力，个人知识及权限不依附某个模型。',['PLAN-12']),
        ('统一对象身份与动态物理布局','用内容身份连接文件、应用、设备与网络对象，逻辑分解与物理打包分别选择。',['PLAN-14','PLAN-15','PLAN-16','PLAN-17']),
        ('人类表现层与AI结构接口','保留人类语言与图形表现，让机器直接处理对象、类型、操作、依赖和检验结果。',['PLAN-18']),
        ('内容变化驱动依赖图演化','声明的构造与依赖改变产生新身份，沿上层依赖构造候选新版本，再验证与选择启用。',['PLAN-19']),
        ('可核验的软件生态与文明协作','用可核验的知识、代码和变更支撑数据主权及公共协作；身份本身不赋予权限或保证公平。',['PLAN-09','REQUEST'])]
    concepts=[]
    for label,definition,refs in definitions:
        concepts.append(store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
            'evidence':linkset([sources[r] for r in refs]+[chapter]),'asserted_by':ACTOR,'lineage':None}))
    relations=[]
    for a,b,scope in [(0,2,'迁移路径承接应用能力的拆分'),(1,4,'共同结构区分语义与物理布局'),
                      (2,7,'能力组合连接个人主权与共同创造'),(3,5,'机器接口支持模型替换'),
                      (4,5,'精确对象支撑机器直接处理'),(4,6,'内容身份支撑依赖演化'),
                      (5,7,'结构接口减少协作中的重复解释'),(6,7,'版本与验证依据支持持续演化')]:
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'explains','from':link(concepts[a]),'to':link(concepts[b]),
            'evidence':linkset([chapter]),'asserted_by':ACTOR,'basis':'inferred','scope':scope+'；编辑梳理的设计关系，不是已证实的经验因果。'}))
    older=json.loads((C/'new-principles-20261026/report.json').read_bytes())['concepts']; related=[]
    for name,index in [('C13',4),('C16',5),('C17',5),('C19',0),('C20',0),('C21',6),('C27',7),('C12',7),('C34',6)]:
        key=older[name]; obj=previous_object(key); related.append((name,key,obj['label']))
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':'applies-to','from':link(key),'to':link(concepts[index]),
            'evidence':linkset([chapter]),'asserted_by':ACTOR,'basis':'inferred','scope':'把既有主题“'+obj['label']+'”展开到本章；编辑关系待作者审阅。'}))
    timeline=store.put({'schema':'mn/evolution@1','namespaces':NS,
        'steps':[{'concept':link(key),'source_messages':[link(sources[r]) for r in refs],
                  'native_times':[selected[r]['time'] for r in refs]} for key,(_,_,refs) in zip(concepts,definitions)],
        'scope':'Thematic development within the dated discussion. Steps are editorial grouping, not proof of first invention or strict temporal causality.',
        'incomplete_wording':link(sources['PLAN-10']),'completed_wording':link(sources['PLAN-11'])})
    web=[('Unison content-addressed definitions','https://www.unison-lang.org/docs/the-big-idea/','Names separate from syntax-tree identity; exact dependencies.'),
         ('Unison update workflow','https://www.unison-lang.org/docs/usage-topics/workflow-how-tos/update-code/','Impacted dependents and branches; not automatic behavioral equivalence.'),
         ('IPLD data model','https://ipld.io/docs/data-model/','Content links and data model distinct from serialization.'),
         ('MLIR rationale','https://mlir.llvm.org/docs/Rationale/Rationale/','Multilevel intermediate representations; not proof of the proposed universal ecosystem.')]
    evidence=[store.put({'schema':'mn/external-source@1','namespaces':NS,'title':title,'url':url,'scope':scope,
                        'accessed_at':now,'method':'web tool','full_page_copy':False}) for title,url,scope in web]
    change=store.put({'schema':'pkst/change@0.1','operation':'extend','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['REQUEST']]),'asserted_by':ACTOR,'basis':'explicit',
        'reason':'Author requested recent discussion archival and an independent Merkle-native chapter; previous book preserved outside insertion.'})
    batch=store.put({'schema':'mn/conversation-batch@1','namespaces':NS,
        'occurrences':[link(e['occurrence']) for e in events],
        'evidence':linkset([k for e in events for k in e['anchors']]),
        'scope':{'window_start':capture['window_start'],'window_end':capture['window_end'],
                 'native_records':capture['native_records'],'remote_projection_records':capture['remote_projection_records'],
                 'limits':capture['coverage_limits']}})
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','events.json','selected-sources.json','text-verification.json']]
    implementation=[{'path':str(path.relative_to(WORK)),'raw':link(raw(path.read_bytes()))} for path in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset(inputs),'outputs':linkset([document,chapter,change,timeline,batch]+list(sources.values())+concepts+relations+evidence+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'Recent visible conversation text and one book chapter','files':files,'implementation_files':implementation,
                    'pending':['author review of editorial changes'],'not_asserted':['all cloud sources refreshed','Mac raw filesystem completeness','universal performance advantage']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':now,'scope':'Merkle-native chapter and recent conversation increment'},'protocol':link(PROTOCOL)})
    pinned=previous['pinned_sources']+[{'collection':COLLECTION,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([x['root'] for x in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'append recent conversations and Merkle-native chapter; retain all previous collections'}})
    snapshot=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integration]),
        'coverage':{'recorded_cutoff':now,'scope':'federated source and manuscript archive'},'protocol':link(PROTOCOL)})

    # Common full re-import is unnecessary. Verify the append graph against the
    # immutable baseline, then construct a new catalog copy and activate it last.
    new = {}
    for path in sorted((ARCHIVE / 'objects').glob('*.cbor')):
        data = path.read_bytes(); key = path.stem
        assert cid(data) == key
        obj = decode(data); assert encode(obj) == data
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?', (key,)).fetchone():
            new[key] = (obj, path, data)
    for path in sorted((ARCHIVE / 'raw').glob('*.bin')):
        data = path.read_bytes(); key = path.stem
        assert cid(data, 0x55) == key
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?', (key,)).fetchone():
            new[key] = (None, path, data)
    gray, black = set(), set()
    def visit(key):
        if key in black:
            return
        assert key not in gray, 'new object dependency cycle'
        if key not in new:
            previous_object(key)
            black.add(key)
            return
        gray.add(key)
        obj = new[key][0]
        if obj:
            for target in links(obj):
                visit(target)
        gray.remove(key); black.add(key)
    for key in new:
        visit(key)
    destination = C / 'catalog/.private' / RUN
    destination.mkdir(exist_ok=False)
    db = sqlite3.connect(destination / 'catalog.sqlite')
    original_db.backup(db); original_db.close()
    for key, (obj, path, data) in new.items():
        schema = obj['schema'] if obj else 'raw'
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)', (key, schema, str(path.relative_to(BASE)), 0, len(data)))
        if obj is None:
            continue
        historical = {x['$link'] for x in obj.get('parents', [])} if schema == 'pkst/snapshot@0.1' else set()
        db.executemany('INSERT INTO edges VALUES(?,?,?)', [(key, t, int(t in historical)) for t in set(links(obj))])
        if schema == 'pkst/source@0.1':
            db.execute('INSERT INTO sources VALUES(?,?,?,?)', (key, obj['platform'], obj['namespace'], obj['native_thread_id']))
        elif schema == 'pkst/content@0.1':
            db.execute('INSERT INTO content VALUES(?,?)', (key, obj['text']))
        elif schema == 'pkst/occurrence@0.1':
            t = obj['event_time']
            db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)', (key, obj['source']['$link'], obj['native_id'],
                obj['native_role'], obj['actor_kind'], obj['process_kind'], t['value'], t['format'], json.dumps(t, ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)', [(key, i, p['$link']) for i, p in enumerate(obj['content'])])
        elif schema == 'pkst/extraction-record@0.1':
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)', (obj['occurrence']['$link'], key, obj['raw']['$link'],
                json.dumps({k: obj.get(k) for k in ['coordinate', 'start', 'end', 'pointer', 'parser']}, ensure_ascii=False)))
    members, pending = set(), [dossier]
    while pending:
        key = pending.pop()
        if key in members:
            continue
        members.add(key)
        pending.extend(t for t, in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0', (key,)))
    db.executemany('INSERT INTO membership VALUES(?,?)', [(COLLECTION, k) for k in members])
    count = db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count == previous['unique_current_events'] + len(events)
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0] == 0
    for event in events:
        rows = db.execute('SELECT c.text FROM current_content c JOIN parts p ON p.content=c.cid WHERE p.occurrence=? ORDER BY p.ordinal', (event['occurrence'],)).fetchall()
        assert '\n\n'.join(row[0] for row in rows) == event['text']
    counts = dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema', (COLLECTION,)))
    total_blocks = db.execute('SELECT count(*) FROM blocks').fetchone()[0]
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    db.close()
    report = {'schema': 'mn/archive-report@1', 'status': 'verified', 'recorded_at': now,
        'snapshot': dossier, 'federated_snapshot': snapshot, 'baseline_snapshot': pointer['snapshot'],
        'document': document, 'chapter': chapter, 'sources': sources, 'conversation_batch': batch, 'evolution': timeline,
        'quotes': quotes, 'passages': passages, 'concepts': concepts, 'relations': relations, 'change': change,
        'related_prior_concepts': related, 'web_evidence': evidence, 'files': files,
        'new_native_events': capture['native_records'], 'new_remote_projection_events': capture['remote_projection_records'], 'new_events': len(events), 'current_events': count, 'new_objects': sorted(new), 'closure_blocks': len(members),
        'closure_counts': counts, 'verified_previous_link_targets': len(verified_previous),
        'full_catalog_blocks': total_blocks, 'text_verification': checks,
        'verification_scope': 'new blocks, direct baseline link targets, append graph, SQL links, source lookup and complete text replay; previous graph verification inherited'}
    write_json(ARCHIVE / 'report.json', report)
    pinned[-1]['report_sha256'] = sha((ARCHIVE / 'report.json').read_bytes())
    catreport = {**previous, 'run': RUN, 'recorded_at': now, 'snapshot': snapshot, 'baseline_snapshot': pointer['snapshot'],
        'pinned_sources': pinned, 'database': str((destination / 'catalog.sqlite').relative_to(BASE)),
        'unique_current_events': count, 'current_events_with_anchors': count,
        'current_counts_by_collection': {**previous['current_counts_by_collection'], COLLECTION: counts},
        'all_catalog_blocks_including_history_and_federation': total_blocks,
        'freshly_byte_verified_blocks': len(new) + len(verified_previous), 'status': 'verified',
        'verification_scope': report['verification_scope'], 'baseline_verification_report': pointer['report']}
    write_json(C / 'catalog' / ('report-' + RUN + '.json'), catreport)
    assert json.loads((C / 'catalog/current.json').read_bytes()) == pointer
    next_pointer = {'report': 'report-' + RUN + '.json', 'snapshot': snapshot, 'database': catreport['database']}
    temp = C / 'catalog/current.merkle-native.tmp'
    write_json(temp, next_pointer)
    temp.replace(C / 'catalog/current.json')
    write_json(ARCHIVE / 'status.json', {'status': 'active', 'snapshot': snapshot, 'verified_at': datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k: report[k] for k in ['status', 'snapshot', 'federated_snapshot', 'current_events', 'closure_blocks', 'verified_previous_link_targets']}, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    archive()
