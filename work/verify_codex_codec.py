import json,sys,hashlib
from pathlib import Path
root=Path(r'C:\Users\langr\Documents\Codex\2026-10-24\ni\outputs\personal-thought-archive')
sys.path.insert(0,str(root/'contributions/codex'))
import pkst_codec as c
sys.path.insert(0,str(root/'contributions/claude'))
from run_vectors_claude import EXTRA_CBOR_NEGATIVE
v=json.loads((root/'protocol/test-vectors.json').read_text(encoding='utf-8'))
for p in v['positive']:
    b=c.encode(p['value'])
    assert b.hex()==p['cbor_hex'] and c.cid(b)==p['cid'] and c.decode(b)==p['value'],p['name']
for name,h in EXTRA_CBOR_NEGATIVE:
    try:c.decode(bytes.fromhex(h))
    except (ValueError,UnicodeError):pass
    else:raise AssertionError(name)
for item in v['negative']:
    try:c.encode(item['value'])
    except (ValueError,UnicodeError):pass
    else:raise AssertionError(item['name'])
for item in v['negative_json']:
    try:c.loads(item)
    except ValueError:pass
    else:raise AssertionError(item)
(root/'protocol/decoder-negative-vectors.json').write_text(json.dumps([{'name':n,'hex':h,'expected':'reject'} for n,h in EXTRA_CBOR_NEGATIVE],indent=2),encoding='utf-8')
result={'positive_roundtrip_pass':len(v['positive']),'negative_encoder_rejected':len(v['negative'])+len(v['negative_json']),
        'negative_decoder_rejected':len(EXTRA_CBOR_NEGATIVE),'codec_sha256':hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest()}
(root/'contributions/codex/codec-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
