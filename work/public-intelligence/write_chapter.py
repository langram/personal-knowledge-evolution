"""Weave the new reflection into the approved reading flow, preserving sources."""
import copy, difflib, json, re, sys
from prepare import ROOT,BASE,WORK,OUT,ARCHIVE,OLD,PRIOR,write_json,sha
sys.path.insert(0,str(ROOT/'work/new-principles-expanded'))
import book
DATA=json.loads((ARCHIVE/'selected-sources.json').read_bytes());book.DATA=DATA
old_manifest=json.loads((OLD/'passage-manifest.json').read_bytes())
old_report=json.loads((PRIOR/'report.json').read_bytes())
c=book.Chapter('22');c.key='23';c.title=old_manifest['title']
def take(n):
    x=copy.deepcopy(old_manifest['items'][n])
    for k in ['ordinal','chapter_span','document_span']:x.pop(k,None)
    x['previous_passage']={'cid':old_report['passages'][n],'ordinal':n,'relationship':'verbatim retained or moved'}
    c.items.append(x)
def old_range(a,b):
    for n in range(a,b):take(n)
def new_source(first=None,last=None,**kw):
    kw.setdefault('note','本次作者发言；所引名言另标归属，实质性润色是编辑建议')
    c.src('INTELLIGENCE-REQUEST',first,last,**kw)
def heading(text):c.heading(text)

old_range(0,5)
heading('二、知识与智能怎样相互生成')
c.add('''要理解这种担心为什么会出现，我们需要把视野从一项成果的署名，再向外推开一步：知识怎样产生，产生知识的能力又掌握在谁手里？''','从数学合作问题转入知识与智能的相互生成')
new_source(1,replacements=[('其实全新的体制下，人与人，人与AI的关系，相比旧体制，有了新的结构性的改变。','在全新的体制下，人与人、人与AI的关系，相比旧体制，将发生新的结构性改变。')])
new_source(2,start='我们所处的宇宙',end='是知识和智能，',replacements=[
('巨大的动态演化的进化系统','巨大的、不断动态演化的系统'),
('人们试图寻找其基本规律，从哲学意义上考察，这是存在和变化的关系，从数学的范畴论视角来看，是对象和态射，从物理学角度出发，是物质和能量，是粒子和波，从计算机科学角度出发看，是数据对象和程序函数，如果我们从整个人类文明的视角来看，是知识和智能，',
 '人们试图寻找其基本规律。从哲学意义上考察，我们讨论存在和变化；从数学的范畴论视角来看，我们讨论对象以及对象之间的态射；从物理学角度出发，我们研究物质的状态与变化、能量的传递与转换，也研究粒子和波这两种描述的关系；从计算机科学角度看，我们讨论数据对象和程序函数。如果从整个人类文明的视角来看，我所关心的，就是知识和智能。')])
c.add('''这些领域有各自的概念，不能简单地互相画等号。但把它们放在一起观察，可以帮助我们同时看见：一个系统已经形成了什么结构，又通过什么过程继续发生变化。对文明来说，知识是已有经验与认识的积累，智能则使这些积累能够被运用、检验，并产生新的认识。''','限定跨学科类比的含义，不把对象态射、物质能量、波粒写成同一科学定律')
new_source(2,start='两者之间都是二位一体',replacements=[
('两者之间都是二位一体，互相转化的关系。','在这个意义上，知识与智能是二位一体、相互转化的。'),
('训练和过的智能能力的原料','训练和形成智能能力的原料'),
('互相转换互相促进','互相转换、互相促进')])
c.add('''一个数学家通过学习已有定义、定理和证明，形成新的理解问题的能力；他用这种能力提出猜想、完成证明，又把结果交给别人学习。对于AI，也可以考察这样的循环：已有知识参与训练和推理，新的研究产出经过检验后，再进入公共知识与后续学习。我们不只关心知识库里增加了多少材料，还关心这些材料怎样使整个系统更善于发现问题、解决问题和纠正错误。''','用本章数学案例解释知识与能力循环')
new_source(3,replacements=[
('文明早期时代，传统的智能与知识之间的关系，往往是绑定在某个特定的单个的人类生物智能体上的，而这些知识和获得知识的智能能力往往和该智能人类生物个体在社会生存的经济生活中的物质利益捆绑在一起。',
 '在早期文明中，许多知识，尤其是实际运用知识的技能，往往紧密依附于某个具体的人类生物智能体。这些知识和获得知识的智能能力，又往往与这个人在社会生存、经济生活中的物质利益捆绑在一起。'),
('人的技能智能以及知识与实际创造的物质产品密切相关，在集体合作的人类社会中，人的知识和智能与所产出的产品一起，作为商品以互相交换的方式进行合作。',
 '人的技能、智能以及知识，与实际创造的物质产品密切相关。在集体合作的人类社会中，人们可以通过交换劳动、服务和所产出的产品，交换彼此能力带来的成果。')])
