"""Verifier-first append: retain immutable prior catalog, activate the new copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OUT, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261031-ability-resource-formation-v1'
COLLECTION='ability-resource-formation-20261031'
NS={'rfa':'urn:pkst:editorial:ability-resource-formation:1'}
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
    document=store.put({'schema':'rfa/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造',
        'raw':filekeys['02-new-principles.md'],'previous':link(baseline['document']),
        'revision':filekeys['revision-manifest.json'],'edition':'2026-10-31 resource conditions and ability formation',
        'authorship':'source-led editorial proposal; author originals and assistant assessments remain distinct'})
    sources={e['ref']:store.put({'schema':'rfa/source@1','namespaces':NS,'ref':e['ref'],
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
                    'rfa:source_span':{'coordinate':'unicode-scalar-half-open','range':item['source_span']}})
                quotes.append(quote)
            key=store.put({'schema':'rfa/passage@1','namespaces':NS,'document':link(document),
                'section_file':section['file'],**{k:v for k,v in item.items() if k!='ref'},
                'source':link(source) if source else None,'quote':link(quote) if quote else None,
                'discussion_basis':linkset([sources[r] for r in item.get('basis_refs',[])])})
            local.append(key); passages.append(key)
        sections.append(store.put({'schema':'rfa/section@1','namespaces':NS,'title':section['title'],
            'document':link(document),'raw':filekeys[section['file']],'passages':[link(x) for x in local],
            'placement':next(x['marker'] for x in json.loads((OUT/'revision-manifest.json').read_bytes())['replacements'] if x['file']==section['file']),
            'author_acceptance':False}))
    definitions=[
      ('资源条件参与能力形成','教育训练与机会不仅影响绩效，也可能参与形成已习得能力；须区分初始条件与成长过程。'),
      ('绩效分布与反事实能力分布','现行制度的结果分布不能单独识别资源条件改变后的能力分布，也不证明后者必然正态。'),
      ('资源依赖与体育能力分布的比较假说','跑跳与高尔夫、跳伞的资源依赖和分布比较是作者提出的待检验预测，须控制群体选择与测量。'),
      ('能力培养保障与决策权重分离','扩大培养条件的可获得性，保留知识技能积累，同时限制优势无边界地转换为支配权。'),
      ('需求差异与按需保障','不从职业绩效推断需要，不以符合预设分布为获得合理支持的前提。')]
    all_evidence=list(sources.values())+sections
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset(all_evidence),'asserted_by':ACTOR,'lineage':None}) for label,definition in definitions]
    relations=[]
    def relation(a,b,predicate,scope):
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(a),'to':link(b),
            'evidence':linkset(all_evidence),'asserted_by':ACTOR,'basis':'inferred',
            'scope':scope+'；编辑语义关系，不是已确认的现实因果或作者逐项认可。'}))
    for a,b,scope in [(0,1,'资源参与形成能力，因而需区分观察与反事实'),
                      (1,2,'将一般因果主张具体化为可检验的体育比较'),
                      (0,3,'培养条件与权重规则需要同时改进'),
                      (3,4,'能力判断与个人生活保障分别安排')]:
        relation(concepts[a],concepts[b],'explains',scope)
    related=[]
    key=baseline['concepts'][2]
    value=prior_object(key)
    for index in [0,1,3,4]:
        relation(key,concepts[index],'explains','对第十版需求能力与支配权主题补入作者的成长条件解释')
        related.append({'cid':key,'label':value['label'],'new_concept':concepts[index]})
    external=[store.put({'schema':'rfa/external-source@1','namespaces':NS,**item})
              for item in json.loads((OUT/'external-sources.json').read_bytes())]
    change=store.put({'schema':'pkst/change@0.1','operation':'revise','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['ABILITY-RESOURCE-REPLY']]),'asserted_by':ACTOR,
        'basis':'explicit','reason':'Revise one dynamic-weight section with the author clarification on resource-dependent ability formation; retain exact originals and the previous edition.'})
    evolution=[]
    earlier=baseline['sources']['CIVILIZATION-REPLY'];prior_object(earlier)
    for start,end,reason in [(earlier,sources['ABILITY-RESOURCE-REPLY'],'作者从第十版的分布主张进一步说明资源如何塑造能力'),
           (sources['EDITION-TEN-RESPONSE'],sources['ABILITY-RESOURCE-REPLY'],'作者回应AI对分布论证的限定，要求补入资源形成机制')]:
        evolution.append(store.put({'schema':'rfa/discussion-evolution@1','namespaces':NS,
            'from':link(start),'to':link(end),'relation':'visible-discussion-progression',
            'reason':reason,'recorded_by':ACTOR,'first_invention_claim':False}))
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset([document,change]+sections+list(sources.values())+concepts+relations+external+evolution+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'two visible discussion records and one reversible section revision','files':files,
            'implementation_files':implementation,'pending':['author review of individual editorial changes'],
            'not_asserted':['universal normality after resource equalization','all skewness caused by capital','validated cross-sport distribution ordering','institutional effectiveness']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'author clarification on resource conditions and ability formation'},'protocol':link(PROTOCOL)})
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
    report={'schema':'rfa/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
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
    tmp=C/'catalog/current.ability-resource-formation.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
