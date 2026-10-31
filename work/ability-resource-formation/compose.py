"""Compose edition eleven as one reversible, source-mapped section replacement."""
import difflib
import json
import re
from prepare import ARCHIVE, BASE, OLD, OUT, sha, write_json

TITLE = '需求、能力与决策权重，为什么不能成为新的资本'
REF = 'ABILITY-RESOURCE-REPLY'

def compose():
    assert not (ARCHIVE/'report.json').exists(), 'Archive frozen; do not rewrite it.'
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    source=next(e for e in events if e['ref']==REF)['text']
    previous=(OLD.parent/'05-weight-and-integrity.md').read_bytes()
    old=OLD.read_bytes(); assert old.count(previous)==1
    prior=previous.decode(); paragraphs=prior.strip().split('\n\n')
    assert len(paragraphs)==7 and paragraphs[0]=='### '+TITLE
    items=[]
    def add(text,kind='editorial-addition',**extra):
        items.append({'id':'P'+str(len(items)+1).zfill(2),'kind':kind,'text':text,
                      'basis_refs':[REF],'author_acceptance':False,**extra})
    def inherited(text):
        at=prior.index(text)
        add(text,'inherited-text',baseline_section_span=[at,at+len(text)],basis_refs=[])
    def adapted(start,end,text):
        a=source.index(start);b=source.index(end,a)
        original=source[a:b];edits=[]
        for tag,i,j,k,l in difflib.SequenceMatcher(None,original,text,autojunk=False).get_opcodes():
            if tag!='equal':edits.append({'operation':tag,'source_span':[a+i,a+j],
                                          'before':original[i:j],'after':text[k:l]})
        add(text,'source-adaptation',ref=REF,source_span=[a,b],source_sha256=sha(original.encode()),edits=edits)
    inherited(paragraphs[1])
    add('#### 观察能力差异之前，先问能力是怎样形成的','heading')
    adapted('因为这些所谓的','因为人类个体对象的',
      '对职业绩效发现明显偏离正态分布的研究结果，并不能直接成为“在排除资源累积差异之后，人的能力和需求仍然不服从正态分布”的证据。相反，我提出的一个需要检验的解释是：这种偏离，可能恰恰与资本、资源等可复利累积的因素有关。')
    adapted('因为人类个体对象的','你可以看一下',
      '因为人类个体的能力训练和获取过程中，资源和资本等可复利累积的资源起到了很大的作用，而旧体制下许多个体可以获得的培养资源，受到这种累积规则的影响。在这种背景下成长起来的人类个体，其能力本身就可能被资源差异持续塑造，形成明显不均衡的分布。')
    add('这里需要再向前追问一步。资源的影响，不只是让两个能力相同的人获得不同的成果和收入，还可能使他们在长期成长后，真的形成不同的能力。一个人从小有充足的学习时间、适合的老师和不断试错的机会，另一个人连进入这个领域的机会都没有，那么多年以后看到的技能差距，不能全部归入两个人最初的生物差异。已经形成的能力差距可以是真实的，它的形成原因却仍然需要解释。')
    add('儿童技能形成研究将早期投入、已有技能和后续学习的相互促进纳入模型，说明能力可以在培养过程中积累。这支持研究成长条件怎样塑造能力，同时也提醒我们：学习本身存在累积效应，不能笼统说能力完全不会积累。[技能形成研究](https://jenni.uchicago.edu/papers/Cunha-Heckman_AER_v97n2_2007.pdf)')
    add('于是，在某些分配规则下，可能出现这样的循环：先获得资源的人，更有条件训练能力；形成的能力帮助他取得成果；成果又带来更多资源与认可。如果后续机会持续偏向已经成功的人，最初不大的差异就可能被放大。社会最后看到的差距，包含了这个过程的产物。只观察最终分布，不能把资源累积的作用与初始能力的作用自动分开。')
    add('荷兰科研资助的一项断点研究发现，初次评审分数接近资助门槛的申请者中，刚获资助者在随后八年取得的其他经费超过刚落选者的两倍。这支持早期机会会放大后续资源差距，并不证明能力本身相差两倍。[科研资助的累积优势研究](https://pmc.ncbi.nlm.nih.gov/articles/PMC5948972/)')
    add('因此，已有职业绩效研究可以描述特定样本的成果分布，却不能单凭这种分布回答：如果培养机会、设备、时间与基本生活保障更公平，人们的能力会怎样分布。关于现有绩效的统计发现，与关于不同制度下能力形成的反事实问题，需要分别研究。把旧条件下产生的差距，直接当作新条件不可能改善差距的证明，就可能把需要解释的结果当成解释本身。[绩效分布研究及其测量对象](https://www.hermanaguinis.com/pdf/PPsych2012.pdf)')
    add('#### 跑跳与高尔夫的比较，怎样成为可以检验的问题','heading')
    adapted('你可以看一下','你觉得我说的',
      '我们可以据此提出一个需要检验的设想：当能力的训练过程越是依赖外部资源，能力的分布就越可能偏离正态分布。比如同样是体育项目，更接近生物基本运动能力的跑跳项目，可能更接近正态分布；越是需要较多资本资源的项目，比如高尔夫、跳伞等，能力的分布可能越不符合正态分布。这里提出的是对训练资源影响的预期，需要在可比较的人群和条件下检验。')
    add('这个设想需要观察谁有机会进入、谁能持续训练，以及同样的支持对不同人产生什么作用。没有接触过高尔夫的人，不能因为没有成绩就被视为高尔夫天赋为零；只观察已经进入职业赛场的人，也不能代表所有人。美国2020年的调查显示，儿童参加有组织体育活动的比例随家庭收入上升而提高。这是机会差异的证据，不是跑跳和高尔夫的能力分布比较。[美国儿童体育参与调查](https://www.cdc.gov/nchs/products/databriefs/db441.htm)')
    add('比较时，还需要把年龄、健康、训练时间、测量方式和参赛筛选等条件记录下来。普通人的跑跳也受到营养、训练和环境影响，高水平竞技更不能只靠生物本能解释。跑完固定距离所用的时间、速度和名次，是不同的指标；统计曲线的形状还会受到指标选择的影响。因此，资源依赖越强是否就越偏离正态，需要专门的数据，不能仅凭项目名称推定。')
    add('一种更有辨别力的做法，是在参与者同意、基本保障不受损害的条件下，逐步扩大训练和设备的可获得性，追踪原本缺少机会的人是否更容易进入、技能是否提高，以及家庭资源与后续表现的联系是否减弱。再比较不同项目对这些变化的反应。这样的结果才更接近回答：改变资源条件，究竟改变了多少能力差距。')
    add('#### 新机制要改变形成差距的条件，也要约束差距转化为权力的规则','heading')
    add('不过，从“资源累积能够塑造并放大差异”，还不能直接推出“消除这种累积之后，所有能力必然严格服从正态分布”。正态分布是关于具体指标、具体群体和具体条件的判断。新的制度可以检验某些差距是否缩小、某些分布是否更加集中，却不必事先规定每条曲线最后都应当长成同一种形状。反过来，没有证实正态分布，也不能成为忽略培养机会不平等的理由。')
    add('需求同样不能从职业绩效推断出来。人的年龄、身体状况、生活任务和环境不同，所需要的资源也不同。一个人在特定阶段需要更多照护，不等于他占有了可以不断支配别人的资本；某种需要暂时高于多数人，也不能只因为偏离统计平均就被判定为不合理。按需分配要辨认实际需要及其满足条件，不能把一条预设的分布曲线当作分配依据。')
    add('所以，我所期待的新机制，要把培养能力所需的知识、工具、训练机会与基本生活保障，逐步变成人人可以实际获得的条件。让已经积累的知识帮助更多人学习，让一个人的成长增加其他人的成长机会，而不是不断提高后来者进入的门槛。这里要区分的是知识和技能的有益积累，与借助资源占有和制度优势不断扩大的支配权。前者应当受到鼓励，并尽可能被分享；后者需要受到规则的限制。')
    inherited(paragraphs[3]);inherited(paragraphs[4]);inherited(paragraphs[5]);inherited(paragraphs[6])
    text='### '+TITLE+'\n\n'
    for item in items:
        a=len(text);text+=item['text'];item['section_span']=[a,len(text)];text+='\n\n'
    block=text.encode();a=old.index(previous);b=a+len(previous);whole=old[:a]+block+old[b:]
    offset=len(old[:a].decode())
    for item in items:item['document_span']=[offset+x for x in item['section_span']]
    (OUT/'01-section.md').write_bytes(block)
    (OUT/'02-new-principles.md').write_bytes(whole)
    (OUT/'05-previous-section.md').write_bytes(previous)
    patch=''.join(difflib.unified_diff(prior.splitlines(keepends=True),text.splitlines(keepends=True),
                 fromfile='05-previous-section.md',tofile='01-section.md'))
    (OUT/'06-section-revision.patch').write_bytes(patch.encode())
    write_json(OUT/'revision-manifest.json',{'operation':'replace-one-section','baseline_sha256':sha(old),
        'combined_sha256':sha(whole),'replacements':[{'file':'01-section.md','before_file':'05-previous-section.md',
        'old_byte_span':[a,b],'new_byte_span':[a,a+len(block)],'before_sha256':sha(previous),'after_sha256':sha(block),
        'marker':'### '+TITLE,'scope':'same dynamic-weight section; rest of book unchanged'}]})
    write_json(OUT/'passage-manifest.json',{'coordinate':'unicode-scalar-half-open',
        'sections':[{'file':'01-section.md','title':TITLE,'level':3,'items':items}]})
    cjk=lambda value:len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]',value))
    adapted_items=[x for x in items if 'ref' in x]
    retained=sum(sum(x.size for x in difflib.SequenceMatcher(None,source[slice(*p['source_span'])],p['text'],autojunk=False).get_matching_blocks()) for p in adapted_items)
    stats={'combined_sha256':sha(whole),'prior_cjk':cjk(old.decode()),'combined_cjk':cjk(whole.decode()),
        'section_cjk':cjk(text),'prior_section_cjk':cjk(prior),'net_added_cjk':cjk(text)-cjk(prior),
        'source_events':len(events),'source_adaptations':len(adapted_items),'passage_units':len(items),
        'selected_source_characters':sum(p['source_span'][1]-p['source_span'][0] for p in adapted_items),
        'verbatim_retained_selected_source_characters':retained,
        'retention_scope':'Character matches within selected source spans, not a fraction of the new section or whole book.'}
    write_json(OUT/'editorial-statistics.json',stats)
    ledger=['# 能力形成与资源累积的来源及编辑对照','完整作者原话与上一轮AI公开答复分别保留。正文中新增的连接、例子、证据和限定为AI编辑建议，不冒充作者逐句确认。']
    for e in events:ledger.append('## '+e['ref']+'\n\n角色：'+e['role']+'；原生时间：'+e['time']+'\n\n内容 CID：`'+e['content']+'`。\n\n全文见 [来源原文](00-'+e['ref'].lower()+'.txt)。')
    for item in items:
        ledger.append('## '+item['id']+'　'+item['kind'])
        if 'ref' in item:ledger.append('原话：\n\n'+source[slice(*item['source_span'])]+'\n\n成文：\n\n'+item['text'])
        elif item['kind']=='inherited-text':ledger.append('继承第十版原段落：\n\n'+item['text'])
        else:ledger.append('AI编辑补写：\n\n'+item['text'])
    (OUT/'03-source-ledger.md').write_bytes(('\n\n'.join(ledger)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':compose()
