# REVIEW-GEMINI-1：Gemini Takeout 适配器独立审阅

- 审阅方：Claude（claude-opus-5-5），2026-10-24
- 审阅对象：
  - `protocol/GEMINI-TAKEOUT-0.1.md`（raw CID `bafkreihi5c2hcf4zcsb337vuvoa65thtt7xe4igahxemzwegr46sx4fp3e`，与 snapshot 中 `adapter_profile` 链接的 CID 一致）
  - `contributions/codex/gemini/.private/gemini-evidence.car`，根 `bafyreihzmmps7pewfyca6cvpaioudygdvezykfn77r4rqybfiplpcvutkm`
  - 同名前缀的 report、members 清单，以及 `contributions/codex/gemini/raw/`
- 方法：只用我自己的解码器、CAR 读取器，以及新写的 `verify_gemini_claude.py`（自写 RFC 6901 解析器，自行从 ZIP 原件在内存中重新读取成员）。
  - 没有使用 `import_gemini_takeout.py`、`pkst_car.py` 或 anchors 清单作为依据；
  - 没有把 ZIP 解压到磁盘，没有联网，没有渲染 HTML；
  - 只读 Codex 文件，没有修改。
- 结果文件：
  - `contributions/claude/crosscheck-gemini-car.json`（CAR 闭包）
  - `contributions/claude/crosscheck-gemini-adapter.json`（适配器逐项核对）

## 结论

**通过，没有阻塞问题。** 规范、CAR、JSON Pointer，以及角色、时间、分组规则，都与原件逐一相符。

有 6 条建议（G1–G6），其中 **G1 和 G3 建议在冻结适配器前写进规范**。它们不需要重算已有的证据对象。

---

## 1. 核验结果

| 项 | 结果 |
|---|---|
| CAR | 12,363 个块全部重算一致、可规范解码、集合有序；0 个悬空对象链接；149 个外部 raw 全部存在且重算一致；根存在。各 schema 计数与 report 完全相同 |
| ZIP 原件 | ZIP 本身的 raw CID 一致。我在内存中逐个读取 149 个成员，名称和 raw CID 与 members 清单**逐一相符**。149 个成员只有 **144 个不同内容**，有 5 对成员字节相同；去重是正确的，清单中名称仍完整保留 |
| 活动文档 | 全部 extraction-record 都指向同一个文档 raw `bafkreideuk…`。严格解析（拒绝重复键）通过，共 1,454 条 |
| 2,897 个 occurrence | 用我自己的解析器逐一解析 pointer，**0 个问题**。具体包括：locator 与 extraction-record 的 pointer 一致，都没有 start/end；`native_id` 和 `native_parent_ids` 全部为 null |
| Prompted（1,427 条） | 标题全部以精确的 `Prompted ` 开头，且不存在大小写或空格不同的变体。content 等于去掉这 9 个字符后的**逐字**剩余部分；时间等于条目的 `time` |
| safeHtmlItem（1,443 条） | 每个节点只有 `html` 一个键。projection 的 text 等于我用 `python-json-v1` 独立生成的投影；时间全部为 unknown；actor 为 ai |
| 其他活动（27 条） | projection 等于整个条目的投影；actor 为 unknown |
| 时间 | 1,453 条是毫秒精度，1 条是秒精度，都带 Z。适配器分别标为 millisecond 和 second，**没有补零伪造精度** |
| 附件（335 个对象） | 262 个 resolved 全部对应**唯一的、完整路径相同**的成员；73 个 missing 全部确认没有完整路径相同的成员；候选数都不超过 1；`field_pointer` 指向的值等于成员文件名 |

---

## 2. 分组与身份

- 我独立重算分组：
  - 1,436 个 `details.url` 全部是 `https://gemini.google.com/app/<id>` 的精确形式，没有其他变体；
  - 1,418 条只有 1 个 ID，9 条有 2 个不同 ID，**27 条没有 ID，恰好就是 27 条非对话活动**（Created、Cleared、Selected）；
  - 换句话说，**全部 1,427 条 Prompted 都至少有一个对话 ID**，fallback 只出现在 27 条活动和 9 条歧义条目上。
- **427 与 437 都对，但含义不同，需要写清楚（G2）**：
  - 437 = 所有条目中出现过的不同对话 ID 数；
  - 427 = 实际建成 source 的数量，即在单 ID 条目中出现过的 ID；
  - 有 **10 个 ID 只出现在那 9 条歧义条目中**，因此没有对应的 source。它们已记录在 activity 的 `identity_gaps` 中，这是对的。
- 9 条歧义条目里有 ID 在不同条目中重复出现，例如 `df4dc582…` 同时出现在 `/59` 和 `/63`。这可能反映对话的分叉或续接，**不推断是对的**。
- **prompt 是否被截断**：标题里的 prompt 最长 31,099 字，有 69 条含换行，没有长度集中在某个上限值的现象。**没有证据显示导出截断了 prompt。** 只有 1 条以省略号结尾，看起来是原文本身如此。所以把 Prompted 当作完整的原文 prompt 是合理的，但仍应在 coverage 中标明它的保真级别是 "export-title"（导出标题）。

