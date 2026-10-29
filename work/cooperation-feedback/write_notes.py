"""Record factual boundaries and the conceptual extension beside the manuscript."""
from prepare import OUT, ARCHIVE, write_json
import json

sources=[
    {'title':'Introduction to the Inefficiency of Equilibria','url':'https://www.cs.cornell.edu/~eva/agtchap17.pdf','scope':'作者提供的博弈论教材章节；均衡可低效，不能把纳什均衡直接等同于整体最优。','evidence_kind':'primary-author-text'},
    {'title':'The Evolution of Cooperation (Axelrod and Hamilton, 1981)','url':'https://public.websites.umich.edu/~axe/research/Axelrod%20and%20Hamilton%20EC%201981.pdf','scope':'TFT首次合作、以后复制对方上一轮行为的定义及特定研究结果；不证明普遍最优。','evidence_kind':'primary-paper'},
    {'title':'Boeing 737 MAX 2021 DOJ agreement announcement','url':'https://www.justice.gov/archives/opa/pr/boeing-charged-737-max-fraud-conspiracy-and-agrees-pay-over-25-billion','scope':'2021年协议材料所载MCAS信息隐瞒与评估、培训材料缺失；不叙述此后案件最终处置，也不推断飞行记录器信息被隐瞒。','evidence_kind':'official-primary-record'},
    {'title':'FAA Oversight of Boeing’s Broken Safety Culture: hearing','url':'https://www.hsgac.senate.gov/subcommittees/investigations/hearings/faa-oversight-of-boeings-broken-safety-culture/','scope':'2024年安全文化与监管听证背景；证言不等同于每一项指控已经裁定。','evidence_kind':'official-primary-record'},
    {'title':'FAA testimony on Boeing safety culture','url':'https://www.transportation.gov/faa-oversight-boeings-broken-safety-culture-0','scope':'报告安全问题不受报复及报告得到调查的重要性。','evidence_kind':'official-primary-testimony'},
    {'title':'EPA and California Volkswagen notice, 2015','url':'https://www.epa.gov/archive/epa/newsreleases/epa-california-notify-volkswagen-clean-air-act-violations-carmaker-allegedly-used.html','scope':'识别排放测试的软件及独立分析引发监管调查的经过。','evidence_kind':'official-primary-record'},
    {'title':'尊界刹车踏板支架断裂风波再追问','url':'https://www.thepaper.cn/newsDetail_forward_34216478','scope':'仅用于确认围绕事件存在公开争议；本轮未直接取得完整原始试验、厂方原帖或独立最终调查，不能据此作工程归因或认定隐瞒。','evidence_kind':'secondary-report-of-dispute'}]
write_json(OUT/'external-sources.json',sources)
request=json.loads((ARCHIVE/'request-capture.json').read_bytes())
text=f'''# 编辑说明与思想演化

来源为作者本轮完整消息，原生时间 `{request['time']}`，保存为[作者原话](00-author-original.txt)。此时间是会话时间，不是思想首次形成时间。正文的原话区间、逐项润色及补写理由见[编辑对照](03-source-ledger.md)与 passage-manifest.json。

新章“公共知识、互惠与合作的正向循环”放在“权力的约束、伤害的防止与信任的生长”之后、“从一个人的云存储开始”之前。整章之外的第七版正文保持原有字节；这次是第八个已保存全文版本。

论述沿作者的顺序展开：信息不充分与隐瞒增加对抗成本；商业案例引出共同核查的需要；互惠反应可能放大不信任，也可能强化合作；正向起点需要查证与纠错来维持；五项规则把分享、保护、补偿与长期风险安排连起来；最后讨论因果理解与人的情绪、认知怎样互相促进。

这次保留了作者正文的全部主要段落与五项规则。纳入正文的15个来源片段覆盖2146个原始字符，不包括写作指令与分隔符。字面保留量与补写量分别记录在 editorial-statistics.json；不能把全部成文都归作未经编辑的原话。对具体改写的作者采纳状态仍待作者审阅。

## 必要校正

- “全局最优的纳什平衡”改为整体更有利且能够持续的合作。纳什均衡说明单方面偏离的收益条件，不保证整体效率；社会目标与公平条件也需要明确。
- “全人类都知道且遵守以牙还牙”改为广泛存在的互惠倾向。严格TFT有明确的两步规则；本章提出的核查、修复、补偿与有边界防护，是更丰富的制度设想。
- “公开后怀疑几乎不可能发生”改为使怀疑能够通过证据澄清，使缺陷更早被发现。公开记录需要与实物、实际运行版本、测试和交付批次核对，哈希不能替代现实核验。
- “初始方向是最关键一步”保留为关键条件，同时补入误操作和误解后的恢复路径。没有在本轮证明该规则在所有博弈、收益条件与噪声水平下最优。
- 保留积极分享，明确与合作有关、必要且有实际保护的信息；公共记录不要求公开全部私人资料，也不把发送通知等同于形成共同理解。
- 保留及时补偿和策略修复，补入立即止损、救助、补偿资源和责任核查。受损者不必先认定恶意，也不能被要求放弃怀疑或追责。有限资源下的补偿需有实际安排，不承诺一切伤害都可恢复。
- 长期成本由事前告知、受影响者参与、适用授权、停止条件和承诺兑现来支持。失败是否涉及故意或过失要查证，不能被预先免责；成功也不能使未获授权的伤害自动正当化。
- 将“机制已经消除一切伤害”表述为持续消除任意伤害条件的设计目标。内容记录、集体判断、执行权限及现实救济需要分别检验。
- 因果理解与理性优先保留；“所有差异均可重现解释”“所有善恶与宗教判断仅为非理性”改为可检验的解释方向，以及对固定敌我标签的批判。理解原因不取消责任，情绪也可以传达真实处境。

## 事件证据范围

尊界：仅作为已经公开报道的争议及“怎样共同核查”的问题入口。本轮取得新闻报道和对厂方声明的转述，没有取得可直接复核的完整原始工程材料；没有采用网传力值、车型参数、标准编号或所谓最终责任结论。

波音：以2021年司法部公开材料中的MCAS信息披露问题、2024年听证及FAA证词为依据。原话中的“黑匣子”未被改写为对飞行记录器隐瞒的事实指控；未引入吹哨人死亡原因等没有支持的推论，也未声称MCAS是所有事故或后续问题的唯一原因。

大众：采用EPA的2015年官方公告，限于测试识别软件和独立分析引发调查的经过。

战争与大国对抗：保留作者的考察方向，不用一个反馈模型替代具体历史研究，也不把任何一方全部动机归结为信息问题。

文中链接对应实际用于写作的资料。尝试获取的另一些论文、诺奖说明页遇到访问限制，不作为已完整阅读或直接引用的依据。本轮外部核查日期为2026年10月29日。

## 知识库新增关系

新增信息隐瞒与互惠对抗循环、合作起点与可纠错的互惠、共享依据与实际保护、救助补偿与证据责任、长期成本与停止条件、因果理解与合作认知六个概念。它们连接既有合作、公共知识、动态权重、隐私、资源分配、数据主权及保护—信任主题，同时衔接上一章的可核验文明协作底座。

这些关系是有来源的编辑梳理，不是已经验证的制度效果。原话、编辑解释、外部事实与作者是否接受具体措辞，分别保存。
'''
(OUT/'04-editorial-notes.md').write_bytes(text.encode())
print('Editorial notes and external source ledger written.')
