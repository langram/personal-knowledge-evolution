# HotPath Launcher — Phase 0 设计方案与启动提示词

**项目代号**：HotPath Launcher（暂定，可改）
**文档版本**：v0.1（启动版）
**目标受众**：作者本人 + Claude Code / Codex / 类似的 coding agent
**日期**：2026-05

---

## 第一部分　Phase 0 的边界

### 什么是 Phase 0

这个项目长期看是"基于哈希索引的类型化语义解析系统"，最终愿景是一个本地优先、内容寻址、由 AI 辅助构造的可执行行为知识库。但 Phase 0 **不实现愿景的全部**——它只验证一个核心假设：

> **高频用户意图能否被编译为本地热路径，使重复执行时显著快于 LLM 重新推理，也显著快于用户手动操作？**

如果这个假设在 Phase 0 被证实，后续所有层（Hub / Merkle-DAG native language / 全球 Nexus）才有根基。如果证伪，应该立刻重新设计基础机制而不是叠加上层。

### Phase 0 的明确范围

**做：**

- 一个 Windows 11 上的桌面应用，全局快捷键唤起
- 输入框 + 结果列表 UI（类 Raycast / Alfred）
- 内置 12 条"原语级"热路径（见后文清单）
- 基于 alias 表 + pattern 表 + 整句缓存的语义解析
- 简单的 type tag 系统（先不做 subtype hierarchy）
- 热路径以 YAML 文件定义，运行时编译并 hash
- 执行结果缓存（content-addressed）
- 单一 LLM provider 接入（Anthropic API 或 OpenAI 兼容接口）
- 完整的执行 trace 日志
- 本地路径库快照与回滚

**不做：**

- macOS / Linux / 移动端（Phase 1+）
- Nexus / Hub / 路径分享（Phase 2+）
- subtype lattice 与复杂类型推理（Phase 1+）
- WASM 沙箱（Phase 1+）
- 本地 LLM（先用云端 API，Phase 1 加本地）
- 自我升级 / 自动晋升热路径（Phase 1+，先手动）
- Merkle-DAG native language（Phase 3+）
- 多用户 / 协作（永远不在核心，留给 Hub 层）

### 成功判据

Phase 0 在以下指标全部达成后视为成功：

| 指标 | 目标 |
|---|---|
| 冷启动唤起延迟 | < 200ms |
| 整句缓存命中时 query → 结果 | < 30ms |
| 整句缓存未命中、alias 解析时 | < 100ms |
| LLM 冷路径推理 | < 5s (云端 API) |
| 至少能跑通 12 条原语热路径 | 100% |
| 作者本人能在两周连续使用中替代至少 5 个原有工作流 | dogfood |

---

## 第二部分　技术栈

### 选型与理由

| 层 | 选择 | 理由 |
|---|---|---|
| 桌面框架 | **Tauri 2.x** | 包体小、Rust 后端、跨平台预留、WebView 前端灵活 |
| 后端语言 | **Rust** | 性能、并发、与 Tauri 原生集成、与 Nova Principia 技术栈一致 |
| 前端 | **Svelte 5 + Vite** | 比 React 轻、reactivity 模型适合 launcher 的实时输入响应 |
| 本地存储 | **SQLite + FTS5** | 单文件、零配置、FTS5 已经能做 alias 匹配 |
| 内容寻址 | **Blake3** | 比 SHA-256 快几倍、有标准 Rust 实现 |
| 全局快捷键 | **`tauri-plugin-global-shortcut`** | 官方插件 |
| 路径定义格式 | **YAML**（可序列化为 JSON 做 hash） | 人可读、未来迁移 DAG-CBOR 不破坏上层 |
| LLM provider | **Anthropic API** (`anthropic-sdk-rust` or HTTP) | 兼容 prompt-eng 习惯；接口设计为 provider-agnostic |
| 日志 | **`tracing` + `tracing-subscriber`** | Rust 生态标准 |

### 不选什么及理由

