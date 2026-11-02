"""Two bounded edits in chapter 16, aligned across languages."""
from prepare import WORK

EDITS=[
    {'id':'agi-institutional-imagination','chapter':16,'mode':'insert-heading',
     'anchors':{'zh':'### 怎样理解对未来的担心','en':'### Taking Concerns About the Future Seriously'},
     'text':{lang:(WORK/'fragments'/f'01-agi-institutional-imagination.{lang}.md').read_text(encoding='utf-8').rstrip() for lang in ('zh','en')},
     'rationale':'Integrate the author scenario after control of AI; distinguish hypotheses about goals, information access, institutional alternatives and demonstrated safety.'},
    {'id':'chapter-16-next-step','chapter':16,'mode':'replace',
     'anchors':{'zh':'这也不能靠一句“将来的 AI 会更强”就完成。','en':'Equally, “future AI will be stronger” is not an institutional design.'},
     'text':{'zh':'这样的改变，最终要落实到知识怎样共享、个人怎样参与、共同决策怎样产生、资源怎样分配这些具体机制之中。下一步，我们就要把这个文明智能的大脑展开，看看动态权重究竟怎样把许多个体的知识和行动连接起来，又怎样避免把这种连接重新变成少数节点对其他人的支配。',
             'en':"These changes must ultimately take concrete form: how knowledge is shared, how individuals participate, how collective decisions are made, and how resources are allocated. The next chapter examines how dynamic weights might connect many individuals' knowledge and actions into a collective capacity—and how that connection might avoid becoming another means for a few nodes to dominate the rest."},
     'rationale':'Carry the new distinction between collective capability and domination into the existing next chapter on dynamic weights.'}
]
