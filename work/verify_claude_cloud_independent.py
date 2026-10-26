"""Independent field-by-field audit of the current Claude.ai snapshot.

Uses only the Codex codec/CAR reader and raw export, never the peer importer.
History parent closure is hash checked but does not count as current coverage.
"""
import argparse,hashlib,json,re,sqlite3,sys
from collections import Counter,defaultdict
from pathlib import Path
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import cid,encode,decode,loads,links,link,cid_bytes
from pkst_car import inspect_car
ap=argparse.ArgumentParser();ap.add_argument('--summary',required=True);args=ap.parse_args()
summary=loads(Path(args.summary).read_bytes());peer=base/'contributions/claude';car_path=base/summary['car']
assert hashlib.sha256(car_path.read_bytes()).hexdigest()==summary['car_sha256']
index=base/'contributions/codex/.private'/('claude-ai-audit-'+summary['run']+'-'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:10]+'.sqlite')
verification=inspect_car(car_path,peer/'raw',index)
db=sqlite3.connect(index);car=car_path.open('rb')
def get(key):
    row=db.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone()
    if not row:raise KeyError(key)
    car.seek(row[0]);raw=car.read(row[1]);assert cid(raw)==key;return decode(raw)
root=get(summary['snapshot']);assert root['schema']=='pkst/snapshot@0.1'
assert root['protocol']['$link']=='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
current={};stack=list(links(root['roots']))
while stack:
    key=stack.pop()
    if key in current or cid_bytes(key)[1]==0x55:continue
    obj=get(key);current[key]=obj;stack.extend(links(obj))
documents={}
def document(raw_key):
    if raw_key not in documents:documents[raw_key]=loads((peer/'raw'/(raw_key+'.bin')).read_bytes())
    return documents[raw_key]
def at(doc,ptr):
    if ptr=='':return doc
    assert ptr.startswith('/')
    for token in ptr[1:].split('/'):
        token=token.replace('~1','/').replace('~0','~')
        doc=doc[int(token)] if isinstance(doc,list) else doc[token]
    return doc
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def timestamp(value):
    if value is None:return dict(value=None,format='unknown',precision='unknown',zone_known=False,unit=None)
    m=re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.(\d+))?(?:Z|[+-]\d\d:\d\d)',value);assert m
    digits=len(m[1] or '')
    return dict(value=value,format='rfc3339',precision='second' if digits==0 else 'millisecond' if digits<=3 else 'microsecond' if digits<=6 else 'unknown',zone_known=True,unit=None)
occurrences={k:o for k,o in current.items() if o['schema']=='pkst/occurrence@0.1'}
ers=defaultdict(list);blocks=defaultdict(list)
for key,obj in current.items():
    if obj['schema']=='pkst/extraction-record@0.1':ers[obj['occurrence']['$link']].append(obj)
    if obj['schema']=='pkst/block-reference@0.1':blocks[obj['occurrence']['$link']].append(obj)
count=Counter();message_ids=set();types=Counter()
for key,occ in occurrences.items():
    assert len(ers[key])==1
    er=ers[key][0];assert er['coordinate']=='json-pointer' and 'start' not in er and 'end' not in er
    raw_key=er['raw']['$link'];doc=document(raw_key);original=at(doc,er['pointer'])
    source=get(occ['source']['$link']);assert source['namespace']=='owner-claude-account'
    role=occ['native_role'];count[role]+=1
    assert occ['process_kind']=='unknown'
    if source['platform']=='claude-ai':
        assert role==original['sender'] and occ['native_id']==original['uuid'] and occ['locator'] is None
        expected_actor='ai' if role=='assistant' else 'tool' if original['content'] and all(x.get('type')=='tool_result' for x in original['content']) else 'unknown'
        assert occ['actor_kind']==expected_actor
        assert occ['native_parent_ids']==[original['parent_message_uuid']]
        assert occ['event_time']==timestamp(original['created_at'])
        conv=doc[int(er['pointer'].split('/')[1])]
        assert source['native_thread_id']==conv['uuid']
        message_ids.add((conv['uuid'],original['uuid']))
    else:
        assert occ['actor_kind']=='unknown' and occ['native_parent_ids'] is None
        if role.startswith('material:'):
            assert occ['native_id']==original['uuid'] and occ['locator'] is None
            assert occ['event_time']==timestamp(original['created_at'])
        else:
            assert role.startswith('derived-memory:') and occ['native_id'] is None
            assert occ['locator']=={'raw':link(raw_key),'coordinate':'json-pointer','pointer':er['pointer']}
            assert occ['event_time']==timestamp(original['updated_at'] if role=='derived-memory:file' else None)
            if role=='derived-memory:file':assert 'version-state' in er['role_basis']
    refs=sorted(blocks[key],key=lambda b:b['ordinal'])
    assert [r['ordinal'] for r in refs]==list(range(len(occ['content'])))
    for ref,content_link in zip(refs,occ['content']):
        assert ref['raw']['$link']==raw_key and ref['document_pointer']==er['pointer']
        value=at(original,ref['pointer']);obj=get(content_link['$link']);schema=obj['schema'];types[schema]+=1
        kind=ref['native_type']
        if schema=='pkst/content@0.1':
            assert obj['media_type']=='text/plain;charset=utf-8'
            assert obj['text']==(value['text'] if kind=='text' else value)
        elif schema=='pkst/projection@0.1':
            if kind=='message.text':value={'text':value}
            elif kind=='memory_file.meta':value={k:v for k,v in value.items() if k!='content'}
            assert obj['native_type']==kind and obj['profile']=='python-json-v1' and obj['text']==canonical(value)
            assert kind!='thinking'
        else:
            assert schema=='pkst/opaque-block@0.1' and obj['handling']=='raw-only'
            assert obj['digest']==hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()
doc=next(d for d in documents.values() if isinstance(d,list) and d and 'chat_messages' in d[0])
expected={(c['uuid'],m['uuid']) for c in doc for m in c['chat_messages']};assert message_ids==expected
assert len(expected)==2095 and len(occurrences)==2132
report={'schema':'pkst.claude-cloud-independent-verification@0.1','root':summary['snapshot'],'car_sha256':summary['car_sha256'],
        'verification':verification,'current_snapshot_objects':len(current),'current_occurrences':len(occurrences),
        'current_roles':dict(count),'raw_documents_used':len(documents),'native_messages_checked':len(expected),
        'extraction_records_checked':sum(map(len,ers.values())),'block_references_checked':sum(map(len,blocks.values())),
        'block_uses_by_schema':dict(types),'status':'passed','scope':'hashes, closure, full current raw fields, role/time/parent/opaque handling; not truth or user adoption',
        'peer_importer_or_decoder_used':False}
(base/'reports/claude-cloud-independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
