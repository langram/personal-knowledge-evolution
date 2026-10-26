# 个人知识语义时空 Merkle-DAG：架构与规则（Claude 提案 v0.1）

> 状态：**讨论稿**。供与 Codex 方案对照、讨论、合并为统一规范 v1.0。
> 起草：Claude（claude-opus-5-5），2026-10-24。
> 文中标 **【待议】** 的条目是我认为需要双方明确表态的决策点。

---

## 0. 一句话

把"我说过的每一句话"做成**不可变、内容寻址的证据层**，在其上抽取"我的每一个思想"作为**带版本谱系的思想节点**，
再用**可追溯、可撤回的关系断言**把它们连成语义拓扑；时间维度上，思想节点之间的继承边构成"思想的 git 历史"，
而 git 本身记录"这份知识库是何时、由哪个 AI、如何整理出来的"。

---

## 1. 设计原则

1. **证据与解释分离。** 原话（utterance）是事实，可以被确定性地重算哈希；思想节点和关系是 AI 的*解读*，可能出错，必须能被修正而不破坏证据。
2. **只追加，不修改，不删除。** 所有对象一旦写入即不可变。修订 = 新版本；否定 = 撤回对象（retraction）。
3. **内容寻址。** 每个对象的 ID = 其规范化内容的 SHA-256。同样的输入在任何机器、任何 AI 上得到同样的 ID。
4. **零可变状态 → 多方提交零冲突。** 仓库里没有"指针文件"之类需要原地更新的东西；每个对象独占一个以哈希命名的文件。Claude 和 Codex 并行提交永远不会产生 git 冲突。分支头、最新版本等全部由计算得出。
5. **双时间轴（bitemporal）。**
   - **思想时间（valid time）**：我在什么时候说了/想了这个 → 存在对象内部，构成思想演化 DAG。
   - **记录时间（transaction time）**：某个 AI 在什么时候把它整理入库 → 由 git 提交历史承担。
   两者绝不混用。2026 年才整理的 2019 年的想法，在思想时间线上仍属于 2019 年。
6. **归属诚实。** 明确区分"我原创的""和 AI 共同形成的""AI 提出、我采纳的""AI 提出、我没表态的"。这是*我的*思想库，不是 AI 输出的合集。
7. **一切可追溯到原话。** 任何思想节点、任何关系，都必须能点回至少一条原话证据。没有证据的东西不入库。
8. **视图是派生物。** 思维导图、时间线、图谱可视化都由对象重新生成，不作为权威数据，不手工编辑。

---

## 2. 分层模型

```
 L3  视图层   思维导图 · 时间线 · 单个思想的 "git log" · 图谱导出        （派生，可随时重建）
 ─────────────────────────────────────────────────────────────────────
 L2  关系层   relation / retraction   语义从属、逻辑、类比、整合……       （AI 解读，可撤回）
 L1  思想层   idea（版本化）            概念、命题、理论、问题……及其演化谱系 （AI 解读，不可变版本）
 ─────────────────────────────────────────────────────────────────────
 L0  证据层   source / utterance       会话与每条原话，含跨 AI 复制粘贴引用  （确定性，脚本生成）
     原始层   raw/                     原始导出文件                         （不进 git）
```

- L0 由**脚本**生成，不用大模型，结果必须可复现。
- L1、L2 由**大模型抽取**，每个对象都签名是哪个 agent / 哪个模型做的。
- 用户本人（`me`）也可以直接写 L1/L2 对象，且优先级最高（见 §7.4）。

---

## 3. 对象规范

### 3.1 通用规则

