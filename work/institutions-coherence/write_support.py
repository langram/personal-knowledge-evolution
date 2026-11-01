"""Readable provenance, actual review coverage, and edition-specific publication notes."""
import json, re
from prepare import ARCHIVE, EDITION, OUT, PUBLIC, WORK, sha, write_json

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
        'exact_author_span_boundary':'Exact latest-message matches are recorded; retained baseline author wording has its earlier provenance, not a new attribution.'}
    write_json(OUT/'editorial-statistics.json',stats)
    review=json.loads((WORK/'review/notes.json').read_bytes())
    assert len(review)==32 and len({r['chapter'] for r in review})==32
    oldchapters=re.split(r'(?=^## )',originals['zh'],flags=re.M)[1:]
    for r,old in zip(review,oldchapters):
        assert sha(old.encode())==r['source_sha256'],r['chapter']
        r['edit_ids']=[e['id'] for e in changes if e['language']=='zh' and e['chapter']==int(r['chapter'])]
        r['decision']='bounded revision' if r['edit_ids'] else 'retain'
    review_record={'schema':'ic/full-book-review@1','edition':EDITION,'baseline_edition':'14-civilization-attention',
        'coverage':{'chinese':'All 32 chapters, including the final appendix, read in full for coherence.',
            'english':'Changed passages and their immediate context compared semantically; all 32 chapter pairs structurally checked. Unchanged English inherited from edition 14, not claimed to be freshly reread word for word.',
            'external_facts':'New institutional-gap claims checked against six primary sources. Earlier citations retained; no claim of a fresh verification of every historical fact.'},
        'chapters':review,'author_approval':'Editorial review is not line-by-line author acceptance.'}
    write_json(OUT/'full-book-review.json',review_record)
    review_md=['# 全书衔接复核记录\n',
        '本轮通读中文32章及末尾附录。英文对所有改动及相关上下文进行意义对照，全书检查章节、标题和引用对应；未改动英文沿用第十四版，不称为本轮逐字重读或重译。新事实核验集中于新增制度落差段落。\n',
        '|章|标题|处理|发现与理由|','|---|---|---|---|']
    review_md += [f"|{r['chapter']}|{r['title']}|{'局部修订' if r['edit_ids'] else '保留'}|{r['findings']}|" for r in review]
    review_md += ['\n检查重点：个人记忆与共同知识；不可变版本与变化运行时；注意力、证据、权利与授权；互惠与纠错；公平条件、能力互补和按需保障；技术加速与制度自我修正。',
        '\n重复并非一律删除。技术原理、制度规则与数学案例分别承担定义、推理和应用的作用；保留必要展开，只压缩真正重复的开头与例子。修改未把全书压成提纲。',
        '\n[逐处前后文本](revision-manifest.json) · [中英对照](translation-ledger.json) · [来源与限定](08-source-ledger.md)']
    (OUT/'full-book-review.md').write_bytes(('\n'.join(review_md)+'\n').encode())
    t=['# 从制度落差的观察，到可检验的共同自我修正\n',
       '完整保留第十四版完成答复和本次作者消息，分别作为更新起点与新增论述来源。原话不覆盖，事实限定与衔接修改属于本轮编辑，不伪造为作者已经明确采纳的修正。\n',
       '|时间（UTC）|角色与来源|作用|','|---|---|---|']
    for e,item in zip(events,timeline):t.append(f"|{e['time']}|[{e['ref']}](00-{e['ref'].lower()}.txt)|{item['status']}|")
    t += ['\n演化联系：技术与制度发展不匹配 → 财富与主观生活体验不能混为一谈 → 注意力目标也须由参与者掌握 → 在明确任务中比较影响传播与纠错能力 → 让新机制同样接受事实修正。',
      '\n原话中的“中美top0.1%翻了3倍”完整保存。正文区分美国0.1%的1978—2012年估计与中国1%的1995—2015年估计；不把它们改写成作者已自行纠正的发言。青年幸福感下降的地域范围也同样保留原话、另记编辑限定。',
      '\n此前从强调正态分布转向公平发展条件、能力多样性与跨领域合作的作者修正继续有效。本版沿版本父链接及既有采纳节点保存该过程，没有恢复分布保证或把注意力分数变成权力。']
    (OUT/'07-thought-evolution.md').write_bytes(('\n'.join(t)+'\n').encode())
    notes=f'''# 第十五版：制度与技术的落差及全书衔接修订

本版在第十四版32章结构上增补“技术红利为什么没有自动变成共同幸福”，放在文明的技术力量与自我治理能力一章中，先讨论现实中的制度、财富、信任与生活体验，再进入AI加速的未来情景。末尾自我反思附录增加“制度落差的判断，怎样接受事实检验”。中英文同步。

## 以作者的论述为主线

保留“令人触目惊心”“生存幸福”与“心理幸福感”“坏事传千里”“从量变走向质变”等表达和逐步追问的方式。补入的数据、范围限定和逻辑桥接属于编辑文字；[作者原话](00-author-institutional-gap-and-review.txt)保持完整，[段落清单](passage-manifest.json)逐项记录能与本次原话精确匹配的片段。没有把编辑内容记成作者逐句认可。

## 事实与范围的校准

- 战后制度发生过重大变化；论点落在技术影响与参与、约束、纠错能力的不匹配，不依靠“制度几十年从未改变”。
- 美国最富0.1%的7%至22%是1978—2012年的一项历史估计；中国最富1%的15%至30%是1995—2015年的另一组估计。两者不是同一人群口径，也不是今天的数字。
- 全球综合财富、家庭财富份额、收入与生活评价分别说明。幸福感下降限定为报告识别的地区，不宣称全球青年同向下降。
- OECD信任资料限定为2023年30个成员国的调查。负面标题实验支持点击行为差异，不直接证明心理健康的普遍下降。
- 这些材料支持继续研究问题，不单独证明本书提出的完整因果链或新制度优越性。

## 主要衔接修订

前言压缩与后文重复的金字塔例子，给弃子比喻说明人与棋子的区别；个人自我对话限定为授权记忆；社会博弈的早期表述不再把互惠策略直接等同于必然收敛的不动点迭代。

MerkleVM结尾接回紧邻的软件生态章；个人代理接入既有个人空间；注意力架构连接冷路径、热路径、对象版本和运行时；平等的参与机会与证据可靠性、代理数量分别说明。共同目标按任务范围形成，人的需要可以由本人解释与质疑。

文明自我进化段落修补悬空的模型指代，减少重复介绍；云存储开头压缩已经展开过的众筹说明；数学灵感案例补入QKV如何寻找合作者、又不能代替证明与权利的具体联系。

详见[32章复核记录](full-book-review.md)。中文全书已通读；英文核对所有改动和相关上下文，并对32章作结构与引用检查，未改动英文继承第十四版。既有详尽案例与作者原话尽量保留，不作全面重写。

## 可核验记录

中英文各{stats['revisions_by_language']['zh']}处有边界的编辑，全部保存[前后文本与区间](revision-manifest.json)，可双向还原；[中文差异](03-zh-revisions.patch)和[英文差异](03-en-revisions.patch)之外的文字保持原样。全书32章、{stats['headings']}个标题，{stats['unchanged_chapter_pairs']}组章节双语逐字节不变。

中文{stats['chinese_cjk_characters']:,}汉字，较上版净增{stats['chinese_cjk_characters']-stats['previous_chinese_cjk_characters']:,}汉字；英文约{stats['english_whitespace_words']:,}个空白分隔词项。规模与哈希证明文稿和来源身份，不证明理论成立。

[本轮新增中文小节](06-additions.zh.md) · [New English sections](06-additions.en.md) · [思想演化](07-thought-evolution.md) · [外部依据](08-source-ledger.md)
'''
    (OUT/'04-editorial-notes.md').write_bytes(notes.encode())
    trans=['# 中英文逐章对照 / Chinese–English chapter map\n',
        '英文按英语表达习惯同步全部改动。中文32章均作完整衔接阅读；英文改动及相关上下文作语义核对，未改动文字继承第十四版；结构与引用检查覆盖全书。\n',
        '|章节|中文|English|本轮状态|','|---|---|---|---|']
    trans += [f"|{r['id']}|{r['title_zh']}|{r['title_en']}|{r['review']['status']}|" for r in ledger]
    trans += ['\n[中文全文](01-new-principles.zh.md) · [Full English text](02-new-principles.en.md) · [精确区间与引用对照](translation-ledger.json)']
    (OUT/'05-translation-notes.md').write_bytes(('\n'.join(trans)+'\n').encode())
    landing=(PUBLIC/'book/readme.md').read_text(encoding='utf-8').replace('2026-11-01-civilization-attention',OUT.name)
    landing=landing.replace('新增讨论将个人与文明层级的注意力、持续变化的社会状态和博弈机制连接起来，并考察技术加速之下，制度怎样通过自愿合作、公开检验与和平试验持续自我修正。',
        '个人与文明层级的注意力、持续变化的社会状态和博弈机制，在书中与数据主权和能力复用相连接。最新修订进一步讨论技术红利、财富分配与生活体验之间的落差，并考察制度怎样通过自愿合作、公开检验与和平试验持续自我修正。')
    landing=landing.replace('New chapters and sections connect attention at personal and civilizational scales with changing social states and strategic interaction. They ask how institutions can keep learning through voluntary cooperation, public scrutiny, and peaceful experiments as technology accelerates.',
        'The book connects attention at personal and civilizational scales with changing social states, strategic interaction, data sovereignty, and reusable capabilities. The latest revision examines gaps between technological gains, wealth distribution, and lived well-being, asking how institutions can keep learning through voluntary cooperation, public scrutiny, and peaceful experiments.')
    (OUT/'book-readme.md').write_bytes(landing.encode())
    refs=json.loads((WORK/'references.json').read_bytes());write_json(OUT/'08-external-references.json',refs)
    source=['# 本轮外部依据与口径边界\n','六项原始研究或发布机构材料于2026年11月1日核对。数字均带时期与人群口径。正文没有将跨国相关观察写成制度方案已获因果验证。\n',
        '|来源|类型|可支持的范围与限制|','|---|---|---|']
    source += [f"|[{r['title']}]({r['url']})|{r['type']}|{r['scope']}|" for r in refs]
    source += ['\n战后重大制度变迁用作历史背景；制度与技术失配是待具体检验的解释框架。“生存幸福/心理幸福感”是作者的分析区分，不是两项标准化指标。国家、代际与因果差异不能被总括判断抹去。',
       '\n未收入完整外部论文、隐藏推理或工具对话。作者与助手的可见原话另见[演化时间线](07-thought-evolution.md)。']
    (OUT/'08-source-ledger.md').write_bytes(('\n'.join(source)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))
