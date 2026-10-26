import json,re,hashlib,sys
from pathlib import Path
W=Path(__file__).resolve().parent;B=W.parents[1]/'outputs/personal-thought-archive';O=B/'contributions/codex/new-principles-20261026';D=B/'dossiers/2026-10-26-new-principles'
selection=json.loads((O/'selected-sources.json').read_text(encoding='utf-8'));sources={**selection['records'],**selection['artifacts']}
# Explicit additional, already-read native source.
if 'R49187' not in sources:
 for i,line in enumerate((W/'retrieval.jsonl').open(encoding='utf-8')):
  if i==49187:
   r=json.loads(line);r['ref']='R49187';r['source_kind']='native-user-channel';import sqlite3
   db=sqlite3.connect((B/selection['baseline']['database']).as_uri()+'?mode=ro',uri=True);r['anchors']=[x[0] for x in db.execute('SELECT extraction_record FROM anchors WHERE occurrence=?',(r['occurrence'],))];db.close();selection['records']['R49187']=r;sources[r['ref']]=r;break
 (O/'selected-sources.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
parts='\n\n'.join(p.read_text(encoding='utf-8').strip() for p in sorted((W/'chapters').glob('*.md')))
chapters=[]
for i,m in enumerate(re.finditer(r'^## (.+)$',parts,re.M)):
 end=next((n.start() for n in re.finditer(r'^## ',parts[m.end():],re.M)),None)
 nextpos=parts.find('\n## ',m.end());section=parts[m.end():nextpos if nextpos!=-1 else len(parts)]
 sm=re.search(r'<!-- sources: (.*?) -->',section)
 assert sm,m.group(1)
 refs=[s.strip() for s in sm.group(1).split(',')]
 for ref in refs:assert ref in sources,(m.group(1),ref)
 chapters.append({'id':'ch'+str(i).zfill(2),'title':m.group(1),'sources':refs})
i=iter(chapters)
parts=re.sub(r'^## (.+)$',lambda m:'<a id="'+next(i)['id']+'"></a>\n\n'+m.group(0),parts,flags=re.M)
i=iter(chapters)
parts=re.sub(r'<!-- sources: .*? -->',lambda m:'[本章来源与校订](04-chapter-map.md#'+next(i)['id']+')',parts)
header='# 新原理\n\n## 从数学与科学的共同结构，到人类社会的新组织机制\n\n思想与原始材料：langram。第一人称整理扩写：Codex。2026 年 10 月 26 日整合稿 v1，供作者审订。\n\n本稿沿用早期《新原理》的论证顺序，依据后续讨论扩写；第一人称编辑衔接不等于新增的用户原话。完整旧稿、原话、逐段对照与时间线另附，正文可独立阅读。\n\n'
header+='**目录**\n\n'+'\n\n'.join(' · '.join('['+c['title'].split('：')[0]+'](#'+c['id']+')' for c in chapters[j:j+4]) for j in range(0,len(chapters),4))+'\n\n---\n\n'
notes='''
<a id="数学与工程注释"></a>

## 数学与工程注释

这些注释核对原稿中涉及的既有概念，不替代作者的新理论论证。正文与这些材料之间进一步建立的社会类比，属于本稿的研究设想。

**数学注一。** 序列收敛、范畴极限与同伦等价并非同义概念。类型论与同伦的联系可从研究共同体编写的 [《Homotopy Type Theory》](https://homotopytypetheory.org/book/) 继续阅读；不能用一个词的相似性取代所需构造。

**数学注二。** Lawvere 在 [《Diagonal arguments and cartesian closed categories》](https://www.tac.mta.ca/tac/reprints/articles/15/tr15abs.html) 中研究自指、对角线论证与不动点的共同范畴结构。它不直接推出意识或文明的涌现。此次取得作者论文的出版摘要和入口，PDF 抓取超时，未声称重新核读全文证明。

**数学注三。** 诺特原论文讨论具有连续群不变性的变分问题；参见 [《Invariant Variation Problems》英文译本](https://arxiv.org/abs/physics/0503066)。正文对协议平等、功能多样性的讨论，是新的类比与研究问题，并非诺特定理的现成社会学推论。

**数学注四。** 最短程序长度的定义及一般不可计算性，参见作者论文 [Paul Vitányi：How incomputable is Kolmogorov complexity?](https://ir.cwi.nl/pub/30215)。实际压缩文件的长度提供一个候选描述长度，不等于已经找到了最短描述。

**科学注一。** 普里高津的 [诺贝尔讲演《Time, Structure and Fluctuations》](https://www.nobelprize.org/uploads/2018/06/prigogine-lecture.pdf) 区分系统与环境的熵交换及内部熵产生。局部秩序与第二定律并不直接冲突。此次使用官方论文检索内容核对这一处，PDF 直开被拒，未声称全文审阅。

**社会科学注一。** 重复互动中的合作演化，参见 [Axelrod 与 Hamilton，The Evolution of Cooperation](https://pubmed.ncbi.nlm.nih.gov/7466396/)。某一竞赛或模型中的策略表现，不能直接当作所有历史社会的统一规律。

**社会科学注二。** [Caspi 等，Role of genotype in the cycle of violence in maltreated children](https://pubmed.ncbi.nlm.nih.gov/12161658/) 研究的是特定基因差异与童年环境的相互作用，不是政治立场、民族或制度的基因分类。本文保存作者研究假设，并将其与既有证据的范围分开。

**社会科学注三。** [Nash，Equilibrium points in n-person games](https://www.pnas.org/doi/10.1073/pnas.36.1.48) 讨论均衡。正文用均衡与整体改善的区别说明制度问题，不将均衡等同于全局福利最优或能量最小化。

**工程注一。** [IPLD 的内容寻址说明](https://ipld.io/docs/intro/hello-world/) 将内容身份与权威问题区分。相同内容的寻址、防止无痕改写、身份认证、保密、可用性、当前授权与语义正确性，需要分别处理；公开一个 CID 并不自动公开其内容。

更多原文与编辑依据见 [来源原文](03-sources.md)、[章节与节点对应](04-chapter-map.md)、[思想演化](05-evolution.md) 和 [校订记录](06-editorial-ledger.md)。
'''
template=header+parts+'\n\n'+notes
quotes=[];output=[];cursor=0;length=0
def span(ref,start,end):
 t=sources[ref]['text'];return t[start:end],ref,start,end
for m in re.finditer(r'\{\{(.*?)\}\}',template):
 prior=template[cursor:m.start()];output.append(prior);length+=len(prior)
 v=m.group(1).split(':');kind=v[0]
 if kind=='O':
  s=int(v[1]);i=int(v[2]);p=(W/f'original-section-{s}.txt').read_text(encoding='utf-8').split('\n\n')[i];ref='ORIGINAL';t=sources[ref]['text'];start=t.find(p)
  assert start>=0,(m.group(0),'not exact in original');text,ref,start,end=span(ref,start,start+len(p))
 elif kind=='Q':
  ref=v[1];text,ref,start,end=span(ref,0,len(sources[ref]['text']))
 elif kind in ['X','T']:
  ref=v[1];t=sources[ref]['text'];start=t.index(v[2]);assert t.count(v[2])==1,(ref,v[2])
  end=t.index(v[3],start) if kind=='X' else len(t)
  # Trim only boundary whitespace and record the resulting exact source interval.
  while start<end and t[start].isspace():start+=1
  while end>start and t[end-1].isspace():end-=1
  text,ref,start,end=span(ref,start,end)
 else:raise ValueError(kind)
 assert text
 quotes.append({'id':'Q'+str(len(quotes)+1).zfill(3),'source_ref':ref,'source_start':start,'source_end':end,'document_start':length,'document_end':length+len(text),'coordinate':'unicode-scalar-half-open','text':text,'treatment':'exact source excerpt; original authorship classification retained'})
 output.append(text);length+=len(text);cursor=m.end()
output.append(template[cursor:]);document=''.join(output)
assert '{{' not in document
(D/'01-new-principles.md').write_bytes(document.encode('utf-8'))
(D/'02-original-manuscript.md').write_bytes(sources['ORIGINAL']['text'].encode('utf-8'))
for q in quotes:assert document[q['document_start']:q['document_end']]==q['text']
manifest={'document':'01-new-principles.md','sha256':hashlib.sha256(document.encode()).hexdigest(),'characters':len(document),'cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',document)),'chapters':chapters,'quotations':quotes,'explicit_verbatim_characters':sum(len(q['text']) for q in quotes),'original_writing_time':None,'artifact_source_time_rule':'upload time is not writing time','edition':'Codex first-person editorial synthesis for author review; not user-adopted policy'}
(O/'manuscript-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k not in ['chapters','quotations']},ensure_ascii=False))
