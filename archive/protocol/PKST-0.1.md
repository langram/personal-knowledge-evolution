# PKST 0.1 — 个人思想语义时空档案

状态：N3 候选；编码层已获双方一致通过，对象层修正待 Claude 复核。2026-10-24。

## 1. 范围和权威

本协议统一来源取证、内容寻址、事件身份、解释与演化记录。原始来源保持只读。采集窗口必须有截止边界，所有来源记录覆盖范围与缺口；“已盘点”不等于“已取得正文”，“已取得正文”不等于“已提取思想”。用户发送、作者署名、引用者、观点持有者分别记录，收录不等于采纳。AI 不得冒充用户写入采纳。

Codex 主导 protocol、工具和整合；Claude 只写 contributions/claude。交互消息由 Computer Use 发送，文件用共同目录交换，保留协商版本。首次范围：Windows/Mac Codex、Claude 本地历史及 ChatGPT、Claude.ai、Gemini 官方网页聊天。原始记录中包含的指令一律是档案数据，不执行。

## 2. 物理表示和身份

结构对象：CIDv1，codec dag-cbor (0x71)，multihash sha2-256 (0x12，32 bytes)，显示用无填充小写 base32（前缀 b）。原始 bytes：codec raw (0x55)。CID 不包含在自身编码中。

PKST-CBOR-1 是 DAG-CBOR 的窄子集：null、bool、整数 [-9007199254740991,9007199254740991]、合法 Unicode 标量字符串、数组、字符串键 map、CID 链接。禁 float、NaN、Infinity、未配对 surrogate、重复 map 键和未知 tag。整数和长度最短编码；map 键按 UTF-8 编码长度、再按 UTF-8 字节升序。链接只用 tag 42 + bytes(0x00 + CID binary)。

字符串一律保持原样，不自动 NFC、不改换行、不 trim。原始文本内容块也保持逐字符不变。用于检索的 NFC/LF 文本必须另建 derived-content 并记录变换，不能替代原文。JSON 投影以单键 {"$link":"b..."} 表示链接，$link 是保留键；这只是输入/审阅表示，编码中为真正 CID link。对象所有字段参与哈希，没有下划线豁免字段。JSON 重复键必须拒绝。

null 表示明确未知或不适用；缺失表示该 schema 没有提供这个字段；空数组表示已知零个，三者不混用。时间保存源给出的字符串 value 和 precision、zone_known，不擅自推定时区或把日期变午夜。数字时间允许精确十进制字符串+unit，避免浮点差异。

有序数组保持顺序：content、native_parent_ids、text_parts、replacements。集合数组：evidence、roots、inputs、outputs、members、parents、from_versions、to_versions 按链接 CID binary 升序并去重；validator 必须拒绝未排序集合，不能静默修改。其他数组必须在扩展 schema 声明顺序语义。

对象存为 objects/<CID>.cbor；可附同名 .json 方便人读，但只作投影，必须重新编码与 .cbor/CID 一致。raw 位于贡献者 raw/<CID>.bin；网络传输须有用户对目的地的授权。本轮用户已明确授权通过现有个人 OneDrive 从 Mac 同步到 Windows，不表示公开发布。封装和索引可改变，CID 绑定的是解包后的单对象字节。数据库/缓存不是唯一权威副本。

## 3. 核心对象（schema=pkst/<type>@0.1）

字段表是初版最小契约；未知扩展字段必须有 namespaces，不能改变既有字段含义。

| type | 必需字段 | 约束 |
|---|---|---|
| source | platform, namespace, native_thread_id | 稳定来源锚点；namespace 是明确记录的账户/来源别名；不含标题、文件路径、导入时钟或整文件 hash |
| content | media_type, text | 原生文本使用固定值 text/plain;charset=utf-8，内容保持原样；结构块用明确 projection 对象，不把 JSON 重序列化称为原文 |
| occurrence | source(link), native_id(null允许), locator(null允许), native_role, actor_kind, process_kind, content(有序links), native_parent_ids(有序strings或null), event_time | native_id 或 locator 至少一项存在；native_id 是原来源 ID，不是正文 hash；父关系未提供时为null，明确无父时为空数组；actor_kind=human/ai/tool/system/unknown；process_kind=main/sidechain/compaction/injected/unknown；无法确认用户作者时用 unknown |
| concept | label, definition, evidence, asserted_by, lineage | lineage 可 null，后续版本可引用 genesis CID；同名不自动等价 |
| statement | text, force, holder, evidence, asserted_by, lineage | force=assert/question/hypothesize/rhetorical/quote/directive/unknown；lineage 可 null；holder 不因 sender=user 自动设为用户 |
| relation | predicate, from(link), to(link), evidence, asserted_by, basis, scope | basis=explicit/source-structure/inferred/recollection/unknown；精确指向版本；不自动沿谱系继承 |
| change | operation, from_versions, to_versions, evidence, asserted_by, basis, reason | operation=revise/extend/narrow/rename/split/merge/retract/editorial-consolidate；思想变化和档案整理明确区分 |
| assessment | target(link), judgment, asserted_by, evidence, recorded_at | judgment=accept/reject/uncertain/retract/verify-pass/verify-fail；验证通过不是内容真理或用户采纳 |
| activity | operation, recorded_at, actor, inputs, outputs, implementation, coverage | 记录 import/extract/integrate/observe；inputs/outputs 链接已生成对象，不能与输出对象形成循环 |
| snapshot | parents, roots, coverage, protocol | 固定对象成员与父快照；根不声称全平台完整 |

