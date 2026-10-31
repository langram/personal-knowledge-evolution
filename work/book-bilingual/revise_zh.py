"""Make bounded consistency edits without rewriting historical source records."""
import difflib, json, re
from pathlib import Path
from prepare import OLD, OUT, WORK, sha, write_json

old=OLD.read_text(encoding='utf-8')
changes=[]
def replace(before, after, reason):
    assert old.count(before)==1
    changes.append({'before':before,'after':after,'reason':reason,'old_start':old.index(before)})

replace('所以，能力平等的方向，并不是把不同的人压成同一个模板，而是尽量避免一个人因为缺少入口，就永远只能接受别人的判断。',
        '所以，公平的发展条件，并不是把不同的人压成同一个模板，而是尽量避免一个人因为缺少入口，就永远只能接受别人的判断。',
        'Distinguish fair opportunity from identical ability outcomes.')
replace('这就不再是抹除全人类能力差距的工具，反而是某个个体或组织增强能力',
        '这就可能不再是改善所有人发展条件、减少不公平能力障碍的工具，反而是某个个体或组织单方面增强能力',
        'Replace erasure of ability differences with fair development and removal of unequal barriers.')

replace('人与人能力和权力的平等，能否为更复杂的合作提供更好的条件？',
        '人与人之间公平的发展条件，以及对支配权的限制，能否为更复杂的合作提供更好的条件？',
        'Keep the physical analogy from treating equality of individual abilities as a social premise.')
replace('同样的人类/AI个体的能力权力的平等，也不等于功能的单一化，恰恰相反，我希望研究，怎样的共同基础能够赋予和释放这些构件在功能上的多样性。',
        '同样，人类个体借助 AI 获得更公平的学习和参与条件，也不要求每个人具有相同的能力。恰恰相反，我希望研究，怎样的共同基础能够保留能力的多样性，使不同特长通过跨领域合作形成互补。',
        'Express the shared foundation as fair access supporting diversity and complementarity, not identical capacities.')

before=next(p for p in old.split('\n\n') if p.startswith('这样的机制提供了两个相互配合的方向：'))
after='这样的机制提供了两个相互配合的方向：一是信息可以通过计算机和数字存储设备进行充分的共享和存储，并且可以跟踪、防止篡改，有关共同决定的信息能够被参与者核验；二是在 AI 的帮助下，改善参与者获取知识和进行推理的条件，让每一个参与博弈的节点都有更好的理性判断条件。这种公平，不要求大家具有相同的兴趣、经验和判断能力，而是让不同的人能够获得理解问题、表达意见、学习和复核的实际机会。有人偏科但造诣极高，有人善于连接不同领域，把这些能力通过有效沟通连接起来，才能更好地完成跨领域的深度合作。这些条件的改善，使我所设想的分布式动态权重决策机制有了可以逐步研究和实践的基础；它是否有效，还要在具体任务中检验。'
replace(before,after,'Remove an inference from shared information and AI access to already-equal rational capacities; emphasize actual opportunities and complementary abilities.')

before='对于动态权重会不会重新集中成少数人的权力，我的一个判断是，不能忽略能力差异与权力积累之间的区别，人类能力上的差异，与权力和财富在反复的不对等博弈中所产生的巨大累积，并不是同一种现象。'
replace(before,before+'能力可以通过学习和练习不断积累，能力之间也可能存在很大差异。防止支配，不能靠预先假定这些差异很小、符合正态分布，或者天然不能积累；要看规则是否允许某种优势变成对其他人的长期控制。',
        'Make the institutional argument independent of any assumed ability distribution or absence of learning accumulation.')

replace('长期反复博弈后获得的权力和资本资源上的幂律分布优势','长期反复博弈后获得的权力和资本资源集中优势',
        'Describe concentration without treating a specific statistical law as a universal premise.')
replace('第一类个体生存需求的资源是按需按优化分配，只和这个个体的本身生理和心理结构特性有关，',
        '第一类用于个体生活和发展的资源，按照实际需要安排，以个体的生理、心理、照护和发展需要为依据，同时考虑实现这些需要的条件和共同资源的可用范围，',
        'Align the privacy chapter with actual support and development needs rather than treating allocation as a function of bodily characteristics alone.')

before='个体需要的差异，不等于财富和支配权可以无限累积。具体需要究竟怎样分布，仍然要看所讨论的资源和人群；不能先画出一条钟形曲线，再要求每个人把自己的生活塞进去。理解需要，是为了更好地满足人，并为每个人的发展提供适合的条件，而不是为了把人变成某个固定指标。'
replace(before,before+'还需要区分个人消费的适宜范围，与满足需要所需的资源成本：一个人的食量有限，不代表医疗、照护、无障碍设备或学习条件的成本都相近。需要更多支持的人，不应当因为偏离平均数而被排除。消费有边界，也不能自动推出资源和权力不会集中；防止集中成为支配，仍然要靠共同资源的用途、授权范围、复核和退出等具体规则。',
        'Separate bounded consumption from the heterogeneous cost of meeting needs and from control of collective resources.')

