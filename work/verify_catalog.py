import sys,json,sqlite3
from pathlib import Path
from collections import defaultdict,deque
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from query_catalog import search
from pkst_codec import decode,cid
pointer=json.loads((base/'contributions/codex/catalog/current.json').read_text())
db=sqlite3.connect((base/pointer['database']).as_uri()+'?mode=ro',uri=True)
expected={'codex-windows':83924,'claude-windows':22403,'gemini':2897,'claude-ai':2132,'semantic-pilot':2}
current_report=json.loads((base/'contributions/codex/catalog'/pointer['report']).read_text(encoding='utf-8'))
if current_report['run']=='20261024T091300Z':
    expected.update({'codex-mac':62449,'claude-mac':26513,'claude-mac-memory':16,'semantic-pairs':20})
for group,count in expected.items():
    actual=db.execute('SELECT count(*) FROM current_occurrences o JOIN membership m ON o.cid=m.cid WHERE m.collection=?',(group,)).fetchone()[0]
    assert actual==count,(group,actual)
current_events=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
source_groups=[name for name in expected if not name.startswith('semantic-')]
source_events={r[0] for name in source_groups for r in db.execute('SELECT o.cid FROM current_occurrences o JOIN membership m ON m.cid=o.cid WHERE m.collection=?',(name,))}
assert current_events==len(source_events)==current_report['unique_current_events']
# Native identity versions in retained parents must remain out of current search.
history_only=db.execute('SELECT count(*) FROM occurrences WHERE cid NOT IN (SELECT cid FROM current_occurrences)').fetchone()[0]
assert history_only>0
query=search(db,'个人知识发展的时空记录',10)
assert len(query)==2 and len({r['occurrence'] for r in query})==2
assert all(r['actor_kind']=='unknown' and r['anchors'] for r in query)
assert not search(db,'PKST-no-such-text-4194c7d7',5)
# Whole dependency graph is topologically sortable, including historical parents.
vertices={r[0] for r in db.execute('SELECT cid FROM blocks')}
degree=dict.fromkeys(vertices,0);adj=defaultdict(list)
for src,dst in db.execute('SELECT src,dst FROM edges'):
    assert src in vertices and dst in vertices
    adj[src].append(dst);degree[dst]+=1
queue=deque(k for k,v in degree.items() if v==0);seen=0
while queue:
    node=queue.popleft();seen+=1
    for dst in adj[node]:
        degree[dst]-=1
        if degree[dst]==0:queue.append(dst)
assert seen==len(vertices)
# Discriminating fixture: same text, different occurrence; exclude history and opaque.
f=sqlite3.connect(':memory:')
f.executescript('''CREATE TABLE current_occurrences(cid,source,native_id,role,actor,event_time,event_format);
CREATE TABLE sources(cid,platform,native_thread_id); CREATE TABLE parts(occurrence,content);
CREATE TABLE current_content(cid,text); CREATE TABLE membership(collection,cid);
CREATE TABLE anchors(occurrence,extraction_record,raw,coordinates_json);''')
f.execute('INSERT INTO sources VALUES(?,?,?)',('s','fixture','thread'))
f.execute('INSERT INTO current_content VALUES(?,?)',('text','相同原话🙂'))
for name in ('event-a','event-b'):
    f.execute('INSERT INTO current_occurrences VALUES(?,?,?,?,?,?,?)',(name,'s',name,'user','unknown',None,'unknown'))
    f.execute('INSERT INTO parts VALUES(?,?)',(name,'text'))
    f.execute('INSERT INTO membership VALUES(?,?)',('fixture',name))
f.execute('INSERT INTO parts VALUES(?,?)',('historical-event','text'))
f.execute('INSERT INTO parts VALUES(?,?)',('event-a','opaque'))
assert len(search(f,'原话'))==2
assert len(search(f,'🙂'))==2
assert search(f,'opaque-secret')==[]
assert search(f,'原话',role='assistant')==[]
bad_candidates=db.execute('''SELECT count(*) FROM (SELECT c.content FROM candidates c
 JOIN parts p ON p.content=c.content JOIN current_occurrences o ON o.cid=p.occurrence JOIN sources s ON s.cid=o.source
 GROUP BY c.content HAVING count(DISTINCT s.platform)<2)''').fetchone()[0]
assert bad_candidates==0
report={'status':'passed','current_event_counts':expected,'unique_current_events':current_events,
    'source_event_union_equals_current_view':True,'cross_platform_candidate_scope_verified':True,
    'history_only_events_excluded':history_only,'acyclic_verified_vertices':seen,
    'paired_request_search':{'results':2,'distinct_occurrences_preserved':True,'actors_unknown':True,'anchors_present':True},
    'fixture_checks':['same-text distinct events','historical event excluded','opaque absent from text search','CJK and emoji','role filter','negative query'],
    'limits':'Search/index and evidence integrity verification; not theory truth, authorship, or user endorsement'}
report_path=base/'reports'/('catalog-verification-'+current_report['run']+'.json')
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
