"""One bilingual insertion; all existing manuscript bytes remain unchanged."""
from prepare import WORK

EDITS=[{'id':'persuasion-and-voluntary-pilots','chapter':16,'mode':'insert-heading',
    'anchors':{'zh':'### 获取合作信息，不等于全面接管个人生活',
               'en':"### Cooperation Requires Information, Not Control of Everyone's Life"},
    'text':{lang:(WORK/'fragments'/f'01-persuasion-and-voluntary-pilots.{lang}.md').read_text(encoding='utf-8').rstrip() for lang in ('zh','en')},
    'rationale':'Add the author optimistic counterpoint after the dystopian scenario; retain peaceful persuasion and satire while distinguishing intelligence, goals, total costs, and voluntary participation.'}]
