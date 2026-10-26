"""Read-only independent verification of the peer's immutable object files."""
import hashlib,json,sys,time
from pathlib import Path
from collections import Counter
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import encode,decode,cid,cid_bytes,links,check_sets
peer=base/'contributions/claude'
started=time.monotonic()
vectors=json.loads((peer/'n3-object-vectors-claude.json').read_text(encoding='utf-8'))
for v in vectors['positive']:
    data=encode(v['value'])
    assert data.hex()==v['cbor_hex'],v['name']
    assert cid(data)==v['cid'],v['name']
    assert decode(data)==v['value'],v['name']
files=sorted((peer/'objects').glob('*.cbor'))
seen=set();refs=set();counts=Counter();anchors=[]
for p in files:
    data=p.read_bytes();assert cid(data)==p.stem,p.name
    o=decode(data);check_sets(o);seen.add(p.stem);refs.update(links(o));counts[o['schema']]+=1
    if o['schema']=='pkst/extraction-record@0.1':anchors.append((p.stem,o))
external=refs-seen
for key in external:
    assert cid_bytes(key)[1]==0x55,('missing structural block',key)
    h=hashlib.sha256()
    with (peer/'raw'/(key+'.bin')).open('rb') as f:
        while b:=f.read(4*1024*1024):h.update(b)
    assert h.digest()==cid_bytes(key)[4:],key
sample=anchors[::max(1,len(anchors)//32)][:32]
for key,er in sample:
    assert er['coordinate']=='decoded-jsonl-utf8-bytes'
    with (peer/'raw'/(er['raw']['$link']+'.bin')).open('rb') as f:
        f.seek(er['start']);data=f.read(er['end']-er['start']);following=f.read(1)
    assert not data.endswith(b'\n') and following in (b'',b'\n'),key
    rec=json.loads(data)
    occ=decode((peer/'objects'/(er['occurrence']['$link']+'.cbor')).read_bytes())
    if occ['native_id'] is not None:assert occ['native_id']==rec['uuid'],key
    if er['parser']=='claude-code-jsonl@0.1-n3':
        # Preserve ordered textual source blocks. Do not inspect opaque reasoning bodies.
        c=(rec.get('message') or {}).get('content')
        if isinstance(c,str):expected=[c]
        elif isinstance(c,list):expected=[b['text'] for b in c if isinstance(b,dict) and b.get('type')=='text' and isinstance(b.get('text'),str)]
        elif rec.get('type')=='system' and isinstance(rec.get('content'),str):expected=[rec['content']]
        elif rec.get('type')=='attachment' and (rec.get('attachment') or {}).get('type')=='queued_command' and isinstance(rec['attachment'].get('prompt'),str):expected=[rec['attachment']['prompt']]
        else:expected=[]
        actual=[]
        for link in occ['content']:
            part=decode((peer/'objects'/(link['$link']+'.cbor')).read_bytes())
            if part['schema']=='pkst/content@0.1':actual.append(part['text'])
        assert actual==expected,key
report={'schema':'pkst.independent-peer-verification@0.1','verifier':'Codex decoder; Claude implementation not imported',
        'peer_n3_vectors':len(vectors['positive']),'objects':len(seen),'schemas':dict(counts),
        'external_raw_rehashed':len(external),'raw_anchor_samples':len(sample),
        'status':'hashes, canonical decoding, set ordering, closure and sampled raw text anchors passed',
        'elapsed_seconds':round(time.monotonic()-started,3),'scope':'Evidence integrity, not truth or completeness of thoughts'}
(base/'reports/claude-independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