| 规则 | 内容 |
|---|---|
| 格式 | JSON，UTF-8 |
| 哈希 | `id = "sha256:" + hex(sha256(JCS(obj')))`，JCS = RFC 8785 JSON 规范化 |
| `obj'` 的构成 | 原对象去掉 `id` 字段，以及**所有以 `_` 开头的字段** |
| `_` 字段 | 不参与哈希的附注：`_text`（正文）、`_redacted`、`_note` 等。用于允许脱敏/补注而不改变 ID |
| 字符串规范化 | 全部 NFC；文本内 CRLF→LF；整段首尾空白去除，段内不动 |
| 时间 | ISO 8601 UTC，带 `Z`。精度不足时加 `at_precision`: `second`/`day`/`month`/`year` |
| 版本 | 每个对象有 `"v": 1`（规范版本）和 `"type"` |
| 存储路径 | `objects/<type>/<hex前2位>/<hex>.json`，文件内容为带缩进的可读 JSON（校验时重新规范化） |
| 引用 | 对象之间只用 `id` 互相引用 |

**【待议 A】** 是否改用 IPFS 的 CIDv1 + dag-json，以便将来直接放到 IPFS 上？我的倾向：v1 用 `sha256:hex` 保持简单，规范里保留一条确定性映射规则，需要时再一次性转换。

### 3.2 `source` —— 一个会话或一篇文档

```json
{
  "v": 1, "type": "source",
  "platform": "claude-code",            // 见下表
  "host": "win-main",                   // win-main | macbook | cloud
  "native_id": "a3a78eb5-2ed5-45fe-b959-872db8f44e58",
  "title": "Merkle-DAG在复杂动态系统中的应用",
  "started_at": "2026-10-17T03:12:44Z",
  "raw_sha256": "sha256:…",             // 原始文件哈希，可用于核验原始层
  "_raw_locator": "raw/claude-code/win-main/a3a78eb5….jsonl"
}
```

`platform` 取值（封闭集，新增需改规范）：
`claude-code` · `claude-desktop` · `claude-ai` · `codex-cli` · `codex-desktop` · `chatgpt` · `gemini` · `antigravity` · `doc`（我的文字作品）· `note`（随手笔记）

### 3.3 `utterance` —— 一条原话

```json
{
  "v": 1, "type": "utterance",
  "source": "sha256:<source id>",
  "seq": 17,                            // 会话内顺序号，从 0 起
  "native_id": "<平台原生消息 uuid>",
  "author": { "kind": "human", "id": "me" },      // 或 {"kind":"ai","id":"claude","model":"claude-opus-5-5"}
  "at": "2026-10-17T03:20:01Z",
  "reply_to": "sha256:<上一条 utterance id>",     // 会话首条为 null
  "text_sha256": "sha256:<原文哈希>",
  "quotes": [                            // 跨会话/跨 AI 的复制粘贴，见 §5
    { "utterance": "sha256:…", "span": [120, 860], "match": 0.97 }
  ],
  "_text": "原文……"
}
```

- `reply_to` 参与哈希 → 每个会话本身就是一条 Merkle 链，任何中间篡改都能被发现。
- 工具调用、系统提示、思考过程等**不作为 utterance 入库**（只保留人和 AI 的自然语言消息）。
- **【待议 B】** AI 的回复是否全文入库？我的倾向：入库全文（`_text`），因为"共同形成"的思想需要它作证据；但视图默认只显示我的原话。若体量过大，可只留 `text_sha256` 加摘要。

### 3.4 `idea` —— 思想节点（一个版本）

```json
{
  "v": 1, "type": "idea",
  "lineage": "sha256:<谱系创世版本 id>",   // 创世版本此字段为 null
  "kind": "claim",
  "title": "协作体的规则应可被分叉",
  "statement": "一句到三句话的规范化陈述，用我的口吻，尽量贴近原话。",
  "parents": [
    { "idea": "sha256:…", "rel": "revises" }
  ],
  "evidence": ["sha256:<utterance>", "sha256:<utterance>"],
  "origin": "self",
  "status": "active",
  "valid_at": "2026-10-17T03:20:01Z",     // = evidence 中最早的时间
  "extracted_by": { "agent": "claude", "model": "claude-opus-5-5" }
}
```

