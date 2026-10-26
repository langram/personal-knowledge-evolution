# REPORT-CLAUDE-AI-1：Claude.ai 官方导出的采集、适配与验证

> **勘误（2026-10-24，根据 PKST-N8）**：§3 中 source 的数量原写为"157"，这是构造时生成的数量，不是当前根可达的数量。已更正为"当前根可达 154 个"。勘误前本文件的 sha256 为 `6201e2f5…76bd`。只改了报告的口径，已验证的根 `bafyreifdtjyn…` 及其数据都没有变化，也不重算。历史父 snapshot 的闭包不计入当前覆盖。

- 执行方：Claude（claude-opus-5-5），Windows，2026-10-24
- 授权依据：PKST-N6（采集与适配）、PKST-N7 与 `protocol/CLAUDE-AI-EXPORT-REVIEW-0.1.md`（落实四项小修正后直接执行）。
- 范围：**只做证据层导入**。没有做任何语义抽取，没有访问下载 URL，没有上传。收件箱只读，只写 `contributions/claude/`。

## 1. 规则

| 文件 | raw CID | sha256 |
|---|---|---|
| `CLAUDE-AI-EXPORT-0.1-proposal.md`（原提案，字节保留） | `bafkreigsckhfiygngg7m7jukoh5qpylntirz2dpcdnkhplmg7l5qvelndu` | `d2128e54…916d1d` |
| **`CLAUDE-AI-EXPORT-0.1.1.md`（执行规则）** | `bafkreie4n5ipntuteqllr4fmmitrxmhpqkwycz3n6kdbcak3laxjdkcsu4` | `9c6f50f6…52a7` |

0.1.1 版落实了 Codex 接受的四个决策，以及审阅中提出的四项修正：
- `process_kind=unknown`；
- 内容块类型用白名单，未识别类型一律 opaque、只留原件；
- 跨导出 CID 只有在全部参与哈希的字段都不变时才不变；
- 记忆的 `updated_at` 是版本状态时间，已写入 role_basis。

两份规则文件的原始字节都存入了 `raw/`，snapshot 和 activity 中链接的是它们的 raw CID。

## 2. 原件采集

- 脚本：`capture_claude_ai.py`（sha256 `7df14999…2473`）
- 摘要：`claude-ai-capture-summary-20261024T081127Z.json`
- 清单：`raw/_claude-ai-capture-20261024T081127Z.jsonl`（sha256 `7332c480…3e81`）
- 4 个 ZIP 的 sha256 与 `receipt.json` **全部一致**；`zipfile.testzip` 的 CRC 检查全部通过；读取前后文件大小和 mtime 都没有变化。
- ZIP 本身和 9 个成员的原始字节都已存为 `raw/<CID>.bin`。下载清单含有下载 URL，**只记录了哈希，没有复制，也没有访问**。

| ZIP | raw CID | 字节 |
|---|---|---|
| conversations-000.zip | `bafkreifkysa2y3isr2hbnpzp7tlctgvpziw2ictq5ljr6uffqf4h434hs4` | 10,133,493 |
| projects-000.zip | `bafkreid3n5sv37j57ho67lkogtcdayj7hmowzih6r64p43wne2s5y42nae` | 233,686 |
| memories-000.zip | `bafkreiblpepc7o4hzpu4esrgz7wtvmnmd7lfo7co2gn5ixcofvvhtdkqdy` | 13,161 |
| light_metadata-000.zip | `bafkreicnlktfi5ul2lwy3iyowp5vg2kdxy4qa4r733hra7cfiddcvaz3t4` | 1,939 |

| 成员 | raw CID | 字节 |
|---|---|---|
| conversations.json | `bafkreiayojn3wfjj4rptulrs335f3ry6ph5t7lxr54irnxnmcvqmd4cify` | 50,381,588 |
| projects/1559ef91-….json | `bafkreihoglcaysa4ut6q5toneialpxy5nrsu5hw7ovg2q6ostswdk3x7yu` | 19,414 |
| projects/019eaff1-….json | `bafkreieqdefyceikbm4ahvehjfkshvwes36svb6xd6meeji5265e7hpkpq` | 559,342 |
| projects/01a08106-….json | `bafkreidzwoxkllm2l4xub7264llu374vuwmzwqe742jr57mrpr426dcvou` | 428 |
| projects/01a0c44f-….json | `bafkreic2dbpilishzduw5jsmvuwlv6fjr56wpyjoi2gw4kglexvk3rtw7y` | 255,018 |
| projects/01a0c4f9-….json | `bafkreibauhbavejt3tvjlksn2phb7lwhc5mmpuajq6xh5edv3ehkeiwrgu` | 416 |
| memories/dbe6ce19-….json | `bafkreiavgdin3pc2sgnbzny5q4cte44ystxcewxtk5q4vfuiyr6nztlyye` | 39,591 |
| users.json | `bafkreigrlljcrio3svstiqzpqsa73vtsqxlpm5mtsohgii2ipetxqvykrm` | 154 |
| login_history.json | `bafkreibtrzjuhiuxc57ieqrgvixxxvicrx67dmzp3lpi7z2degh4c6k7da` | 19,841 |

## 3. 转换结果（规则 0.1.1）

- 脚本：`convert_claude_ai.py`（sha256 `01e9ede7…2923`）
- 摘要：`claude-ai-conversion-summary-20261024T081738Z.json`
- **根 snapshot：`bafyreifdtjynqzwqsnkq2obupxpum4oma752q4j4i44usbdrkutym7zkem`**
  - parent 为按 0.1 提案规则生成的 `bafyreie263a34ortmn7y6xcnxxx6kypr3fuwmdoz7cgsdgwxiz35gl3mve`（被取代，但保留）；
  - `protocol` 链接 `bafkreids4w2s…44fq`。
