"""Freeze the visible research request, result and author response for edition ten."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT/'outputs/personal-thought-archive'
C = BASE/'contributions/codex'
ARCHIVE = C/'civilization-self-governance-20261031'
OUT = BASE/'dossiers/2026-10-31-civilization-self-governance'
PUBLIC = ROOT/'publication/personal-knowledge-evolution'
PRIOR = C/'recording-and-reflection-20261030'
OLD = BASE/'dossiers/2026-10-30-recording-and-reflection/02-new-principles.md'
THREAD = '01a16c8a-f6e1-7580-b378-b6e49f0be965'
NATIVE = Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-'+THREAD+'.jsonl')
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())
def raw(data):
    key=cid(data,0x55); path=ARCHIVE/'raw'/(key+'.bin')
    if path.exists(): assert path.read_bytes()==data
    else: path.write_bytes(data)
    return key

def prepare():
    if (ARCHIVE/'capture.json').exists():
        raise RuntimeError('Frozen capture exists; inspect before retrying.')
    OUT.mkdir(parents=True,exist_ok=True)
    (ARCHIVE/'raw').mkdir(parents=True,exist_ok=True)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    previous=json.loads((PRIOR/'report.json').read_bytes())
    assert OLD.read_bytes()==(PUBLIC/'book/current.md').read_bytes()
    write_json(ARCHIVE/'baseline.json',{'pointer':pointer,'document':previous['document'],
        'dossier_root':previous['snapshot'],'concepts':previous['concepts'],
        'manuscript':str(OLD.relative_to(BASE)),'sha256':sha(OLD.read_bytes())})
    prior_capture=json.loads((PRIOR/'capture.json').read_bytes())
    begin=prior_capture['events'][-1]['capture']['native_end']
    prefixes=[('RESEARCH-REQUEST','一直以来，都是我在逐步完善'),
              ('RESEARCH-RESULT','已完成三轮独立研发'),
              ('CIVILIZATION-REPLY','先谈谈对你的几轮研究中')]
    selected=[]
    with NATIVE.open('rb') as stream:
        stream.seek(begin)
        while True:
            start=stream.tell(); line=stream.readline()
            if not line or not line.endswith(b'\n'): break
            record=json.loads(line); p=record.get('payload',{})
            if record.get('type')!='response_item' or p.get('type')!='message': continue
            if p.get('is_summary') or p.get('isMeta'): continue
            if p.get('role')=='assistant':
                if p.get('phase')!='final_answer' or p.get('channel') not in {None,'final'}: continue
            elif p.get('role')!='user': continue
            for i,block in enumerate(p.get('content',[])):
                text=block.get('text','')
                for ref,prefix in prefixes:
                    if text.startswith(prefix): selected.append((ref,start,line,record,i,text))
            if selected and selected[-1][0]=='CIVILIZATION-REPLY': break
    assert [s[0] for s in selected]==[p[0] for p in prefixes]
    store=Store(ARCHIVE)
    source=store.put({'schema':'pkst/source@0.1','platform':'codex-local',
                     'namespace':'owner-openai-account','native_thread_id':THREAD})
    events=[]
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
            'pointer':'/payload/content/'+str(i)+'/text','parser':'civilization-selfgov-visible-native-v1',
            'role_basis':'native author or assistant final answer; no internal reasoning'})
        events.append({'ref':ref,'source':source,'occurrence':occurrence,'content':content,'anchors':[anchor],
            'role':role,'platform':'codex-local','thread':THREAD,'time':record['timestamp'],'time_format':'rfc3339',
            'native_event_time':time,'text':text,'text_sha256':sha(text.encode()),'phase':p.get('phase'),
            'capture':{'native_file':str(NATIVE),'native_start':start,'native_end':start+len(line),'raw':key,
                       'bytes':len(line),'sha256':sha(line),'captured_at':datetime.now(timezone.utc).isoformat()}})
    write_json(ARCHIVE/'capture.json',{'scope':'two user messages and one assistant final answer; author response authorizes edition ten','events':events})
    write_json(OUT/'00-sources.json',[{k:v for k,v in e.items() if k!='capture'} for e in events])
    for e in events: (OUT/('00-'+e['ref'].lower()+'.txt')).write_bytes(e['text'].encode())
    commit='4127d3f9ec4cfb7a61cbb2ea195cd6d64faef110'
    context={'branch':'codex/open-civilization-research-20261030','commit':commit,
             'scope':'AI research context referenced by the author; not automatic adoption or a merge of the research branch.','files':[]}
    for name in ['round-01.md','round-02.md','round-03.md','dag/index.json']:
        path='research/codex-open-civilization/'+name
        data=subprocess.check_output(['git','show',commit+':'+path],cwd=PUBLIC)
        context['files'].append({'path':path,'bytes':len(data),'sha256':sha(data),
            'url':'https://github.com/langram/personal-knowledge-evolution/blob/'+commit+'/'+path})
        if name=='dag/index.json': context['research_roots']=json.loads(data)['rounds']
    write_json(OUT/'research-context.json',context)
    print(json.dumps([{'ref':e['ref'],'role':e['role'],'time':e['time'],'characters':len(e['text'])} for e in events],ensure_ascii=False))

if __name__=='__main__': prepare()
