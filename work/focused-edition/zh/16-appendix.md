## 附录　依据、推论与未竟之事

前言里说过，本书各个部分的可靠程度不同。这里逐条分开，免得读者把一个推论当作定论，或者把一件今天就能做的事当作幻想。

### 依据：已有定论的数学和科学

以下内容不是本书的发现，本书只是使用它们。

- 变分原理与热力学：最小作用量，自由能最小化与熵最大化，以及它们之间的等价形式。
- 不动点与均衡：平衡态，吸引子，纳什均衡及其存在性；耗散结构。
- 对称性与相对性：物理规律在参考系变换下的不变性，对称性与守恒量的对应。
- 涌现：高层结构有自己的规律，同时服从低层的约束。
- 博弈论：重复博弈中合作与背叛都可以是均衡；以牙还牙在重复囚徒困境竞赛中的表现；鹰鸽博弈的混合均衡；公共知识的定义和作用；安全困境。
- 概率与网络：按比例增长和"富者愈富"的过程产生长尾和幂律分布。
- 机器学习：按历史表现加权汇总多个判断者的在线学习算法及其保证；注意力机制；没有标准答案时靠自我对弈和反馈训练的方法；"苦涩的教训"所总结的历史。
- 预测研究：统计模型与专家个人判断的比较，按记录加权的群体预测。
- 软件工程：密码学哈希，默克尔树与内容寻址，数字签名，版本管理。

### 推论：本书所做的推广和设计

以下内容建立在上面的依据和完整的推理链条之上。它们可以被质疑，但质疑应当针对链条中的某一个具体环节。

- "内部代价最小化、外部关联最大化"作为贯穿物理、生物和社会的工作原理。它在社会层面的操作定义，目前只有严厉度一个，这是起点，不是终点。
- 认知参考系的相对性，以及由它得出的元认知。
- 以牙还牙作为评价函数的迭代算子，严厉度作为收敛速度和稳定性的控制参数；基因决定排序、博弈决定切分点；威权体制作为一个正反馈循环的稳定吸引子，以及退出成本对制度形态的影响。
- 两条连锁反应，五条元规则；隐私和安全问题的根源是权力不对等。
- 两类资源的划分；幂律分配来自不对等博弈的复利；规则意义上的平等。制度是否合理，不以某一种能力分布成立为前提。
- 动态权重的社会神经网络，权重附着于问题并且过期，基本权利的平等与影响力的动态分开。
- 文明体的训练与推理不能分离；每个人的评价和决策就是数据的标注；通用人工智能是整个文明体而不是某一个模型；大文明模型与社会力学的方向。
- 对齐的三个层次，以及第一层决定其余两层。
- 个人资源没有继承权。这一条是我对未来制度的个人意见，不是从前面的原理推出来的结论。

### 今天就能做的

以下内容以当前和可预期的计算机与AI技术能力为前提，是工程问题。

- 一个人的Merkle-DAG个人知识库：把自己在各个平台上的全部记录收回来，按内容标识符、来源和时间保存，原话与AI的回复分别标记，所有版本可以核对。本书的材料就在这样一个库里。
- 以哈希为名字和地址的语言，以及先兼容、再替代的迁移机制。我的项目正在做，并且已经产生了可以记录的负结果。
- 热路径：由大模型处理第一次出现的任务，验证后固化为可复用的程序，并在用户之间共享。
- 个人数据的采集、查看权限规则和可核验的设备。
- 从一个人的云存储开始的组织，以及任务粒度的参与方式。
- 两个人、一项任务、一份记录的最小合作检验。

### 还不能承诺的

- 动态权重的社会神经网络在真实社会决策中的表现。它需要在反馈足够快的领域先运行，在反馈慢的领域先积累记录。
- 新机制在扩张过程中不产生新的支配。这需要在扩张的每一步同时检查内部的平等和对外不形成支配，而不是从机制的定义推出来。
- 技术运行起来之后，分配规则和组织形式能否独立成立。效率的提升不会自动变成公平的分配。
- 大文明模型与社会力学。它的每一个单元本身就是一个高维语义模型，算力要求比今天的大模型高出几个数量级；它的训练素材要靠社会神经网络运行起来才能积累。这是方向，不是今天的能力。
- 虚拟实验室的结果能否迁移到现实。它的作用是筛选，不是替代现实的检验。

### 扩展篇

还有一批内容没有进入本书：范畴论与对偶体，悖论、不完备性与涌现的关系，子对象分类器与意识的数学根源，对齐的不动点刻画，文明注意力的查询、键、值对应，MerkleVM、软件种子与热路径的工程细节，FPM与有类型的不确定性，自我实现的科幻的具体设定，等等。它们是我长期思考的一部分，但或者缺乏广泛的共识，或者还没有展开成完整的论证，或者离本书的主线较远。我把它们整理成一份独立的《扩展篇：实验性假说与设想》，供有兴趣的读者参考。本书的论证不以其中任何一条为前提。

### 怎样让科学预言被现实修正

本书希望成为一种能够靠自身完成自我实现的科学预言。但预言要能够被现实修正，否则它就是信仰。修正的办法只有一个：把本书所说的每一件事，都做成一条可以被记录、被核对、被推翻的记录。本书的知识库已经这样做了：每一个论点的原话、每一次修改、每一个被接受和被拒绝的反对意见，都在那里。读者可以带着问题、不同意见和实践经验来读它，然后把你的记录加进去。

### 参考

- Newton, I. (1687). *Philosophiæ Naturalis Principia Mathematica*.
- Einstein, A. (1905). Zur Elektrodynamik bewegter Körper. *Annalen der Physik*.
- Noether, E. (1918). Invariante Variationsprobleme.
- Nash, J. (1950). Equilibrium points in n-person games. *PNAS*.
- Meehl, P. (1954). *Clinical versus Statistical Prediction*.
- Simon, H. (1955). On a class of skew distribution functions. *Biometrika*.
- Lewis, D. (1969). *Convention*.
- Anderson, P. W. (1972). More is different. *Science*.
- Maynard Smith, J., & Price, G. (1973). The logic of animal conflict. *Nature*.
- Aumann, R. (1976). Agreeing to disagree. *Annals of Statistics*.
- Nicolis, G., & Prigogine, I. (1977). *Self-Organization in Nonequilibrium Systems*.
- Jervis, R. (1978). Cooperation under the security dilemma. *World Politics*.
- Axelrod, R. (1984). *The Evolution of Cooperation*.
- Merkle, R. (1987). A digital signature based on a conventional encryption function. *CRYPTO '87*.
- Littlestone, N., & Warmuth, M. (1994). The weighted majority algorithm. *Information and Computation*.
- Barabási, A.-L., & Albert, R. (1999). Emergence of scaling in random networks. *Science*.
- Tetlock, P. (2005). *Expert Political Judgment*.
- Saez, E., & Zucman, G. (2016). Wealth inequality in the United States since 1913. *Quarterly Journal of Economics*.
- Vaswani, A., et al. (2017). Attention is all you need. *NeurIPS*.
- Silver, D., et al. (2018). A general reinforcement learning algorithm that masters chess, shogi, and Go through self-play. *Science*.
- World Inequality Lab (2018). *World Inequality Report 2018*.
- Sutton, R. (2019). The bitter lesson.
- Jumper, J., et al. (2021). Highly accurate protein structure prediction with AlphaFold. *Nature*.
