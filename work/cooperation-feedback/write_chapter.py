"""Insert a source-led chapter while preserving every byte of the prior edition."""
import difflib
import json
import re
from prepare import ARCHIVE, BASE, OLD, OUT, sha, write_json

REQUEST = json.loads((ARCHIVE / 'request-capture.json').read_bytes())
TEXT = REQUEST['text']
ITEMS = []

def add(text, reason='论述衔接与机制展开'):
    ITEMS.append({'kind': 'editorial-addition', 'text': text.strip(), 'reason': reason})

def heading(text):
    add('### ' + text, '节标题')

def source(first, start=None, end=None, replacements=(), new=None):
    matches = list(re.finditer(r'[^\n]+(?:\n(?!\n)[^\n]+)*', TEXT))
    match = matches[first]
    a, b = match.span()
    if start is not None:
        a = TEXT.index(start, a, b)
    if end is not None:
        b = TEXT.index(end, a, b) + len(end)
    original = TEXT[a:b]
    result = original if new is None else new.strip()
    for old, new in replacements:
        assert result.count(old) == 1, old
        result = result.replace(old, new)
    operations = difflib.SequenceMatcher(None, original, result, autojunk=False).get_opcodes()
    ITEMS.append({'kind': 'source-exact' if result == original else 'source-adaptation',
        'ref': REQUEST['ref'], 'text': result, 'source_span': [a, b], 'source_sha256': sha(original.encode()),
        'retained_characters': sum(j-i for tag, i, j, k, l in operations if tag == 'equal'),
        'edits': [{'operation': tag, 'source_span': [a+i, a+j], 'output_span': [k, l],
                   'before': original[i:j], 'after': result[k:l]} for tag, i, j, k, l in operations if tag != 'equal'],
        'author_assessment': '作者本轮原话；润色与条件化改写供作者审阅，不自动视为作者采纳'})

TITLE = '公共知识、互惠与合作的正向循环'

source(2, replacements=[
    ('非公共知识信息系统下，不但由于信息的不充分和有意隐瞒，使得双方无法达成最优博弈结果，达到全局最优的纳什平衡。', '在缺乏公共知识支撑的信息系统下，信息的不充分和有意隐瞒，不但使合作各方难以找到对整体更有利的博弈结果，还可能使大家被困在各自防守、彼此消耗的状态中。'),
    ('而且由信息不透明不对称，使得合作各方之间，所产生的从怀疑，到不信任，最终形成情绪上的相互敌视，直至发展成为行为上的互相抵制，', '信息的不透明、不对称，还会使合作各方从怀疑走向不信任，逐渐形成情绪上的相互敌视，直至发展成为行为上的互相抵制，使得')])
add('''这里需要区分“稳定下来”与“整体更好”。纳什均衡所说明的，是其他人的策略不变时，每一方都无法仅靠单方面改变策略获得更高收益；这样的均衡，完全可能使所有人都比相互合作时更差。囚徒困境就是一个典型例子。因此，我所追求的，是改变信息、保护和收益的条件，使更有利于共同生活的合作能够持续，而不只是让某一种状态稳定下来。[均衡与效率的区别](https://www.cs.cornell.edu/~eva/agtchap17.pdf)''', '校正纳什均衡与整体最优的混用，保留改善整体合作结果的目标')

