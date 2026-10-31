"""Verify source identity, reversible adaptations, four insertions and final appendix."""
import difflib
import json
from collections import defaultdict
from prepare import ARCHIVE, OLD, OUT, cid, sha, write_json

def verify():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    assert [e['ref'] for e in events]==['RESEARCH-REQUEST','RESEARCH-RESULT','CIVILIZATION-REPLY']
    byref={e['ref']:e for e in events}
    for e in events:
        c=e['capture']; data=(ARCHIVE/'raw'/(c['raw']+'.bin')).read_bytes()
        assert sha(data)==c['sha256'] and cid(data,0x55)==c['raw']
        native=json.loads(data);p=native['payload']
        assert p['role']==e['role'] and native['timestamp']==e['time']
        assert any(b.get('text')==e['text'] for b in p['content'])
        if e['role']=='assistant':assert p.get('phase')=='final_answer'
        with open(c['native_file'],'rb') as stream:
            stream.seek(c['native_start']);assert stream.read(c['bytes'])==data
        assert sha(e['text'].encode())==e['text_sha256']
        assert (OUT/('00-'+e['ref'].lower()+'.txt')).read_bytes()==e['text'].encode()
    assert json.loads((OUT/'00-sources.json').read_bytes())==[{k:v for k,v in e.items() if k!='capture'} for e in events]
    insertion=json.loads((OUT/'insertion-manifest.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    old=OLD.read_bytes();whole=(OUT/'02-new-principles.md').read_bytes()
    assert sha(old)==baseline['sha256']==insertion['baseline_sha256']
    assert sha(whole)==insertion['combined_sha256']
    assert len(insertion['insertions'])==len(manifest['sections'])==4
    forward=b'';cursor=0
    for row in insertion['insertions']:
        at=row['old_byte_offset'];block=(OUT/row['file']).read_bytes()
        assert sha(block)==row['sha256'] and len(block)==row['bytes']
        assert old[at:].startswith(row['marker'].encode())
        forward+=old[cursor:at];assert len(forward)==row['new_byte_offset']
        forward+=block;cursor=at
    assert forward+old[cursor:]==whole
    inverse=whole
    for row in reversed(insertion['insertions']):
        a=row['new_byte_offset'];b=a+row['bytes']
        assert inverse[a:b]==(OUT/row['file']).read_bytes()
        inverse=inverse[:a]+inverse[b:]
    assert inverse==old
    marker='## 附录　对理论基础与实践可行性的自我反思'.encode()
    assert old[old.index(marker):]==whole[whole.index(marker):]
    assert whole.rfind(b'\n## ')+1==whole.index(marker)
    spans=defaultdict(list);units=0
    for section in manifest['sections']:
        text=(OUT/section['file']).read_text(encoding='utf-8')
        replay='#'*section['level']+' '+section['title']+'\n\n'
        for item in section['items']:
            units+=1
            assert text[slice(*item['section_span'])]==item['text']
            assert whole.decode()[slice(*item['document_span'])]==item['text']
            if 'ref' in item:
                source=byref[item['ref']]['text'];a,b=item['source_span'];original=source[a:b]
                assert sha(original.encode())==item['source_sha256']
                edited=original
                for op in reversed(item['edits']):
                    x,y=op['source_span'];assert original[x-a:y-a]==op['before']
                    edited=edited[:x-a]+op['after']+edited[y-a:]
                assert edited==item['text']
                spans[item['ref']].append((a,b))
            replay+=item['text']+'\n\n'
        assert replay==text
    for ref,ranges in spans.items():
        ranges.sort();assert all(b<=c for (a,b),(c,d) in zip(ranges,ranges[1:]))
    bundled='# 本次增补正文\n\n'+''.join((OUT/s['file']).read_text(encoding='utf-8') for s in manifest['sections'])
    assert bundled.encode()==(OUT/'08-edition-additions.md').read_bytes()
    draft=(OUT/'draft-01-additions.md').read_text(encoding='utf-8')
    draft_manifest=json.loads((OUT/'draft-01-passages.json').read_bytes())
    draft_replayed='# 本次增补正文\n\n'
    draft_spans=0
    for section in draft_manifest['sections']:
        draft_replayed+='#'*section['level']+' '+section['title']+'\n\n'
        for item in section['items']:
            if 'ref' in item:
                a,b=item['source_span'];original=byref[item['ref']]['text'][a:b]
                assert sha(original.encode())==item['source_sha256']
                edited=original
                for op in reversed(item['edits']):
                    x,y=op['source_span'];assert original[x-a:y-a]==op['before']
                    edited=edited[:x-a]+op['after']+edited[y-a:]
                assert edited==item['text'];draft_spans+=1
            draft_replayed+=item['text']+'\n\n'
    assert draft_replayed==draft
    expected=''.join(difflib.unified_diff(draft.splitlines(keepends=True),bundled.splitlines(keepends=True),
        fromfile='draft-01-additions.md',tofile='08-edition-additions.md'))
    assert expected.encode()==(OUT/'draft-01-to-final.patch').read_bytes()
    report={'status':'pass','native_events_verified':len(events),'source_spans_replayed':sum(map(len,spans.values())),
        'passages_replayed':units,'insertion_count':4,'outside_insertions_byte_preserved':True,
        'insertion_and_inverse_replayed':True,'prior_appendix_unchanged_and_last':True,
        'draft_revision_verified':True,'draft_source_spans_replayed':draft_spans,'combined_sha256':sha(whole),
        'scope':'Source identities, roles, times, edit replay and placement; not proof of scientific or institutional claims.'}
    write_json(ARCHIVE/'text-verification.json',report)
    return report

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