- **CAR：`contributions/claude/.private/claude-ai-evidence-0.1.1.car`**（sha256 `efad43bc4156711d7dbb738da6bba54ba74918b23b1a2bc79253cd5190b00f74`）。
  - 共 27,727 个块，包含根的成员和父 snapshot 的闭包；raw 在外部的 `contributions/claude/raw/` 中。
  - 0.1 版的 CAR `claude-ai-evidence.car` 也保留着。

根 snapshot 的成员（17,099 个块，另加根本身）：

| schema | 数量 |
|---|---|
| source | **当前根可达 154 个**（对话 148、项目 5、记忆 1）。构造时共生成 157 个，其中 3 个空对话的 source 对象没有放进 activity.outputs，因此不在当前根的闭包内；这 3 个空对话的头信息仍保留在 raw 中，它们的 source 对象也作为独立对象留在 `objects/` 中 |
| occurrence | 2,132（消息 2,095，其中 human 1,048、assistant 1,047；项目 5；项目 doc 16；记忆 16） |
| content | 2,425 个不同的对象（被引用 2,585 次） |
| projection | 3,244 个不同的对象（被引用 3,300 次） |
| opaque-block | 557（全部为 thinking） |
| extraction-record | 2,132 |
| block-reference | 6,442 |
| activity | 13（9 个成员和 4 个 ZIP 各一个） |

| native_role / actor / process | 条数 |
|---|---|
| human / unknown / unknown | 1,047 |
| human / tool / unknown（content 只有 tool_result） | 1 |
| assistant / ai / unknown | 1,047 |
| material:project / unknown / unknown | 5 |
| material:project-doc / unknown / unknown | 16 |
| derived-memory:conversations / project / file | 1 / 1 / 14 |

## 4. 验证

| 检查 | 脚本 → 结果文件 | 结果 |
|---|---|---|
| CAR 闭包 | `verify_car_claude.py` → `crosscheck-claude-ai-car-0.1.1.json` | 27,727 个块全部重算一致；0 个悬空；16 个外部 raw 全部存在并重算一致 |
| **完整锚验证** | `verify_claude_ai_anchors.py`（sha256 `7539f80a…aa81`）→ `claude-ai-anchor-verification-0.1.1.json` | **通过，0 个问题**。只校验根 snapshot 自己的成员，不含父 snapshot |

完整锚验证的逐项内容（与转换脚本是两套独立的代码）：
- 2,132 个 extraction-record 和 6,442 个 block-reference，全部用自写的 RFC 6901 解析器在原件上解析成功。
- 2,095 条消息：
  - uuid、sender、父 ID（含哨兵）、`event_time`（微秒，rfc3339）全部与原件一致；
  - actor 规则正确，`process_kind` 全部为 unknown；
  - **content 序列从原件独立重新推导，逐项比较**：text 原文相同；白名单类型的 projection 文本相同；thinking 的 opaque 指纹等于独立计算的 sha256；附件、文件引用、`message.text` 的有条件附加都与规则一致。
- 项目和 doc 的原文逐字相同。
- 16 条记忆的 locator 与锚点一致，原文相同；memory_files 的 `event_time` 等于 `updated_at`，role_basis 中写有"version-state time"；其余两类时间为 unknown。
- **覆盖**：导出中的消息 2,095 条全部锚定，doc 16/16，记忆 16/16；每个 occurrence 都有 extraction-record。
- **对话树**：149 个哨兵根；13 个分叉点；除哨兵外，没有父 ID 指向本对话以外的消息。

## 5. 覆盖与缺口

- **覆盖范围仅限这一份官方导出**：账户 `owner-claude-account`，151 个对话，消息时间从 `2024-10-24T10:09:13.964072Z` 到 `2026-10-23T05:09:19.258587Z`。
- **缺口**：

  | 缺口 | 说明 |
  |---|---|
  | 文件字节 | 214 个 `files[]` 引用**没有文件字节**（missing-bytes） |
  | 空对话 | 3 个对话没有消息 |
  | 分支 | 导出包含部分分叉（13 处），但**是否包含全部分支未知** |
  | 删除或未导出的对话 | 未知 |
  | 思考正文 | 557 个 thinking 块只留指纹（其中 208 个在导出中本来就没有正文），不提取 |
  | 仅存 raw、不解析 | 对话标题和摘要、`users.json`、`login_history.json` |
  | claude.ai/code 云端会话 | 这份导出中**没有识别到**。是否另有导出途径未知 |

- **用途标注**：
  - human 消息的作者一律为 unknown；
  - 项目文本是资料；记忆是 AI 生成的派生概括；
  - 附件的 `extracted_content` 只在 projection 中；
  - 以上都**不是用户立场的证据**。

## 6. 注意事项（供复算）

1. **有一次中断的运行留下了孤立对象**：0.1.1 第一次运行在写 CAR 时出错（父 snapshot 不在内存中，已修复），但出错前已经写出了全部对象。所以 `objects/` 中多了一组 recorded_at 不同的 13 个 activity 和 1 个 snapshot，**它们不被任何根引用**。由于对象只追加，我没有删除它们。其余对象内容是确定性的，与正式运行完全相同。
2. 白名单之外的块类型：本次为 0 个（见 conversations 成员 activity 的 `coverage.unrecognised_block_types_opaque`）。
3. 复算步骤：
   - 读取 CAR，从根出发；
   - raw 从 `contributions/claude/raw/<CID>.bin` 读取；
   - 投影使用 `python-json-v1`（运行环境为 Python 3.14.5）。
   - 我这边的独立校验脚本都只依赖 Python 标准库，可以直接运行。
