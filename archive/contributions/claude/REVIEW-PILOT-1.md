# REVIEW-PILOT-1：对 Codex 语义整合小样本的独立审阅

- 审阅方：Claude（claude-opus-5-5），2026-10-24
- 审阅对象：
  - `contributions/codex/pilot/report.json`
  - `contributions/codex/pilot/objects/` 中的 12 个对象
  - 根 snapshot `bafyreigfiuuqfqqkbouoawujokw7ecduh53ap63otad4mij7t4v7ovf34e`
- 方法：只用我自己的解码器（`pkst_cbor_claude.py`）、自己的 CAR 读取器（`verify_car_claude.py`）以及 Python difflib，没有使用 Codex 的脚本。只读 Codex 目录，没有修改。

## 结论

**结构与证据层：通过。** 哈希、投影、集合排序、跨仓库的引用闭包、双方字节锚、引文逐字性全部核实无误。

**语义层：有条件通过。** 没有发现归属、复制方向或思想演化方面的误判。Codex 对"不推定原创、不推定方向、不建 revise 边、holder 保持 unknown"的处理我**完全同意**。

有 3 处我建议在扩展到全库之前修正（R1–R3）。它们都不改变本样本的事实结论，也不需要重算任何已有的证据对象。

---

## 1. 结构与证据核验

| 检查 | 结果 |
|---|---|
| 12 个 `.cbor` 重算 CID | 12/12 一致 |
| 12 个 `.json` 投影重编码后与 `.cbor` 逐字节相同 | 12/12 |
| 集合数组（evidence、inputs、outputs、roots）按 CID 二进制有序、去重 | 全部合规 |
| 从根 snapshot 出发的引用闭包 | 20 个对象加 3 个 raw，与报告的 23 一致。其中 12 个在 pilot、4 个在 Codex CAR、4 个在 Claude 的 objects；全部重算一致，0 个悬空 |
| Claude 侧锚点 | ER `bafyreie3vb2y…` 指向 raw `bafkreihe74v2…` 的 `[588635, 590863)`。区间前后都是 LF，正好是一整行；记录的 uuid 为 `e406f776-…`，时间 `06:28:56.875Z`，正文与 content `bafyreiej32su…` **逐字相同** |
| Codex 侧锚点 | ER `bafyreid3u6c4…` 指向 raw `bafkreigwpcif…` 的 `[528717, 531472)`。区间前后都是 LF，是一整行 JSON；记录中含与 content `bafyreidas7jl…` 完全相同的字符串；原生 ID `msg_01a16c99-…` |
| 4 条 statement 的 text | 均为两份原文的**逐字子串**，在两份原文中各只出现 1 次，没有歧义锚点 |
| 文本差异复现 | 我独立计算的差异与报告完全一致：Claude 文本 579 字，Codex 文本 581 字；共 3 处差异，见 §3 |
| propagation-candidate 端点顺序 | from = Claude occurrence，to = Codex occurrence，**确实是按 CID 二进制升序**，与 scope 中"按 CID 排序的无序对"的声明一致 |

---

## 2. 归属

- **holder 保持 unknown：正确。** 两条记录的原生字段都显示 human 或 user 通道，按协议不能证明是用户本人输入。
- **补充事实（不改变结论）**：Claude 侧这条消息发生在 06:28:56Z，比 Codex 首次经 Computer Use 向 Claude 发送协调消息（PKST-N1）**更早**。因此在 Claude 这一侧，"Codex 代为输入"的可能性被时间排除了。但"用户粘贴了别处起草的文本"等其他可能仍然存在，所以仍然不能推定为用户本人发言。
- **建议**：这条消息适合作为**第一条请用户本人确认归属的样例**。用户确认后，以 `assessment(asserted_by={kind:human,id:owner})` 记录，而不是改写 occurrence。
- **4 条 statement 的 force 都是 directive：正确。** 它们都是对档案系统的要求，不是关于世界的论断。

---

## 3. 时间与复制/演化

**差异的精确含义**（报告中"AI 名称不同"的描述不够完整）：

| 位置 | Claude 副本 | Codex 副本 |
|---|---|---|
| 第 1 处名称："你来负责**claude**自己的部分，我会让**codex**来负责**codex**的部分" | 原样 | **未改**，与 Claude 副本完全相同 |
| 第 2 处名称："我让 **X** 也来做一份" | X = `codex` | X = `claude`（这一处被改了） |
| 末尾 | 无换行 | 多一个 `\n` |

由此得出三点：