c.add('''例如，一个工匠把手艺传给另一个人，常常需要长时间的示范与练习。即使把全部步骤说出来，对方也未必马上获得同样的能力。知识已经能够传递，能力却仍需要在另一个人的身上重新培养。一个人掌握什么、能做什么，与他怎样谋生、能在合作中占据什么位置，因而很容易紧密相连。''','解释技能传递和知识复制的差别，避免把早期合作归结为单一商品交换')

heading('三、从知识共享到智能共享')
new_source(4,replacements=[
('但是随着文字语言的发明，以及印刷术等技术的发展，','随着语言、文字以及印刷术等技术的发展，'),
('知识中的纯理论部分(和生产制造等应用领域的技能知识仍然不是自由共享的)，逐步从少数人的垄断，变成了可以相对自由共享，虽然书籍印刷和教育传授仍然被作为知识的载体和传递工具，仍然一种商品来进行交换，但是理论知识本身还是被当作了可以自由传播的内容。',
 '越来越多的理论知识，可以离开最初掌握它的人，在更大的范围内传播和共享。书籍印刷和教育传授，作为知识的载体和传递活动，仍然可以作为商品或服务交换；但一个人已经公开的理论内容，也可以被更多人学习和接续。生产制造等应用领域的技能、诀窍，则仍有不少受到保密和使用条件的限制。'),
('到了工业文明时代，连专利这种生产制造等领域的技能知识，也开始松动了，很多开明的先驱开始提出可更彻底知识共享的理念。',
 '随着工业文明的发展，更彻底地共享知识的理念，也扩展到生产制造等应用领域。')])
c.add('''这里存在一个很容易被忽略的区别：把一个物品交给别人，自己可能就不再拥有这个物品；把一个想法告诉别人，自己通常仍然能够继续使用这个想法。知识传播所需要的载体、劳动和条件有成本，却不意味着每多一个人理解它，就必须从原来理解它的人那里减去同样一份知识。''','连接知识传播成本与非排他使用的直观区别')
new_source(6,replacements=[
('杰斐逊说过：“从我这里得到一个想法的人，他本人得到了教导，但我的想法并没有减少；这就像他用我的蜡烛点亮了他的蜡烛，他得到了光明，却并没有让我陷入黑暗。”',
 '杰斐逊在1813年致艾萨克·麦克弗森的信中，用一支蜡烛点燃另一支蜡烛来比喻思想的传播：接受者得到启发，并不会减少原有思想；借光点亮自己的蜡烛，也不会使给予者陷入黑暗。[书信原文](https://monadnock.net/jefferson/mcpherson.html)')],note='作者提供的杰斐逊引语；核对书信后改为意译，未将其全部专利立场等同于本文制度主张')
new_source(7,replacements=[
('萧伯纳也说过“','还有一个流传很广的比喻：“')],note='保留作者提供的苹果与思想比喻；未找到可靠的萧伯纳原始出处，正文不署该姓名，核对记录在附录')
c.add('''而思想的交流，还可能不止让两个人分别多得到一个现成想法。一个人的问题与另一个人的方法相遇，会产生原来谁都没有的第三个想法。共享已有知识，由此又成为创造新知识的条件。''','从交换已有知识推进到共同生成新知识')
new_source(8,replacements=[
('由于二进制数据代码的复制传播成本几乎为零，所以针对知识的，更加彻底的开源运动开始了。理查德·斯托曼把目标直指数字化的知识--软件。',
 '数据和代码可以以很低的边际成本复制、传播，为更大范围的知识共享提供了技术条件。理查德·斯托曼把自由共享的目标直接指向数字化的知识——软件。')])