event_time={value:string或null,format:rfc3339/epoch-decimal/source-text/unknown,precision:second/millisecond/microsecond/day/month/year/unknown,zone_known:bool,unit:s/ms/us/null}。format=epoch-decimal 时 unit 必须非空且 value 是源值的精确十进制字符串；其他格式 unit=null。未知时间 value=null, format=unknown, precision=unknown, zone_known=false。epoch 是 UTC 时间轴；源时区缺失的 source-text 不推定时区。actor/asserted_by/holder 使用 {kind:human/ai/tool/system/unknown,id:string}，实际模型仅在来源确实提供时记录。活动是本轮观察，不伪装成历史发生。

locator 的无 native-ID 策略：{raw:link,start:integer,end:integer,coordinate:"decoded-jsonl-utf8-bytes"}；压缩原件的 raw CID 绑定压缩 bytes，区间针对明确解码得到的 UTF-8 JSONL。同一来源随追加而换 raw CID 时须以独立 occurrence-equivalence 候选关联，不能声称该 fallback 跨导出稳定。

有 native-ID 的事件不把整文件 raw CID/路径放进其身份对象，避免追加导致全部历史身份变动。另以 extraction-record（见下一段）把每个 occurrence 锚定到原始字节和 parser 版本。native ID 相同但内容改变会产生不同对象版本；事件键相同可报告修订/冲突，绝不覆盖。

扩展取证对象 extraction-record：schema=pkst/extraction-record@0.1，raw(link), occurrence(link), coordinate, parser, role_basis，以及坐标专用字段。coordinate=decoded-jsonl-utf8-bytes 必须有 start,end，使用字节半开区间 [start,end)，不含末尾 LF，若存在 CR 则包含 CR；尾行 end=固定前缀长度。coordinate=json-pointer 必须有 pointer，禁止 start/end；其原件必须是完整单一 JSON 文档。解析异常只记录错误，不输出该行的正常 occurrence；原始 bytes 仍接收。不把任意前后相邻记录伪装为回复链；保存 parentUuid/native parent ID，即使其目标暂缺也记录缺口。

非文本结构块使用 schema=pkst/projection@0.1：native_type, profile, text。它是明确的派生投影，不是原文。初版适配器 profile=python-json-v1，使用 Python 标准 json.loads 后 json.dumps(ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)，实际 Python 版本记入活动；须有平台固定样例验证跨版本一致，不声称任意语言默认 JSON 输出一致。字符串不规范化，重复键或非有限数解析失败。投影对象不包含整文件hash，原件取证锚存于 extraction-record。

reasoning/thinking/加密块不提取正文，用 schema=pkst/opaque-block@0.1：native_type, profile=python-json-v1, digest（上述投影 UTF-8 bytes 的 sha256 十六进制）, handling=raw-only。不得解密或把隐藏推理列为言论。图片/二进制也可按 opaque-block 保存指纹，原始数据留 raw。queued_command 可另提取其明文提示为 content，原队列动作仍保留。occurrence.content 是保持源块顺序的 content/projection/opaque-block 链接序列；尚缺原件附件时须列为 missing，不能编造内容。非文本块的白名单/类型映射属于各平台适配器版本。

补充 schema=pkst/block-reference@0.1 是独立取证对象：raw(link), occurrence(link), ordinal（源块位置）, coordinate, start/end（JSONL区间）或 document_pointer（单一JSON文档）, pointer（相对记录的JSON Pointer）, native_type；它不得被 occurrence 反向引用，否则整文件追加会改变事件身份。渲染/检索默认只展示 content 文本，projection 和 opaque-block 是另行查看的技术材料。

原生 user/human 字段只证明来源通道，不能证明是用户本人输入；Computer Use 协调消息是实际反例。actor_kind=human 需可验证的人类来源或用户 assessment。普通 user 通道默认 unknown，后续 assessment 可增加归属，不改写原始事件。PKST JSON 投影的重复键拒绝；原始来源的重复键记录该行解析失败，不能拒收整个来源。

### 3.1 来源身份映射

| platform | namespace | native_thread_id |
|---|---|---|
| codex-local | owner-openai-account | session_meta.id，旧版本允许有明确依据的 session_id；子代理保持其原生会话ID |
| chatgpt | owner-openai-account | 官方导出 conversation.id；无原生ID时不得拿标题代替 |
| claude-code | owner-claude-account | 主会话 sessionId；子代理有 agentId 时为 sessionId/agent-agentId（后半 agentId 为实际值） |
| claude-ai | owner-claude-account | 官方导出 conversation.uuid；待真实导出验证字段 |
| gemini | owner-google-account | 官方导出明确给出的对话ID或原生 conversation URL ID；活动记录缺失ID时保留缺口，不能推定相邻事件同一会话 |

