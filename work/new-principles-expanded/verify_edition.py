"""Independently reparse selected native bytes and replay editorial edits."""
import hashlib,json,re,sqlite3,sys
from collections import defaultdict,Counter
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from compression import zstd
from sources import BASE,WORK
sys.path.insert(0,str(BASE/'contributions/codex'))
from pkst_codec import cid,cid_bytes,decode,encode,check_sets
O=BASE/'contributions/codex/new-principles-expanded-20261026';D=BASE/'dossiers/2026-10-26-new-principles-expanded'
baseline=json.loads((O/'baseline.json').read_text());selected=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'))
db=sqlite3.connect((BASE/baseline['pointer']['database']).as_uri()+'?mode=ro',uri=True)
checked=set()
def get(k):
 row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone()
 if row:
  with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
 else:
  p=O/('raw' if cid_bytes(k)[1]==0x55 else 'objects')/(k+('.bin' if cid_bytes(k)[1]==0x55 else '.cbor'));b=p.read_bytes()
 assert cid(b,cid_bytes(k)[1])==k,k;checked.add(k)
 if cid_bytes(k)[1]==0x55:return b
 o=decode(b);check_sets(o);assert encode(o)==b;return o
def at(d,p):
 for tok in p.split('/')[1:]:
  tok=tok.replace('~1','/').replace('~0','~');d=d[int(tok)] if isinstance(d,list) else d[tok]
 return d
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,list):
  for y in x:yield from strings(y)
 elif isinstance(x,dict):
  for y in x.values():yield from strings(y)

rawgroups=defaultdict(list);events=set();files=0
for ref,r in selected.items():
 assert hashlib.sha256(r['text'].encode()).hexdigest()==r['text_sha256']
 if r.get('occurrence'):
  o=get(r['occurrence']);c=get(r['content']);s=get(o['source']['$link'])
  assert c['text']==r['text'];assert r['content'] in [x['$link'] for x in o['content']]
  assert o['native_role']==r['role'] and o['actor_kind']=='unknown'
  assert o['event_time']['value']==r['time'] and s['platform']==r['platform'] and s['native_thread_id']==r['thread']
  assert r['anchors'];events.add(r['occurrence'])
  for a in r['anchors']:
   er=get(a);assert er['occurrence']['$link']==r['occurrence'];rawgroups[er['raw']['$link']].append((ref,r,er))
 else:
  b=get(r['raw']);assert b.decode('utf-8')==r['text'];assert len(b)==r['bytes'];files+=1
anchors=0
for rawid,entries in rawgroups.items():
 b=get(rawid)
 if b.startswith(bytes.fromhex('28b52ffd')):b=zstd.decompress(b)
 doc=json.loads(b,parse_float=Decimal) if any(e[2]['coordinate']=='json-pointer' for e in entries) else None
 for ref,r,e in entries:
  if e['coordinate']=='json-pointer':n=at(doc,e['pointer'])
  else:
   assert e['coordinate']=='decoded-jsonl-utf8-bytes';n=json.loads(b[e['start']:e['end']],parse_float=Decimal)
  assert any(r['text'] in t for t in strings(n)),(ref,'source text missing')
  p=r['platform']
  if p=='chatgpt':assert n['author']['role']==r['role'] and Decimal(str(n['create_time']))==Decimal(r['time'])
  elif p=='claude-ai':assert n['sender']==r['role'] and n['created_at']==r['time']
  elif p=='claude-code':assert n['type']==r['role'] and n['timestamp']==r['time']
  elif p=='codex-local':assert n['payload']['role']==r['role'] and n['timestamp']==r['time']
  elif p=='gemini':assert at(doc,e['pointer'].rsplit('/',1)[0])['time']==r['time'] and n=='Prompted '+r['text']
  else:raise AssertionError(p)
  anchors+=1
 del b,doc

