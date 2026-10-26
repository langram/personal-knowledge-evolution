import sys,json,hashlib,tarfile,unicodedata
from pathlib import Path,PurePosixPath
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import cid,decode,links
from pkst_car import inspect_car
peer=base/'contributions/claude'
tar_path=base/'coordination/.private/mac-inbox/pkst-claude-supplement-20261024.tar'
summary=json.loads((peer/'mac-supplement-conversion-summary-20261024T084015Z.json').read_text())
assert hashlib.sha256(tar_path.read_bytes()).hexdigest()=='c86787dc410f94d616491361859e10b1c1353183bc95a3b6839aa495419f2fb5'
archive={};folded=set()
with tarfile.open(tar_path) as tar:
    for member in tar:
        p=PurePosixPath(member.name)
        assert member.isfile() and not p.is_absolute() and '..' not in p.parts
        assert not any(c in member.name for c in ('\\',':','\0')) and str(p)==member.name
        fold=unicodedata.normalize('NFC',member.name).casefold()
        assert fold not in folded;folded.add(fold)
        data=tar.extractfile(member).read()
        key=cid(data,0x55)
        assert (peer/'raw'/(key+'.bin')).read_bytes()==data
        archive[member.name]={'cid':key,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    manifest=[json.loads(x) for x in tar.extractfile('supplement-manifest.jsonl').read().decode().splitlines()]
assert len(manifest)==435 and len(archive)==437
assert {r['archive_path'] for r in manifest}==set(archive)-{'supplement-manifest.jsonl','supplement-report.txt'}
for row in manifest:
    actual=archive[row['archive_path']]
    assert actual['sha256']==row['sha256'] and actual['bytes']==row['size_before']==row['size_after_hash']
    assert not row['changed_during_hash']
car=base/summary['car']
assert hashlib.sha256(car.read_bytes()).hexdigest()==summary['car_sha256']
verification=inspect_car(car,peer/'raw')
assert verification['blocks']==439 and verification['external_raw_verified']==328
root_data=(peer/'objects'/(summary['snapshot']+'.cbor')).read_bytes()
assert cid(root_data)==summary['snapshot']
root=decode(root_data)
activity_objects=[]
for key in links(root['roots']):
    data=(peer/'objects'/(key+'.cbor')).read_bytes();assert cid(data)==key
    activity_objects.append(decode(data))
# No source import can be mistaken for a message in this package.
assert all(o['schema']=='pkst/activity@0.1' for o in activity_objects)
assert len(activity_objects)==438
by_path={o['coverage']['archive_path']:o for o in activity_objects if 'archive_path' in o['coverage']}
assert len(by_path)==437 and set(by_path)==set(archive)
for name,actual in archive.items():
    activity=by_path[name];coverage=activity['coverage']
    assert coverage['bytes']==actual['bytes'] and coverage['sha256']==actual['sha256']
    assert activity['inputs']==[{'$link':actual['cid']}] and activity['outputs']==[]
    assert coverage['host']=='macbook' and coverage['parsed'] is False
for row in manifest:
    coverage=by_path[row['archive_path']]['coverage']
    assert coverage['mac_source_path']==row['source_path']
    assert coverage['mac_mtime_ns']==str(row['mtime_before_ns'])==str(row['mtime_after_hash_ns'])
report={'status':'passed','snapshot':summary['snapshot'],'tar_bytes':tar_path.stat().st_size,
    'tar_sha256':hashlib.sha256(tar_path.read_bytes()).hexdigest(),'members_verified_against_raw':437,
    'source_members_verified_against_mac_manifest':435,'safe_path_and_type_checks':True,
    'car_verification':verification,'root_activities_verified':438,'occurrences':0,
    'member_activity_bytes_and_raw_links_verified':437,'source_path_and_exact_mtime_provenance_verified':435,
    'scope':'raw archive and provenance; no native conversation body in this supplement'}
(base/'reports/mac-supplement-independent-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
