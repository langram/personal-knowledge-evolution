"""Edition-specific attribution, review scope, source limits, and publication notes."""
import json
import re
from prepare import EDITION, OUT, PUBLIC, WORK, sha, write_json

def support(results, originals, changes, ledger, passages, events, timeline):
    from build_edition import headings, urls
    stats={'edition':EDITION,'chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',results['zh'])),
        'previous_chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',originals['zh'])),
        'english_whitespace_words':len(results['en'].split()),'previous_english_whitespace_words':len(originals['en'].split()),
        'chinese_sha256':sha(results['zh'].encode()),'english_sha256':sha(results['en'].encode()),
        'chapters':32,'headings':len(headings(results['zh'])),'external_citation_occurrences':len(urls(results['zh'])),
        'revisions_by_language':{l:sum(e['language']==l for e in changes) for l in ('zh','en')},
        'unchanged_chapter_pairs':sum(r['review']['status']=='inherited-byte-identical' for r in ledger),
        'new_visible_events':len(events),'author_messages':sum(e['role']=='user' for e in events),
        'passages_with_exact_author_spans':sum(bool(p['exact_author_spans']) for p in passages),
        'exact_author_span_boundary':'Exact matches record retained latest-message wording; semantic association does not attribute all editorial explanation to the author.'}
    write_json(OUT/'editorial-statistics.json',stats)
    review={'schema':'ag/targeted-review@1','edition':EDITION,'baseline_edition':'15-institutions-coherence',
        'baseline_sha256':{l:sha(t.encode()) for l,t in originals.items()},'reviewed_chapters':[16],
        'coverage':{'semantic':'Chinese and English chapter 16, including the new sections and the transition to dynamic weights.',
            'structural':'All 32 chapter pairs, headings, citation sequences, reversible boundaries and exact inherited bytes.',
            'inherited':'31 unchanged chapter pairs; edition-15 full Chinese review retained as historical evidence, not claimed to be repeated this turn.',
            'external_facts':'Two original sources on intelligence/goals and reward specification. Literary references used as distinct motifs, not uniform plot summaries.'},
        'findings':[
            'The prior chapter already separates capability from goals; the addition makes the author AGI scenario conditional and develops the control question.',
            'Human common interests require participation and revision, rather than a self-appointed single utility maximizer.',
            'Task-relevant information, local processing and authorized evidence do not imply access to every private thought.',
            'Possible institutional alternatives do not establish a globally optimal design or remove technical AI risks.',
            'The closing transition connects cooperation to dynamic weights without turning relevance into executive authority.'
        ],'author_approval':'Editorial judgments and English adaptation are pending author review, not recorded acceptance.'}
    write_json(OUT/'targeted-review.json',review)
    (OUT/'targeted-review.md').write_bytes('''# 本轮阅读与衔接复核

本轮完整阅读第16章“具有感官与行动能力的文明智能”的中英文文本，核对新增三节和章末过渡。其他31组章节继承第十五版并核对逐字节不变；没有把上轮的全书通读记成本轮再次通读。

新增内容接在能力增长、机器所有权和AI控制权之后，先展开老大哥式恐惧的结构来源，再区分共同任务的信息需求与全面监视，最后讨论制度探索的开放空间。原有“怎样理解对未来的担心”继续承担技术验证与可靠性讨论；章末再转入动态权重，避免用“分布式”三个字代替具体机制。

核对的逻辑边界：能力与目标分别设计；共同利益不能由单一主体自行定义；信息分享不自动转移控制权；制度变革不能代替技术安全研究；新架构仍须接受检验。作者原话不覆盖，正文限定不伪造为作者已经采纳。

[逐处修改](revision-manifest.json) · [中英对照](translation-ledger.json) · [外部来源范围](08-source-ledger.md)
'''.encode())
    timeline_md=['# 从文明智能的控制权，到制度想象的开放空间\n',
        '第十五版完成答复作为本次更新起点，作者新消息作为直接来源。事件时间来自可见会话记录，不宣称思想首次产生时间。\n',
        '|时间（UTC）|来源|地位|','|---|---|---|']
    for e,item in zip(events,timeline):
        timeline_md.append(f"|{e['time']}|[{e['ref']}](00-{e['ref'].lower()}.txt)|{item['status']}|")
    timeline_md += ['\n演化联系：文明智能不能等同于超级老板 → 以老大哥式科幻意象说明集中控制的矛盾 → 将信息合作与权力让渡分开 → 将既有制度视为可探索形式的一部分 → 让替代方案通过自愿采用和实际检验承担组织职能。',
        '\n作者原话中“自我意识必然带来全人类利益目标”“必须获取所有各方信息”“最佳架构不在金字塔子集”“必然被替代”等表述完整保存。正文将前两项改写为有条件的思想实验及具体任务的信息需求，将后两项区分为探索方向和制度主张。这些是编辑限定，不是作者已确认的新一轮修正。',
        '\n原有从强调正态分布转向公平的发展条件、能力多样性和跨领域合作的作者修正，继续沿既有版本与采纳节点保留。新章没有恢复统计分布保证，也没有把公开记录当作公平或安全已经成立的证明。']
    (OUT/'07-thought-evolution.md').write_bytes(('\n'.join(timeline_md)+'\n').encode())
    notes=f'''# 第十六版：超级智能、老大哥与制度想象的边界

在第16章“具有感官与行动能力的文明智能”中，接着AI的控制权问题，加入三节：

1. 超级智能为什么总被想象成老大哥。
2. 获取合作信息，不等于全面接管个人生活。
3. 不要让旧制度规定未来想象的边界。

作者的原始论述是本轮主线：文明中的持续博弈、老大哥式的恐惧与对抗、传统组织形态对未来想象的限制，以及不冒称自己的方案已经最优、仍须勇于探索的立场。保留这条推理次序和第一人称表达，拆分长句，补入共享闲置算力的例子，并以一处章末过渡接回动态权重。

## 原话与编辑边界

[完整作者消息](00-author-agi-and-institutional-imagination.txt)不作修改。[段落来源清单](passage-manifest.json)记录与原话至少24个连续字符精确匹配的片段；这种匹配只证明文字保留，不替代语义审阅，也不把其余编辑文字归为作者原话。

- “吸收全人类知识”“具有自我意识”不足以直接推出全人类利益目标。正文将共同利益目标明确为思想实验的假设，并保留目标需要共同解释与修正的前提。
- “需要充分信息”不等于“必须获得所有人的一切信息”。补充任务范围、个人代理与授权的区分，不假定分布式处理已经解决泄露、误报和技术失误。
- 《1984》《黑客帝国》《终结者》用作各不相同的权力与风险意象，不声称它们都是AGI题材或都以禁止AI收场。
- 金字塔结构只是可探索形式的一部分，并不单独证明最优架构必在其外。保留探索与替代传统职能的主张，同时说明自愿采用、实际效果和持续修正的要求。
- 制度变革与AI技术安全研究需要共同推进；不把任何一方写成可以自动替代另一方。

以上限定、例子和桥接属于编辑补充，尚未得到作者逐句确认，知识库不记录虚构的“作者已采纳”。

## 版本和检查

中英文各{stats['revisions_by_language']['zh']}处有边界的编辑，共4处，均可双向还原。全书仍为32章、{stats['headings']}个标题；{stats['unchanged_chapter_pairs']}组章节中英文逐字节不变。本轮语义阅读覆盖第16章与衔接，其余章节继承第十五版。

中文{stats['chinese_cjk_characters']:,}汉字，净增{stats['chinese_cjk_characters']-stats['previous_chinese_cjk_characters']:,}汉字；英文约{stats['english_whitespace_words']:,}个空白分隔词项。英文以自然英语重新组织表达，保存对应论证、例子和限定。字数、哈希和来源关系不证明理论正确。

[新增中文](06-additions.zh.md) · [New English sections](06-additions.en.md) · [本轮复核范围](targeted-review.md) · [来源](08-source-ledger.md) · [思想演化](07-thought-evolution.md) · [逐项修改](revision-manifest.json)
'''
    (OUT/'04-editorial-notes.md').write_bytes(notes.encode())
    table=['# 中英文逐章对照 / Chinese–English chapter map\n',
        '第16章新增内容和结尾衔接同步为自然英语。其他31组章节逐字节继承第十五版；本轮全书结构与引用一致性检查不等于再次逐字阅读。\n',
        '|章|中文|English|本轮状态|','|---|---|---|---|']
    table += [f"|{r['id']}|{r['title_zh']}|{r['title_en']}|{r['review']['status']}|" for r in ledger]
    table += ['\n[中文全文](01-new-principles.zh.md) · [Full English text](02-new-principles.en.md) · [精确区间](translation-ledger.json)']
    (OUT/'05-translation-notes.md').write_bytes(('\n'.join(table)+'\n').encode())
    landing=(PUBLIC/'book/readme.md').read_text(encoding='utf-8').replace('2026-11-01-institutions-coherence',OUT.name)
    before='最新修订进一步讨论技术红利、财富分配与生活体验之间的落差，并考察制度怎样通过自愿合作、公开检验与和平试验持续自我修正。'
    after='书中讨论技术红利、财富分配与生活体验之间的落差，也追问：超级智能为何常被想象成老大哥，合作所需的信息怎样避免变成控制个人的工具，新的制度又怎样通过自愿合作、公开检验与和平试验持续自我修正。'
    assert landing.count(before)==1
    landing=landing.replace(before,after)
    before='The latest revision examines gaps between technological gains, wealth distribution, and lived well-being, asking how institutions can keep learning through voluntary cooperation, public scrutiny, and peaceful experiments.'
    after='It examines gaps between technological gains, wealth distribution, and lived well-being. It also asks why superintelligence is so often imagined as Big Brother, how information sharing might support cooperation without surrendering personal control, and how institutions can keep learning through voluntary participation, public scrutiny, and peaceful experiments.'
    assert landing.count(before)==1
    (OUT/'book-readme.md').write_bytes(landing.replace(before,after).encode())
    refs=json.loads((WORK/'references.json').read_bytes())
    write_json(OUT/'08-external-references.json',refs)
    sources=['# 外部依据与论证范围\n','两项原始来源于2026年11月2日核对。它们用于限定关于目标的推断，不作为本书制度方案已获验证的依据。\n',
        '|来源|类型|支持范围与限制|','|---|---|---|']
    sources += [f"|[{r['title']}]({r['url']})|{r['type']}|{r['scope']}|" for r in refs]
    sources += ['\n科幻意象属于解释性的类比。超级AI的自我意识、共同利益目标和新制度的整体效果在此均非已证实事实；制度多样性的论证也不是全局最优性的证明。',
        '\n作者原话和上版完成答复保持为可见会话来源。未收录外部文章全文、隐藏推理或工具日志。']
    (OUT/'08-source-ledger.md').write_bytes(('\n'.join(sources)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))
