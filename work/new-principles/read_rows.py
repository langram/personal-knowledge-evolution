import json,sys
from pathlib import Path
wanted={int(x) for x in sys.argv[1:]}
for i,line in enumerate(Path('work/new-principles/retrieval.jsonl').open(encoding='utf-8')):
 if i in wanted:
  r=json.loads(line);print('\nROW',i,r['occurrence'],r['platform'],r['time'],'\n'+r['text'])
