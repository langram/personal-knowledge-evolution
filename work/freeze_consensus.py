import json,hashlib,sys
from datetime import datetime,timezone
from pathlib import Path
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import cid
protocol=(base/'protocol/PKST-0.1.md').read_bytes()
expected='bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
assert cid(protocol,0x55)==expected
receipts=[]
for name in ['contributions/claude/ACK-N3.md','contributions/claude/ACK-N3.1.md','contributions/claude/crosscheck-codex-car.json','reports/claude-independent-verification.json']:
    data=(base/name).read_bytes();receipts.append({'path':name,'raw_cid':cid(data,0x55),'sha256':hashlib.sha256(data).hexdigest()})
doc={'schema':'pkst.consensus-record@0.1','recorded_at':datetime.now(timezone.utc).isoformat(),
     'status':'accepted-by-codex-and-claude','revision':'PKST-0.1 / N3.1',
     'protocol':{'path':'protocol/PKST-0.1.md','raw_cid':expected,'sha256':hashlib.sha256(protocol).hexdigest(),'bytes':len(protocol)},
     'receipts':receipts,'meaning':'Agreement on serialization and evidence contract; not user adoption of any extracted belief',
     'note':'The protocol file retains its historical candidate heading to preserve bytes. This separate dated receipt records subsequent acceptance.',
     'future_changes':'New immutable protocol version and explicit migration; do not silently replace bytes behind this accepted CID'}
out=base/'protocol/consensus.json'
with out.open('x',encoding='utf-8') as f:json.dump(doc,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':doc['status'],'protocol':expected,'receipts':len(receipts)}))