- **不用 Electron**：包体大、启动慢，与 launcher 性质矛盾
- **不用 Tantivy（暂时）**：Phase 0 数据量小到 SQLite FTS5 完全够用，少一个组件
- **不用 sled / RocksDB**：SQLite 的事务和工具生态更成熟
- **不用 WASM 插件（暂时）**：Phase 0 所有原语都是 Rust 原生实现，WASM 留给 Phase 1 引入第三方插件时
- **不用 LangChain / 类似框架**：直接调 HTTP API，不引入抽象层

---

## 第三部分　架构

### 核心数据流

```
用户敲键
  ↓
[输入归一化] → 小写 / NFC / trim
  ↓
[L1 整句缓存] → hash(normalized_input) → SQLite 查找
  ↓ 命中 → 返回缓存的 AST → 执行
  ↓ 未命中
[L2 Alias 匹配] → Aho-Corasick / FST → 所有候选 (span, semantic_node) 对
  ↓
[L3 候选图构建] → 节点 = 候选语义，边 = 包含 / 邻接 / 类型
  ↓
[L4 Pattern 匹配] → (action.X, type.Y) → hotpath.Z
  ↓ 1 个候选 → 直接执行
  ↓ N 个候选 → UI 询问消歧
  ↓ 0 个候选
[L5 LLM 冷路径]→ 提示词描述可用原语和 schema，生成候选 AST
  ↓
[执行引擎] → 按 AST 调度原语，收集结果，写 trace
  ↓
[结果展示] + [写回缓存]（如果成功且用户未否决）
```

### 模块分解

```
src-tauri/src/
  main.rs                 # Tauri 入口
  commands.rs             # 暴露给前端的 Tauri 命令
  core/
    intent.rs             # 输入归一化 + 整句缓存查询
    alias.rs              # alias 索引 (Aho-Corasick)
    pattern.rs            # pattern 匹配
    types.rs              # type tag 注册表
    ast.rs                # AST 数据结构 + hash 计算
    cache.rs              # 多级缓存层
  runtime/
    executor.rs           # AST 执行调度器
    primitives/           # 原语实现 (12 条 + 通用 helper)
      math.rs
      file.rs
      text.rs
      clipboard.rs
      web.rs
      llm.rs
      ...
  hotpath/
    schema.rs             # YAML hotpath 定义 schema
    loader.rs             # 从 YAML 加载、validate、hash
    registry.rs           # 内存中的 hotpath 注册表
  storage/
    db.rs                 # SQLite 连接池、迁移
    content_addr.rs       # Blake3 包装
    snapshot.rs           # 路径库快照
  llm/
    provider.rs           # LLM provider trait
    anthropic.rs          # Anthropic 实现
  trace/
    logger.rs             # 结构化执行 trace

hotpaths/                 # 内置热路径定义
  evaluate_expr.yaml
  list_files.yaml
  ...

src/                      # Svelte 前端
  App.svelte
  lib/
    Launcher.svelte       # 主输入框 + 结果列表
    Result.svelte         # 单个结果项
    Disambig.svelte       # 消歧 UI
    Render/               # 不同输出类型的渲染组件
      Table.svelte
      Text.svelte
      File.svelte
```

### Hotpath 文件 schema

```yaml
# hotpaths/list_files.yaml
id: hp.file.list
version: 0.1.0
# hash 由内容自动计算，不手填

intent:
  pattern: "action.list + type.file"

labels:
  zh:
    name: "列出文件"
    aliases:
      - "列文件"
      - "列出 {dir} 的文件"
      - "查看 {dir} 里的文件"
  en:
    name: "List files"
    aliases:
      - "list files in {dir}"
      - "show files in {dir}"
      - "ls {dir}"

inputs:
  dir:
    type: path
    required: false
    default: "{{cwd}}"
  recursive:
    type: bool
    default: false

outputs:
  type: list<file_entry>

permissions:
  filesystem:
    read: ["{{dir}}"]

steps:
  - id: scan
    primitive: fs.list_directory
    args:
      path: "{{dir}}"
      recursive: "{{recursive}}"
  - id: render
    primitive: ui.render_table
    args:
      input: "{{scan.output}}"
      columns: ["name", "size", "modified"]

validators:
  - primitive: assert_type
    args: {target: "{{scan.output}}", type: "list"}

fallback:
  strategy: ask_llm_to_repair
  max_retries: 1
```