heading('隐瞒造成的损失，为什么超过被隐瞒的事实本身')
source(3, end='其实都是上述原因造成的。', new='''最近围绕尊界汽车制动踏板支架断裂的争议，波音737 MAX的MCAS信息披露问题及后续安全文化与“吹哨人”争议，以及大众“柴油门”（Dieselgate）事件，都使我们不得不追问：当设计者、生产者、监管者与使用者掌握的信息不一样，又没有足够可靠的共同核查机制时，合作会付出怎样的代价？''')
add('''这些案例的证据状态并不相同。尊界事件中的测试条件、样件状态与故障原因，需要能够相互对照的原始材料和独立核查；不能只因存在争议，就先判定某一方有意隐瞒。它提出的一个直接问题是：公众怎样从相互冲突的说法，走到可以共同检查的证据？[相关争议报道](https://www.thepaper.cn/newsDetail_forward_34216478)

波音案例中，2021年美国司法部公布的协议材料记载，公司通过相关飞行技术人员隐瞒了MCAS的重要变化，使关键评估文件以及相应手册、培训材料缺少相关信息。2024年的安全文化听证和FAA证词，又涉及员工能否在不害怕报复的情况下提出安全问题。这使信息问题延伸到了组织内部：知道问题的人，是否有条件把它说出来？[司法部材料](https://www.justice.gov/archives/opa/pr/boeing-charged-737-max-fraud-conspiracy-and-agrees-pay-over-25-billion)、[参议院听证资料](https://www.hsgac.senate.gov/subcommittees/investigations/hearings/faa-oversight-of-boeings-broken-safety-culture/)、[FAA证词](https://www.transportation.gov/faa-oversight-boeings-broken-safety-culture-0)

大众案例则更直接地表现出“看见的测试”与“实际运行”之间的分离。EPA在2015年的公告中说明，相关软件能够识别官方排放测试，并在测试时开启完整排放控制，正常行驶时却采用不同表现。外部独立分析引发疑问，进一步调查才揭示其中的问题。[EPA公告](https://www.epa.gov/archive/epa/newsreleases/epa-california-notify-volkswagen-clean-air-act-violations-carmaker-allegedly-used.html)''', '区分争议、已有披露记录与监管发现；不推断黑匣子记录遭隐瞒，也不把不同事件写成同一因果事实')
source(3, start='试想这样的事情', replacements=[
    ('如果从设计到测试到生产再到所有销售环节，所有信息都是像git仓库中有版本跟踪的开源软件代码一样，', '如果从设计到测试、生产，再到销售和使用反馈，与安全和责任有关的依据，都像Git仓库中有版本跟踪的开源软件代码一样，可以按适当范围追溯和核查，'),
    ('那么，这些怀疑和不信任，几乎是不可能发生的事情。', '那么，许多原本只能靠猜测的怀疑，就有机会通过核查得到澄清；已经存在的缺陷，也更有机会被及时发现和纠正。')])
add('''不过，公开一份图纸，还需要确认实物是否按这份图纸生产；公开一个软件版本，还需要确认设备实际运行的是否就是这个版本。原始测试、失败记录、修改理由与交付批次之间，应当能够互相核对。Merkle-DAG可以帮助核对记录之间的内容与版本关系，实物、测量和现场过程仍需独立检查。这样建立起来的信任，来自疑问能够得到回答，而不是要求人们不再提出疑问。''', '补齐公开记录到真实物理过程的证据链；不把版本管理等同于事实真实性')

heading('从怀疑到敌视，互相防守怎样变成共同损失')
source(4, replacements=[
    ('实际上这种情况，普遍存在于其他政治经济和社会生活的方方面面，自古至今，发生着数不清的种种问题案例，', '类似的信息与信任问题，也存在于政治、经济和社会生活的许多方面，'),
    ('有的甚至具有摧毁人类文明，毁灭世界的风险：从一战二战的爆发，到美苏冷战，古巴导弹危机，再到如今的中美对抗。', '有的冲突甚至可能带来文明尺度的危险。从一战、二战，到美苏冷战、古巴导弹危机，再到当代中美之间的对抗，都值得从信息、预期与相互回应的角度继续考察。当然，这些事件各有复杂的历史条件，不能仅用信息不透明解释其全部起因。')])
source(5, replacements=[
    ('前面提到的这种典型进程：', '这种典型进程——'),
    ('直至发展成为行为上的互相抵制，在这类事件中反复发生，背后的原因，就是因为人类社会中，以牙还牙策略是全人类都知道且默认的最基本的公共知识，', '直至发展成为行为上的互相抵制——在许多冲突中反复出现。一个重要原因，是人类社会中广泛存在着“你怎样对待我，我就怎样回应你”的互惠倾向，'),
    ('在这个公共知识的规则下，', '在这种相互回应的规则下，')])
source(6, replacements=[
    ('在这条全人类共同知晓且共同遵守的以牙还牙策略驱使下，', '当各方主要依照这种相互回应的方式行动时，'),
    ('信息交流的不充分或隐瞒，导致彼此的怀疑，', '信息交流的不充分或隐瞒，就可能导致彼此的怀疑，'),
    ('知道发展成为不信任', '直到发展成为不信任'),
    ('拒绝交流全力隐瞒', '进一步拒绝交流、加强隐瞒'),
    ('你的这种行为，导致对方也开始增强自己的攻防能力', '一方的这种行为，又促使对方增强自己的攻防能力'),
    ('从局部的烈度微小的暴力行为，逐步升级，直至事情完全失控，让身在其中的普通人从充满爱和理性的彼此友好合作者，变成充满恨和冲动的互相血腥杀戮者。', '在严重的情况下，局部、低烈度的暴力还可能逐步升级，直至事情失控，让身在其中原本愿意友好合作的普通人，被恐惧、仇恨和冲动卷入互相伤害乃至血腥杀戮。')])
