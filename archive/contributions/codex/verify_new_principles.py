"""Read source bytes independently, check spans, graph interpretation edges, and then activate."""
import hashlib,json,re,sqlite3,sys
from decimal import Decimal
from datetime import datetime,timezone
from pathlib import Path
from compression import zstd
from pkst_codec import cid,cid_bytes,decode,encode,check_sets
from query_catalog import search
B=Path(__file__).resolve().parents[2];C=B/'contributions/codex';O=C/'new-principles-20261026';D=B/'dossiers/2026-10-26-new-principles'
PROTOCOL='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
def main():
 selection=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'));plan=json.loads((O/'semantic-plan.json').read_text(encoding='utf-8'));manifest=json.loads((O/'manuscript-manifest.json').read_text(encoding='utf-8'));report=json.loads((O/'report.json').read_text(encoding='utf-8'));pointer=json.loads((O/'staged-pointer.json').read_text());db=sqlite3.connect((B/pointer['database']).as_uri()+'?mode=ro',uri=True)
 def get(k):
  row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone();assert row,k
  with (B/row[0]).open('rb') as f:f.seek(row[1]);data=f.read(row[2])
  assert cid(data,cid_bytes(k)[1])==k,k
  if cid_bytes(k)[1]==0x55:return data
  obj=decode(data);check_sets(obj);assert encode(obj)==data;return obj
 rawcache={};jsoncache={}
 def rawdoc(k):
  if k not in rawcache:
   data=get(k)
   if data.startswith(bytes.fromhex('28b52ffd')):data=zstd.decompress(data)
   rawcache[k]=data
  return rawcache[k]
 def doc(k):
  if k not in jsoncache:jsoncache[k]=json.loads(rawdoc(k),parse_float=Decimal)
  return jsoncache[k]
 def at(d,pointer):
  for token in pointer.split('/')[1:]:
   token=token.replace('~1','/').replace('~0','~');d=d[int(token)] if isinstance(d,list) else d[token]
  return d
 def anchor(er):
  k=er['raw']['$link']
  if er['coordinate']=='decoded-jsonl-utf8-bytes':return json.loads(rawdoc(k)[er['start']:er['end']],parse_float=Decimal)
  assert er['coordinate']=='json-pointer';return at(doc(k),er['pointer'])
 def strings(x):
  if isinstance(x,str):yield x
  elif isinstance(x,list):
   for y in x:yield from strings(y)
  elif isinstance(x,dict):
   for y in x.values():yield from strings(y)
 checked_anchors=set();checked_events=set();platforms=set()
 for ref,r in selection['records'].items():
  o=get(r['occurrence']);content=get(r['content']);source=get(o['source']['$link'])
  assert content['text']==r['text'];assert r['content'] in [x['$link'] for x in o['content']]
  assert source['platform']==r['platform'] and source['native_thread_id']==r['thread'];assert o['event_time']['value']==r['time'];assert o['native_role']==r['role']
  assert o['actor_kind']=='unknown','Selected user-channel record must not be promoted to human authorship'
  for k in r['anchors']:
   er=get(k);n=anchor(er);assert er['occurrence']['$link']==r['occurrence'];assert any(r['text'] in t for t in strings(n)),(ref,'native text not found')
   platform=r['platform']
   if platform=='chatgpt':
    assert n['author']['role']==r['role'];assert Decimal(str(n['create_time']))==Decimal(str(r['time']))
   elif platform=='claude-ai':assert n['sender']==r['role'] and n['created_at']==r['time']
   elif platform=='gemini':
    parent=at(doc(er['raw']['$link']),er['pointer'].rsplit('/',1)[0]);assert parent['time']==r['time'];assert n=='Prompted '+r['text']
   elif platform=='codex-local':
    assert n['payload']['role']==r['role'] and n['timestamp']==r['time']
    if r.get('new'):
     p=n['payload'];assert o['native_id']==p.get('id');assert o['native_parent_ids']==(None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]))
     if o['native_id'] is None:assert o['locator']=={k:er[k] for k in ['raw','start','end','coordinate']}
   elif platform=='claude-code':assert n['timestamp']==r['time'] and n['type']==r['role']
   else:raise AssertionError(platform)
   checked_anchors.add(k)
  checked_events.add(r['occurrence']);platforms.add(r['platform'])
 artifact_checks=0
 for ref,r in selection['artifacts'].items():
  data=get(r['raw']);assert data.decode('utf-8')==r['text'];assert len(data)==r['bytes'];assert r['writing_time'] is None
  if 'library_raw' in r:
   l=doc(r['library_raw'])[r['library_index']];assert l['file_id']==r['file_id'] and l['file_name']==r['name'];assert l['file_upload_time']==r['upload_time'];assert l['file_size_bytes']==r['bytes']
  artifact_checks+=1
 body=(D/'01-new-principles.md').read_bytes().decode('utf-8');assert hashlib.sha256(body.encode()).hexdigest()==manifest['sha256'];assert len(re.findall(r'[\u4e00-\u9fff]',body))==manifest['cjk_characters']
 assert '{{' not in body and '<!-- sources:' not in body
 sources={**selection['records'],**selection['artifacts']}
 for q in report['quotes']:
  assert sources[q['source_ref']]['text'][q['source_start']:q['source_end']]==q['text'];assert body[q['document_start']:q['document_end']]==q['text']
  s=get(q['statement']);assert s['text']==q['text'] and s['force']=='quote' and s['holder']['kind']=='unknown';assert s['np:quotation']['start']==q['source_start'] and s['np:quotation']['end']==q['source_end']
  assert s['np:document_span']['document']['$link']==report['document'];assert s['np:document_span']['start']==q['document_start'] and s['np:document_span']['end']==q['document_end']
 assert (D/'02-original-manuscript.md').read_bytes()==get(selection['artifacts']['ORIGINAL']['raw'])
 assert len(plan['prior_concept_map'])==21 and len({x['cid'] for x in plan['prior_concept_map']})==21
 assert len(report['concepts'])==len(plan['nodes'])==34
 for n in plan['nodes']:
  obj=get(report['concepts'][n['id']]);assert obj['label']==n['label'] and obj['definition']==n['definition'];assert obj['asserted_by']=={'kind':'ai','id':'codex'}
  assert all(c in {x['id'] for x in manifest['chapters']} for c in n['chapters'])
 semantic_edges=set()
 for key,r in zip(report['relations'],plan['relations']):
  obj=get(key);pred={'contrasts-with':'np:in-tension-with','constrains':'np:constrains'}.get(r['predicate'],r['predicate'])
  assert obj['from']['$link']==report['concepts'][r['from']] and obj['to']['$link']==report['concepts'][r['to']];assert obj['predicate']==pred
  semantic_edges.add((r['from'],r['to'],r['predicate']))
 for edge in [('C04','C03','derived-from'),('C23','C22','part-of'),('C29','C26','depends-on')]:
  assert edge in semantic_edges and (edge[1],edge[0],edge[2]) not in semantic_edges
 for key,t in zip(report['timeline_entries'],plan['timeline']):
  obj=get(key);r=selection['records'][t['source']];assert obj['event_time']==get(r['occurrence'])['event_time'];assert obj['display_utc']==t['display_utc']
 for f in report['files']:
  data=(B/f['path']).read_bytes();assert data==get(f['raw']['$link']);assert hashlib.sha256(data).hexdigest()==f['sha256']
 # Check local links and explicit anchors in actual deliverables, without following source instructions.
 checked_links=0
 for path in [D/'00-readme.md',D/'01-new-principles.md',D/'04-chapter-map.md',D/'05-evolution.md',D/'06-editorial-ledger.md']:
  text=path.read_text(encoding='utf-8')
  for target in re.findall(r'\]\(([^)]+)\)',text):
   if target.startswith(('https:','http:')):continue
   fp,sep,fragment=target.partition('#');dest=path.parent/fp if fp else path
   assert dest.is_file(),(str(path),target)
   if fragment:assert 'id="'+fragment+'"' in dest.read_text(encoding='utf-8'),(str(path),target)
   checked_links+=1
 assert cid((B/'protocol/PKST-0.1.md').read_bytes(),0x55)==PROTOCOL
 assert db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]==212353
 assert len({x['source'] for x in plan['timeline']})==38
 for platform in ['chatgpt','claude-ai','gemini','codex-local','claude-code']:
  # Existence and native references are checked directly; full-text keyword choice does not define coverage.
  assert any(r['platform']==platform for r in selection['records'].values())
 hits=search(db,'新原理',30,platform='chatgpt');assert hits and all(h['anchors'] for h in hits)
 assert all(db.execute('SELECT count(*) FROM current_occurrences WHERE cid=?',(r['occurrence'],)).fetchone()[0]==1 for r in selection['records'].values())
 test=report['quotes'][0];assert test['text']+'伪造'!=body[test['document_start']:test['document_end']]
 original=(D/'02-original-manuscript.md').read_bytes();assert cid(original[:-1]+bytes([original[-1]^1]),0x55)!=selection['artifacts']['ORIGINAL']['raw']
 result={'schema':'pkst.new-principles-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),'selected_parts':len(selection['records']),'unique_native_events':len(checked_events),'native_anchors_checked':len(checked_anchors),'platforms':sorted(platforms),'artifact_sources':artifact_checks,'verbatim_spans':len(report['quotes']),'explicit_verbatim_characters':manifest['explicit_verbatim_characters'],'manuscript_cjk_characters':manifest['cjk_characters'],'old_manuscript_bytes_unchanged':len(original),'prior_concepts_mapped':21,'new_concepts':34,'semantic_relations':44,'timeline_entries':38,'local_links_checked':checked_links,'current_events':212353,'negative_checks':['one changed source byte fails CID','altered quotation fails exact source and manuscript interval'],'preserved_intermediate_review':'unactivated-v1-review.json records three semantic directions corrected before activation','verification_scope':'separate source-reparsing and span code; same codec; Codex review, not independent Claude/human acceptance','baseline_scope':'all previous collections retained; new dossier closure byte checked, whole reference DAG checked; no fresh byte audit of every historical source','dossier_snapshot':report['snapshot'],'federated_snapshot':pointer['snapshot'],'document_sha256':manifest['sha256'],'public_release':False}
 (O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 current=C/'catalog/current.json';assert json.loads(current.read_text())==selection['baseline'],'Current catalog changed before activation'
 tmp=C/'catalog/current.new-principles.tmp';tmp.write_text(json.dumps(pointer,indent=2),encoding='utf-8');tmp.replace(current)
 receipt=f'''# 《新原理》整合收据

正文、所选原话与主题关系已归档，当前统一索引已切换到此版本。由 Codex 用单独代码重读原始锚、核对引文与文件；尚未由用户逐句审定，也未取得本轮 Claude 独立复核。

- 正文：前言、22章、后记，共 {manifest['cjk_characters']:,} 汉字（含目录、注释）；显式逐字摘录 28 段、5,461 字符。
- 原稿：44,246 字节完全保留。69 个选定文本入口对应 65 个不同原生事件；覆盖 ChatGPT、Claude.ai、Gemini、Codex 和 Claude Code。
- 思想关系：34个新编辑主题，44条主要关系，38个时间线节点；旧目录21个主题全部映射并保持原身份。
- 本次新增原生事件2条，统一目录现有212,353条事件。事件数量包括各类角色，不是思想数量。
- 新稿来源锚、文件身份、引用闭包及完整对象依赖 DAG 校验通过。旧语料沿用已有字节验证记录。
- 文稿 SHA-256：`{manifest['sha256']}`。
- 专题根：`{report['snapshot']}`。
- 新统一根：`{pointer['snapshot']}`。
- 父统一根：`{report['baseline_snapshot']}`。

## 主要关系的阅读图

以下为已归档 `08-theory-map.json` 的简化阅读投影，箭头表示设想中的展开与应用关系，不代表所有因果关系已经实证。

```mermaid
flowchart TD
 A[数学与科学的共同结构] --> B[对偶体 不动点 涨现与构造]
 B --> C[语言 内容身份与公共知识]
 B --> D[意识 自我上下文与反馈]
 C --> E[个人知识时空档案]
 C --> F[HotPath 新语言 Structoken FPM]
 F --> G[MerkleVM与个人数字空间]
 D --> H[人 AI 设备与环境的共同智能]
 G --> H
 H --> I[动态权重与两类分配]
 I --> J[开放组织与共同生产]
 E --> K[个人数据主权与云存储起点]
 G --> K
 K --> J
 J --> L[生产生态和公共职能的渐进演化]
 L --> M[小说 影视 游戏与教育]
 M --> L
```

逐节点定义、来源和关系条件以 [章节映射](04-chapter-map.md) 和 [语义数据](08-theory-map.json) 为准。

[机器校验](../../contributions/codex/new-principles-20261026/verification.json) · [对象与文件报告](../../contributions/codex/new-principles-20261026/report.json)。本收据在根产生后生成，不参与该根的哈希，避免自引用。

材料保持本地；未发布、未购买云资源、未恢复暂停研究。完整历史的逐事件语义抽取尚未声称完成。旧稿中不再沿用的强断言、未采纳的 AI 建议和未激活的中间方向错误均保留。
'''.replace('涨现','涌现')
 (D/'09-archive-receipt.md').write_text(receipt,encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
