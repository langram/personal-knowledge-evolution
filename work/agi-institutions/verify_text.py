"""Verify preserved boundaries, exact originals, edit reversibility and bilingual coverage."""
import json
import re
from prepare import ARCHIVE, OLD, OLD_EN, OUT, WORK, sha, write_json
from build_edition import headings, read, sections, urls

def verify():
    originals={'zh':read(OLD),'en':read(OLD_EN)}
    texts={'zh':read(OUT/'01-new-principles.zh.md'),'en':read(OUT/'02-new-principles.en.md')}
    manifest=json.loads((OUT/'revision-manifest.json').read_bytes())
    metrics=json.loads((OUT/'editorial-statistics.json').read_bytes())
    for lang,old in originals.items():
        new=texts[lang];edits=[e for e in manifest['changes'] if e['language']==lang]
        assert len(edits)==2 and sum(e['kind']=='insert' for e in edits)==1
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
        assert forward==new and backward==old,'Unrecorded change outside approved edit spans'
        assert new.endswith('\n') and '\ufffd' not in new
        assert len(sections(new))==32 and len(headings(new))==228
        assert len(urls(new))==96
        assert new.count('\\[')==new.count('\\]')
    assert [x[0] for x in headings(texts['zh'])]==[x[0] for x in headings(texts['en'])]
    assert urls(texts['zh'])==urls(texts['en'])
    assert sections(texts['zh'])[-1]['title']=='附录　对理论基础与实践可行性的自我反思'
    assert 'Appendix' in sections(texts['en'])[-1]['title']
    # Existing English may contain names/quoted originals; this release adds no untranslated prose.
    for e in manifest['changes']:
        if e['language']=='en':assert not re.search(r'[\u4e00-\u9fff]',e['after']),e['id']
        assert not re.search(r'\b(?:TODO|FIXME|TBD)\b',e['after'])
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events'];byref={e['ref']:e for e in events}
    assert len(events)==2 and sum(e['role']=='user' for e in events)==1
    for e in events:
        assert sha(e['text'].encode())==e['text_sha256']
        assert read(OUT/f"00-{e['ref'].lower()}.txt")==e['text']
        cap=e['capture'];blob=(ARCHIVE/'raw'/(cap['raw']+'.bin')).read_bytes()
        assert len(blob)==cap['bytes'] and sha(blob)==cap['sha256']
        payload=json.loads(blob)['payload']
        assert payload['role']==e['role']
        visible=''.join(p['text'] for p in payload['content'] if p.get('type') in ('input_text','output_text'))
        assert visible==e['text']
        # Recheck frozen byte range against the append-only native source, without reading other messages.
        with open(cap['native_file'],'rb') as stream:
            stream.seek(cap['native_start']);native=stream.read(cap['native_end']-cap['native_start'])
        assert native==blob
    passage=json.loads((OUT/'passage-manifest.json').read_bytes())
    exact=0
    for p in passage['passages']:
        text=texts['zh'][slice(*p['document_span'])];assert sha(text.encode())==p['sha256']
        assert all(ref in byref for ref in p['source_refs'])
        for match in p['exact_author_spans']:
            event=byref[match['ref']];assert event['role']=='user'
            assert event['text'][slice(*match['source_span'])]==match['text']
            assert text[slice(*match['paragraph_span'])]==match['text'];exact+=1
    ledger=json.loads((OUT/'translation-ledger.json').read_bytes());assert len(ledger['chapters'])==32
    for row in ledger['chapters']:
        zh=texts['zh'][slice(*row['char_span'])];en=texts['en'][slice(*row['english_char_span'])]
        assert read(WORK/row['source_file'])==zh and read(WORK/row['english_source_file'])==en
        assert sha(zh.encode())==row['sha256'] and sha(en.encode())==row['english_sha256']
        assert urls(zh)==urls(en)==row['external_links']
        assert len(headings(zh))==len(row['section_map'])==len(headings(en))
    references=json.loads((OUT/'08-external-references.json').read_bytes())
    newurls={url for e in manifest['changes'] for url in urls(e['after'])}
    assert newurls=={r['url'] for r in references},'Every new citation needs a declared evidence scope'
    review=json.loads((OUT/'targeted-review.json').read_bytes())
    assert review['reviewed_chapters']==[16]
    assert metrics['unchanged_chapter_pairs']==31
    assert review['baseline_sha256']==manifest['baseline_sha256']
    result={'status':'pass','edition':manifest['edition'],'reversible_edits':len(manifest['changes']),
        'native_source_roundtrips':len(events),'exact_author_spans_verified':exact,
        'chapters':32,'headings':228,'citation_occurrences':96,'new_external_sources':len(newurls),
        'unchanged_chapter_pairs':metrics['unchanged_chapter_pairs'],
        'chinese_sha256':metrics['chinese_sha256'],'english_sha256':metrics['english_sha256'],
        'boundary':'Checks prove provenance and structural/replay properties; semantic review is editorial, not a mathematical equivalence proof or author approval.'}
    frozen=ARCHIVE/'text-verification.json'
    if (ARCHIVE/'report.json').exists():assert json.loads(frozen.read_bytes())==result
    else:write_json(frozen,result)
    return result

if __name__=='__main__': print(json.dumps(verify(),ensure_ascii=False))
