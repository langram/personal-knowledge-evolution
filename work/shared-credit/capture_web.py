"""Save the public historical references used in the prose; keep failed captures."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from prepare import WORK, ARCHIVE, sha, write_json

SOURCES = [
    {'id':'newton', 'title':'The Newton Project: Life and Work at a Glance', 'url':'https://www.newtonproject.ox.ac.uk/his-life-and-work-at-a-glance', 'claim':'Distinct Leibniz and Hooke disputes; Newton role in the 1712 committee report. Historical summary, not a verdict on personalities.'},
    {'id':'darwin-wallace', 'title':'Darwin and Wallace 1858 joint paper, with Lyell and Hooker cover letter', 'url':'https://darwin-online.org.uk/content/contentblock?basepage=1&itemID=F350&hitpage=1&viewtype=text', 'claim':'1858 joint communication acknowledges independent intellectual contributions; does not establish perfect allocation of all subsequent credit.'},
    {'id':'perelman-2010', 'title':'Interfax direct interview reporting, 1 July 2010', 'url':'https://www.interfax.ru/russia/143587', 'claim':'Perelman declined the Millennium Prize; said reasons were multiple and Hamilton contribution no less than his. Not the 2006 Fields Medal explanation or a request for a 50/50 split.'},
    {'id':'fields-2006', 'title':'IMU Fields Medal official record', 'url':'https://www.mathunion.org/imu-awards/fields-medal', 'claim':'Perelman declined the 2006 Fields Medal. Does not establish the reason for refusal.'},
]

def capture(source):
    item = dict(source)
    record = {'url':item['url'], 'retrieved_at':datetime.now(timezone.utc).isoformat()}
    try:
        with urlopen(Request(item['url'],headers={'User-Agent':'Mozilla/5.0'}), timeout=35) as response:
            data=response.read();record.update(status='captured',http_status=response.status,final_url=response.url,
                file=item['id']+'.html',bytes=len(data),sha256=sha(data))
        (WORK/'web'/record['file']).write_bytes(data)
    except (HTTPError, URLError, TimeoutError) as error:
        record.update(status='failed',error=str(error))
    item['capture']=record
    item['access']='web tool read full relevant passages; direct public HTML capture recorded separately'
    return item

if __name__=='__main__':
    (WORK/'web').mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(capture,SOURCES))
    write_json(ARCHIVE/'external-sources.json',results)
    print(json.dumps([{'id':r['id'],**r['capture']} for r in results],ensure_ascii=False))
