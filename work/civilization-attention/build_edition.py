"""Bounded bilingual insertions with exact source spans and reversible edits."""
import difflib
import json
import re
from pathlib import Path
from prepare import ARCHIVE, BASE, EDITION, OLD, OLD_EN, OUT, PUBLIC, WORK, sha, write_json

SOURCES = {
    'bridge': ['AUTHOR-QKV-RUNTIME', 'RESPONSE-QKV-RUNTIME'],
    '01-attention': ['AUTHOR-ATTENTION','RESPONSE-ATTENTION','AUTHOR-QKV-RUNTIME','RESPONSE-QKV-RUNTIME',
                     'AUTHOR-GAME-MODEL','RESPONSE-GAME-MODEL','AUTHOR-EMERGENCE','RESPONSE-EMERGENCE'],
    '02-watchmen': ['AUTHOR-INTEGRATION-AND-SPEECH'],
    '03-singularities': ['AUTHOR-INTEGRATION-AND-SPEECH'],
    '04-participation': ['AUTHOR-PARTICIPATION','RESPONSE-PARTICIPATION'],
    '05-reflection': ['AUTHOR-ATTENTION','AUTHOR-QKV-RUNTIME','AUTHOR-GAME-MODEL','AUTHOR-EMERGENCE',
                      'AUTHOR-PARTICIPATION','AUTHOR-INTEGRATION-AND-SPEECH'],
}
ANCHORS = {
    'zh': [
        '## 个人需求与集体资源的两种分配',
        '### 技术的可靠性，与使用技术的文明的可靠性',
        '### 让真实分享带来保护与回报，改变文明认识自身的条件',
        '### 关键岔路口上的选择',
        '### 怎样使科学预言能够被现实修正',
    ],
    'en': [
        '## Personal Needs and Collective Resources',
        '### The reliability of technology and the reliability of the civilization using it',
        '### Protection and reward for truthful sharing can change how civilization understands itself',
        '### Choosing at a critical fork',
        '### Letting reality revise a scientific anticipation',
    ],
}
BRIDGES = {
    'zh': (
        '不过，让每个人成为共同决策的一部分，还需要回答一个更切身的问题：如果一个人的判断权重下降，他的生活会不会也被削减？如果某个人在专业领域里作出了更大的贡献，他是不是就应该永久拥有更多共同资源？这两个问题把我们带到制度中另一项关键的构造：个人需求和集体资源必须分开讨论。',
        '怎样让这些关系实际运作，还需要把动态权重展开为信息选择、任务协作、授权执行和反馈修正的具体过程。我们可以先借鉴注意力与动态博弈，构造一个能够持续变化的文明运行时，再进一步讨论个人需求和集体资源的分配。'),
    'en': (
        "That raises another immediate question. If someone's judgment receives less weight, should their livelihood shrink too? If someone makes a major specialist contribution, should they permanently control more common resources? These questions require a distinction between meeting personal needs and allocating collective resources.",
        'To make these relationships work, we need to develop dynamic weights into concrete processes for selecting information, coordinating tasks, authorizing actions, and learning from results. Attention and dynamic games offer starting points for a civilizational runtime that can change as it operates. We can then return to the distinction between personal needs and collective resources.'),
}

def read(path):
    return path.read_bytes().decode('utf-8')

def sections(text):
    points = list(re.finditer(r'^## (.+)$', text, re.M))
    return [{'title':m[1], 'span':[m.start(),points[i+1].start() if i+1<len(points) else len(text)]}
            for i,m in enumerate(points)]

def urls(text):
    return re.findall(r'\]\((https?://[^)\s]+)\)',text)

def headings(text):
    return re.findall(r'^(#{2,6}) (.+)$',text,re.M)

