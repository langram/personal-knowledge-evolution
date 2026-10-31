"""Check source bytes, reversible Chinese edits, complete bilingual structure and provenance."""
import difflib
import json
import re
from prepare import ARCHIVE, OLD, OUT, WORK, cid, sha, write_json
from assemble import TITLE, headings, urls

def verify():
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    assert [e['ref'] for e in events]==['PREVIOUS-EDITION-RESPONSE','BILINGUAL-REQUEST','README-LANGUAGE-CHOICE']
    for e in events:
        c=e['capture']; data=(ARCHIVE/'raw'/(c['raw']+'.bin')).read_bytes()
        assert sha(data)==c['sha256'] and cid(data,0x55)==c['raw'] and len(data)==c['bytes']
        record=json.loads(data); p=record['payload']
        assert p['role']==e['role'] and record['timestamp']==e['time']
        if e['role']=='assistant': assert p.get('phase')=='final_answer'
        assert any(x.get('text')==e['text'] for x in p['content'])
        with open(c['native_file'],'rb') as stream:
            stream.seek(c['native_start']); assert stream.read(c['bytes'])==data
        assert sha(e['text'].encode())==e['text_sha256']
        assert (OUT/('00-'+e['ref'].lower()+'.txt')).read_bytes()==e['text'].encode()
    assert '中英双语简介' in events[-1]['text']
    hist=json.loads((OUT/'00-historical-sources.json').read_bytes())
    assert [e['ref'] for e in hist]==['DEVELOPMENT-GOALS','AUTHOR-REVISION']
    assert all(e['already_imported'] and e['role']=='user' for e in hist)
    assert '重要的不是让能力去逼近正态分布' in hist[-1]['text']
    old=OLD.read_bytes(); zh=(OUT/'01-new-principles.zh.md').read_bytes(); en=(OUT/'02-new-principles.en.md').read_bytes()
    m=json.loads((OUT/'zh-revision-manifest.json').read_bytes())
    assert sha(old)==m['baseline_sha256'] and sha(zh)==m['result_sha256']
    assert len(m['changes'])==10
    a,b=old.decode(),zh.decode(); cursor=0; built=''
    for c in m['changes']:
        x,y=c['old_char_span'];u,v=c['new_char_span']
        assert a[x:y]==c['before'] and b[u:v]==c['after']
        assert sha(c['before'].encode())==c['before_sha256'] and sha(c['after'].encode())==c['after_sha256']
        built+=a[cursor:x];assert len(built)==u
        built+=c['after'];assert len(built)==v;cursor=y
    assert (built+a[cursor:]).encode()==zh
    reverse=b
    for c in reversed(m['changes']):
        u,v=c['new_char_span'];reverse=reverse[:u]+c['before']+reverse[v:]
    assert reverse.encode()==old
    patch=''.join(difflib.unified_diff(a.splitlines(keepends=True),b.splitlines(keepends=True),fromfile='edition-12.zh.md',tofile='edition-13.zh.md'))
    assert patch.encode()==(OUT/'03-zh-revisions.patch').read_bytes()
    ledger=json.loads((OUT/'translation-ledger.json').read_bytes())
    assert ledger['source_sha256']==sha(zh) and ledger['target_sha256']==sha(en)
    rebuilt=TITLE
    for r in ledger['chapters']:
        source=(WORK/r['source_file']).read_bytes(); target=(WORK/r['english_source_file']).read_bytes()
        assert sha(source)==r['sha256'] and source.decode()==b[slice(*r['char_span'])]
        assert sha(target)==r['english_source_sha256']
        chunk=target.decode().rstrip()+'\n\n'; assert en.decode()[slice(*r['english_char_span'])]==chunk
        assert sha(chunk.encode())==r['english_sha256']
        assert [x[0] for x in headings(source.decode())]==[x[0] for x in headings(target.decode())]
        assert urls(source.decode())==urls(target.decode())==r['external_links']
        rebuilt+=chunk
    assert rebuilt.encode()==en and len(ledger['chapters'])==31
    assert len(re.findall('^## ',b,re.M))==len(re.findall('^## ',en.decode(),re.M))==31
    assert headings(b)[-14][1].startswith('附录')
    assert headings(en.decode())[-14][1].startswith('Appendix:')
    assert '### 公平的发展条件、能力互补与防止支配' in b
    assert '### Fair conditions, complementary abilities, and preventing domination' in en.decode()
    assert 'institutional argument does not require normally distributed abilities or needs' in en.decode()
    assert not re.search(r'\b(?:TODO|TBD|TRANSLATE_ME)\b',en.decode())
    assert not re.search('[\u4e00-\u9fff]',en.decode()), 'Unexpected untranslated Chinese in English book.'
    assert len(urls(b))==len(urls(en.decode()))==69
    timeline=json.loads((OUT/'07-thought-evolution.json').read_bytes())
    byref={e['ref']:e for e in hist+events}
    assert len(timeline['stages'])==5
    assert [s['time'] for s in timeline['stages']]==sorted(s['time'] for s in timeline['stages'])
    for s in timeline['stages']:
        e=byref[s['ref']]
        assert all(s[k]==e[k] for k in ['role','time','occurrence','content','text_sha256'])
        assert s['quote']==e['text']
    audit=json.loads((OUT/'full-book-audit.json').read_bytes())
    assert audit['chapters_reviewed']==31 and len(audit['chapters'])==31 and audit['source_sha256']==sha(zh)
    report={'status':'pass','source_events':3,'historical_sources':2,'chinese_replacements':10,
        'outside_replacements':'byte-identical to edition 12; reversible replay verified',
        'chapters_in_each_edition':31,'heading_and_subheading_count':len(headings(b)),
        'external_citation_occurrences':69,'appendix':'revised and still last in both editions',
        'chinese_sha256':sha(zh),'english_sha256':sha(en),
        'editorial_semantic_review':'all source chapters read and adapted; statistical-premise consistency reviewed in context',
        'boundary':'Automated checks establish bytes, attribution, replay and structural coverage, not absolute translation equivalence or validity of the theory.'}
    existing=ARCHIVE/'text-verification.json'
    if (ARCHIVE/'report.json').exists(): assert json.loads(existing.read_bytes())==report
    else: write_json(existing,report)
    return report

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
