import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
DEST=ROOT/'publication/personal-knowledge-evolution'
editions=[
 ('01-initial','2026-10-26-new-principles','01-new-principles.md','初稿'),
 ('02-expanded','2026-10-26-new-principles-expanded','01-manuscript.md','逐章扩充稿'),
 ('03-mathematics','2026-10-26-mathematics-and-contribution','02-new-principles.md','数学与贡献案例'),
 ('04-public-intelligence','2026-10-26-public-intelligence','02-new-principles.md','知识与公共智能融合'),
 ('05-shared-credit','2026-10-26-shared-credit','02-new-principles.md','贡献记录与及时分享扩展'),
]
rows=[]
for key,folder,name,title in editions:
    relative=f'archive/dossiers/{folder}/{name}';data=(DEST/relative).read_bytes()
    rows.append({'edition':key,'title':title,'file':relative,'sha256':hashlib.sha256(data).hexdigest(),
       'cjk_characters':len(re.findall('[\u3400-\u9fff]',data.decode()))})
(DEST/'history').mkdir(exist_ok=True);(DEST/'book').mkdir(exist_ok=True)
(DEST/'book/current.md').write_bytes((DEST/rows[-1]['file']).read_bytes())
(DEST/'history/editions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
text='''# 文章版本与编辑过程

以下顺序来自已经保存的稿件、来源清单、段落对照与 Merkle 版本关系。公开仓库在2026年10月27日开始导入这些材料，Git 提交时间记录导入行为，原生发言时间仍在来源对象中。

|版本|正文汉字|阅读入口|
|---|---:|---|
'''
for row in rows:text+=f'|{row["title"]}|{row["cjk_characters"]:,}|[正文](../{row["file"]})|\n'
text+='''
更早的[整体框架与起步方案](../archive/dossiers/2026-10-25-seed/README.md)保存实践路线、宣传文本和创作计划。

各版本目录同时保留已存在的原话摘录、段落对照、来源时间、编辑说明和归档收据。`work/` 保存构稿与校验脚本，`archive/contributions/` 保存两方协商和验证材料。`book/current.md` 在导入各稿的 Git 提交中依次更新，方便直接查看修订差异。

这是全部现存编辑材料的版本化导入；没有原始记录的临时修改不能补造。用户赞许某一版不自动成为对后续所有补写的采纳。历史收据引用的原始备份和私有索引不随公开仓库发布。
'''
(DEST/'history/README.md').write_text(text,encoding='utf-8',newline='\n')
target=DEST/'tools/publication';target.mkdir(parents=True,exist_ok=True)
for name in ['safety.py','export_public.py','copy_documents.py','finish_documents.py','remove_secret_fingerprints.py']:
    shutil.copyfile(HERE/name,target/name)
coverage=json.loads((DEST/'publication/coverage.json').read_bytes())
scope=f'''# 本次公开范围

原档案当前目录含 {coverage['catalog_events']:,} 条来源记录。本次公开 {coverage['published_events']:,} 条记录，其中会话 {coverage['record_kinds']['conversation']:,} 条、材料 {coverage['record_kinds']['material']:,} 条；另保存 {coverage['editorial_objects']:,} 个理论与编辑对象的公开投影。

未进入公开事件集的 {coverage['omitted_events']:,} 条分别记录在 `omitted-events.json`：包括非会话记录、工具或内部记录，以及没有可公开文本的记录。公开 {coverage['gemini_html_projections']:,} 个 Gemini HTML 回复的纯文本转换。删除、缺失附件和原始采集窗口之外的会话不推定为已取得。

{coverage['redacted_entries']} 个内容条目经过凭据类型的自动脱敏。标记保留字段类型，不公开秘密值或单独的密码哈希。匹配规则及来源到公开内容的映射可查；自动规则并不证明所有可能的敏感信息都已被识别。

本地原件不改写。Git 管理公开正文、各版本、接口与公开对象分片；原始备份身份通过原CID和本地收据关联。可重建数据库不纳入 Git。

仓库公开是作者的明确要求。公开事件集、正文版本与构建程序已经过发布前检查；没有对外启动作者电脑上的HTTP服务。
'''
(DEST/'publication/README.md').write_text(scope,encoding='utf-8',newline='\n')
print(json.dumps({'editions':rows,'coverage':coverage['published_events']},ensure_ascii=False))
