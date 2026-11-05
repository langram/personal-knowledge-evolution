"""Check exact source recovery, reversible edits and bilingual boundaries."""
import json
import re
from prepare import ARCHIVE, ATTACHMENT, OLD, OLD_EN, OUT, WORK, sha, write_json
from build_edition import headings, read, sections, urls

def verify():
    originals={'zh':read(OLD),'en':read(OLD_EN)}
    texts={'zh':read(OUT/'01-new-principles.zh.md'),'en':read(OUT/'02-new-principles.en.md')}
    manifest=json.loads((OUT/'revision-manifest.json').read_bytes())
    metrics=json.loads((OUT/'editorial-statistics.json').read_bytes())
    for lang,old in originals.items():
        new=texts[lang];edits=[e for e in manifest['changes'] if e['language']==lang]
        assert len(edits)==7 and sum(e['kind']=='insert' for e in edits)==3
        assert sha(old.encode())==manifest['baseline_sha256'][lang]
        assert sha(new.encode())==manifest['result_sha256'][lang]
        forward=old;backward=new
        for e in reversed(edits):
            a,b=e['old_span'];x,y=e['new_span']
            assert old[a:b]==e['before'] and new[x:y]==e['after']
            assert sha(e['before'].encode())==e['before_sha256']
            assert sha(e['after'].encode())==e['after_sha256']
            forward=forward[:a]+e['after']+forward[b:]
            backward=backward[:x]+e['before']+backward[y:]
        assert forward==new and backward==old,'Unrecorded edit outside manifest'
        assert new.endswith('\n') and '\ufffd' not in new
        assert len(sections(new))==33 and len(headings(new))==246
        assert len(urls(new))==102
        assert new.count('$$')%2==0
    assert texts['zh'].startswith('# 新原理：社会科学的数学原理\n')
    assert texts['en'].startswith('# Nova Principia: Mathematical Principles of Social Science\n')
    assert [x[0] for x in headings(texts['zh'])]==[x[0] for x in headings(texts['en'])]
    assert urls(texts['zh'])==urls(texts['en'])
    assert sections(texts['zh'])[-1]['title']=='附录　对理论基础与实践可行性的自我反思'
    assert 'Appendix' in sections(texts['en'])[-1]['title']
    for e in manifest['changes']:
        if e['language']=='en':assert not re.search(r'[\u4e00-\u9fff]',e['after'])
        assert not re.search(r'\b(?:TODO|FIXME|TBD)\b',e['after'])
        assert '\u00ad' not in e['after']
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events'];byref={e['ref']:e for e in events}
    assert len(events)==15 and sum(e['role']=='user' for e in events)==8
    assert sum(e['platform']=='gemini' for e in events)==10
    assert (OUT/'00-gemini-reference-frames.md').read_bytes()==ATTACHMENT.read_bytes()
    for e in events:
        assert sha(e['text'].encode())==e['text_sha256']
        assert read(OUT/f"00-{e['ref'].lower()}.txt")==e['text']
        cap=e['capture'];blob=(ARCHIVE/'raw'/(cap['raw']+'.bin')).read_bytes()
        assert len(blob)==cap['bytes'] and sha(blob)==cap['sha256']
        if cap.get('format')=='markdown-export':
            assert blob[cap['body_start']:cap['body_end']].decode()==e['text']
            assert blob==ATTACHMENT.read_bytes()
            assert e['native_event_time']['zone_known'] is False
            if e['role']=='assistant':assert e['time'] is None
        else:
            payload=json.loads(blob)['payload'];assert payload['role']==e['role']
            visible=''.join(p['text'] for p in payload['content'] if p.get('type') in ('input_text','output_text'))
            assert visible==e['text']
            with open(cap['native_file'],'rb') as stream:
                stream.seek(cap['native_start']);native=stream.read(cap['native_end']-cap['native_start'])
            assert native==blob
    first=byref['AUTHOR-RELATIVITY-ALIGNMENT-FIRST']['text']
    latest=byref['AUTHOR-RELATIVITY-ALIGNMENT']['text']
    assert latest.split('## My request:\n',1)[1].strip()==first.strip()
    exact=0
    for p in json.loads((OUT/'passage-manifest.json').read_bytes())['passages']:
        text=texts['zh'][slice(*p['document_span'])];assert sha(text.encode())==p['sha256']
        assert all(ref in byref for ref in p['source_refs'])
        for match in p['exact_author_spans']:
            event=byref[match['ref']];assert event['role']=='user'
            assert event['text'][slice(*match['source_span'])]==match['text']
            assert text[slice(*match['paragraph_span'])]==match['text'];exact+=1
    ledger=json.loads((OUT/'translation-ledger.json').read_bytes());assert len(ledger['chapters'])==33
    for row in ledger['chapters']:
        zh=texts['zh'][slice(*row['char_span'])];en=texts['en'][slice(*row['english_char_span'])]
        assert read(WORK/row['source_file'])==zh and read(WORK/row['english_source_file'])==en
        assert sha(zh.encode())==row['sha256'] and sha(en.encode())==row['english_sha256']
        assert urls(zh)==urls(en)==row['external_links']
        assert len(headings(zh))==len(row['section_map'])==len(headings(en))
    references=json.loads((OUT/'08-external-references.json').read_bytes())
    newurls={url for e in manifest['changes'] for url in urls(e['after'])}
    assert newurls=={r['url'] for r in references}
    review=json.loads((OUT/'targeted-review.json').read_bytes())
    assert review['reviewed_chapters']==[1,7,25,33]
    assert metrics['unchanged_chapter_pairs']==29
    assert review['baseline_sha256']==manifest['baseline_sha256']
    result={'status':'pass','edition':manifest['edition'],'reversible_edits':len(manifest['changes']),
        'source_roundtrips':len(events),'native_source_roundtrips':5,'markdown_source_roundtrips':10,
        'exact_author_spans_verified':exact,'chapters':33,'headings':246,'citation_occurrences':102,
        'new_external_sources':len(newurls),'unchanged_chapter_pairs':29,
        'chinese_sha256':metrics['chinese_sha256'],'english_sha256':metrics['english_sha256'],
        'boundary':'Checks prove source/replay/structural properties; semantic review is editorial, not proof of the theory or author approval.'}
    frozen=ARCHIVE/'text-verification.json'
    if (ARCHIVE/'report.json').exists():assert json.loads(frozen.read_bytes())==result
    else:write_json(frozen,result)
    return result

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
