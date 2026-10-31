"""Assemble both complete editions and an explicit editorial/translation ledger."""
import json
import re
import posixpath
from prepare import ARCHIVE, OLD, OUT, PRIOR, WORK, sha, write_json

TITLE = '# New Principles: Modern Science and the Making of Human Civilization\n\n'

def headings(text):
    return re.findall(r'^(#{2,6}) (.+)$', text, re.M)

def urls(text):
    return re.findall(r'\]\((https?://[^)]+)\)', text)

def assemble():
    assert not (ARCHIVE/'report.json').exists(), 'Frozen archive must not be rewritten.'
    index=json.loads((WORK/'chapters.json').read_bytes())
    zh=(OUT/'01-new-principles.zh.md').read_bytes().decode()
    assert sha(zh.encode())==index['source_sha256']
    whole=TITLE; rows=[]
    for row in index['chapters']:
        source=(WORK/row['source_file']).read_bytes().decode()
        text=(WORK/'en-chapters'/(row['id']+'.md')).read_bytes().decode()
        assert sha(source.encode())==row['sha256'] and zh[slice(*row['char_span'])]==source
        hs,he=headings(source),headings(text)
        assert [x[0] for x in hs]==[x[0] for x in he], row['id']
        assert urls(source)==urls(text), row['id']
        assert text.startswith('## ') and len(text.split())>300
        assert not re.search(r'\b(?:TODO|TBD|TRANSLATE_ME)\b',text)
        begin=len(whole); whole+=text.rstrip()+'\n\n'; end=len(whole)
        rows.append({**{k:v for k,v in row.items() if k!='review'},
            'title_en':he[0][1], 'english_source_file':'en-chapters/'+row['id']+'.md',
            'english_source_sha256':sha(text.encode()),'english_char_span':[begin,end],
            'english_sha256':sha(whole[begin:end].encode()),'english_whitespace_words':len(text.split()),
            'section_map':[{'level':len(a[0]),'zh':a[1],'en':b[1]} for a,b in zip(hs,he)],
            'external_links':urls(text),'review':{'source_read_in_full':True,'english_adapted_directly':True,
                'heading_order_and_citations':'verified','semantic_equivalence':'editorial judgment; structural checks do not prove it'}})
    (OUT/'02-new-principles.en.md').write_bytes(whole.encode())
    ledger={'schema':'pkst-editorial/translation-ledger@1','source_language':'zh','target_language':'en',
        'source_file':'01-new-principles.zh.md','source_sha256':sha(zh.encode()),
        'target_file':'02-new-principles.en.md','target_sha256':sha(whole.encode()),
        'method':'Complete chapter-by-chapter English adaptation, with natural syntax; source arguments, examples, qualifications, headings and citations retained.',
        'author_wording_approval':False,'scope':'31 top-level sections including preface, afterword and final appendix; not an abridgment.',
        'coordinate':'unicode-scalar-half-open; exact UTF-8 decoded text, no newline normalization','chapters':rows}
    write_json(OUT/'translation-ledger.json',ledger)
    write_json(WORK/'translation-progress.json',{'completed_chapters':len(rows),'total_chapters':31,
        'english_whitespace_words':len(whole.split()),'source_sha256':sha(zh.encode()),'chapters':rows})
    manifest=json.loads((OUT/'zh-revision-manifest.json').read_bytes())
    changes=manifest['changes']
    cjk=lambda s:len(re.findall('[\u4e00-\u9fff]',s))
    metrics={'chinese_sha256':sha(zh.encode()),'english_sha256':sha(whole.encode()),
        'chinese_cjk_characters':cjk(zh),'chinese_total_characters':len(zh),'english_whitespace_words':len(whole.split()),
        'chapters_in_each_edition':len(rows),'chinese_edits':len(changes),'net_added_cjk':cjk(zh)-cjk(OLD.read_bytes().decode()),
        'external_citation_occurrences':len(urls(whole)),'count_method':'CJK U+4E00..U+9FFF; English whitespace-delimited tokens, including headings/tables/links.'}
    write_json(OUT/'editorial-statistics.json',metrics)
    historical=json.loads((OUT/'00-historical-sources.json').read_bytes())
    events=json.loads((OUT/'00-sources.json').read_bytes())
    prior=json.loads((PRIOR/'report.json').read_bytes())
    timeline={'schema':'pkst-editorial/revision-continuation@1','previous_dossier':prior['snapshot'],
        'previous_author_revision':prior['author_revision'],'previous_author_acceptance':prior['author_acceptance'],
        'previous_timeline':'../2026-10-31-ability-cooperation/07-thought-evolution.json',
        'stages':[{'ref':e['ref'],'time':e['time'],'role':e['role'],'occurrence':e['occurrence'],'content':e['content'],
            'source_object':e.get('source_object'),'text_sha256':e['text_sha256'],'quote':e['text'],
            'status':'already archived; linked, not imported twice' if e.get('already_imported') else 'new visible event'}
            for e in sorted(historical+events,key=lambda e:e['time'])],
        'current_emphasis':['fair conditions for development','diverse and complementary abilities','deep cooperation across fields',
                            'testable limits on domination independent of a statistical distribution'],
        'boundary':'Native message chronology and explicit author revision; not date of first invention or endorsement of every editorial sentence.'}
    write_json(OUT/'07-thought-evolution.json',timeline)
    audit={'schema':'pkst-editorial/full-book-audit@1','source_sha256':sha(zh.encode()),'chapters_reviewed':31,
        'baseline_finding':'Edition 12 already contained no direct affirmative normality-implies-no-domination claim. Related equality/need/analogy ambiguities were clarified in ten bounded edits.',
        'current_finding':'No remaining affirmative inference from normal ability/need distributions to guaranteed absence of dominant nodes.',
        'method':'Full chapter reading during English adaptation plus contextual review of distribution, equality, accumulation and domination passages.',
        'remaining_distribution_mentions': [{'line':i,'text':s,'disposition':'retained rejection of a distribution premise or contextual explanation'}
            for i,s in enumerate(zh.splitlines(),1) if re.search('正态|钟形',s)],
        'chapters':[{'id':r['id'],'title':r['title_zh'],'full_read':True,
            'edits':[c['id'] for c in changes if r['char_span'][0]<=c['new_char_span'][0]<r['char_span'][1]],
            'finding':'No affirmative distribution-based guarantee of non-domination; source proposals and qualifications retained.'} for r in rows],
        'scope_boundary':'Editorial consistency review, not fresh verification of every scientific or historical claim or external URL.'}
    write_json(OUT/'full-book-audit.json',audit)
    readme='''# 《新原理》 / New Principles

**现代科学与人类文明的构造 · Modern Science and the Making of Human Civilization**  
作者 / Author: **Tangram Liu（langram）**

**阅读全文 / Read the complete book**

- [中文全文](current.md)
- [Full English edition](current.en.md)

《新原理》从存在、变化与可构造性出发，讨论知识与智能如何相互促进，以及人类如何在 AI 时代共同构造新的社会组织方式。全书将数学与自然科学的探索，连接到公共知识、个人数据主权、动态权重决策、按需保障与共同资源治理，并提出从一个人的知识库和云存储开始、逐步扩展合作的实践路径。

本书强调公平的发展条件、能力多样性与跨领域合作。防止支配不以任何预设的能力分布为保证，而要通过可以核验、质疑、修正和退出的机制接受实践检验。数学假说、经验依据、制度主张与已实现能力在正文及末尾自我反思附录中分别讨论。

*New Principles* explores how knowledge and intelligence can reinforce one another, and how people might build new forms of cooperation in the age of AI. Beginning with questions about existence, change, and what can be constructed, it connects scientific inquiry with shared knowledge, personal data sovereignty, dynamic decision weights, provision according to need, and the governance of common resources. Its practical path starts small: one person's knowledge archive and cloud storage, growing through voluntary cooperation.

The book argues for fair conditions in which diverse abilities can develop and complement one another across disciplines. Freedom from domination is a goal to test through accountable, revisable institutions—not a consequence assumed from a statistical distribution. The final appendix critically assesses the mathematics, scientific hypotheses, social arguments, and feasibility of the proposed systems. The complete English edition is written for English readers, with the original arguments, examples, and qualifications retained.

**版本与来源 / Versions and sources**

- [编辑与版本历史 / Editorial and version history](../history/README.md)
- [本版修改记录 / This edition's revision record](../archive/dossiers/2026-10-31-book-bilingual/04-editorial-notes.md)
- [逐章中英对照目录 / Chinese–English chapter map](../archive/dossiers/2026-10-31-book-bilingual/05-translation-notes.md)
- [思想演化记录 / Evolution of the argument](../archive/dossiers/2026-10-31-book-bilingual/07-thought-evolution.md)
- [知识库与只读接口 / Knowledge archive and read-only API](../README.md)

原话、AI 回答、编辑补写与作者采纳记录分别保存。欢迎带着问题、不同意见和实践经验阅读与讨论。  
Original statements, AI responses, editorial additions, and recorded author revisions remain distinct. Questions, disagreement, and practical experience are welcome.
'''
    readme=re.sub(r'\]\(([^)]+)\)',lambda m:'](https://github.com/langram/personal-knowledge-evolution/blob/main/'+posixpath.normpath('book/'+m.group(1))+')',readme)
    (OUT/'book-readme.md').write_bytes(readme.encode())
    notes=['# 第十三版编辑说明：全文一致性与英文版\n',
        '本版根据作者要求通读正文、后记和最后附录，共 31 个二级章节；书籍简介按作者明确选择使用中英双语，不制作法文简介。\n',
        '第十二版已经没有直接以“能力和需求服从正态分布”证明“不会出现支配节点”的现行断言。本轮发现并澄清的是相关的能力平等类比、AI辅助条件、能力积累与需要边界等表述；不把这些十处修改都宣称为发现了旧断言。\n',
        '中文仅作十处有边界的替换或增补，尽量保留作者文字。其余正文逐字节保留；历史版本、原话和明确修正过程不覆盖。附录最后新增“公平的发展条件、能力互补与防止支配”，把统计经验问题与制度目标、可检验的防支配安排分开。附录仍为全文最后一章。\n',
        '英文按最新中文逐章完整改写为自然英语，保留论证、例子、异议解答、科学限定、表格及全部外部引用链接。没有用摘要替代长章节，也不因改写语言而提高结论的确定性。原文段落可合并或重排句序以适应英语；不是逐句对译。\n',
        f'中文 {metrics["chinese_cjk_characters"]:,} 个汉字；英文约 {metrics["english_whitespace_words"]:,} 个空白分隔词项；各 31 个章节。字数是描述性统计，不代表论证质量。\n',
        '本轮公开来源新增三条：上一版公开最终答复、作者本轮请求、README语言确认。另连接两条已归档作者原话，不重复导入。保存的是可见原话、编辑决策及版本关系，不包含隐藏推理或系统消息。\n',
        '作者已明确接受从分布前提转向能力互补的概念修正；尚未把本轮每句补写或英文措辞标记为作者逐句认可。全文阅读与语义判断由本轮编辑完成；程序检查覆盖字节、来源、章节、引用和链接，不能证明翻译绝对等价或理论正确。\n',
        '## 中文改动\n']
    for c in changes:
        notes += [f'### {c["id"]}\n',c['reason']+'\n','**修改前**\n\n'+c['before']+'\n','**修改后**\n\n'+c['after']+'\n']
    notes += ['## 可复核材料\n',
        '- [中文精确修改差异](03-zh-revisions.patch)\n- [坐标与修改清单](zh-revision-manifest.json)\n- [全文审读记录](full-book-audit.json)\n- [逐章英文来源与哈希](translation-ledger.json)\n- [思想演化记录](07-thought-evolution.md)\n']
    (OUT/'04-editorial-notes.md').write_bytes(('\n'.join(notes)+'\n').encode())
    translation=['# 英文改写与术语说明\n',
        'English title: **New Principles: Modern Science and the Making of Human Civilization**.\n',
        '英文全文以本版中文为唯一基准，保留独立作品的叙述方式；采用英语习惯组织句子，不加入读者必须了解旧稿的回顾。31 章全部阅读并改写，章节层级和外部链接逐项核对。原话在来源层保持中文原文；英文是明确标注的派生版本，不冒充新的作者原生发言。\n',
        '## 核心术语\n',
        '| 中文 | English | 用法 |\n|---|---|---|\n| 新原理 | New Principles | 书名 |\n| 公平的发展条件 | fair conditions for development | 不等同于相同能力结果 |\n| 能力互补 | complementary abilities / complementarity | 保留不同能力结构 |\n| 跨领域合作 | cooperation across fields / disciplines | 根据语境自然表达 |\n| 动态权重 | dynamic decision weights | 区分任务相关影响力与执行权 |\n| 公共知识 | public/shared knowledge; common knowledge | 共享资料与博弈中的相互知晓按语境区分 |\n| 数据主权 | data sovereignty | 具体控制、迁移和退出能力 |\n| 按需保障 | provision according to need | 与共同生产资源的治理区分 |\n| 对偶体 | Dualoid | 尚待形式化的作者概念 |\n| 不动点 | fixed point | 不自动包含收敛性 |\n| 自我实现的科幻 | self-realizing science fiction | 通过自愿创作与实践连接想象和现实 |\n| Merkle-DAG / FPM / Structoken / MerkleVM / HotPath | 原名保留 | 不将不同项目合并成已实现的统一产品 |\n',
        '## 完整章节对应\n','| # | 中文 | English |\n|---|---|---|']
    translation += [f'|{r["id"]}|{r["title_zh"]}|{r["title_en"]}|' for r in rows]
    translation += ['\n[英文全文](02-new-principles.en.md) · [中文全文](01-new-principles.zh.md) · [机器可读对照](translation-ledger.json)\n',
        '章节数、外部链接和字节身份检查均可复现；自然度与语义忠实度属于编辑判断，仍欢迎读者指出具体措辞问题。既有来源链接按中文版保留，本轮没有声称重新验证全部外部网页。\n']
    (OUT/'05-translation-notes.md').write_bytes(('\n'.join(translation)+'\n').encode())
    evolution=['# 从分布前提到能力互补：本轮的延续\n',
        '此前的原始命题、质疑、回应和明确修正，完整保存在[第十二版时间线](../2026-10-31-ability-cooperation/07-thought-evolution.md)及其[作者修正记录](../2026-10-31-ability-cooperation/author-revision.json)。本轮继承这条历史，不改写早期发言。\n']
    for s in timeline['stages']:
        evolution += [f'## {s["ref"]} · {s["time"]}\n',f'角色：{s["role"]}；状态：{s["status"]}。\n',
                      '\n'.join('> '+line for line in s['quote'].splitlines())+'\n',
                      f'来源事件：`{s["occurrence"]}`；内容：`{s["content"]}`。\n']
    evolution += ['## 本轮编辑实现\n',
        '从作者已确认的公平条件、能力多样性与跨领域合作出发，统一审读中文，并将同一理解用于英文版。统计分布可以继续研究；制度不以某一曲线为成立前提。防止支配需要在能力长尾、历史优势、信息不均和联合行动等条件下检验具体规则。\n',
        '此处记录讨论与编辑的演化，不宣称新增措辞已获作者逐句认可，也不把时间戳当作世界范围内最早发明的证明。\n']
    (OUT/'07-thought-evolution.md').write_bytes(('\n'.join(evolution)+'\n').encode())
    print(json.dumps(metrics,ensure_ascii=False))

if __name__=='__main__': assemble()
