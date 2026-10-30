"""Editorial decisions and bounded external evidence, separate from author originals."""
import json
from prepare import OUT, write_json

def notes():
    sources=[
      ('deterrence','Five Things About Deterrence','https://nij.ojp.gov/topics/articles/five-things-about-deterrence','研究机构对威慑证据的综合说明，前轮已读；支持确定性与严厉程度的区别，不证明未来AI消除恶意。'),
      ('c2pa','C2PA Specification 2.1','https://spec.c2pa.org/specifications/specifications/2.1/specs/C2PA_Specification.html','前轮已读相关规范；来源声明、签名与内容可信判断有区别；不声称这是最新版本。'),
      ('firmware','NIST SP 800-193','https://csrc.nist.gov/pubs/sp/800/193/final','前轮已读官方说明；固件保护、检测、恢复，不保证任何特定硬件已经实现。'),
      ('attestation','RFC 9334','https://www.rfc-editor.org/rfc/rfc9334.html','前轮已读新鲜度相关段落；证明的时效及核验后状态可能变化。'),
      ('transparency','RFC 9162','https://www.rfc-editor.org/rfc/rfc9162.html','前轮已读日志一致性和分叉视图边界；独立核对仍是额外机制。'),
      ('anger-paper','Kjærvik and Bushman 2024','https://doi.org/10.1016/j.cpr.2024.102414','论文标识；出版商正文访问受限，本次数字与结论依据研究机构的直接说明，不声称精读全文。'),
      ('anger-institution','Ohio State research report','https://news.osu.edu/breathe-dont-vent-turning-down-the-heat-is-key-to-managing-anger/','前轮及本轮读正文；154项研究、10189名参与者；不是全部虚拟游戏或脑机接口的效果判断。'),
      ('gaming','WHO gaming disorder FAQ','https://www.who.int/standards/classifications/frequently-asked-questions/gaming-disorder','前轮已读官方说明；重在失控及显著功能受损，不以题材偏好诊断。'),
      ('ordinal','Turing 1939 ordinal logics and Feferman preface','https://people.math.ethz.ch/~halorenz/4students/Literatur/TuringOrdinalLogic.pdf','本轮读相关前言及原文入口；理论逐步加强与不完备性边界，不声称完成全部技术证明审阅。'),
      ('category','Riehl Category Theory in Context','https://emilyriehl.github.io/files/context.pdf','本轮读对偶定义与相关米田说明；反范畴保留对象并反转态射，不等于对象态射互换。'),
      ('applied-category','Fong and Spivak Seven Sketches','https://ocw.mit.edu/courses/18-s097-applied-category-theory-january-iap-2019/a4175d61479a35340d6307ae5e48ef5a_18-s097iap19textbook.pdf','书稿已有来源，本轮重开；子对象分类器与内部逻辑的数学角色，不证明意识或物理探测器。'),
      ('fixed-point','Bindel Numerical Methods for Data Science','https://www.cs.cornell.edu/~bindel/nmds/00-Background/04-Calculus.html','本轮读压缩映射定理条件；文中三个线性迭代例子为独立可直接检查的反例与对照。'),
      ('kolmogorov','Vitányi How Incomputable Is Kolmogorov Complexity','https://homepages.cwi.nl/~paulv/papers/incomp.pdf','本轮读相关不可计算性与压缩近似边界；不把压缩结果当成最短程序证明。'),
      ('computation-thermodynamics','Bennett Notes on Landauer principle','https://arxiv.org/abs/physics/0210005','本轮读作者摘要；逻辑不可逆操作与环境熵变化，不用程序字符数计算硬件能耗。'),
      ('action','Tong Classical Dynamics section 2','https://www.damtp.cam.ac.uk/user/tong/dynamics/dynhtml/S2.html','本轮读作用量变分及Euler-Lagrange推导；驻值条件与绝对最小能量有区别。'),
      ('dissipation','Prigogine Time structure and fluctuations','https://pubmed.ncbi.nlm.nih.gov/17738519/','本轮读论文摘要；非平衡可产生有序耗散结构。Nobel网站全文访问403，未据此声称全文已读。'),
      ('bell','Giustina et al 2015 Bell test','https://arxiv.org/abs/1511.03190','本轮读作者摘要；实验对相应局域实在论模型的约束，不据此给作者构想补造量子方程。'),
      ('genetics','Genetics of child aggression a systematic review','https://pmc.ncbi.nlm.nih.gov/articles/PMC11167064/','前轮与本轮读摘要及相关正文；87项研究，多种结果不一致，不支持单基因政治归因。'),
      ('cooperation','Nowak Five Rules for the Evolution of Cooperation','https://pmc.ncbi.nlm.nih.gov/articles/PMC3279745/','前轮读论文相关段落；本轮访问触发验证页，沿用已读材料；机制有条件，不是普遍TFT定理。'),
      ('contact','Pettigrew and Tropp 2006 contact meta-analysis','https://pubmed.ncbi.nlm.nih.gov/16737372/','前轮读论文摘要；群体接触与偏见变化，不证明一次顿悟消除冲突。'),
      ('weights','Littlestone and Warmuth Weighted Majority','https://homepages.math.uic.edu/~lreyzin/papers/littlestone94.pdf','前轮检索到论文摘要，本轮再次打开扫描PDF，无可提取正文；只用明确任务存在加权算法性能界这一层结论，不引具体界或假称全文证明复核。'),
      ('unison','Unison The Big Idea','https://www.unison-lang.org/docs/the-big-idea/','前轮读官方说明；程序定义内容寻址先例，不证明所有Merkle生态更快。'),
      ('metr','METR task time horizons','https://metr.org/time-horizons/','前轮读评估说明，页面标注更新为2026-09-08；引用任务范围和成功率边界，不给出AGI实现日期。'),
      ('commons','Ostrom Beyond Markets and States','https://dlc.dlib.indiana.edu/dlc/items/484f4147-bdce-4d55-9b8d-fe61f3b2d37b','前轮读机构存档及所附稿件相关内容；正文使用概述，无直接引文；具体环境下的多中心治理不等于普遍最优组织。')]
    write_json(OUT/'external-sources.json',[{'id':i,'title':t,'url':u,'reading_scope':scope,'checked_date':'2026-10-30','full_page_copy':False} for i,t,u,scope in sources])
    text='''# 本次编辑说明与讨论覆盖

## 版本与放置

基于第八版全文新增《个人信息采集、数据主权与技术落地》，放在合作反馈之后、一个人的云存储实践之前；《对理论基础与实践可行性的自我反思》放在后记之后，成为全文最后的附录。原版其他字节保留。两处插入及逆向恢复由脚本校验。

## 来源与角色

本轮仅导入2026年10月30日本会话的四条作者消息和三条AI完整答复，截止作者明确要求整合的消息；不把此前“先讨论”的要求误解为提前授权，也不把本次工具活动、隐藏推理或环境指令当作作品来源。00-开头的七个文本文件保留完整原话，包括尚未采纳、后来需要修正的表述。来源时间不是思想的首创时间。

正文选取作者技术方案和两项回应，保留叙述顺序与表达，修改错字、语序和必要成立条件。附录保留作者关于现实可行性的要求，其余评估以本书立场写成第一人称的编辑建议；不能反过来记为作者此前说过或已逐项接受。原话、编辑文本、逐字符改动和未改旧稿分别可核对。

## 讨论覆盖

| 讨论内容 | 正文或附录中的落点 |
|---|---|
| 有益公共知识与个人利益保护 | 正文开篇及私密、事件、公共三种范围 |
| 可靠记录的事前威慑、AI缓冲、反馈学习 | 正文前三节，补入预期后果、行动约束和责任区分 |
| 固定设备与穿戴设备、待机、唤醒、接棒 | 正文设备协同，包含访客、提示灯、授权与缺口 |
| 设备、个人、厂家及公共密钥 | 正文密钥分工、固件验证、来源与事实边界 |
| 自然视野与事件授权 | 正文权限拆分、多方证据及拒绝授权难题 |
| 组织可信、按需分配与恶意动机 | 正文能力与动机的双重设计、攻击检查与参与规则 |
| 虚拟文学影视游戏与脑机接口 | 正文独立一节，保留假说并区分表达、调节、功能损害 |
| 疑问、回应与补足论证的写作方式 | 新章多处直接展开异议与回应；不把尚未解决的问题写成已解决 |
| 数学、范畴论与基础科学 | 附录的无穷、自指、对偶体、不动点、极值、计算代价、物理及意识各节 |
| 生理心理、合作、决策与组织可行性 | 附录后半，继承并拓展上一轮综合评估 |
| 可以自我实现的科学预言 | 附录结尾的条件性预测、比较方法和修正条件 |

## 关键编辑判断

“无法预测”没有写成“没有因果关系”；可靠记录没有写成事前绝对阻断；更高理性没有写成共同目标；更全面采集没有写成风险必然更低。非普遍偏好没有直接病理化。虚拟宣泄及脑机接口效果保留为待验证假说。

数学评估区分定义、定理、模型与比喻：范畴对偶不交换对象与态射；不动点存在不保证迭代收敛；短描述不保证低能耗；理论扩展不自动取消不完备性。物理评估区分作用量、能量、熵和算法指标，并要求可观测预测。没有声称完成新公理体系、统一物理或意识理论的证明，也没有用旧理论的存在否定探索本身。

价值原则、经验解释与工程方案分别评估。附录提出的是检验计划，不是本次已经实施的社会实验或设备验收；未部署音视频采集，未申请新设备权限，未修改已有研究项目。

## 外部证据范围

来源逐项记录于external-sources.json。规范与研究只支持所引用的局部论点，不被用于证明整套新体制。全文不可访问或扫描文本不可提取的情况保留说明；未复制文献全文。现有技术的可用性与本项目已经实现的能力分开陈述。
'''
    (OUT/'04-editorial-notes.md').write_bytes(text.encode())
    # Arithmetic examples are checked independently of their literary presentation.
    examples={}
    for name,f in [('negative',lambda x:-x),('double',lambda x:2*x),('half',lambda x:x/2)]:
        seq=[1]
        for _ in range(6): seq.append(f(seq[-1]))
        assert f(0)==0
        examples[name]=seq
    assert examples['negative']==[1,-1,1,-1,1,-1,1]
    assert examples['double'][-1]==64 and examples['half'][-1]==1/64
    daily=2_000_000/8*86400
    assert daily/1e9==21.6
    write_json(OUT/'example-checks.json',{'status':'pass','fixed_point_iterates':examples,
        'assumed_video_bitrate_bits_per_second':2000000,'daily_decimal_GB':daily/1e9,'annual_decimal_TB':daily*365/1e12,
        'scope':'Checks the stated elementary examples and storage arithmetic; not a proof or empirical validation of the general theory.'})
    print(json.dumps({'external_sources':len(sources),'notes_written':True},ensure_ascii=False))

if __name__=='__main__': notes()