c.add('''1983年，斯托曼发布GNU项目的最初公告，希望建设可以自由使用和分享的软件系统。这里的自由，关心用户能否运行、研究、修改和再分发软件，并不等于开发、维护和提供服务不需要费用。[GNU最初公告](https://www.gnu.org/gnu/initial-announcement.html)、[GNU关于自由软件与收费的说明](https://www.gnu.org/philosophy/selling.en.html)''','核对自由软件的历史与自由不等于零价格的含义')
take(8)
new_source(9,replacements=[
('现在这个时代，知识中的大部分，尤其是基本知识理论，重要的基本软件技术领域，以及越来越多的硬件技术领域（尤其是与计算机相关的领域），越来越多的知识，变成了开源的公共知识。',
 '在今天，基础科学理论、许多重要的基础软件，以及一些硬件设计领域中，越来越多的知识，能够以公开文献、开放代码或开放设计的形式，成为可以共同学习、使用和接续的资源。')])
new_source(10,start='如果说信息时代的前AI时代',end='成为全球共享的免费资源。',replacements=[
('如果说信息时代的前AI时代，让知识的复制成本降低到几乎为零，从而进入了科学知识和技术的开源公共知识时代，那么，进入AI时代之后，连产生知识的智能本身也开始成本急速下降，普及程度急速扩张，智能的复制成本几乎为零的时代已经不远了，所以作为智能的AI本身，也应该步知识的后尘，成为公共知识基础设施，成为全球共享的免费资源。',
 '如果说前AI的信息时代，让知识的复制成本大幅降低，推动了科学知识和技术的公开共享，那么，进入AI时代之后，连参与产生知识的智能能力，也开始能够借助模型和软件，在不同设备和不同人之间广泛部署。这就把知识共享的问题，又向前推进了一层。作为智能的AI本身，也应该步知识的后尘，成为公共知识基础设施，逐步使基本的智能服务成为全球共享、人人可以免费使用的资源。')])
c.add('''一个已经训练好的模型，在复制时不必重新经历原来的全部训练过程，这与重新培养一个具有同样知识技能的人很不一样。但复制模型文件，与持续运行模型，是两件不同的事情。训练、推理、存储、通信和设备维护，仍然消耗能源与资源；推理本身的能耗也能够实际测量。[AI部署能耗研究](https://arxiv.org/abs/2311.16863v3)

所以，我所说的免费，是一种需要共同建设的制度安排：由共同体承担基础设施和基本服务的成本，使个人获得基本智能帮助时，不必反复向一个排他性的拥有者购买使用资格。有限的公共算力怎样安排，仍然需要共同决策。这种主张以能力可以广泛复制和复用为技术条件，以保障每个人的发展为制度目的。''','区分模型复制、训练和实际运行成本；保留公共基本服务免费这一规范目标')
new_source(10,start='像阳光和空气',replacements=[
('像阳光和空气为人类生物肉体的体力运动提供免费的养分和能量一样，作为人类大脑的精神和智力活动提供免费的养分和能量。',
 '就像阳光和空气是人类生命活动的重要条件一样，我希望公共智能能够成为每个人都容易获得的条件，为人类大脑的精神和智力活动提供“养分和能量”。')])
c.add('''当一个孩子因为好奇而提问，一个工人因为工作中的观察而想到改进，一个数学爱好者因为看到某种联系而产生猜想，他们接入的，就应当是能够帮助自己继续发展的共同能力。这些最初的火花，不应仅仅因为提出者没有购买昂贵服务的能力，就停留在原地。''','把公共基本智能重新接到本章灵感种子的主题')

