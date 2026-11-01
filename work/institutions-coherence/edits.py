"""Editorial choices, with exact baseline paragraphs resolved before assembly."""
from prepare import WORK

EDITS=[]
def add(key, chapter, mode, zh_anchor, en_anchor, zh, en, reason):
    EDITS.append(dict(id=key,chapter=chapter,mode=mode,anchors={'zh':zh_anchor,'en':en_anchor},
        text={'zh':zh,'en':en},rationale=reason))

add('01-chess-boundary',1,'append','当然，弃子本身不等于高明','A sacrifice, of course,',
    '但棋子与人还有一个根本区别：棋手可以按棋规决定自己的棋子怎样走，却不能因此推论，少数决策者有权为了一个自称更好的未来，替其他人决定牺牲生命或基本权利。把这个比喻用于制度设计，是鼓励我们重新考察假设、选择自己愿意承担的成本，并寻找减少共同损失的新路径。',
    'There is also a fundamental difference between pieces and people. A player may move their pieces under the rules of chess; this does not entitle a few decision-makers to sacrifice other people\'s lives or basic rights for a supposedly better future. Applied to institutions, the analogy invites us to reconsider assumptions, choose costs we are willing to bear ourselves, and find paths that reduce shared losses.',
    'Connect the opening sacrifice metaphor to the later Watchmen argument without authorizing sacrifices imposed on others.')
add('02-preface-duplication',1,'replace','知识可以被许多个体共同使用','Knowledge can be shared by many individuals,',
    '知识可以被许多个体共同使用，而产生和使用这些知识的组织，其结构和运行机制却有很大差别。人类大脑通过神经元之间的联系和反馈形成能力，人类社会中的许多组织，却把资源、权力和决策影响长期绑定在较为固定的职位上。怎样让组织中的共同知识和反馈，能够真正改变共同决策，而不是只能等待少数掌权者改变看法，是这部书需要逐步展开的问题。',
    'Knowledge can be shared by many people, yet the organizations that create and use it differ greatly. A brain develops capabilities through connections and feedback among neurons; many human organizations attach resources, authority, and influence to relatively fixed positions. How can shared knowledge and feedback actually change collective decisions, rather than leave everyone waiting for a few people in authority to change their minds? This is one of the questions the book will develop.',
    'Keep the detailed aging-leader example in the material-conditions chapter; give the preface its introductory role.')
add('03-personal-memory-scope',6,'append','AI 系统的设计，可以尝试采用这种方式','An AI architecture could experiment',
    '这里的“全局”，是相对于这个智能体经授权可以使用的个人记忆和任务而言，不是让一个中心模型收走所有人的内部对话。许多个人智能体可以在共同任务中交换获准共享的内容，同时保留各自的私人空间。持续的自我对话与文明范围的共同协作，是可以连接、但不能混为一体的两个层次。',
    'Here, a unified context means the personal memories and tasks this agent is authorized to use. It does not mean collecting everyone\'s internal conversations into a central model. Personal agents can exchange permitted information for a shared task while retaining separate private spaces. Continuing personal reflection and cooperation across civilization are connected but distinct levels.',
    'Clarify the scope of global context and preserve the personal/shared distinction used by the attention architecture.')
add('04-dispositions-and-institutions',7,'replace','当然，即使都在同一个民主制度环境下','Within either setting, differences',
    '当然，即使都在同一个制度环境下，人们也不会形成完全相同的反应。个体的生理特点、成长经历、所处位置和对事情的理解不同，在某个临界状态下，原本都倾向于使用温和手段的人，也可能分化出相对强硬和相对温和的倾向；在权力高度集中的体系下，也可能围绕具体事情产生鹰派和鸽派的分化。遗传因素是否以及怎样参与其中，需要具体研究，不能单凭制度名称或某种基因，就预先判定一个人会怎样行动。',
    'People do not respond identically even within the same institutions. Physiology, experience, position, and interpretation can differ. At a difficult threshold, participants who usually favor conciliatory methods may divide into harder and softer positions; highly centralized systems can also contain hawkish and dovish approaches to a particular issue. Whether and how genetic factors contribute requires specific investigation. Neither an institutional label nor a genotype determines in advance how a person will act.',
    'Align the early biological example with the appendix and the multidimensional institutional comparison.')
