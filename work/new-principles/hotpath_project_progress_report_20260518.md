# HotPath Launcher 项目进度与实现评估报告

**日期**：2026-05-18  
**评估对象**：

- `hplauncher_claude_source_2026-05-18.zip`
- `hotpath_launcher_eval_20260518.zip`
- `Merkle-DAG存储层中的可变数据处理方案.md`
- `hotpath_storage_layer_design.md`
- `hotpath_launcher_design_v0.5.md`

**重要限制**：当前评估环境没有安装 `cargo`，因此本报告不能独立确认 Rust 编译、测试、clippy、Tauri 构建是否通过。报告中的“可运行性”判断主要基于源码静态检查、目录结构、模块完整度，以及 Codex 包中自带的进度报告。Codex 包声称已通过 `cargo fmt --all`、`cargo test`、`cargo clippy --all-targets --all-features -- -D warnings` 与前端构建，但我没有在当前环境中复验。

---

## 1. 总体结论

两份实现都已进入 **Phase 0.5 可评估原型** 状态，不再只是骨架：

- 两者都包含 Rust workspace、CLI、Tauri/Svelte GUI、hotpath YAML、LLM provider 层、semantic view 字段。
- 两者都实现了 `hp.llm.chat / list_models / list_providers`，并支持本地 OpenAI-compatible provider，用于 Ollama / LM Studio 等本地模型服务。
- 两者都保留了 `hp.text.translate/summarize` 与 `hp.llm.translate/summarize` 的多视角入口，开始体现 v0.5 的“容器元语言”定位。

但两者侧重点仍然不同：

| 分支 | 当前气质 | 最适合承担 |
|---|---|---|
| Claude Code | 产品化、交互、丰富功能、较强 alias/pattern 基础 | GUI/UX、semantic parsing、更多 primitive、dogfood 体验 |
| Codex | correctness、确定性、trace、LLM provider、测试与报告更完整 | 主干 core、schema、hash/effects/version、LLM trace、CI 门控 |

我的建议是：**继续双线发展，但以 Codex 分支作为当前 v0.5 correctness 主干；从 Claude 分支迁移更强的 alias 解析、GUI/Inspector、更多本地 primitive 和 storage/warm-cache 思路。**

---

## 2. 当前项目进度

### 2.1 架构层

当前两个实现均延续三层基本结构：

```text
Kernel / core infrastructure
→ Primordial hotpath: Rust implementation + YAML declaration
→ Derived hotpath: YAML step composition
```

v0.5 的核心新增是把 HotPath 从“launcher/agent framework”提升为“容器元语言”：

```text
N 种自然表达 / entrypoint / view
→ 1 个 canonical capability
→ M 个 concrete implementation
```

代码层表现为：

- schema 中新增 `canonical_capability`、`view_kind`。
- trace 中开始记录 entrypoint / canonical capability / implementation。
- `hp.text.translate` 与 `hp.llm.translate` 不再互相替代，而是同一 canonical capability 的不同 semantic view。

### 2.2 LLM Provider Layer

两个实现均已具备 OpenAI-compatible provider 层，覆盖本地 Ollama / LM Studio / vLLM 等服务。

已出现的主要能力：

- `providers.toml`
- `default` / `default_model`
- `model_aliases`
- provider `privacy = local | external`
- `hp.llm.chat`
- `hp.llm.list_models`
- `hp.llm.list_providers`
- `hp.llm.translate`
- `hp.llm.summarize`
- `hp.text.translate` / `hp.text.summarize` 作为 text-centric wrappers

Codex 分支还增加了：

- `hp.llm.set_default_model`
- 独立 LLM trace 模块
- external provider 默认阻止，需 `HOTPATH_ALLOW_EXTERNAL_LLM=1`
- `HOTPATH_LLM_RECORD_FULL_TEXT` 开关

### 2.3 CLI

两个分支均有 CLI。Codex 的 CLI 更贴近 v0.5 最小 LLM provider 目标，包含：

- `llm list-providers`
- `llm list-models`
- `llm test`
- `llm config`
- `llm doctor`
- `llm set-default-model`

Claude 分支也有 LLM CLI 与 doctor，但整体 CLI 中还混合了较多产品型功能和 trace/snapshot/warm-cache 操作。

### 2.4 GUI

两个分支都已经不是纯 CLI。

Claude 分支：

- 更像一个 launcher 产品。
- 有更完整的 spotlight 风格窗口、托盘、快捷键、Inspector 组件。
- 适合继续打磨日常使用体验。

Codex 分支：

- UI 中已经加入 trace panel、recent traces、external provider 确认路径。
- 更像 correctness/debuggable launcher。
- 适合做主干，但需要继续吸收 Claude 的 Inspector / alias / UX。

### 2.5 Trace 与可观测性

Codex 分支更系统：

- general execution trace：`entrypoint_id`、`canonical_capability`、`view_kind`、`implementation_id`、args、env fingerprint、duration、status、output_hash/preview。
- LLM trace：provider、privacy、model、purpose、format、prompt_hash、response_hash、token、latency、finish_reason、是否记录全文。

