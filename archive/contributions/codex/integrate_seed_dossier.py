"""Append one reviewed local dossier to the derived PKST catalog, preserving the baseline."""
import argparse,hashlib,json,sqlite3,time
from collections import Counter,defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
from pkst_codec import Store,cid,cid_bytes,decode,encode,links,link,linkset,check_sets

BASE=Path(__file__).resolve().parents[2]
CODEX=BASE/'contributions/codex'
OUT=CODEX/'civilization-seed-20261025'
DOC=BASE/'dossiers/2026-10-25-seed'
RUN='20261025-seed-v1'
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
ACTOR={'kind':'ai','id':'codex'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',default=RUN);ap.add_argument('--amend',action='store_true');args=ap.parse_args()
    run=args.run
    if not run.replace('-','').isalnum():raise ValueError('Invalid run name')
    started=time.monotonic();now=datetime.now(timezone.utc).isoformat()
    capture=json.loads((OUT/'capture.json').read_text(encoding='utf-8'))
    pointer=json.loads((CODEX/'catalog/current.json').read_text())
    if not args.amend and pointer!=capture['prior_catalog']:raise ValueError('Catalog changed after evidence selection')
    prior_dossier=json.loads((OUT/'report.json').read_text(encoding='utf-8')) if args.amend else None
    baseline=json.loads((CODEX/'catalog'/pointer['report']).read_text(encoding='utf-8'))
    dest=CODEX/'catalog/.private'/run;dest.mkdir(exist_ok=False)
    old=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    db=sqlite3.connect(dest/'catalog.sqlite');old.backup(db);old.close()
    store=Store(OUT);catalogstore=Store(CODEX/'catalog')
    verified=set()
    def raw_put(data):
        key=cid(data,0x55);path=OUT/'raw'/(key+'.bin')
        if path.exists():
            if path.read_bytes()!=data:raise ValueError('Raw collision')
        else:path.write_bytes(data)
        return key
    def read(key):
        row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
        if row:
            path=BASE/row[0]
            with path.open('rb') as f:f.seek(row[1]);data=f.read(row[2])
        else:
            extension='.bin' if cid_bytes(key)[1]==0x55 else '.cbor'
            folder='raw' if extension=='.bin' else 'objects'
            path=next((root/folder/(key+extension) for root in [OUT,CODEX/'catalog'] if (root/folder/(key+extension)).is_file()),None)
            if path is None:raise FileNotFoundError(key)
            data=path.read_bytes()
            row=(str(path.relative_to(BASE)),0,len(data))
        if cid(data,cid_bytes(key)[1])!=key:raise ValueError('Content hash mismatch '+key)
        verified.add(key)
        if cid_bytes(key)[1]==0x55:return None,row,data
        obj=decode(data);check_sets(obj)
        return obj,row,data
    def load(key):
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone():return
        obj,row,data=read(key);schema=obj['schema'] if obj is not None else 'raw'
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(key,schema,*row))
        if obj is None:return
        current=set(links({k:v for k,v in obj.items() if k!='parents'})) if schema=='pkst/snapshot@0.1' else set(links(obj))
        db.executemany('INSERT INTO edges VALUES(?,?,?)',[(key,k,int(k not in current)) for k in set(links(obj))])
        if schema=='pkst/source@0.1':db.execute('INSERT INTO sources VALUES(?,?,?,?)',(key,obj['platform'],obj['namespace'],obj['native_thread_id']))
        elif schema=='pkst/content@0.1':db.execute('INSERT INTO content VALUES(?,?)',(key,obj['text']))
        elif schema=='pkst/occurrence@0.1':
            t=obj['event_time'];db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(key,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)',[(key,i,p['$link']) for i,p in enumerate(obj['content'])])
        elif schema=='pkst/extraction-record@0.1':
            coords={k:obj[k] for k in ['coordinate','start','end','pointer','parser'] if k in obj}
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],key,obj['raw']['$link'],json.dumps(coords,ensure_ascii=False)))
    files=[]
    for p in sorted(DOC.glob('*.md')):
        if p.name=='12-archive-receipt.md':continue
        data=p.read_bytes();key=raw_put(data)
        files.append({'path':str(p.relative_to(BASE)),'raw':link(key),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                      'authorship':'native transcript projection with editorial headings' if p.name=='01-originals.md' else 'codex editorial draft; not user verbatim or adopted policy'})
    research=[]
    researchroot=Path('C:/Users/langr/Dev/civic-neural-commons')
    for name in ['docs/CHARTER.md','docs/CURRENT.md','theory/FOUNDATIONS.md','reports/E002-REVIEW.md']:
        p=researchroot/name;data=p.read_bytes();key=raw_put(data)
        research.append({'source_path':str(p),'raw':link(key),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'handling':'read-only research material, not a new conversation occurrence'})
    impl=raw_put(Path(__file__).read_bytes());profile=raw_put((OUT/'PROFILE.md').read_bytes());capturekey=raw_put((OUT/'capture.json').read_bytes())
    roots=json.loads((OUT/'pending-roots.json').read_text())
    activity=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([capturekey,profile]+[x['raw']['$link'] for x in research]),'outputs':linkset(roots+[x['raw']['$link'] for x in files]),
        'implementation':link(impl),'coverage':{'scope':'bounded discussion, prior evidence and editorial dossier','files':files,'research_materials':research,
        'new_occurrences':len(capture['recent']),'reused_occurrences':len(capture['history']),'statement_count':len(capture['quotes']),
        'review':'Codex source and structural validation; no new Claude review or user endorsement','privacy':'local-only'}})
    dossier=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([prior_dossier['snapshot']]) if args.amend else [],'roots':linkset([activity]),'protocol':link(PROTOCOL),
        'coverage':{'recorded_cutoff':now,'event_cutoff':capture['cutoff_native_time'],'scope':'explicit message window and five selected prior records',
        'missing':['ChatGPT official export','full corpus semantic extraction'],'interpretations':'editorial candidates; user text and assistant corrections separate'}})
    members=set();stack=[dossier]
    while stack:
        key=stack.pop()
        if key in members:continue
        members.add(key);load(key)
        stack.extend(r[0] for r in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(key,)))
    # Recheck every referenced dossier block, including reused evidence and original raw bytes.
    for key in members:read(key)
    if args.amend:db.execute('DELETE FROM membership WHERE collection=?',('civilization-seed-20261025',))
    db.executemany('INSERT INTO membership VALUES(?,?)',[('civilization-seed-20261025',k) for k in members])
    count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count==baseline['unique_current_events']+(0 if args.amend else len(capture['recent']))
    assert db.execute('SELECT count(*) FROM current_occurrences o WHERE NOT EXISTS(SELECT 1 FROM anchors a WHERE a.occurrence=o.cid)').fetchone()[0]==0
    pinned=[p for p in baseline['pinned_sources'] if p['collection']!='civilization-seed-20261025']+[{'collection':'civilization-seed-20261025','root':dossier,'report':'contributions/codex/civilization-seed-20261025/report.json'}]
    integrated=catalogstore.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':ACTOR,
        'inputs':linkset([p['root'] for p in pinned]),'outputs':[],'implementation':link(impl),
        'coverage':{'scope':'baseline catalog plus bounded local dossier','current_events':count,'baseline_snapshot':pointer['snapshot'],
            'verification_scope':'baseline receipt reused; dossier closure byte-verified; full graph references and acyclicity checked',
            'candidate_scan':'prior 10 exact text groups retained within prior source scan scope; this addition not rescanned for propagation'}})
    snapshot=catalogstore.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([integrated]),'protocol':link(PROTOCOL),
        'coverage':{'recorded_cutoff':now,'local_only':True,'scope':'previous collections and new dossier','pending':['ChatGPT official export','full semantic graph','cloud service deployment','public release']}})
    stack=[snapshot]
    while stack:
        k=stack.pop()
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(k,)).fetchone():continue
        load(k);stack.extend(x[0] for x in db.execute('SELECT dst FROM edges WHERE src=?',(k,)))
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON e.dst=b.cid WHERE b.cid IS NULL').fetchone()[0]==0
    # An actual graph check, not just a parent-order check.
    indegree={x[0]:0 for x in db.execute('SELECT cid FROM blocks')};children=defaultdict(list)
    for a,b in db.execute('SELECT DISTINCT src,dst FROM edges'):children[a].append(b);indegree[b]+=1
    queue=deque(k for k,v in indegree.items() if v==0);visited=0
    while queue:
        a=queue.popleft();visited+=1
        for b in children[a]:
            indegree[b]-=1
            if indegree[b]==0:queue.append(b)
    assert visited==len(indegree),'Reference cycle'
    db.commit();assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',('civilization-seed-20261025',)))
    report={'schema':'pkst.seed-dossier-report@0.1','recorded_at':now,'snapshot':dossier,'federated_snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],
        'native_new_events':len(capture['recent']),'reused_prior_events':len(capture['history']),'verbatim_statements':len(capture['quotes']),
        'concepts':len(capture['concepts']),'relations':len(capture['relations']),'assistant_interpretation_changes':len(capture['changes']),
        'dossier_closure_blocks':len(members),'dossier_closure_counts':counts,'freshly_byte_verified_blocks':len(verified),
        'full_reference_graph_nodes':visited,'new_unique_current_events':count,'files':files,'research_materials':research,
        'status':'source anchors and quotation spans require separate verifier before final receipt','public_release':False,
        'elapsed_seconds':round(time.monotonic()-started,3)}
    if args.amend:
        (OUT/('report-before-'+run+'.json')).write_bytes((OUT/'report.json').read_bytes())
        report['amendment']='Readability correction to timeline Markdown table; source events and semantic objects unchanged.'
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    pinned[-1]['report_sha256']=hashlib.sha256((OUT/'report.json').read_bytes()).hexdigest()
    catalogreport={'schema':'pkst.federated-catalog-report@0.1','run':run,'recorded_at':now,'snapshot':snapshot,'pinned_sources':pinned,
        'database':str((dest/'catalog.sqlite').relative_to(BASE)),'unique_current_events':count,'current_events_with_anchors':count,
        'current_counts_by_collection':{**baseline['current_counts_by_collection'],'civilization-seed-20261025':counts},
        'all_catalog_blocks_including_history_and_federation':visited,'verification_scope':report['status'],
        'baseline_verification_report':pointer['report'],'freshly_byte_verified_blocks':len(verified),
        'exact_long_text_candidate_groups':baseline['exact_long_text_candidate_groups'],'candidate_scan_scope':'unchanged baseline source collections',
        'query_rule':baseline['query_rule'],'status':'staged; activation after independent source verification'}
    (CODEX/'catalog'/('report-'+run+'.json')).write_text(json.dumps(catalogreport,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'staged-pointer.json').write_text(json.dumps({'report':'report-'+run+'.json','snapshot':snapshot,'database':catalogreport['database']},indent=2),encoding='utf-8')
    db.close()
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','research_materials')},ensure_ascii=False))

if __name__=='__main__':main()
