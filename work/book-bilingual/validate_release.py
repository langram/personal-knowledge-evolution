"""Validate the prepared release without modifying published materials."""
import json
import re
import sqlite3
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from prepare import ARCHIVE, BASE, C, OUT, PUBLIC, WORK, sha, write_json
from verify_text import verify

BASE_COMMIT='33f5bcf8f371f354451f914a02ed8a0c54647ce4'
RESEARCH_COMMIT='4127d3f9ec4cfb7a61cbb2ea195cd6d64faef110'

def git(*args):
    return subprocess.check_output(['git',*args],cwd=PUBLIC)

def validate():
    checks=verify(); report=json.loads((ARCHIVE/'report.json').read_bytes())
    assert git('rev-parse','HEAD').decode().strip()==BASE_COMMIT
    assert git('rev-parse','codex/open-civilization-research-20261030').decode().strip()==RESEARCH_COMMIT
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    assert pointer['snapshot']==report['federated_snapshot']
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    hist=json.loads((OUT/'00-historical-sources.json').read_bytes())
    sys.path.insert(0,str(PUBLIC))
    from pkst_public import __main__ as api
    public_map={r['original_cid']:r['cid'] for r in json.loads((PUBLIC/'corpus/editorial-index.json').read_bytes())}
    with api.connect() as db:
        coverage=api.stats(db)
        assert coverage['catalog_events']==report['current_events']==212765
        assert coverage['published_events']==158309
        assert db.execute('PRAGMA integrity_check').fetchall()[0][0]=='ok'
        for e in events+hist:
            by_original=api.event(db,e['occurrence']);by_public=api.event(db,by_original['cid'])
            assert by_original==by_public and by_original['text']==e['text']
            assert (by_original['time'],by_original['role'])==(e['time'],e['role'])
            assert e['content'] in by_original['parts']
        for key in [report['document'],report['english_document'],report['book_landing']]+report['translations']:
            obj=api.object_value(db,public_map[key])['object']
            assert obj['original_cid']==key and obj['redactions']==[]
            if obj['original_schema']=='bb/translation@1':
                assert obj['object_projection']['source_document']['$link']==report['document']
                assert obj['object_projection']['document']['$link']==report['english_document']
        en=api.object_value(db,public_map[report['english_document']])['object']['object_projection']
        assert en['derived_from']['$link']==report['document']
    original=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    assert original.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]==212765
    for e in events+hist:
        row=original.execute('SELECT c.text FROM current_content c JOIN parts p ON p.content=c.cid WHERE p.occurrence=?',(e['occurrence'],)).fetchone()
        assert row[0]==e['text']
    original.close()
    for source,target in [('01-new-principles.zh.md','current.md'),('02-new-principles.en.md','current.en.md'),('book-readme.md','readme.md')]:
        assert (OUT/source).read_bytes()==(PUBLIC/'book'/target).read_bytes()
    editions=json.loads((PUBLIC/'history/editions.json').read_bytes());assert len(editions)==13
    for e in editions:
        assert sha((PUBLIC/e['file']).read_bytes())==e['sha256']
    e=editions[-1];assert e['translations']['en']['derived_from_sha256']==e['sha256']
    assert sha((PUBLIC/e['translations']['en']['file']).read_bytes())==e['translations']['en']['sha256']
    links_checked=0
    pages=[PUBLIC/'book/readme.md',PUBLIC/'README.md',PUBLIC/'history/README.md']
    pages+=list((PUBLIC/'archive/dossiers'/OUT.name).glob('*.md'))
    for page in pages:
        for target in re.findall(r'\]\(([^)]+)\)',page.read_text(encoding='utf-8')):
            prefix='https://github.com/langram/personal-knowledge-evolution/blob/main/'
            if target.startswith(prefix): path=PUBLIC/unquote(urlsplit(target).path.split('/blob/main/',1)[1])
            elif target.startswith(('http:','https:','mailto:','#','C:','/')): continue
            else: path=page.parent/unquote(target.split('#')[0])
            assert path.is_file(),(page,target)
            links_checked+=1
    changed=git('diff','--name-only','-z').decode().split('\0')
    shards=[p for p in changed if p.startswith(('corpus/objects/','corpus/events/'))]
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=PUBLIC,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    old_rows=0;added_objects=0;added_events=0
    for path in shards:
        proc.stdin.write((BASE_COMMIT+':'+path+'\n').encode());proc.stdin.flush()
        header=proc.stdout.readline().decode().split();assert header[1]=='blob',header
        data=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n'
        old={json.loads(line)['cid']:line for line in data.splitlines()}
        new={json.loads(line)['cid']:line for line in (PUBLIC/path).read_bytes().splitlines()}
        assert all(k in new and new[k]==v for k,v in old.items()),path
        assert list(new)==sorted(new),path
        old_rows+=len(old)
        if path.startswith('corpus/objects/'):added_objects+=len(new)-len(old)
        else:added_events+=len(new)-len(old)
    proc.stdin.close();assert proc.wait()==0
    prep=json.loads((WORK/'public-preparation.json').read_bytes())
    assert added_events==3 and added_objects==prep['update']['added_public_objects']
    assert len(json.loads((PUBLIC/'corpus/editorial-index.json').read_bytes()))==coverage['editorial_objects']
    result={'status':'pass','text':checks,'editions':13,'api_source_roundtrips':len(events+hist),
        'translation_relationships':len(report['translations']),'public_events':coverage['published_events'],
        'public_objects':coverage['public_objects'],'local_links_checked':links_checked,
        'historical_corpus_rows_byte_preserved':old_rows,'added_events':added_events,'added_public_objects':added_objects,
        'protected_research_branch':RESEARCH_COMMIT,'baseline_commit':BASE_COMMIT,
        'boundary':'Existing source citations retained; external historical claims not re-researched in this publication check.'}
    write_json(WORK/'release-verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='text'},ensure_ascii=False))

if __name__=='__main__':validate()
