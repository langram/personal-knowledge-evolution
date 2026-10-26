"""Public supporting pages only; a failed fetch is recorded, not substituted."""
import concurrent.futures, json, urllib.request
from datetime import datetime, timezone
from prepare import WORK, write_json, sha
PAGES=[
 ('jefferson','https://monadnock.net/jefferson/mcpherson.html'),
 ('gnu-initial','https://www.gnu.org/gnu/initial-announcement.html'),
 ('gnu-selling','https://www.gnu.org/philosophy/selling.en.html'),
 ('quotation-attribution','https://quoteinvestigator.com/2011/12/13/swap-ideas/'),
 ('inference-energy','https://arxiv.org/abs/2311.16863v3'),
]
def fetch(pair):
    key,url=pair;p=WORK/'web'/(key+'.html');meta=WORK/'web'/(key+'.json')
    if meta.exists():return json.loads(meta.read_bytes())
    r={'id':key,'url':url,'captured_at':datetime.now(timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request,timeout=15) as response:
            b=response.read();r.update(status='captured',http_status=response.status,final_url=response.url,bytes=len(b),sha256=sha(b),file=p.name)
        p.write_bytes(b)
    except (OSError,TimeoutError) as e:
        r.update(status='fetch-failed',error_type=type(e).__name__,error=str(e),boundary='claim checked through web tool where noted; no raw page substituted')
    write_json(meta,r);return r
if __name__=='__main__':
    (WORK/'web').mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:records=list(pool.map(fetch,PAGES))
    write_json(WORK/'web-captures.json',records)
    print(json.dumps(records,ensure_ascii=False))