heading('四、共同的智能，需要怎样的共同组织')
new_source(12,start='而且，从本质上来讲',end='是产生知识的能力和过程。',replacements=[
('而且，从本质上来讲，AI是一个可以聚集收集全人类智力活动所产生的知识，通过计算机算法，大规模的，自动化的整理、蒸馏全人类的知识，所建立的大模型，就是将全人类知识的内容，整合到一个巨大的高维潜空间中，形成一个亿万参数的模型。他本质上，就是人类智力活动的大规模自动化采集处理快速完成知识的整合和迭代演化的人类智力集成系统，是产生知识的能力和过程。',
 '从这个角度看，AI可以汇集人类智力活动产生的大量知识，通过计算机算法，大规模、自动化地学习、整理和提炼这些知识。由此建立的大模型，把从材料中学到的关系和规律，编码为具有大量参数的模型及其高维表示。它可以成为人类智力活动的集成系统，帮助完成知识的整合和迭代演化，参与产生知识的过程。')])
c.add('''模型并不是把全人类知识完整、无误地复印了一遍。能够发挥作用的共同智能，还需要可核对的知识库、检验工具、人的判断以及现实反馈。但它所依靠的大量基础知识、语言、数学、科学与实践经验，显然不可能由最后训练模型的某一个团队从零独自创造。''','限定模型与全人类知识的关系；共同智能包括知识库、验证与现实反馈')
new_source(12,start='只不过，现在的AI',end='将自己的命运交由别人决定。',replacements=[
('只不过，现在的AI，是整个地球村中，少数精英们，组建的一些商业公司，通过传统的资本主义政治和经济体制，在彼此互不信任，互相竞争对抗的情况下，低效的来完成这个任务，',
 '但是，如果这个集成过程，主要由地球村中少数精英组建的商业公司，通过传统的资本主义政治和经济体制，在彼此互不信任、互相竞争对抗的条件下来组织，信息隔离和重复工作，就会成为需要不断付出的代价。'),
('在这种体制下，其他的国家，企业，个人，出于在传统机制下，维护个人利益，保护自己安全的目的下，','在这种体制下，其他国家、企业和个人，出于维护自身利益、保护自己安全的考虑，'),
('不会将自己的信息放心的交给他人，将自己的命运交由别人决定。','就很难放心地将自己的信息交给他人，将自己的命运交由别人决定。')])
take(28);take(30)
new_source(11,replacements=[
('AI，作为全球共享的智能，不应该被某个人，某个公司所拥有，不是一种传统意义上的商品资产，','我所主张的、作为全球共享基础设施的AI，不应该被某个人、某个公司排他地拥有和支配，也不应继续只被看成一种传统意义上的商品资产。'),
('从训练数据的采集获取，到学习训练，再到实际使用，产出新的数据，反馈后继续迭代循环的全过程，所有的数据代码的创造权，使用权，反馈权，解释权，记录权以及决策权，分配荣誉和利益权，所有的所有权，都是公共知识和数据，机制上要确保不会被文明体中的局部的某个个人或团体所支配。',
 '从训练数据的采集获取，到学习训练，再到实际使用、产出新的数据、经过反馈继续迭代循环的全过程，都需要共同的规则。数据和代码的创造、使用、反馈、解释、记录怎样进行，决策权怎样行使，荣誉和利益怎样分配，以及公共资源怎样归属和支配，都应该具有可以共同审查的规则与记录。机制上要确保，公共智能不会被文明体中的某个局部个人或团体单方面支配。')])
c.add('''这并不抹去具体人的创造。研究者、数据提供者、软件开发者、设备维护者都付出了劳动，他们的贡献应该留下来源，得到承认和相应安排。共同积累的知识与能力成为公共基础，不要求贡献者消失，也不能给某个中心机构任意取走个人资料的权力。

公共的是共同规则、公共资源及其使用、共同研究中应当共享的过程和成果。个人哪些材料愿意提供、按什么用途提供，仍由明确的权利与授权来约束。把公共系统怎样运行公开出来，与把每个人的私人生活公开出来，是不同的要求。''','解释公共权能、个人贡献与个人资料支配的相容关系')
take(17)
new_source(12,start='把地球文明看作是一个巨型的文明体智能生物的话',replacements=[
('把地球文明看作是一个巨型的文明体智能生物的话，一个高效运行的，能够收集所有自身和外界信息，并进行智能处理的真正的星球文明体AI，必须要全地球人类的共同合作才可以完成。',
 '如果把地球文明看作一个巨型的文明智能体，那么，要逐步形成能够汇集自身与外界相关信息、进行智能处理的星球文明体AI，就需要向全人类的共同合作开放。'),
('只不过这次机制的对象，不是静态的数据/代码/软件，而是整个文明智能体，文明体中的所有个体节点，系统的运行机制，运行轨迹，都成为公共知识。',
 '这次机制所覆盖的对象，要从已经形成的数据、代码和软件，继续扩展到整个文明智能体：各个节点怎样连接和协作，系统怎样运行，共同决策怎样产生和执行，都成为可以追踪、检验、修正的公共知识。')])
