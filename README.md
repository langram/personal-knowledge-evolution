# Personal Knowledge Evolution

个人知识、言论与思想演化的公开档案。作者：Tangram Liu（langram）。

这里保存已收集的跨 AI 会话正文、思想关系、《新原理》及其现存编辑版本，并提供可以在普通电脑上运行的只读访问接口。来源身份与内容身份分别保留，原话、AI 回复、编辑解释和作者是否采纳互不替代。

## 阅读文章

- [《新原理》当前全文](book/current.md)
- [本次修订：能力形成、资源累积与分布](archive/dossiers/2026-10-31-ability-resource-formation/01-section.md)
- [文明自我治理、权重边界与制度探索](archive/dossiers/2026-10-31-civilization-self-governance/08-edition-additions.md)
- [个人信息采集、数据主权与技术落地](archive/dossiers/2026-10-30-recording-and-reflection/01-chapter.md)
- [书末附录：对理论基础与实践可行性的自我反思](archive/dossiers/2026-10-30-recording-and-reflection/05-self-reflection-appendix.md)
- [公共知识、互惠与合作的正向循环](archive/dossiers/2026-10-29-cooperation-feedback/01-chapter.md)
- [新增：AI时代的Merkle-DAG语言与软件生态](archive/dossiers/2026-10-29-merkle-native/01-chapter.md)
- [Merkle-DAG章节的原话与演化记录](archive/dossiers/2026-10-29-merkle-native/04-evolution-and-placement.md)
- [权力的约束、伤害的防止与信任的生长](archive/dossiers/2026-10-27-protection-and-trust/01-chapter.md)
- [从数学家的灵感到文明的共同创造](archive/dossiers/2026-10-26-shared-credit/01-chapter.md)
- [从学生的灵感到基层的创造](archive/dossiers/2026-10-26-shared-credit/05-section-ten.md)
- [现存版本与修改过程](history/README.md)
- [本轮原话与逐项改写对照](archive/dossiers/2026-10-31-ability-resource-formation/03-source-ledger.md)

## 运行访问接口

需要 Python 3.10 或更高版本，公开阅读程序仅使用标准库，不需要 API Key，也不需要访问作者的设备或 AI 账户。

```sh
git clone https://github.com/langram/personal-knowledge-evolution.git
cd personal-knowledge-evolution
python -m pkst_public verify
python -m pkst_public build
python -m pkst_public search "动态权重" --limit 10
python -m pkst_public stats
python -m pkst_public serve
```

首次构建会核对全部公开对象的 CID，并生成 `.cache/catalog.sqlite`。数据库可以删除重建，不上传 Git。默认 HTTP 地址为 `http://127.0.0.1:8765/v1/stats`；服务只读。GitHub 仓库提供代码和数据，HTTP 服务由阅读者自行启动。

[接口说明与示例](docs/API.md) · [公开格式与来源规则](docs/PUBLIC_FORMAT.md)

## 内容与范围

- `corpus/`：按 CID 分片的公开会话、项目文本和编辑对象，可直接读取 JSONL。
- `archive/dossiers/`：文章、早期方案、来源选取、段落对照和已有归档收据。
- `archive/protocol/`：此前协商的 PKST 协议及记录。
- `archive/contributions/`：两方的转换、核验、协商与编辑材料。
- `work/`：保存下来的构稿、转换和验证脚本及编辑工作文件。
- `publication/`：覆盖统计、脱敏记录、剔除清单及文件完整性清单。

准确的来源数量和剔除原因见[公开覆盖报告](publication/coverage.json)。这个版本公开的是知识与会话的可阅读投影，**不是未经处理的原始账号备份**：凭据字段和授权下载链接被替换；系统及开发者消息、隐藏推理、工具内部记录和整包原始备份不公开。部分附件未在原始采集中取得，不能据此认为这里覆盖所有账户的全部历史。

原始内容哈希、原生发言时间和公开转换关系保留。发生脱敏或格式转换时生成新的公开对象身份，不冒充原始字节。Gemini 的 HTML 回复转换为不执行 HTML 的纯文本，并明确标记派生关系。

文章的所有已保存版本、编辑对照与构稿脚本纳入 Git。首次导入会按版本顺序重建阅读上的修改轨迹，提交时间是实际导入时间，不伪造过去的 Git 历史；未曾保存或已经被覆盖的中间修改无法凭空复原。

## 理论与证据

本仓库也用于发展关于公共知识、公共智能、动态权重协作与新组织机制的理论。收录一个观点不代表作者赞同它；提出一种机制不代表已证明其有效。Merkle-DAG 及哈希用于核对内容和版本关系，不能单独证明原创、真理、公平或现实授权。

历史报告中的“本地”“未发布”等表述保留其原始语境。当前公开范围以本 README 和 `publication/` 中的发布记录为准。

会话批量增量（2026年10月29日）：385条可见对话消息，271条本机原生记录、114条远程会话接口投影；不代表所有云端已刷新。完整边界见[覆盖说明](archive/dossiers/2026-10-29-merkle-native/06-import-coverage.md)。

随后追加作者关于公共知识、互惠与合作反馈的一条原话，形成第八版全文；[编辑说明与事实核查](archive/dossiers/2026-10-29-cooperation-feedback/04-editorial-notes.md)记录本次整理的依据与边界。

2026年10月30日追加七条来源讨论，形成第九版全文；个人信息采集与技术落地进入正文，涵盖数学和基础科学的自我反思成为书末最后附录。详见[本次编辑说明](archive/dossiers/2026-10-30-recording-and-reflection/04-editorial-notes.md)。

2026年10月31日形成第十版：加入作者对制度分叉、动态权重和混合互惠反馈的回应，展开文明技术力量与自我治理能力的关系。完整保留原话、首遍草稿、再校订差异与来源。详见[本次编辑说明](archive/dossiers/2026-10-31-civilization-self-governance/04-editorial-notes.md)。

2026年10月31日第十一版补入作者关于资源参与能力形成的回应，区分现有绩效、成长条件与不同制度下的能力分布。体育项目的比较保留为待检验假说；全文与编辑记录见[说明](archive/dossiers/2026-10-31-ability-resource-formation/04-editorial-notes.md)。
