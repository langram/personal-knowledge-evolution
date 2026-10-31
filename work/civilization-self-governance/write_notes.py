"""Keep editorial decisions and bounded factual checks outside the author-facing prose."""
import difflib
import json
from fractions import Fraction
from prepare import OUT, sha, write_json

def notes():
    sources=[
      ('performance','O’Boyle and Aguinis 2012 The Best and the Rest','https://www.hermanaguinis.com/pdf/PPsych2012.pdf','作者公开PDF的摘要与开篇，讨论所研究职业中的绩效分布；不把绩效等同人的内在能力，也不推出所有需求服从任一分布。'),
      ('bitcoin','Nakamoto Bitcoin whitepaper','https://bitcoin.org/bitcoin.pdf','读取摘要、工作量证明、网络有效性检查及相关概率说明；少于半数不是所有攻击均不可能的通用定理。'),
      ('reciprocity','Nowak and Sigmund 1993 win-stay lose-shift','https://www.nature.com/articles/364056a0','原论文摘要经大学存档检索返回；出版社正文访问受限，存档为扫描件，未声称完成全文证明复核。仅支持策略比较依赖模型条件这一层论述。'),
      ('weather-model','Andrychowicz et al MetNet-3','https://arxiv.org/abs/2306.06079','读取作者摘要；特定变量、区域与预报时效内的气象预测进展。该论文是MetNet-3，不是GraphCast，也不证明控制天气。'),
      ('alphafold','Jumper et al 2021 AlphaFold','https://pubmed.ncbi.nlm.nih.gov/34265844/','读取PubMed论文摘要；结构预测的任务与CASP评估范围。Nature直接访问受限，PMC触发检查页，不声称据此读过全文。'),
      ('weather-modification','WMO Statement on Weather Modification','https://public.wmo.int/content/wmo-statement-weather-modification','读取官方说明；页面说明材料范围截至2024年6月，发布于2025年6月，页面后更新。区分局部干预、预测和无依据的大尺度控制。'),
      ('atoms','Eigler and Schweizer Positioning single atoms','https://research.ibm.com/publications/positioning-single-atoms-with-a-scanning-tunnelling-microscope','读取作者机构的论文摘要；低温、特定表面的单原子排列，不是任意材料任意尺度制造。'),
      ('gene-editing','FDA first sickle-cell gene therapies announcement','https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapies-treat-patients-sickle-cell-disease','读取2023年12月8日官方公告；特定疾病与细胞治疗中的基因编辑先例，不提供个体医疗建议或推广到全部疾病。'),
      ('individual-simulation','Park et al LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of Individuals v3','https://arxiv.org/abs/2411.10109v3','读取2026年6月28日v3摘要；1052名受访者、访谈或问卷构建的代理与所列预测任务，不证明全球社会长期演化已可模拟。'),
      ('simulation-method','Madden Evaluating the Use of Large Language Models as Synthetic Social Agents v2','https://arxiv.org/abs/2509.26080v2','读取2025年10月28日v2作者摘要；方法讨论提出适用范围、人类基线及校准，不当作本方案的实测验收。')]
    write_json(OUT/'external-sources.json',[{'id':i,'title':title,'url':url,'reading_scope':scope,
                                          'checked_date':'2026-10-31','full_page_copy':False} for i,title,url,scope in sources])
    score=[1,2,3]; direct=Fraction(max(score),sum(score)); mapped=[10**x for x in score]
    amplified=Fraction(max(mapped),sum(mapped))
    assert direct==Fraction(1,2) and amplified>Fraction(9,10)
    write_json(OUT/'example-checks.json',{'status':'pass','scores':score,'linear_highest_share':str(direct),
        'mapped_scores':mapped,'mapped_highest_share':str(amplified),'mapped_percentage':float(amplified*100),
        'scope':'Arithmetic illustration of a weight mapping; not population data or an institutional experiment.'})
    before=(OUT/'draft-01-additions.md').read_text(encoding='utf-8')
    after=(OUT/'08-edition-additions.md').read_text(encoding='utf-8')
    patch=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                                      fromfile='draft-01-additions.md',tofile='08-edition-additions.md'))
    (OUT/'draft-01-to-final.patch').write_bytes(patch.encode())
    write_json(OUT/'draft-revision.json',{'from':'draft-01-additions.md','to':'08-edition-additions.md',
        'before_sha256':sha(before.encode()),'after_sha256':sha(after.encode()),
        'reason':'Second editorial pass reduces unnecessary paraphrase while keeping factual and logical qualifications.',
        'before_statistics':json.loads((OUT/'draft-01-statistics.json').read_bytes()),
        'after_statistics':json.loads((OUT/'editorial-statistics.json').read_bytes()),
        'patch':'draft-01-to-final.patch','intermediate_draft_is_not_current_book':True})
    text='''# 第十版编辑说明

## 放置与书稿连续性

本版以第九版为底稿，新增《文明的技术力量与自我治理能力》，放在《公共知识、互惠与合作的正向循环》之后、个人信息采集章之前。另在动态权重、自由区、科幻与文化建设三处加入对应小节。四处插入之外保留旧稿字节，书末自我反思附录保持原样并继续位于最后。

## 原话与论证覆盖

原生来源包括2026年10月30日作者的独立研究委托、AI公开最终答复，以及2026年10月31日作者本次完整回应。角色、原话、来源时间均保留；时间不冒充思想首创时间。研究分支的三轮材料以固定提交、文件摘要和根引用连接，不把整个AI研究分支自动并入作者观点。

| 本次讨论 | 入书位置 |
|---|---|
| 统一基本规则、制度分叉、演化路径迷宫与能量成本 | 自由区章新增小节 |
| AI虚拟社会实验室、游戏与生物实验类比 | 科幻与文化建设章新增小节 |
| 按需分配与按能力判断、代理数量和历史优势 | 动态权重章新增小节 |
| 恶意篡改与账本安全 | 同一小节，明确协议条件 |
| 正负反馈只是两极简化，现实为混合互动 | 新章开篇 |
| 从个人经验、媒介到计算机和AI | 新章第二节 |
| 自愿表达、权力压制与信息质量 | 新章第三节 |
| 链子锤类比、军备恐惧与风险反馈 | 新章第四节 |
| 技术可靠性与文明自身可靠性 | 新章第五节 |
| 分享、保护、回报与文明智能 | 新章第六节 |
| 关键岔路口与共同选择 | 新章结尾 |

正文依作者论述次序展开，拆开过长段落，保留其例子、类比与第一人称表达。21个来源片段覆盖本次七个实质论述段；完整原话独立保存。最初编辑稿及其来源映射也被保留，第二遍校订恢复了更多原表达，前后差异可由补丁核查。

## 实质性限定及其理由

1. “任何需求、能力都正态分布”没有写成已证事实。保留的是需求、能力与可复利积累的资本支配权需要分开的制度主张；分布、权重转换和执行授权分别论证。绩效研究不被用来证明所有内在能力都幂律分布。
2. “绝不出现支配节点”改成制度必须阻断的关系，而不是仅由人群分布推出的保证。代理不是独立参与者，公共任务资源不是负责人的个人所有份额。
3. “作恶算力不超过一半就行”限定到协议及其攻击模型；内容身份、历史一致性、密钥与授权、原始信息真实性、实际执行并非同一问题。
4. “遍历所有演化可能性”和“完成亿万年进化”保留为广泛探索与加速愿景，没有作为有限资源能够穷尽无限空间或模拟已经替代自然演化的结论。
5. 天气预测不等于任意控制天气；蛋白质结构预测不等于掌握全部生命机制；基因治疗与原子排列保留具体条件。
6. 自愿分享是作者提出的关键瓶颈解释，不写成唯一障碍。补入数据质量、因果识别、参与者反应和模型误差，保留“不愿真实提供信息会限制认识”的核心论证。
7. “美俄冷战”更正为美苏冷战；恐惧引发升级写成有条件的反馈。未定义共同收益函数时，不直接给历史结局贴上数学上的全局或局部最优标签。事件列举保留历史性质，不当作当日战况报道；和平抗议不等同暴力侵害。
8. 文明作为生物体是信息协作类比，不取消人的独立意愿。精确控制全部博弈改为持续提高理解、预测与调节能力；岔路口表示行动方向与风险，不是两个注定的结局。

这些限定均可以在03-source-ledger.md与passage-manifest.json中逐项对照，不对原话做追溯覆盖。新的编辑补写明确记录为AI编辑建议，未声称作者已逐句确认。

## 核查范围

核查原生记录、文本身份、逐片段改写重放、四处插入和逆向恢复、书末附录位置，以及权重映射例子的算术。外部来源逐项说明实际阅读范围；访问受限时不声称完成全文审阅。本文未部署社会模拟、实际采集个人信息、执行真实资源分配，也未证明文明制度效果。
'''
    (OUT/'04-editorial-notes.md').write_bytes(text.encode())

if __name__=='__main__':notes()
