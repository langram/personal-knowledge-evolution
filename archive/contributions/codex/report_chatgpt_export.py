"""Generate local, rebuildable navigation from verified source objects; no new beliefs."""
import json,sqlite3
from collections import Counter
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from pathlib import Path
from pkst_codec import cid

BASE=Path(__file__).resolve().parents[2];ROOT=BASE/'contributions/codex/chatgpt';REPORTS=BASE/'reports';HK=timezone(timedelta(hours=8))

def clock(value):
    if value is None:return '未知'
    return datetime.fromtimestamp(float(Decimal(str(value))),HK).strftime('%Y-%m-%d %H:%M:%S')

def md(value):return str(value).replace('|','&#124;').replace('\r',' ').replace('\n',' ')

def main():
    report=json.loads((ROOT/'import-report-v1.json').read_text(encoding='utf-8'));accepted=json.loads((ROOT/'catalog-acceptance-v1.json').read_text(encoding='utf-8'))
    capture=json.loads((ROOT/'capture-current.json').read_text(encoding='utf-8'));members=[json.loads(x) for x in (ROOT/capture['manifest']).read_text(encoding='utf-8').splitlines()]
    anchors=json.loads((BASE/report['anchors']).read_text(encoding='utf-8'));lookup={(x['thread'],x['node']):x for x in anchors['anchors']}
    conversations=[];selected={};terms=['数据主权','动态权重','决策网络','个人需求','集体资源','自由区','新体制','自我实现','Merkle','merkle','文明','开源','云存储'];hits=[]
    selections={
      'e8e4846f-ec63-4013-a559-fe2f261bc3c5':('个人＋AI与社会神经网络','而我现在正在做的这些事情，其实就是在准备好这个想法' ,'这些技术项目被放在同一文明组织愿景中，涉及个人与 AI、公共知识、交互入口和资源分配。'),
      '0ec4031c-148f-4053-95e0-1521b04723d0':('从种子到兼容接管旧生态','再接下来，可以替代过去传统商业模式下的互联网服务','提出先包装旧对象、逐步替换内部实现，再扩展服务和硬件生产的路径。'),
      'cbc1abbc-3d5c-4e3d-bba2-d4429b0fd652':('REA、两类分配与温和过渡','帮我把这个白板上我写的内容整理一下','把接口兼容、个人需求与共同资源的区别、动态决策及非暴力过渡放在同一段表述中。'),
      '4ef5812a-0d8b-4464-b7fa-61e81ccf9863':('自我实现的科幻作品','关于自我实现的科幻作品的设想','提出文学、影视创作与现实协作项目并行的世界观；其中外星文明、永生等为科幻设定，不是现实事实。')}
    for member in members:
        if member['member_name'] not in report['shards']:continue
        for ci,c in enumerate(json.loads((ROOT/'raw'/(member['raw_cid']+'.bin')).read_bytes())):
            counts=Counter();matches=[]
            for nk,node in c['mapping'].items():
                m=node['message']
                if m is None:continue
                typ=m['content']['content_type'];role=m['author']['role'];counts['records']+=1;counts[role]+=1
                if typ in ('thoughts','reasoning_recap'):counts['opaque']+=1;continue
                textparts=[p for p in m['content'].get('parts',[]) if isinstance(p,str)]
                if role=='user':
                    found=sorted({t for t in terms for p in textparts if t in p})
                    if found:matches.append({'native_id':m['id'],'terms':found,'occurrence':lookup[(c['id'],nk)]['occurrence']})
                if nk in selections:
                    # Selected source has one native text part; no joined/reconstructed quotation.
                    assert len(textparts)==1
                    selected[nk]={'title':c['title'],'thread':c['id'],'message':m,'text':textparts[0],'anchor':lookup[(c['id'],nk)],'raw':member['raw_cid']}
            conversations.append({'thread':c['id'],'title':c['title'],'created':c['create_time'],'updated':c['update_time'],'counts':dict(counts),'raw':member['raw_cid'],'pointer':'/'+str(ci)})
            if matches:hits.append({'thread':c['id'],'title':c['title'],'messages':matches})
    assert set(selected)==set(selections) and len(conversations)==431
    (ROOT/'.private/conversation-navigation-v1.json').write_text(json.dumps(conversations,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'.private/theory-retrieval-candidates-v1.json').write_text(json.dumps({'terms':terms,'scope':'user-channel native text; literal hits only','matches':hits},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# ChatGPT 会话目录','', '2026-10-26 从已验证官方导出生成。本表按会话创建时间排列；香港时间仅作显示，原生时间精度保存在对象与原件中。记录数含推理标记，非思想数。最后更新时间是来源字段，不能证明所有内容均在该时刻产生。','', '[返回导入报告](chatgpt-import-20261026.md)','', '| 会话标题 | 创建时间（香港） | 来源记录 | user 通道 | assistant 通道 | 其中推理类 |','|---|---|---:|---:|---:|---:|']
    for c in sorted(conversations,key=lambda x:(x['created'] is None,x['created'] or 0,x['thread'])):
        ct=c['counts'];lines.append(f"| [{md(c['title'])}](#c-{c['thread']}) | {clock(c['created'])} | {ct.get('records',0)} | {ct.get('user',0)} | {ct.get('assistant',0)} | {ct.get('opaque',0)} |")
    lines+=['','## 原件定位','', '`.bin` 是按原字节保存的 JSON 分卷；JSON Pointer 定位到对应会话。打开时按文本查看，不执行来源内容。','']
    for c in conversations:
        lines += [f"<a id=\"c-{c['thread']}\"></a>",f"### {md(c['title'])}",'',f"会话 ID：`{c['thread']}`；创建：{clock(c['created'])}；最后更新：{clock(c['updated'])}。",'',f"[原始 JSON 分卷](../contributions/codex/chatgpt/raw/{c['raw']}.bin)，JSON Pointer：`{c['pointer']}`。",'']
    (REPORTS/'chatgpt-conversations-20261026.md').write_text('\n'.join(lines),encoding='utf-8')
    lines=['# ChatGPT 新体制相关材料入口','', '2026-10-26。以下为本次检索后选出的四条相关材料，不是最早起源证明，也不是全库思想提炼。编辑说明由 Codex 撰写；引文保留原字符并给出精确位置。user 通道不单独证明每一段都是本人原创，尤其跨 AI 粘贴文本需要另行区分。','', '[返回导入报告](chatgpt-import-20261026.md) · [已有整体框架](../dossiers/2026-10-25-seed/02-framework.md) · [已有思想演化](../dossiers/2026-10-25-seed/03-evolution.md)','',f'固定关键词扫描涉及 {len(hits)} 个会话、{sum(len(x["messages"]) for x in hits)} 条 user 通道消息。这个宽泛召回包含无关项，不能称为相关思想数量；下列四条已实际阅读。','']
    quote_manifest=[]
    for nk,item in sorted(selected.items(),key=lambda kv:kv[1]['message']['create_time']):
        label,startphrase,note=selections[nk];text=item['text']
        if nk=='e8e4846f-ec63-4013-a559-fe2f261bc3c5':startphrase='而我现在正在做的这些事情，其实就是在准备好这个设想'
        start=text.index(startphrase)
        if nk=='cbc1abbc-3d5c-4e3d-bba2-d4429b0fd652':end=len(text)
        elif nk=='4ef5812a-0d8b-4464-b7fa-61e81ccf9863':end=text.index('大概框架是')
        else:
            stop=text.find('\r\n\r\n',start);end=stop if stop!=-1 else min(len(text),start+400)
        quote=text[start:end];a=item['anchor'];content=cid(__import__('pkst_codec').encode({'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':text}))
        # Verify quote is anchored in the active catalog's exact native content.
        pointer=json.loads((BASE/'contributions/codex/catalog/current.json').read_text());db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
        assert db.execute('SELECT text FROM content WHERE cid=?',(content,)).fetchone()[0][start:end]==quote;assert db.execute('SELECT 1 FROM parts WHERE occurrence=? AND content=?',(a['occurrence'],content)).fetchone();db.close()
        lines += [f'## {clock(item["message"]["create_time"])} — {label}','',f'来源会话：**{item["title"]}**。编辑说明：{note}','',*['> '+line for line in quote.splitlines()],'',f"事件 CID：`{a['occurrence']}`。",'',f"[原始 JSON](../contributions/codex/chatgpt/raw/{item['raw']}.bin)，Pointer：`{a['pointer']}`；原文字符区间：`[{start}, {end})`。",'']
        quote_manifest.append({'occurrence':a['occurrence'],'extraction_record':a['extraction_record'],'raw':item['raw'],'pointer':a['pointer'],'content':content,'start':start,'end':end,'coordinate':'unicode-scalar-half-open','quote':quote,'editorial_label':label,'editorial_note':note})
    lines += ['## 对已有框架的补充','', '这些材料把当前讨论连接到更早的技术与组织构想：五月讨论个人与 AI 的社会节点及控制权；十月初提出兼容包装和逐步替代服务；十月十八日明确两类分配与温和过渡；十月二十二日形成自我实现科幻的创作构想。这里记录的是有日期的相关表述序列，尚未据此建立“影响”“原创”或“立场修订”的确定关系。','', '原有 10 月 25 日专题和版本不改写。此次新增来源可供下一次修订引用；本报告是可重建导航，尚非经独立语义审阅的 statement/change 对象。','']
    (REPORTS/'chatgpt-theory-entries-20261026.md').write_text('\n'.join(lines),encoding='utf-8')
    (ROOT/'.private/theory-quotation-spans-v1.json').write_text(json.dumps(quote_manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    text=f'''# ChatGPT 官方导入完成报告

2026-10-26。用户已下载的官方 ZIP 已完成原件保全、全分卷导入、原文核验及统一索引启用。所有操作在本地完成。

[431 个会话目录](chatgpt-conversations-20261026.md) · [新体制相关材料入口](chatgpt-theory-entries-20261026.md) · [统一档案](../README.md)

## 本包覆盖

| 项目 | 结果 |
|---|---:|
| ZIP 大小 | 958,001,574 bytes（约 914 MiB） |
| ZIP 成员 | 369，全部保存并通过 CRC / 字节散列核验 |
| 声明展开总大小 | 1,162,951,426 bytes |
| 聊天 JSON 分卷 | 5，均与官方 export_manifest 对应 |
| 会话 | 431 |
| 原生拓扑节点 | 12,430，其中 431 个空根节点不当作发言 |
| 来源消息记录 | 11,999 |
| user 通道 | 3,724 |
| 普通 assistant 文本/多模态记录 | 4,528 |
| 推理和推理摘要记录 | 3,747，只存原件及 opaque 指纹，不进入言论检索 |
| 含非空文本、可文字检索的消息 | 8,227 |
| 仅有空文本的消息 | 13，仍保留 |
| 纯图片多模态消息 | 12，仍保留，未 OCR |
| 原生父节点分叉位置 | 108 |

消息事件时间范围为 **{clock(report['event_time_min'])} 至 {clock(report['event_time_max'])}（香港）**。它是包内已有消息的最小/最大时间，不是账户历史完整覆盖承诺。导出请求之后新增的内容、已删除或服务未导出的历史是否存在缺口，仍未知。chat.html、账户设置、文件库等保留原件，不重复计为聊天。

## 已标出的缺口

- mapping.parent 与 metadata.parent_id 有 **3,980 次不一致**，两者分别保存；无缺失的 mapping 父节点。未把其中一套关系擅自解释为思想因果链。
- **312 处消息附件引用**中，198 处精确对应包内文件，114 处按本版精确规则未找到。这里是引用次数，不是去重文件数量。
- 文件库共有 **398 条资料记录**，其中 333 条的 file_id 对应包内 `.dat`，65 条未匹配。84 条导出附件名称映射的目标文件均存在。这些不同口径不相加，也不据此断言文件永久丢失。
- 353 个 `.dat` 成员全部按原字节保存；没有执行、解密或自动识别其中内容。

## 整合与验证

当前统一目录为 **212,351 条来源记录**，由此前 200,352 条增加本次 11,999 条。它不是去重后的现实发言数量，更不是思想数量。

每条消息的角色、精确时间、原生身份、原文、两个父字段、元数据、JSON Pointer 均经过独立代码路径重新解析核验；12,066 个块引用、312 处附件引用及全部会话拓扑也通过核验。重复导入稳定、同文不同事件、分叉、精确小数时间、空时间、推理不进入正文、重复 JSON 键和损坏内容检测等检查通过。

新整合过程校验 **61,680 个新块**，检查包含历史的 **777,257 节点引用图**闭包与无环性。旧原件字节沿用此前核验，没有宣称本次重新散列整个旧库。旧快照仍保留，默认检索排除历史版本。

验收时首次发现“8,252 条普通消息都应含文本”的假设错误，断言阻止了切换；重新检查原件区分出 12 条纯图片和 13 条空文本后，修正计数并通过验收。该失败保留在收据中。

跨来源完全相同、长度至少 150 字符的文本候选现有 **42 组**，其中 40 组涉及 ChatGPT。此前为 10 组；本次没有自动合并发言，也没有推断复制方向、作者或用户赞同。全库语义抽取与完整思想图尚未完成。

可在档案目录运行：

```text
python contributions/codex/query_catalog.py --stats
python contributions/codex/query_catalog.py "自我实现" --platform chatgpt --role user --limit 20
python contributions/codex/query_catalog.py "动态权重" --platform chatgpt --limit 20
```

## 收据与身份

- [原件保全收据](../contributions/codex/chatgpt/capture-current.json)
- [导入与 CAR 校验](../contributions/codex/chatgpt/import-report-v1.json)
- [逐字段原文核验](../contributions/codex/chatgpt/verification-v1.json)
- [目录验收与启用收据](../contributions/codex/chatgpt/catalog-acceptance-v1.json)
- [适配格式](../protocol/CHATGPT-EXPORT-0.1.md)

原 ZIP SHA-256：`{report['archive']['sha256']}`。

ChatGPT 来源快照：`{report['root']}`。

当前统一目录快照：`{accepted['snapshot']}`。

本次为 Codex 本地取证与自验证，尚无新的 Claude 独立审阅。没有更改原始下载文件、再次请求导出或上传私人语料。本报告和会话目录为可重建视图，原始字节和 CID 对象仍为权威来源。
'''
    (REPORTS/'chatgpt-import-20261026.md').write_text(text,encoding='utf-8')
    print(json.dumps({'conversation_navigation':len(conversations),'selected_theory_entries':len(quote_manifest),'literal_match_conversations':len(hits),'literal_match_user_messages':sum(len(x['messages']) for x in hits),'status':'reports-written'},ensure_ascii=False))

if __name__=='__main__':main()
