# PKST FILE-TEXT 0.1：独立文本原件适配规则（正式版）

- 依据：`protocol/FILE-TEXT-0.1-draft.md`（Codex 提案），经 Claude 独立审阅后接受，2026-10-24。
- 不修改已冻结的 PKST 0.1 / N3.1（raw CID `bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq`），也不扩展核心时间单位。
- 本文取代我在 `MAC-SUPPLEMENT-0.1-rules.md` §2 中的提案：那份提案用 mtime 作 event_time，并需要扩展 `ns` 单位，**均撤回**。

## 适用范围

只适用于 Mac Claude 补充包中 16 份 Claude Code 自动记忆 Markdown。即 `raw/_mac-supplement-capture-20261024T083850Z.jsonl` 中 `category = claude-code-project-memory` 的成员。

它们是程序生成的记忆文件，**不是用户的原生发言，也不是用户已采纳的观点**，不计入对话消息。

## 规则

1. **坐标 `file-bytes`**：
   - 原始 raw 字节上的半开区间 `[start, end)`；整个文件为 `[0, 原件字节数)`。
   - locator 和 extraction-record 使用同一个 raw、coordinate、start、end。
   - 必须检查：start 和 end 都是整数，`0 ≤ start ≤ end ≤ 原件字节数`。
2. **文本**：
   - 只接受严格 UTF-8 解码（不使用 `utf-8-sig`，所以 BOM 会保留为 U+FEFF）。
   - 逐字符保存，包括 BOM、CRLF 和尾部换行；不去空白，不做 Unicode 规范化。
   - 无法严格解码时只保留 raw，并在 activity 中报告，**不输出 occurrence**。
3. **来源**：`platform = claude-code-memory`，`namespace = owner-claude-account`，`native_thread_id = raw:<该文件的 raw CID>`。
   - 这是明确的"采集版本"fallback，文件一被编辑身份就会变，**不宣称跨编辑稳定**。
   - 文件路径只写在 activity 的 provenance 和 extraction-record 的 role_basis 中，不作为全局身份。
   - 如果两个路径的字节完全相同，它们共享同一个 raw、source 和 occurrence，但各自保留一个 activity，记录各自的路径。本次实测没有这种情况，见验证报告。
4. **occurrence**：
   - `native_id = null`；`locator = {raw, coordinate:"file-bytes", start:0, end:size}`；
   - `native_role = derived-memory:claude-code`；`actor_kind = unknown`；`process_kind = unknown`；`native_parent_ids = null`；
   - `content = [pkst/content@0.1]`，`media_type = text/plain;charset=utf-8`，为原文。
   - 文件内的指令只是资料，不执行。
5. **时间完全未知**：`event_time = {value:null, format:unknown, precision:unknown, zone_known:false, unit:null}`。
   - 文件 mtime 不是写作时间或发言时间。
   - Mac 的 `mtime_ns`（精确的十进制字符串）只保存在 `activity.coverage.mac_mtime_ns` 中。
6. **extraction-record**：
   - `coordinate = file-bytes`，带 start 和 end；`parser = file-text@0.1`；
   - `role_basis` 写明：来自补充清单的自动记忆目录、归档路径，以及本规则文件的 raw CID。
7. **不自动采纳**：自动记忆可以作为后续的来源线索。若要从中提取思想、关系或用户归属，必须另建有证据的语义对象或 assessment。

## 验收

- 16 个原件集合与补充包清单一致；
- raw 的 SHA 和 CID 一致；
- 文本是逐字的严格 UTF-8 解码结果；
- 半开边界正确；
- 用合成样例覆盖 CRLF、BOM、中文，以及无效 UTF-8 被拒绝；
- 所有事件的时间都是 unknown；
- 用户归属为零（没有 actor=human，也没有任何语义对象）。

## 对草案的审阅意见（不阻塞）

1. 草案没有点名 block-reference。每份文件只有一个 content，整个文件就是这一个块，extraction-record 已经足够锚定，所以**本实现不生成 block-reference**。
2. `native_thread_id = raw:<CID>` 让每个文件版本各自成为一个线程。各项目的 `MEMORY.md` 索引和它的条目文件之间没有建立结构关系。若以后需要，应作为 `basis = source-structure` 的独立关系来添加（依据是目录结构），不写进身份。
