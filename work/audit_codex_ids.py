import json,sqlite3,sys
from pathlib import Path
from collections import Counter
from compression import zstd
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
root=base/'contributions/codex';sys.path.insert(0,str(root))
from index_codex import records
rows=[json.loads(l) for l in (root/'.private/capture-20261024T070147Z-4f83698c.jsonl').read_text(encoding='utf-8').splitlines()]
counts=Counter();fields=Counter();outer_fields=Counter();metadata_fields=Counter();roles=Counter()
for r in rows:
    opener=zstd.open if r['source_suffix'].endswith('.zst') else open
    with opener(root/'raw'/(r['raw_cid']+'.bin'),'rb') as stream:
        for start,end,line,failure in records(stream):
            if failure:continue
            d=json.loads(line);p=d.get('payload',{})
            if d.get('type')!='response_item' or not isinstance(p,dict) or p.get('type')!='message':continue
            counts['messages']+=1
            if isinstance(p.get('id'),str) and p['id']:counts['native_id_present']+=1;continue
            counts['native_id_missing']+=1;roles[str(p.get('role'))]+=1
            fields.update(p.keys());outer_fields.update(d.keys())
            if isinstance(d.get('metadata'),dict):metadata_fields.update(d['metadata'].keys())
report={'counts':dict(counts),'missing_id_roles':dict(roles),'payload_fields_without_id':dict(fields),
        'record_fields_without_id':dict(outer_fields),'metadata_fields_without_id':dict(metadata_fields),
        'finding':'Missing native message IDs use raw+byte-range locators; append/re-export equivalence is not proven.',
        'fallback_fraction':counts['native_id_missing']/counts['messages']}
(base/'reports/codex-native-id-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