---

## 第四部分　Phase 0 的 12 条原语热路径

按 ChatGPT 提议的 A–E 五类各挑几个，确保元结构闭环：

### A 类（数据访问）
1. `hp.fs.list` — 列目录（含可选递归）
2. `hp.fs.find` — 按名/扩展名找文件
3. `hp.fs.read` — 读文件内容
4. `hp.clipboard.get` / `hp.clipboard.set` — 剪贴板
5. `hp.web.fetch_title` — 抓网页标题（HTTP GET + HTML title 提取）

### B 类（解析抽取）
6. `hp.text.extract_urls` — 从文本提取 URL

### C 类（转换计算）
7. `hp.math.eval` — 数学表达式求值（用 `meval` crate）
8. `hp.text.translate` — 翻译（调 LLM）
9. `hp.text.summarize` — 摘要（调 LLM）
10. `hp.hash.content` — 计算文件或文本的 Blake3

### D 类（验证）
11. `hp.assert.exists` — 断言路径存在（作为其他路径的子组件）

### E 类（路径管理）
12. `hp.system.list_hotpaths` — 列出所有已注册热路径（自反射）

最后一条很重要——它让系统能解释自己。Phase 0 阶段你应该能在 launcher 里输入 "列出所有路径" 并看到这 12 条。

---

## 第五部分　Phase 0 的开发顺序

按依赖关系排：

1. **Week 1**：Tauri 项目骨架 + 全局快捷键 + 空 launcher 窗口
2. **Week 2**：SQLite + Blake3 + hotpath YAML loader + hash 计算
3. **Week 3**：原语注册表 + 实现 `hp.math.eval` + `hp.clipboard.*`（最简单的两条）
4. **Week 4**：Alias 索引（Aho-Corasick） + pattern 匹配 + 整句缓存
5. **Week 5**：实现 `hp.fs.*` 三条 + `hp.web.fetch_title`
6. **Week 6**：LLM provider 抽象 + Anthropic 实现 + `hp.text.translate` / `hp.text.summarize`
7. **Week 7**：UI 打磨（结果渲染、消歧、键盘导航）+ 剩余原语
8. **Week 8**：执行 trace + 快照与回滚 + dogfood 期开始

时间表是给一个全职 solo dev 的。按你实际可投入精力，**乘 1.5–2.0** 比较现实。

---

## 第六部分　Phase 0 完成后做什么

Phase 0 跑稳之后，按这个顺序扩展：

**Phase 0.5（dogfood 期，4–8 周）**：自己每天用。新增任何热路径都先手写 YAML。记录所有"手动多次的操作"作为下一批热路径候选。

**Phase 1（plugin + 多平台）**：引入 WASM 沙箱、第三方插件机制、macOS / Linux 支持。

**Phase 2（温/热路径晋升）**：实现自动 trace 抽取 → 温路径候选生成 → 用户确认后晋升为热路径。

**Phase 3（Hub 雏形）**：本地热路径库的导出/导入。GitHub repo 作为最初的 "Hub"。

**Phase 4+**：见 vision v0.1。

---

# 启动提示词（给 Claude Code / Codex）

下面这段可以原样复制粘贴给 Claude Code 或 Codex 作为初始任务描述。

---

## START PROMPT FOR CLAUDE CODE / CODEX

我要启动一个新项目，代号 **HotPath Launcher**。这是一个 Windows 11 桌面应用，长期愿景是"本地优先、内容寻址、AI 辅助构造的可执行行为知识库"，但当前阶段（Phase 0）只验证核心机制，**不实现长期愿景的任何上层**。

### 项目目标（Phase 0）

