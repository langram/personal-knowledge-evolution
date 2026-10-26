import json, sqlite3
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
current=json.loads((BASE/'contributions/codex/catalog/current.json').read_text())
db=sqlite3.connect((BASE/current['database']).as_uri()+'?mode=ro',uri=True)
terms=['自我实现','自由区','科幻','游戏框架','全民平等','个人需求','动态权重','reverse','REA','神经系统']
hits={}
for term in terms:
    rows=db.execute('''SELECT DISTINCT o.cid,o.event_time,o.role,s.platform,s.native_thread_id,c.text
      FROM current_occurrences o JOIN sources s ON s.cid=o.source
      JOIN parts p ON p.occurrence=o.cid JOIN content c ON c.cid=p.content
      WHERE instr(c.text,?)>0 AND o.role IN ('user','human','Prompted') ORDER BY o.event_time DESC LIMIT 24''',(term,)).fetchall()
    print(term, len(rows))
    for cid,t,role,platform,thread,text in rows:
        hits[cid]={'cid':cid,'event_time':t,'role':role,'platform':platform,'thread':thread,'text':text}
Path('work/theory-context-hits.json').write_text(json.dumps(list(hits.values()),ensure_ascii=False,indent=2),encoding='utf-8')
for i,h in enumerate(hits.values()):
    print(json.dumps({'i':i,**{k:v for k,v in h.items() if k!='text'},'chars':len(h['text']),'excerpt':h['text'][:520]},ensure_ascii=False))

p=Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
size=p.stat().st_size
with p.open('rb') as f: raw=f.read(size)
out=Path('work/theory-current-prefix.jsonl');out.write_bytes(raw)
events=[];offset=0
for line in raw.splitlines(keepends=True):
    end=offset+len(line)-(1 if line.endswith(b'\n') else 0)
    try:d=json.loads(line)
    except json.JSONDecodeError:offset+=len(line);continue
    pld=d.get('payload',{})
    if d.get('type')=='response_item' and pld.get('type')=='message' and pld.get('role') in ('user','assistant') and pld.get('channel') not in ('analysis',):
        text=''.join(x.get('text','') for x in pld.get('content',[]) if x.get('type') in ('input_text','output_text','text'))
        events.append({'start':offset,'end':end,'time':d.get('timestamp'),'role':pld.get('role'),'channel':pld.get('channel'),'text':text})
    offset+=len(line)
start=next(i for i,e in enumerate(events) if e['role']=='user' and e['text'].startswith('现在是不是其他都整理好了'))
last=next(i for i,e in enumerate(events) if e['role']=='user' and e['text'].startswith('把我们这几轮讨论整理进'))
selected=events[start:last+1]
Path('work/theory-recent-events.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
print('RECENT',len(selected),'PREFIX',size,'END',selected[-1]['end'])
for i,e in enumerate(selected):print(json.dumps({'i':i,**{k:v for k,v in e.items() if k!='text'},'chars':len(e['text']),'excerpt':e['text'][:100]},ensure_ascii=False))