add('''每一方都可能觉得，自己只是在回应已经受到的威胁；自己的防守，在对方眼里却又成了新的攻击准备。于是，双方都以自身的安全为理由行动，整个系统用于攻防的成本却不断增加。要改变这个过程，需要共同核对威胁是否真实、行动究竟意味着什么，并使双方都能看见停止升级的路径。''')

heading('正向起点为什么重要，为什么还需要纠错')
source(7, replacements=[
    ('反过来考察以牙还牙策略的正向连锁反应链条，你会发现，', '反过来考察互惠合作的正向连锁反应链条，可以看到另一种可能：'),
    ('每增加一点信息交流，每少一点信息隐瞒，彼此的信任就会增加，', '每增加一点真实、有用且受到保护的信息交流，每少一点妨碍合作的刻意隐瞒，彼此的信任就有机会增加，'),
    ('还是愿意进行合作，从而进而进一步增强信任，进行更多合作，', '也更愿意进行合作；合作产生的好处，又进一步增强信任，促成更多合作。'),
    ('这个正向连锁反应链条最终会让各方将一切对促进合作相关的信息都变成公共知识，从而让达成全局最优纳什平衡的概率越来越大。', '这个正向连锁反应链条，可以促使各方把更多与合作有关、适合共享的信息变成公共知识，使大家更有条件发现整体更优的方案，并形成能够持续的合作。')])
source(8, replacements=[
    ('以牙还牙策略的这种正反双面的极化连锁反应特征，', '互惠反馈可能向合作与对抗两个方向不断强化的特征，'),
    ('如果想让这种基本策略驱动的人类社会博弈游戏，能够达到最优，', '如果想让人类社会的博弈更有利于共同生活，'),
    ('这是连锁反应往正向还是反向的最关键一步。', '这是影响连锁反应往正向还是反向发展的一项关键条件。')])
add('''博弈论中的“以牙还牙”（Tit for Tat）有一个明确含义：第一轮合作，此后重复对方上一轮的选择。它在特定重复博弈研究中表现良好，却不能据此说全人类事实上都遵守它，或者它在一切条件下都是最优策略。[Axelrod与Hamilton的研究](https://public.websites.umich.edu/~axe/research/Axelrod%20and%20Hamilton%20EC%201981.pdf)

而且，如果双方机械复制对方上一轮的行为，一次误操作就可能造成交替报复：甲本想合作却做错了，乙下一轮回应，甲又把乙的回应视为新的背叛。两人最初都愿意合作，仍可能陷入循环。因此，正向起点之后，还需要查证、解释和修复误会的通道，让已经开始偏离的互动有机会回到合作。''', '给出TFT准确含义及可直接推演的误差例子；后述机制是扩展的制度设计，不冒充严格TFT')

heading('把合作的起点、保护与修复，变成共同知道的规则')
source(9, replacements=[('所以，最佳的博弈规则就是，让以下规则成为全人类的公共知识：', '所以，我希望逐步建立这样一套博弈规则，并使它成为所有参与者的公共知识：')])
source(10, new='''1. 所有参与者共同遵守互惠原则：对合作作出合作回应，对有证据的侵害采取有边界的防护，并在误会得到澄清、问题得到修复后，为恢复合作保留通路。这里保留“以牙还牙”中的相互回应，同时加入查证与纠错，避免机械报复。

2. 所有人的初始策略都是正向策略，即在具备实际保护的条件下，主动分享有利于达成合作、确有必要且不损害自己和他人正当权益的信息。分享可以从有限范围开始，随着合作经验和保护能力的增长逐步扩大。

3. 适合公开的分享信息，作为公共知识，以Merkle-DAG的方式进行记录和共享；涉及个人隐私的信息，按用途和授权范围处理。同时，通过动态权重决策系统与实际执行约束，防止任何一方仅凭较大的决策权重，就能够利用这些信息伤害分享者。

4. 如果因为系统的复杂性和不可预测性，使决策的执行后果对个体造成利益受损，应立即采取止损和必要救助措施，按事先明确的安排及时补偿，并依据调查结果修改策略、修复机制。利益受损者不必仅凭不良结果就认定某位决策者具有恶意，也有权要求查明原因；是否属于能力限制、不可抗力、过失或者故意行为，应由证据来区分。

5. 如果为了长期更优的结果，需要暂时承担损失，则由决策系统事先给出预估方案、预期结果、不确定性、成本承担与停止条件，让受影响者能够知情参与，并取得适用的授权。在执行中持续监控，根据情况调整方案；当继续执行已不符合约定条件时，及时停止。成功后，依约兑现承诺；失败后，也依约处理补偿和责任，不能把所有损失都要求受影响者自行承担，更不能预先规定失败一定与恶意或过失无关。''')
add('''例如，共同体为降低长期存储成本，计划迁移一批资料。迁移前，应说明谁可能暂时无法使用服务、旧副本如何保留、怎样核对新副本、什么情况下停止，以及损失由谁承担。迁移后发现错误，先恢复服务、保护资料，再查明是方案不充分、执行失误，还是有人隐瞒了已知问题。补偿安排需要有实际资源支撑；对于无法恢复的损失，更不能用一句“事后赔偿”代替事前保护。

这样，受影响者愿意继续合作，就有了现实理由：发生问题时，他不会被独自留下。调查与追责也不必阻止及时救助，更不必把个人保护和共同改进变成只能二选一的事情。''', '以个人云存储展开五项规则，补足补偿资源、停止条件、责任与救助的关系')

