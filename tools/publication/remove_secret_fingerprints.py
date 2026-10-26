"""Remove credential-only fingerprints from an uncommitted public export."""
import collections,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DEST=ROOT/'publication/personal-knowledge-evolution'
sys.path.insert(0,str(DEST/'archive/contributions/codex'))
from pkst_codec import cid,encode

def load(kind):
    rows=[]
    for p in sorted((DEST/'corpus'/kind).glob('*.jsonl')):
        rows.extend(json.loads(line) for line in p.read_text(encoding='utf-8').splitlines())
    return rows

def clean(value):
    if isinstance(value,str):return re.sub(r'\[REDACTED:([a-z-]+):[0-9a-f]{12}\]',r'[REDACTED:\1]',value)
    if isinstance(value,list):return [clean(x) for x in value]
    if isinstance(value,dict):
        return {k:clean(v) for k,v in value.items() if not (k=='sha256' and 'kind' in value and 'characters' in value)}
    return value

def write(kind,rows):
    folder=DEST/'corpus'/kind;groups=collections.defaultdict(list)
    for row in rows:groups[hashlib.sha256(row['cid'].encode()).hexdigest()[:2]].append(row)
    names={p.stem for p in folder.glob('*.jsonl')}|set(groups)
    for name in names:
        with (folder/(name+'.jsonl')).open('w',encoding='utf-8',newline='\n') as stream:
            for row in sorted(groups[name],key=lambda r:r['cid']):stream.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

objects=load('objects');changes={}
for row in objects:
    obj=row['object']
    if obj.get('redactions'):
        obj=clean(obj);key=cid(encode(obj))
        if key!=row['cid']:changes[row['cid']]=key;row.update(cid=key,object=obj)
for row in objects:
    obj=row['object']
    if obj['schema']=='pkst-public/event@1':
        changed=False
        for part in obj['content']:
            if part['$link'] in changes:part['$link']=changes[part['$link']];changed=True
        for part in obj['content_provenance']:
            if part['public_content_cid'] in changes:part['public_content_cid']=changes[part['public_content_cid']]
        if changed:
            key=cid(encode(obj));changes[row['cid']]=key;row['cid']=key
events=load('events')
for row in events:
    row['cid']=changes.get(row['cid'],row['cid'])
    row['content']=[changes.get(k,k) for k in row['content']]
write('objects',objects);write('events',events)
for name in ['publication/redactions.json','corpus/editorial-index.json']:
    path=DEST/name;value=clean(json.loads(path.read_bytes()))
    for row in value:
        for field in ['public_cid','cid']:
            if field in row:row[field]=changes.get(row[field],row[field])
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'changed_public_objects':len(changes),'object_count':len(objects),'event_count':len(events)}))