body=(D/'01-manuscript.md').read_bytes().decode('utf-8');state=json.loads((D/'edition-state.json').read_text(encoding='utf-8'));man=json.loads((D/'source-manifest.json').read_text(encoding='utf-8'))
assert hashlib.sha256(body.encode()).hexdigest()==state['manuscript_sha256']
assert len(man['chapters'])==state['complete_chapters']==state['planned_chapters']==24
assert len(re.findall('[\u3400-\u9fff]',body))==state['total_cjk_characters']
assert not re.search(r'我在原稿中|重新回到原稿|你之前提到|，。|。。|，，|？。|，：',body)
sourceunits=editunits=literal=0
def replay(raw,base,edits):
 cursor=0;out=[];removed=0
 for e in edits:
  a,b=(z-base for z in e['source_span']);assert cursor<=a<=b<=len(raw)
  assert raw[a:b]==e['before'];out.extend((raw[cursor:a],e['after']));cursor=b;removed+=b-a
 out.append(raw[cursor:]);return ''.join(out),len(raw)-removed
for c in man['chapters']:
 ch=(D/'chapters'/f'{c["chapter"]}.md').read_bytes().decode('utf-8')
 for x in c['items']:
  a,b=x['document_span'];u,v=x['chapter_span'];assert body[a:b]==ch[u:v]==x['text']
  if x.get('ref'):
   sourceunits+=1;r=selected[x['ref']];s,t=x['source_span'];raw=r['text'][s:t]
   assert hashlib.sha256(raw.encode()).hexdigest()==x['source_sha256']
   output,count=replay(raw,s,x['edits']);assert output==x['text'] and count==x['retained_characters'];literal+=count
   for e in x['edits']:assert x['text'][e['output_span'][0]:e['output_span'][1]]==e['after']
  elif x.get('reason')!='节标题':editunits+=1
 assert state['chapters'][int(c['chapter'])]['status']=='expanded-copyedited'
stats=json.loads((D/'editorial-statistics.json').read_text());assert stats['literal_aligned_source_characters']==literal
assert stats['source_units']==sourceunits and stats['editorial_units']==editunits
mapping=json.loads((O/'chapter-concept-map.json').read_text());plan=json.loads((O/'semantic-plan.json').read_text())
assert set(mapping)=={x['id'] for x in plan['nodes']} and len(mapping)==34
assert all((D/'chapters'/f'{key}.md').is_file() for keys in mapping.values() for key in keys)
for ref,r in selected.items():assert (D/'sources'/f'{ref}.txt').read_bytes()==r['text'].encode()
linkcount=0
for fn in ['00-readme.md','01-manuscript.md','02-source-atlas.md','04-evolution-and-coverage.md','05-editorial-review.md','06-theory-map.md']:
 p=D/fn
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if target.startswith(('http:','https:','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(fn,target);linkcount+=1
assert hashlib.sha256((BASE/'dossiers/2026-10-26-new-principles/01-new-principles.md').read_bytes()).hexdigest()==baseline['old_manuscript_sha256']
test=next(x for c in man['chapters'] for x in c['items'] if x.get('ref'));r=selected[test['ref']];a,b=test['source_span'];raw=r['text'][a:b]
assert hashlib.sha256((raw+'改').encode()).hexdigest()!=test['source_sha256']
assert body[test['document_span'][0]:test['document_span'][1]]!=test['text']+'伪造'
assert hashlib.sha256(body.replace('\n','\r\n').encode()).hexdigest()!=state['manuscript_sha256']
result={'schema':'np2.source-and-editorial-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),'selected_sources':len(selected),'unique_native_events':len(events),'native_anchors_reparsed':anchors,'artifact_sources':files,'platforms':sorted({r['platform'] for r in selected.values() if r.get('platform')}),'source_units_replayed':sourceunits,'editorial_addition_units':editunits,'literal_aligned_characters':literal,'manuscript_cjk_characters':state['total_cjk_characters'],'manuscript_sha256':state['manuscript_sha256'],'chapters':24,'major_topics_mapped':34,'legacy_semantic_relations_retained':len(plan['relations']),'local_links_checked':linkcount,'blocks_byte_checked':len(checked),'negative_checks':['changed source text fails frozen source-span digest','altered manuscript passage fails document interval equality'],'old_manuscript_unchanged':True,'scope':'selected native records reparsed; edit scripts replayed independently; same PKST codec; Codex review, not independent Claude or owner acceptance; no rerun of research experiments'}
(O/'source-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
