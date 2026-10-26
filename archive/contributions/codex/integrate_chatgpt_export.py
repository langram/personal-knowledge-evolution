"""Add verified ChatGPT CAR to a copy of the current catalog; stage before activation."""
import hashlib,json,sqlite3,time
from collections import defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
from pkst_codec import Store,cid,cid_bytes,decode,check_sets,link,linkset,links

BASE=Path(__file__).resolve().parents[2];CODEX=BASE/'contributions/codex';ROOT=CODEX/'chatgpt';CAT=CODEX/'catalog'
RUN='20261026-chatgpt-v1'

def main():
    started=time.monotonic();now=datetime.now(timezone.utc).isoformat()
    report=json.loads((ROOT/'import-report-v1.json').read_text(encoding='utf-8'));verification=json.loads((ROOT/'verification-v1.json').read_text(encoding='utf-8'))
    assert verification['status']=='pass' and verification['snapshot']==report['root']
    pointer=json.loads((CAT/'current.json').read_text());baseline=json.loads((CAT/pointer['report']).read_text(encoding='utf-8'))
    assert not any(x['collection']=='chatgpt' for x in baseline['pinned_sources'])
    dest=CAT/'.private'/RUN;dest.mkdir(exist_ok=False);old=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    db=sqlite3.connect(dest/'catalog.sqlite');old.backup(db);old.close();print('Baseline copied; importing verified ChatGPT blocks.',flush=True)
    idx=sqlite3.connect((BASE/report['index']).as_uri()+'?mode=ro',uri=True);stream=(BASE/report['car']).open('rb');store=Store(CAT)
    verified=set();cache={}
    def load(key):
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone():return
        if cid_bytes(key)[1]==0x55:
            path=next((p/(key+'.bin') for p in (ROOT/'raw',CAT/'raw') if (p/(key+'.bin')).is_file()),None)
            if path is None:raise FileNotFoundError(key)
            h=hashlib.sha256()
            with path.open('rb') as f:
                while b:=f.read(4*1024*1024):h.update(b)
            assert h.digest()==cid_bytes(key)[4:];obj=None;offset=0;size=path.stat().st_size
        else:
            row=idx.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
            if row:
                offset,size=row;path=BASE/report['car'];stream.seek(offset);data=stream.read(size)
            else:
                path=CAT/'objects'/(key+'.cbor');data=path.read_bytes();offset=0;size=len(data)
            assert cid(data)==key;obj=decode(data);check_sets(obj)
        verified.add(key);schema=obj['schema'] if obj else 'raw';db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)',(key,schema,str(path.relative_to(BASE)),offset,size))
        if obj is None:return
        current=set(links({k:v for k,v in obj.items() if k!='parents'})) if schema=='pkst/snapshot@0.1' else set(links(obj))
        db.executemany('INSERT INTO edges VALUES(?,?,?)',[(key,k,int(k not in current)) for k in set(links(obj))])
        if schema=='pkst/source@0.1':db.execute('INSERT INTO sources VALUES(?,?,?,?)',(key,obj['platform'],obj['namespace'],obj['native_thread_id']))
        elif schema=='pkst/content@0.1':db.execute('INSERT INTO content VALUES(?,?)',(key,obj['text']))
        elif schema=='pkst/occurrence@0.1':
            t=obj['event_time'];db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)',(key,obj['source']['$link'],obj['native_id'],obj['native_role'],obj['actor_kind'],obj['process_kind'],t['value'],t['format'],json.dumps(t,ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)',[(key,i,x['$link']) for i,x in enumerate(obj['content'])])
        elif schema=='pkst/extraction-record@0.1':
            coordinates={k:obj[k] for k in ('coordinate','start','end','pointer','parser') if k in obj}
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)',(obj['occurrence']['$link'],key,obj['raw']['$link'],json.dumps(coordinates,ensure_ascii=False)))
    members=set();stack=[report['root']]
    while stack:
        key=stack.pop()
        if key in members:continue
        members.add(key);load(key);stack.extend(r[0] for r in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0',(key,)))
    db.executemany('INSERT INTO membership VALUES(?,?)',[('chatgpt',k) for k in members]);db.commit()
    count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0];assert count==baseline['unique_current_events']+report['counts']['messages']
    assert db.execute('SELECT count(*) FROM current_occurrences o WHERE NOT EXISTS(SELECT 1 FROM anchors a WHERE a.occurrence=o.cid)').fetchone()[0]==0
    # Recompute literal long-text candidates including the new source; no semantic relation inferred.
    db.execute('DELETE FROM candidates')
    db.execute('''INSERT INTO candidates SELECT c.cid,count(DISTINCT m.collection),count(DISTINCT o.cid),length(c.text)
      FROM current_content c JOIN parts p ON p.content=c.cid JOIN current_occurrences o ON o.cid=p.occurrence
      JOIN sources s ON s.cid=o.source JOIN membership m ON m.cid=o.cid
      WHERE length(c.text)>=150 AND m.collection IN ('codex-windows','claude-windows','gemini','claude-ai','codex-mac','claude-mac','chatgpt')
      GROUP BY c.cid HAVING count(DISTINCT s.platform)>1 AND count(DISTINCT o.cid)>1''')
    candidates=db.execute('SELECT count(*) FROM candidates').fetchone()[0]
    pinned=baseline['pinned_sources']+[{'collection':'chatgpt','root':report['root'],'report':str((ROOT/'import-report-v1.json').relative_to(BASE)),'report_sha256':hashlib.sha256((ROOT/'import-report-v1.json').read_bytes()).hexdigest()}]
    code=Path(__file__).read_bytes();impl=cid(code,0x55);(CAT/'raw'/(impl+'.bin')).write_bytes(code)
    vr=(ROOT/'verification-v1.json').read_bytes();vkey=cid(vr,0x55);(CAT/'raw'/(vkey+'.bin')).write_bytes(vr)
    act=store.put({'schema':'pkst/activity@0.1','operation':'integrate','recorded_at':now,'actor':{'kind':'ai','id':'codex'},'inputs':linkset([x['root'] for x in pinned]+[vkey]),'outputs':[],
        'implementation':link(impl),'coverage':{'current_events':count,'scope':'baseline plus verified official ChatGPT export','same_text_candidates':candidates,
        'candidate_status':'exact text only; no copy direction, authorship, endorsement or semantic merge','baseline_verification':'prior receipts reused; only new blocks freshly byte-verified'}})
    snapshot=store.put({'schema':'pkst/snapshot@0.1','parents':linkset([pointer['snapshot']]),'roots':linkset([act]),'protocol':link(report['protocol']),
        'coverage':{'recorded_cutoff':now,'scope':'previous pinned sources plus official ChatGPT export','pending':['other AI sources and writings','full semantic extraction'],'local_only':True}})
    stack=[snapshot]
    while stack:
        key=stack.pop()
        if db.execute('SELECT 1 FROM blocks WHERE cid=?',(key,)).fetchone():continue
        load(key);stack.extend(r[0] for r in db.execute('SELECT dst FROM edges WHERE src=?',(key,)))
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON e.dst=b.cid WHERE b.cid IS NULL').fetchone()[0]==0
    degree={r[0]:0 for r in db.execute('SELECT cid FROM blocks')};children=defaultdict(list)
    for a,b in db.execute('SELECT DISTINCT src,dst FROM edges'):children[a].append(b);degree[b]+=1
    q=deque(k for k,v in degree.items() if not v);visited=0
    while q:
        a=q.popleft();visited+=1
        for b in children[a]:
            degree[b]-=1
            if not degree[b]:q.append(b)
    assert visited==len(degree),'Dependency cycle'
    db.commit();assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    counts=dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema',('chatgpt',)))
    result={'schema':'pkst.federated-catalog-report@0.1','run':RUN,'recorded_at':now,'snapshot':snapshot,'baseline_snapshot':pointer['snapshot'],
        'pinned_sources':pinned,'database':str((dest/'catalog.sqlite').relative_to(BASE)),'unique_current_events':count,'current_events_with_anchors':count,
        'current_counts_by_collection':{**baseline['current_counts_by_collection'],'chatgpt':counts},'all_catalog_blocks_including_history_and_federation':visited,
        'freshly_byte_verified_new_blocks':len(verified),'baseline_verification_report':pointer['report'],'exact_long_text_candidate_groups':candidates,
        'query_rule':baseline['query_rule'],'status':'staged; activation after query and source-exclusion verification','elapsed_seconds':round(time.monotonic()-started,3)}
    target=CAT/('report-'+RUN+'.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'staged-pointer.json').write_text(json.dumps({'report':target.name,'snapshot':snapshot,'database':result['database']},indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('pinned_sources','current_counts_by_collection')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
