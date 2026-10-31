"""Verifier-first append: retain immutable prior catalog, activate the new copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OUT, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261031-civilization-self-governance-v1'
COLLECTION='civilization-self-governance-20261031'
NS={'csg':'urn:pkst:editorial:civilization-self-governance:1'}
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
    document=store.put({'schema':'csg/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造',
        'raw':filekeys['02-new-principles.md'],'previous':link(baseline['document']),
        'insertion':filekeys['insertion-manifest.json'],'edition':'2026-10-31 civilization self-governance and institutional exploration',
        'authorship':'source-led editorial proposal; author originals and assistant assessments remain distinct'})
    sources={e['ref']:store.put({'schema':'csg/source@1','namespaces':NS,'ref':e['ref'],
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
                    'csg:source_span':{'coordinate':'unicode-scalar-half-open','range':item['source_span']}})
                quotes.append(quote)
            key=store.put({'schema':'csg/passage@1','namespaces':NS,'document':link(document),
                'section_file':section['file'],**{k:v for k,v in item.items() if k!='ref'},
                'source':link(source) if source else None,'quote':link(quote) if quote else None,
                'discussion_basis':linkset([sources[r] for r in item.get('basis_refs',[])])})
            local.append(key); passages.append(key)
        sections.append(store.put({'schema':'csg/section@1','namespaces':NS,'title':section['title'],
            'document':link(document),'raw':filekeys[section['file']],'passages':[link(x) for x in local],
            'placement':next(x['marker'] for x in json.loads((OUT/'insertion-manifest.json').read_bytes())['insertions'] if x['file']==section['file']),
            'author_acceptance':False}))
    definitions=[
      ('统一基本规则与制度演化分叉','在保护与责任的共同边界内，比较多种制度路径及其成本，不要求所有具体规则一致。'),
      ('虚拟社会实验室与现实反馈','把文化体验、生成式模拟与真实试点区分，并通过授权观察和失败反馈校准。'),
      ('需求能力与支配权的分离','按需保障、任务能力判断和基本权利分别安排；不由分布形状直接推导不存在支配。'),
      ('账本安全与实际行为安全的区别','内容核验、共识、身份授权和执行约束采用各自适用的机制，不能普遍套用过半算力条件。'),
      ('互惠正负反馈的理想模型边界','两个方向帮助识别机制，现实互动混合合作、背叛、误判与修复。'),
      ('自愿表达与社会信息质量','保护和正向回报有望提高真实分享；仍需因果识别、模型检验与参与者反应分析。'),
      ('技术与文明的双重可靠性','技术能力增长需要与共同决策、协调和自我约束能力相匹配。'),
      ('文明整体智能与个人主体性','借鉴生物体的信息反馈与协作，不把个人化为失去选择的组成部分。')]
    all_evidence=list(sources.values())+sections
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset(all_evidence),'asserted_by':ACTOR,'lineage':None}) for label,definition in definitions]
    relations=[]
    def relation(a,b,predicate,scope):
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(a),'to':link(b),
            'evidence':linkset(all_evidence),'asserted_by':ACTOR,'basis':'inferred',
            'scope':scope+'；编辑语义关系，不是已确认的现实因果或作者逐项认可。'}))
    for a,b,scope in [(0,1,'并行制度探索连接虚拟与现实试验'),(2,3,'防止权力积累与防止恶意篡改需要不同条件'),
                      (4,5,'真实互惠互动需要受保护的信息与修复通道'),(5,6,'信息质量与文明自我治理能力相关'),
                      (6,7,'文明可靠性需要与个人参与主体性相容'),(1,6,'模拟通过现实反馈检验制度可靠性')]:
        relation(concepts[a],concepts[b],'explains',scope)
    related=[]
    older=json.loads((C/'new-principles-20261026/report.json').read_bytes())['concepts']
    targets=[(('动态权重',),2),(('隐私','数据主权'),5),(('公共知识',),4),
             (('科幻','游戏'),1),(('文明','合作'),6)]
    for name,key in older.items():
        value=prior_object(key); label=value.get('label','')
        for words,index in targets:
            if any(word in label for word in words):
                relation(key,concepts[index],'applies-to','对既有主题“'+label+'”增加制度探索与文明自我治理的论述')
                related.append({'ref':name,'cid':key,'label':label,'new_concept':concepts[index]})
    for key,index in [(baseline['concepts'][0],5),(baseline['concepts'][8],2),(baseline['concepts'][9],0)]:
        prior_object(key); relation(key,concepts[index],'applies-to','从第九版数据主权与理论反思延伸到自愿分享、制度探索和权重边界')
    external=[store.put({'schema':'csg/external-source@1','namespaces':NS,**item})
              for item in json.loads((OUT/'external-sources.json').read_bytes())]
    change=store.put({'schema':'pkst/change@0.1','operation':'extend','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['CIVILIZATION-REPLY']]),'asserted_by':ACTOR,
        'basis':'explicit','reason':'Integrate the author response on institutional exploration, mixed reciprocal feedback, voluntary information and civilization self-governance; preserve all prior book text.'})
    evolution=[]
    for a,b,reason in [('RESEARCH-REQUEST','RESEARCH-RESULT','作者委托三轮独立探索，AI交付可审查的研究结果'),
                       ('RESEARCH-RESULT','CIVILIZATION-REPLY','作者回应分叉与权重问题，补充混合互惠模型和文明自我治理，并授权入书')]:
        evolution.append(store.put({'schema':'csg/discussion-evolution@1','namespaces':NS,
            'from':link(sources[a]),'to':link(sources[b]),'relation':'visible-discussion-progression',
            'reason':reason,'recorded_by':ACTOR,'first_invention_claim':False}))
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset([document,change]+sections+list(sources.values())+concepts+relations+external+evolution+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'three visible discussion records, one chapter and three section insertions','files':files,
            'implementation_files':implementation,'pending':['author review of individual editorial changes'],
            'not_asserted':['universal normality of needs or ability','universal honest-majority safety','validated social simulator','institutional effectiveness']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'author response and civilization self-governance editorial extension'},'protocol':link(PROTOCOL)})
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
    report={'schema':'csg/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
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
    tmp=C/'catalog/current.civilization-self-governance.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