add('05-feedback-not-convergence-theorem',7,'replace','奖惩机制其实就是一个评价函数','Rewards and penalties can be viewed',
    '在一个简化模型中，可以把奖惩机制看作评价的一部分，把反复的互惠回应看作持续反馈的过程。它可以使关系在互动中加强或减弱，在相应条件下形成比较稳定的合作结构；也可能因为误判、过强的回应或条件变化而振荡、瓦解，甚至使参与者退出。以牙还牙是一种具体策略，并不等于任意评价函数的迭代，更不能仅凭“不动点”这个词就断言社会一定收敛。不同强度的回应，会影响关系的稳定性和修复空间。过强的结构稳定性可能使既有关系难以改变，削弱进化的能力；过于脆弱的关系也难以维持合作。所以，如何构造合理的反馈、奖惩与修复机制，使稳定和改变能够相互支持，是影响整个人类文明进化能力的重要问题。',
    'In a simplified model, rewards and penalties can form part of an evaluation process, while repeated reciprocal responses provide feedback. Relationships may strengthen or weaken and, under suitable conditions, sustain cooperation. Misjudgment, excessive responses, or changing circumstances may instead cause oscillation, breakdown, or withdrawal. Tit for Tat is a particular strategy, not the iteration of any arbitrary evaluation function; invoking a fixed point does not prove social convergence. The strength of a response affects both stability and the room for repair. Excessive rigidity can obstruct change, while fragile relationships may fail to sustain cooperation. Designing feedback, incentives, and repair so that persistence and change support each other is therefore a central problem for civilization.',
    'Remove the unsupported fixed-point convergence shortcut and agree with the later game-theory definitions.')
add('06-vm-to-ecosystem',13,'replace','由此，MerkleVM 的远景既是个人数字空间','MerkleVM is therefore both',
    '由此，MerkleVM 的远景既是个人数字空间，也是共同构造网络中的一个入口。它从现有设备、现有应用和真实需求开始，逐步把分散能力组织起来。要让这样的软件种子继续生长，还需要说明：这些对象、程序和运行记录，怎样形成一种能够被不同AI和设备共同理解、检验和接续的语言与软件生态。',
    'MerkleVM is therefore both a vision of personal digital space and an entry point into a shared construction network. It begins with real devices, existing applications, and actual needs. For this software seed to keep growing, we must explain how its objects, programs, and execution records can form a language and software ecosystem that different AIs and devices can understand, check, and extend together.',
    'Lead to the immediately following software-ecosystem chapter rather than skip to research collaboration.')
add('07-credit-cross-reference',14,'substring','前面关于贡献、荣誉与知识生长的讨论，在这里获得了能够逐步实现的技术支撑。','The earlier discussion of contribution and recognition would gain a practical technical basis.',
    '贡献、荣誉与知识生长的问题，由此获得了能够逐步实现的技术支撑。',
    'Questions of contribution, recognition, and the growth of knowledge would thereby gain a practical technical basis.',
    'Remove a backwards reference to a detailed case study that actually appears later.')
add('08-coordination-scope',16,'append','这样的中枢可以分布在很多设备','Such coordination can span',
    '这里需要协调的，是具体任务中的相互依赖和共同承诺，并不是让全人类在所有问题上只能拥有同一个目标。不同的人可以保留不同偏好，不同群体可以试验不同办法；只有涉及共同资源和外部影响的部分，才需要在相应范围内形成约束。这也是后面个人空间与文明空间的注意力机制，需要分层而又能够连接的原因。',
    'What needs coordination is the interdependence and shared commitments of a particular undertaking, not every person\'s goals on every question. People may retain different preferences, and groups may try different approaches. Shared resources and effects on others call for constraints at the relevant scale. This is why attention within personal spaces and across civilization must operate at distinct but connected levels.',
    'Keep collective coordination task-scoped rather than turn civilization into a single imposed query.')
add('09-capability-does-not-select-goals',16,'append','这条推理并不是说，只要能力提高','Greater technical capability does not automatically',
    '能力的提高也不会自动替人或AI选定目标。更丰富的资源扩大了合作的可能，却不能单独保证一个系统愿意珍惜人的生命和自主性。目标、授权、行为约束与实际反馈，仍然需要共同设计和检验。这正是技术自身的可靠性与文明使用技术的可靠性，必须同时提高的原因。',
    'Greater capability also does not choose goals for people or AI. More abundant resources expand the possibilities for cooperation but do not, by themselves, ensure that a system values human life and autonomy. Goals, permissions, constraints on action, and actual feedback still need to be designed and tested together. Technical reliability and the reliability of the civilization using the technology must both improve.',
    'Connect the abundance argument to the later two-part account of technological and institutional risk.')
