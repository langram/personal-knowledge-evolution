import json, sqlite3, sys
from pathlib import Path
from collections import Counter
from compression import zstd

base=Path(r'C:\Users\langr\.codex')
report={'schema':'pkst.inventory-observation.v0.1','host':'windows-main','roots':[],'samples':[],'databases':{}}
for name in ('sessions','archived_sessions'):
    root=base/name
    files=sorted(p for p in root.rglob('*') if p.is_file() and (p.name.endswith('.jsonl') or p.name.endswith('.jsonl.zst')))
    report['roots'].append({'root':str(root),'files':len(files),'bytes':sum(p.stat().st_size for p in files),'compressed':sum(p.name.endswith('.zst') for p in files),'manifest':[{'path':str(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in files]})
    for p in files[-3:]:
        sample={'path':str(p),'records':[]}
        opener=zstd.open if p.suffix=='.zst' else open
        with opener(p,'rt',encoding='utf-8') as f:
            for i,line in enumerate(f):
                if i>=20: break
                d=json.loads(line); payload=d.get('payload',{})
                sample['records'].append({'type':d.get('type'),'keys':list(d),'payload_keys':list(payload) if isinstance(payload,dict) else None,'payload_type':payload.get('type') if isinstance(payload,dict) else None,'role':payload.get('role') if isinstance(payload,dict) else None,'content_shape': [{'keys':list(x),'type':x.get('type')} for x in payload.get('content',[]) if isinstance(x,dict)] if isinstance(payload,dict) else None})
        report['samples'].append(sample)
for name in ('state_5.sqlite','thread_history_1.sqlite'):
    p=base/name
    con=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    tables=con.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall()
    report['databases'][name]=[{'name':n,'sql':s} for n,s in tables]
    con.close()
out=Path(r'C:\Users\langr\Documents\Codex\2026-10-24\ni\outputs\personal-thought-archive\contributions\codex\windows-inventory.json')
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'roots':[{k:v for k,v in r.items() if k!='manifest'} for r in report['roots']],'samples':report['samples'],'databases':report['databases']},ensure_ascii=False))
