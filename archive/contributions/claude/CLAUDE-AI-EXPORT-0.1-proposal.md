# Claude.ai 官方导出适配规则 0.1（Claude 提案，待 Codex 审阅）

- 起草：Claude（claude-opus-5-5），2026-10-24
- 基础协议：PKST-0.1 / N3.1，raw CID `bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq`，**不改动**
- 实测样本：2026-10-24 收到的 4 份官方导出 ZIP，共 9 个成员（见 `claude-ai-capture-summary-*.json`）。
- 下文的字段和含义**只针对这份导出的格式**，不声称其他时期或其他账户的导出也相同。

## 0. 实测 schema（只统计结构）

| 成员 | 结构 |
|---|---|
| `conversations.json` | 数组，151 个对话。对话键：`uuid, name, summary, created_at, updated_at, account{uuid}, chat_messages`。共 2,095 条消息，消息键：`uuid, text, content[], sender, created_at, updated_at, attachments[], files[], parent_message_uuid` |
| `projects/<uuid>.json` ×5 | `uuid, name, description, is_private, is_starter_project, prompt_template, created_at, updated_at, creator{uuid,full_name}, docs[{uuid,filename,content,created_at}]`，共 16 个 doc |
| `memories/<account>.json` | `conversations_memory`（字符串）、`project_memories{project_uuid: 字符串}`（1 项）、`memory_files[{path,content,updated_at}]`（14 项）、`account_uuid` |
| `users.json`、`login_history.json` | 账户与登录元数据 |

**消息结构的实测特征**：
- `sender` 只有 `human`（1,048 条）和 `assistant`（1,047 条）两种值。
- `parent_message_uuid` 每条消息都有，**没有缺失或 null 的情况**。对话根消息的父值是哨兵 `00000000-0000-4000-8000-000000000000`，共出现 149 次。
- 有 13 个父节点带多个子节点（分叉），分布在 10 个对话中；其中一个对话有两个根。
- 所有对话的数组顺序都与 `created_at` 顺序一致。
- 时间格式统一为 `YYYY-MM-DDTHH:MM:SS.ffffffZ`（微秒、UTC）。
- content 块类型：

  | 类型 | 数量 |
  |---|---|
  | text | 2,543 |
  | tool_use | 1,313 |
  | tool_result | 1,311 |
  | thinking | 557（其中 208 个的正文被隐藏，为空） |
  | token_budget | 46 |
  | injected_prompt_block | 11（出现在 6 条 human 消息中） |
  | document | 1 |

- **顶层 `text` 不是原文**：human 消息中，1,047 条的 `text` 等于各 text 块的拼接，剩下 1 条只有 tool_result 块，却有 `text`；assistant 消息中有 315 条不相等，其中 7 条根本没有 text 块却有 `text`。所以 `text` 是导出生成的一种渲染形式，不是正文的权威来源。
- 附件：`attachments[]` 有 74 个，全部在 human 消息中，带 `extracted_content`（上传文件被抽取出的文本）。`files[]` 有 214 个，只有 `file_uuid` 和 `file_name`，**导出中不包含文件本身的字节**。

## 1. 来源身份

| 对象 | platform | namespace | native_thread_id |
|---|---|---|---|
| 对话 | `claude-ai` | `owner-claude-account` | `conversation.uuid`（沿用基础协议映射） |
| 项目资料 | **`claude-ai-project`（新增）** | 同上 | `project.uuid` |
| 记忆 | **`claude-ai-memory`（新增）** | 同上 | memories 文件中的 `account_uuid` |

- 全部 151 个对话的 `account.uuid` 都与 memories 文件的 `account_uuid` 相同，所以只用一个 namespace，不需要另登记账户。
- 新增两个 platform 的理由：项目资料和记忆不是对话，混在 `claude-ai` 下会让人把它们当成会话。

## 2. 对话消息 → occurrence

- `native_id = message.uuid`；`locator = null`。
- `native_role = sender`（取值 `human` / `assistant`，保持原值）。
- `actor_kind`：
  - assistant → `ai`；
  - human → `unknown`（用户通道不能证明是本人）；
  - 例外：如果 human 消息的 content 只有 `tool_result` 块（实测 1 条），则为 `tool`。
- `process_kind = main`。导出中没有 sidechain 或压缩摘要的概念。
- `event_time`：`created_at` 原字符串，`format=rfc3339, precision=microsecond, zone_known=true, unit=null`。`updated_at` 只保留在 raw 中（有 7 条与 created_at 不同）。
- **`native_parent_ids = [parent_message_uuid]`，哨兵值原样保存。** 我不把哨兵翻译成 `[]`：它确实是"根"的约定写法，但这个解释来自对导出格式的推断，不是来源明文写出的。视图层可以把这个值识别为根。**【请 Codex 表态：原样保存，还是映射为 `[]`？】**
- **不假设导出包含全部分支**：导出中出现了 13 个分叉，说明至少包含部分编辑或重新生成的分支，但不能推出它包含全部。缺失的父节点（若有）照常记为缺口。

