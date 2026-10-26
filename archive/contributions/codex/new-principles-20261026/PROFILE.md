# 《新原理》编辑整合配置 NP-1

复用冻结 PKST 0.1。Codex 为单一写入者，Claude 原贡献不改。新稿、主题、关系与校订均由 Codex 整理，不写入用户 accept 评价。原始记录、旧稿、旧概念、旧目录和原始失败保留。

本次比较三条构造路线：重导全库代价高且不能提高已保存正文保真；只写长文不能追溯关系；采用既有原件与取证锚，追加明确选择的编辑对象并复制可重建目录。后者使验证集中于本轮材料与完整引用图，而不宣称再次逐字节扫描全部历史原件。

np 命名空间 URI 为 urn:pkst:editorial:new-principles:1。扩展字段和对象全部参与 CID。扩展 schema 不改变核心对象语义：

- np/file-evidence@1：ref、raw、source_kind、writing_time、upload_time、capture_time、library_raw（可 null）、library_index（可 null）、origin。指向文件 bytes；未知写作时间保留 null，上传和观察时间独立。
- np/document@1：title、raw、edition、authorship。只是文稿，不是历史 user occurrence。
- np/evolution-entry@1：source_ref、occurrence、event_time、display_utc、description、interpretation_boundary、asserted_by。event_time 取 occurrence 原值；display 是派生显示，不是新的时间证据。
- statement.np:quotation：source_ref、content 或 raw 的 CID、Unicode 标量半开区间 start/end；np:document_span 另记正文区间和 document 链接。holder 保持 unknown；文件中的混合对话不整体认作用户。
- concept.np:chapters 与 np:source_refs 是按阅读顺序排列的数组；编辑概念独立于历史概念，不继承旧采纳。
- relation 的 np:in-tension-with 表示仍需澄清的条件张力；np:constrains 表示草稿路线受到另一主张约束。它们是明确的编辑扩展，不是数学证明。其余谓词复用核心协议。
- np:source_refs、np:chapters、files、timeline 等展示数组有序；核心 evidence/inputs/outputs/roots/parents/from_versions/to_versions 仍按 CID 字节去重排序。

关系图可含反馈环。内容引用与快照父图必须无环。正文、所选原文、来源账、章节映射、时间线和校订表一起归档。收据在根产生后保存，避免收据把自身根写进自身内容。

本轮仅追加两个较新的原生请求事件，固定同一会话前缀至 2026-10-26T04:01:39.792Z。其余文本事件复用旧 CID 和原取证锚。主要思想整理依据完整旧稿、既有21个概念与69个所选文本入口、10份材料；不是对全部事件的逐条语义审定。全部对象暂为 local-only。
