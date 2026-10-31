"""Build a source-led edition with two reversible replacements and explicit roles."""
import difflib
import json
import re
from prepare import ARCHIVE, OLD, OUT, sha, write_json

TITLE='公平的发展条件、能力多样性与跨领域合作'

def compose():
    assert not (ARCHIVE/'report.json').exists(), 'Frozen archive must not be rewritten.'
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events'];byref={e['ref']:e for e in events}
    old=OLD.read_bytes();prior=(OLD.parent/'01-section.md').read_bytes();assert old.count(prior)==1
    paragraphs=prior.decode().strip().split('\n\n')
    needs_start=old.index('我用正态分布来帮助理解个体需要'.encode())
    needs_end=old.index(b'\n\n',needs_start)+2;prior_needs=old[needs_start:needs_end]
    frames=[];items=[]
    def add(text,kind='editorial-addition',**extra):
        items.append({'id':'S'+str(len(frames)+1)+'P'+str(len(items)+1).zfill(2),
            'kind':kind,'text':text,'basis_refs':['DEVELOPMENT-GOALS','AUTHOR-REVISION','INTEGRATION-REQUEST'],
            'wording_author_approved':False,**extra})
    def adapt(ref,start,end,text):
        source=byref[ref]['text'];a=source.index(start);b=source.index(end,a) if end else len(source.rstrip())
        original=source[a:b];edits=[]
        for tag,i,j,k,l in difflib.SequenceMatcher(None,original,text,autojunk=False).get_opcodes():
            if tag!='equal':edits.append({'operation':tag,'source_span':[a+i,a+j],'before':original[i:j],'after':text[k:l]})
        add(text,'source-adaptation',ref=ref,source_role=byref[ref]['role'],source_span=[a,b],
            source_sha256=sha(original.encode()),edits=edits)
    def inherit(prefix):
        text=next(p for p in paragraphs if p.startswith(prefix));at=prior.decode().index(text)
        add(text,'inherited-text',baseline_file='05-previous-section.md',baseline_section_span=[at,at+len(text)],basis_refs=[])
    def finish(file,title,level,before_file,before):
        text=('#'*level+' '+title+'\n\n') if level else ''
        for p in items:
            a=len(text);text+=p['text'];p['section_span']=[a,len(text)];text+='\n\n'
        (OUT/file).write_bytes(text.encode());(OUT/before_file).write_bytes(before)
        frames.append({'file':file,'title':title,'level':level,'before_file':before_file,'items':list(items)})
        return text.encode()

    adapt('DEVELOPMENT-GOALS','我的回答是，理性的社会制度','\n\n一方面',
          '理性的社会制度，应该以完成以下两个目标为诉求。')
    adapt('DEVELOPMENT-GOALS','一方面，让培养机会','\n另一方面',
          '一方面，让培养机会、设备与基本生活保障等外部条件更公平，减少不公平的外部资源累积对个人成长的影响，让人们更多地能够根据自身特点和后天偏好，发展自己的能力。能力的形成，需要考虑个体自身的差异，也需要考虑后天投入的时间、练习次数和实际获得的培养条件。')
    adapt('DEVELOPMENT-GOALS','另一方面，让每个人','\n\n这样的话',
          '另一方面，让每个人都能够掌握关于自身和外部世界充足的信息，逐步认识自身的特点，了解自己的特长，同时提供充足的自由发展的时间和自由，用于自由发展自己偏好的能力。')
    add('这里的公平，需要落实到人们实际上能够使用的条件。每天拥有同样长的钟表时间，不等于每个人都有同样多可以自主安排的时间。一个人如果长期被基本生存压力和无法分担的照护任务占据，即使学习资料对他免费开放，也未必真正拥有学习机会。因材施教，既要帮助人找到合适的方法，也要使他能够实际使用这些方法。')
    adapt('AUTHOR-REVISION','所以重要的不是',None,
          '所以，重要的不是让能力去逼近正态分布，而是让系统的机制，能够让这些不同能力的个体建立起尽可能有效的合作，让这些偏科和全面的人们有效沟通、合作起来，共同完成跨领域的深度合作。')

    add('#### 能力的成长条件，也属于制度需要解决的问题','heading')
    inherit('因为人类个体的能力训练')
    inherit('这里需要再向前追问一步。资源的影响')
    inherit('儿童技能形成研究')
    inherit('于是，在某些分配规则下')
    inherit('荷兰科研资助的一项断点研究')
    add('因此，考察一个制度是否公平，不能只看最后谁的成绩更高，还要看谁有机会进入、谁能够持续训练、谁能够在失败以后继续尝试。人的能力究竟会呈现怎样的统计分布，可以作为经验问题研究；制度要完成的工作，是减少不合理的成长障碍，并帮助不同的能力形成合作。它不需要先规定每个人的能力最后都应当符合某一种曲线。')
    inherit('所以，我所期待的新机制，要把培养能力')

    add('#### 不同的能力结构，可以在合作中形成互补','heading')
    adapt('AUTHOR-REVISION','实际上先天基因的差异','所以重要的不是',
          '人们在是否容易转移偏好、能否在某个方向上持续关注和投入精力等方面，也会表现出差异。这样，有的人偏科但造诣极高，有的人样样都懂，但是却缺乏单个方向上的深入。')
    add('对于这些差异有多少来自遗传、成长经历、训练或者个人选择，可以继续研究。合作机制的建立，不必等待我们先把每一个人的所有差异都解释清楚，也不必用一种测试或预测，提前决定一个人一生只能走哪一条路。了解自己的过程，本身就可以通过尝试、反馈与重新选择不断发展。')
    add('人们也没有必要先把所有能力折算成一个总分，再按照这个总分决定谁更有价值。一个人在某个问题上能够深入到别人难以达到的细节，另一个人能够看见不同问题之间的联系，他们的贡献要在具体的合作中理解。制度可以为不同任务提供可比较的判断依据，同时保留能力结构的多样性。')
    adapt('COOPERATION-SYNTHESIS','- **深入解决问题**','\n\n它们是任务中的',
          '深入解决问题的人，可以在某个领域持续投入，掌握细节，发现一般性讨论容易忽略的困难，并验证具体方案。连接不同领域的人，则可以理解各方的问题、条件和表达方式，发现联系，把整体目标拆成可以协作的任务，再检查各部分能否共同工作。')
    adapt('COOPERATION-SYNTHESIS','它们是任务中的不同角色','\n\n例如',
          '它们是任务中的不同角色，同一个人在不同情境下可以承担不同角色，不必把人固定划分成“专才”和“通才”两类。')
    add('在一个非常具体的问题上深入的人，面对更大的问题时，也可能成为连接多个方向的人；善于连接不同领域的人，也可以通过持续学习，在某个方向逐步深入。这样的角色应当随着问题和人的成长而变化。因材施教所要提供的自由，也包括改变方向、扩大兴趣和重新开始的自由。')

    add('#### 跨领域的深度合作，需要把各方的条件连接起来','heading')
    adapt('COOPERATION-SYNTHESIS','例如，开发一种储能设备','\n\n这也让你设想',
          '例如，开发一种储能设备，材料研究者关注材料性能，工程人员关注结构和运行，制造人员关注生产条件，使用者关注成本与实际需要。跨领域合作的关键，是让这些条件能够彼此传递：某个局部性能的提高，会不会使制造变得困难？某个降低成本的办法，会不会损害使用者最在意的功能？连接者的贡献，在于帮助大家发现这些关系；专业研究者的贡献，在于把相关问题解决到足够深。')
    add('假如材料研究者只报告一个性能数字，却没有说明它在什么温度、寿命和制造条件下成立，其他人就可能把局部结果当成整个方案已经成熟。反过来，如果工程人员发现了实际约束，却没有办法把问题送回研究环节，整个合作就会在信息断裂处停住。需要共同保存的，不只是结论，还有结论的条件、尚未解决的问题，以及改变一个条件可能影响哪些其他环节。')
    add('这样的协作，也不应当让擅长协调的人变成所有信息必须经过的唯一关口。任务如何拆分、各方提出了什么要求、为什么作出某个选择，都应当在获得相应授权的协作范围内可以追溯。一个协调者暂时离开，其他人仍然能够接续工作；有人认为连接方式有问题，也能够提出替代方案并接受检验。')
    adapt('COOPERATION-SYNTHESIS','- AI帮助各方解释概念','\n\n这样，系统要衡量',
          '在我设想的技术系统中，AI帮助各方解释概念、查找相关知识、提出可能被遗漏的联系；Merkle-DAG保存问题、证据、修改与贡献之间的关系，让后来者能够接续工作；动态权重围绕具体问题分配判断影响力，同时允许质疑、复核和修正；协调过程可以被理解和接替，使跨领域连接不依赖某个不可替代的信息中介。')
    add('这些功能需要在实际任务中逐步验证。AI给出的跨领域解释，需要相关参与者检查是否保留了原本的条件和含义；记录下来的贡献，也需要结合具体证据理解。公共知识系统的作用，是让讨论能够建立在可检查、可继续发展的基础上，让不同的人不必从头猜测对方已经做了什么。')

    add('#### 让专业优势服务于共同创造','heading')
    adapt('DEVELOPMENT-GOALS','加上人们合作中形成的能力互补和信任。','\n\n你觉得呢',
          '通过因材施教、发挥自己的特长，再加上人们合作中形成的能力互补和信任，我希望系统能够减少被个别人支配的机会。这个目标要靠具体机制实现：个人能够获得成长的条件，专业判断能够发挥作用，而这些优势又不能自动变成对其他人的普遍支配权。')
    add('一个材料专家可以对材料测试作出更有依据的判断，却不能仅凭这一点替所有使用者决定他们应当接受怎样的成本与风险；善于组织合作的人，也不能因为掌握了全局信息，就取得永久决定别人是否可以参与的权力。问题的性质、证据的范围和受影响者的需要，应当共同进入决策过程。')
    inherit('所以，更多代理首先代表')
    inherit('我们还要防止恶意的破坏和篡改能力')
    inherit('但是，“作恶算力不到一半”')
    adapt('COOPERATION-SYNTHESIS','这样，系统要衡量的','\n\n你这段观点',
          '这样，系统要衡量的，就包括：相关的人能否找到彼此，误解能否及时发现，专业判断能否得到检验，以及合作成果能否被其他人继续发展。')
    add('还可以继续观察：原本缺少资源的人是否真正获得了培养和参与的机会，跨领域合作是否减少了反复解释与返工，参与者能否在保持自主性的同时持续合作。能力分布的形状仍然可以被记录，但它不再替代这些与人的实际生活、成长和共同创造直接相关的判断。')
    block=finish('01-section.md',TITLE,3,'05-previous-section.md',prior)
    items=[]
    add('个体需要的差异，不等于财富和支配权可以无限累积。具体需要究竟怎样分布，仍然要看所讨论的资源和人群；不能先画出一条钟形曲线，再要求每个人把自己的生活塞进去。理解需要，是为了更好地满足人，并为每个人的发展提供适合的条件，而不是为了把人变成某个固定指标。','editorial-alignment')
    needs=finish('08-needs-paragraph.md','按需保障与公平发展条件的衔接',0,'05-previous-needs-paragraph.md',prior_needs)

    replacements=[]
    for frame,before,after in [(frames[0],prior,block),(frames[1],prior_needs,needs)]:
        a=old.index(before);replacements.append({'file':frame['file'],'before_file':frame['before_file'],
            'old_byte_span':[a,a+len(before)],'before_sha256':sha(before),'after_sha256':sha(after),
            'marker':before.decode().split('\n')[0]})
    replacements.sort(key=lambda r:r['old_byte_span'][0]);whole=b'';cursor=0
    for row in replacements:
        a,b=row['old_byte_span'];whole+=old[cursor:a];x=len(whole);after=(OUT/row['file']).read_bytes()
        whole+=after;row['new_byte_span']=[x,len(whole)];cursor=b
        frame=next(f for f in frames if f['file']==row['file']);offset=len(whole[:x].decode())
        for item in frame['items']:item['document_span']=[offset+k for k in item['section_span']]
        patch=''.join(difflib.unified_diff((OUT/row['before_file']).read_text(encoding='utf-8').splitlines(keepends=True),
                    after.decode().splitlines(keepends=True),fromfile=row['before_file'],tofile=row['file']))
        patch_name='06-section-revision.patch' if row['file']=='01-section.md' else '06-needs-revision.patch'
        row['patch']=patch_name;(OUT/patch_name).write_bytes(patch.encode())
    whole+=old[cursor:];(OUT/'02-new-principles.md').write_bytes(whole)
    write_json(OUT/'revision-manifest.json',{'operation':'replace-section-and-align-needs-paragraph',
        'baseline_sha256':sha(old),'combined_sha256':sha(whole),'replacements':replacements})
    write_json(OUT/'passage-manifest.json',{'coordinate':'unicode-scalar-half-open','sections':frames})
    cjk=lambda text:len(re.findall(r'[\u3400-\u4dbf\u4e00-\u9fff]',text))
    stats={'combined_sha256':sha(whole),'prior_cjk':cjk(old.decode()),'combined_cjk':cjk(whole.decode()),
        'section_cjk':cjk(block.decode()),'net_added_cjk':cjk(whole.decode())-cjk(old.decode()),
        'source_events':len(events),'replacements':len(replacements),'passage_units':sum(len(f['items']) for f in frames)}
    for role in ['user','assistant']:
        adapted=[p for f in frames for p in f['items'] if p.get('source_role')==role]
        stats[role+'_adaptations']=len(adapted)
        stats[role+'_selected_characters']=sum(p['source_span'][1]-p['source_span'][0] for p in adapted)
        stats[role+'_verbatim_retained_characters']=sum(sum(m.size for m in difflib.SequenceMatcher(None,
            byref[p['ref']]['text'][slice(*p['source_span'])],p['text'],autojunk=False).get_matching_blocks()) for p in adapted)
    stats['retention_scope']='Character matches within selected source spans, separately by speaker; not a percentage of the new section.'
    write_json(OUT/'editorial-statistics.json',stats)
    ledger=['# 公平发展与能力合作的原话及修改对照',
        '作者已明确接受从分布前提转向能力互补的概念修订，并授权整理入书。该接受不表示作者逐句确认本轮新编辑文字，也不把AI建议改记为作者原话。']
    for e in events:
        ledger.append('## '+e['ref']+'\n\n角色：'+e['role']+'；原生时间：'+e['time']+'。\n\n内容 CID：`'+e['content']+'`。\n\n[完整原话](00-'+e['ref'].lower()+'.txt)。')
    for frame in frames:
        for p in frame['items']:
            ledger.append('## '+p['id']+'　'+p['kind'])
            if 'ref' in p:ledger.append('来源角色：'+p['source_role']+'；来源：'+p['ref']+'。\n\n原话：\n\n'+byref[p['ref']]['text'][slice(*p['source_span'])]+'\n\n成文：\n\n'+p['text'])
            elif p['kind']=='inherited-text':ledger.append('继承第十一版文字：\n\n'+p['text'])
            else:ledger.append('AI编辑补写：\n\n'+p['text'])
    (OUT/'03-source-ledger.md').write_bytes(('\n\n'.join(ledger)+'\n').encode())
    print(json.dumps(stats,ensure_ascii=False))

if __name__=='__main__':compose()