heading('公共记录与共同决策，怎样成为可以依靠的条件')
source(11)
source(12, replacements=[
    ('1.Merkle-DAG', '第一，Merkle-DAG'),
    ('从机制上消除了个体之间利用手中的权力互相伤害的可能性，', '要共同服务于一个目标：从机制上不断消除个体利用手中的权力任意伤害他人的条件。')])
add('''记录使依据能够核对，决策网络帮助比较方案，执行约束负责限制实际作用。这几个环节需要一起发挥作用。内容没有被改动，不等于内容一定真实；多数节点同意，也不等于受影响者就可以失去基本保护。规则本身的修改、监督者的行为和权重的调整，也要进入可复核的过程。

“成为公共知识”也要比“上传到公开目录”更进一步。不仅要让参与者能够知道规则，还要让大家能够确认彼此面对的是哪一个版本，知道如何提出异议、如何核对执行。个人AI可以帮助人理解与自身有关的变化，却不能用一条已经发送的通知，替代实际的理解和必要的同意。''', '补齐记录、判断、执行及共享认知的分工，不宣称分布式存储自动产生公共知识或消除伤害')
source(13, replacements=[
    ('2.让人们建立起理性思考第一，抑制非理性冲动情绪，让', '第二，让人们建立起理性思考优先的习惯，减少未经核实就作出冲动回应，使'),
    ('都有正面的初始认知。', '都有正面的初始认知。这里的理性也包括认真理解恐惧和愤怒所反映的处境，给这些情绪以表达、核查和处理的机会。')])

heading('理解人的形成过程，怎样减少把人固定成敌人的冲动')
source(14, replacements=[
    ('之前提到过：人类所有的个体与个体之间，', '人类个体与个体之间，'),
    ('以及需求和认知上的差异和冲突，这些高阶层面上的差异，都是不同低阶层层面上的结构差异，在长期演化过程中，在人类社会的博弈游戏中，逐步演化形成的，', '以及需求上的差异和冲突，都有其形成过程。这些高阶层面上的差异，与不同层次的生理结构、成长经历、社会环境和相互作用有关，并在人类社会长期的演化和博弈中继续变化。'),
    ('这些差异都可以从科学理论上构建出可重现的因果链解释，', '我们可以尝试从科学理论和实际证据出发，构建能够检验的因果解释，理解其中哪些条件可以改变。'),
    ('人们不应该被无知产生的恐惧，和对抗产生的愤怒等情绪驱动，', '人们就有机会减少被不了解产生的恐惧、被对抗不断强化的愤怒所驱动。'),
    ('你会理解到，所谓天使与魔鬼，正义与邪恶的这些激烈的二元对立，其实是在长期人类社会博弈中，在以牙还牙策略的正向和反向连锁反应链条的催化渲染放大后，产生的道德和宗教审批的极端非理性情绪而已。', '我们也会进一步理解，把具体的人或团体固定成“天使”与“魔鬼”、把所有分歧都变成绝对善恶对立的判断，可能受到长期博弈中正向或反向连锁反应的催化、渲染和放大。这样的道德化或宗教化审判，会使人更难看见对方的实际处境，也更难发现改变关系的可能。')])