Claude 分支：

- 有 JSONL trace store，支持按日期、recent、find_by_id、stats。
- 有 warm store / warm counter 等对未来“冷路径→温路径→热路径”更有帮助的模块。
- 但 LLM trace 的隐私化元数据结构不如 Codex 独立清楚。

---

## 3. Claude Code 实现评估

### 3.1 优点

1. **更强的产品感**：GUI、托盘、快捷键、Inspector 与日常 launcher 使用体验更完整。
2. **alias 解析更强**：`kernel/alias.rs` 支持 exact alias、prefix 参数、suffix、多参数 alias，例如 `translate {text} to {target_lang}`，这是 Codex 当前不具备的能力。
3. **更多 primitive**：比 Codex 多出 app launch、URL open、fs write/append、username、types registry 等能力，更适合实际 dogfood。
4. **storage/warm path 预演**：包含 `storage/db.rs`、`trace_store.rs`、`warm_store.rs`、`warm_counter.rs`，这些对后续 v0.6 存储层与温路径机制有参考价值。
5. **LLM resolver 原型**：`llm_resolver.rs` 显示它已经尝试 L4 冷路径解析，虽然现在不应作为主任务，但对后续有参考。

### 3.2 问题

1. **LLM trace 不如 Codex 严格**：缺少独立 `llm/trace.rs` 那种默认不记录全文、只记录 hash/token/latency/privacy/purpose 的结构。
2. **确定性与 schema 严谨性略弱**：部分地方仍使用 `HashMap`，而 Codex 更系统使用 `BTreeMap` 保证稳定序列化与 hash。
3. **功能面偏大**：含 Anthropic 旧路径、LLM resolver、warm store、snapshot 等多个方向，容易造成 Phase 0.5 范围扩张。
4. **与 v0.5 最小 OpenAI-compatible 本地 LLM 路线相比，遗留概念较多**：例如旧 Anthropic 模块应降级为未来 provider，而不是当前主路径。

### 3.3 建议迁移给 Codex 的部分

- `kernel/alias.rs` 的多参数 alias 解析器。
- Inspector / GUI 交互模式。
- `TraceStore` 的按日期 trace 文件与 stats 设计。
- warm_store / warm_counter 的思路，作为未来 Layer 4 / warm path 统计基础。
- app launch、url open、fs write/append 等实用 primitive。
- 更丰富的 root discovery 和 package/dev 运行兼容处理。

---

## 4. Codex 实现评估

### 4.1 优点

1. **更适合作为主干**：源码组织更清晰，报告中列出通过 fmt/test/clippy/build 的结果。
2. **v0.5 LLM provider 实现较完整**：OpenAI-compatible client、provider config、model aliases、privacy、doctor、set default model 等较系统。
3. **LLM trace 设计好**：默认不记录全文，只存 prompt/response hash 与元数据，符合隐私优先原则。
4. **semantic view trace 到位**：trace 能记录 entrypoint、canonical_capability、view_kind、implementation_id。
5. **external provider 安全闸门**：external provider 默认阻止，需显式环境变量或 GUI 确认。
6. **BTreeMap 与 deterministic config**：更符合 content-addressed / reproducible 设计要求。

### 4.2 问题

1. **alias 能力不如 Claude**：目前主要支持 tail single-param alias；不能覆盖 `translate {text} to {target_lang}` 这类高频自然表达。
2. **primitive 较少**：缺少 app launch、URL open、fs write/append 等对 launcher dogfood 很重要的动作。
3. **GUI 产品感仍需增强**：有 trace panel 与 external confirm，但 Inspector/spotlight 的体验不如 Claude。
4. **缺少更成熟的 storage/warm path 模块**：当前 trace 足够清晰，但温路径统计和 cache 机制不如 Claude 的 storage 模块有探索性。
5. **`canonical_capability` 和 `view_kind` 是否进入 contract hash 需要重新判断**：建议 v0.6 中区分 capability contract hash 与 entrypoint/presentation hash，避免 view 表达变化引起不必要的 contract hash 变动。

### 4.3 建议继续保留的部分

- `BTreeMap` everywhere 的确定性风格。
- LLM provider config 与 deterministic rendering。
- 独立 `llm/trace.rs`。
- external provider 隐私 gate。
- `hp.llm.set_default_model`。
- progress report / smoke report 的工程纪律。

---

## 5. 取长补短建议

### 5.1 主干策略

建议以 **Codex 分支作为 v0.5 主干**，因为它更接近“可验证 correctness 主线”，且它自带报告称测试与构建已通过。

Claude 分支不应废弃，而应作为：

```text
UX / alias / primitive / warm path 实验分支
```

### 5.2 优先迁移清单

从 Claude → Codex：

1. 多参数 alias 解析。
2. Inspector / GUI 交互。
3. app launch、url open、fs write、fs append。
4. TraceStore 的按日期 JSONL 与 stats 能力。
5. warm_store / warm_counter 思路。
6. 更丰富的 type registry / pattern registry。

