import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
OUT=BASE/'contributions/codex/civilization-seed-20261025'
DOC=BASE/'dossiers/2026-10-25-seed'
c=json.loads((OUT/'capture.json').read_text(encoding='utf-8'))
lookup={r['ref']:r for r in c['recent']+c['history']}
stages=[('H1','2024 年讨论保留多样性和条件优势','原文同时含其他未经本次核查的事实判断；这里只引用多样性主张。'),
('H2','语义功能节点动态映射到物理节点','这是共同智能网络的早期架构关联，首次提出时间未确定。'),
('H3','个人需要与集体资源的分配分开','保留原文的正态分配设想，未将统计形状升级为规范定律。'),
('H4','非暴力自由区、兼容加入退出、以实际收益吸引参与','建立研究、公众写作与组织筹备三线的旧指令只作为历史记录。'),
('H5','科幻和游戏作为体验与现实参与的接口','混合粘贴发生于此时；内部原讨论时间和每段作者未全部确定。'),
('R3','数据导出等待引发对服务资源优先级的质疑','个人体验记录与对企业动机的推断分开。'),
('R7','从等待问题转向数据控制与公共使命的落差','公开技术新闻未在本次档案中重新核实为事实。'),
('R10','REA 与每个人可支配的本地云端资源','用户明确数据收回在新框架中的作用。'),
('R14','澄清目标包括开放生产组织与分配决策机制','用户说设想比助手表述更进一步；不能据此说用户此前只想要备份。'),
('R16','以人 AI 设备的整体智能网络重新定义分析单位','用户修正助手的建模前提；关于新系统能力的判断保留为架构假说。'),
('R18','要求把理论接入个人云存储及经济文化发展路径','本次任务授权；宣言、小说与路线是助手新草稿，不倒填成历史用户原话。')]
out=['# 思想演化与理解修正','时间表使用香港时间 UTC+8，由原生时间派生。顺序表示本次可见材料的先后，不表示思想的首次产生，也不自动证明因果。','| 时间 | 来源 | 本轮整理出的推进 | 解释边界 |','| --- | --- | --- | --- |']
for ref,title,note in stages:
    r=lookup[ref];t=datetime.fromisoformat(r['time'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    out.append(f'| {t} | {ref} | {title} | {note} |')
out+=['','## 两条助手理解修正','R12 → R15：助手从个人数据与服务选择的理解，修订为生产、运营、分配与决策组织本身也属于新机制。证据是 R14 的明确纠正和 R15 的承认。','R15 → R17：助手补充以人、AI、传感器和执行设备组成的整体网络作为分析单位。证据是 R16 的纠正和 R17 的回应。这不是用户从某种旧立场转向另一立场的证明。','两条 change 对象均针对助手解释，保留旧版本。用户关于组织和智能的主张分别保留为独立 statement，未强行合并为一段最终教义。','## 逐字语义单元','以下引用都带内容块内的 Unicode 字符半开区间，原文无改写；statement 的 force 标识言语行为，不标识真理。']
for q in c['quotes']:
    out.extend([f"### {q['id']} {q['topic']}",f"来源 {q['ref']}；性质 `{q['nature']}`；言语行为 `{q['force']}`。",'> '+q['quote'].replace('\n','\n> '),f"对象 `{q['statement']}`；内容 `{q['content']}`；区间 [{q['start']}, {q['end']})。"])
out+=['## 尚未由整理者代为解决的问题','H1 的多样性与 R18 的全面替代目标怎样共同解释；“完全支配”的可执行范围；个人需求是否适合任何统一统计分布；动态权重如何影响具体执行；完整共同智能是否产生预期社会效果。路线中的建议只是候选解释，保留这些问题便于下一轮讨论。']
import re
timeline=re.sub(r'(?<=\|)\n\n(?=\|)', '\n', '\n\n'.join(out)+'\n')
(DOC/'03-evolution.md').write_text(timeline,encoding='utf-8')
profile='''# 本专题取证与编辑配置

复用冻结的 PKST 0.1 核心格式。范围是固定 JSONL 前缀中的 18 条所选原生消息和 5 条既有事件。每个新消息保持原生来源 ID、角色、正文、时间与父 ID；无消息 ID 时使用 raw 加字节区间的采集内身份。没有新建原生回复链。

本地 seed 命名空间：statement 的 seed:nature 是编辑分类字符串；seed:quotation 含 content CID 与 Unicode scalar 半开区间 start/end。assessment 的 seed:note 说明待审阅解释。所有扩展字段参与哈希，不改变核心字段含义。

新文稿均为 Codex 起草，按原始 UTF-8 文件字节归档；文稿不是用户 occurrence。文件元数据记录在生成 activity.coverage 中。文稿引用与声明仅代表草稿解释，不代表用户采纳。原话和混合粘贴的来源界限保留。

比较三条构造路线：重导全库会重复处理七十余万块；只写 Markdown 无法提供逐字取证与版本关系；采用现有编码器的少量新对象、复用旧证据，再增量更新可重建索引。字节校验、引用闭包与原文区间是验收对象，不以对象数量证明理论正确或性能优势。

基准目录、对象与协议不覆盖。增量索引重用上一目录的已核验记录，验证新链接和本轮引用的旧材料。全图引用完整性与无环性另行检查，但不称已重新计算所有历史原件散列。外部研究项目只读，不恢复暂停任务。
'''
(OUT/'PROFILE.md').write_text(profile,encoding='utf-8')
print('timeline and profile written')