def assemble(language, baseline):
    before,after=BRIDGES[language]
    assert baseline.count(before)==1,(language,'bridge')
    pos=baseline.index(before)
    edits=[{'id':'bridge','language':language,'old_span':[pos,pos+len(before)],'before':before,'after':after,
            'kind':'replace','rationale':'Move the existing needs/resources transition to the end of the new runtime chapter.',
            'source_refs':SOURCES['bridge']}]
    for stem,anchor in zip(list(SOURCES)[1:],ANCHORS[language]):
        assert baseline.count(anchor+'\n')==1,(language,anchor)
        pos=baseline.index(anchor+'\n')
        body=read(WORK/'fragments'/f'{stem}.{language}.md').rstrip()+'\n\n'
        edits.append({'id':stem,'language':language,'old_span':[pos,pos],'before':'','after':body,
            'kind':'insert','before_heading':anchor,'source_refs':SOURCES[stem],
            'fragment':f'fragments/{stem}.{language}.md',
            'rationale':'Integrate the post-edition-13 discussion while preserving the surrounding book verbatim.'})
    edits.sort(key=lambda e:e['old_span'])
    pieces=[];cursor=0;newpos=0
    for e in edits:
        start,end=e['old_span'];assert start>=cursor
        gap=baseline[cursor:start];pieces += [gap,e['after']];newpos+=len(gap)
        e['new_span']=[newpos,newpos+len(e['after'])];newpos+=len(e['after']);cursor=end
        e['before_sha256']=sha(e['before'].encode());e['after_sha256']=sha(e['after'].encode())
    pieces.append(baseline[cursor:]);result=''.join(pieces)
    return result,edits

