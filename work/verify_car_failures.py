import json,sys,tempfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_car import CarWriter,inspect_car,varint
from pkst_codec import encode,cid,cid_bytes,link
def envelope(header,blocks):
    b=encode(header)
    return varint(len(b))+b+b''.join(varint(36+len(v))+cid_bytes(k)+v for k,v in blocks)
passed=[]
with tempfile.TemporaryDirectory(prefix='pkst-car-',dir=base.parents[1]/'work') as tmp:
    root=Path(tmp);raw=root/'raw';raw.mkdir()
    evidence=b'raw\r\n';raw_key=cid(evidence,0x55);(raw/(raw_key+'.bin')).write_bytes(evidence)
    obj={'schema':'test/evidence','raw':link(raw_key)};b=encode(obj);key=cid(b)
    p=root/'good.car';w=CarWriter(p);assert w.put(obj)==key;w.finish([key],[raw_key])
    assert inspect_car(p,raw)['blocks']==1;passed.append('valid roundtrip and external raw')
    h={'version':1,'roots':[link(key)]};good=p.read_bytes()
    cases={'truncated section':good[:-1], 'hash mismatch':good[:-1]+bytes([good[-1]^1]),
      'duplicate block':envelope(h,[(key,b),(key,b)]),
      'missing root':envelope(h,[]),
      'non-link root':envelope({'version':1,'roots':['x']},[(key,b)]),
      'boolean version':envelope({'version':True,'roots':[link(key)]},[(key,b)]),
      'nonminimal varint':b'\x80\x00', 'truncated varint':b'\x80'}
    for name,data in cases.items():
        q=root/'bad.car';q.write_bytes(data)
        try:inspect_car(q,raw)
        except (ValueError,FileNotFoundError):passed.append(name)
        else:raise AssertionError(name)
    (raw/(raw_key+'.bin')).write_bytes(b'corrupted')
    try:inspect_car(p,raw)
    except ValueError:passed.append('corrupt external raw')
    else:raise AssertionError('corrupt external raw accepted')
result={'cases':passed,'all_pass':True,'scope':'CAR framing/hash/closure rejection; not full semantic schema validation'}
(base/'reports/car-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
