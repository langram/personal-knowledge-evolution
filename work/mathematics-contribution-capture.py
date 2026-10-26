import urllib.request,hashlib,json,re
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime,timezone
W=Path(__file__).resolve().parent/'mathematics-contribution';W.mkdir(exist_ok=True)
class Extract(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.depth=0;self.active=False;self.out=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='div':
   if not self.active and 'inner_content' in a.get('class','').split():self.active=True;self.depth=1;return
   if self.active:self.depth+=1
  if self.active and tag in ('p','br','section','h1','h2','h3'):self.out.append('\n')
 def handle_endtag(self,tag):
  if self.active and tag=='div':
   self.depth-=1
   if self.depth==0:self.active=False
  if self.active and tag in ('p','section','h1','h2','h3'):self.out.append('\n')
 def handle_data(self,data):
  if self.active:self.out.append(data)
url='https://zhishifenzi.com/depth/newsview/10737?category=multiple'
with urllib.request.urlopen(url,timeout=25) as r:b=r.read();final=r.url
(W/'speech-page.html').write_bytes(b)
p=Extract();p.feed(b.decode('utf-8'));text=re.sub(r'\n\s*\n+', '\n\n',''.join(p.out)).strip()
(W/'speech-reading.txt').write_bytes(text.encode())
meta={'url':url,'final_url':final,'captured_at':datetime.now(timezone.utc).isoformat(),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'title':re.search('<title>(.*?)</title>',b.decode('utf-8')).group(1),'derived_text':'inner_content HTML text projection; not exact native bytes','public_article_text_not_republished':True}
(W/'web-capture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False));print(text)