def build():
    assert not (ARCHIVE/'report.json').exists(),'Do not rebuild a frozen edition.'
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    originals={'zh':read(OLD),'en':read(OLD_EN)}
    assert sha(originals['zh'].encode())==baseline['sha256']
    assert sha(originals['en'].encode())==baseline['english_sha256']
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events'];byref={e['ref']:e for e in events}
    results={};changes=[]
    for lang,original in originals.items():
        text,edits=assemble(lang,original);results[lang]=text;changes+=edits
        name='01-new-principles.zh.md' if lang=='zh' else '02-new-principles.en.md'
        (OUT/name).write_bytes(text.encode())
        patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),
            fromfile='edition-13/'+name,tofile=EDITION+'/'+name))
        (OUT/f'03-{lang}-revisions.patch').write_bytes(patch.encode())
        additions='\n\n'.join(read(WORK/'fragments'/f'{stem}.{lang}.md').rstrip() for stem in list(SOURCES)[1:])+'\n'
        (OUT/f'06-additions.{lang}.md').write_bytes(additions.encode())
    manifest={'schema':'ca/revision-manifest@1','coordinate':'unicode-scalar-half-open',
        'edition':EDITION,'baseline_edition':'13-book-bilingual',
        'baseline_sha256':{l:sha(t.encode()) for l,t in originals.items()},
        'result_sha256':{l:sha(t.encode()) for l,t in results.items()},'changes':changes,
        'unchanged_boundary':'All text outside the recorded spans is preserved exactly; source utterances are never overwritten.'}
    write_json(OUT/'revision-manifest.json',manifest)
    write_json(OUT/'zh-revision-manifest.json',{**manifest,'changes':[e for e in changes if e['language']=='zh']})
    zsections=sections(results['zh']);esections=sections(results['en'])
    assert len(zsections)==len(esections)==32
    old_by_title={l:{r['title']:t[slice(*r['span'])] for r in sections(t)} for l,t in originals.items()}
    ledger=[]
    for i,(z,e) in enumerate(zip(zsections,esections),1):
        ztext=results['zh'][slice(*z['span'])];etext=results['en'][slice(*e['span'])]
        zheads=headings(ztext);eheads=headings(etext)
        assert [h[0] for h in zheads]==[h[0] for h in eheads],(z['title'],e['title'])
        assert urls(ztext)==urls(etext),(z['title'],'citation mismatch')
        sourcefile=f'zh-chapters/{i:02}.md';engfile=f'en-chapters/{i:02}.md'
        for name,txt in [(sourcefile,ztext),(engfile,etext)]:
            p=WORK/name;p.parent.mkdir(exist_ok=True);p.write_bytes(txt.encode())
        unchanged=old_by_title['zh'].get(z['title'])==ztext and old_by_title['en'].get(e['title'])==etext
        ledger.append({'id':f'{i:02}','title_zh':z['title'],'title_en':e['title'],
            'char_span':z['span'],'english_char_span':e['span'],'source_file':sourcefile,'english_source_file':engfile,
            'sha256':sha(ztext.encode()),'english_sha256':sha(etext.encode()),'english_source_sha256':sha(etext.encode()),
            'section_map':[{'level':len(a[0]),'zh':a[1],'en':b[1]} for a,b in zip(zheads,eheads)],
            'external_links':urls(ztext),'review':{'status':'inherited-byte-identical' if unchanged else 'editorial-reviewed',
                'scope':'English meaning, argument, examples, qualifications and citations compared with Chinese; not author approval or proof of theory'}})
    write_json(OUT/'translation-ledger.json',{'schema':'ca/translation-ledger@1','coordinate':'unicode-scalar-half-open',
        'edition':EDITION,'chapters':ledger,'method':'Idiomatic English adaptation; unchanged translations inherited byte-for-byte from edition 13.'})
    # Record exact recoverable author wording, separate from semantic attribution.
    passages=[]
    for edit in (e for e in changes if e['language']=='zh'):
        for i,m in enumerate(re.finditer(r'(?s)(\S.*?)(?=\n\n|\Z)',edit['after']),1):
            paragraph=m[1];exact=[]
            for ref in edit['source_refs']:
                event=byref[ref]
                if event['role']!='user':continue
                for block in difflib.SequenceMatcher(None,event['text'],paragraph,autojunk=False).get_matching_blocks():
                    if block.size<24:continue
                    exact.append({'ref':ref,'source_span':[block.a,block.a+block.size],
                        'paragraph_span':[block.b,block.b+block.size],
                        'text':paragraph[block.b:block.b+block.size]})
            passages.append({'id':f"{edit['id']}-{i:03}",'edit':edit['id'],
                'document_span':[edit['new_span'][0]+m.start(1),edit['new_span'][0]+m.end(1)],
                'sha256':sha(paragraph.encode()),'source_refs':edit['source_refs'],'exact_author_spans':exact,
                'attribution':'Mixed author-led adaptation and editorial explanation; source association does not attribute every sentence to the author.',
                'author_wording_approved':False})
    write_json(OUT/'passage-manifest.json',{'schema':'ca/passage-manifest@1','coordinate':'unicode-scalar-half-open',
        'minimum_exact_span_characters':24,'passages':passages})
    timeline=[{'step':i,'ref':e['ref'],'role':e['role'],'event_time':e['native_event_time'],
        'occurrence':e['occurrence'],'content':e['content'],'text_sha256':e['text_sha256'],
        'status':'prior release context' if i==1 else 'author proposal' if e['role']=='user' else 'assistant response, not automatic author endorsement'}
        for i,e in enumerate(events,1)]
    write_json(OUT/'07-thought-evolution.json',{'schema':'ca/evolution@1','previous_edition':'13-book-bilingual',
        'stages':timeline,'boundary':'Native message timestamps describe visible speech events, not first invention; no hidden reasoning captured.'})
    timeline_md=['# 从注意力类比到可演化的文明运行时\n',
        '本轮从第十三版完成答复之后的可见讨论中提取六条作者消息、五条讨论答复，另保留一条上版完成答复作为范围边界。原话完整保存，编辑文字不回写来源。\n',
        '|时间（UTC）|角色与来源|作用|','|---|---|---|']
    for e,t in zip(events,timeline):
        timeline_md.append(f"|{e['time']}|[{e['ref']}](00-{e['ref'].lower()}.txt)|{t['status']}|")
    timeline_md+=['\n思想的发展顺序是：个人与文明的注意力类比 → QKV与可变对象 → 持续状态及博弈机制 → 开放式涌现与模型修订 → 主动合作作为信息条件 → 技术加速的制度紧迫性与扩大和平选项。',
        '\n此前从正态分布前提转向公平发展、能力多样性与跨领域合作的修正继续有效；本轮没有用注意力分数、算力比例或任何分布假设替代权利和授权保障。',
        '\n作者要求整合并不等于逐句认可AI补写。完整中英文版本、精确差异与段落来源链均保存，后续可以逐项修改。']
    (OUT/'07-thought-evolution.md').write_bytes(('\n'.join(timeline_md)+'\n').encode())
    stats={'edition':EDITION,'chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',results['zh'])),
        'previous_chinese_cjk_characters':len(re.findall(r'[\u4e00-\u9fff]',originals['zh'])),
        'english_whitespace_words':len(results['en'].split()),'previous_english_whitespace_words':len(originals['en'].split()),
        'chinese_sha256':sha(results['zh'].encode()),'english_sha256':sha(results['en'].encode()),
        'chapters':32,'headings':len(headings(results['zh'])),'external_citation_occurrences':len(urls(results['zh'])),
        'revisions_by_language':{'zh':6,'en':6},'unchanged_chapter_pairs':sum(r['review']['status']=='inherited-byte-identical' for r in ledger),
        'new_visible_events':len(events),'author_messages':sum(e['role']=='user' for e in events),
        'passages_with_exact_author_spans':sum(bool(p['exact_author_spans']) for p in passages),
        'exact_author_span_boundary':'Matching spans are evidence of reused words, not a claim that all additions are quotations.'}
    write_json(OUT/'editorial-statistics.json',stats)
    notes=f'''# 第十四版：文明注意力、动态博弈与制度自我进化

本版承接第十三版，收录2026年11月1日的五组讨论及作者本次整合要求。保留六条作者原话、六条可见AI答复（其中一条仅为上版完成边界）。中文增加一章与四个小节，并调整一处承接段；英文同步。其他文字逐字节保留，末尾自我反思附录仍在全书最后。

## 放置与内容

|位置|本次内容|主要来源|
|---|---|---|
|动态权重之后、个人需求与共同资源之前|从注意力到可演化的文明运行时：QKV、个人代理、现实状态、串并行协作、多视角、博弈概念、开放式演化和最小实验|AUTHOR-ATTENTION、AUTHOR-QKV-RUNTIME、AUTHOR-GAME-MODEL、AUTHOR-EMERGENCE及各自答复|
|文明的技术力量与自我治理能力|《守望者》与扩大和平选项；技术加速与文明纠错；合作意愿和信息质量共同迭代|AUTHOR-INTEGRATION-AND-SPEECH、AUTHOR-PARTICIPATION及答复|
|末尾附录|注意力类比、动态博弈、社会选择、参与条件与技术加速的检验边界|上述原话、编辑补充与外部研究|

## 保留与校准

尽量保留作者的第一人称、生活与工程类比、逐步推理和演讲力度。对QKV、博弈等原话中未展开的概念，编辑补充了定义、例子与读者疑问。逐段出处和能够逐字匹配的原话片段见[段落来源清单](passage-manifest.json)，所有原始消息见[时间线](07-thought-evolution.md)。来源关联不表示AI补充已获作者逐句认可。

技术区别在正文中直接讲清：RNN递推与CNN局部并行不再倒置；推理时的模型参数与随上下文变化的注意力权重分开；信息相关性、证据、参与权与执行权分开。纳什均衡不等于公平或全局最优，透明并不单独消除囚徒困境。马尔可夫博弈保持候选模型地位，并区分容纳创新、预测创新与可靠引导创新。

《守望者》区分漫画的伪外星乌贼与电影嫁祸曼哈顿博士；“较小损失”作为人物的判断，而不是已获证明或正当授权的结论。AI路线的变化说明创造新选项的可能，不写成Transformer终结全部分歧。技术和商业探索也可能涉及真实人身损害，避免把其成本简单说成只有算力和金钱。

作者关于奇点迫近、加速不可逆、差距与风险无限增加及彻底消除风险的原话完整保留在来源中。正文保持紧迫感，将日期、不可逆性与零风险保证改为有条件的情景和制度目标；现有研究只支持局部可验证任务中的自我改进，不支持已出现无限递归通用智能。政治文件用于核对公开表述，不证明任何国家的真实动机、合作效果或未来必然结局。

## 可核验的改动

- [中文版差异](03-zh-revisions.patch)与[英文版差异](03-en-revisions.patch)各包含六处有边界的编辑；[修改清单](revision-manifest.json)保存前后文本、Unicode半开区间与哈希，可以双向还原。
- [本轮中文新增稿](06-additions.zh.md)与[英文新增稿](06-additions.en.md)方便单独审读。
- [逐章双语对照](05-translation-notes.md)覆盖32章，其中{stats['unchanged_chapter_pairs']}组章节完整继承上版字节；改动章节作语义、例子、限定条件、标题层级和引用核对。
- [外部依据与边界](08-source-ledger.md)区别研究结论、制度提案与文学思想实验。

本版中文{stats['chinese_cjk_characters']:,}汉字，比上版净增{stats['chinese_cjk_characters']-stats['previous_chinese_cjk_characters']:,}汉字；英文约{stats['english_whitespace_words']:,}个空白分隔词项。数量是文稿规模，不表示理论已经验证。既有公平发展、能力互补和跨领域合作的修正原样保留。
'''
    (OUT/'04-editorial-notes.md').write_bytes(notes.encode())
    trans=['# 中英文逐章对照 / Chinese–English chapter map\n',
        '英文使用英语行文表达，保留中文论证的方向、例子与限定条件。未改动章节沿用第十三版，不冒称本轮重新逐字翻译。\n',
        '|章节|中文|English|本轮状态|','|---|---|---|---|']
    trans += [f"|{r['id']}|{r['title_zh']}|{r['title_en']}|{r['review']['status']}|" for r in ledger]
    trans += ['\n[中文全文](01-new-principles.zh.md) · [Full English text](02-new-principles.en.md) · [精确区间与引用对照](translation-ledger.json)']
    (OUT/'05-translation-notes.md').write_bytes(('\n'.join(trans)+'\n').encode())
    landing=read(PUBLIC/'book/readme.md').replace('2026-10-31-book-bilingual',OUT.name)
    marker='本书强调公平的发展条件、能力多样性与跨领域合作。'
    assert landing.count(marker)==1
    landing=landing.replace(marker,'新增讨论将个人与文明层级的注意力、持续变化的社会状态和博弈机制连接起来，并考察技术加速之下，制度怎样通过自愿合作、公开检验与和平试验持续自我修正。\n\n'+marker)
    marker='The book argues for fair conditions'
    assert landing.count(marker)==1
    landing=landing.replace(marker,'New chapters and sections connect attention at personal and civilizational scales with changing social states and strategic interaction. They ask how institutions can keep learning through voluntary cooperation, public scrutiny, and peaceful experiments as technology accelerates.\n\n'+marker)
    (OUT/'book-readme.md').write_bytes(landing.encode())
    references=json.loads((WORK/'references.json').read_bytes())
    write_json(OUT/'08-external-references.json',references)
    source_lines=['# 本轮外部依据与来源边界\n',
        '新增正文中的研究与事实引用如下。社会架构、文明奇点和元规则是本书提出的研究方向，不能据引用推定已被这些研究验证。已有章节的历史引用原样保留，本轮未重新核查全部历史事实。\n',
        '|来源|材料类型|可支持的范围与限制|','|---|---|---|']
    source_lines += [f"|[{r['title']}]({r['url']})|{r['type']}|{r['scope']}|" for r in references]
    source_lines += ['\n作者与AI的原始讨论另见[思想演化时间线](07-thought-evolution.md)，精确引用区间另见[段落来源清单](passage-manifest.json)。未将全部研究论文收入公开语料，也未保存本轮隐藏推理或工具日志。']
    (OUT/'08-source-ledger.md').write_bytes(('\n'.join(source_lines)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':build()
