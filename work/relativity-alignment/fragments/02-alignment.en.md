### Alignment begins with a question: aligned with whom?

The discussion of cognitive frames showed how people can inhabit the same world while holding different information, needs, and judgments. Once AI enters this continuing game of social interaction, a frequently omitted question becomes unavoidable. When we say that AI should align with humanity, whom do we mean by humanity?

AI alignment is commonly described as bringing a system's outputs and actions into agreement with human values, intentions, and social norms. For a conversational model, an accessible example is the transition from a base model that continues text to a helpful, honest, and harmless assistant. Learning from human demonstrations and feedback is one practical research approach. But making a model better match the expectations of particular users or evaluators is a long way from resolving society's disagreements over values. [Research on training language models with human feedback](https://arxiv.org/abs/2203.02155)

Consider the fact that different peoples, governments, social classes, and communities do not share all the same values, intentions, political rules, or social norms. A consequence follows quite naturally. In humanity's ongoing social game, each player capable of creating or controlling AI—a government, a social class, a company, or an individual—may have an assistant that is helpful, honest, and harmless from its own perspective, yet appears to others as a dangerous accomplice of an opponent.

An AI can execute its client's instructions accurately while shifting losses onto people who had no part in the instruction. A system might improve a firm's negotiating effectiveness, for example, while treating workers' circumstances as irrelevant because success is defined only in terms of the firm's returns. The problem need not be disobedience to the owner. It may be highly effective obedience to a goal that excludes other affected people.

Local alignment therefore cannot simply stand for collective safety. Evaluating a system requires more than checking whether it understood its client's words. What can that client authorize? Whose rights cannot be overridden? Who can challenge the consequences? These questions extend beyond how a conversational assistant answers a prompt. They concern the institutions through which we live together.

### Neither dominance nor a balance of power removes the need for shared rules

As AI capabilities improve and automation extends into research, programming, and experimentation, the actors using these tools may expand their ability to act more quickly. Unequal access to computing resources, data, talent, and infrastructure may allow AI to widen existing disparities.

We should take the possibility of rapid, consequential change seriously. But without a defined task and supporting evidence, we cannot assign a universal ratio in which a lead of a few months necessarily produces a hundredfold or thousandfold difference in capability. Institutional design does not depend on proving a dramatic number. If some capabilities grow markedly faster than our ability to constrain their use and correct mistakes together, we already have reason for concern.

If development is highly uneven and one actor becomes dominant, that actor may see AI-enabled coercion as easier than negotiation among equals. When benefits are assessed only from the dominant party's position, other people's lives and autonomy, future trust, and the creative possibilities lost to civilization may disappear from the calculation.

That does not make coercion necessarily the most rewarding or least costly strategy. Coercion can provoke resistance, degrade information, damage cooperation, and create lasting uncertainty. The earlier discussion of reasoned persuasion and voluntary trials sought another path. The danger here is that, without shared constraints, a local evaluation can reward actions that damage the whole. It is not that every actor with an advantage is destined to choose violence.

Nor does more balanced development settle the problem. Several powers may face one another with comparable capabilities while mistrust, inadequate communication, and rapid action allow a passing thought or minor misunderstanding to escalate toward a catastrophe for civilization, even without a strong initial intention to cause harm. Each may simply want to avoid falling behind, yet keep taking actions that intensify the others' fear. Anxiety about nuclear confrontation during the Cold War helps illustrate this structural danger. AI operates differently from nuclear weapons, however, and its particular risks require particular analysis.

Dominance and confrontation are thus two risk pathways worth studying, not an exhaustive pair of inevitable futures. Parties can establish communication, verification, limits on external harm, and joint procedures for handling accidents. They can retain competition and disagreement while reducing irreversible escalation. What needs to change is the assumption that threatening one another is the only route to safety.

### A civilization swinging a chained hammer in each hand

The earlier image of a child swinging a chained hammer can be extended to the problem of alignment. Consider the adversarial aspects of AI competition between China and the United States. It resembles a creature with two brains, one directing each hand, and each hand swinging a heavy hammer on a chain—without an effective mechanism for coordinating the two.

The left brain sees the right-hand hammer accelerating and concludes that its own hammer must move faster to avoid injury. The right brain reaches the same conclusion. Both hands increase their strength and speed without checking their trajectories together. Each acts in the name of self-protection, yet the hammers may collide or their chains become entangled, injuring the body they share.

The analogy highlights interdependence and a failure of coordination. It does not suggest that a country has a single will, or that China and the United States are the world's only participants. Each contains different people and organizations; other countries and ordinary people also bear the consequences. Precisely because those affected extend far beyond a few decision centers, the rules cannot be settled privately by those holding the hammers.

A better outcome is not to break the other half of the body, or permanently subordinate one brain to the other. It is to make shared dangers verifiable: which actions create them, what information needs to be exchanged, how errors can be recognized, when action must stop, and how correction can occur without being treated as surrender. Strength can continue to grow, but coordination must grow with it.

### Alignment among people, and between people and AI

At a broader scale, people sometimes imagine humanity as a single player and AI as another, fearing that self-awareness will turn an assistant into a tyrant that enslaves or destroys us. Earlier chapters distinguished consciousness, objectives, and behavioral reliability. Humanity likewise cannot be treated as a player whose objectives and conduct are already unified.

In my view, we can no longer avoid alignment among human organizations and individuals themselves. How can different values, intentions, and norms be brought under shared constraints on actual outputs and actions, so that pursuing one's own goals does not casually undermine another person's basic conditions of survival and autonomy?

This does not require identical tastes, faiths, occupations, or ambitions. What needs alignment first is the framework for cooperation and the relationship between promises and actions. We can disagree about the best life while agreeing not to force one another to live it. We can compete to solve a problem while preserving results and failures for others to examine. We can dispute a proposal while protecting the basic rights of the person who questions it.

Better institutional coordination among people gives human–AI alignment a more substantial foundation. Who may set a goal, who will be affected, whether authorization can be withdrawn, who bears the costs, and how disputes are resolved no longer remain hidden behind the relationship between a model and its client. Cooperative AI research likewise identifies improving the shared circumstances of people and machines, and of multiple agents, as an explicit research direction. [Open Problems in Cooperative AI](https://arxiv.org/abs/2012.08630)

Yet a shared foundation does not automatically solve technical problems. Goals can be expressed badly, feedback can be misunderstood, and systems can fail in unfamiliar conditions. Even sincere cooperation requires tests of whether a system acts within its authority, can be stopped, and can recover when something goes wrong. Institutional coordination among people and technical alignment between people and AI need to support one another and advance together. Neither can wait for the other to be completed once and for all.

### What would it mean to model alignment as a fixed point?

When I suggest that alignment might be understood as a fixed point, I am asking whether repeated observation, action, feedback, and revision can produce a form of coordination that does not continually push participants toward harming one another.

To turn that idea into mathematics, we must first specify the object that remains unchanged and the transformation acting on it. A reward function ordinarily maps states and actions to an evaluation, as in $r_i(s,a)$. Its inputs and outputs need not belong to the same space. The phrase “a fixed point of the reward function” is therefore not, on its own, a well-defined model.

One possibility is to collect participants' evaluation rules, action strategies, and cooperative protocols into a state $z$. We then define an update rule $F_e$ that revises those components in response to evidence and feedback, with $e$ representing temporarily fixed environmental conditions:

$$
F_e:\mathcal{Z}\to\mathcal{Z},\qquad z_{t+1}=F_e(z_t),\qquad F_e(z^*)=z^*.
$$

Now $z^*$ is a fixed point of that update rule. If we are specifically concerned with revisions to reward evaluation, we could instead denote a collection of evaluation functions by $R$, define an update operator $U$ on that same function space, and ask whether $U(R^*)=R^*$. This is a modeling proposal that must be constructed and tested. It proves neither that such a point exists in actual society nor that every starting condition leads to it.

A fixed point carries no guarantee of fairness. An institution may remain unchanged because vulnerable people cannot speak, or because erroneous information keeps confirming itself. The coordination we seek must satisfy conditions such as basic rights, opportunities for challenge, and the ability to revise. We must also examine its response to disturbance. Existence, stability, and legitimacy are separate requirements.

A Nash equilibrium asks whether a participant would benefit from changing strategy alone, given the others' strategies. Pareto optimality asks whether someone can be made better off without making anyone else worse off. Maximization and minimization require specified objectives, constraints, and costs. These concepts answer different questions. They do not become a single conclusion merely because each can involve some sense of no further change. Tit for tat, meanwhile, is a particular strategy of response, not a theorem guaranteeing an optimal outcome.

The real world also produces new objects, technologies, and needs; the environment $e$ changes. A more practical aim may therefore be an evolving path that continues to meet shared constraints, allows local experiments, and corrects mistakes in time. Alignment should keep common development possible, rather than lock civilization permanently into a point or forbid its evaluative rules from ever changing.

### Beyond humanity and AI: the conditions that sustain us

Looking further ahead, the new civilization formed by humans and AI must coordinate its activities with the Earth and, eventually, with the wider environments it enters. This is the longer-term direction I mean by alignment.

Humanity has faced the prospect of widespread destruction from nuclear weapons and now faces climate change arising from accumulated patterns of production and consumption. The IPCC's Sixth Assessment Synthesis Report identifies human activities as the cause of global warming. If we fail to examine the wider consequences of civilization's actions, AI may accelerate and enlarge existing patterns of damage. [IPCC Synthesis Report](https://www.ipcc.ch/report/ar6/syr/)

Ecological alignment does not mean that Earth or the universe has a single will waiting to be read, or that a universal reward function has already been given to us. It means bringing energy use, material cycles, ecological limits, and effects on other life and future generations into decisions and feedback. An action that looks profitable while leaving irreversible losses to those without a voice cannot readily be counted as progress for civilization as a whole.

Alignment, then, is more than a model giving a satisfactory answer in one conversation. It concerns relationships among individuals and organizations, between people and AI, and between civilization and the conditions of its existence. Tests at one level cannot substitute for tests at another, but they must connect: how goals are formed, how information is obtained, how power is constrained, how outcomes are recorded, and how mistakes are repaired. The discussions of shared knowledge, dynamic decision weights, and institutional self-revision seek structures through which that full sequence can gradually become practicable.
