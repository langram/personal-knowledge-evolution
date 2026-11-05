"""Freeze edition 17 and the new peaceful-superintelligence supplement before editing."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/personal-thought-archive'
C = BASE / 'contributions/codex'
ARCHIVE = C / 'relativity-alignment-20261105'
OUT = BASE / 'dossiers/2026-11-05-relativity-alignment'
PUBLIC = ROOT / 'publication/personal-knowledge-evolution'
PRIOR = C / 'cooperative-superintelligence-20261102'
OLD = BASE / 'dossiers/2026-11-02-cooperative-superintelligence/01-new-principles.zh.md'
OLD_EN = BASE / 'dossiers/2026-11-02-cooperative-superintelligence/02-new-principles.en.md'
THREAD = '01a16c8a-f6e1-7580-b378-b6e49f0be965'
BASE_COMMIT = '5a6850fd2980c0ce246bd4e50a28823da00d0f7b'
EDITION = '18-relativity-alignment'
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

PREFIXES = [
    ('PREVIOUS-EDITION-RESPONSE', '已完成**第十七版**'),
    ('AUTHOR-WORD-COUNT', '现在中英文版本分别有多少字？'),
    ('WORD-COUNT-RESPONSE', '当前第十七版全文（含附录）'),
    ('AUTHOR-RELATIVITY-ALIGNMENT-FIRST', '以下内容的前半部分，相对性原理的大纲式的文字'),
    ('AUTHOR-RELATIVITY-ALIGNMENT', '\n# Files mentioned by the user:\n\n## Gemini_参考系的本质与相对性_20261105-1602.md'),
]
ATTACHMENT=Path(r'C:\Users\langr\Downloads\Gemini_参考系的本质与相对性_20261105-1602.md')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())

def raw(data):
    key = cid(data, 0x55)
    path = ARCHIVE / 'raw' / (key+'.bin')
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    return key

def capture_gemini(store):
    data=ATTACHMENT.read_bytes();text=data.decode('utf-8');key=raw(data)
    (OUT/'00-gemini-reference-frames.md').write_bytes(data)
    source=store.put({'schema':'pkst/source@0.1','platform':'gemini','namespace':'owner-google-account',
        'native_thread_id':'704d4de24bdcab7e'})
    blocks=list(re.finditer(r'^# (you asked|gemini response)\r?\n',text,re.M))
    assert len(blocks)==10
    events=[]
    for i,m in enumerate(blocks):
        end=blocks[i+1].start() if i+1<len(blocks) else text.index('Powered by [AI Exporter]')
        region=text[m.end():end]
        # Remove export framing, retaining the exact body bytes, internal separators and formatting.
        timestamp=re.match(r'\s*message time: ([^\r\n]+)\r?\n',region)
        localtime=timestamp[1] if timestamp else None
        start=m.end()+(timestamp.end() if timestamp else 0)
        while text[start] in '\r\n':start+=1
        tail=text[start:end]
        tail=re.sub(r'\s*---\s*$', '', tail)
        tail=tail.rstrip('\r\n')
        body_end=start+len(tail)
        assert text[start:body_end]==tail and tail
        a=len(text[:start].encode());b=len(text[:body_end].encode())
        role='user' if m[1]=='you asked' else 'assistant'
        assert bool(timestamp)==(role=='user')
        time={'value':localtime,'format':'export-local' if localtime else 'missing',
            'precision':'second' if localtime else None,'zone_known':False,'unit':None}
        ref=f'GEMINI-{i//2+1:02}-'+('AUTHOR' if role=='user' else 'RESPONSE')
        content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':tail})
        occurrence=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':None,
            'locator':{'raw':link(key),'start':a,'end':b,'coordinate':'utf8-bytes'},
            'native_role':role,'actor_kind':'human' if role=='user' else 'ai','process_kind':'main',
            'content':[link(content)],'native_parent_ids':None,'event_time':time})
        anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(key),'occurrence':link(occurrence),
            'coordinate':'utf8-bytes','start':a,'end':b,'pointer':'/markdown/messages/'+str(i),
            'parser':'gemini-ai-exporter-markdown-visible-v1',
            'role_basis':'Explicit export heading; user-supplied attachment, not authenticated cloud retrieval'})
        events.append({'ref':ref,'source':source,'occurrence':occurrence,'content':content,'anchors':[anchor],
            'role':role,'platform':'gemini','thread':'704d4de24bdcab7e','time':localtime,'time_format':time['format'],
            'native_event_time':time,'text':tail,'text_sha256':sha(tail.encode()),'phase':None,
            'capture':{'format':'markdown-export','native_file':str(ATTACHMENT),'raw':key,'bytes':len(data),
                'sha256':sha(data),'body_start':a,'body_end':b,'export_order':i+1,
                'captured_at':datetime.now(timezone.utc).isoformat()}})
    assert sum(e['role']=='user' for e in events)==5
    return events

def prepare():
    assert not (ARCHIVE/'capture.json').exists(), 'Capture exists; reconcile before retry.'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=PUBLIC).decode().strip() == BASE_COMMIT
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=PUBLIC)
    assert OLD.read_bytes() == (PUBLIC/'book/current.md').read_bytes()
    assert OLD_EN.read_bytes() == (PUBLIC/'book/current.en.md').read_bytes()
    OUT.mkdir(parents=True, exist_ok=True)
    (ARCHIVE/'raw').mkdir(parents=True, exist_ok=True)
    (WORK/'fragments').mkdir(exist_ok=True)
    pointer = json.loads((C/'catalog/current.json').read_bytes())
    previous = json.loads((PRIOR/'report.json').read_bytes())
    assert pointer['snapshot'] == previous['federated_snapshot']
    write_json(ARCHIVE/'baseline.json', {
        'pointer':pointer,'document':previous['document'],'english_document':previous['english_document'],
        'dossier_root':previous['snapshot'],'concepts':previous['concepts'],
        'manuscript':str(OLD.relative_to(BASE)), 'english_manuscript':str(OLD_EN.relative_to(BASE)),
        'sha256':sha(OLD.read_bytes()),'english_sha256':sha(OLD_EN.read_bytes()),
        'base_commit':BASE_COMMIT,'protected_research_branch':subprocess.check_output(
            ['git','rev-parse','codex/open-civilization-research-20261030'],cwd=PUBLIC).decode().strip(),
        'prior_event_count':previous['current_events']})
    previous_capture = json.loads((PRIOR/'capture.json').read_bytes())
    native = Path(previous_capture['events'][-1]['capture']['native_file'])
    begin = previous_capture['events'][-1]['capture']['native_end']
    selected = []
    with native.open('rb') as stream:
        stream.seek(begin)
        while True:
            start = stream.tell(); line = stream.readline()
            if not line or not line.endswith(b'\n'):
                break
            record = json.loads(line); p = record.get('payload',{})
            if record.get('type') != 'response_item' or p.get('type') != 'message':
                continue
            if p.get('is_summary') or p.get('isMeta'):
                continue
            if p.get('role') == 'assistant':
                if p.get('phase') != 'final_answer' or p.get('channel') not in (None,'final'):
                    continue
            elif p.get('role') != 'user':
                continue
            for i, block in enumerate(p.get('content',[])):
                text = block.get('text','')
                for ref, prefix in PREFIXES:
                    if text.startswith(prefix):
                        selected.append((ref,start,line,record,i,text))
            if selected and selected[-1][0] == PREFIXES[-1][0]:
                break
    assert [x[0] for x in selected] == [x[0] for x in PREFIXES]
    store = Store(ARCHIVE)
    source = store.put({'schema':'pkst/source@0.1','platform':'codex-local',
        'namespace':'owner-openai-account','native_thread_id':THREAD})
    events = capture_gemini(store)
    for ref,start,line,record,i,text in selected:
        p=record['payload']; role=p['role']; key=raw(line)
        content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text})
        time={'value':record['timestamp'],'format':'rfc3339','precision':'millisecond','zone_known':True,'unit':None}
        occurrence=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':p.get('id'),
            'locator':{'raw':link(key),'start':0,'end':len(line),'coordinate':'decoded-jsonl-utf8-bytes'},
            'native_role':role,'actor_kind':'human' if role=='user' else 'ai','process_kind':'main',
            'content':[link(content)],'native_parent_ids':None,'event_time':time})
        anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(key),'occurrence':link(occurrence),
            'coordinate':'decoded-jsonl-utf8-bytes','start':0,'end':len(line),
            'pointer':'/payload/content/'+str(i)+'/text','parser':'relativity-alignment-visible-native-v1',
            'role_basis':'visible native author message or assistant final; no analysis or tool envelope'})
        events.append({'ref':ref,'source':source,'occurrence':occurrence,'content':content,'anchors':[anchor],
            'role':role,'platform':'codex-local','thread':THREAD,'time':record['timestamp'],'time_format':'rfc3339',
            'native_event_time':time,'text':text,'text_sha256':sha(text.encode()),'phase':p.get('phase'),
            'capture':{'native_file':str(native),'native_start':start,'native_end':start+len(line),'raw':key,
                'bytes':len(line),'sha256':sha(line),'captured_at':datetime.now(timezone.utc).isoformat()}})
    write_json(ARCHIVE/'capture.json',{'scope':'Ten Gemini export blocks and five subsequent visible Codex events; no tools, hidden reasoning or environment envelopes. Gemini local timestamps have no exported timezone; Gemini reply times are unknown. Source order is not a globally resolved chronology. The repeated Codex request remains a distinct occurrence.','native_cursor':events[-1]['capture'],'events':events})
    write_json(OUT/'00-sources.json',[{k:v for k,v in e.items() if k!='capture'} for e in events])
    for e in events:
        (OUT/('00-'+e['ref'].lower()+'.txt')).write_bytes(e['text'].encode())
    print(json.dumps({'status':'frozen','events':len(events),'author_messages':sum(e['role']=='user' for e in events),'last_time':events[-1]['time']},ensure_ascii=False))

if __name__ == '__main__':
    prepare()
