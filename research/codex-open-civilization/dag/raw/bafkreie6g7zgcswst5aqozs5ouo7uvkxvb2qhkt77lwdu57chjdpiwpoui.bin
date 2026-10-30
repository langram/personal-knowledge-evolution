"""Version research artifacts with the repository's existing DAG-CBOR/CID codec."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'archive/contributions/codex'))
from pkst_codec import Store,cid,decode,encode,link,links,linkset
DAG=HERE/'dag'
NS={'cnr':'urn:pkst:codex-independent-research:1'}
def save(path,value):
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

def snapshot(number):
    target=DAG/('round-'+number+'.json')
    if target.exists(): raise RuntimeError('Round snapshot exists; inspect instead of replacing it.')
    record=json.loads((HERE/('round-'+number+'-record.json')).read_bytes())
    store=Store(DAG); (DAG/'raw').mkdir(exist_ok=True)
    indexfile=DAG/'index.json'
    index=json.loads(indexfile.read_bytes()) if indexfile.exists() else {'rounds':[],'latest_proposals':{}}
    assert int(number)==len(index['rounds'])+1
    files=[]
    for name in record['files']:
        path=(HERE/name).resolve()
        assert path.is_relative_to(HERE.resolve())
        data=path.read_bytes(); key=cid(data,0x55); rawpath=DAG/'raw'/(key+'.bin')
        if rawpath.exists(): assert rawpath.read_bytes()==data
        else: rawpath.write_bytes(data)
        files.append({'path':name,'raw':link(key),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    proposals=[]
    for item in record['proposals']:
        previous=index['latest_proposals'].get(item['id'])
        key=store.put({'schema':'cnr/proposal@1','namespaces':NS,'round':int(number),**item,
            'previous':link(previous) if previous else None,'authored_by':{'kind':'ai','id':'codex'},
            'author_adoption':False,'basis':'research proposal and reviewable rationale; no empirical status beyond explicit evidence'})
        proposals.append(key); index['latest_proposals'][item['id']]=key
    activity=store.put({'schema':'cnr/research-activity@1','namespaces':NS,'round':int(number),
        'title':record['title'],'recorded_at':datetime.now(timezone.utc).isoformat(),'files':files,
        'proposals':linkset(proposals),'basis_commit':'15c9dfe82ecbb8f9495ab5eb1b55cd777b2f80f7',
        'book_document_original_cid':json.loads((ROOT/'archive/contributions/codex/recording-and-reflection-20261030/report.json').read_bytes())['document'],
        'scope':'Independent research branch; book reference is a named external archive identifier, not an unverified local DAG link.'})
    parent=index['rounds'][-1]['root'] if index['rounds'] else None
    root=store.put({'schema':'cnr/snapshot@1','namespaces':NS,'round':int(number),
                    'parents':linkset([parent] if parent else []),'roots':linkset([activity])})
    receipt={'round':int(number),'root':root,'parent':parent,'activity':activity,'files':files,'proposals':proposals}
    save(target,receipt); index['rounds'].append({'round':int(number),'root':root}); save(indexfile,index)
    print(json.dumps({'round':int(number),'root':root,'files':len(files),'proposal_versions':len(proposals)},ensure_ascii=False))

def verify():
    objects={}; rawkeys=set()
    for p in (DAG/'objects').glob('*.cbor'):
        data=p.read_bytes(); assert cid(data)==p.stem
        value=decode(data); assert encode(value)==data
        assert json.loads(p.with_suffix('.json').read_bytes())==value
        objects[p.stem]=value
    for p in (DAG/'raw').glob('*.bin'):
        assert cid(p.read_bytes(),0x55)==p.stem; rawkeys.add(p.stem)
    gray,black=set(),set()
    def visit(key):
        if key in black:return
        assert key not in gray,'cycle'
        if key in rawkeys: black.add(key); return
        assert key in objects,key
        gray.add(key)
        for child in links(objects[key]):visit(child)
        gray.remove(key);black.add(key)
    index=json.loads((DAG/'index.json').read_bytes())
    files=0
    for r in index['rounds']:
        visit(r['root'])
        receipt=json.loads((DAG/('round-'+str(r['round']).zfill(2)+'.json')).read_bytes())
        assert receipt['root']==r['root']
        for f in receipt['files']:
            data=(HERE/f['path']).read_bytes()
            assert cid(data,0x55)==f['raw']['$link']
            assert hashlib.sha256(data).hexdigest()==f['sha256']
            files+=1
    print(json.dumps({'status':'pass','rounds':len(index['rounds']),'objects':len(objects),'raw_blocks':len(rawkeys),
                      'file_version_checks':files,'scope':'Content identity, current immutable research files and graph closure; not scientific validity.'},ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='verify': verify()
    elif sys.argv[1]=='snapshot': snapshot(sys.argv[2])
    else: raise ValueError('Expected snapshot NN or verify')
