import hashlib,io,json,sys,uuid,warnings,zipfile
from pathlib import Path
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base/'outputs/personal-thought-archive/contributions/codex'))
from capture_gemini_takeout import capture
from pkst_codec import cid
probe=base/'work'/('gemini-capture-probe-'+uuid.uuid4().hex[:8]);probe.mkdir()
assert probe.resolve().is_relative_to((base/'work').resolve())
source=probe/'fixture.zip'
with warnings.catch_warnings():
    warnings.simplefilter('ignore',UserWarning)
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_STORED) as z:
        z.writestr('Takeout/我的活动记录/Gemini Apps/记录.json','[{"text":"原文\r\n组合 é"}]')
        z.writestr('../outside.txt',b'never extracted as a path')
        z.writestr('duplicate.txt',b'first')
        z.writestr('duplicate.txt',b'second')
original=source.read_bytes();root=probe/'capture';good=capture(source,root)
assert good['captured_members']==4 and not good['failures']
assert (root/'raw'/(good['original']['raw_cid']+'.bin')).read_bytes()==original
rows=[json.loads(l) for l in (root/good['manifest']).read_text(encoding='utf-8').splitlines()]
assert len([r for r in rows if r['member_name']=='duplicate.txt'])==2
assert len({r['raw_cid'] for r in rows if r['member_name']=='duplicate.txt'})==2
assert not (probe/'outside.txt').exists() and not (root/'outside.txt').exists()
for r in rows:assert cid((root/'raw'/(r['raw_cid']+'.bin')).read_bytes(),0x55)==r['raw_cid']
with zipfile.ZipFile(source) as z:
    info=z.infolist()[-1];offset=info.header_offset+30+len(info.filename.encode())+len(info.extra)
damaged=bytearray(original);damaged[offset]^=1
badpath=probe/'corrupt.zip';badpath.write_bytes(damaged)
bad=capture(badpath,probe/'corrupt-capture')
assert bad['status']=='partial' and bad['captured_members']==3 and len(bad['failures'])==1
report={'status':'passed','checks':['Original ZIP byte identity','Unicode and CRLF preservation',
    'Duplicate names keep distinct member ordinals','Archive paths never used as filesystem paths',
    'Member CID recomputation','CRC corruption explicitly reported; valid members retained'],
    'scope':'Synthetic capture verifier, not actual Gemini account coverage'}
(base/'outputs/personal-thought-archive/reports/gemini-capture-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
