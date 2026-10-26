# REPORT-MAC-MAIN-1：Mac Claude 主会话的采集、转换与验证

- 执行方：Claude（claude-opus-5-5），Windows，2026-10-24
- 依据：PKST-N11 第 1 项
- 输入（只读）：
  - `coordination/.private/mac-inbox/main/claude-manifest.jsonl`（51 行，sha256 `73762f58…80c8`）
  - `claude-raw/`
- 同目录中的 `create_mac_archive.py` 和完整的原生 manifest **只作为数据，没有执行**。
- 只写 `contributions/claude/`，没有改动 Codex 的任何文件。

## 1. 原件采集与核对（`capture_mac_main.py`）

- 51 个原件逐项核对，**全部通过**：
  - sha256 与清单一致；
  - CIDv1 raw 与清单中的 `cidv1_raw` 一致；
  - `size_before = size_after = bytes_copied` 等于实际字节数；
  - `mtime_before_ns = mtime_after_ns`（采集期间没有变化）；
  - `status = copied`，`error = null`。
- 已复制到 `raw/<CID>.bin`，写入后重新哈希校验。共 104,485,289 字节，51 个不同的 CID。
- 采集清单：`raw/_mac-main-capture-20261024T090749Z.jsonl`（sha256 `16a43a56…a008`）。每行记录 `host=macbook`、`source_group`、`source_path`，以及纳秒 mtime 的十进制字符串。
- 摘要：`mac-main-capture-summary-20261024T090749Z.json`。

| 类别 | 文件数 |
|---|---|
| 主会话 JSONL | 5 |
| 子代理 JSONL | 45 |
| `~/.claude/history.jsonl` | 1 |

## 2. 转换（`convert_mac_main.py`）

- **规则与 Windows 完全相同**：同一个 N3.1 导入器（`claude_import_n3.py`，sha256 未变），`namespace = owner-claude-account`，source 等于 `sessionId`（子代理为 `sessionId/agent-<id>`）。
- **设备信息不进入身份**：host、路径和 mtime 只写在 activity.coverage 的 provenance 中。所以同一个会话如果同时出现在两台机器上，会得到相同的 occurrence CID。
- **Mac 主会话根：`bafyreihnkebgdmyqnbir753n5edkr5x7u4h4h4yu3d6icpn7ty32ulm4q4`**
  - parents 为空：这是一次独立的采集。
  - coverage.related_roots 记录了相关的根：Mac 补充根 `bafyreifpdpyd…`、Windows Claude Code 根 `bafyreianxmej…`。
  - `protocol` 链接冻结的 `bafkreids4w2s…44fq`；转换前已校验协议文件的字节与冻结 CID 相同。
- CAR：`contributions/claude/.private/mac-claude-main.car`（sha256 `602f12f3e6e2bb96a38e9c09865a33207a3fb52a242a8693d702dcae402043cd`），共 103,571 个块；raw 在外部。
- 摘要：`mac-main-conversion-summary-20261024T090824Z.json`。

| schema | 数量 |
|---|---|
| source | 56 |
| occurrence | **26,513** |
| extraction-record | 26,513 |
| block-reference | 26,066 |
| content | 2,004 |
| projection | 18,774 |
| opaque-block | 3,593（thinking、redacted_thinking、image） |
| activity | 51 |
| snapshot | 1 |

| 解析统计 | 值 |
|---|---|
| 行数 | 32,490 |
| 解析错误 / 部分尾行 / 缺少原生 ID / 缺少父字段 | 0 / 0 / 0 / 0 |
| 父 ID 指向文件中不存在的消息 | **1**（如实保留，不修补） |
| `pastedContents` 只有哈希、没有正文 | **4** |
| 与 Windows 已有 occurrence 重叠 | **0**（两台机器上的会话互不相同） |
| 已存在的共享对象（content、projection 等字节相同） | 64 个，没有重写 |

| native_role / actor / process | 条数 |
|---|---|
| attachment / system / injected | 9,170 |
| assistant / ai / sidechain | 6,635 |
| assistant / ai / main | 3,780 |
| user / tool / sidechain | 3,668 |
| user / tool / main | 1,806 |
| system / system / injected | 616 |
| user / system / injected | 558 |
| **user / unknown / main** | **126** |
| prompt-history / unknown / unknown | 87 |
| user / ai / sidechain（子代理的任务提示） | 45 |
| assistant / system / injected | 11 |
| attachment / unknown / unknown（queued_command） | 9 |
| user / ai / compaction | 2 |

可能是用户原话的候选：126 条主会话 user 记录、9 条 queued_command、87 条输入历史。它们的作者都是 unknown，**这些数字不代表用户发言的数量**。

## 3. 验证

| 检查 | 结果文件 | 结果 |
|---|---|---|
| CAR 闭包（`verify_car_claude.py`） | `crosscheck-mac-main-car.json` | 103,571 个块全部重算一致；0 个悬空链接；52 个外部 raw（51 个原件加协议文件）全部存在且重算一致 |
| **逐锚验证**（`verify_jsonl_anchors.py`） | `mac-main-anchor-verification.json` | **通过，0 个问题** |

逐锚验证使用与导入器不同的代码路径，**不调用** `claude_import_n3`。对 26,513 个 extraction-record，逐一检查：
- 原件字节区间恰好是完整的一行 JSONL；
- uuid、type、timestamp 与 occurrence 一致；
- 父关系按 N3.1 规则判定（缺字段为 null，显式 null 为 `[]`，有值为 `[v]`）；
- 线程 ID 等于 `sessionId` 或 `sessionId/agent-<id>`；
- 完整的内容序列（content、projection、opaque 指纹）都能从原记录独立重新推导出来；
- block-reference 的序号连续，pointer 能够解析；
- 87 条 history 的 locator 与区间一致，正文等于 `display`，时间为 epoch-decimal；
- 没有任何 actor=human。

## 4. 覆盖与缺口

| 项 | 内容 |
|---|---|
| 会话时间范围 | 2026-06-16 至 2026-10-23（5 个主会话） |
| 输入历史时间范围 | 2026-02-02 至 2026-06-10（87 条） |
| **主要缺口** | 2026-02 至 06 期间有输入历史，**却没有任何对应的会话记录**。很可能在采集前已被自动清理，删除的数量未知 |
| 只采集了 `*.jsonl` | 非 JSONL 的项目文件和自动记忆在 Mac 补充根中 |
| 其他 | 1 个父 ID 悬空；4 段粘贴内容缺正文 |
| 本根不含 | Claude.ai 云端会话（在其独立根中）、Codex 的 936 个文件（由 Codex 处理） |