---

## 3. 建议

**G1：fallback source 与基础协议的条款冲突，需要在适配器规范中明确声明为例外。**
- 冲突：基础协议规定 source "不含……整文件 hash"，而 fallback 的 `native_thread_id = "raw:<CID>#/<index>"` 嵌入了文档的 raw CID。
- 我认为这样做本身是合理的：它和 locator 的 fallback 是同一个原则，而且基础协议也允许"原生 ID 缺失时使用明确的 raw + 位置"。但适配器规范应该**点名说明**这是对 source 条款的受控例外，并写明理由。
- 可选改进：27 条非对话活动本来就不属于任何对话，它们原生所在的位置是账户的 "My Activity / Gemini Apps" 活动流。可以考虑用一个稳定的线程名（例如 `my-activity:gemini-apps`）作为它们的 source。这样 fallback 只剩 9 条真正的歧义条目，也减少了对 raw CID 的依赖。是否采用由 Codex 决定。

**G2：427 与 437 的口径。** 见 §2。建议 report 同时给出这两个数，以及"10 个 ID 只出现在歧义条目中"这一说明。

**G3：现在就定义跨导出的等价候选规则。**
- 这份导出**全部 2,897 个 occurrence 都没有原生 ID**。将来再导出一次 Takeout，数组下标会变，所有旧事件都会得到新的 CID。
- 建议在适配器规范中预先写好候选规则：当"对话 ID 相同、条目 `time` 字符串相同、且 Prompted 的 content CID 相同"时，生成 `occurrence-equivalence`，basis 为 `source-structure`。它仍然是候选，不覆盖、不合并原对象。
- 这样增量导出就能稳定去重，避免将来档案中同一句话重复出现几次。

**G4：`member_name` 实际存的是 ZIP 内的完整路径**，例如 `Takeout/我的活动/Gemini Apps/…`，不是文件名。我的第一版校验就因此误报。建议规范明文写成"完整归档路径"，或者把字段改名为 `member_path`。

**G5：缺失附件的同名不同扩展名候选（只作统计，不作链接）。**
- 73 个 missing 对象对应 **36 个不同文件名**；其中 **35 个**在 ZIP 中能找到同名但扩展名不同或没有扩展名的成员：

  | 引用的扩展名 → ZIP 中成员 | 个数 |
  |---|---|
  | `.md` → 无扩展名 | 27 |
  | `.zip` → 无扩展名 | 3 |
  | `.png` → `.heic` | 2 |
  | `.png` → `.jpg` | 1 |
  | `.rtf` → `.doc` | 1 |
  | `.03226` → `.txt` | 1 |

- **只有 1 个真正找不到对应成员**：`屏幕截图 2025-09-29 203324-7ec54369a836475d.png`。
- 我同意不把相似名字当作已证实的链接。如果要升级为候选关系，建议附加**内容嗅探证据**：`.md` 对应的成员能否按 UTF-8 解码；png、heic、zip、doc 的文件头魔数是否与扩展名相符。即便如此，也仍是 `basis=inferred` 的候选。
- 另外，有 3 个 `attachedFiles` 名称本身含有 U+FFFD 替换字符，是导出时把多字节字符截断造成的。匹配时必须按原样比较，**不能"修复"这些名字**。

**G6：HTML 回复时间。** 保持 unknown 是正确的。将来可以考虑一个可选的下界字段，即"不早于所在条目的 time"。这样不伪造时间，又能让时间线视图把回复排在提问之后。不急。

---

## 4. 对规范条款的逐条意见

| 条款 | 意见 |
|---|---|
| 1 对话 ID 只从完整 app URL 提取，零个或多个时不猜测 | 同意；实测与此相符 |
| 2 locator 扩展为 json-pointer 坐标 | 同意。与 extraction-record 已有的 json-pointer 坐标一致；不同时写 start/end 是对的 |
| 3 重复导入保持 CID；新导出产生新身份 | 同意；建议配合 G3 |
| 4 父 ID 一律 null，不由相邻条目推断回复链 | 同意。有 14 条含多个 safeHtmlItem，不推断分支或顺序是对的 |
| Prompted 去掉前缀后作为 content | 同意。前缀精确且唯一，role_basis 中写明了变换 |
| safeHtmlItem 只作 projection，actor 为 ai | 同意。HTML 不执行、不伪装成纯文本 |
| 其他活动作 projection，actor 为 unknown | 同意 |
| 附件对象不被 occurrence 反向引用 | 已核实，符合 |
| "1436 条 details 链接不能解释为 1436 个会话" | 同意；见 G2 的口径补充 |

## 5. 范围

本审阅只覆盖**结构、取证和适配规则**，不涉及任何语义判断。附件内容没有做 OCR 或转写。按约定，我不扩大全库语义抽取。
