import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT/'outputs/personal-thought-archive'
OLD = BASE/'contributions/codex/new-principles-20261026/selected-sources.json'

def sources():
    old=json.loads(OLD.read_text(encoding='utf-8'))
    records={**old['records'], **old['artifacts']}
    for ref,r in records.items():
        r['ref']=ref
    extra=WORK/'extra-sources.json'
    if extra.exists(): records.update(json.loads(extra.read_text(encoding='utf-8')))
    return records

def paragraphs(text):
    return [{'text':m.group(), 'start':m.start(), 'end':m.end()} for m in re.finditer(r'\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*',text)]

if __name__=='__main__':
    args=sys.argv[1:]
    if args[0]=='add':
        wanted={int(x) for x in args[1:]}; extra=WORK/'extra-sources.json'
        records=json.loads(extra.read_text(encoding='utf-8')) if extra.exists() else {}
        for i,line in enumerate((ROOT/'work/new-principles/retrieval.jsonl').open(encoding='utf-8')):
            if i in wanted:
                r=json.loads(line);r['ref']=f'R{i}';records[r['ref']]=r
        extra.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        print('extra records',len(records))
    elif args[0]=='show':
        r=sources()[args[1]];p=paragraphs(r['text'])
        start=int(args[2]) if len(args)>2 else 0;end=int(args[3]) if len(args)>3 else len(p)
        print(r['ref'],{k:r.get(k) for k in ['platform','time','thread','source_kind']},'paragraphs',len(p),'chars',len(r['text']))
        for i in range(start,min(end,len(p))):print(f'\n[P{i} {p[i]["start"]}:{p[i]["end"]}]\n{p[i]["text"]}')
    elif args[0]=='list':
        for ref,r in sources().items():
            print(ref,len(r['text']),r.get('platform','file'),len(paragraphs(r['text'])),r['text'][:65].replace('\n',' '))