add('10-equal-start-and-evidence',17,'append','在这个网络中，每个智慧个体','The proposed network would let',
    '这里的平等初始地位，首先是参与、表达和接受公正检验的机会，不是要求面对已经存在的证据时，把所有技术判断强行赋成同一个可信度。一个没有历史记录的新参与者，应当有提交证据和改变判断的通道；一项已有可靠检验的方法，也不必为了形式上的整齐而从零开始。代理可以代表和协助人，却不能靠不断复制，替同一个委托人增加基本权利或凭空制造独立证据。',
    'An equal starting position means opportunities to participate, speak, and receive a fair hearing. It does not require us to assign identical credibility to every technical judgment despite existing evidence. A newcomer needs a route to submit evidence and change the assessment; a well-tested method need not start from zero for the sake of symmetry. Agents may represent and assist people, but copying agents must not multiply a principal\'s basic rights or manufacture independent evidence.',
    'Resolve equal initial weight versus evidence-sensitive judgment, rights, and duplicated agents.')
add('11-sharing-scope',17,'append','从博弈论上讲，要改善共同决策','Better collective decisions require',
    '这里的“可以共享”，还要经过用途、权益和授权的判断。有助于合作，并不自动等于必须公开原始资料；个人空间可以只提供获准使用的结果或证明。提高共同判断所需的信息质量，与保存每个人的私人边界，应当一起进入设计。',
    'Whether information may be shared still depends on purpose, rights, and permission. Being useful to cooperation does not automatically justify publishing the underlying personal records. A personal space may supply only an authorized result or proof. Better evidence for collective judgment and protection of private boundaries must be designed together.',
    'Make early information-sharing aspirations consistent with later data-sovereignty requirements.')
add('12-attention-existing-layers',18,'append','这种借鉴首先是一种功能上的比较','The comparison is initially',
    '前面已经讨论了共同记忆怎样保留依据，软件怎样复用经过检验的能力，动态权重怎样使专业判断接受反馈。接下来要补上的，是它们之间的调度关系：当前问题应当找到哪些材料和参与者，哪些工作能够沿着已有的热路径完成，哪些新问题需要进入冷路径继续研究，以及什么时候才获得改变现实的授权。注意力架构要把这些能力连接起来。',
    'Earlier chapters described shared memory that preserves evidence, software that reuses tested capabilities, and domain judgments revised through feedback. The next step is to connect them in operation: which material and participants a question should reach, which work can follow an established hot path, which unfamiliar problem needs further investigation on a cold path, and when action gains permission to change the world. The attention architecture should make these capabilities work together.',
    'Connect the new attention chapter to the book\'s existing provenance, reuse, and decision layers.')
add('13-personal-space-continuity',18,'append','我设想，让属于每个人类个体的根AI agent','I envisage a root AI agent',
    '这就是前面个人知识空间与MerkleVM所要支持的同一个个人空间：记忆保存经历和依据，运行环境管理工具与资源，个人代理帮助选择和协调。它们承担不同职能，不需要为每一种新术语另外复制一套个人资料和控制中心。',
    'This is the same personal space supported by the knowledge archive and MerkleVM: memory preserves experience and evidence, the runtime manages tools and resources, and the personal agent helps select and coordinate their use. These are different functions within one arrangement, not reasons to create another copy of the person\'s data and another control center for each new term.',
    'Identify the super agent as a role within the existing personal space, not a competing new platform.')
add('14-runtime-continuity',18,'append','Merkle-DAG可以保存这些变化的依据和版本。','A Merkle-DAG can preserve',
    '这与前面区分对象版本、运行环境和实际执行的思路相接。不可变的是某一份已经形成的记录，不是被记录的世界；需要持续更新的是我们对当前状态、承诺与权限的认识。运行时允许新对象和新规则进入，而历史记录保留这些变化怎样发生，两者共同构成可以学习的系统。',
    'This extends the earlier distinction among object versions, execution environments, and actions. A completed record is immutable; the world it describes is not. Our account of current states, commitments, and permissions must keep changing. The runtime admits new objects and rules, while the historical record preserves how those changes occurred. Together they support learning.',
    'Connect mutable social state to earlier immutable-version and runtime distinctions.')
add('15-bounded-experiment-bridge',18,'append','比较时，既可以采用简单规则','Comparisons can include simple rules',
    '前面关于人与AI共同研究的有限预测实验，已经说明动态加权未必胜过简单方法；这里的共同存储实验，则是下一类需要另行实施的检验。它增加了真实授权、资源承诺和参与者回应，不能借用预测准确率，就宣布共同治理已经有效。',
    'The bounded prediction experiments discussed earlier already show that dynamic weighting need not outperform simpler methods. The shared-storage experiment proposed here is a further test that still needs to be carried out. It adds actual permissions, resource commitments, and participants\' responses. Prediction accuracy cannot stand in for evidence that collective governance works.',
    'Separate the previously reported limited experiment from the proposed cooperation trial.')
