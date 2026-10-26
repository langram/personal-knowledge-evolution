"""Exact long-text matching identifies review candidates, never copy direction or adoption."""
import json,sqlite3,sys
from pathlib import Path
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import decode,cid,encode
codex=base/'contributions/codex';peer=base/'contributions/claude'
db=sqlite3.connect((codex/'.private/windows-evidence.index.sqlite').as_uri()+'?mode=ro',uri=True)
matches={}
for p in (peer/'objects').glob('*.cbor'):
    # Only content objects: no projections or opaque bodies enter semantic matching.
    o=decode(p.read_bytes())
    if o.get('schema')!='pkst/content@0.1' or len(o['text'])<150:continue
    found=db.execute('SELECT offset,size FROM blocks WHERE cid=? AND schema=?',(p.stem,'pkst/content@0.1')).fetchone()
    if found:matches[p.stem]={'content':p.stem,'characters':len(o['text']),'text':o['text'],'claude':[],'codex':[]}
def occurrence_ref(key,o):
    return {'occurrence':key,'source':o['source']['$link'],'native_id':o['native_id'],
            'native_role':o['native_role'],'actor_kind':o['actor_kind'],'event_time':o['event_time']}
for p in (peer/'objects').glob('*.cbor'):
    o=decode(p.read_bytes())
    if o.get('schema')!='pkst/occurrence@0.1':continue
    for part in o['content']:
        if part['$link'] in matches:matches[part['$link']]['claude'].append(occurrence_ref(p.stem,o))
with (codex/'.private/windows-evidence.car').open('rb') as car:
    for key,offset,size in db.execute("SELECT cid,offset,size FROM blocks WHERE schema='pkst/occurrence@0.1'"):
        car.seek(offset);o=decode(car.read(size))
        for part in o['content']:
            if part['$link'] in matches:matches[part['$link']]['codex'].append(occurrence_ref(key,o))
items=[]
for item in matches.values():
    if not item['claude'] or not item['codex']:continue
    item.update(predicate='propagation-candidate',basis='inferred',method='exact unchanged content CID, length>=150 Unicode characters',
                direction='unknown',user_adoption='unknown',review_status='unreviewed')
    items.append(item)
items.sort(key=lambda i:i['content'])
out=base/'coordination/.private';out.mkdir(exist_ok=True,parents=True)
(out/'cross-source-candidates.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in items),encoding='utf-8')
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'matched_distinct_long_texts':len(items),
        'claude_occurrences':sum(len(i['claude']) for i in items),'codex_occurrences':sum(len(i['codex']) for i in items),
        'method':'Exact PKST content CID; >=150 characters; plain text only',
        'limitations':['Same text can be a shared template or quotation','No original author or copy direction inferred',
                      'No user adoption inferred','Candidate table is derived and awaits semantic review'],
        'private_candidates':'coordination/.private/cross-source-candidates.jsonl'}
(base/'reports/cross-source-candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