构建一个 Raycast / Alfred 风格的桌面 launcher：用户按全局快捷键唤起，输入自然语言，系统通过**预编译的热路径库**毫秒级匹配并执行，绕过每次 LLM 推理。当本地无法解析时回落到 LLM 冷路径，结果缓存以加速未来同类查询。

### 核心假设（必须在 Phase 0 验证）

高频用户意图能被编译为本地热路径，使重复执行时比 LLM 重新推理快至少一个数量级，且比手动操作显著快。

### 技术栈（不要替换，理由已经评估过）

- **Tauri 2.x** + **Rust** 后端 + **Svelte 5 + Vite** 前端
- **SQLite + FTS5** 本地存储
- **Blake3** 内容寻址
- **YAML** 作为热路径定义格式
- **Anthropic API** 作为 LLM provider（HTTP 直连，不引入 langchain 类抽象）
- **`tracing`** crate 做结构化日志
- **`tauri-plugin-global-shortcut`** 全局快捷键
- **`aho-corasick`** crate 做 alias 匹配
- **`meval`** crate 做数学表达式求值
- **`scraper`** crate 做 HTML 解析

### Phase 0 范围（严格遵守）

实现 **12 条原语热路径**：
1. `hp.fs.list` — 列目录
2. `hp.fs.find` — 找文件
3. `hp.fs.read` — 读文件
4. `hp.clipboard.get`
5. `hp.clipboard.set`
6. `hp.web.fetch_title` — 抓网页标题
7. `hp.text.extract_urls`
8. `hp.math.eval`
9. `hp.text.translate` — 调 LLM
10. `hp.text.summarize` — 调 LLM
11. `hp.hash.content`
12. `hp.system.list_hotpaths` — 自反射列出所有路径

### 不在 Phase 0 范围内（不要实现）

- macOS / Linux 支持（暂时只针对 Windows 11）
- 自动晋升 / 自我升级机制（路径由人手写 YAML）
- WASM 沙箱（所有原语都是 Rust 原生）
- 本地 LLM（云端 API only）
- Hub / 路径分享 / 多用户
- Merkle-DAG native language
- Subtype lattice（用扁平 type tag 即可）

### 第一周的具体任务

请按以下顺序完成。每完成一项停下来让我 review，再继续下一项。

**任务 1：项目骨架**

```bash
# 期望的初始目录结构
hotpath-launcher/
├── Cargo.toml
├── tauri.conf.json
├── package.json
├── vite.config.ts
├── README.md
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   └── lib.rs       (空模块声明)
│   └── tauri.conf.json
├── src/                  (Svelte 前端)
│   ├── App.svelte
│   ├── main.ts
│   └── app.css
├── hotpaths/             (YAML 路径定义，先放占位文件)
├── docs/
│   └── architecture.md
└── .gitignore
```

要求：
- 使用 `pnpm` 而非 `npm`
- Cargo.toml 包含上面列出的所有 Rust 依赖
- README.md 写一段 200 字的项目说明（说明这是 Phase 0、当前能做什么、不能做什么）
- `cargo tauri dev` 必须能跑起来并显示一个空窗口

**任务 2：全局快捷键 + Launcher 窗口**

- 注册全局快捷键 `Ctrl+Space`（如果与系统冲突可临时改为 `Ctrl+Alt+Space`）
- 按下快捷键时：屏幕中央偏上显示一个 640×80 px 的窗口，仅含一个输入框
- 失焦或 Esc 时窗口隐藏（不退出进程）
- 进程常驻：系统托盘图标，右键菜单含 "Quit"

**任务 3：Hotpath YAML loader**

实现 `src-tauri/src/hotpath/` 模块：
- `schema.rs`：定义 Hotpath struct，对应上面"Hotpath 文件 schema"小节给出的 YAML 格式（见附录）
- `loader.rs`：从 `hotpaths/` 目录读取所有 `.yaml` 文件，解析为 Hotpath struct，**计算每个的 Blake3 hash**（基于规范化 JSON 序列化）
- `registry.rs`：内存中的 Hotpath 注册表，key 是 hash，value 是 Hotpath struct

