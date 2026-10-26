# ChatGPT 官方导出适配 0.1

2026-10-26。Codex 实现与独立代码路径核验；尚无 Claude 审阅。扩展 PKST 0.1/N3.1，不改写冻结核心。

## 范围与构造选择

处理用户已下载的官方 ZIP。原 ZIP 和每个成员按字节保存，成员路径仅作元数据，绝不用其创建本地路径。对照 export_manifest.json 的文件名、长度、logical_files 分卷清单，再逐卷解析。chat.html、账户资料、文件库清单等仅保存原件，避免重复聊天或将账户配置算作个人思想。

候选比较：网页 HTML 抓取容易遗漏分支和原生身份；重建整库成本高且不必要；采用已有流式原件保全、CAR 编码及 SQLite 增量视图，并添加原件逐字段核验。记录实际耗时和字节数，不预先声称能耗优势。

## 身份、时间与父关系

- source 为 chatgpt / owner-openai-account / conversation.id；conversation_id 必须一致。标题不能替代 ID。
- mapping 中每个非空 message 产生 occurrence，包括 opaque 推理记录；空根节点只保留在拓扑和原件中，不虚构发言。
- message.id 是 native_id；节点 ID 与 message.id 的差异会保留。无 ID 时以原始 JSON Pointer 为定位，不编造跨导出身份。
- user 通道 actor_kind=unknown，assistant=ai，其余显式映射或 unknown；process_kind=unknown。通道不证明作者身份。
- create_time 用 Decimal 读取，保存精确十进制秒字符串，绝不借用会话时间。未知保持 null。显示日期是派生 UTC/香港时间，原 epoch 不改。
- native_parent_ids 保存 mapping 节点的 parent。metadata.parent_id 另存 chatgpt:metadata_parent_id，二者不一致记录缺口，不猜测哪一条代表真实回复或思想因果。
- chatgpt:node_id、chatgpt:content_type、chatgpt:metadata_parent_id 是 occurrence 扩展字段。conversation 节点记录完整原生拓扑和 current_node；不依据字典顺序排序为对话，不宣称导出包含全账户全部分支。
- 各事件 extraction-record 指向 /会话序号/mapping/转义节点键/message；block-reference 指向每个原块。消息其他元数据另作 projection，从取证对象引用，不改变正文。

## 内容规则

text / multimodal_text 的字符串 parts 原字符保留为 content，数组顺序保留；结构 parts 用明确 python-json-v1 projection。未识别类型只作 projection，不默认为用户言论。thoughts、reasoning_recap、analysis、reasoning、thinking 及加密类型使用 PKST opaque-block：只存规范投影的 SHA-256 指纹、原生类型、raw-only 标记；不向正文索引输出其文本。原生 channel=analysis 也适用。

纯文本不 trim、NFC、改换行或转换标点。重复 JSON 键和非有限数字拒绝解析，记录来源错误，保全仍然有效。一个分卷失败不得激活完整新索引；其它原件保持接收。

## 附件与扩展对象

pkst/chatgpt-conversation@0.1 包含 source、raw、pointer、metadata、topology；metadata/topology 为投影链接，拓扑只含节点 ID、parent、消息 ID，不重复正文。

pkst/chatgpt-attachment@0.1 包含 occurrence、raw、pointer、reference、resolution、candidates。只接受原生附件 ID 加 .dat 或明确 file-service:// / sedim:// 标识与包内名称的一对一精确匹配。不使用相似文件名来确认身份。candidates 是按 CID 二进制排序的集合。未匹配表示此规则在本包未找到，不证明文件永久丢失。文件库的全部条目另列精确覆盖报告；不下载任何外部 URL。二进制及图片不执行、不 OCR、不推定内容。

## 核验和版本

检查 ZIP CRC、所有原件 SHA-256/CID、官方清单、每个非空消息的角色/正文/时间/父字段/原件坐标、完整节点覆盖、附件绑定、CAR 引用闭包、规范编码和统一目录 DAG。验证同文不同事件、重复转换稳定、分叉、空根、未知时间、精确小数、推理不进入检索、损坏块拒绝。新目录从上一数据库备份构建并保留父快照，逐字段核验和查询通过后才切换 current.json。

这次是证据层导入，不将 11,999 条记录称为 11,999 个思想；跨来源文本候选和语义提炼是后续独立步骤。新记录不自动变成用户已采纳观点。
