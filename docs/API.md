# 公开知识库访问接口

先在仓库根目录运行 `python -m pkst_public build`。构建过程读取公开 JSONL、逐个校验 CID，再生成本机索引。不会打开作者私有备份中的数据库或原始文件。

## 命令行

```sh
python -m pkst_public search "数据主权" --platform chatgpt --role user --limit 10
python -m pkst_public event <公开事件CID或原始发言CID>
python -m pkst_public object <公开对象CID>
python -m pkst_public stats
python -m pkst_public verify
```

查询使用文字包含匹配，支持中文，不进行语义相似度推断。`--limit` 范围为 1 到 100。结果显示平台、来源、角色、原生时间、原始发言 CID 和片段位置。

## HTTP

```sh
python -m pkst_public serve --port 8765
```

|方法|路径|用途|
|---|---|---|
|GET|`/v1/stats`|来源与公开范围统计|
|GET|`/v1/search?q=动态权重&limit=10`|检索；可加 `platform`、`role`|
|GET|`/v1/events/<CID>`|以公开或原始发言 CID 读取正文和出处|
|GET|`/v1/objects/<CID>`|读取已公开的内容寻址对象|
|GET|`/v1/threads/<source-CID>?limit=20&offset=0`|分页读取一个来源内的事件|
|GET|`/v1/editions`|文章现存版本目录|

响应为 UTF-8 JSON。无效参数返回 400，未公开或不存在的对象返回 404，未建立索引返回 503。没有写入、上传、执行代码或任意读取本机文件的接口。

默认只监听本机回环地址。本项目没有代替使用者部署一个公网服务器。对外部署时的网络入口与访问策略由部署者另行管理。

## 时间、分支和来源

原生时间字段原样保留。已知时间用于排序，未知时间置后，同一排序时间按 CID 排列；这个顺序不冒充完整的回复顺序。原始父消息 ID 保存在事件对象中，缺失保持未知。

`user` 或 `human` 仅表示来源通道，不能自动证明作者身份。`material` 表示项目材料、来源中的自动记忆或提示历史，与对话正文分别标记。AI 回复保留 AI 身份，不自动转换成作者观点。
