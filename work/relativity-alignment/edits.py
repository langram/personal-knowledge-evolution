"""Seven bounded edits per language, including consistent title references."""
from prepare import WORK

AUTHOR=['AUTHOR-RELATIVITY-ALIGNMENT']
def fragment(stem):
    return {lang:(WORK/'fragments'/f'{stem}.{lang}.md').read_text(encoding='utf-8').rstrip() for lang in ('zh','en')}

EDITS=[
 {'id':'book-title','chapter':0,'mode':'substring',
  'anchors':{'zh':'# 新原理：现代科学与人类文明的构造','en':'# New Principles: Modern Science and the Making of Human Civilization'},
  'text':{'zh':'# 新原理：社会科学的数学原理','en':'# Nova Principia: Mathematical Principles of Social Science'},
  'sources':AUTHOR,'rationale':'Adopt the author suggested Chinese subtitle and Latin-style English title; preserve historical edition titles.'},
 {'id':'title-purpose','chapter':1,'mode':'append',
  'anchors':{'zh':'除了这些心理学层面上的因素，本文命名的最主要原因在于文章的内容。',
             'en':'In an age of information overload, attention is scarce.'},
  'text':{'zh':'我把这本书命名为《新原理：社会科学的数学原理》，英文主标题采用拉丁语形式 Nova Principia。这个名字表达的是一个研究方向：从存在与变化、构造与演化的基本问题出发，寻找能够连接自然科学、人的认知与社会合作的共同语言，并把它落实到可以试验、可以修正的制度与技术中。它不是宣布我已经完成了一套与牛顿体系相当的定理，也不意味着人的需要与价值能够被一条公式包办。正因为这个目标尚未完成，书中既要大胆提出联系，也要把需要证明、需要实验和需要共同选择的部分说清楚。',
          'en':'I call this book Nova Principia: Mathematical Principles of Social Science. The title names a direction of inquiry: beginning with existence and change, construction and evolution, I seek a language that can connect natural science, human cognition, and social cooperation, then inform institutions and technologies that can be tested and revised. It does not announce a completed system of theorems comparable to Newton\'s, or suggest that one equation can settle human needs and values. Because the project remains unfinished, the book must both propose connections boldly and distinguish what requires proof, what requires experiments, and what requires shared choices.'},
  'sources':AUTHOR,'rationale':'Explain the proposed title within a standalone preface, distinguishing research ambition from established mathematical results.'},
 {'id':'title-reference','chapter':1,'mode':'substring',
  'anchors':{'zh':'用《新原理》这一标题来命名','en':'*New Principles*'},
  'text':{'zh':'用《新原理：社会科学的数学原理》这一标题来命名','en':'*Nova Principia*'},
  'sources':AUTHOR,'rationale':'Keep the preface reference consistent with the new standalone title.'},
 {'id':'title-foundation','chapter':1,'mode':'substring',
  'anchors':{'zh':'因此，也许更准确的标题应该是"数学与科学的统一原理"。',
             'en':'In that sense, a more precise title for this undertaking might be *Unifying Principles of Mathematics and Science*.'},
  'text':{'zh':'这种关于数学与科学统一底座的探索，也构成了本书讨论社会科学数学原理的出发点。',
          'en':'This search for common foundations in mathematics and science also provides the starting point for the book\'s inquiry into mathematical principles of social science.'},
  'sources':AUTHOR,'rationale':'Retain the original unification ambition while removing an alternative-title proposal inconsistent with the requested new title.'},
 {'id':'cognitive-reference-frames','chapter':7,'mode':'insert-heading',
  'anchors':{'zh':'## 合作、冲突与社会结构的形成','en':'## Cooperation, Conflict, and the Formation of Social Structures'},
  'text':fragment('01-reference-frames'),'sources':['GEMINI-01-AUTHOR','GEMINI-02-AUTHOR','GEMINI-03-AUTHOR','GEMINI-04-AUTHOR','GEMINI-05-AUTHOR',*AUTHOR],
  'rationale':'Insert a complete chapter between consciousness and social cooperation; develop the author reference-frame trajectory without importing Gemini assertions as scientific proof.'},
 {'id':'multilevel-alignment','chapter':24,'mode':'insert-heading',
  'anchors':{'zh':'### 人类的道路不只有电车难题中的两条轨道',"en":"### Humanity has more than the trolley problem's two tracks"},
  'text':fragment('02-alignment'),'sources':AUTHOR,
  'rationale':'Extend the chain-hammer analogy into local versus collective alignment, two conditional risk pathways, a typed fixed-point proposal and ecological constraints.'},
 {'id':'relativity-alignment-reflection','chapter':32,'mode':'insert-heading',
  'anchors':{'zh':'### 怎样使科学预言能够被现实修正','en':'### Letting reality revise a scientific anticipation'},
  'text':fragment('03-reflection'),'sources':AUTHOR,
  'rationale':'Add explicit validation and counterexample requirements; semantic representations, institutional coordination and technical alignment remain separately testable.'},
]