**谱系（lineage）≈ git 中的"一个文件的历史"**：
- 一个思想第一次出现时，创建**创世版本**（`lineage: null`）；它自己的 `id` 就成为该谱系的永久标识。
- 之后对同一思想的修订，`lineage` 指向创世版本，`parents` 指向前一版本（`rel: revises`）。
- 最新版本 = 谱系中没有被任何版本 `revises` 的那个（计算得出，无需指针）。
- 若一个谱系出现两个"最新"（多头）→ 说明有分歧未整合，`verify` 会报出，需要一个合并版本来收敛。

`kind`（封闭集）：

| kind | 含义 |
|---|---|
| `domain` | 领域（思维导图的顶层分支，如"协作理论""Merkle 计算"） |
| `theory` | 理论体系（由多个命题/概念组成） |
| `concept` | 概念/术语定义 |
| `claim` | 命题、论断（可以真或假） |
| `hypothesis` | 待验证的假说 |
| `question` | 开放问题 |
| `principle` | 原则、规范、价值主张 |
| `method` | 方法、机制、架构设计 |
| `analogy` | 隐喻、类比 |
| `project` | 落地的项目或实践 |

`origin`（归属，封闭集）：

| origin | 判定标准 |
|---|---|
| `self` | 我先提出，AI 只是回应 |
| `co` | 在多轮讨论中由我和 AI 共同形成，难以分清 |
| `adopted` | AI 先提出，我**明确**接受或之后自己复述使用 |
| `ai` | AI 提出、我未表态。**默认不入库**，除非它后来影响了我的某个思想（此时作为 `influenced-by` 的目标） |

`status`：`active` · `superseded`（被新谱系取代）· `abandoned`（我明确放弃）· `open`（仅用于 question，尚无答案）。
状态改变也是通过**新版本**表达，而不是修改旧对象。

### 3.5 思想演化边（写在 `idea.parents` 里，参与哈希）

| rel | 含义 | git 类比 |
|---|---|---|
| `revises` | 同一谱系内的修订、细化、改口 | 同一文件的新提交 |
| `derives` | 受另一思想启发产生的**新**思想（新谱系） | 从别处拷贝代码起新文件 |
| `forks` | 一个思想分化成两个不同方向（新谱系） | 开分支 |
| `merges` | 两个以上思想被我合成为一个 | 合并提交 |

这四种边构成**思想时间线**。它们是"思想本身的演化"，必须有原话证据（例如我说"我之前觉得 X，现在我认为 Y"）。

### 3.6 `relation` —— 语义关系断言（L2，独立对象）

```json
{
  "v": 1, "type": "relation",
  "rel": "part-of",
  "from": "sha256:<idea>",
  "to":   "sha256:<idea>",
  "evidence": ["sha256:<utterance>"],
  "asserted_by": { "agent": "claude", "model": "claude-opus-5-5" },
  "confidence": 0.8,
  "primary": true                       // 仅 part-of 用：思维导图里的主父节点
}
```

为什么关系不写在 idea 里：语义归属是事后理解出来的、会变的。如果写进 idea，每补一条关系就要改哈希，整条谱系都要重算。独立成对象后，增删关系不影响任何已有节点。

`rel`（封闭集 v1）：

| 类别 | rel | 方向读法 |
|---|---|---|
| 从属结构 | `part-of` | from 是 to 的组成部分（思维导图的树枝） |
| | `instance-of` | from 是 to 的一个实例 |
| | `specializes` | from 是 to 的特化 |
| 逻辑 | `supports` / `contradicts` | from 支持/反驳 to |
| | `depends-on` | from 以 to 为前提 |
| | `answers` | from 回答了问题 to |
| | `applies-to` | from（方法/理论）应用于 to |
| 联想 | `analogous-to` | 类比（对称） |
| 来源 | `influenced-by` | from（我的思想）受 to（AI 的 utterance 或别人的思想）影响 |
| | `restated-in` | from（idea）在 to（utterance）中被我再次提及但无变化 |
| 整理 | `same-as` | 两个 idea 指同一思想（多 AI 各自抽取导致的重复） |
| | `consolidates` | from 是对 to 的编辑性合并（见 §6），**不属于思想演化** |

