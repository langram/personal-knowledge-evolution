import hashlib,json,tarfile,unicodedata
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
source=Path('C:/Users/langr/OneDrive/PKST-transfer/pkst-mac-20261024.tar')
dest=base/'coordination/.private/mac-inbox/pkst-mac-20261024.tar'
expected='6ec0bbc81f11c95e3a9c62a515d937fac01f15375e56d39860c057c493e24c37'
assert source.stat().st_size==781793280
if not dest.exists():
    temp=dest.with_suffix('.receiving')
    h=hashlib.sha256();n=0
    with source.open('rb') as src,temp.open('xb') as out:
        while part:=src.read(4*1024*1024):
            out.write(part);h.update(part);n+=len(part)
            if n%(128*1024*1024)==0:print(json.dumps({'copied_bytes':n}),flush=True)
    assert n==781793280 and h.hexdigest()==expected
    temp.rename(dest)
h=hashlib.sha256()
with dest.open('rb') as f:
    for data in iter(lambda:f.read(4*1024*1024),b''):h.update(data)
assert h.hexdigest()==expected
names=set();folded=set();control=[];members=[]
with tarfile.open(dest) as tar:
    for m in tar:
        p=PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts and str(p)==m.name
        assert not any(c in m.name for c in ('\\',':','\0'))
        fold=unicodedata.normalize('NFC',m.name).casefold()
        assert fold not in folded;folded.add(fold);names.add(m.name)
        members.append({'name':m.name,'bytes':m.size})
        if '/' not in m.name:control.append({'name':m.name,'bytes':m.size})
assert len(names)==990
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'received-sha256-and-container-safety-verified',
    'source':str(source),'received':str(dest),'bytes':dest.stat().st_size,'sha256':h.hexdigest(),
    'tar_members':len(names),'top_level_files':control,'source_member_hashes':'pending manifest inspection'}
(base/'reports/mac-main-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(dest.parent/'main-member-index.json').write_text(json.dumps(members,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
