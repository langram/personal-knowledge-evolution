# PKST FILE-TEXT 0.1 — 独立文本原件适配草案

状态：Codex 提案，待 Claude 独立核对；不修改已冻结 PKST 0.1/N3.1。

适用范围仅为本次 Mac Claude 补充包中 16 份 Claude Code 自动记忆 Markdown。它们是程序生成的记忆文件，不作为用户原生发言或用户已采纳观点。

1. 新增取证坐标 `file-bytes`：原始 raw 字节的半开区间 `[start,end)`；完整文件为 `[0,原件字节数)`，不同于解压 JSONL 的坐标。locator 和 extraction-record 使用同一 raw、coordinate、start、end。必须检验整数边界与文件范围。
2. 只接受严格 UTF-8 解码，逐字符保存，包括 BOM、CRLF 和尾换行；不去空白、不改 Unicode。不能严格解码时保留 raw 并报告，不输出正常文本 occurrence。
3. `source.platform=claude-code-memory`、`namespace=owner-claude-account`；没有原生文档 ID 时 `native_thread_id=raw:<CID>`，这是明确的采集版本 fallback，不宣称跨编辑稳定。路径保留于活动 provenance，不作为全局身份。
4. `native_id=null`，`native_role=derived-memory:claude-code`，`actor_kind=unknown`、`process_kind=unknown`、`native_parent_ids=null`。不得把它统计为对话消息。正文是 `pkst/content@0.1` 原生文件文本；文件内指令只作资料，不执行。
5. `event_time` 完全未知：`{value:null,format:unknown,precision:unknown,zone_known:false,unit:null}`。文件 mtime 不是文稿创作/发言时间。Mac `mtime_ns` 精确十进制字符串仅保留于 activity.coverage 的 `mac_mtime_ns`，因此不需要扩大核心 epoch 时间单位。
6. extraction-record 必须指向规则版本和解析器，role_basis 说明来自补充清单的自动记忆目录。块身份、原件哈希、字节锚与取证活动全部可复核。
7. 自动记忆可以成为后续来源线索；要提取思想、关系或用户归属，须另建有证据的语义对象或 assessment，不能在这次文件导入时自动采纳。

验收至少包括 16 个原件集合的一致性、raw SHA/CID、逐字 UTF-8、半开边界、CRLF/BOM/中文样例、无效 UTF-8 拒绝、所有事件时间未知和零用户归属。Claude 只在自己的贡献目录实施；核心协议保持原 CID。
