import json,re
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'new-principles/retrieval.jsonl'
hits=[]
for i,l in enumerate(p.open(encoding='utf-8')):
 r=json.loads(l);t=r['text']
 if not 150<len(t)<8000:continue
 if not re.search('教育|学习者|终身学习|学校|学生|创造者',t):continue
 if not re.search('新体制|新机制|神经网络|集体智慧|动态权重|全民|创造知识',t):continue
 score=sum(t.count(x) for x in ['教育','学习者','终身学习','学校','学生','创造者'])
 hits.append((score,i,r))
for score,i,r in sorted(hits,reverse=True)[:12]:
 print('\nREF',i,'score',score,'platform',r.get('platform'),'time',r.get('time'),'chars',len(r['text']))
 t=r['text'];spans=[]
 for m in re.finditer('教育|学习者|终身学习|学校|学生|创造者',t):
  a=max(0,m.start()-90);b=min(len(t),m.end()+260)
  if spans and a<=spans[-1][1]:spans[-1][1]=b
  else:spans.append([a,b])
 print('\n...\n'.join(t[a:b] for a,b in spans)[:3200])
