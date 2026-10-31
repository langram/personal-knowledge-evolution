"""Verifier-first append: retain immutable prior catalog, activate the new copy last."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from prepare import ARCHIVE, BASE, C, OUT, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset
from verify_text import verify

RUN='20261031-ability-cooperation-v1'
COLLECTION='ability-cooperation-20261031'
NS={'acc':'urn:pkst:editorial:ability-cooperation:1'}
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
    document=store.put({'schema':'acc/document@1','namespaces':NS,'title':'新原理：现代科学与人类文明的构造',
        'raw':filekeys['02-new-principles.md'],'previous':link(baseline['document']),
        'revision':filekeys['revision-manifest.json'],'edition':'2026-10-31 fair development, ability diversity and cross-domain cooperation',
        'authorship':'source-led editorial proposal; author originals and assistant assessments remain distinct'})
    sources={e['ref']:store.put({'schema':'acc/source@1','namespaces':NS,'ref':e['ref'],
        'occurrence':link(e['occurrence']),'content':link(e['content']),'role':e['role'],
        'evidence':linkset(e['anchors']),'event_time':e['native_event_time'],
        'boundary':'native message time, not first invention; AI answers are not author statements'}) for e in events}
    historical=json.loads((OUT/'00-historical-sources.json').read_bytes())
    for e in historical:
        obj=prior_object(e['source_object'])
        assert obj['role']==e['role'] and obj['occurrence']['$link']==e['occurrence'] and obj['content']['$link']==e['content']
        content=prior_object(e['content']);assert content['text']==e['text']
        occurrence=prior_object(e['occurrence']);assert occurrence['event_time']['value']==e['time']
        sources[e['ref']]=e['source_object'];byref[e['ref']]=e
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
                    'acc:source_span':{'coordinate':'unicode-scalar-half-open','range':item['source_span']}})
                quotes.append(quote)
            key=store.put({'schema':'acc/passage@1','namespaces':NS,'document':link(document),
                'section_file':section['file'],**{k:v for k,v in item.items() if k!='ref'},
                'source':link(source) if source else None,'quote':link(quote) if quote else None,
                'discussion_basis':linkset([sources[r] for r in item.get('basis_refs',[])])})
            local.append(key); passages.append(key)
        sections.append(store.put({'schema':'acc/section@1','namespaces':NS,'title':section['title'],
            'document':link(document),'raw':filekeys[section['file']],'passages':[link(x) for x in local],
            'placement':next(x['marker'] for x in json.loads((OUT/'revision-manifest.json').read_bytes())['replacements'] if x['file']==section['file']),
            'author_acceptance':{'conceptual_direction':'explicitly accepted in AUTHOR-REVISION','final_wording':False}}))
    definitions=[
      ('公平的发展条件与探索自由','让培养机会、设备、基本生活保障与可支配时间成为可以实际使用的成长条件。'),
      ('能力多样性与互补','允许不同的能力结构存在，通过沟通和合作形成共同能力，不以逼近正态为制度目标。'),
      ('深入研究与跨领域连接','区分任务中的专业深度和连接作用，角色可变化，不固定划分人的类别。'),
      ('可追溯且可接替的协作','保留结论的条件、任务联系与贡献，使协作能够复核和继续，不依赖唯一中介。'),
      ('专业优势与支配权的分离','让任务相关判断发挥作用，同时限制优势自动变成跨领域、永久的支配权。'),
      ('统计假说与制度目标的分离','能力分布保持经验研究地位；公平与合作机制无需以某一分布成立为前提。')]
    all_evidence=list(sources.values())+sections
    concepts=[store.put({'schema':'pkst/concept@0.1','label':label,'definition':definition,
        'evidence':linkset(all_evidence),'asserted_by':ACTOR,'lineage':None}) for label,definition in definitions]
    relations=[]
    def relation(a,b,predicate,scope):
        relations.append(store.put({'schema':'pkst/relation@0.1','predicate':predicate,'from':link(a),'to':link(b),
            'evidence':linkset(all_evidence),'asserted_by':ACTOR,'basis':'inferred',
            'scope':scope+'；编辑语义关系，不是已确认的现实因果或作者逐项认可。'}))
    for a,b,scope in [(0,1,'公平条件支持多样发展和互补'),(1,2,'能力互补具体化为不同任务角色'),
                      (2,3,'跨域分工需要条件传递与可接替的协调'),(3,4,'协作中的影响力要与支配权分开'),
                      (5,1,'将分布前提与能力互补目标分离')]:
        relation(concepts[a],concepts[b],'explains',scope)
    related=[]
    for old_index,new_index,scope in [(0,0,'保留资源参与能力形成的解释，转向公平的发展条件'),
                                    (2,5,'体育项目分布假说保留于历史，不作为制度的必要前提'),
                                    (3,4,'延续培养条件与任务权重分离'),(4,0,'按需保障与实际成长机会相衔接')]:
        key=baseline['concepts'][old_index];value=prior_object(key)
        relation(key,concepts[new_index],'explains',scope)
        related.append({'cid':key,'label':value['label'],'new_concept':concepts[new_index]})
    external=[store.put({'schema':'acc/external-source@1','namespaces':NS,**item})
              for item in json.loads((OUT/'external-sources.json').read_bytes())]
    change=store.put({'schema':'pkst/change@0.1','operation':'revise','from_versions':linkset([baseline['document']]),
        'to_versions':linkset([document]),'evidence':linkset([sources['INTEGRATION-REQUEST'],sources['AUTHOR-REVISION']]),
        'asserted_by':ACTOR,'basis':'explicit','reason':'Present the author-confirmed emphasis on fair development, diverse abilities and cross-domain cooperation; preserve previous text and conceptual revision separately.'})
    revision=json.loads((OUT/'author-revision.json').read_bytes())
    def quote_for(spec):
        ref=spec['ref'];e=byref[ref]
        assert e['text'][slice(*spec['source_span'])]==spec['quote']
        key=store.put({'schema':'pkst/statement@0.1','namespaces':NS,'text':spec['quote'],'force':'quote',
            'holder':{'kind':'human','id':'archive-owner'} if e['role']=='user' else ACTOR,
            'evidence':linkset([sources[ref]]),'asserted_by':ACTOR,'lineage':None,
            'acc:source_span':{'coordinate':'unicode-scalar-half-open','range':spec['source_span']}})
        if key not in quotes:quotes.append(key)
        return key
    before=quote_for(revision['before']);after=quote_for(revision['after']);acceptance_quote=quote_for(revision['acceptance'])
    author_change=store.put({'schema':'pkst/change@0.1','operation':'revise','from_versions':linkset([before]),
        'to_versions':linkset([after]),'evidence':linkset([sources['AUTHOR-REVISION'],acceptance_quote]),
        'asserted_by':ACTOR,'basis':'explicit','reason':revision['scope']})
    acceptance_object=store.put({'schema':'acc/author-acceptance@1','namespaces':NS,
        'change':link(author_change),'source':link(sources['AUTHOR-REVISION']),'quote':link(acceptance_quote),
        'status':'explicit-conceptual-revision','scope':revision['scope'],'retained':revision['retained'],
        'current_emphasis':revision['current_emphasis'],'not_inferred':revision['not_inferred'],
        'final_manuscript_wording_approved':False,'recorded_by':ACTOR})
    timeline=json.loads((OUT/'07-thought-evolution.json').read_bytes());stages={}
    for row in timeline['stages']:
        stages[row['id']]=store.put({'schema':'acc/discussion-stage@1','namespaces':NS,
            'source':link(sources[row['ref']]),'quote':link(quote_for(row)),
            'time':row['time'],'role':row['role'],'interpretation':row['title'],'status':row['status'],
            'recorded_by':ACTOR,'first_invention_claim':False})
    evolution=[]
    for row in timeline['relations']:
        evolution.append(store.put({'schema':'acc/discussion-evolution@1','namespaces':NS,
            'from':link(stages[row['from']]),'to':link(stages[row['to']]),'relation':row['relation'],
            'evidence':linkset([sources[row['evidence_ref']]]) if 'evidence_ref' in row else [],
            'recorded_by':ACTOR,'boundary':'visible discussion progression or explicit author revision, not proof of social causation'}))
    inputs=[raw((ARCHIVE/name).read_bytes()) for name in ['baseline.json','capture.json','text-verification.json']]
    implementation=[{'path':p.name,'raw':link(raw(p.read_bytes()))} for p in sorted(WORK.glob('*.py'))]
    activity=store.put({'schema':'pkst/activity@0.1','namespaces':NS,'operation':'integrate','recorded_at':now,
        'actor':ACTOR,'inputs':linkset(inputs),'outputs':linkset([document,change]+sections+list(sources.values())+concepts+relations+external+list(stages.values())+evolution+[author_change,acceptance_object]+[f['raw']['$link'] for f in files]),
        'implementation':link(raw(Path(__file__).read_bytes())),
        'coverage':{'scope':'six new visible records, two historical sources, two text replacements and explicit author conceptual revision','files':files,
            'implementation_files':implementation,'pending':['author review of individual editorial changes'],
            'not_asserted':['universal normality after resource equalization','fixed genetic specialist/generalist categories','validated cooperation system','institutional effectiveness']}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([baseline['dossier_root']]),'roots':linkset([activity]),
        'coverage':{'recorded_cutoff':events[-1]['time'],'scope':'author-confirmed transition from distribution premises to fair development and ability cooperation'},'protocol':link(PROTOCOL)})
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
    report={'schema':'acc/archive-report@1','status':'verified','recorded_at':now,'snapshot':dossier,
        'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],'document':document,'sections':sections,
        'sources':sources,'occurrences':[e['occurrence'] for e in events],'quotes':quotes,'passages':passages,
        'concepts':concepts,'relations':relations,'discussion_evolution':evolution,'discussion_stages':stages,'change':change,
        'author_revision':author_change,'author_acceptance':acceptance_object,'historical_sources':[e['source_object'] for e in historical],
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
    tmp=C/'catalog/current.ability-cooperation.tmp'
    write_json(tmp,{'report':'report-'+RUN+'.json','snapshot':snapshot,'database':catreport['database']})
    tmp.replace(C/'catalog/current.json')
    write_json(ARCHIVE/'status.json',{'status':'active','snapshot':snapshot,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k:report[k] for k in ['status','snapshot','federated_snapshot','current_events','new_native_events','closure_blocks']},ensure_ascii=False))

if __name__=='__main__': archive()
