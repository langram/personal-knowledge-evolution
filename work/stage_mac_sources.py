import hashlib,json,sys,tarfile
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'outputs/personal-thought-archive'
sys.path.insert(0,str(base/'contributions/codex'))
from pkst_codec import cid
inbox=base/'coordination/.private/mac-inbox'
controls=inbox/'main';controls.mkdir(exist_ok=True)
codex=base/'contributions/codex/mac';(codex/'raw').mkdir(parents=True,exist_ok=True);(codex/'.private').mkdir(exist_ok=True)
claude=controls/'claude-raw';claude.mkdir(exist_ok=True)
receipt=json.loads((base/'reports/mac-main-receipt.json').read_text())
assert receipt['status']=='received-sha256-and-container-safety-verified'
def save(path,data):
    if path.exists():assert path.read_bytes()==data
    else:
        with path.open('xb') as f:f.write(data)
with tarfile.open(inbox/'pkst-mac-20261024.tar') as tar:
    manifest=tar.extractfile('manifest.jsonl').read()
    assert hashlib.sha256(manifest).hexdigest()=='222ce45fc6fb225b9696cfc8c388a6ffda7430c6ddb85b463c6f2734c3d4adf6'
    rows=[json.loads(line) for line in manifest.decode().splitlines()]
    sources=[r for r in rows if 'source_path' in r]
    assert len(sources)==987 and len({r['raw_path'] for r in sources})==987
    assert set(tar.getnames())=={r['raw_path'] for r in sources}|{'manifest.jsonl','create_mac_archive.py','collection-report.txt'}
    for name in ('manifest.jsonl','create_mac_archive.py','collection-report.txt'):
        save(controls/name,tar.extractfile(name).read())
    codex_rows=[];claude_rows=[];counts=Counter();total=0
    for r in sources:
        assert r['status']=='copied' and r['error'] is None
        assert r['size_before']==r['size_after']==r['bytes_copied']
        assert r['mtime_before_ns']==r['mtime_after_ns']
        data=tar.extractfile(r['raw_path']).read()
        assert len(data)==r['bytes_copied'] and hashlib.sha256(data).hexdigest()==r['sha256']
        key=cid(data,0x55);assert key==r['cidv1_raw'] and r['raw_path']=='raw/'+key+'.bin'
        counts[r['source_group']]+=1;total+=len(data)
        if r['source_group'] in ('codex_sessions','codex_archived_sessions'):
            save(codex/'raw'/(key+'.bin'),data)
            codex_rows.append({'status':'captured','raw_cid':key,'source_path':r['source_path'],
                'source_suffix':'.jsonl.zst' if r['source_path'].endswith('.jsonl.zst') else '.jsonl',
                'source_group':r['source_group'],'source_host':'macbook','bytes':len(data),'sha256':r['sha256'],
                'mtime_before_ns':str(r['mtime_before_ns']),'mtime_after_ns':str(r['mtime_after_ns']),
                'capture_rule':'fixed starting size; unchanged size and mtime; full archive and member hashes verified',
                'original_manifest_raw_cid':cid(manifest,0x55)})
        elif r['source_group'] in ('claude_projects','claude_history'):
            save(claude/(key+'.bin'),data);claude_rows.append(r)
        else:raise ValueError(r['source_group'])
    assert len(codex_rows)==936 and len(claude_rows)==51 and total==780445227
    save(codex/'.private/capture-mac-20261024.jsonl', ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in codex_rows).encode())
    save(controls/'claude-manifest.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in claude_rows).encode())
report={'recorded_at':datetime.now(timezone.utc).isoformat(),'status':'all-source-bytes-and-metadata-verified',
    'members_verified':987,'source_bytes':total,'source_counts':dict(counts),'manifest_sha256':hashlib.sha256(manifest).hexdigest(),
    'codex_raw':str(codex/'raw'),'codex_manifest':str(codex/'.private/capture-mac-20261024.jsonl'),
    'claude_staged_raw':str(claude),'claude_manifest':str(controls/'claude-manifest.jsonl'),
    'archive_script_handling':'raw preserved only; not executed'}
(base/'reports/mac-main-source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False),flush=True)
