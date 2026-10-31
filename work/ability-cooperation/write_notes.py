"""Record the explicit conceptual revision without overwriting historical claims."""
import json
from datetime import datetime,timedelta,timezone
from prepare import ARCHIVE, OLD, OUT, sha, write_json

def notes():
    assert not (ARCHIVE/'report.json').exists()
    current=json.loads((OUT/'00-sources.json').read_bytes())
    historical=json.loads((OUT/'00-historical-sources.json').read_bytes())
    byref={e['ref']:e for e in historical+current}
    def excerpt(ref,start,end=None):
        text=byref[ref]['text'];a=text.index(start);b=text.index(end,a) if end else len(text.rstrip())
        return {'ref':ref,'source_span':[a,b],'quote':text[a:b],'sha256':sha(text[a:b].encode())}
    before=excerpt('CIVILIZATION-REPLY','而人的任何一种需求和任何一种能力','我们要防止的是')
    after=excerpt('AUTHOR-REVISION','所以重要的不是')
    acceptance=excerpt('AUTHOR-REVISION','是的，我同意你的修正','实际上')
    revision={'schema':'pkst-editorial/author-revision@1','before':before,'after':after,
        'acceptance':acceptance,'authorization_ref':'INTEGRATION-REQUEST',
        'scope':'作者明确承认先前表达过于绝对，将重点从能力逼近正态分布转向不同能力的有效合作。',
        'retained':['公平的培养与基本生活条件','自由探索与因材施教','减少资源累积导致的支配风险'],
        'current_emphasis':['能力结构多样性','能力互补与信任','跨领域深度合作'],
        'not_inferred':['作者否定所有正态分布经验假说','作者逐句认可本轮新增编辑文字','新机制已得到实证验证','特定基因已被证明决定个人的专才或通才角色']}
    write_json(OUT/'author-revision.json',revision)
    stages=[
      ('CIVILIZATION-REPLY','以正态分布与非资本式积累解释不会出现支配节点','historical-author-proposition',before),
      ('ABILITY-RESOURCE-REPLY','指出资源和资本参与能力的训练与形成','historical-author-refinement',excerpt('ABILITY-RESOURCE-REPLY','因为人类个体对象的','你可以看一下')),
      ('EDITION-ELEVEN-RESPONSE','AI区分资源形成机制与普遍正态结论','assistant-editorial-response',excerpt('EDITION-ELEVEN-RESPONSE','仍须区分：','已写入')),
      ('DEVELOPMENT-GOALS','作者提出公平发展与自由探索目标，仍尝试推导综合能力分布','author-intermediate-proposal',excerpt('DEVELOPMENT-GOALS','我的回答是','\n\n这样的话')),
      ('GOALS-REVIEW','AI补充相同时间、增长率与综合能力计量的区别','assistant-editorial-response',excerpt('GOALS-REVIEW','我认为，','你这次论述中')),
      ('AUTHOR-REVISION','作者明确接受修正，转向能力互补与跨领域合作','author-confirmed-conceptual-revision',after),
      ('COOPERATION-SYNTHESIS','AI整理深入研究、跨域连接及技术支持的分工','assistant-editorial-synthesis',excerpt('COOPERATION-SYNTHESIS','它们是任务中的不同角色','\n\n例如')),
      ('INTEGRATION-REQUEST','作者要求按最新理解入书、保存思想修正并同步GitHub','explicit-editorial-authorization',excerpt('INTEGRATION-REQUEST','请把最近'))]
    rows=[]
    for i,(ref,title,status,quote) in enumerate(stages,1):
        e=byref[ref];local=datetime.fromisoformat(e['time'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8)))
        rows.append({'id':'E'+str(i).zfill(2),'ref':ref,'title':title,'status':status,'role':e['role'],
            'time':e['time'],'display_time_hong_kong':local.isoformat(),'occurrence':e['occurrence'],
            'content':e['content'],'source_object':e.get('source_object'),**quote})
    relations=[]
    for left,right in zip(rows,rows[1:]):
        relation='explicit-author-revision' if right['ref']=='AUTHOR-REVISION' else 'discussion-progression'
        relations.append({'from':left['id'],'to':right['id'],'relation':relation})
    relations.append({'from':'E01','to':'E06','relation':'author-revises-central-premise',
                      'evidence_ref':'AUTHOR-REVISION'})
    write_json(OUT/'07-thought-evolution.json',{'schema':'pkst-editorial/discussion-evolution@1','stages':rows,
        'relations':relations,'boundary':'Native message time and visible discussion progression; no claim of first invention or proved social causation.'})
    md=['# 从分布前提到能力互补的思想修正',
        '作者在2026年10月31日明确接受对先前绝对化表述的修正，并在随后授权按最新理解入书。本文记录实际发生的讨论；正文呈现最新理解，历史原话不被改写。',
        '## 时间线\n\n以下显示香港时间（UTC+08:00）；原生UTC时间、角色、内容身份与引用范围保存在同名JSON中。',
        '| 时间 | 发言方 | 内容及状态 |\n|---|---|---|']
    for row in rows:md[-1]+='\n|'+row['display_time_hong_kong'][11:23]+'|'+('作者' if row['role']=='user' else 'AI')+'|'+row['title']+'|'
    md.append('```mermaid\nflowchart TD\n  A[原先以分布推导不支配] --> B[资源参与能力形成]\n  B --> C[公平发展与自由探索]\n  C --> D[讨论增长率与总能力的条件]\n  D --> E[作者明确接受修正]\n  E --> F[能力多样性与跨领域合作]\n  A -. 核心前提被修订 .-> E\n  F --> G[授权入书与公开归档]\n```')
    md.append('箭头表示讨论承接或明确修订，不表示已经证明的现实因果。')
    for row in rows:
        md.append('## '+row['id']+'　'+row['title']+'\n\n原生时间：'+row['time']+'；角色：'+row['role']+'。\n\n'+row['quote']+'\n\n内容 CID：`'+row['content']+'`。')
    md.append('## 修正的范围\n\n'+revision['scope']+'公平的发展条件、自由探索与减少支配风险的诉求继续保留；并未把所有先前讨论整体否定，也未把任何新的编辑句子自动视为已获作者逐句确认。')
    (OUT/'07-thought-evolution.md').write_bytes(('\n\n'.join(md)+'\n').encode())
    previous=json.loads((OLD.parent/'external-sources.json').read_bytes())
    external=[{**item,'reuse_scope':'Citation and bounded interpretation retained from edition eleven; no new full-paper review claimed in this editorial pass.'}
              for item in previous if item['id'] in ['S2','S3']]
    external.append({'id':'INHERITED-BITCOIN','title':'Bitcoin: A Peer-to-Peer Electronic Cash System',
        'url':'https://bitcoin.org/bitcoin.pdf','reuse_scope':'Unchanged protocol-scope paragraph inherited from editions ten and eleven; no new safety claim or review.'})
    write_json(OUT/'external-sources.json',external)
    (OUT/'04-editorial-notes.md').write_bytes('''# 公平发展与能力合作的编辑说明

第十二版按作者最新明确确认的理解，重写动态权重章节中的相关小节，并调整紧随其后的按需保障段落。新节以公平的发展条件、能力多样性和跨领域合作为中心。两处替换之外保留第十一版的字节；书末自我反思附录保持原样并继续位于最后。

## 原话保留与角色区分

本轮新增三条作者发言、三条AI公开最终答复；另引用两条已归档的早期作者发言。来源角色、原生时间与完整文本分别保存，不将AI的建议记作作者原话。人类与AI来源片段的文字保留统计分别计算，不把它们合并宣称为作者原文比例。

作者关于两个发展目标、偏好与专注方式差异、“偏科但造诣极高”“样样都懂”，以及不再以能力逼近正态为重点的核心表述，尽量保留在正文。早期仍试图用相同时间推导综合能力分布的整段原话，保留在来源和演化记录中，不再当成正文当前结论。

完整原话的语气不被追溯修改。独立书稿去掉“我同意你的修正”等会话指向，由来源账本和思想时间线保存这次主动修正的历史。

## 具体编辑判断

1. 公平条件不被写成取消一切知识或技能的有益积累；改为减少不公平的外部资源累积对成长的影响。
2. “准确判断自身的基因”调整为逐步认识自身特点和特长。正文描述偏好与专注方式的差异，不断言特定遗传机制已被证明，也不将人固定划为生物学上的专才或通才两类。遗传假说的原话完整保留。
3. 作者已明确修订的是制度论证的重点。新的文本不要求综合能力服从某一种分布，也不声称作者否定了一切关于分布的经验研究。
4. 跨领域分工、储能设备的例子、可接替的协调过程与技术支持来自前一轮AI建议及本轮编辑补写。接受核心修订不等于逐句接受这些补写。
5. AI解释、Merkle-DAG追溯与动态权重协作写为设计方向；没有据此声称已经部署完整协作系统或验证制度优越性。
6. 保留按需保障、任务判断和执行授权的区分，以及账本安全条件的范围。新机制的评价转向实际成长机会、沟通、复核和接续合作的表现。

## 可追溯的编辑与思想变化

05开头的文件保存替换前的原段落，06开头的补丁保存本次实际修改。passage-manifest.json记录每个成文单元，revision-manifest.json支持按字节重放和逆向恢复。

07-thought-evolution.md及同名JSON记录八个讨论阶段，author-revision.json保存原先命题、作者明确接受修正的原句和当前核心句。Merkle-DAG中将同时记录书稿版本修改、讨论承接和作者明确修订；它们不是同一种关系。

核验覆盖来源、角色、时间、引用身份、文字重放、两处替换及附录位置。既有研究引用沿用前版已读材料及其适用范围，本轮没有新增实验或证实遗传与能力分布假说。
'''.encode())
    write_json(OUT/'construction-choice.json',{'scope':'One manuscript section, one adjacent alignment paragraph, explicit author revision and source archive.',
        'candidates':[{'path':'append-current-chat-to-book','limitation':'Leaves superseded premises in current prose.'},
                      {'path':'replace-entire-book-or-build-new-publisher','limitation':'Unnecessary rewriting and framework cost.'},
                      {'path':'two-reversible-replacements-with-explicit-revision-links','limitation':'Requires source-span and old-byte checks before activation.'}],
        'selected':'two-reversible-replacements-with-explicit-revision-links',
        'cost_basis':'Reuse current codec, catalog and public API; no measured energy claim.'})

if __name__=='__main__':notes()
