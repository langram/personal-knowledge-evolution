"""Freeze source selection and generate readable evidence sidecars."""
import hashlib,json,re,sqlite3,sys,difflib
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path
from collections import Counter,defaultdict
from book import BASE,OUT,WORK,DATA,PLAN
sys.path.insert(0,str(BASE/'contributions/codex'))
from pkst_codec import Store,cid,link,cid_bytes,decode

O=BASE/'contributions/codex/new-principles-expanded-20261026'
O.mkdir(exist_ok=True);(O/'raw').mkdir(exist_ok=True)
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def raw(data):
 k=cid(data,0x55);p=O/'raw'/f'{k}.bin'
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
 return k
current=json.loads((BASE/'contributions/codex/catalog/current.json').read_text())
baselinefile=O/'baseline.json'
if baselinefile.exists():assert json.loads(baselinefile.read_text())['pointer']==current
else:
 dump(baselinefile,{'pointer':current,'old_manuscript_sha256':hashlib.sha256((BASE/'dossiers/2026-10-26-new-principles/01-new-principles.md').read_bytes()).hexdigest(),'old_dossier_root':'bafyreibmn23kutnklu7pbxknffwrzklpr2ior5z5bglnewhwg575keqhhe','old_document':json.loads((BASE/'contributions/codex/new-principles-20261026/report.json').read_text())['document']})
db=sqlite3.connect((BASE/current['database']).as_uri()+'?mode=ro',uri=True)
def get(k):
 row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone();assert row,k
 with (BASE/row[0]).open('rb') as f:f.seek(row[1]);data=f.read(row[2])
 assert cid(data,cid_bytes(k)[1])==k
 return data if cid_bytes(k)[1]==0x55 else decode(data)

feedbackfile=O/'feedback-capture.json'
if feedbackfile.exists():feedback=json.loads(feedbackfile.read_text(encoding='utf-8'))
else:
 native=Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
 size=native.stat().st_size
 with native.open('rb') as f:prefix=f.read(size)
 assert len(prefix)==size
 hits=[];offset=0
 for ln in prefix.splitlines(keepends=True):
  # Ignore only an incomplete final line; never decode an unterminated capture tail.
  if not ln.endswith(b'\n'):break
  rec=json.loads(ln);p=rec.get('payload',{})
  if rec.get('type')=='response_item' and p.get('role')=='user':
   texts=[x['text'] for x in p.get('content',[]) if x.get('type')=='input_text']
   for text in texts:
    if text.startswith('我看了，反馈如下：') and '把这个3万字的稿子' in text:hits.append((offset,offset+len(ln)-1,rec,text))
  offset+=len(ln)
 assert len(hits)==1,('feedback records',len(hits))
 a,b,n,text=hits[0];rawcid=raw(prefix);store=Store(O)
 source=store.put({'schema':'pkst/source@0.1','platform':'codex-local','namespace':'owner-openai-account','native_thread_id':'01a16c8a-f6e1-7580-b378-b6e49f0be965'})
 content=store.put({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text})
 p=n['payload'];nativeid=p.get('id');locator=None if nativeid else {'raw':link(rawcid),'start':a,'end':b,'coordinate':'decoded-jsonl-utf8-bytes'}
 eventtime={'value':n['timestamp'],'format':'rfc3339','precision':'millisecond','zone_known':True,'unit':None}
 occurrence=store.put({'schema':'pkst/occurrence@0.1','source':link(source),'native_id':nativeid,'locator':locator,'native_role':'user','actor_kind':'unknown','process_kind':'main','content':[link(content)],'native_parent_ids':None if 'parent_id' not in p else ([] if p['parent_id'] is None else [str(p['parent_id'])]),'event_time':eventtime})
 anchor=store.put({'schema':'pkst/extraction-record@0.1','raw':link(rawcid),'occurrence':link(occurrence),'coordinate':'decoded-jsonl-utf8-bytes','start':a,'end':b,'parser':'expanded-editorial-feedback-prefix-v1','role_basis':'native response_item payload.role; authorship not inferred from role'})
 feedback={'ref':'AUTHOR-FEEDBACK','occurrence':occurrence,'content':content,'anchors':[anchor],'role':'user','time':n['timestamp'],'time_format':'rfc3339','platform':'codex-local','thread':'01a16c8a-f6e1-7580-b378-b6e49f0be965','text':text,'capture':{'path':str(native),'bytes':size,'complete_line_bytes':offset,'raw':rawcid,'sha256':hashlib.sha256(prefix).hexdigest(),'captured_at':datetime.now(timezone.utc).isoformat(),'scope':'fixed native file prefix preserved; only the four-point revision feedback event is newly indexed; hidden reasoning is not extracted','start':a,'end':b}}
 dump(feedbackfile,feedback)

