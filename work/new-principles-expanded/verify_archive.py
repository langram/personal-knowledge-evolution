"""Verify frozen archive objects and only then activate its catalog pointer."""
import hashlib,json,sqlite3,sys
from datetime import datetime,timezone
from pathlib import Path
from sources import BASE
sys.path.insert(0,str(BASE/'contributions/codex'))
from pkst_codec import cid,cid_bytes,decode,encode,check_sets,links
from query_catalog import search
C=BASE/'contributions/codex';O=C/'new-principles-expanded-20261026';D=BASE/'dossiers/2026-10-26-new-principles-expanded'
baseline=json.loads((O/'baseline.json').read_text());report=json.loads((O/'report.json').read_text());pointer=json.loads((O/'staged-pointer.json').read_text());sourcecheck=json.loads((O/'source-verification.json').read_text());selected=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'));man=json.loads((D/'source-manifest.json').read_text(encoding='utf-8'));state=json.loads((D/'edition-state.json').read_text(encoding='utf-8'))
assert sourcecheck['status']=='pass' and hashlib.sha256((O/'source-verification.json').read_bytes()).hexdigest()==report['source_verification_sha256']
db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
verified=set()
def get(k):
 row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone();assert row,k
 with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
 assert len(b)==row[2] and cid(b,cid_bytes(k)[1])==k;verified.add(k)
 if cid_bytes(k)[1]==0x55:return b
 obj=decode(b);check_sets(obj);assert encode(obj)==b
 p=BASE/row[0]
 if p.suffix=='.cbor' and p.with_suffix('.json').exists():assert encode(json.loads(p.with_suffix('.json').read_text(encoding='utf-8')))==b
 return obj
for k in report['new_catalog_blocks']:get(k)
doc=get(report['document']);body=get(doc['raw']['$link']).decode('utf-8')
assert doc['previous']['$link']==baseline['old_document']
assert body.encode()==(D/'01-manuscript.md').read_bytes();assert hashlib.sha256(body.encode()).hexdigest()==state['manuscript_sha256']==sourcecheck['manuscript_sha256']
cursor=0;quote_count=0;chapter_texts=[]
for ch in man['chapters']:
 key=ch['chapter'];obj=get(report['chapters'][key]);assert obj['document']['$link']==report['document'] and obj['key']==key
 text='## '+obj['title']+'\n\n'
 assert len(obj['passages'])==len(ch['items'])
 for i,(ln,x) in enumerate(zip(obj['passages'],ch['items'])):
  assert ln['$link']==report['passages'][cursor];cursor+=1
  p=get(ln['$link']);assert p['text']==x['text'] and p['ordinal']==i and p['chapter']==key
  assert p['document_span']==x['document_span'] and p['chapter_span']==x['chapter_span'] and p['edits']==x.get('edits',[])
  a,b=p['document_span'];assert body[a:b]==p['text'];text+=p['text']+'\n\n'
  if x.get('ref'):
   r=selected[x['ref']];s,t=x['source_span'];q=get(p['quotation']['$link']);quote_count+=1
   assert q['text']==r['text'][s:t] and q['force']=='quote' and q['holder']['kind']=='unknown'
   assert p['source']['$link']==report['source_nodes'][x['ref']]
   assert get(p['source']['$link'])['target']['$link']==(r.get('content') or r['raw'])
  else:assert p['source'] is None and p['quotation'] is None
 assert text.encode()==get(obj['raw']['$link'])==(D/'chapters'/f'{key}.md').read_bytes();chapter_texts.append(text)
assert '# '+doc['title']+'\n\n'+''.join(chapter_texts)==body
assert cursor==len(report['passages']) and quote_count==len(report['quotes'])==sourcecheck['source_units_replayed']
for f in report['files']:
 b=get(f['raw']['$link']);assert b==(BASE/f['path']).read_bytes() and len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256']