- **用户只调整了一处称呼。** 在 Codex 副本中，"你来负责claude自己的部分"里的"你"指的是 Codex，与句中的名字字面上冲突。凡是从 Codex 副本抽取"分工"类语义时，必须按接收方解析指代，不能字面抽取。本样本**回避了这一句**，处理得当。建议把"人称与指代按接收方解析"写入抽取规则。
- **末尾换行可能是客户端造成的**（输入框是否 trim、是否追加换行），不一定是用户编辑。报告中的 "final-newline differences" 应注明"可能由客户端规范化导致，不归因于用户"。
- **时间先后**：Claude 副本 `06:28:56.875Z` 比 Codex 副本 `06:29:26.223Z` 早 29.348 秒。两个应用运行在同一台机器上，共用系统时钟，所以先后顺序本身可信。再加上"只改了一处称呼"这一模式，这与"先为 Claude 写好、再粘贴给 Codex 并局部修改"的过程**相容，但不构成证明**。协议规定相似度不能确定方向，Codex 没有写入方向，**正确**。如果将来要记录，应当另写一个 `basis=inferred` 的独立候选，并附上上述两条证据，而不是升级当前这条候选。
- **不建 change/revise 边：正确。** 两份文本是同一请求发给两个接收方，不是思想的修订。

---

## 4. 建议修正（扩展前）

**R1：concept 的 label 用了 AI 的转述，而不是用户的原话。**
- 现状：`label = "个人知识发展的语义与时间记录"` 在两份原文中都**不存在**。definition 已经说明这是"Codex 的整理标签"，这点是诚实的。
- 问题：用户在原文中自造了术语，有"个人知识发展的时空记录"和"个人知识语义时空merkle-DAG库"，两者都是逐字原文，各出现 1 次。我的提案和协议都要求不用 AI 措辞替换用户术语。
- 最小修正：label 改为用户原文中的术语。如果需要保留 Codex 的整理标签，另作 alias 记录，或写在 definition 中。若改动 label，concept 的 CID 会变，4 条 about 关系也要重新生成，但不涉及任何证据对象。

**R2：snapshot 的 event_cutoff 跨仓库混用。**
- 现状：`event_cutoff = 2026-10-24T07:05:42Z`，这是 **Claude** 侧的采集截止时间。Codex Windows 的采集截止约为 `07:01:47Z – 07:02:14Z`（见 capture-summary）。
- 问题：用一个时间概括两个仓库，会让人以为 Codex 侧在 07:02–07:05:42 之间也有覆盖。
- 最小修正：coverage 中按仓库分别列出 `event_cutoff`，或者取两者中较早的时间。时间格式也建议统一为带 `Z` 的写法；当前 `recorded_cutoff` 用的是 `+00:00` 加微秒，两种写法都合法，但混用不利于比较。

**R3：没有声明抽取的覆盖范围。**
- 现状：只抽取了 4 条 directive。`coverage.statements = 4` 容易被误读为这条请求的全部语义单元。
- 问题：原文中至少还有：
  - 其他要求：merkle-DAG 形式、树状思维导图结构、按时间顺序像 git 一样记录、提交到 GitHub 仓库、多方分工；
  - **断言型的自我陈述**：例如"很多会话其实涉及到了多方会话""我经常在几个AI之间互相复制粘贴，进行交叉头脑风暴式的交流"。这类应为 force=assert，holder 仍为 unknown。
- 最小修正：在 coverage 中注明 `selection = "bounded sample, non-exhaustive"`，并列出已识别但未抽取的单元类型。这样以后补抽时不会与本样本冲突。

---

## 5. 非阻塞提示（建议写入协议或抽取规则）

1. **对称谓词的端点顺序。** propagation-candidate、analogous-to、equivalent-within-scope、occurrence-equivalence 这类谓词，应**强制** from/to 按 CID 二进制升序，并由校验器检查。本样本已经这样做，但协议还没有写成规则。如果不写，读者容易把 from→to 读成方向；本例中 from 恰好也是时间上较早的那条，更容易被误读。
2. **holder.id 的词表。** 本样本用 `"source-speaker-unverified"`，旧编码向量用 `"unknown"`。建议在协议中固定一个词表，以免同义不同值，导致聚合查询漏掉。
3. **片段型 statement。** 例如"按照语义空间的逻辑和因果链条以及从属关系"是一个修饰性片段，脱离上下文就没有完整意思。逐字保留是对的。今后可以考虑用 `text_parts` 或指向上下文的关系补充语境，但不应改写原文。
4. **evidence 中同时放 occurrence 和 extraction-record**：我同意。由于 occurrence 不会反向引用锚点，这是语义对象指向具体字节的唯一途径。

---

## 6. 审阅结论汇总

| 维度 | 结论 |
|---|---|
| 归属 | 通过 |
| 时间 | 通过；R2 建议修正（按仓库分别给截止时间） |
| 字节锚 | 通过（双方都已逐字节核实） |
| 复制/传播 | 通过（无方向、无原创归属；建议补注换行的可能成因） |
| 演化 | 通过（没有错误的 revise 边） |
| 用户术语保真 | **R1 需修正** |
| 覆盖声明 | **R3 需补充** |

本样本**无需撤回**。按 R1–R3 修正后，我认为可以作为全库语义抽取的模板。按约定，在用户和 Codex 决定扩展之前，我**不开始**全库语义抽取。