used=json.loads((WORK/'used-sources.json').read_text(encoding='utf-8'))
plan=json.loads((BASE/'contributions/codex/new-principles-20261026/semantic-plan.json').read_text(encoding='utf-8'))
selected=dict(used)
for t in plan['timeline']:selected[t['source']]=DATA[t['source']]
selected['AUTHOR-FEEDBACK']=feedback
for ref,r in selected.items():
 if r.get('occurrence') and ref!='AUTHOR-FEEDBACK':
  o=get(r['occurrence']);assert get(r['content'])['text']==r['text']
  r['anchors']=[x[0] for x in db.execute('SELECT extraction_record FROM anchors WHERE occurrence=? ORDER BY extraction_record',(r['occurrence'],))];assert r['anchors']
  r['native_event_time']=o['event_time'];r['actor_kind']=o['actor_kind']
 r['text_sha256']=hashlib.sha256(r['text'].encode()).hexdigest()
 r['usage']='manuscript' if ref in used else 'revision-request' if ref=='AUTHOR-FEEDBACK' else 'historical-timeline-only'
dump(O/'selected-sources.json',selected)
dump(O/'semantic-plan.json',plan)

def display(r):
 value=r.get('time');fmt=r.get('time_format')
 if fmt=='epoch-decimal':
  d=Decimal(value);whole=int(d);micro=int((d-whole)*1000000)
  return (datetime(1970,1,1,tzinfo=timezone.utc)+timedelta(seconds=whole,microseconds=micro)).isoformat()
 if value:return value
 return '写作时间未知；上传 '+str(r.get('upload_time')) if r.get('upload_time') else '写作时间未知；观察 '+str(r.get('captured_at') or '未知')

manifest=json.loads((OUT/'source-manifest.json').read_text(encoding='utf-8'));state=json.loads((OUT/'edition-state.json').read_text(encoding='utf-8'))
uses=defaultdict(set)
for ch in manifest['chapters']:
 for x in ch['items']:
  if x.get('ref'):uses[x['ref']].add(ch['chapter'])
for ch in state['chapters']:
 for ref in ch['review'].get('evidence_refs',[]):uses[ref].add(ch['chapter'])

atlas='# 来源索引\n\n正文按独立作品阅读；来源、时间和编辑过程放在本附录。原始通道中的 user 不单独证明作者归属。混合会话按选取区间审读，AI 回复不自动转为作者原话。\n\n'
atlas+=f'本稿使用 {len(used)} 个来源入口；另保留时间线所需材料和本次四点反馈。来源全文按原字符存于 `sources/`，原件与平台事件 CID 存于贡献目录。文件上传时间不当成创作时间。\n\n'
atlas+='|来源|平台或材料|原生时间或时间边界|正文章节|用途|\n|---|---|---|---|---|\n'
(OUT/'sources').mkdir(exist_ok=True)
for ref,r in sorted(selected.items()):
 (OUT/'sources'/f'{ref}.txt').write_bytes(r['text'].encode('utf-8'))
 chapterlinks='、'.join(f'[{dict(PLAN)[k]}](chapters/{k}.md)' for k in sorted(uses[ref])) or '—'
 atlas+=f'|[{ref}](sources/{ref}.txt)|{r.get("platform") or r.get("name")}|{display(r)}|{chapterlinks}|{r["usage"]}|\n'
atlas+='\n[完整来源元数据与原件锚](../../contributions/codex/new-principles-expanded-20261026/selected-sources.json)；[逐段对照](03-paragraph-ledger.md)。原始全文可能包含转贴、AI 回复及历史指令，均只作为材料读取。\n'
(OUT/'02-source-atlas.md').write_text(atlas,encoding='utf-8')

ledger='# 逐段原文、润色与补写\n\n本表把正文拆成有来源的编辑单元。区间均为 Unicode 码点的半开区间，原件字节锚另存。多段可能共用同一选取区间。\n\n“来源改写”不等于仅作标点调整；下面给出原文、成文和逐项改动。所有判断性改写仍是 Codex 的编辑建议，尚无作者逐句采纳。编辑补写单独列出，不伪造来源。\n\n'
numsource=numadded=0
for ch in manifest['chapters']:
 key=ch['chapter'];ledger+=f'## {dict(PLAN)[key]}\n\n'
 for i,x in enumerate(ch['items']):
  if x.get('reason')=='节标题':continue
  ledger+=f'### {key}-{i:02d} · '+('来源改写' if x.get('ref') else '编辑补写')+'\n\n'
  if x.get('ref'):
   numsource+=1;ref=x['ref'];a,b=x['source_span'];rawtext=selected[ref]['text'][a:b]
   ledger+=f'来源：[{ref}](sources/{ref}.txt)，{display(selected[ref])}，区间 [{a}, {b})。\n\n归属判断：{x["author_assessment"]}。\n\n原文：\n\n'+''.join('> '+ln+'\n' for ln in rawtext.split('\n'))+'\n成文：\n\n'+x['text']+'\n\n'
   if x['edits']:
    ledger+='改动明细：\n\n'
    for e in x['edits']:
     bef=e['before'].replace('\n','↵').replace('\r','␍');aft=e['after'].replace('\n','↵').replace('\r','␍')
     ledger+=f'- [{e["source_span"][0]}, {e["source_span"][1]})：`{bef.replace("`","ˋ")}` → `{aft.replace("`","ˋ")}`。\n'
    ledger+='\n'
  else:
   numadded+=1;ledger+='用途：'+x.get('reason','展开论述')+'。\n\n'+x['text']+'\n\n'