要求：每个 Hotpath 加载后，hash 必须稳定且可复现。重新加载同一个 YAML 必须得到相同 hash。

**任务 4：实现两条最简单的原语**

- `hp.math.eval`：YAML 定义 + `runtime/primitives/math.rs` 中的实现
- `hp.clipboard.get`：同上，`runtime/primitives/clipboard.rs`

要求：
- 写完后能通过单元测试调用
- 在 Tauri command 中暴露一个 `execute_hotpath(id: String, args: serde_json::Value)`，前端可以测试调用
- 前端临时加几个按钮直接调用这两个 hotpath 验证打通

### 编码规范

- **错误处理**：使用 `anyhow::Result` 在应用层，`thiserror` 定义模块级错误类型
- **日志**：所有跨模块调用使用 `tracing::instrument`
- **测试**：每个原语必须有至少 2 个单元测试（成功 + 失败路径）
- **注释**：公开 API 必须有 doc comment，内部 helper 简短即可
- **提交粒度**：每完成一个任务一个 commit，commit message 写清楚做了什么
- **没把握时停下来问**，不要自己脑补设计决策

### 质量门控

任何 PR / commit 前必须确认：
- `cargo fmt` 跑过
- `cargo clippy --all-targets -- -D warnings` 没有 warning
- `cargo test` 全过
- `pnpm typecheck` 没有 TypeScript 错误

### 与我协作的方式

- 完成一个任务后，给我一个简短总结 + 关键决策点 + 任何踩坑
- 遇到不确定的设计决策时，**先列出 2–3 个方案并说明 trade-off，让我选**，不要自己拍板
- 不要试图一次性把 Phase 0 全部做完——任务 1–4 是第一周，做完后等我反馈
- 如果发现这份提示词里的某个决定明显错了（比如某个 crate 不存在），告诉我并提议修正，不要悄悄换

### 附录：Hotpath YAML schema 的完整字段定义

```yaml
id: string                    # 必填，全局唯一，形如 hp.<category>.<name>
version: string               # 必填，semver
# hash 由系统计算，不手填

intent:
  pattern: string             # 形如 "action.X + type.Y"，Phase 0 简单字符串即可

labels:                       # 多语言 alias
  <lang_code>:                # zh, en, ja, ko 等
    name: string              # 路径的人类可读名
    aliases:                  # alias 列表
      - string                # 可含 {param_name} 占位符

inputs:                       # 输入参数
  <param_name>:
    type: string              # path | string | integer | bool | list | ...
    required: bool            # default: true
    default: any              # 可选默认值

outputs:
  type: string                # 输出类型

permissions:                  # 权限声明
  filesystem:
    read: [path]
    write: [path]
  network:
    domains: [string]

steps:                        # 执行步骤
  - id: string
    primitive: string         # 原语名
    args: map<string, any>    # 参数，可引用 {{prev_step.output}} 或 {{input.param}}

validators:                   # 后置验证
  - primitive: string
    args: map<string, any>

fallback:
  strategy: string            # ask_llm_to_repair | retry | fail
  max_retries: integer
```

---

**确认开始前，请回答**：

1. 上面所有 Rust crate 你是否都熟悉它们当前的最新 API？如果某个 crate 你不确定，列出来
2. Tauri 2.x 的全局快捷键插件你是否清楚最新用法？
3. 我们的协作节奏（一任务一确认）你能否接受？
4. 有没有任何你强烈建议改动的设计决策？如果有，列出 + 理由

回答以上 4 点后等我确认，然后开始任务 1。

## END OF START PROMPT

---

# 后续迭代建议

把上面的 prompt 给 Claude Code 之前，你可以做以下两件准备：

1. **在 GitHub 上开私有 repo `hotpath-launcher`**，授权 Claude Code 访问
2. **准备好 Anthropic API key**（或 OpenAI key），存到环境变量，**不要让 Claude Code 把它写进任何 commit**

Phase 0 完成后，把这份文档和实际的实现做对照，修正与现实差异最大的部分作为 v0.2 文档。这份文档应该和代码一起演化，而不是事后写。