c.add('''这种共同性，可以由许多相互连接的人、模型和组织共同实现。不同的研究路线、不同判断可以同时存在，通过共享的接口、可核对的依据和反馈继续比较。一个人既使用公共能力，又能够把自己的新发现带回公共体系；共同体系的成长，又使这个人获得进一步创造的条件。知识与智能的相互促进，由此获得一种新的组织形式。''','把共同协议解释为多节点协作，而不是单一模型或固定管理者')

heading('五、让贡献可以共享，让贡献者不必消失')
old_range(6,8);old_range(9,14)
heading('六、在第一点灵感出现时，就开始记录它的生长')
old_range(15,17);take(18)
heading('七、一颗灵感种子，怎样长成理论大树')
old_range(20,22)
c.add('''这条贡献链，还可以继续进入公共智能的下一轮学习：哪些经过检验的结果进入了知识库，哪些材料被许可用于训练，哪次模型更新借助了这些材料，更新后又帮助谁开展新的研究，都应在能够核验的范围内留下关系。我们既要看见一项发现怎样形成，也要看见产生发现的共同能力怎样积累；不能因为知识进入了模型，原来应当保留的来源、使用条件和贡献就失去位置。''','把数学研究过程接到数据、训练、使用、反馈的完整循环；不许诺无法做到的逐参数归因')
heading('八、怎样承认贡献，才能减少对贡献的争夺')
old_range(23,27)
heading('九、智能网络的能力，怎样成为每个人的能力')
take(31);take(29);old_range(32,40)
heading('十、从学生的灵感，到基层的创造')
old_range(41,44)
heading('十一、从一次可以核对的合作开始')
old_range(45,48)