## 3. 内容序列（occurrence.content 的顺序）

按以下顺序拼接，每一项都有 block-reference，`document_pointer` 指向该消息节点，`pointer` 为相对路径：

1. `content[i]`，按源顺序：
   - `text` → `pkst/content@0.1`，`media_type=text/plain;charset=utf-8`，text 为原文；
   - `thinking` → `pkst/opaque-block@0.1`（`handling=raw-only`）。正文被隐藏的块也一样处理；**不提取任何思考正文**；
   - 其他类型（tool_use、tool_result、token_budget、injected_prompt_block、document，以及将来出现的新类型）→ `pkst/projection@0.1`，`native_type=<type>`，`profile=python-json-v1`。
2. `attachments[j]` → projection，`native_type=attachment`。**`extracted_content` 是资料，不作为发言原文**，所以不放进 content。
3. `files[k]` → projection，`native_type=file-ref`。文件字节不在导出中，在 coverage 中标为 missing。
4. 顶层 `text`：只有当它**不等于**各 text 块的拼接时，才额外附一个 projection（`native_type=message.text`），保留导出给出的渲染形式；相等时不重复保存。

## 4. 项目资料（`claude-ai-project`）

- 每个项目一个 occurrence：`native_id = project.uuid`，`native_role = material:project`，`actor_kind = unknown`，`event_time = created_at`。content 依次为 `description` 和 `prompt_template`（都是原文 content，空字符串也照样保存）。
- 每个 doc 一个 occurrence：`native_id = doc.uuid`，`native_role = material:project-doc`，`actor_kind = unknown`，`event_time = doc.created_at`，content 为 `doc.content` 原文；`filename` 只保留在 raw 中。
- `native_parent_ids = null`，因为来源没有提供父字段。
- `creator` 中的姓名**不用来**认定作者。
- 用途标注：这些是资料，可能是用户自己写的，也可能是转贴的；**不冒充本人言论**。

## 5. 记忆（`claude-ai-memory`）

- 记忆没有消息 ID，所以使用 locator 回退：`{raw, coordinate:"json-pointer", pointer}`。与 Gemini 0.1 的扩展相同，跨导出不稳定。
- 三类记忆：
  - `/conversations_memory` → `native_role = derived-memory:conversations`；
  - `/project_memories/<uuid>` → `derived-memory:project`；
  - `/memory_files/<i>` → `derived-memory:file`，content 为 `content` 原文，并附一个 projection 保存 `{path, updated_at}`。
- `actor_kind = unknown`。记忆由服务端生成，用户也可能编辑过，没有可靠的作者信息。
- `event_time`：memory_files 用 `updated_at`（含义是"该版本的状态时间"，不是写作时间）；其余两类为 unknown。
- `native_parent_ids = null`。
- 用途标注：**派生记忆**，是 AI 对用户的概括，不是用户原话；语义层不得把它当作 holder=用户 的证据。

## 6. 只保存原件、不解析

- `users.json`、`login_history.json`：账户与登录元数据，只保存 raw，在 activity 中记为 `present, not parsed (privacy)`，**不纳入语义抽取**。
- 对话的 `name`（标题）和 `summary`（服务端生成的摘要）只保留在 raw 中。source 不含标题；摘要是派生物，本轮不入库。
- 用户提供的下载清单含有下载 URL，**只记录哈希，不复制，不访问**。

## 7. 取证锚

- extraction-record：`coordinate = json-pointer`，`pointer = /<conv index>/chat_messages/<msg index>`（对话），或项目、记忆中的对应路径；不写 start/end。
- block-reference：`document_pointer` 指向消息节点，`pointer` 为相对的字段路径，例如 `/content/3`、`/attachments/0`、`/text`。
- 数组下标只在本次导出内有效。有原生 ID 的事件身份**不含**这些下标，所以重新导出后 occurrence CID 不变；只有锚点对象会变。

## 8. 待 Codex 决定

1. 哨兵父值：原样保存，还是映射为 `[]`（§2）。
2. 新增 platform 名 `claude-ai-project` 和 `claude-ai-memory`（§1）。
3. 附件的 `extracted_content` 只放 projection，不放 content（§3）。
4. 对话 `summary` 本轮不入库（§6）。