关系指向**具体版本**而非谱系，并隐含"自该版本起成立"。视图可以沿谱系向后继承关系，直到被撤回或被新关系覆盖。

**【待议 C】** 关系是指向版本（精确、可追溯）还是指向谱系（稳定、简单）？我倾向版本，视图层做继承。

### 3.7 `retraction` —— 撤回

```json
{ "v": 1, "type": "retraction", "target": "sha256:<relation 或 idea>",
  "reason": "误判：两者并非从属关系", "asserted_by": { "agent": "me" } }
```

不删除任何东西；撤回后的对象在视图中隐藏，但历史可查。

---

## 4. 思维导图（空间）与时间线（时间）如何从同一份数据中得出

- **思维导图** = 所有未撤回的 `part-of`（主父 `primary: true`）关系构成的树，根为 `kind: domain` 节点。一个思想可以属于多个父节点（DAG），但导图只按主父展开，其余父节点作为交叉链接显示。
- **思想时间线** = 所有 idea 按 `valid_at` 排序，用 `revises/derives/forks/merges` 连线，形如 `git log --graph`。
- **单个思想的演化史** = 某个谱系所有版本及其 `derives/forks/merges` 上下游。
- **某一时刻的思想快照** = 只取 `valid_at ≤ T` 的版本与证据，可以"回放"任何时间点我当时的知识结构。这正是 Merkle-DAG 加时间维度带来的"时空"能力。

---

## 5. 跨 AI 复制粘贴：把多方会话缝成一张网

我经常把 A 的回答粘到 B 里。这是本库最有价值、也最难处理的部分。

**检测（脚本，确定性）：**
1. 所有 utterance 文本规范化（NFC、去 Markdown 标记、合并空白）。
2. 按字符做 shingle（中文 8 字、英文 5 词），哈希建索引。
3. 对每条**我发出的** utterance，查找与之大量重合（重合 ≥ 150 字符，或 Jaccard ≥ 0.5）且**时间更早**的其他 utterance。
4. 命中则写入 `quotes`，记录片段区间 `span` 和匹配度 `match`。

**意义：**
- `quotes` 让 "Gemini 的某个回答 → 我粘给 Claude → Claude 的回应 → 我粘给 Codex" 这条链在证据层就是连通的。
- 抽取思想时，"粘贴内容"属于被引用的原作者，只有我在粘贴前后加的评论才算我的原话（影响 `origin` 判定）。

由于 utterance 文本由各自的 agent 入库，**跨 AI 的引用检测只能在整合阶段，在合并后的全量证据层上运行**（见 §6）。

---

## 6. 多 AI 协作流程

### 6.1 分工

| 负责方 | 数据源 |
|---|---|
| Claude | Claude Code（Windows + MacBook）、Claude 桌面版、claude.ai 网页版导出 |
| Codex | Codex CLI / 桌面版会话、ChatGPT 导出、Gemini / Antigravity 导出 |
| 共同 | 我的文字作品（`doc`）、笔记；跨源整合 |

### 6.2 流水线（每个 agent 对自己的数据源执行 1–3）

1. **ingest**（脚本）：原始文件 → `source` + `utterance`。必须可重复执行，重跑得到完全相同的对象（幂等）。
2. **extract**（大模型）：**按时间顺序**逐个会话阅读；阅读时加载已有思想的索引（标题 + 陈述 + 谱系 ID），优先复用已有谱系（产生 `revises` 或 `restated-in`），确认是新的才创建新谱系。产出 `idea` 和 `relation`。
3. **self-verify**（脚本）：重算所有哈希、检查引用完整性、检查每个 idea 有证据。
4. **integrate**（在整合分支上，一次只由一个 agent 执行，另一方评审）：
   - 在全量证据层上运行跨 AI 引用检测（§5）；
   - 找出两边重复抽取的思想 → `same-as`，再写一个 `consolidates` 版本作为统一表述；
   - 补跨源的 `derives` / `influenced-by`（例如 Codex 会话里的想法源自 Claude 会话）；
   - 构建/修订顶层 `domain` 与 `part-of` 树。
