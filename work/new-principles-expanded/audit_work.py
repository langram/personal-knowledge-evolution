import json,re,hashlib
from pathlib import Path
from collections import Counter
from book import OUT,WORK
man=json.loads((OUT/'source-manifest.json').read_text(encoding='utf-8'))
summary=[];issues=[];duplicates=[];seen={}
for c in man['chapters']:
 a=Counter();ch=c['chapter']
 for i,x in enumerate(c['items']):
  if x.get('reason')=='节标题':continue
  t=x['text'];a[x['kind']]+=len(t);a['literal']+=x.get('retained_characters',0)
  for pat in [r'原稿|原文中|以前的文章|重新回到|我之前|你之前|前面提到的第|上述第',r'[，。；：！？][，。；：！？]',r'你提出|你提到|你的|请你|作为一个AI|以下是|我来为',r'在确定性过程|形式的形式|过程的过程']:
   for m in re.finditer(pat,t):issues.append({'chapter':ch,'item':i,'match':m.group(),'context':t[max(0,m.start()-80):min(len(t),m.end()+100)]})
  for p in t.split('\n\n'):
   if len(p)>120 and p in seen:duplicates.append({'first':seen[p],'second':[ch,i],'text':p[:150]})
   seen[p]=[ch,i]
 total=a['source-adaptation']+a['source-exact']+a['editorial-addition']
 summary.append({'chapter':ch,'total':total,'source_adapted':a['source-adaptation']+a['source-exact'],'literal':a['literal'],'added':a['editorial-addition'],'ratio':round((a['source-adaptation']+a['source-exact'])/total,4)})
print(json.dumps({'summary':summary,'totals':{k:sum(x[k] for x in summary) for k in ['total','source_adapted','literal','added']},'issues':issues,'duplicates':duplicates},ensure_ascii=False,indent=2))