add('16-needs-personal-choice',19,'append','之所以要考察物质需要和精神需要的边际效用','Too little water, food, rest, or stimulation',
    '能够研究这些条件，并不意味着存在一个由管理者或AI替所有人算出的、唯一正确的精神生活配方。人的需要还包括探索、改变偏好和自主安排生活的自由。系统可以提供依据、帮助理解后果，个人也能够质疑系统对自己的解释；共同资源不足时的取舍，则需要进入共同讨论。',
    'Investigating these conditions does not produce one correct formula for everyone\'s mental life, to be prescribed by an administrator or AI. Needs include exploration, changing preferences, and the freedom to arrange one\'s life. A system can supply evidence and help people understand consequences, while remaining open to their objections to its account of them. Trade-offs imposed by limited shared resources require collective deliberation.',
    'Align the earlier appropriate-range claim with the appendix, autonomy, and plural goals.')
add('17-institutional-gap',24,'insert-heading','### 让文明的自我修正能力跟上技术的加速',"### Keeping civilization's capacity for correction abreast of technological acceleration",
    (WORK/'fragments/01-institutional-gap.zh.md').read_text(encoding='utf-8').rstrip(),
    (WORK/'fragments/01-institutional-gap.en.md').read_text(encoding='utf-8').rstrip(),
    'Place the new author-led evidence and argument between existing technological power and prospective AI acceleration.')
add('18-participation-transition',24,'replace','当然，这个数学模型不一定就是未来新体制算法模型的最佳选择','No particular mathematical model is necessarily',
    '回到前面关于文明运行时的讨论，马尔可夫博弈等模型，是帮助我们研究持续互动的候选工具。重要的不是具体哪个数学模型，重要的是经过反复研究、迭代和实验构造出来的算法，能够怎样理解和改善真实的合作。计算所需的信息是否充足和准确，要针对实际任务判断；这些信息能否真实地到来，又与参与者怎样理解和使用制度有关。由此，注意力与博弈的技术设计，需要接上制度自身的反馈过程。',
    'Returning to the civilizational runtime, models such as Markov games are candidate tools for studying continuing interaction. What matters is how the algorithms developed through research, iteration, and experiment can understand and improve real cooperation. Whether information is sufficiently rich and accurate depends on the task; whether truthful information becomes available also depends on how participants understand and use the institution. The technical design of attention and games therefore has to connect with institutional feedback.',
    'Replace the orphaned this-model reference and repeated participation introduction with a direct chapter connection.')
add('19-seed-entry-deduplication',26,'replace','这个起点与通常的众筹有所不同','This starting point differs from conventional crowdfunding.',
    '从我一个人做起，从最简单、成本能够承担的云存储开始，从我个人的小资金零钱开始。这就是前面开放组织原则的第一个实际入口：不必等待某个众筹数量或金额目标，消费者也可以逐步成为生产者和创造者；无论一个人愿意投入多少，还是只想先使用服务，这个新机制都要保证他的数据主权。',
    'I can begin on my own, with the simplest cloud storage I can afford and a small amount of my own money. This is a practical entry into the open organization described earlier: no crowdfunding threshold has to be reached, and users can gradually become builders. Whether someone contributes substantially or simply wants to use the service, their data sovereignty must remain protected.',
    'Condense the repeated crowdfunding list and retain the author\'s concrete personal starting point.')
add('20-mathematics-attention-connection',30,'append','第二步，在他同意的范围内','Second, within the researcher\'s permissions,',
    '这正是前面注意力架构可以发挥作用的地方：尚未解决的问题形成Q，方法、经验和已有结果的适用条件构成可匹配的K，获准共享的材料与协作能力提供V。注意力帮助这颗种子找到合适的生长条件，却不替代后面的数学证明，也不把被模型优先找到的人变成能够独占成果的权威。',
    'Here the earlier attention architecture has a concrete role. The unresolved question supplies Q; the conditions under which methods, experience, and existing results apply provide matching keys; permitted materials and assistance supply V. Attention helps the seed find suitable conditions to grow. It does not replace proof, or make the person ranked most highly by a model an authority entitled to own the result.',
    'Show how the new QKV proposal serves the established detailed mathematical case without replacing proof or rights.')
add('21-empirical-reflection',32,'insert-heading','### 怎样使科学预言能够被现实修正','### Letting reality revise a scientific anticipation',
    (WORK/'fragments/02-empirical-reflection.zh.md').read_text(encoding='utf-8').rstrip(),
    (WORK/'fragments/02-empirical-reflection.en.md').read_text(encoding='utf-8').rstrip(),
    'Make the new empirical argument itself subject to measurement, comparison, alternative explanations, and revision.')
