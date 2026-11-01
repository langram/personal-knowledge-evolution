## From Attention to an Evolving Civilizational Runtime

I want to develop this vision of a social neural network with dynamic decision weights into something that can actually operate through social organization, science, and computing. Human attention and attention in AI offer useful starting points. Both invite us to ask how a system facing a vast, complex, changing world can select what matters, connect relevant information, and organize its next actions within limited resources.

The comparison is initially a functional one. Brains, Transformers, and human societies differ in their structures, learning processes, and relationships of authority and rights. The task is to extract mechanisms we can build and test. Transplanting the vocabulary of one system into another does not complete the design.

### Limited resources and selective attention

Resources are finite, and efficiency requires us to focus selectively on what matters. This is the first feature of attention I want to draw on. Our eyes and brains continually receive visual and auditory input. When we read in a noisy cafe, we cannot process every detail equally closely. We suppress some distractions and concentrate on the page. An important, unexpected sound can also interrupt that concentration. Research on attention examines competition and selection guided by behavioral goals; it does not establish that the brain runs the same algorithm as a Transformer. [Research on competition and selection in visual attention](https://pubmed.ncbi.nlm.nih.gov/9142748/)

The second feature is the use of changing weights to establish appropriate contextual relationships within a large and shifting body of information. If we hear, "That apple is really sweet," we connect the apple to fruit and taste rather than first thinking of a phone. An object can have different relevance to different questions, and the same knowledge can serve different purposes at different stages of a task.

The third feature is matching a question to descriptions of relevant objects and obtaining useful content from them. Transformers organize this computation through queries, keys, and values: Q, K, and V. They assess the compatibility of content with a query and use the resulting weights to form representations. During ordinary inference, trained parameters generally remain fixed, while input-dependent Q, K, V, and attention weights change with context. Standard dense attention does not simply devote all computation to a few highly weighted words. Selective influence over a representation and an actual reduction in computation are separate questions. [The original Transformer paper](https://arxiv.org/html/1706.03762v7)

Civilization likewise cannot have every person and every model think equally deeply about every problem at once. A household appliance failure, a new mathematical conjecture, and a regional energy shortage call for different circles of attention. The organizational task is to bring relevant people, knowledge, and tools together within limited time, computing capacity, and communication budgets, while leaving room for clues that established judgments have not yet recognized.

### QKV in personal and shared spaces

I envisage a root AI agent for each person: a personal super agent that helps map a space encompassing the individual and their private resources. A person and their agent would work together to organize attention within that space, supporting self-management and development. These personal spaces and intelligences would also participate in a wider civilizational space, where attention and cooperation could be organized around shared concerns.

A personal root agent could provide a unified interface backed by several replaceable models, tools, and devices. Its role would be to help a person understand their information and choices, subject to that person's authorization and correction. Cooperation in a shared space involves multiple participants with independent wills. Increasing the system's scale would not automatically make personal information available for everyone to inspect or use.

| Component | In a personal space | In a shared undertaking |
|---|---|---|
| Q: the current question or purpose | What do I want to accomplish, what needs solving, and what limits apply to time and resources? | What problem do participants face together, and what needs and constraints do they each bring? |
| K: descriptions relevant to the question | The source, date, version, capabilities, and availability conditions of files, knowledge, devices, and tools | The relationship of collaborators, evidence, and resources to the task, including validity and access conditions |
| V: content or assistance available | Information, explanations, methods, and tool capabilities that may be accessed | Evidence, expert advice, resource commitments, and candidate actions that may be shared |

Value here means content available to the computation; it is not a person's social worth. Someone whose opinion is irrelevant to a particular technical assessment still retains their rights over their life and information. Descriptions can themselves reveal private information. Calling something an index does not make it suitable for public disclosure.

The same person can pose a question, supply evidence, and help carry out a plan. Q, K, and V describe roles in a particular computation, rather than permanent classes of people who command, are assessed, or are treated as resources. The query for a shared problem must itself be formed through participation. Lower cost, greater reliability, and protection of privacy can all be legitimate aims without being simultaneously maximizable. Establishing goals and constraints is part of the collective work.

A reader might ask why we cannot simply let the weights decide. At least four relationships are involved. Relevance to a question concerns attention. Reliability concerns evidence and prediction. Being affected and entitled to speak concerns participation and rights. The ability to change devices, resources, or people's circumstances concerns execution authority. These relationships must be connected, but a single score cannot stand in for all of them.

### Changing objects require a runtime

The real world is plainly more than a static collection of information. Objects in society and the wider world change through people's decisions, actions, and interactions. Objects may be added or removed; their properties can change; they may be destroyed. Nonrenewable resources diminish as they are consumed, while renewable resources have their own conditions of recovery. Rewards and penalties can change someone's resources and may change their future choices. A single attention calculation inside a model cannot simply be copied into this setting.

If semantic objects containing data and programs are knowledge that can be organized and invoked, a social system must also maintain its runtime: which objects currently exist, who can do what, which resources are occupied, which commitments remain outstanding, and which operations have already changed the world. A standard Transformer operates directly on numerical representations. The duality of data and code proposed here is a direction for designing semantic objects; the analogy alone does not establish that ordinary model inputs already possess all of those properties.

We can express the relationship to be recorded in a simple form:

\[
S_{t+1}=F(S_t,A_t,\varepsilon_t)
\]

S represents the current state, A the actions taken, and epsilon environmental disturbances and factors not yet adequately understood. Their interaction determines what happens next. This is only a starting point for modeling. What the system actually possesses is an estimate of the state, with errors and omissions. A database is not the world itself.

Inventory depletion may be recorded item by item. Forest regeneration depends on time and ecological conditions. Trust must be understood through actual cooperation. These cannot all be reduced to adding or subtracting a score. Learning can give a person new capabilities and change the tasks they can undertake; a device leaving the system can require dependent plans to be rearranged. Research on dynamic graphs already addresses attributes and connections that change through events, providing a reference for this part of the work. [Temporal Graph Networks](https://arxiv.org/abs/2006.10637)

A Merkle-DAG can preserve the evidence and versions associated with these changes. An object's identity must be distinguished from the version of its state. A device remains the same device when its available capacity changes, and its old state should not silently be overwritten as though it had always been the new one. Once retired, it remains part of the historical record but must no longer appear as an available resource. Observations, inferences, proposals, authorizations, actions, and outcomes should also retain their relationships. Hashes help verify content and version integrity. Whether a record corresponds to reality, and whether permission remains valid, require separate checks.

### Combining sequential dependencies with parallel exploration

Complex systems mix tasks that require a logical or constructive sequence with tasks that can proceed in parallel. A building needs the relevant foundations before subsequent structural work can proceed, but many activities within each stage can run concurrently. Products pass through design, manufacture, and use, while different production batches, uses, and later design work can overlap. Information collection, analysis, decisions, and action have dependencies, yet each process and the relationships among different tasks also allow substantial parallel work.

Some technical distinctions matter here. An RNN proceeds along a sequence, with later steps usually depending on earlier hidden states. A CNN can compute local convolutions at different positions in the same layer in parallel. Transformers changed how relationships between positions are established, but did not remove every sequential dependency: autoregressive generation still produces outputs step by step. CPUs and GPUs both have forms of parallelism and cannot be strictly divided into machines that only compute sequentially and machines that only compute in parallel.

Calling a country a CNN or an RNN therefore does not explain how its institutions operate. We can retain the underlying question: how should the autonomy, diversity, and room for adjustment emphasized in American multiparty, federal, and divided-power arrangements be compared, task by task, with the coordination and long-range planning emphasized in China's more centralized organization? Democratic participation, administrative concentration, market allocation, local autonomy, and planning capacity are distinct dimensions. A political label alone cannot establish that a system necessarily serves either individual or collective interests.

I want to investigate how shared coordination and diverse exploration can both be supported. Tasks that can be completed locally with limited effects on others can retain substantial autonomy. Interdependent tasks and competition for scarce resources require common interfaces, sequencing, and constraints. The necessary scope of coordination can expand with the scope of effects. Research on polycentric governance likewise directs attention to organizing cooperation at scales appropriate to different public problems. [Ostrom on polycentric governance](https://web.pdx.edu/~nwallace/EHP/OstromPolyGov.pdf)

For example, members of a shared storage service can organize their own information in parallel. They cannot, however, promise the same remaining capacity to several incompatible tasks. The system must identify the conflict and establish explicit commitments. Observation continues during execution. If a device fails, the affected work can be rescheduled without requiring every task to stop while a central node replans everything. A common project schedule also does not give its coordinator permanent authority over unrelated matters.

### Turning multiple perspectives into an executable plan

Complex problems and difficult medical cases benefit from different perspectives and specialists working together, because they improve the chances of noticing omissions and finding a solution. Large social projects need this capacity too. The useful inspiration from multi-head attention is to examine the same problem from several angles. Assigning those perspectives to a social system is our design choice; Transformer attention heads do not naturally correspond to social departments.

A shared storage proposal can be examined for reliability, resource costs, usability, privacy, and long-term portability. One proposal might be technically advanced yet make it impossible for users to take their data elsewhere. Another might be cheap because it leaves a few people carrying an indefinite maintenance burden. Bringing these perspectives together makes such differences easier to detect.

Different recommendations cannot simply be averaged into an action. "Migrate immediately" and "delay the migration" must be compared against conditions, consequences, and evidence. Multiplying each by a weight does not produce an executable plan. Factual judgments can sometimes be combined; incompatible actions require selection or staged experiments; basic rights must remain constraints.

If several AI agents use the same erroneous source, more agents do not mean more independent evidence. The system must also admit unfamiliar clues, the circumstances of minorities, and challenges to its evaluation rules. Attention can adjust quickly, but resource commitments need explicit conditions for revision. Shared rules cannot be rewritten with every fluctuation in a score. Adaptability and predictability have to be designed together.

### From the outcomes of a game to the rules of cooperation

When participants have needs of their own, understand rules, and choose their actions accordingly, statistics and information retrieval are not enough. Game theory examines how one person's choices affect others and how they respond. Mechanism design asks how rules can be changed so that honest expression, sustained cooperation, and individual protection are easier to achieve together.

| Concept | The question it addresses |
|---|---|
| Prisoner's dilemma | Why can choices that benefit each participant individually leave everyone worse off? |
| Tit-for-tat | How should another participant's previous behavior affect the next decision to cooperate? |
| Nash equilibrium | Can anyone gain by changing their strategy alone while everyone else's strategy remains unchanged? |
| Pareto optimality | Is there still a feasible change that benefits someone without making anyone worse off? |

These are not four interchangeable algorithms ready to install. A Nash equilibrium does not guarantee fairness or collective efficiency; Pareto optimality does not decide which distribution is fair. The existence of an equilibrium also does not mean that actual learning will converge to it. [Definitions and examples of Nash equilibrium](https://www.mit.edu/~6.7980/nfgs_nash.html)

Imagine two people maintaining a shared service. If both cooperate, each receives 3. If one free-rides while the other cooperates, the free-rider receives 5 and the cooperator 0. If neither cooperates, each receives 1. These numbers illustrate a structure rather than report measured benefits. For either person, refusing to cooperate gives a higher immediate payoff regardless of the other's choice. They may therefore end up with 1 each. Receiving 3 each would be better, yet the rules of this one-shot interaction do not give each person a reason to maintain that outcome. Publishing the entire payoff table does not resolve the problem.

Transparency must therefore develop alongside the rules of cooperation. Repeated interaction brings the value of future cooperation into present choices. Reliable records support verification, while repair and compensation can prevent an accidental mistake from destroying a relationship. Strict tit-for-tat can also turn one mistake into alternating retaliation. Forgiving reciprocity, win-stay/lose-shift strategies, and conditional cooperation with investigation and restoration all need comparison under particular conditions. Success in one model does not establish a universally best social rule.

Mechanism design asks further questions. Does allocating resources by declared need reward exaggeration? Does counting contributions encourage useless entries? Does counting agents reward duplicated identities? Incentives for honesty, participation conditions, resource feasibility, and the boundaries of actual execution all need examination. If an administrator can still technically perform an action forbidden on paper, that action remains part of the threat model. [Mechanism design basics](https://timroughgarden.org/f13/l/l2.pdf)

Different tasks can draw on different tools. Public infrastructure raises cost-sharing and free-riding problems. Shared equipment requires scheduling and reservations. The division of benefits can draw on bargaining and fair allocation. Contribution assessment can draw inspiration from the Shapley value in cooperative game theory. Marginal contribution, however, involves counterfactual questions about what would have happened without a contribution. Timestamps cannot answer them automatically, and a contribution score should not become a single measure governing basic provision and all individual rights. [Cooperative games and cost sharing](https://www.cs.cornell.edu/~eva/algorithmic-game-theory.pdf)

Correlated equilibrium and regret matching offer another direction for gradual coordination. A system can give participants compatible recommendations and examine whether they have reason to follow them. Under the relevant assumptions, particular regret-matching procedures in fixed finite games cause the long-run empirical distribution of play to approach the set of correlated equilibria. This cannot be extended directly into a guarantee of global optimality for an evolving civilization, but it supplies a candidate method for bounded cooperation experiments. [Hart and Mas-Colell on regret matching](https://www.ma.huji.ac.il/hart/papers/adapt.pdf)

### Persistent states and the emergence of new things

Society requires a model of persistent state. Markov games provide one reference: participants act in a changing environment whose state affects their payoffs, while their joint actions change that environment. The framework can represent competition, cooperation, and mixtures of both. It is a candidate tool, not a mathematical language that future civilization must adopt permanently. [Markov games and multi-agent learning](https://mlanthology.org/icml/1994/littman1994icml-markov/)

The Markov property says that, given a sufficiently descriptive current state and current actions, the probability of the next transition does not additionally depend on earlier history. History has not vanished. Past learning becomes present knowledge; past exchanges become current obligations; previous cooperation shapes present trust. If the state description omits these effects, it must be expanded, or its adequacy acknowledged as an approximation. [States, strategies, and history in stochastic games](https://www.mit.edu/~6.7980/stochastic_games.html)

A reader may ask whether this confines the world to a fixed list of possibilities and excludes genuinely new technology. Several cases must be distinguished. New combinations and behaviors may fit an existing representation. New programs, devices, and organizations can be expressed through variable structures and construction rules. If a phenomenon exceeds the concepts and mechanisms represented by the model, the model itself must be revised.

A computer interpreter need not enumerate every future program before it can run new programs. Likewise, a constructive system need not contain the names of every future technology. When a team develops a new compression algorithm, the knowledge base gains a verifiable program, devices gain new operations, the relationship between storage and computing costs changes, and new services and demands may follow. This can be represented as a sequence of runtime transitions. Multi-agent experiments have also produced new tool-use strategies through interaction. [Emergent tool use in multi-agent learning](https://arxiv.org/abs/1909.07528)

Representing innovation, predicting a particular innovation, and reliably guiding innovation remain different capabilities. Formally imagining the entire world inside one enormous state does not supply the information or computing capacity needed to use it. The world evolves, and the model must evolve too. Phenomena the old model cannot explain should become new research tasks. Work such as POET explores the joint development of challenges and solutions, while also revealing the limitations imposed by problem representations and evaluation methods. [Enhanced POET](https://proceedings.mlr.press/v119/wang20l.html)

### Testing a small cooperative setting

We can begin with a few people, several devices, and a shared storage task. Personal agents organize their owners' information and supply the necessary results within authorization. The shared system detects resource conflicts and develops candidate plans. Actions follow agreed commitments. When outcomes differ from expectations, the participants investigate and revise. Device failures, withdrawn permissions, new members, and new technology can then be introduced to test whether the system updates its current state without erasing the grounds for earlier decisions.

Comparisons can include simple rules and fixed roles alongside dynamic attention and more elaborate game-theoretic mechanisms. With the same information and budgets, do needs get met more effectively? Are errors and delays reduced? Can false reports profit? Can work continue after a coordinator leaves? The system's own computing, communication, and maintenance costs must be included. A task already handled well by a simple method need not be made complicated to fit a grand analogy.

The capability to develop is reliable cooperation within the interactions currently understood, together with room for new problems, technologies, and rules. Attention helps identify relevance; game theory examines strategic interaction; mechanism design improves conditions for cooperation; records and verification preserve the process of change. Their combination should be determined through repeated research and experiment.

As shared decision-making becomes more concrete, another immediate question remains. If someone's technical judgment receives less weight, should their livelihood also be reduced? If a person contributes a better algorithm, should they permanently own more of the common resources? These questions lead to a further basic distinction: personal needs and collective resources must be considered separately.

