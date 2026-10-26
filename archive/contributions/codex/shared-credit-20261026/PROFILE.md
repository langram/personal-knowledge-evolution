# 共同贡献与及时分享增量归档

沿用PKST 0.1和PKST-CBOR-1。sc命名空间为urn:pkst:editorial:shared-credit:1。新增一个原生发言，复用12个此前来源；user通道不自动证明作者身份。

sc/document@1、sc/chapter@1、sc/passage@1、sc/source@1、sc/source-timepoint@1、sc/web-evidence@1沿用上一版相应pi结构的字段含义。段落previous_passage指向直接前版；版本保留全部原文，新增内容只在第十节。新增语义关系为编辑解释，不是社会机制的实证结果或作者全面采纳。

沿用既有编解码和索引方案，新SQLite视图约1.4GB。正文、对象、引用和检索重放核验后才启用；没有重新导入全库，没有新服务或外部发布。
