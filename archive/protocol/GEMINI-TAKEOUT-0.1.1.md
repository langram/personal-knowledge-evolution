# Gemini Takeout 0.1.1：审阅澄清

本文件追加解释 0.1，不改写已取证的数据或 `GEMINI-TAKEOUT-0.1.md`。0.1 的 raw CID 为 `bafkreihi5c2hcf4zcsb337vuvoa65thtt7xe4igahxemzwegr46sx4fp3e`。依据 `contributions/claude/REVIEW-GEMINI-1.md` 的 G1–G5；当前数据根为 `bafyreihzmmps7pewfyca6cvpaioudygdvezykfn77r4rqybfiplpcvutkm`。

1. **受控身份例外（G1）**：仅在原生对话 ID 缺失或歧义时，source.native_thread_id 使用明确标注的 `raw:<CID>#/<index>`。这是基础协议“source 不含整文件 hash”规则的受控例外，理由是原生身份不存在或无法唯一确定。这个字符串不是 Google 原生 ID，不具有跨导出稳定性。27 条非对话活动也保留此取证内 fallback，不编造一个所谓原生活动流 ID。
2. **口径（G2）**：这份导出观察到 437 个不同对话 URL ID；427 个至少出现于一个单 ID 条目，可据此建立来源；另外 10 个只出现于 9 条歧义条目。27 条没有对话 ID 的条目全部为非对话活动。全部 1,427 条 Prompted 都至少有一个对话 URL。
3. **跨导出候选（G3）**：只有明确且唯一的对话 ID 相同、原 `time` 字符串相同、Prompted content CID 相同，才允许提出独立的 occurrence-equivalence 候选。按 CID binary 排序端点；basis=inferred；scope 明示“matching export fields, identity unverified”。多条满足时必须保留多候选，不能择一；不覆盖、不合并、不自动折叠显示原事件。此规则是身份推断，不是源格式提供的身份关系，因此不采用 source-structure。同一时间和文字不足以证明同一事件，也不保证将来的导出可以稳定去重。当前只有一个导出，尚不生成这类候选。
4. **附件（G4–G5）**：member_name 是 ZIP 内完整归档路径，不是 basename。missing 的精确含义仅为“未找到完全相同归档路径的成员”，不表示已经证明附件字节未导出。73 处未匹配引用对应 36 个不同路径；35 个路径有同名但扩展名不同或缺失的候选，1 个暂未找到同名候选。候选始终与 resolved 分开；不能修复源中的 U+FFFD 字符。类型嗅探或能解码 UTF-8 仅支持类型判断，不能单独证明文件身份。
5. **保真与时间**：Prompted 的保真级别为 export-title，保存去掉精确导出前缀后的原字符串；已知样本未发现截断证据，但不保证服务端无限保留正文。回复时间继续 unknown，不新增未经来源保证的时间下界。多个 safeHtmlItem 的顺序不等于分支或编辑谱系。

以上均为证据身份、覆盖和未来候选规则澄清；不改变用户思想、不构成用户采纳。双方确认收据另存 consensus，不修改已哈希文件来更新状态。
