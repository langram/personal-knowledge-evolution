# Claude.ai 官方导出适配规则 0.1.1（已经 Codex 审阅接受）

- 起草：Claude（claude-opus-5-5），2026-10-24
- 来源：
  - `contributions/claude/CLAUDE-AI-EXPORT-0.1-proposal.md`（raw CID `bafkreigsckhfiygngg7m7jukoh5qpylntirz2dpcdnkhplmg7l5qvelndu`，字节保留不改）
  - `protocol/CLAUDE-AI-EXPORT-REVIEW-0.1.md`（Codex 审阅：四个待议项全部接受，另有四项执行前的小修正）
- 基础协议：PKST-0.1 / N3.1，raw CID `bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq`，不改动。
- 本文件是完整的执行规则：0.1 提案中凡与本文冲突的，以本文为准。实测 schema 见 0.1 提案 §0。

## 1. 已定的决策（0.1 提案中的待议项）

1. **`parent_message_uuid` 原样保存**，包括根哨兵 `00000000-0000-4000-8000-000000000000`，**不映射为 `[]`**。视图可以把它显示为"疑似根哨兵"，但不能把这个解释伪装成来源字段本身的声明。实测：149 个父值是哨兵，另外 1,946 个父 ID 都能在同一对话的消息集合中找到。
2. 新增 platform：`claude-ai-project`（`native_thread_id = project.uuid`）和 `claude-ai-memory`（`native_thread_id = account_uuid`）。对话仍为 `claude-ai`（`conversation.uuid`）。namespace 一律为 `owner-claude-account`。
3. 附件的 `extracted_content` 只放在 projection 中（`native_type=attachment`），不冒充用户发言原文。文件引用（`native_type=file-ref`）没有文件字节，在 coverage 中记为 missing-bytes。
4. 对话的 `summary` 和 `name` 只保留在 raw 中。账户和登录元数据（`users.json`、`login_history.json`）也只保留 raw。项目和记忆**不自动**成为用户立场。

## 2. 0.1.1 修正（Codex 审阅提出，已落实）

1. **`process_kind = unknown`**，适用于全部对话消息。导出中没有 sidechain 字段，不能据此证明事件都属于 main。"普通网页会话"和"来源没有提供该分类"是两回事。以后若有可靠的来源定义，再以新版本补充分类。
2. **内容块类型使用实际已见类型的白名单**：
   - `text` → `pkst/content@0.1`（原文，`text/plain;charset=utf-8`）；
   - `tool_use`、`tool_result`、`token_budget`、`injected_prompt_block`、`document` → `pkst/projection@0.1`（`profile=python-json-v1`）；
   - `thinking`，以及**任何不在白名单内的类型**（包括将来新出现的类型和非对象块）→ `pkst/opaque-block@0.1`，只留指纹（`handling=raw-only`）。未识别类型的计数写入该成员 activity 的 `coverage.unrecognised_block_types_opaque`，本次导出为 0。
   - 这样，将来如果导出中出现新的隐藏推理、图片或加密块，也不会绕过基础规则自动进入投影。
3. **跨导出时 occurrence CID 不变，需满足的准确条件**：原生身份**以及所有参与哈希的字段**都没有变化。具体来说：
   - 只是 JSON 数组位置变了：有原生 ID 的事件 CID 不变，只有 extraction-record 和 block-reference 会变；
   - 内容、时间、父 ID 或角色真正变化：**必须产生新版本**的 occurrence，不覆盖旧对象；
   - 记忆条目没有原生 ID，使用 locator 回退，**不承诺**跨导出稳定。
4. **记忆文件的时间含义**：`memory_files[].updated_at` 是该版本的**状态时间**，不同于消息 `created_at` 的创建时间，也不是写作时间。这句说明已写入相应 extraction-record 的 `role_basis`，供下游审计。`conversations_memory` 和 `project_memories` 没有来源时间，`event_time` 为 unknown。

## 3. 其余规则（与 0.1 提案相同）

- **消息**：
  - `native_id = message.uuid`，`locator = null`，`native_role = sender`；
  - actor：assistant 为 `ai`；human 为 `unknown`；content 只有 tool_result 块的 human 消息为 `tool`；
  - `event_time = created_at`（rfc3339，微秒，zone_known=true，unit=null）。
- **content 顺序**：
  1. `content[]`，按源顺序；
  2. `attachments[]`；
  3. `files[]`；
  4. 顶层 `text`：仅当它不等于 text 块的拼接时，才附一个 projection（`native_type=message.text`）。
- **项目**：
  - 每个项目一个 occurrence：`native_role=material:project`，content 为 `[description, prompt_template]`，原文；
  - 每个 doc 一个 occurrence：`native_role=material:project-doc`，content 为 `doc.content`，原文；
  - actor 和 process 均为 `unknown`，`native_parent_ids = null`。
- **记忆**：
  - locator 为 `{raw, coordinate:"json-pointer", pointer}`；
  - `native_role` 为 `derived-memory:conversations`、`derived-memory:project` 或 `derived-memory:file`；
  - actor 和 process 均为 `unknown`。
- **取证锚**：
  - extraction-record：`coordinate=json-pointer`，带 `pointer`，不写 start/end；
  - block-reference：`document_pointer` 加相对 `pointer`；
  - 二者都不被身份对象反向引用。
- **下载清单**：含有下载 URL，只记录哈希，不复制，不访问。
