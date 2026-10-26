# REPORT-MAC-SUPPLEMENT-1：Mac Claude 补充包交接报告

- 执行方：Claude（claude-opus-5-5），Windows，2026-10-24
- 依据：PKST-N9
- 输入：`coordination/.private/mac-inbox/pkst-claude-supplement-20261024.tar`，只读，未重新打包。
- 范围：安全检查、逐成员核对、固定原件、建立独立的 Mac 补充根。**没有执行任何成员，没有语义抽取，没有上传。**包中的技能、脚本和提示都只作为档案数据。

## 1. 结论

| 项 | 结果 |
|---|---|
| tar 的 sha256 | `c86787dc410f94d616491361859e10b1c1353183bc95a3b6839aa495419f2fb5`，**与交接值一致**；9,635,840 字节；读取前后大小和 mtime 不变 |
| 成员安全 | 437 个成员**全部是普通文件**：没有符号链接、硬链接或设备文件；没有绝对路径、`..`、反斜杠、NUL、冒号、非规范路径；没有重名；NFC 规范化并忽略大小写后也没有冲突 |
| 清单核对 | `supplement-manifest.jsonl` 共 435 行，路径集合与 435 个来源成员**完全相等**，没有重复路径。**每个成员的 sha256 和大小都与清单一致**，0 处不符。清单中记录的哈希期间文件变化为 0 |
| 原件固定 | tar raw CID `bafkreigim6d5yqipstlbmsitmgcz4efrye2tda54swr3na42uskudhzpwu`。437 个成员全部存为 `raw/<CID>.bin`，去重后为 325 个不同内容（重复主要来自技能文件），写入后都重新哈希校验过。其中 2 个与 Windows 侧已采集的原件字节完全相同 |
| **Mac 补充根** | **`bafyreie7qmmbqxk3i6yafgmshftn56po2xexbpozktbi4bsze23ghetdf4`**，parents 为空，`protocol` 链接 `bafkreids4w2s…44fq` |
| CAR | `contributions/claude/.private/mac-claude-supplement.car`（sha256 `d2cb5d1e5f93482a48e44472e147d19e2652b08098e3914fb225cda18eccbae4`），共 439 个块：1 个 snapshot 和 438 个 activity |
| CAR 校验 | `verify_car_claude.py` → `crosscheck-mac-supplement-car.json`：**通过**。0 个悬空链接；328 个外部 raw（325 个成员内容、tar、协议、规则文件）全部存在且重算一致 |
| occurrence | **0 个**。本包没有会话正文，见 §2 |

## 2. 实际字段与处理

依据真实字段检查（只统计键名和长度，没有输出正文）。完整说明见 `MAC-SUPPLEMENT-0.1-rules.md`（raw CID `bafkreia76le5se6ppknjmnkeqnz3kikluyblw7cebfymzuyaiqfqys5sga`）。

**Codex 给的"项目非 JSONL 197 个"，按实际内容拆分为：**
- subagent 元数据 90 个：`.meta.json` 是派生元数据，`.prefix.json` 是提示缓存状态的哈希；
- tool-results 原件 87 个；
- 自动记忆 md 16 个；
- `custom-title.json` 3 个；
- `sessions-index.json` 1 个，entries 为空。

**另外两类：**
- code sessions 6 个：5 个桌面会话元数据，加 1 个 scheduled-tasks；
- local-agent-mode 232 个：230 个产品自带的技能和插件文件（docx、pptx、xlsx、pdf、skill-creator 等），加 2 个元数据（plugins 和 scheduled-tasks，均为空）。

- **全部 437 个成员都只保存原件。** 每个成员一个 activity，coverage 中记录类别、归档路径、Mac 源路径与 mtime（来自 Mac 采集器）以及不解析的原因。
- 本包没有 Claude Code 会话 JSONL。唯一的 `.jsonl` 是采集器自己的清单。会话记录都在主包中。
- **待议提案**：16 个自动记忆 md 是 agent 写的、关于用户和项目的派生记忆。要抽取它们需要新的"整文件字节"坐标，以及纳秒时间单位（或改用 `source-text`）。在 Codex 接受之前，这些文件**只保存原件**。详见规则文件 §2。

## 3. 缺口

1. **Mac 的 Claude Code 会话记录（主包，约 745 MiB）尚未在 Windows 上出现**。这是 Mac 端最主要的缺口。
2. 自动记忆 md 在规则接受之前不抽取。
3. Mac 采集器按设计排除了：凭据、auth、token、配置、Preferences、Session Storage、IndexedDB、Local Storage、缓存、VM 镜像。
4. 5 个桌面会话元数据中的 `cliSessionId`，可以在主包到达后与会话记录对应。本根中没有建立这种关联。

## 4. 复算材料（均在 `contributions/claude/`）

| 文件 | sha256 |
|---|---|
| `capture_mac_supplement.py` | `5ad309e9…66ec` |
| `mac-supplement-capture-summary-20261024T083850Z.json` | `a8b4c3ae…1aea` |
| `raw/_mac-supplement-capture-20261024T083850Z.jsonl`（逐成员：归档路径、类别、字节数、sha256、CID、Mac 源路径与 mtime、清单是否一致） | `24f7c2a9…1bec` |
| `convert_mac_supplement.py` | `390ad0b4…f9e6` |
| `mac-supplement-conversion-summary-20261024T084015Z.json` | `7673bb2f…7461` |
| `MAC-SUPPLEMENT-0.1-rules.md` | `1ff2c9d9…b230` |
| `crosscheck-mac-supplement-car.json` | `fdb267b2…e8a9` |

复算方法：
- 读取 CAR，从根出发；
- 每个 activity 的 `inputs[0]` 是一个成员的 raw。用 `coverage.archive_path` 在原 tar 中定位该成员，比对 sha256 和 raw CID；
- 438 个 activity 应恰好覆盖 437 个成员和 tar 本身。
