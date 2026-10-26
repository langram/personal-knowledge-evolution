# 公开格式与来源规则

原档案使用 [PKST](../archive/protocol/PKST-0.1.md) 的 DAG-CBOR、CIDv1、SHA-256。公开数据以 JSONL 提供，JSON 对象经过同一规范编码即可重新计算 CID。

`corpus/objects/*.jsonl` 每行包含 `cid` 和 `object`。文件名仅用于分片，不是对象身份。`corpus/events/*.jsonl` 是便于建立索引的事件目录，事件正文仍由内容对象提供。

## 公开对象

- `pkst/content@0.1`、`pkst/source@0.1`：无需修改的原对象保留原 CID。
- `pkst-public/content@1`：需要脱敏或 HTML 转纯文本的内容，拥有新的 CID，保留原对象 CID 和转换说明。
- `pkst-public/event@1`：公开事件，保留原发言 CID、角色、时间、父消息 ID 和公开内容引用。原始备份取证位置只在本地档案保存。
- `pkst-public/editorial-object@1`：概念、论断、关系、稿件版本等既有对象的公开投影；内部的原档案链接可能指向未公开对象，不能误认为完整原始引用闭包已上传。

这些公开 schema 使用有序数组；对象 ID 由规范 DAG-CBOR 的 SHA-256 生成。原始内容 CID 与公开事件 CID 不同，是明确转换的结果。CID 校验只确认字节身份。

## 两种版本历史

Git 跟踪公开文件、程序和书稿的变化。Merkle 对象及来源清单保留语义关系、发言身份与原生时间。Git 提交的导入日期与原生发言时间是不同字段；不能用新建 Git 提交的时间倒推思想产生日期。

[文件清单](../publication/files.json) 对公开文件记录 SHA-256，并以二叉 Merkle 树合并叶子。叶子为 `SHA256(0x00 || UTF8(path) || 0x00 || bytes.fromhex(file_sha256))`，按路径排序；内部节点为 `SHA256(0x01 || left || right)`，单数节点复制末节点。清单本身不参与自己的根。

`omitted-events.json` 逐条记录没有进入公开事件集的原发言身份及原因。`redactions.json` 记录发生转换的内容身份和字段类型，不公开凭据原值或单独的密码哈希。完整原件仍在作者本地保存。

历史构稿脚本保留其原始输入约定，部分需要本地原件才能重跑；公开阅读和 API 使用 `pkst_public`，不依赖这些私有输入。
