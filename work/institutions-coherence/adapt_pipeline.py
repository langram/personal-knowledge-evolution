"""Create this edition's bounded pipeline from the previously verified implementation."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'civilization-attention'
def swap(s,a,b):
    assert a in s,a
    return s.replace(a,b)
def save(name,s):
    (HERE/name).write_bytes(s.encode())

s=(PRIOR/'build_edition.py').read_text(encoding='utf-8')
core=s[s.index('def read('):s.index('    timeline_md=')]
a=core.index('def assemble(');b=core.index('def build():')
assembly='''def assemble(language, baseline):
    chapter_map=sections(baseline);edits=[]
    for spec in EDITS:
        chapter=chapter_map[spec['chapter']-1];start,end=chapter['span']
        content=baseline[start:end];anchor=spec['anchors'][language];mode=spec['mode']
        if mode=='insert-heading':
            assert content.count(anchor+'\\n')==1,(language,spec['id'],anchor)
            pos=start+content.index(anchor+'\\n');before='';after=spec['text'][language]+'\\n\\n'
        elif mode=='substring':
            assert content.count(anchor)==1,(language,spec['id'],anchor)
            pos=start+content.index(anchor);before=anchor;after=spec['text'][language]
        else:
            matches=[p for p in content.split('\\n\\n') if p.startswith(anchor)]
            assert len(matches)==1,(language,spec['id'],anchor)
            before=matches[0];assert content.count(before)==1
            pos=start+content.index(before)
            after=before+'\\n\\n'+spec['text'][language] if mode=='append' else spec['text'][language]
        edits.append({'id':spec['id'],'chapter':spec['chapter'],'language':language,
            'old_span':[pos,pos+len(before)],'before':before,'after':after,
            'kind':'insert' if not before else 'replace','rationale':spec['rationale'],
            'source_refs':SOURCES[spec['id']],
            'attribution':'Author-requested editorial integration; baseline wording retains prior provenance; additions are not automatically author-approved.'})
    edits.sort(key=lambda e:e['old_span']);pieces=[];cursor=0;newpos=0
    for e in edits:
        start,end=e['old_span'];assert start>=cursor
        gap=baseline[cursor:start];pieces += [gap,e['after']];newpos+=len(gap)
        e['new_span']=[newpos,newpos+len(e['after'])];newpos+=len(e['after']);cursor=end
        e['before_sha256']=sha(e['before'].encode());e['after_sha256']=sha(e['after'].encode())
    pieces.append(baseline[cursor:]);return ''.join(pieces),edits

'''
core=core[:a]+assembly+core[b:]
core=swap(core,'for stem in list(SOURCES)[1:]','for stem in FRAGMENTS')
core=core.replace('edition-13/','edition-14/').replace('13-book-bilingual','14-civilization-attention')
core=core.replace("'ca/","'ic/").replace('edition 13.','edition 14.')
core=swap(core,'English meaning, argument, examples, qualifications and citations compared with Chinese; not author approval or proof of theory',
    'Changed English passages and adjacent context compared with Chinese; full chapter structure and citations checked. Unchanged wording inherited, not claimed freshly reread in full; not author approval or proof of theory')
header='''"""Reversible bilingual coherence edits and a fully attributed new author passage."""
import difflib
import json
import re
from pathlib import Path
from prepare import ARCHIVE, BASE, EDITION, OLD, OLD_EN, OUT, PUBLIC, WORK, sha, write_json
from edits import EDITS
SOURCES={e['id']:['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW'] for e in EDITS}
FRAGMENTS=['01-institutional-gap','02-empirical-reflection']

'''
save('build_edition.py',header+core+'''    from write_support import support
    support(results,originals,changes,ledger,passages,events,timeline)

if __name__=='__main__':build()
''')
s=(PRIOR/'verify_text.py').read_text(encoding='utf-8')
s=swap(s,"assert len(edits)==6 and sum(e['kind']=='replace' for e in edits)==1","assert len(edits)==21 and sum(e['kind']=='insert' for e in edits)==2")
s=s.replace('==223','==225').replace('==88','==94').replace("'headings':223","'headings':225").replace("'citation_occurrences':88","'citation_occurrences':94")
s=swap(s,"assert len(events)==12 and sum(e['role']=='user' for e in events)==6","assert len(events)==2 and sum(e['role']=='user' for e in events)==1")
s=swap(s,"    result={'status':'pass'",'''    review=json.loads((OUT/'full-book-review.json').read_bytes())
    assert len(review['chapters'])==32
    for row,section in zip(review['chapters'],sections(originals['zh'])):
        assert sha(originals['zh'][slice(*section['span'])].encode())==row['source_sha256']
    result={'status':'pass' ''').replace("{'status':'pass' ,","{'status':'pass',")
save('verify_text.py',s)
s=(PRIOR/'archive_edition.py').read_text(encoding='utf-8')
s=s.replace('civilization-attention','institutions-coherence').replace("'ca'","'ic'").replace("'ca:","'ic:").replace("'ca/","'ic/")
s=s.replace('edition-13','edition-14').replace('edition 13','edition 14').replace('edition 14 and retain','edition 15 and retain')
a=s.index('    definitions=[');b=s.index('    concepts=',a)
definitions=[
 ('技术影响与制度纠错的落差','技术的影响范围和传播速度，与参与、约束和纠错能力分别考察；不是宣称战后制度从未变化。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']),
 ('物质条件与主观生活体验','生活条件的改善不自动等于安心、自主和被尊重；地区与因果差异需要独立研究。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']),
 ('财富和信任资料的口径','具体年份、人群、财富份额和调查范围各自保留；编辑核验不覆盖作者原话。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']),
 ('注意力目标与个人掌控','预测点击与改善长期生活不同，注意力目标也需要个人参与、解释、调整与退出。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']),
 ('运行时与授权分层衔接','个人记忆、MerkleVM、冷热路径、任务注意力、证据权重、基本权利和执行授权协同而不混同。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW']),
 ('制度自我修正的经验检验','比较影响传播和纠错链条，在反例、不同人群与相同任务中检验新旧安排，允许修正自身优越性的判断。',['AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW'])]
s=s[:a]+'    definitions='+repr(definitions)+'\n'+s[b:]
a=s.index('    for a,b,predicate in [');b=s.index('        relations.append',a)
s=s[:a]+"    for a,b,predicate in [(0,1,'motivates'),(2,0,'qualifies'),(1,3,'motivates'),(4,3,'supports'),(3,5,'informs'),(5,0,'qualifies')]:\n"+s[b:]
s=s.replace("link(concepts[3]),\n            'evidence'","link(concepts[4]),\n            'evidence'")
s=s.replace('Retain fair development, complementary abilities and rights distinctions in the new architecture.',
    'Extend the preceding attention, runtime, cooperation, and institutional framework without replacing its earlier source or accepted ability-complementarity revision.')
s=s.replace('AUTHOR-INTEGRATION-AND-SPEECH','AUTHOR-INSTITUTIONAL-GAP-AND-REVIEW')
s=s.replace('Integrate subsequent discussion and author passages; preserve originals and edition-14 text outside bounded edit spans.',
    'Integrate the institutional-gap passage and coherence review; preserve originals and edition-14 text outside bounded edit spans.')
s=s.replace('Twelve visible events including prior-release context; six author messages; twelve reversible bilingual edits; 32 chapter pairs',
    'Two visible events including prior-release context; one author message; 42 reversible bilingual edits; all 32 Chinese chapters read, English changes compared and whole-book structure checked')
s=s.replace("['literal equivalence of brains, Transformers and society','proved singularity timeline','zero-risk social system','validated institutional effectiveness']",
    "['unchanged postwar institutions','identical US and China top-0.1 wealth trends','universal youth well-being decline','causal validation of the proposed institutions']")
s=s.replace('Civilization attention, evolving games, participation and peaceful institutional correction',
    'Institutional gap, distribution and well-being evidence, whole-book coherence and empirical self-correction')
save('archive_edition.py',s)
s=(PRIOR/'publish_edition.py').read_text(encoding='utf-8')
s=s.replace("'ca/'","'ic/'").replace('第十四版','第十五版')
a=s.index("    receipt=f'''");b=s.index("    (OUT/'09-archive-receipt.md')",a)
s=s[:a]+'''    receipt=f\'''# 第十五版归档收据：制度落差与全书衔接

中英文各21处可逆编辑，增加制度与技术落差、财富分配与生活体验，以及相应的经验自我反思。全书32章、{metrics['headings']}个标题；中文{metrics['chinese_cjk_characters']:,}汉字，英文约{metrics['english_whitespace_words']:,}个空白分隔词项。{metrics['unchanged_chapter_pairs']}组章节中英文逐字节不变。

新增2条可见来源事件：1条作者原话与1条上版完成答复。原话、编辑核验与补充、正文版本和英文派生关系分别保存。中文32章完整通读；英文改动及相关上下文作语义对照，全书作结构与引用检查，未改动英文继承上版。

专题根：`{report['snapshot']}`。

统一根：`{report['federated_snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

中文 SHA-256：`{metrics['chinese_sha256']}`。

英文 SHA-256：`{metrics['english_sha256']}`。

统一来源事件{report['current_events']:,}条；公开事件{coverage['published_events']:,}条。

来源、修改双向还原、章节引用、对象身份与版本关系经过检查；这些结果不证明理论成立，也不表示编辑措辞已获作者逐句认可。本收据在专题根形成后生成，由公开文件清单和Git保存，不参与自身专题根。
\'''
'''+s[b:]
s=s.replace("assert len(editions)==13","assert len(editions)==14")
s=s.replace("'title':'文明注意力、动态博弈与制度自我进化'","'title':'制度与技术落差、生活体验及全书衔接修订'")
s=s.replace('edition 13','edition 14').replace('13-book-bilingual','14-civilization-attention')
s=swap(s,"    for path in workfiles:","    workfiles += list((WORK/'review').glob('*.json')) + list((WORK/'review').glob('*.py'))\n    for path in workfiles:")
a=s.index("    text+='\\n2026年11月1日第十五版收录");b=s.index('    history.write_bytes',a)
s=s[:a]+"    text+='\\n2026年11月1日第十五版增补制度与技术落差、财富分配与生活体验，通读中文全书并修补注意力、博弈和文明自我进化的衔接，中英文同步。[修改、来源与32章复核记录](../archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\\n'\n"+s[b:]
a=s.index("    old='- [本轮全文修订");b=s.index('    readme.write_bytes',a)
s=s[:a]+'''    old='- [本轮新增章节、原话与中英对照记录](archive/dossiers/2026-11-01-civilization-attention/04-editorial-notes.md)'
    assert text.count(old)==1
    text=text.replace(old,'- [本轮全文衔接、新增论述与中英对照记录](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)')
    text+='\\n2026年11月1日第十五版增补技术红利、财富分配与生活体验的讨论，并完成中文全书衔接复核及对应英文修订。原话、事实口径、逐项修改和思想演化分别保存，详见[本版修改记录](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\\n'
'''+s[b:]
s=s.replace("text.index('截至第十三版')","text.index('截至第十四版')")
save('publish_edition.py',s)
s=(PRIOR/'validate_release.py').read_text(encoding='utf-8').replace("'ca/translation@1'","'ic/translation@1'").replace('len(editions)==14','len(editions)==15').replace("'editions':14","'editions':15")
save('validate_release.py',s)
refs=[
 {'title':'The Changing Wealth of Nations 2024','url':'https://www.worldbank.org/en/publication/the-changing-wealth-of-nations','type':'World Bank report page','scope':'1995—2020全球实际人均综合财富增长21%；含生产、人力、自然资本与净国外资产，不能当作家庭财产或分配指标。'},
 {'title':'Saez and Zucman: Wealth Inequality in the United States','url':'https://eml.berkeley.edu/~saez/SaezZucman2015.pdf','type':'Authors\' research paper','scope':'一项资本化估计：美国家庭最富0.1%的财富份额由1978年7%至2012年22%；不是今天或中国的估计。'},
 {'title':'World Inequality Report 2018 executive summary','url':'https://wir2018.wid.world/executive-summary.html','type':'World Inequality Lab report','scope':'中国最富1%的财富份额约15%（1995）至30%（2015）；与美国0.1%案例的人群口径和时期不同。'},
 {'title':'OECD trust survey 2024 results: release','url':'https://www.oecd.org/en/about/news/press-releases/2024/07/governments-must-better-engage-all-citizens-to-tackle-growing-gaps-in-trust.html','type':'OECD survey release','scope':'2023年10—11月30个成员国调查，政府低/无信任44%，高/中度信任39%；不能代表所有国家或所有公共机构。'},
 {'title':'World Happiness Report 2026 executive summary','url':'https://www.worldhappiness.report/ed/2026/executive-summary-happiness-and-social-media/','type':'Report executive summary','scope':'青年生活评价下降存在地区差异；不支持全球青年一致下滑，也不单独识别制度或社交媒体的因果贡献。'},
 {'title':'Negativity drives online news consumption','url':'https://www.nature.com/articles/s41562-023-01538-4','type':'Primary randomized-headline research, 2023','scope':'在线标题的负面措辞增加点击；结果不等于负面新闻导致普遍长期心理健康下降。'},
]
(HERE/'references.json').write_bytes((json.dumps(refs,ensure_ascii=False,indent=2)+'\n').encode())
print('Edition-specific build, validation, archive and public projection scripts prepared.')