5. **review**（我）：我浏览视图，对不认可的写 `retraction`，或直接写 `asserted_by: me` 的对象。

### 6.3 抽取粒度规则（最容易两边做得不一致，必须统一）

- **一个 idea = 一个可以单独被同意或反对的陈述，或一个可以单独被定义的概念。** 太大就拆（用 `part-of` 组合成 `theory`），太小（一句修辞）就不收。
- **修订 vs 新谱系**：核心论断不变、只是更精确 → `revises`；论断变了但是从旧的长出来的 → 新谱系 + `derives`；我说"不对，应该反过来" → `revises` 且新陈述取代旧陈述（旧的不变，自动成为历史）。
- **只是复述，没有新内容** → 不建新版本，写 `restated-in` 关系（用来统计一个思想被我提到多少次、跨越多长时间）。
- **statement 用我的口吻，贴近原话**，不要用 AI 的润色语言替换我的术语。我自创的术语保持原样。
- **语言**：statement 用原话语言（多为中文）；`title` 同语言。**【待议 D】** 是否额外加英文 `title_en` 便于检索？

### 6.4 归属优先级

当不同来源的断言冲突时：`me` > 整合阶段 agent > 抽取阶段 agent。视图按此优先级展示，低优先级的冲突断言标灰。

---

## 7. 仓库与 git 约定

### 7.1 目录

```
knowledge-spacetime/
├── SPEC.md                     # 最终共识规范
├── schema/                     # 各对象 JSON Schema
├── objects/
│   ├── source/ab/abcdef….json
│   ├── utterance/…
│   ├── idea/…
│   ├── relation/…
│   └── retraction/…
├── tools/                      # ingest / verify / view 脚本（语言【待议 E】，我倾向 Python）
├── views/                      # 生成物：mindmap.md、timeline.md、graph.json（可 gitignore 或每次重建）
├── raw/                        # 原始导出 —— 永远 gitignore
└── .gitignore
```

### 7.2 分支与提交

- `main`：只接受经过 verify 的合并。
- `extract/claude`、`extract/codex`：各自的入库与抽取。
- `integrate/<日期>`：整合工作，以 PR 形式合入 `main`，由另一方 AI 评审、我最终批准。
- 因为对象文件名即哈希、且没有可变文件，**两边分支合并不会冲突**；唯一可能的"冲突"是语义上的（多头谱系、矛盾关系），由 verify 报告、在整合阶段解决。

提交信息格式（记录时间轴的元数据）：

```
extract: Claude Code 会话 2026-10-10 ~ 2026-10-17（12 个会话）

Agent: claude
Model: claude-opus-5-5
Stage: extract
Sources: 12
Objects: +318 utterance, +41 idea, +57 relation
Prompt: sha256:<抽取提示词文件的哈希>
```

抽取提示词本身也放入仓库（`tools/prompts/`），让"这个思想是用什么规则抽出来的"也可追溯。

### 7.3 隐私与安全（必须在第一次提交前定好）

- 仓库**私有**。
- `raw/` 永不提交。
- 入库前运行密钥扫描（如 gitleaks），会话里出现过的 API key、token、密码、邮箱、电话一律脱敏：`_text` 中替换为 `[REDACTED:类型]` 并设 `_redacted: true`。由于 `text_sha256` 是对**原文**算的，持有原始文件的我仍可核验，而仓库里不泄露。
- 第三方的私人信息（如会话中提到的他人）同样脱敏。

### 7.4 `me` 的直接写入

我可以手写任何 idea / relation / retraction，`extracted_by` / `asserted_by` 填 `{"agent": "me"}`。这类对象拥有最高优先级，也是我"校对"整个库的方式。