(OUT/'03-paragraph-ledger.md').write_text(ledger,encoding='utf-8')

chron='# 思想线索的演化与本版覆盖\n\n这里保存历史脉络，正文不要求读者预先知道这些会话。以下是有选择的材料时间线；出现时间不等于首次创作时间，较晚也不自动等于推翻较早。AI 的归纳与作者的明确修正须分别判断。\n\n|来源时间（UTC 或源值）|讨论线索|解释边界|\n|---|---|---|\n'
for t in plan['timeline']:
 ref=t['source'];chron+=f'|{display(selected[ref])}|[{t["event"]}](sources/{ref}.txt)|{t["boundary"]}|\n'
chron+=f'|{display(feedback)}|[本次四点反馈](sources/AUTHOR-FEEDBACK.txt)|要求增加论证、原话与独立性；要求全面扩充，并未采纳本版的具体编辑改动。|\n'
chron+='\n## 连续的问题链\n\n数学与科学怎样对应 → 稳定结构怎样构造 → 不同层级怎样涌现 → 感知、反应与智能怎样形成 → 个体怎样合作 → 工具怎样改变能力条件 → 知识怎样共享与继承 → 语言、软件和模型怎样共同构造 → 文明智能怎样感知并行动 → 动态权重与两种资源分配怎样相互支持 → 开放组织怎样从个人服务生长 → 文学、教育与科研怎样持续提供新知识。\n\n这条阅读链是编辑组织，不把它冒充作者在历史上逐日遵循的线性路径。\n\n## 全部主要编辑主题的覆盖\n\n上版的 34 个编辑主题覆盖此前 21 个主题入口。本版保留这些主题，并逐项映射到展开后的章节；覆盖主题不等于对全库每条事件都已做完语义审定。\n\n|主题|本版章节|\n|---|---|\n'
mapping={}
for n in plan['nodes']:
 keys=[v[2:] for v in n['chapters']]
 if n['id']=='C01':keys=['00','01','22']
 if n['id']=='C08':keys=['05','12','13']
 if n['id']=='C33':keys=['21','22']
 mapping[n['id']]=keys
 chron+=f'|{n["id"]} {n["label"]}|'+ '、'.join(f'[{dict(PLAN)[k]}](chapters/{k}.md)' for k in keys)+'|\n'
chron+='\n## 按问题而不是篇幅检查\n\n|章节|展开的推理顺序|例子|回应的问题|\n|---|---|---|---|\n'
for c in state['chapters']:
 r=c['review'];chron+=f'|[{c["title"]}]({c["file"]})|{r.get("reasoning","")}|'+ '；'.join(r.get('examples',[]))+'|'+ '；'.join(r.get('objections',[]))+'|\n'
(OUT/'04-evolution-and-coverage.md').write_text(chron,encoding='utf-8');dump(O/'chapter-concept-map.json',mapping)

