# NP2：原话主导的扩充稿与编辑溯源

复用已冻结 PKST 0.1，命名空间 `np2=urn:pkst:editorial:new-principles-expanded:1`。Codex 为本轮唯一写入者。所有对象保持 local-only；不修改 Claude 的贡献，不写入用户接受评价。

选择的构造路线：全库重导会增加成本且不能提高已存原件保真；仅写长文无法核对原话；本轮复用已有事件和取证锚，只新增四点反馈事件、文稿及逐段编辑对象，最后复制一次可重建目录并在核验后切换指针。

- `np2/source@1`：ref、kind、target（原文 content 或 raw）、occurrence（允许 null）、evidence、event_time、source_kind、library_raw（允许 null）。target 保持原字符，文件未知创作时间不从上传时间推定。
- `np2/document@1`：title、raw、edition、authorship、previous。previous 是旧文稿对象；新文稿不是新的历史用户发言。
- `np2/passage@1`：document、chapter、ordinal、kind、text、document_span、chapter_span、quotation（允许 null）、source（允许 null）、source_span（允许 null）、source_sha256（允许 null）、edits、author_assessment、editorial_reason。坐标为 Unicode 标量半开区间；edits 保持顺序，可从原文重建成文。
- 原文另存 `pkst/statement@0.1`，force=quote，holder=unknown，asserted_by=Codex。来源通道与人工选段判断，不被提升为作者原创或采纳证明。
- `np2/chapter@1`：document、key、title、raw、passages（阅读顺序）、review。章节 review 为编辑判断。
- `np2/chapter-topic@1`：chapter、concept、asserted_by、basis、scope。连接上版概念与本版章节，只是阅读映射，既有关系不自动变成本版每句话的真理判断。
- `pkst/change@0.1` 用 extend 表示用户要求的文稿扩充。from/to 指文稿版本，evidence 指本次四点反馈；不宣称用户思想随编辑改动而变更。

除核心集合字段外，passages、edits、files、implementation_files、区间数组均有序。核心集合按 CID 二进制排序去重。统计小数只放 JSON 原始文件，不引入 PKST-CBOR-1 禁止的 float。

新专题快照的 parent 是旧文稿专题快照。新统一目录的 parent 是旧统一目录。依赖图与父图保持 DAG；思想关系仍可有环。

正文 24 个部分、82 个正文来源入口、其余时间线材料和作者反馈一起保存。89 个所选来源逐一复核；这不是全库每条事件的完整语义审定。原话改写、编辑补写、技术校订与未来设想分开保存。所有实质性校订均待作者审阅。

反馈来自当前原生会话的固定字节前缀；只新增索引那一条反馈，前缀中的其他新增记录没有冒充全量导入。隐藏推理不提取正文。

核验分两步：先从已有原件独立重解析平台时间、角色和选取正文，再重放逐段改动；后核对新对象、归档文件、引用闭包与全目录 DAG。旧原件的全库字节检查沿用前次收据，不宣称本轮重复扫描整个语料。收据在根产生后生成，不把自身根写入自身内容。
