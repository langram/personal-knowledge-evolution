"""Verifier-first append: retain immutable prior catalog, activate the new copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OUT, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261030-recording-and-reflection-v1'
COLLECTION='recording-and-reflection-20261030'
NS={'rr':'urn:pkst:editorial:recording-and-reflection:1'}
ACTOR={'kind':'ai','id':'codex'}
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'

def archive():
    if (ARCHIVE/'report.json').exists():
        raise RuntimeError('Report exists; reconcile catalog and activation before any retry.')
    checks=verify()
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes()); pointer=baseline['pointer']
    assert json.loads((C/'catalog/current.json').read_bytes())==pointer
    previous=json.loads((C/'catalog'/pointer['report']).read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    byref={e['ref']:e for e in events}
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    now=datetime.now(timezone.utc).isoformat(); store=Store(ARCHIVE)
    original_db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    verified_previous=set()
    def prior_object(key):
        row=original_db.execute('SELECT schema,path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        assert row is not None,key
        schema,path,offset,size=row
        with (BASE/path).open('rb') as stream:
            stream.seek(offset); data=stream.read(size)
        assert cid(data,cid_bytes(key)[1])==key
        verified_previous.add(key)
        return None if schema=='raw' else decode(data)
    prior_object(baseline['document'])
    for e in events:
        assert original_db.execute('SELECT 1 FROM occurrences WHERE cid=?',(e['occurrence'],)).fetchone() is None
        # Detect an already imported semantic event even if the extraction locator differs.
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
    document=store.put({'schema':'rr/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造',
        'raw':filekeys['02-new-principles.md'],'previous':link(baseline['document']),
        'insertion':filekeys['insertion-manifest.json'],'edition':'2026-10-30 recording and self-reflection',
        'authorship':'source-led editorial proposal; author originals and assistant assessments remain distinct'})
    sources={e['ref']:store.put({'schema':'rr/source@1','namespaces':NS,'ref':e['ref'],
        'occurrence':link(e['occurrence']),'content':link(e['content']),'role':e['role'],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'native message time, not first invention; AI answers are not author statements'}) for e in events}
    quotes=[]; passages=[]; sections=[]
    for section in manifest['sections']:
        local=[]
        for item in section['items']:
            quote=None; source=None
            if 'ref' in item:
                e=byref[item['ref']]; source=sources[item['ref']]
                quote=store.put({'schema':'pkst/statement@0.1','namespaces':NS,
                    'text':e['text'][slice(*item['source_span'])],'force':'quote',
                    'holder':{'kind':'human','id':'archive-owner'} if e['role']=='user' else ACTOR,
                    'evidence':linkset([source]),'asserted_by':ACTOR,'lineage':None,
                    'rr:source_span':{'coordinate':'unicode-scalar-half-open','range':item['source_span']}})
                quotes.append(quote)
            key=store.put({'schema':'rr/passage@1','namespaces':NS,'document':link(document),
                'section_file':section['file'],**{k:v for k,v in item.items() if k!='ref'},
                'source':link(source) if source else None,'quote':link(quote) if quote else None,
                'discussion_basis':linkset([sources[r] for r in item.get('basis_refs',[])])})
            local.append(key); passages.append(key)
        sections.append(store.put({'schema':'rr/section@1','namespaces':NS,'title':section['title'],
            'document':link(document),'raw':filekeys[section['file']],'passages':[link(x) for x in local],
            'placement':'before personal cloud chapter' if len(sections)==0 else 'final appendix after afterword',
            'author_acceptance':False}))
    definitions=[
      ('个人信息采集与分层数据主权','私密原件、事件证据和公共治理知识分别授权；同一Merkle结构不意味着全部公开。'),
      ('记录的威慑约束与学习','把可靠记录连接到事前预期、事中权限和事后反馈；仍需检验，不能保证消除全部伤害。'),
      ('采集设备接棒与主动同意','身份、状态、有效授权和采集视野共同决定接棒；允许缺口而不越权。'),
      ('事件限定的证据协作','从已有权限出发逐步请求证据，处理范围发现、同意、责任和申诉。'),
      ('个人AI缓冲与虚拟体验的条件','个人辅助、行动授权与情绪调节分别设计；宣泄及脑机接口效果仍待验证。'),
      ('对偶体与动态数学体系的形式化边界','给出定义、组合规则、模型与可核查命题；不以比喻替代证明或取消不完备性。'),
      ('不动点最小化与涌现的可检验联系','区分不动点存在、收敛、成本及新能力；明确适用条件与反例。'),
      ('跨层物理与意识解释的验证条件','共同图景需要转化为状态、规律、观测与预测；软件有效不证明统一物理或主观体验。'),
      ('预测权重与制度授权的区别','事实预测、价值取舍和执行权限分别论证，防止反馈和评分制造固化权力。'),
      ('可失败可修订的文明建设方案','分层验证数学、经验、工程和价值选择；每阶段独立有用，保留反例与退出。')]
    all_evidence=list(sources.values())+sections
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset(all_evidence),'asserted_by':ACTOR,'lineage':None}) for label,definition in definitions]
    relations=[]
    def relation(a,b,predicate,scope):
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(a),'to':link(b),
            'evidence':linkset(all_evidence),'asserted_by':ACTOR,'basis':'inferred',
            'scope':scope+'；编辑语义关系，不是已确认的现实因果或作者逐项认可。'}))
    for a,b,scope in [(0,2,'个人数据边界落实到设备协作'),(0,3,'个人授权延伸到事件处理'),
                      (1,4,'记录机制结合个人辅助和情绪调节'),(5,6,'数学形式化检验构造原理'),
                      (6,7,'跨层推论需要每层独立检验'),(8,9,'决策机制需要独立比较'),(9,0,'个人原型提供独立可检验起点')]:
        relation(concepts[a],concepts[b],'explains',scope)
    related=[]
    older=json.loads((C/'new-principles-20261026/report.json').read_bytes())['concepts']
    targets=[(('对偶','范畴'),5),(('不动点','最小化'),6),(('物理','意识'),7),
             (('动态权重',),8),(('隐私','数据主权'),0),(('公共知识',),9)]
    for name,key in older.items():
        value=prior_object(key); label=value.get('label','')
        for words,index in targets:
            if any(word in label for word in words):
                relation(key,concepts[index],'applies-to','对既有主题“'+label+'”增加实施条件或自我反思')
                related.append({'ref':name,'cid':key,'label':label,'new_concept':concepts[index]})
    for key,index in [(baseline['concepts'][1],1),(baseline['concepts'][2],0),(baseline['concepts'][5],9)]:
        prior_object(key); relation(key,concepts[index],'applies-to','从合作反馈延伸到技术约束与理论自我修订')
    external=[store.put({'schema':'rr/external-source@1','namespaces':NS,**item})
              for item in json.loads((OUT/'external-sources.json').read_bytes())]
    change=store.put({'schema':'pkst/change@0.1','operation':'extend','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['INTEGRATION-REQUEST']]),'asserted_by':ACTOR,
        'basis':'explicit','reason':'Integrate pending discussions and append a final self-reflection covering mathematics, fundamental science, society and engineering; preserve previous text.'})
    evolution=[]
    for a,b,reason in [('CAPTURE-PROPOSAL','RECORDING-REPLY','作者补充事前威慑、文明反馈学习及虚拟体验设想'),
                       ('RECORDING-REPLY','EVALUATION-REQUEST','作者要求对社会和工程可行性进行综合评估'),
                       ('EVALUATION-REQUEST','INTEGRATION-REQUEST','作者将评估扩展到数学与基础科学并授权入稿')]:
        evolution.append(store.put({'schema':'rr/discussion-evolution@1','namespaces':NS,
            'from':link(sources[a]),'to':link(sources[b]),'relation':'author-discussion-progression',
            'reason':reason,'recorded_by':ACTOR,'first_invention_claim':False}))
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset([document,change]+sections+list(sources.values())+concepts+relations+external+evolution+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'seven visible discussion records, one chapter and one final appendix','files':files,
            'implementation_files':implementation,'pending':['author review of individual editorial changes'],
            'not_asserted':['new mathematical proof','deployed recording hardware','institutional effectiveness']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'recording and self-reflection editorial extension'},'protocol':link(PROTOCOL)})
    pinned=previous['pinned_sources']+[{'collection':COLLECTION,'root':dossier,'report':str((ARCHIVE/'report.json').relative_to(BASE))}]
    integration=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([x['root'] for x in pinned]),'outputs':[],'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'append current edition and retain all prior source collections'}})
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
        historical={x['$link'] for x in obj.get('parents',[])} if schema=='pkst/snapshot@0.1' else set()
        db.executemany('INSERT INTO edges VALUES(?,?,?)',[(key,t,int(t in historical)) for t in set(links(obj))])
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
    report={'schema':'rr/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
        'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'sections':sections,
        'sources':sources,'occurrences':[e['occurrence'] for e in events],'quotes':quotes,'passages':passages,
        'concepts':concepts,'relations':relations,'discussion_evolution':evolution,'change':change,
        'related_prior_concepts':related,'external_evidence':external,'files':files,'new_native_events':len(events),
        'current_events':count,'new_objects':sorted(new),'closure_blocks':len(members),'closure_counts':counts,
        'verified_previous_link_targets':len(verified_previous),'full_catalog_blocks':total,'text_verification':checks,
        'verification_scope':'new blocks, direct prior link targets, append graph, SQL links, exact sources and edit replay; earlier graph verification inherited'}
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
    tmp=C/'catalog/current.recording-reflection.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
