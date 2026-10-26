"""Compare every imported field with the captured document, plus edge fixtures."""
import json, sys, sqlite3, hashlib, re
from collections import Counter
from pathlib import Path, PurePosixPath
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import decode,encode,cid,loads
from import_gemini_takeout import convert
root=base/'contributions/codex/gemini'
report=json.loads((root/'.private/gemini-evidence.report.json').read_text(encoding='utf-8'))
document=json.loads((root/'raw'/(report['document_raw']+'.bin')).read_bytes())
anchors=json.loads((root/report['anchors_manifest']).read_text(encoding='utf-8'))
db=sqlite3.connect((root/'.private/gemini-evidence.index.sqlite').as_uri()+'?mode=ro',uri=True)
car=(root/'.private/gemini-evidence.car').open('rb')
def get(key):
    offset,size=db.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
    car.seek(offset);b=car.read(size);assert cid(b)==key;return decode(b)
def resolve(p):
    current=document
    for part in p.lstrip('/').split('/'):
        current=current[int(part)] if isinstance(current,list) else current[part.replace('~1','/').replace('~0','~')]
    return current
counts=Counter()
for row in anchors['checks']:
    original=resolve(row['pointer']);occ=get(row['occurrence']);content=get(row['content'])
    assert occ['locator']=={'raw':{'$link':report['document_raw']},'coordinate':'json-pointer','pointer':row['pointer']}
    assert occ['native_id'] is None and occ['native_parent_ids'] is None
    if row['kind']=='Prompted':
        assert original.startswith('Prompted ') and content['text']==original[9:]
        assert occ['actor_kind']=='unknown'
    else:
        assert json.loads(content['text'])==original
        if row['kind']=='safeHtmlItem': assert occ['event_time']['value'] is None
    counts[row['kind']]+=1
assert len(anchors['checks'])==2897
assert counts['Prompted']==1427 and counts['safeHtmlItem']==1443
for key,offset,size in db.execute("SELECT cid,offset,size FROM blocks WHERE schema='pkst/extraction-record@0.1'"):
    er=get(key);occ=get(er['occurrence']['$link'])
    assert er['pointer']==occ['locator']['pointer'];resolve(er['pointer'])
for key,offset,size in db.execute("SELECT cid,offset,size FROM blocks WHERE schema='pkst/block-reference@0.1'"):
    br=get(key);occ=get(br['occurrence']['$link'])
    assert br['document_pointer']+br['pointer']==occ['locator']['pointer']
manifest=[json.loads(line) for line in next((root/'.private').glob('members-*.jsonl')).read_text(encoding='utf-8').splitlines()]
by_name={}
for m in manifest:by_name.setdefault(m['member_name'],set()).add(m['raw_cid'])
unmatched=[]
for ref in anchors['attachments']:
    assert PurePosixPath(ref['member_name']).name==resolve(ref['pointer'])
    expected=by_name.get(ref['member_name'],set())
    assert sorted(expected)==ref['raw_candidates']
    if not expected:
        # Filename family is a diagnostic hypothesis only, never a promoted attachment link.
        name=PurePosixPath(ref['member_name']).name
        token=re.search(r'-([0-9a-f]{16})(?:\.|$)',name)
        candidate_names=[n for n in by_name if token and token.group(1) in PurePosixPath(n).name]
        unmatched.append(dict(pointer=ref['pointer'],export_reference=ref['member_name'],
                              candidate_members=candidate_names,status='unverified-filename-family' if candidate_names else 'no-candidate'))
(root/'.private/attachment-name-candidates.json').write_text(json.dumps(unmatched,ensure_ascii=False,indent=2),encoding='utf-8')

def probe(rows,raw='bafkreideukoih3truyiguj5yybmqd2e4hbuwjuqjtpd2f33lop7iceqoxa',members=()):
    objects={}
    def put(o):
        key=cid(encode(o));objects[key]=o;return key
    outcome=convert(rows,raw,'Takeout/Gemini/activity.json',members,put)
    return objects,outcome
fixture={'header':'Gemini Apps','title':'Prompted A\r\n甲','time':'2026-10-23T03:55:15.980Z',
         'details':[{'url':'https://gemini.google.com/app/abc'}],
         'safeHtmlItem':[{'html':'<p>A &amp; B</p>'},{'html':'<p>Second</p>'}]}
a,ar=probe([fixture,fixture]);b,br=probe([fixture,fixture]);assert a==b
occ=[(k,v) for k,v in a.items() if v['schema']=='pkst/occurrence@0.1']
assert len(occ)==6 and len({k for k,v in occ})==6
assert all(v['native_parent_ids'] is None for k,v in occ)
assert all(v['event_time']['value'] is None for k,v in occ if v['native_role']=='safeHtmlItem')
other,_=probe([fixture,fixture],cid(b'other capture',0x55))
assert not {k for k,v in occ}&{k for k,v in other.items() if v['schema']=='pkst/occurrence@0.1'}
missing={**fixture,'attachedFiles':['missing.txt']};o,res=probe([missing]);assert res[2]['attachment:missing']==1
ambiguous={**fixture,'details':fixture['details']+[{'url':'https://gemini.google.com/app/def'}]}
o,res=probe([ambiguous]);assert len(res[3])==1 and len(res[4])==0
members=[dict(status='captured',member_name='Takeout/Gemini/missing.txt',raw_cid=cid(x,0x55)) for x in [b'a',b'b']]
o,res=probe([missing],members=members);assert res[2]['attachment:ambiguous']==1
try:loads(b'{"x":1,"x":2}')
except ValueError:pass
else:raise AssertionError('Duplicate JSON key accepted')
summary={'status':'passed','scope':'all real field anchors plus discriminating fixtures; independent peer review separate',
    'occurrences_checked':len(anchors['checks']),'field_counts':dict(counts),'extraction_records_checked':2897,
    'block_references_checked':2897,'attachment_references_checked':len(anchors['attachments']),
    'exact_filename_unmatched':len(unmatched),'unmatched_unique_names':len({r['export_reference'] for r in unmatched}),
    'unmatched_with_unverified_name_family':sum(bool(r['candidate_members']) for r in unmatched),
    'fixtures':['repeat-idempotence','same-text-distinct-events','capture-local-fallback','unknown-response-times-and-parentage',
                'missing-attachment','ambiguous-attachment','ambiguous-conversation','duplicate-json-key-rejected'],
    'known_conversation_URL_ids':len({u['url'] for row in document for u in row.get('details',[])})}
(base/'reports/gemini-evidence-verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