chg=get(report['change']);assert chg['operation']=='extend' and chg['from_versions'][0]['$link']==baseline['old_document'] and chg['to_versions'][0]['$link']==report['document']
assert get(report['snapshot'])['parents'][0]['$link']==baseline['old_dossier_root']
assert get(pointer['snapshot'])['parents'][0]['$link']==baseline['pointer']['snapshot']
oldcat=json.loads((C/'catalog'/baseline['pointer']['report']).read_text());cat=json.loads((C/'catalog'/pointer['report']).read_text());assert cat['pinned_sources'][:-1]==oldcat['pinned_sources']
assert cat['pinned_sources'][-1]['report_sha256']==hashlib.sha256((O/'report.json').read_bytes()).hexdigest()
actual=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0];assert actual==report['current_events']==oldcat['unique_current_events']+1
assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
found=search(db,'字数太少，更像是大纲',10,'user','codex-local');assert selected['AUTHOR-FEEDBACK']['occurrence'] in [r['occurrence'] for r in found]
assert hashlib.sha256((BASE/'dossiers/2026-10-26-new-principles/01-new-principles.md').read_bytes()).hexdigest()==baseline['old_manuscript_sha256']
assert hashlib.sha256(body.replace('\n','\r\n').encode()).hexdigest()!=state['manuscript_sha256']
result={'schema':'np2.archive-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),'federated_snapshot':pointer['snapshot'],'dossier_snapshot':report['snapshot'],'manuscript_sha256':state['manuscript_sha256'],'manuscript_cjk_characters':state['total_cjk_characters'],'chapters':len(chapter_texts),'source_passages':quote_count,'all_passage_units':cursor,'frozen_files_checked':len(report['files']),'archive_blocks_checked':len(verified),'full_reference_graph_nodes_checked_at_staging':report['full_reference_graph_nodes'],'native_source_verification':'source-verification.json','feedback_retrieval_passed':True,'current_native_events':actual,'old_edition_preserved':True,'preserved_failure':'preflight-failure.json','negative_checks':['native source and manuscript alteration checks in source verification','CRLF substitution fails exact byte digest'],'review_scope':'Codex independent replay code with shared codec; no claim of Claude or author acceptance','publication':False}
(O/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
current=C/'catalog/current.json';assert json.loads(current.read_text())==baseline['pointer'],'Catalog changed; do not activate over another writer'
tmp=C/'catalog/current.expanded.tmp';tmp.write_text(json.dumps(pointer,indent=2),encoding='utf-8');tmp.replace(current)
(O/'status.json').write_text(json.dumps({'status':'activated-after-verification','recorded_at':datetime.now(timezone.utc).isoformat(),'pointer':pointer,'verification':'verification.json','source_verification':'source-verification.json','author_adoption':False,'public_release':False},ensure_ascii=False,indent=2),encoding='utf-8')
receipt=f'''# 扩充稿归档收据

完整扩充稿及逐段原文对照已接入个人知识 Merkle-DAG 库。正文、章节、来源选取、逐段编辑、演化时间线、主题映射共同保存；旧稿和原始会话保留。

- 前言、22 章与后记，共 **{state['total_cjk_characters']:,} 汉字**。
- 正文使用 82 个来源入口；含时间线与本次反馈共核对 89 个来源，82 个原生事件锚与 7 份文件材料。
- 204 个来源单元保存原话与成文对应；156 个编辑补写单元单独标明。逐字对齐字符占比见[编辑说明](05-editorial-review.md)，不以来源改写段落冒充逐字原话。
- 34 个主要编辑主题映射到新章节，沿用并保留既有 44 条关系与 38 个历史时间线条目，另加本次四点反馈。主题覆盖不表示全部历史事件均已完成思想审定。
- 本轮仅增加 1 条原生反馈事件，当前目录共有 **{actual:,} 条来源事件**；文稿与编辑解释没有伪装成用户发言。
- 新专题引用闭包 {report['closure_blocks']:,} 个块；归档文件 {len(report['files'])} 份；完整目录引用图 {report['full_reference_graph_nodes']:,} 个节点在暂存阶段检查无环，独立复核确认引用闭合、数据库完整、正文区间和原话改动可重放。
- Windows 换行转换导致的首次预检查失败已保留；修正后按 UTF-8 原字节核验正文与章节，避免换行归一化掩盖坐标错误。

正文 SHA-256：`{state['manuscript_sha256']}`。

本版专题根：`{report['snapshot']}`。

旧稿专题根：`{baseline['old_dossier_root']}`。

新统一根：`{pointer['snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

[原件与编辑重放核验](../../contributions/codex/new-principles-expanded-20261026/source-verification.json) · [归档核验](../../contributions/codex/new-principles-expanded-20261026/verification.json) · [文件及对象清单](../../contributions/codex/new-principles-expanded-20261026/report.json) · [启用状态](../../contributions/codex/new-principles-expanded-20261026/status.json)。

本轮为 Codex 编辑和核验，未取得新的 Claude 独立审阅，也不代表作者已经认可所有措辞。资料未公开，未提交 GitHub，未重启其他项目的研究实验。本收据在根产生后生成，不参与自身根的哈希。
'''
(D/'09-archive-receipt.md').write_text(receipt,encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
