"""Source-led editorial support, including partial chronology and uncertainty."""
import json
import re
from prepare import EDITION, OUT, PUBLIC, WORK, sha, write_json

def support(results, originals, changes, ledger, passages, events, timeline):
    from build_edition import headings, urls
    stats={'edition':EDITION,'chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',results['zh'])),
        'previous_chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',originals['zh'])),
        'english_whitespace_words':len(results['en'].split()),'previous_english_whitespace_words':len(originals['en'].split()),
        'chinese_sha256':sha(results['zh'].encode()),'english_sha256':sha(results['en'].encode()),
        'chapters':33,'headings':len(headings(results['zh'])),'external_citation_occurrences':len(urls(results['zh'])),
        'revisions_by_language':{l:sum(e['language']==l for e in changes) for l in ('zh','en')},
        'unchanged_chapter_pairs':sum(r['review']['status']=='inherited-byte-identical' for r in ledger),
        'new_visible_events':len(events),'author_messages':sum(e['role']=='user' for e in events),
        'passages_with_exact_author_spans':sum(bool(p['exact_author_spans']) for p in passages),
        'exact_author_span_boundary':'Exact matches identify preserved wording; source association is not author approval of editorial elaboration.'}
    write_json(OUT/'editorial-statistics.json',stats)
    review={'schema':'ra/targeted-review@1','edition':EDITION,'baseline_edition':'17-cooperative-superintelligence',
        'baseline_sha256':{l:sha(t.encode()) for l,t in originals.items()},'reviewed_chapters':[1,7,25,33],
        'baseline_context_chapters':[1,4,6,16,18,24,32],
        'coverage':{'semantic':'New bilingual material and relevant surrounding arguments; chapter 7 is new, former chapter 24 becomes 25 and appendix becomes 33.',
            'structural':'33 chapter pairs; aligned headings, citations and equations; reversible edits and exact source recovery.',
            'inherited':'29 chapter pairs remain byte-identical. No new full-book semantic reread is claimed.',
            'external_facts':'Five scoped sources; IPCC verified through official indexed statement, direct fetch blocked with HTTP 403.'},
        'findings':['Changing representations is distinct from changing facts, conditions or values.',
            'Semantic embeddings are partial models, neither first mathematical cognition nor complete consciousness.',
            'Social and natural science share a proposed methodological foundation; mathematical social science already exists.',
            'A fixed point needs a defined self-map; existence, stability, legitimacy and changing-environment tracking are separate.',
            'Local alignment can impose external costs; capability imbalance and confrontation are conditional risk pathways.',
            'Human institutional coordination supports but does not replace technical AI alignment.',
            'Ecological constraints do not imply a single planetary or cosmic will.'],
        'author_approval':'No author acceptance of editorial qualifications, examples, notation or English wording is fabricated.'}
    write_json(OUT/'targeted-review.json',review)
    (OUT/'targeted-review.md').write_text('''# 本轮衔接复核

新第7章接在意识与信息之后、合作与社会结构之前：从参考系与可检验事实，进入认知差异和共同规则。原第24章现为第25章，在链子锤的例子之后加入多层级对齐，再接原有《守望者》与和平制度探索。第33章附录补入相对性与不动点建模的检验要求。前言解释新书名，全文不要求读者先了解编辑过程。

重点核对与第4章不动点、第6章意识与语义模型、原第16章超级智能的目标条件、原第18章可演化运行时、原第24章制度落差和原附录的衔接。没有把作者已经修正的正态分布论证重新引入。

中文和英文各7处有界修改，可双向还原到第十七版；29组既有章节双语逐字节继承。全书结构、引用和版本关系检查不等于再次逐句通读所有历史文字。

Gemini回复作为AI讨论材料保留，没有将其中的认知几何、规范变换、曲率、函子等类比直接提升为理论证据。Gemini导出中的用户时间缺少时区、AI回复缺少时间，均保留缺失。

[逐处修改](revision-manifest.json) · [中英对应](translation-ledger.json) · [来源与适用范围](08-source-ledger.md)
''',encoding='utf-8')
    rows=['# 从参考系到多层级对齐\n',
        '这是保留各来源内部顺序的部分时序，不是已解决所有时区关系的单一时间轴。Gemini附件来自作者提供的导出文件；不声称直接访问或核验了Gemini云端。\n',
        '|来源顺序|导出或原生时间|来源|身份|','|---|---|---|---|']
    for e in events:
        clock=(e['time']+'（时区未提供）' if e['time'] else '未提供') if e['platform']=='gemini' else e['time']+'（UTC）'
        rows.append(f"|{e['capture'].get('export_order','Codex原生顺序')}|{clock}|[{e['ref']}](00-{e['ref'].lower()}.txt)|{'作者' if e['role']=='user' else 'AI回复'}|")
    rows+=['\n思想路径：参考系的数学与物理性质 → 向化学与生物延伸 → 相对性是否跨领域成立 → 质疑将自身道德政治坐标绝对化 → 认知语义空间与社会涌现 → 新书名与社会科学共同底座 → 从局部AI对齐扩展到人际制度、人与AI及生态协调。',
      '\n11月5日08:00:42 UTC的请求与08:02:46 UTC附附件的再次请求，分别保留原始发生事件。后一次增加了附件路径说明，理论主体相同；不把重复提交记为两次独立理论发明。此前字数问题及答复只作版本上下文。',
      '\n编辑进一步区分：参考系差异与事实真假；语义代理测量与完整意识；稳定与公平；回报评价函数与更新算子；制度协调与技术安全；生态约束与宇宙意志。这些补充不记录为作者已明确采纳。',
      '\n已有的公平发展条件、能力多样性与跨领域合作修正沿历史版本保留，不由新数学类比替代。']
    (OUT/'07-thought-evolution.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    notes=f'''# 第十八版：相对性、认知参考系与多层级对齐

书名改为《新原理：社会科学的数学原理》；英文为 **Nova Principia: Mathematical Principles of Social Science**。旧版标题与文件保持原样，改名作为新的版本事件保存。

新增第7章“相对性、认知参考系与社会科学的数学表达”。原第24章现为第25章，加入对齐的六个小节；第33章附录补入两节自我反思。前言增加新标题的研究目标说明。

## 原话、改写与补充

[最新完整请求](00-author-relativity-alignment.txt)、[首次请求](00-author-relativity-alignment-first.txt)、[Gemini完整导出](00-gemini-reference-frames.md)及逐条原文均原样保存。正文保留作者的研究方向、问题顺序、公共科学底座、反对神圣化和妖魔化、局部对齐与整体风险、双链子锤等论述。连接论证的案例、形式化符号、部分解释和英文表达属于编辑补写；[段落来源清单](passage-manifest.json)另列可精确对应的原话片段，不冒称全篇均为作者原句。

将“第一次建立意识数学模型”改为可计算的部分语义表示，并补入早期潜在语义分析先例；将“无绝对对错”限定为反对把自己的立场当普遍标准，不取消事实、伤害与责任；将“对齐是回报函数不动点”展开为同一空间上的更新算子模型；将“领先必然选择镇压”“数月必然形成百千倍差距”“人类对齐后AI对齐自然完成”分别改成有条件的风险或待验证关系。这些编辑限定未被记录成作者已经接受的新立场。

附件中的Gemini回复完整归档，但关于认知流形、规范变换、平行移动和曲率的推演，没有足够定义支持直接进入正文作为数学结论。化学生物的例子只保留参考约定与情境依赖的区分，没有采用光学旋光与构型混同、忽略遗传条件等细节。AI回复本身不是科学事实来源。

## 版本与检查

全书33章、{stats['headings']}个标题，29组章节双语逐字节不变。中英文各7处修改可逆还原。中文净增{stats['chinese_cjk_characters']-stats['previous_chinese_cjk_characters']:,}汉字，总计{stats['chinese_cjk_characters']:,}汉字；英文总计约{stats['english_whitespace_words']:,}个空白分隔词项，包含标题与引用。

新增15条可见来源事件：Gemini导出10段、Codex本机会话5条。8条作者问题或陈述、7条AI回复分别标明；正文最新补充不是再收集所有设备或云端会话的声明。Gemini时间缺失与时区未知如实记录；没有读取或发布隐藏推理与工具封套。

[新增中文](06-additions.zh.md) · [New English material](06-additions.en.md) · [局部语义复核范围](targeted-review.md) · [外部资料](08-source-ledger.md) · [思想演化](07-thought-evolution.md) · [可逆修改](revision-manifest.json)
'''
    (OUT/'04-editorial-notes.md').write_text(notes,encoding='utf-8')
    table=['# 中英文逐章对照 / Chinese–English chapter map\n','新增及修改部分采用自然英语表达，既有不变文字继承第十七版。\n','|章|中文|English|状态|','|---|---|---|---|']
    table += [f"|{r['id']}|{r['title_zh']}|{r['title_en']}|{r['review']['status']}|" for r in ledger]
    table+=['\n[中文全文](01-new-principles.zh.md) · [Full English text](02-new-principles.en.md) · [精确对应](translation-ledger.json)']
    (OUT/'05-translation-notes.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    landing=(PUBLIC/'book/readme.md').read_text(encoding='utf-8').replace('2026-11-02-cooperative-superintelligence',OUT.name)
    landing=landing.replace('# 《新原理》 / New Principles','# 《新原理》 / Nova Principia')
    landing=landing.replace('现代科学与人类文明的构造 · Modern Science and the Making of Human Civilization','社会科学的数学原理 · Mathematical Principles of Social Science')
    landing=landing.replace('*New Principles*','*Nova Principia*')
    landing=landing.replace('最新补充强调以理性说服、可靠证据和自愿试点推进改变，并讨论这种乐观期待所需的条件。','相对性与认知参考系的讨论，将不同人的视角接到共同核验与合作规则；对齐问题则从单个助手延伸到人与人、人与AI及文明与生态的协调。')
    landing=landing.replace('The latest addition explores reasoned persuasion, reliable evidence, and voluntary pilots as a path to change, while examining the conditions this optimistic expectation requires.','A discussion of relativity and cognitive frames connects different perspectives with shared tests and cooperative rules. Alignment extends beyond an individual assistant to relations among people, between people and AI, and between civilization and its ecological conditions.')
    (OUT/'book-readme.md').write_text(landing,encoding='utf-8')
    refs=json.loads((WORK/'references.json').read_bytes());write_json(OUT/'08-external-references.json',refs)
    source=['# 本轮来源与适用范围\n','2026年11月5日核对。仅将外部文献用于其直接支持的有限事实，不作为整套社会制度已被证明的依据。\n','|来源|性质|范围|','|---|---|---|']
    source += [f"|[{r['title']}]({r['url']})|{r['type']}|{r['scope']}|" for r in refs]
    source+=['\nIPCC直接网页与PDF访问返回403；人类活动造成全球变暖的A.1结论由官方页面的检索结果核对，不声称已成功下载整份报告。其余四项打开原论文或原作者摘要核对。',
      '\nGemini导出是作者提供的讨论来源，包含尚未定义的跨学科类比与未核实的断言，独立于外部科学文献。没有发布外部论文全文；附件原文属于作者提供的材料。']
    (OUT/'08-source-ledger.md').write_text('\n'.join(source)+'\n',encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False))
