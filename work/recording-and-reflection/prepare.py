"""Freeze only the seven visible messages authorized for this book edition."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/personal-thought-archive'
C = BASE / 'contributions/codex'
ARCHIVE = C / 'recording-and-reflection-20261030'
OUT = BASE / 'dossiers/2026-10-30-recording-and-reflection'
PUBLIC = ROOT / 'publication/personal-knowledge-evolution'
PRIOR = C / 'cooperation-feedback-20261029'
OLD = BASE / 'dossiers/2026-10-29-cooperation-feedback/02-new-principles.md'
THREAD = '01a16c8a-f6e1-7580-b378-b6e49f0be965'
NATIVE = Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-' + THREAD + '.jsonl')
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())
def raw(data):
    key = cid(data, 0x55)
    path = ARCHIVE / 'raw' / (key + '.bin')
    if path.exists(): assert path.read_bytes() == data
    else: path.write_bytes(data)
    return key

def prepare():
    if (ARCHIVE / 'capture.json').exists():
        raise RuntimeError('Existing frozen capture must be reconciled, not overwritten.')
    OUT.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / 'raw').mkdir(parents=True, exist_ok=True)
    pointer = json.loads((C / 'catalog/current.json').read_bytes())
    prior = json.loads((PRIOR / 'report.json').read_bytes())
    assert OLD.read_bytes() == (PUBLIC / 'book/current.md').read_bytes()
    write_json(ARCHIVE / 'baseline.json', {'pointer': pointer, 'document': prior['document'],
        'dossier_root': prior['snapshot'], 'concepts': prior['concepts'],
        'manuscript': str(OLD.relative_to(BASE)), 'sha256': sha(OLD.read_bytes())})
    selected = []
    with NATIVE.open('rb') as stream:
        while True:
            start = stream.tell(); line = stream.readline()
            if not line or not line.endswith(b'\n'): break
            r = json.loads(line); p = r.get('payload', {})
            if r.get('type') != 'response_item' or p.get('type') != 'message': continue
            if r.get('timestamp', '') < '2026-10-30T03:56:29.596Z': continue
            if p.get('role') == 'assistant':
                if p.get('phase') != 'final_answer' or p.get('channel') not in {None, 'final'}: continue
            elif p.get('role') != 'user': continue
            if p.get('is_summary') or p.get('isMeta'): continue
            blocks = [(i,b['text']) for i,b in enumerate(p.get('content', []))
                      if b.get('type') in {'input_text','output_text','text'} and isinstance(b.get('text'),str)]
            if len(blocks) != 1: continue
            i, text = blocks[0]
            if text.lstrip().startswith(('# AGENTS.md instructions','<environment_context>')): continue
            selected.append((start,line,r,i,text))
            if text.startswith('请你将上述尚未纳入到文章中的讨论内容'): break
    assert len(selected) == 7, [(x[2]['timestamp'],x[4][:60]) for x in selected]
    assert [x[2]['payload']['role'] for x in selected] == ['user','assistant','user','assistant','user','assistant','user']
    refs = ['CAPTURE-PROPOSAL','CAPTURE-RESPONSE','RECORDING-REPLY','RECORDING-RESPONSE','EVALUATION-REQUEST','EVALUATION-RESPONSE','INTEGRATION-REQUEST']
    store = Store(ARCHIVE)
    source = store.put({'schema':'pkst/source@0.1','platform':'codex-local',
                       'namespace':'owner-openai-account','native_thread_id':THREAD})
    events = []
    for ref,(start,line,r,i,text) in zip(refs,selected):
        p=r['payload']; role=p['role']; key=raw(line)
        content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text})
        time={'value':r['timestamp'],'format':'rfc3339','precision':'millisecond','zone_known':True,'unit':None}
        occurrence=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':p.get('id'),
            'locator':{'raw':link(key),'start':0,'end':len(line),'coordinate':'decoded-jsonl-utf8-bytes'},
            'native_role':role,'actor_kind':'human' if role=='user' else 'ai','process_kind':'main',
            'content':[link(content)],'native_parent_ids':None,'event_time':time})
        anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(key),'occurrence':link(occurrence),
            'coordinate':'decoded-jsonl-utf8-bytes','start':0,'end':len(line),
            'pointer':'/payload/content/'+str(i)+'/text','parser':'recording-reflection-visible-native-v1',
            'role_basis':'native author or assistant final answer; roles retained; no internal reasoning'})
        events.append({'ref':ref,'source':source,'occurrence':occurrence,'content':content,'anchors':[anchor],
            'role':role,'platform':'codex-local','thread':THREAD,'time':r['timestamp'],'time_format':'rfc3339',
            'native_event_time':time,'text':text,'text_sha256':sha(text.encode()),'phase':p.get('phase'),
            'capture':{'native_file':str(NATIVE),'native_start':start,'native_end':start+len(line),'raw':key,
                'bytes':len(line),'sha256':sha(line),'captured_at':datetime.now(timezone.utc).isoformat()}})
    write_json(ARCHIVE/'capture.json',{'scope':'four user messages and three assistant final answers; cutoff is integration request','events':events})
    public=[{k:v for k,v in e.items() if k!='capture'} for e in events]
    write_json(OUT/'00-sources.json',public)
    for e in events:
        (OUT/('00-'+e['ref'].lower()+'.txt')).write_bytes(e['text'].encode())
    print(json.dumps([{'ref':e['ref'],'role':e['role'],'time':e['time'],'characters':len(e['text'])} for e in events],ensure_ascii=False))

if __name__=='__main__': prepare()