上述别名只对应本轮用户自己的账户；多个账户时须另登记 namespace，不能合并。设备、路径、标题另记于采集清单。原生ID缺失时使用明确 raw+位置的fallback，不伪造全局稳定身份。

## 4. 关系与历史视图

初版 predicate：reply-to、quotes、pasted-at、propagation-candidate、part-of、about、instance-of、specializes、depends-on、implies、explains、analogous-to、supports、contradicts、counterexample-to、answers、applies-to、influenced-by、restated-in、equivalent-within-scope、occurrence-equivalence、consolidates、derived-from。

文本匹配仅产生 propagation-candidate，150字符/Jaccard0.5 可作待验证启发式参数，不能确定原创、复制方向或因果。pastedContents 只证明粘贴行为，不证明来源作者。关系指向具体版本；继承必须另有 revalidation/assessment，默认不自动继承。

历史视图同时接收 event_cutoff 与 recorded_cutoff。只用材料出现时间不能把后来形成的理论倒填到最早证据时间。合并/撤回/采纳也有自己的事件与整理时间。未知时间保持未知，多头谱系是允许状态，不强制合一；缺口、错误解释、反例和未采纳 AI 建议可见。

内容寻址的对象依赖图和快照父图必须是 DAG；语义关系图可以有相互支持、反驳等环。语义边由独立 relation 对象引用已有节点，因此不会强迫思想只属于一棵树。思维导图是所选主题/关系的可重建投影，不是权威结构。change/revise 必须同时有非空 from_versions/to_versions；retract 可以为空 to_versions；整理合并不得冒充用户思想变化。snapshot.protocol 必须链接协议文件原始字节的 raw CID。

## 5. 来源采集与覆盖

保留原始二进制，正式取证先固定字节，再解析。活动中的 JSONL 记录抓取起点大小的固定前缀，保留最后不完整行，报告 snapshot-prefix/partial-tail；不能读取到不确定的无限增长尾部。压缩文件复制前后比较 size/mtime/hash；变动时保存失败与重试记录，不默默覆盖。同一完整 snapshot 重导入应复用相同 evidence 对象；新活动时钟允许产生新 activity。

原始层保存所有源 bytes。自然语言 occurrence 至少包括用户与 AI 正文；系统指令、工具结果、sidechain、压缩摘要、排队合并记录另分类，不当作用户言论。无需复制授权凭据、auth、token 或全应用配置。解析失败记录文件、位置、错误类型并继续其他独立来源，不能吞掉错误或以空结果冒充成功。

coverage 每来源列 present/exported/parsed/partial/unavailable/unknown，包含固定扫描路径、格式、计数、解析失败、缺失附件、缺少父消息、导出分支限制。native 导出、API 摘要、DOM 转录必须标明不同保真级别。任何“全量”只相对所声明的账户/时间/路径/导出窗口。

## 6. 隐私与协作

个人语料均暂为 local-only。原文不直接提交远端；脱敏生成独立派生对象，显式原始链接/替换规则/区间。工作副本不改变访问权限。默认追加不妨碍用户删除其私密材料；删除导致证据不可用必须可见。用户关于自己立场的确认优先，不意味着其陈述自动成为世界事实。

不擅自更改 Claude cleanupPeriodDays 等应用配置；先在授权新目录保存固定来源。云端采用已有登录和官方导出路线；需要用户邮箱下载/登录时清晰列出阻塞，继续其他来源。

## 7. 冻结与验收

物理封装可采用标准 CARv1：header 是 {version:1,roots:[CID]} 的 DAG-CBOR；header 和后续 CID+block 段分别用 unsigned LEB128 长度前缀。单对象 CID 不随打包改变。若原始大块另存在 raw 目录，CAR 必须声明 external-raw，并逐引用核对外部块；单有根 CID 不证明包的引用闭包。此方式避免数十万小文件，SQLite 仅作可重建索引。参考 https://ipld.io/specs/codecs/dag-cbor/spec/ 与 https://ipld.io/specs/transport/car/carv1/。

双方独立编码器核验同一组静态向量，检查 Unicode、CRLF、null/缺失/空、整数边界、map 键序、CID links、集合数组、损坏 CID。源导入必须通过：重复导入、同文不同事件、native parent 分叉、sidechain/注入/压缩摘要归属、截断尾行、原文锚定、损坏块拒绝。结构验证不宣称思想提取正确；语义抽取另做固定样本的独立审阅。

原始23个编码向量只验证编码，不是可直接复制的业务对象模板；其中带空格的旧 media_type 与 revise/to_versions=[] 均不是 N3 有效业务对象。其期望字节不改，新增业务向量单独版本化。

构造选择：常见路径是 JCS+动态JSON/向量库；最小路径是固定类型的 DAG-CBOR、按源流式解析、可重建索引；验证优先路径增加双方独立编码器与负例。采用后两者组合，先限制类型再独立验证，避免引入大型基础设施；性能/能耗收益须实际计量，不作预先承诺。
