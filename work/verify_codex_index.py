import hashlib,json,sqlite3,sys
from pathlib import Path
from compression import zstd
root=Path(r'C:\Users\langr\Documents\Codex\2026-10-24\ni\outputs\personal-thought-archive\contributions\codex')
sys.path.insert(0,str(root))
from pkst_codec import cid,encode
con=sqlite3.connect((root/'.private/windows-index.sqlite').as_uri()+'?mode=ro',uri=True)
con.row_factory=sqlite3.Row
manifest=[json.loads(l) for l in (root/'.private/capture-20261024T070147Z-4f83698c.jsonl').read_text(encoding='utf-8').splitlines()]
byraw={r['raw_cid']:r for r in manifest}
allrows=con.execute('SELECT * FROM message ORDER BY raw,start').fetchall()
samples=[allrows[i] for i in range(0,len(allrows),max(1,len(allrows)//32))][:32]
checked=0
for r in samples:
    entry=byraw[r['raw']]
    opener=zstd.open if entry['source_suffix'].endswith('.zst') else open
    with opener(root/'raw'/(r['raw']+'.bin'),'rb') as f:
        f.seek(r['start']);line=f.read(r['end']-r['start'])
    p=json.loads(line)['payload']
    parts=[x['text'] for x in p['content'] if isinstance(x,dict) and x.get('type') in ('input_text','output_text','text') and isinstance(x.get('text'),str)]
    expected=[cid(encode({'schema':'pkst/content@0.1','media_type':'text/plain','text':text})) for text in parts]
    assert expected==json.loads(r['content_cids'])
    assert p['role']==r['native_role']
    for key,text in zip(expected,parts):
        assert con.execute('SELECT text FROM content WHERE cid=?',(key,)).fetchone()[0]==text
    checked+=1
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert con.execute("SELECT COUNT(*) FROM message WHERE native_role='user' AND actor_kind='human'").fetchone()[0]==0
result={'index_integrity':'ok','exact_raw_anchor_samples':checked,'source_files':len(manifest),
        'messages':len(allrows),'user_envelope_not_automatically_human':True,
        'content_address_check':'all parts in 32 deterministic raw-anchored samples',
        'scope':'Sampling verifies the derived index against raw bytes, not semantic accuracy.'}
(root/'index-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