从 Codex → Claude：

1. LLM trace 模块。
2. external privacy gate。
3. `hp.llm.set_default_model`。
4. deterministic config render。
5. `BTreeMap` 替换可参与 hash/trace 的 `HashMap`。
6. 清理 Anthropic 旧路径，使其成为未来 provider，而不是特殊路径。

---

## 6. 存储层讨论对当前 v0.5 的影响

新的存储层文档提出了四层架构：

```text
Layer 1 内容层：不可变 Merkle-DAG，对象内容即身份
Layer 2 身份层：稳定实体身份记录
Layer 3 引用层：唯一真正可变层，含版本化引用与当前态引用
Layer 4 派生缓存层：索引、向量、压缩派生品、搜索缓存等，可丢弃可重建
```

这对当前 v0.5 有直接影响：

### 6.1 不需要推翻 v0.5

v0.5 的 semantic view / LLM provider / trace / canonical capability 设计仍然成立。存储层是更底层的架构补强，不要求立即删除当前 YAML registry 或 SQLite trace。

### 6.2 需要改变的理解

1. **不要在 Merkle-DAG 节点中加入 mutable/immutable 标记**。Merkle-DAG 层本身只存不可变内容。
2. **`canonical_capability` 未来应成为 Layer 2 identity anchor**，而不只是字符串字段。
3. **alias 集合与 implementation 集合应采用 append-only set 模式**，而不是长期作为某个 YAML 的嵌入字段。
4. **intent cache、alias index、query cache、FTS/向量索引都应归入 Layer 4**，不能参与 correctness contract。
5. **provider config、default model、用户偏好属于本机当前态引用 / local config**，不应进入全局 content-addressed registry。
6. **trace 是事件日志**。普通 trace 可以是 local append-only log；LLM trace 默认只存 hash 与元数据，全文必须 opt-in。

### 6.3 应删改的 v0.5 表述

建议修改 v0.5 中以下理解：

- “snapshot / rollback” 不应是所有 mutable 对象的统一机制，只适用于 history-meaningful 的离散可变对象。
- “当前 registry” 不应被理解为一个单一 YAML 目录的事实源，长期应拆成 content objects + identity anchors + refs + local Layer 4 indexes。
- “alias / implementation 归属在 hotpath YAML 内” 是 Phase 0 方便做法，不应作为长期本体结构。

### 6.4 应增加的 v0.6 内容

- Storage Layer 四层架构。
- Mutable 对象三分类。
- Append-only set for expressions / implementations。
- Active / latent / silenced 三层休眠机制。
- Layer 4 local-only 原则。
- Query/alias/search cache 的 Layer 4 定位。
- `storage_class` / `retention_policy` / `cache_tier` 之类字段预留，但不强制所有 hotpath 填写。

---

## 7. 下一阶段建议路线

### Phase 0.5 stabilization

目标：将 Codex 主干稳定为可 dogfood 的本地 LLM launcher。

任务：

1. 用 Codex 分支继续跑 fmt/test/clippy/build。
2. 加入 Claude 的多参数 alias parser。
3. 加入 Claude 的 GUI Inspector 思路。
4. 加入 Claude 的 app/url/fs write primitive。
5. 明确 `canonical_capability` 与 `view_kind` 的 hash 归属。
6. 保持 benchmark runner 延后。

### Phase 0.6 storage integration

目标：不大改业务逻辑，但将存储抽象放入代码。

任务：

1. 新增 `storage` 模块接口：`ContentStore`、`IdentityStore`、`RefStore`、`CacheStore`。
2. 当前 YAML loader 仍然工作，但加载后可选写入 Layer 1 content store。
3. 现有 intent cache / alias index / trace index 明确标注为 Layer 4。
4. 对 `canonical_capability` 建立最小 identity record 结构。
5. 先不做分布式，不做 RocksDB 强绑定；可继续用 SQLite / filesystem 作为本地实现。

### Phase 1

目标：从“本地工具”进入“可演化容器语言”。

任务：

1. L4 LLM cold path：根据 capability schema 生成候选 derived AST。
2. Warm path：冷路径成功后进入温路径存储，多次成功后建议晋升。
3. Benchmark v0：先评测多个本地 LLM 在 translate/summarize 上的表现。
4. Append-only set 原型：natural expressions 与 implementations 的增量事件链。
5. Layer 4 tiering：active/latent/silenced 先从 alias/search index 开始。

---

## 8. 总评

项目已经从“架构想法”进入“可评估工程原型”。现在最重要的不是继续扩张功能，而是稳定三条主线：

```text
1. Codex correctness 主干
2. Claude UX / alias / primitive 经验
3. v0.6 storage layer 抽象
```

如果下一轮开发能做到：

- Codex 主干可稳定构建；
- Claude 的多参数 alias 与 GUI/primitive 被吸收；
- 存储层四层模型进入设计文档但不造成大规模重构；

那么 HotPath 就会从 Phase 0.5 的“本地 LLM hotpath launcher”进入 Phase 0.6 的“可持续演化的容器元语言底座”。
