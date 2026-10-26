import json,sqlite3
from book import DATA,WORK,BASE
from collections import Counter
used=json.loads((WORK/'used-sources.json').read_text(encoding='utf-8'))
print('USED',len(used),Counter(r.get('platform','file') for r in used.values()))
for ref in ['R48220','R1857','R54886','ORIGINAL','META-THEORY','E002','R47840','SEED-R14-0']:
 r=DATA[ref];print(ref,{k:v for k,v in r.items() if k!='text'})
plan=json.loads((BASE/'contributions/codex/new-principles-20261026/semantic-plan.json').read_text(encoding='utf-8'))
for n in plan['nodes']:print(n['id'],n['label'],n['chapters'])
print('timeline sample',plan['timeline'][:2])
ptr=json.loads((BASE/'contributions/codex/catalog/current.json').read_text())
db=sqlite3.connect((BASE/ptr['database']).as_uri()+'?mode=ro',uri=True)
for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='view'"):print(r)