def build():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    oldbytes=(OLD/'02-new-principles.md').read_bytes();oldchapter=(OLD/'01-chapter.md').read_bytes()
    assert sha(oldbytes)==baseline['old_manuscript_sha256'] and sha(oldchapter)==baseline['old_chapter_sha256']
    assert oldbytes.count(oldchapter)==1
    posbytes=oldbytes.index(oldchapter);prefix=oldbytes[:posbytes];suffix=oldbytes[posbytes+len(oldchapter):]
    pos=len(prefix.decode());chapter='## '+c.title+'\n\n';items=[]
    for i,item in enumerate(c.items):
        x=dict(item);x['ordinal']=i;x['chapter_span']=[len(chapter),len(chapter)+len(x['text'])]
        x['document_span']=[pos+a for a in x['chapter_span']]
        chapter+=x['text']+'\n\n';items.append(x)
    newbytes=chapter.encode();whole=prefix+newbytes+suffix
    (OUT/'01-chapter.md').write_bytes(newbytes);(OUT/'02-new-principles.md').write_bytes(whole)
    write_json(OUT/'passage-manifest.json',{'schema':'public-intelligence.passages@1','title':c.title,'coordinate':'Unicode code point; half-open','items':items})
    body=[x for x in items if x.get('reason')!='节标题'];new=[x for x in body if not x.get('previous_passage')]
    stats={'chapter_cjk_characters':len(re.findall('[\u3400-\u9fff]',chapter)),
           'combined_cjk_characters':len(re.findall('[\u3400-\u9fff]',whole.decode())),
           'previous_chapter_cjk':len(re.findall('[\u3400-\u9fff]',oldchapter.decode())),
           'body_unicode_characters':sum(len(x['text']) for x in body),
           'source_adapted_characters':sum(len(x['text']) for x in body if x.get('ref')),
           'literal_aligned_source_characters':sum(x.get('retained_characters',0) for x in body),
           'source_blocks':sum(bool(x.get('ref')) for x in body),'editorial_blocks':sum(not x.get('ref') for x in body),
           'source_entries_used':sorted({x['ref'] for x in body if x.get('ref')}),
           'retained_previous_passages':sum(bool(x.get('previous_passage')) for x in items),
           'new_body_characters':sum(len(x['text']) for x in new),
           'new_literal_aligned_source_characters':sum(x.get('retained_characters',0) for x in new),
           'chapter_sha256':sha(newbytes),'combined_sha256':sha(whole),
           'boundary':'Source-adapted does not mean verbatim; first-person editorial writing does not assert author acceptance.'}
    write_json(OUT/'editorial-statistics.json',stats)
    replacement={'schema':'public-intelligence.chapter-replacement@1','baseline_file':baseline['old_manuscript'],
                 'baseline_sha256':sha(oldbytes),'previous_chapter_file':baseline['old_chapter_file'],
                 'previous_chapter_sha256':sha(oldchapter),'replace_at_utf8_byte':posbytes,
                 'replace_at_codepoint':pos,'removed_bytes':len(oldchapter),'removed_characters':len(oldchapter.decode()),
                 'inserted_bytes':len(newbytes),'inserted_characters':len(chapter),
                 'chapter_file':'01-chapter.md','combined_file':'02-new-principles.md',
                 'chapter_sha256':sha(newbytes),'combined_sha256':sha(whole),
                 'outside_chapter_byte_preserved':True,'author_acceptance':'positive prior reading feedback is recorded; not interpreted as approval of this new draft'}
    write_json(OUT/'replacement-manifest.json',replacement)
    ledger='# 原话、来源改写与编辑补写\n\n此前章节的保留段落带有上一版段落CID和序号，本次新增段落另标来源。区间为Unicode码点半开区间；原始文字不改写。来源改写包括校订，不等于逐字原话。\n\n'
    for x in body:
        ledger+=f'## {x["ordinal"]} · '+('来源选取与改写' if x.get('ref') else '编辑补写')+'\n\n'
        if x.get('previous_passage'):
            p=x['previous_passage'];ledger+=f'上一版单元 {p["ordinal"]}，`{p["cid"]}`；正文文字保留，位置可能调整。\n\n'
        if x.get('ref'):
            r=DATA[x['ref']];a,b=x['source_span'];text=r['text'][a:b]
            ledger+=f'来源：{x["ref"]}，原生时间 {r["time"]}，区间 [{a}, {b})。\n\n'+x['author_assessment']+'。\n\n原话：\n\n'
            ledger+=''.join('> '+line+'\n' for line in text.split('\n'))+'\n成文：\n\n'+x['text']+'\n\n'
            for e in x['edits']:
                before=e['before'].replace('\n','↵').replace('\r','␍').replace('`','ˋ');after=e['after'].replace('\n','↵').replace('\r','␍').replace('`','ˋ')
                ledger+=f'- [{e["source_span"][0]}, {e["source_span"][1]})：`{before}` → `{after}`。\n'
            ledger+='\n'
        else:ledger+=x.get('reason','论述展开')+'。\n\n'+x['text']+'\n\n'
    (OUT/'03-source-ledger.md').write_bytes(ledger.encode())
    oldord=[x['previous_passage']['ordinal'] for x in items if x.get('previous_passage')]
    assert len(oldord)==len(set(oldord))
    omitted=[x['ordinal'] for x in old_manifest['items'] if x['ordinal'] not in oldord]
    write_json(OUT/'reorganization.json',{'retained_previous_ordinals_in_reading_order':oldord,'omitted_previous_ordinals':omitted,'omission_reason':'only old section headings replaced by new numbering; all prior body units retained exactly','new_section_count':11})
    assert all(old_manifest['items'][i].get('reason')=='节标题' for i in omitted)
    print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':build()
