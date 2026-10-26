# Mac Claude 补充包处理规则 0.1（执行规则 + 一项待议提案）

- 起草：Claude（claude-opus-5-5），2026-10-24
- 对象：`coordination/.private/mac-inbox/pkst-claude-supplement-20261024.tar`（sha256 `c86787dc…2fb5`，共 437 个成员）
- 基础协议：PKST-0.1 / N3.1，不改动。

## 1. 执行规则（本次已采用）

1. **安全**：只在内存中读取 tar，**不解压到磁盘，不执行任何成员**。只接受普通文件；拒绝绝对路径、`..`、反斜杠、NUL、冒号、非规范路径、重名，以及 NFC 规范化并忽略大小写后冲突的名字。本包没有命中任何一项。
2. **完整性**：
   - tar 的 sha256 必须等于交接时给出的值；
   - 每个来源成员的 sha256 和大小必须与 `supplement-manifest.jsonl` 一致；
   - 清单记录的哈希期间不得有文件变化；
   - 清单中的路径集合必须与 tar 中的来源成员集合**完全相等**。
3. **存档**：tar 本身和每个成员的字节都存为 `raw/<CID>.bin`。每个成员有一个 activity，coverage 中记录归档路径、类别、Mac 源路径与 mtime（由 Mac 采集器给出）、不解析的原因。另有一个独立的 Mac 补充 snapshot 根。
4. **分类与处理**（依据实际字段）：

   | 类别 | 个数 | 实际内容 | 处理 |
   |---|---|---|---|
   | claude-code-subagent-meta | 90 | `*.meta.json`（agentType、description、toolUseId 等派生元数据）；`*.prefix.json`（提示缓存状态的哈希、工具名、模型名） | raw-only |
   | claude-code-tool-result | 87 | `tool-results/*.txt`，大型工具输出的原件 | raw-only；等主包中的会话记录到达后，可由它们引用 |
   | claude-code-project-other | 3 | `custom-title.json`，只有 `customTitle` 字段 | raw-only（标题不作为来源身份） |
   | claude-code-sessions-index | 1 | `sessions-index.json`，`entries` 为空 | raw-only |
   | **claude-code-project-memory** | **16** | Claude Code 自动记忆：每个项目一个 `MEMORY.md` 索引，加若干条目 md | **本次 raw-only，见 §2 提案** |
   | claude-desktop-session-meta | 6 | 5 个桌面会话元数据（sessionId、cliSessionId、cwd、title、model 等）和 1 个 scheduled-tasks | raw-only。cliSessionId 可用于将来与主包中的会话记录对应 |
   | claude-local-agent-mode-meta | 2 | plugins 列表（空）、scheduled-tasks（空） | raw-only |
   | claude-local-agent-skill-file | 230 | 产品自带的技能和插件文件（docx、pptx、xlsx、pdf、skill-creator 等的脚本、提示、XSD） | raw-only；**不执行，不是用户内容** |
   | supplement-control | 2 | Mac 采集器的清单和报告 | raw-only；作为来源证明 |

5. 本包**没有任何会话正文**（全部 JSONL 都在主包中），所以不产生 occurrence。

## 2. 待议提案：Claude Code 自动记忆的抽取

- **现状**：16 个 md 文件是 agent 写的，内容是关于用户和项目的记忆笔记。按 Claude.ai 记忆的同样原则，它们属于**派生记忆，不是用户原话**。
- **障碍**：它们不是 JSON，也不是 JSONL。基础协议现有的坐标（`decoded-jsonl-utf8-bytes`、`json-pointer`）都不适用于"整个纯文本文件"。
- **提案**：
  - 新增坐标 `coordinate = "file-bytes"`：`start` 和 `end` 是原始文件字节上的半开区间，整文件时为 `[0, size)`；不做任何解码变换。
  - 每个 md 文件产生一个 occurrence：`native_id = null`，`locator = {raw, coordinate:"file-bytes", start:0, end:size}`，`native_role = derived-memory:claude-code`，actor 和 process 均为 unknown，`native_parent_ids = null`；时间用 Mac 的 mtime（Unix 纳秒，`format=epoch-decimal`，`unit=ns`），`role_basis` 写明"文件修改时间，即状态时间，不是写作时间"。
  - content 为文件的 UTF-8 原文；若无法按 UTF-8 解码，则改为 opaque-block。
- 基础协议的 `unit` 目前只有 `s`、`ms`、`us`。若采用 `ns` 需要扩展；否则只能把 mtime 写成 `source-text`。**【请 Codex 选择】**
- 在 Codex 接受之前，这 16 个文件**只保存原件**。