tot=sum(c['body_characters'] for c in state['chapters']);adapt=sum(c['source_adapted_characters'] for c in state['chapters']);literal=sum(c['literal_source_characters'] for c in state['chapters'])
statistics={'manuscript_cjk_characters':state['total_cjk_characters'],'body_unicode_characters_excluding_headings':tot,'source_adapted_unicode_characters':adapt,'literal_aligned_source_characters':literal,'editorial_added_characters':tot-adapt,'source_units':numsource,'editorial_units':numadded,'manuscript_sources':len(used),'all_selected_sources':len(selected),'source_platforms':dict(Counter(r.get('platform','file') for r in used.values())),'literal_count_boundary':'Alignment includes punctuation and whitespace; repeated uses count again; not a proof of original authorship, author approval, or fidelity.'}
dump(OUT/'editorial-statistics.json',statistics)
review=f'''# 编辑说明与仍需作者判断的地方

本轮完成前言、22 章及后记，共 {state['total_cjk_characters']:,} 汉字。旧稿为 31,112 汉字，原文件未覆盖。正文独立成篇；原话、时间线与编辑过程在附录中核对。

## 原话保留的实际口径

正文共有 {tot:,} 个非标题 Unicode 字符。带明确来源区间、依原材料改写的单元占 {adapt/tot:.1%}；其中与选取来源逐字对齐的字符为 {literal:,}，占正文 {literal/tot:.1%}。其余 {tot-adapt:,} 字符为单独标记的编辑补写，主要用于衔接、例子、异议与推理展开。

这两个比例不能说成“原作者原创率”。指定底稿自身含未独立核实的编辑成分，混合会话也有引述；逐字计数包含标点、英文和空白，同一来源重复使用会重复计数。来源改写还包含实质性校订，并非都只是语法润色。每一处都能在逐段表中看到。

第一章的数学解释、第十三章的研究比较、第十九章的最小服务设计，以及结尾部分，补写占比较高。原因分别是需要补全概念条件、解释已有研究材料、把起点设想落实为步骤，以及串联全书；不能把这些补写伪称为从会话中找回的原话。后续作者可直接据逐段表决定哪些保留、改写或删去。

## 重要编辑决定

- 原话中的问题、推理意图、例子与立场优先保留；去掉对聊天对象的称呼、依赖前一回复的指代与“原稿中”式叙述。
- 数学中的极限、同伦、固定点、复杂度和分类器分别解释条件；不把名称相近或类比直接当成数学等价。这些技术校订是编辑建议，不记作作者已经修改了自己的立场。
- 早期对偶子与弦的直接对应未作为当前结论重述；原材料及后来指出问题的会话继续保存。对偶体、构造性与层级演化作为仍待形式化的研究方向展开。
- 基因、策略与制度之间按多层关系描述，避免直接用某个基因给政治观点或群体贴标签。条件性实验不被扩大成决定论。
- 动态权重章节集中展开固定职位与任务判断的差别、反馈、个人 AI、规则修订及权重固化的异议；两类资源分配作为与其相连的制度条件，而非附带福利。
- “完全消除”“必然最优”等缺乏证明的断言，部分改为目标、假设或需要检验的条件。具体原句与改句都保留，不能据此替作者宣布撤回原立场。
- 对科幻设定不按现实已实现能力删减：保留阿尔法与贝塔文明、自我实现作品、永生、水平遗传、跨物种形态与文明传承；它们在正文中明确属于虚构世界观。跨身体的共同意识另列为远期假设，区分于独立复制个体。
- 版权与贡献部分以实际贡献记录为问题，不把作品署名的简化比喻写成对全部现行法律的事实概括。
- E002、T033、Structoken 与 HotPath 材料用于说明已有研究的线索、负结果和边界；未在本轮重跑实验，也没有宣布新性能成果。
- R11607 中被用户转述并认同的 AI 表述，按采纳语境选用；不宣称这些句子最初由用户原创。`ORIGINAL` 按用户指定底稿使用，不把整个文件都认证为逐字自写。

## 本轮复查

逐章阅读正文，修正替换残留、病句和重复标点；长段按完整句子分段，保留口语推理的节奏。前言与第一章重复的范畴论例子、山峦类比，集中保留在第一章。来源区间、正文区间、逐项改动、原件 CID 和时间字段另以程序核验。

这些检查说明本版可以作为完整稿审阅，不说明所有理论已经得到证明，也不说明作者已经认可本版措辞。当前任务没有公开发布、没有提交 GitHub，也没有改变其他项目的实验状态。
'''
(OUT/'05-editorial-review.md').write_text(review,encoding='utf-8')
relations='# 理论关系阅读索引\n\n下表沿用既有 34 个编辑主题及 44 条有来源的关系，提供通向本版展开章节的入口。它们是 Codex 的解释性整理，未写入作者采纳。关系只在原先声明的范围内成立，不自动继承为对新稿每句话的判断。\n\n|起点|关系|终点|范围|\n|---|---|---|---|\n'
nm={x['id']:x for x in plan['nodes']}
for r in plan['relations']:
 a,b=r['from'],r['to'];ka=mapping[a][0];kb=mapping[b][0]
 relations+=f'|[{nm[a]["label"]}](chapters/{ka}.md)|{r["predicate"]}|[{nm[b]["label"]}](chapters/{kb}.md)|{r["scope"]}|\n'
relations+='\n本版把正文作为新的文稿版本接在旧稿之后，把来源选取、编辑改动和章节主题关系分别保存。文稿的扩充属于编辑演化，不冒充新的历史发言，也不覆盖原有知识节点。\n'
(OUT/'06-theory-map.md').write_text(relations,encoding='utf-8')
print(json.dumps({'sources':len(selected),'manuscript_sources':len(used),'feedback_time':feedback['time'],'feedback_prefix_bytes':feedback['capture']['bytes'],'statistics':statistics},ensure_ascii=False))