marker='### 动态权重怎样避免成为新的固定权力\n\n'
addition='''### 公平的发展条件、能力互补与防止支配

我所追求的目标，是让培养机会、设备、基本生活保障等外部条件更公平，让每个人有充足的自由发展的时间和自由，逐步了解自己的特长，发展自己偏好的能力。重要的不是让能力去逼近正态分布，而是让系统的机制，能够让这些不同能力的个体建立起尽可能有效的合作，让这些偏科和全面的人们有效沟通、合作起来，共同完成跨领域的深度合作。

这条制度论证，不需要把“能力和需求服从正态分布”作为前提。观察到的绩效分布，同时受到培养条件、机会、资源累积、任务选择和评价方式的影响；它不能直接告诉我们先天能力怎样分布，也不能证明改善条件以后必然得到另一种特定分布。相同的钟表时间，也不代表相同的可支配时间、学习速度或适合的发展路径。公平的条件值得争取，不需要等待某条统计曲线成立。

需要同样不能只用一个总量或者一个平均数来理解。不同的人在不同阶段，可能需要不同的照护、工具、环境和学习方式。按需保障要理解这些具体差异；共同生产资源则需要根据任务及其影响组织。两种用途的区分，不等于已经证明所有需求都有相同边界，也不等于资源安排自动免于滥用。

因此，“不会出现支配节点”应当作为需要持续检验的制度设计目标，不能作为由能力分布直接推出的定理。即使某个领域出现能力远高于其他人的个体，系统仍应让他的知识能够发挥作用，又使其他参与者能够质疑、复核、学习和形成替代方案。专业判断的影响力，不能自动兑换为对基本生活、个人资料和其他领域的永久决定权。

进一步检验时，需要允许能力分布有长尾、经验积累明显、信息掌握不均以及多个节点联合行动等情况，观察共同资源、权重规则和执行权限是否仍然能够被审查和修正。若一种机制只有在所有人能力相近、没有历史优势时才不会集中权力，那么它还没有解决所要解决的问题。

合作方面也要看具体结果：公平条件是否使原本缺少机会的人真正能够进入，深入研究与跨领域连接能否互相支持，沟通是否减少误解和返工，协调者离开以后工作能否接续。只有把这些结果与其他可行安排进行比较，才能逐步判断新机制在哪些条件下实现了目标，在哪些地方还需要修正。

'''
replace(marker,addition+marker,'Add an explicit self-reflection appendix separating empirical distribution questions, normative aims, cooperative design and anti-domination tests.')

new=old
for row in sorted(changes,key=lambda x:x['old_start'],reverse=True):
    new=new[:row['old_start']]+row['after']+new[row['old_start']+len(row['before']):]
cursor=0;delta=0
for n,row in enumerate(sorted(changes,key=lambda x:x['old_start']),1):
    row['id']=f'ZH-{n:02}'
    row['old_char_span']=[row.pop('old_start'),0];row['old_char_span'][1]=row['old_char_span'][0]+len(row['before'])
    row['new_char_span']=[row['old_char_span'][0]+delta,row['old_char_span'][0]+delta+len(row['after'])]
    row['before_sha256']=sha(row['before'].encode());row['after_sha256']=sha(row['after'].encode())
    delta+=len(row['after'])-len(row['before'])
changes.sort(key=lambda x:x['old_char_span'])
inverse=new
for row in reversed(changes):
    a,b=row['new_char_span'];assert inverse[a:b]==row['after'];inverse=inverse[:a]+row['before']+inverse[b:]
assert inverse==old
(OUT/'01-new-principles.zh.md').write_bytes(new.encode())
(OUT/'03-zh-revisions.patch').write_bytes(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='edition-12.zh.md',tofile='edition-13.zh.md')).encode())
write_json(OUT/'zh-revision-manifest.json',{'schema':'pkst-editorial/full-book-consistency@1','baseline_sha256':sha(old.encode()),'result_sha256':sha(new.encode()),'changes':changes,'scope':'Bounded consistency edits; other Chinese text unchanged.'})
parts=list(re.finditer(r'^## .+$',new,re.M));chapter_dir=WORK/'zh-chapters';chapter_dir.mkdir(exist_ok=True)
chapters=[]
for i,m in enumerate(parts):
    end=parts[i+1].start() if i+1<len(parts) else len(new);text=new[m.start():end]
    name=f'{i+1:02}.md';(chapter_dir/name).write_bytes(text.encode())
    chapters.append({'id':f'{i+1:02}','title_zh':m.group()[3:],'char_span':[m.start(),end],'source_file':'zh-chapters/'+name,'sha256':sha(text.encode()),'characters':len(text),'review':'pending full reading and English adaptation'})
(WORK/'en-chapters').mkdir(exist_ok=True)
write_json(WORK/'chapters.json',{'source_sha256':sha(new.encode()),'title_zh':new[:parts[0].start()],'chapters':chapters})
print(json.dumps({'edits':len(changes),'chinese_characters':len(re.findall('[\u4e00-\u9fff]',new)),'chapters':len(chapters),'sha256':sha(new.encode())}))
