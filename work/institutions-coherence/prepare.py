"""Freeze edition 14 and the new institutional-gap/coherence request before editing."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/personal-thought-archive'
C = BASE / 'contributions/codex'
ARCHIVE = C / 'institutions-coherence-20261101'
OUT = BASE / 'dossiers/2026-11-01-institutions-coherence'
PUBLIC = ROOT / 'publication/personal-knowledge-evolution'
PRIOR = C / 'civilization-attention-20261101'
OLD = BASE / 'dossiers/2026-11-01-civilization-attention/01-new-principles.zh.md'
OLD_EN = BASE / 'dossiers/2026-11-01-civilization-attention/02-new-principles.en.md'
THREAD = '01a16c8a-f6e1-7580-b378-b6e49f0be965'
BASE_COMMIT = '11689a4ecf662ba5bf620dfedeb79fa6800f6a98'
EDITION = '15-institutions-coherence'
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

PREFIXES = [
    ('PREVIOUS-EDITION-RESPONSE', '已完成**第十四版**'),
    ('AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW', '关于制度与技术发展落差的部分，添加如下内容：'),
]

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
    events = []
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
            'pointer':'/payload/content/'+str(i)+'/text','parser':'institutions-coherence-visible-native-v1',
            'role_basis':'visible native author message or assistant final; no analysis or tool envelope'})
        events.append({'ref':ref,'source':source,'occurrence':occurrence,'content':content,'anchors':[anchor],
            'role':role,'platform':'codex-local','thread':THREAD,'time':record['timestamp'],'time_format':'rfc3339',
            'native_event_time':time,'text':text,'text_sha256':sha(text.encode()),'phase':p.get('phase'),
            'capture':{'native_file':str(native),'native_start':start,'native_end':start+len(line),'raw':key,
                'bytes':len(line),'sha256':sha(line),'captured_at':datetime.now(timezone.utc).isoformat()}})
    write_json(ARCHIVE/'capture.json',{'scope':'Edition 14 completion context and new author request for institutional-gap evidence and full-book coherence review; visible dialogue only','events':events})
    write_json(OUT/'00-sources.json',[{k:v for k,v in e.items() if k!='capture'} for e in events])
    for e in events:
        (OUT/('00-'+e['ref'].lower()+'.txt')).write_bytes(e['text'].encode())
    print(json.dumps({'status':'frozen','events':len(events),'author_messages':sum(e['role']=='user' for e in events),'last_time':events[-1]['time']},ensure_ascii=False))

if __name__ == '__main__':
    prepare()