---

## 8. 工具（v1 最小集）

| 命令 | 作用 |
|---|---|
| `ks ingest <platform> <path>` | 原始文件 → L0 对象 |
| `ks verify` | 重算哈希；检查引用、证据、多头谱系、关系方向合法性 |
| `ks quotes` | 跨会话复制粘贴检测（§5） |
| `ks log <谱系或关键词>` | 某个思想的演化史，类似 `git log --graph` |
| `ks tree [--at 2025-06-01]` | 思维导图；带 `--at` 时回放到该时刻 |
| `ks export graph` | 导出 Cytoscape / GraphML，用于可视化 |

---

## 9. 已知难点（提醒双方）

1. **时间可靠性**：网页版 chatbox 的导出有的只有日期；我的文字作品可能只有大致年份 → 用 `at_precision`，排序时精度低的排在该区间开头并标注。
2. **全局时间顺序**：理想情况下应按全局时间顺序抽取，但两个 agent 并行处理各自数据源做不到 → 允许抽取阶段先各自建谱系，整合阶段再用 `same-as` + `consolidates` + 跨源 `derives` 修正。这是本方案接受的妥协。
3. **MacBook 上的数据**：我（Claude）在这台 Windows 上无法直接读取 Mac 的文件。需要把 Mac 上的 `~/.claude/projects/` 拷到本机 `raw/claude-code/macbook/`，或在 Mac 上的 Claude 会话中运行同一套 ingest 脚本后推送到 `extract/claude` 分支（因为确定性哈希，两种方式结果一致）。
4. **规模**：先做一个会话的端到端试点，确认粒度和格式，再批量处理。

---

## 10. 需要与 Codex 达成共识的清单

| # | 决策 | Claude 的倾向 |
|---|---|---|
| A | 哈希/ID 格式 | `sha256:hex` + JCS；保留到 CIDv1 的映射 |
| B | AI 回复是否全文入库 | 全文入 `_text`，视图默认隐藏 |
| C | 关系指向版本还是谱系 | 版本 |
| D | 是否加英文标题 | 可选字段 `title_en` |
| E | 工具语言 | Python 3.11+，零外部依赖（hashlib + 自写 JCS） |
| F | `kind` / `rel` / `origin` 封闭集 | 按本文 v1，新增需修订规范 |
| G | 抽取粒度判定规则（§6.3） | 按本文，试点后调整 |
| H | 跨 AI 粘贴检测阈值 | 150 字符 / Jaccard 0.5，试点后调整 |
| I | 整合阶段的轮值与评审方式 | 一方执行、另一方 PR 评审、用户批准 |

---

## 附录：最小示例（虚构内容，仅演示结构）

```
utterance U1  (me, claude-code, 2026-10-10)  "我觉得协作规则应该像代码一样可以 fork"
utterance U2  (me, gemini,      2026-10-12)  粘贴了 Claude 的回答 + "但 fork 之后怎么保证共识？"
    quotes → U1.reply（Claude 的回答）
utterance U3  (me, codex,       2026-10-15)  "规则可以 fork，但需要一个 merge 回主线的仪式"

idea I1  (genesis, claim, origin=self)   "协作规则应可被分叉"            evidence [U1]
idea I2  (question, origin=self)         "分叉后的共识如何保证？"         evidence [U2]  parents [{I1, derives}]
idea I3  (lineage=I1, claim, origin=co)  "协作规则应可分叉，并有合并回主线的机制"
                                          evidence [U3]  parents [{I1, revises}]
relation  I3 answers I2
relation  I1 part-of D1（domain: 自由协作体）  primary
```

思想时间线：`I1 ──revises──▶ I3`，`I1 ──derives──▶ I2 ◀──answers── I3`；
思维导图：`自由协作体 → 协作规则应可分叉（最新版 I3）→ ……`；
证据层：U1（Claude）→ U2（Gemini，引用 Claude 回复）→ U3（Codex），三家会话被缝成一条链。
