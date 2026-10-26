"""Keep the independent reading text separate from editorial and source records."""
import json,re
from prepare import BASE,WORK,OUT,ARCHIVE,PRIOR,OLD,write_json
from verify_text import time_display

def write():
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    stats=json.loads((OUT/'editorial-statistics.json').read_bytes())
    section=(OUT/'05-section-ten.md').read_bytes().decode()
    count=len(re.findall('[\u3400-\u9fff]',section))
    (OUT/'sources').mkdir(exist_ok=True)
    (OUT/'sources/CREDIT-REQUEST.txt').write_bytes(selected['CREDIT-REQUEST']['text'].encode())
    intro=f'''# 从学生的灵感到基层的创造 扩展修订版

[直接阅读第十节](05-section-ten.md) · [完整案例章节](01-chapter.md) · [《新原理》全文](02-new-principles.md) · [原话与改写对照](03-source-ledger.md) · [历史核对与编辑说明](04-sources-and-editing.md)

第十节现为 **{count:,} 汉字**，案例章节 **{stats['chapter_cjk_characters']:,} 汉字**，《新原理》全文 **{stats['combined_cjk_characters']:,} 汉字**。

本次将贡献记录的技术条件、历史上的荣誉分配、及时分享的正向反馈，以及提出想法与执行决策的关系，融入第十节。原版79个段落单元全部保留，新增内容仅位于第十节，其他章节和本章其他小节按原字节保留。

沿用12个来源入口，新增本次作者补充1条。新增5个来源选取单元；本次原话保留在来源文件，逐项修订与补写另列。这是依据作者观点展开的审阅稿，不把编辑补充自动记作作者采纳。

[上一版](../2026-10-26-public-intelligence/00-readme.md) · [归档收据](09-archive-receipt.md)
'''
    (OUT/'00-readme.md').write_bytes(intro.encode())
    note='''# 来源、演化与编辑说明

本版对应作者对第十节的两点补充。正文独立阅读；本说明保存原话、历史校订和编辑判断的界线。

## 本次论述的展开

1. 旧技术条件限制了日常协作过程的细致记录，使贡献承认更依赖记忆、个人意愿和组织权力；保留作者主线，同时承认历史上已有书信、期刊和学会制度。
2. 数字记录、版本关系和多方保存降低查证难度；评价标准仍需共同制定和复核，未将哈希、时间戳或动态权重等同于自动公平。
3. 可信的贡献承认、及时获得合作、参与扩大，可能相互促进。将“彻底失去荣誉”限定为“可能失去最先公开的机会”，保留独立发现、验证、应用和暂不公开的选择。
4. 保留作者希望降低错误执行概率的目标，补足提出、检验、试验、资源决定和执行的过程。动态权重的有效性取决于证据与实际反馈，不承诺零伤害或绝对正确。诚实试错不等于无责执行，错误也不成为人的永久标签。

## 历史核对

- [牛顿文献项目年表](https://www.newtonproject.ox.ac.uk/his-life-and-work-at-a-glance)：牛顿与莱布尼茨之争、与罗伯特·胡克的争议分别叙述；1712年调查中的利益与程序关系用于说明记录和公平审查的差别。不把历史冲突全部归因为个人品德。
- [达尔文与华莱士1858年文献](https://darwin-online.org.uk/content/contentblock?basepage=1&itemID=F350&hitpage=1&viewtype=text)：以共同发表及对独立原创的承认为例，不据此断言此后全部荣誉分配都已公平。安排共同发表的植物学家约瑟夫·胡克，与牛顿时代的罗伯特·胡克是不同人物。
- [国际数学联盟记录](https://www.mathunion.org/imu-awards/fields-medal)确认2006年菲尔兹奖被拒；[2010年7月1日国际文传电讯社采访](https://www.interfax.ru/russia/143587)对应拒绝千禧年大奖及对汉密尔顿贡献的说明。原话中的两个奖项已区分；未把多方面理由缩减为唯一动机，也未声称佩雷尔曼要求按某个比例分奖。

上述历史支持问题的提出，不构成新机制已经奏效的证据。编辑增加的数学爱好者、生产工艺场景均为说明机制的设想。

## 来源时间与演化

本次发言延展此前数学案例和公共智能论述；原记录和旧稿保持不变。以下日期是来源中的原生消息时间，不是相应思想的首次产生日期。编辑记录时间另见归档收据。

|原生时间|来源|与本版的关系|
|---|---|---|
'''
    for ref,r in selected.items():
        if ref=='CREDIT-REQUEST':path='sources/CREDIT-REQUEST.txt';usage='贡献记录技术、历史例子、及时分享及动态权重的新补充'
        elif ref=='INTELLIGENCE-REQUEST':path='../2026-10-26-public-intelligence/sources/INTELLIGENCE-REQUEST.txt';usage='此前知识与公共智能论述'
        elif ref=='MATH-REQUEST':path='../2026-10-26-mathematics-and-contribution/sources/MATH-REQUEST.txt';usage='数学案例写作请求'
        else:path=f'../2026-10-26-new-principles-expanded/sources/{ref}.txt';usage='沿用此前正文与原话区间'
        note+=f'|{time_display(r)}|[{ref}]({path})|{usage}|\n'
    (OUT/'04-sources-and-editing.md').write_bytes(note.encode())
    (ARCHIVE/'PROFILE.md').write_bytes('''# 共同贡献与及时分享增量归档

沿用PKST 0.1和PKST-CBOR-1。sc命名空间为urn:pkst:editorial:shared-credit:1。新增一个原生发言，复用12个此前来源；user通道不自动证明作者身份。

sc/document@1、sc/chapter@1、sc/passage@1、sc/source@1、sc/source-timepoint@1、sc/web-evidence@1沿用上一版相应pi结构的字段含义。段落previous_passage指向直接前版；版本保留全部原文，新增内容只在第十节。新增语义关系为编辑解释，不是社会机制的实证结果或作者全面采纳。

沿用既有编解码和索引方案，新SQLite视图约1.4GB。正文、对象、引用和检索重放核验后才启用；没有重新导入全库，没有新服务或外部发布。
'''.encode())
    plan={'schema':'sc/semantic-plan@1','new_concept':{
        'label':'可核对贡献、及时分享与可检验执行的正向反馈',
        'definition':'作者提出贡献记录技术和可信承认可能促进更早分享并扩大合作；编辑进一步展开独立发现、反例与提出和执行分离的条件。'},
        'relations':[
            {'concept':'C13','refs':['CREDIT-REQUEST','R34499'],'scope':'版本与来源记录支持贡献查证；不把记录等同于公平判断'},
            {'concept':'C23','refs':['CREDIT-REQUEST','R34511'],'scope':'动态权重参与评估，结合验证、反馈和执行条件降低错误执行概率'},
            {'concept':'C31','refs':['CREDIT-REQUEST','MATH-REQUEST'],'scope':'数学灵感、独立发现、证明及共同贡献的承认'},
            {'concept':'C32','refs':['CREDIT-REQUEST','R54886'],'scope':'分享得到可信承认后可能促进更多合作；加速是有条件的机制假说'}],
        'basis':'author-requested editorial extension; no empirical validation'}
    write_json(ARCHIVE/'semantic-plan.json',plan)
    write_json(ARCHIVE/'section-metrics.json',{'section_ten_cjk':count,'new_cjk':stats['chapter_cjk_characters']-stats['previous_chapter_cjk']})
    print(json.dumps({'section_ten_cjk':count,'chapter_cjk':stats['chapter_cjk_characters'],'whole_cjk':stats['combined_cjk_characters']},ensure_ascii=False))

if __name__=='__main__':write()
