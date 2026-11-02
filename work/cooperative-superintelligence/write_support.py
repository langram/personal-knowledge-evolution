"""Record the author's supplement separately from conditional editorial wording."""
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
        'exact_author_span_boundary':'Exact matches identify retained wording only; semantic association is not approval of editorial additions.'}
    write_json(OUT/'editorial-statistics.json',stats)
    review={'schema':'cs/targeted-review@1','edition':EDITION,'baseline_edition':'16-agi-institutions',
        'baseline_sha256':{l:sha(t.encode()) for l,t in originals.items()},'reviewed_chapters':[16],
        'coverage':{'semantic':'New bilingual section and surrounding chapter-16 discussion of goals, dystopian power, cooperation and information.',
            'structural':'32 chapter pairs, aligned headings/citations, source roundtrips and reversible insertion; 31 chapter pairs byte-identical.',
            'inherited':'All existing manuscript text retained. No new full-book reading claimed.',
            'external_facts':'One official historical document for a bounded example of US intervention; earlier AI sources retained.'},
        'findings':['A system born in an existing hierarchy may still propose peaceful institutional change.',
            'Whole-civilization costs include lives, autonomy, trust and correction, rather than only the coercing actor\'s immediate cost.',
            'Peaceful persuasion requires inspectable evidence and the possibility of refusal, withdrawal and correction.',
            'The author\'s confidence and satire remain distinct from a proof that intelligence guarantees benevolence.',
            'The historical source supports one documented proposal, not every US policy or universal comparative costs.'],
        'author_approval':'Conditional wording, example and English adaptation are editorial; no author acceptance is fabricated.'}
    write_json(OUT/'targeted-review.json',review)
    (OUT/'targeted-review.md').write_bytes('''# 本轮衔接复核

新增小节放在第16章“超级智能为什么总被想象成老大哥”之后、“获取合作信息，不等于全面接管个人生活”之前。先给恐惧场景增加一个积极的回应，再回到信息、授权与合作的实现条件。

本轮核对新增小节的中英文及相关上下文。其他31组章节逐字节继承第十六版，第16章既有文字也全部保留。全书结构和引用检查不记为再次通读。

保留作者对和平沟通的期待和讽刺表达，补入目标条件、整体成本、拒绝与退出、接受反证的说明。智利会议笔记只支撑具体例证，不概括美国全部对外政策。能力强、目标好与行为可靠分别考察，不把任何一个条件当作其他条件已经成立的证明。

[逐处插入](revision-manifest.json) · [中英对应](translation-ledger.json) · [史料范围](08-source-ledger.md)
'''.encode())
    rows=['# 从对老大哥的忧虑，到和平改变的积极设想\n',
        '上版完成答复是更新起点，本次作者补充是直接来源。时间来自可见原始事件，不代表思想首次产生时间。\n',
        '|时间（UTC）|来源|地位|','|---|---|---|']
    for e,item in zip(events,timeline):rows.append(f"|{e['time']}|[{e['ref']}](00-{e['ref'].lower()}.txt)|{item['status']}|")
    rows += ['\n演化联系：上一版批评把超级智能固定想象为老大哥 → 本次作者强调即使诞生于传统架构，也可能通过理论、证据和自愿试点推动和平改变 → 编辑补入文明整体成本、目标条件与接受反证的要求 → 接回已有的信息主权和共同协作机制。',
        '\n作者原话中的“显然不可能做出错误的选择”“除非它是超级通用人工智障”完整保存。正文保留后者的讽刺修辞，同时把必然性表述写成有条件的期待。该限定不是作者已经明确确认的新观点，不记录虚假的采纳事件。',
        '\n关于公平发展条件、能力互补与跨领域合作的既有作者修正，沿此前的版本与采纳节点继续保留；本次没有把高能力重新写成不可能支配或伤害他人的保证。']
    (OUT/'07-thought-evolution.md').write_bytes(('\n'.join(rows)+'\n').encode())
    notes=f'''# 第十七版：理性说服、自愿试点与超级智能的选择

在第16章的老大哥式忧虑之后，新增“超级智能为什么应当选择说服，而不是强迫”。保留作者“话说回来，我相信”的转折、构造理论与实验说服的主线，对宗教迫害和强权手段的批评，以及结尾的讽刺表达。英文采用自然英语表达，修辞也保留相应力度。

## 原话与编辑补充

[完整原话](00-author-peaceful-superintelligence.txt)不改动。[段落清单](passage-manifest.json)记录精确文字片段及来源。

编辑补入的内容有：比较文明整体成本时，纳入生命、自主、信任与纠错机会；说服允许拒绝、退出和反证，避免滑向操纵；把“超级智能必然不会错误选择”限定为在相关目标和认识条件下的合理期待，而不作为已证明的安全结论。

对美国的批评保留为作者立场，并补入1970年9月15日智利会议的具体史料。没有把所有宗教审判笼统定位为中世纪，也没有把一份会议笔记推广为美国全部外交的描述。史料只支撑具体事实，不证明和平在所有目标和情境下都成本最低。

讽刺性用语保留在理论作品的论述语境中；它表达评价与期望，不能替代对实际系统目标和行为的检验。新增解释和英语措辞未冒称已获作者逐句确认。

## 保存与检查

中英文各1处插入，可双向还原；原有正文未删改。全书32章、{stats['headings']}个标题，其他31组章节逐字节不变。中文净增{stats['chinese_cjk_characters']-stats['previous_chinese_cjk_characters']:,}汉字，共{stats['chinese_cjk_characters']:,}汉字；英文约{stats['english_whitespace_words']:,}个空白分隔词项。

本轮阅读和语义核对覆盖新增小节及相关上下文，结构和引用检查覆盖32章，不宣称再次通读全书。来源身份、版本完整性和语义审阅各自记录，不以校验成功证明理论成立。

[新增中文](06-additions.zh.md) · [New English section](06-additions.en.md) · [复核范围](targeted-review.md) · [史料与范围](08-source-ledger.md) · [演化脉络](07-thought-evolution.md) · [修改清单](revision-manifest.json)
'''
    (OUT/'04-editorial-notes.md').write_bytes(notes.encode())
    table=['# 中英文逐章对照 / Chinese–English chapter map\n',
        '新增小节对应自然英语版本。其余正文逐字节继承第十六版，结构、标题层级和引用顺序全书核对。\n',
        '|章|中文|English|状态|','|---|---|---|---|']
    table += [f"|{r['id']}|{r['title_zh']}|{r['title_en']}|{r['review']['status']}|" for r in ledger]
    table += ['\n[中文全文](01-new-principles.zh.md) · [Full English text](02-new-principles.en.md) · [精确对应](translation-ledger.json)']
    (OUT/'05-translation-notes.md').write_bytes(('\n'.join(table)+'\n').encode())
    landing=(PUBLIC/'book/readme.md').read_text(encoding='utf-8').replace('2026-11-02-agi-institutions',OUT.name)
    before='新的制度又怎样通过自愿合作、公开检验与和平试验持续自我修正。'
    after=before+'最新补充强调以理性说服、可靠证据和自愿试点推进改变，并讨论这种乐观期待所需的条件。'
    assert landing.count(before)==1;landing=landing.replace(before,after)
    before='and how institutions can keep learning through voluntary participation, public scrutiny, and peaceful experiments.'
    after=before+' The latest addition explores reasoned persuasion, reliable evidence, and voluntary pilots as a path to change, while examining the conditions this optimistic expectation requires.'
    assert landing.count(before)==1;landing=landing.replace(before,after)
    (OUT/'book-readme.md').write_bytes(landing.encode())
    refs=json.loads((WORK/'references.json').read_bytes());write_json(OUT/'08-external-references.json',refs)
    source=['# 本轮新增史料与边界\n','2026年11月2日核对美国国务院历史文献集。既有关于智能与目标的理论来源保留于前一小节，本次不重复新增引用。\n',
        '|来源|性质|范围|','|---|---|---|']
    source += [f"|[{r['title']}]({r['url']})|{r['type']}|{r['scope']}|" for r in refs]
    source += ['\n作者对强制和干预的评价与上述具体史实分开。超级智能选择和平策略仍是包含目标与环境条件的设想，不是由这份史料推出的定理。',
        '\n原话完整保留；没有公开原始工具封套、隐藏推理或外部文献全文。']
    (OUT/'08-source-ledger.md').write_bytes(('\n'.join(source)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))
