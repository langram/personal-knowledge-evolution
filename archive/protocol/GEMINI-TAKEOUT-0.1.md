# Gemini Takeout 适配规范 0.1

状态：Codex 已实现候选，待 Claude 独立审阅。基础协议仍为已冻结的 PKST 0.1/N3.1；本文件不改写基础协议字节。

实际样本：Google Takeout 的 My Activity / Gemini Apps JSON 数组。2026-10-24 收到的 ZIP 有 149 个成员；活动 JSON 有 1,454 个条目。字段与含义只针对这个格式，不声称所有年份/账户导出相同。

## 身份与坐标扩展

1. 来源仅从条目 `details[].url` 中的完整 `https://gemini.google.com/app/<id>` 提取对话 ID；重复相同 URL 去重。零个或多个不同 ID 时不猜测分组，使用 `raw:<CID>#/<array-index>` 明示采集内 fallback，并报告缺口。
2. 此导出没有原生消息 ID。扩展 occurrence.locator 为 `{raw:link, coordinate:"json-pointer", pointer:string}`，指向完整原始 JSON 文档中的节点。JSON Pointer 遵循 RFC 6901 的字符串形式；数组索引只是此次采集内位置，不是跨导出稳定身份。
3. extraction-record 继续使用基础协议已有的 `coordinate=json-pointer`，指向同一节点；不得同时添加 start/end。重复导入同一原件保持证据 CID；数组重排或新增导出将产生新的 fallback 身份，不自动认定同一事件。
4. 所有原生父 ID 为 null；相邻条目不能推定回复链。`safeHtmlItem` 的数组顺序仅保留导出顺序，不推断多条回复的分支、编辑或时间顺序。

## 字段投影与作者

- `title` 以精确 ASCII `Prompted ` 开头：去掉该导出标签后，其余字符逐字保存为 content；native_role=`Prompted`，actor_kind=unknown。extraction-record.role_basis 明示这一变换；原 title 仍在 raw 中。
- `safeHtmlItem[j].html`：保存为 `pkst/projection@0.1`，native_type=`gemini-safeHtmlItem`，profile=`python-json-v1`，text 是整个 `{html:...}` 对象的规范 JSON 投影。对应 occurrence.native_role=`safeHtmlItem`、actor_kind=ai，依据是导出字段及已检查的同一对话网页；这不提供模型版本或用户采纳。HTML 不执行、不把去标签文本伪装成原生文本。
- 每条 HTML 回复的时间保持 unknown：条目的 `time` 只赋给 Prompted/其他活动 occurrence，不冒充回复生成时刻。原数组条目 pointer 的前缀能恢复条目级同组关系，不自动创建 reply-to 或 answers 边。
- 其余活动（Created Canvas、Cleared feedback、Selected draft 等）保存整个条目的 projection；native_role=`activity:<title第一个词>`、actor_kind=unknown。不当作用户言论。
- 每个 extraction-record 保存字段类型和转换依据；每个 block-reference 的 document_pointer 指向活动条目，pointer 指向其中字段。所有正文仍可溯源到完整原始 JSON。

## 附件扩展对象

新增 `pkst/gemini-attachment@0.1`：`occurrence(link), document_raw(link), document_pointer, field_pointer, member_name, candidates(按 CID binary 排序的 links), status`。其中 candidates 必须零个或一个；同名多成员且内容不同属于 ambiguous，candidates 为空并在报告记录候选。此对象独立引用 occurrence，不能被 occurrence 反向引用。

仅将 attachedFiles、imageFile、subtitles[].url 中的导出相对文件名与 ZIP 清单相匹配。URL 不联网，文件不执行，ZIP 路径不用于解压。missing/ambiguous 显式保留。所有成员原件都纳入快照，包括尚未对应到消息的文件。附件内容不在本轮进行 OCR、转写或语义抽取。

## 验证与范围

逐对象 CID 和 CAR 闭包、全部原件 SHA-256、全部 JSON Pointer、逐字 prompt、逐 HTML 投影、附件引用逐一验证。最小反例覆盖相同文字不同事件、不同 raw 的 fallback 身份变化、多回复不捏造时间/分支、重复 JSON 键拒绝、附件缺失/同名歧义。

1436 条 details 链接不能解释为 1436 个会话；当前实测去重为 437 个对话 ID。覆盖仅限这一份官方导出，不代表被删除/未保留/导出未包含的全部会话。语义抽取与思想归属另行审阅。