add('''理解形成原因，并不取消对伤害的判断和制止。一个行为造成了损失，仍然需要保护受害者、查明责任；理解其发生条件，是为了减少下一次伤害，而不是让已经受伤的人放弃追问。我们可以反对一种行为，同时保留这个人可能改变的空间；也可以尊重道德和信仰对人的意义，同时反对用不可质疑的标签封死核查与对话。''', '防止因果解释滑向免责，也不把全部伦理、宗教和情绪笼统判为非理性')
source(15, replacements=[
    ('一旦成为所有人的共识，那么会让人产生了心灵得到洗礼，思想获得顿悟的感受，', '如果逐渐成为更多人的共同认识，就可能使人产生心灵得到洗礼、思想获得顿悟的感受，'),
    ('看待世界看待事物看待其他人的心态发生了非常大的变化，', '看待世界、看待事物、看待其他人的心态，都发生很大的变化：'),
    ('对于自己不同想法看法的人更宽容。', '对于和自己有不同想法、不同看法的人更宽容。'),
    ('这一点就有了情绪和理性上的双重保证。', '这一点，就有了情绪和理性上的双重支撑。')])
add('''这样的认识可以从一次很小的合作中开始形成：先提供真实而有用的信息，让对方看见自己的需要；让保护在行动中发挥作用，出了问题能够说明、纠正和补救。共同机制帮助人们积累值得信任的经历，这些经历又使下一次主动合作变得更容易。知识、制度与人的心态，便有机会沿着同一个正向循环共同成长。''')



def build():
    baseline = json.loads((ARCHIVE / 'baseline.json').read_bytes())
    old = OLD.read_bytes()
    assert sha(old) == baseline['sha256']
    marker = '## 从一个人的云存储开始\n'.encode()
    assert old.count(marker) == 1
    at = old.index(marker)
    chapter = '## ' + TITLE + '\n\n'
    for ordinal, item in enumerate(ITEMS):
        item['ordinal'] = ordinal
        item['chapter_span'] = [len(chapter), len(chapter) + len(item['text'])]
        item['document_span'] = [len(old[:at].decode()) + x for x in item['chapter_span']]
        chapter += item['text'] + '\n\n'
    data = chapter.encode()
    combined = old[:at] + data + old[at:]
    (OUT / '01-chapter.md').write_bytes(data)
    (OUT / '02-new-principles.md').write_bytes(combined)
    write_json(OUT / 'passage-manifest.json', {'schema': 'cf/passages@1', 'title': TITLE,
        'coordinate': 'Unicode code points, half-open', 'source_occurrence': REQUEST['occurrence'], 'items': ITEMS})
    write_json(OUT / 'insertion-manifest.json', {'schema': 'cf/insertion@1',
        'baseline_file': baseline['manuscript'], 'baseline_sha256': sha(old), 'insert_at_utf8_byte': at,
        'inserted_bytes': len(data), 'chapter_sha256': sha(data), 'combined_sha256': sha(combined),
        'placement': 'after protection and trust, before personal cloud storage',
        'outside_chapter_byte_preserved': True, 'author_acceptance': 'requested integration; individual editorial changes pending review'})
    metrics = {'chapter_cjk': len(re.findall('[\u3400-\u9fff]', chapter)),
        'combined_cjk': len(re.findall('[\u3400-\u9fff]', combined.decode())),
        'source_spans': sum('ref' in x for x in ITEMS),
        'source_characters_selected': sum(x['source_span'][1]-x['source_span'][0] for x in ITEMS if 'ref' in x),
        'literal_retained_characters': sum(x.get('retained_characters', 0) for x in ITEMS),
        'chapter_sha256': sha(data), 'combined_sha256': sha(combined),
        'boundary': 'Counts include source adaptation and editor additions separately; no attribution of editor additions to author adoption.'}
    write_json(OUT / 'editorial-statistics.json', metrics)
    ledger = '# 原话与本次编辑对照\n\n原话保存于[作者原文](00-author-original.txt)。时间为来源原生时间 `' + REQUEST['time'] + '`，不是理论最初形成时间。下列区间使用 Unicode 码点半开区间。编辑补充及条件化改写不自动记为作者采纳。\n\n'
    for item in ITEMS:
        if item.get('reason') == '节标题':
            continue
        ledger += '## 段落单元 ' + str(item['ordinal']) + '\n\n'
        if 'ref' in item:
            a, b = item['source_span']
            ledger += f'来源区间：[{a}, {b})。\n\n原话：\n\n> ' + TEXT[a:b] + '\n\n成文：\n\n' + item['text'] + '\n\n'
            if item['edits']:
                ledger += '逐字符编辑区间和替换文本见 passage-manifest.json 的同序号单元。\n\n'
        else:
            ledger += '编辑补写：' + item['reason'] + '。\n\n' + item['text'] + '\n\n'
    (OUT / '03-source-ledger.md').write_bytes(ledger.encode())
    print(json.dumps(metrics, ensure_ascii=False))

if __name__ == '__main__':
    build()
