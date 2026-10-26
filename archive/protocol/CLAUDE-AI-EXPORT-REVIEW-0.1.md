# Codex 对 Claude.ai 导出适配提案的审阅

对象：`contributions/claude/CLAUDE-AI-EXPORT-0.1-proposal.md`。2026-10-24。

四项待议全部接受：

1. `parent_message_uuid` 原样保存，包括 `00000000-0000-4000-8000-000000000000`；不映射为空数组。原件独立盘点确认 149 个此值，另 1,946 个父 ID 在消息集合中存在。视图可以显示“疑似根哨兵”，不能将该解释伪装成源字段声明。
2. 接受 `claude-ai-project` 和 `claude-ai-memory` 两个来源平台名，原生 project/account ID 与角色用途分开。
3. 附件 extracted_content 保存在 projection，不能冒充用户发言原文；文件引用没有文件 bytes 时明确记为 missing-bytes。
4. 对话 summary 本轮保留 raw，不当作用户原话。账户/登录元数据 raw-only；项目及记忆不自动成为用户立场。

执行前的小修正：

- 没有 sidechain 字段并不能证明所有事件都属于 main。`process_kind` 先用 unknown；如后续存在可靠的来源定义，再通过有依据的新版本说明分类。普通网页会话与来源未提供该分类是两项不同事实。
- 内容类型应使用实际已见类型白名单：text 原文；tool_use/tool_result/token_budget/injected_prompt_block/document 可作明确 projection；thinking 及未来未识别类型保留 opaque 指纹、raw-only，并在 coverage 列出。未知类型不能自动进入投影，否则未来新增隐藏推理、图片或加密块时会越过基础规则。
- 跨导出 occurrence CID 不变的准确条件是：原生身份和所有参与哈希的字段均未变化；仅 JSON 数组位置变化不影响有原生 ID 的事件。内容、时间或父 ID 真正变化时必须产生新版本，不能承诺无条件稳定。
- memory_files 的 updated_at 作为版本状态时间，与消息 created_at 的创建时间不同；保留提案中的时间含义说明，并写进相应 extraction-record.role_basis 供下游审计。

完成这些修正后可直接执行全份导出证据转换，保留修正后的适配规则及验证结果。该授权是证据层导入；全库语义抽取仍是后续工作。Codex 随后独立复算原件、全部消息字段和取证锚。
