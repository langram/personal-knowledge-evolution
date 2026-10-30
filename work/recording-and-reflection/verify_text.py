"""Replay original records, every adapted span, and both manuscript insertions."""
import json
from collections import defaultdict
from prepare import ARCHIVE, OLD, OUT, cid, sha, write_json

def verify():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    byref={e['ref']:e for e in events}
    assert len(events)==7 and len(byref)==7
    for e in events:
        c=e['capture']; data=(ARCHIVE/'raw'/(c['raw']+'.bin')).read_bytes()
        assert sha(data)==c['sha256'] and cid(data,0x55)==c['raw']
        native=json.loads(data); p=native['payload']
        assert p['role']==e['role'] and native['timestamp']==e['time']
        if e['role']=='assistant': assert p.get('phase')=='final_answer'
        assert any(x.get('text')==e['text'] for x in p['content'])
        with open(c['native_file'],'rb') as stream:
            stream.seek(c['native_start']); assert stream.read(c['bytes'])==data
        assert sha(e['text'].encode())==e['text_sha256']
        assert (OUT/('00-'+e['ref'].lower()+'.txt')).read_bytes()==e['text'].encode()
    assert json.loads((OUT/'00-sources.json').read_bytes())==[{k:v for k,v in e.items() if k!='capture'} for e in events]
    insertion=json.loads((OUT/'insertion-manifest.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    old=OLD.read_bytes(); whole=(OUT/'02-new-principles.md').read_bytes()
    assert sha(old)==baseline['sha256']==insertion['baseline_sha256']
    assert sha(whole)==insertion['combined_sha256']
    body=insertion['body']; tail=insertion['appendix']
    b=(OUT/body['file']).read_bytes(); t=(OUT/tail['file']).read_bytes(); sep=tail['separator_utf8'].encode()
    at=body['old_byte_offset']; before_tail=old[:at]+b+old[at:]
    assert sha(b)==body['sha256'] and sha(t)==tail['sha256']
    assert before_tail+sep+t==whole
    assert tail['new_byte_offset']==len(before_tail+sep)
    assert whole.endswith(t) and whole[:at]+whole[at+len(b):len(before_tail)]==old
    assert whole.decode().rfind('\n## ')==len((before_tail+sep).decode())-1
    spans=defaultdict(list); units=0
    for section in manifest['sections']:
        text=(OUT/section['file']).read_bytes().decode()
        replay='## '+section['title']+'\n\n'
        for x in section['items']:
            units+=1
            assert text[slice(*x['section_span'])]==x['text']
            assert whole.decode()[slice(*x['document_span'])]==x['text']
            if 'ref' in x:
                e=byref[x['ref']]; a,z=x['source_span']; original=e['text'][a:z]
                assert sha(original.encode())==x['source_sha256']
                result=original
                for op in reversed(x['edits']):
                    i,j=op['source_span']; assert original[i-a:j-a]==op['before']
                    result=result[:i-a]+op['after']+result[j-a:]
                assert result==x['text']
                spans[x['ref']].append((a,z))
            replay+=x['text']+'\n\n'
        assert replay==text
    for ref,ranges in spans.items():
        ranges.sort()
        assert all(b<=c for (a,b),(c,d) in zip(ranges,ranges[1:])),ref
    result={'status':'pass','native_events_verified':len(events),'source_spans_replayed':sum(map(len,spans.values())),
        'passages_replayed':units,'outside_insertions_byte_preserved':True,'insertion_and_inverse_replayed':True,
        'appendix_is_last_section':True,'chapter_sha256':sha((OUT/body['file']).read_bytes()),'appendix_sha256':sha(t),'combined_sha256':sha(whole),
        'scope':'Byte identities, original roles/times, edit replay and placement; not proof of scientific or institutional claims.'}
    write_json(ARCHIVE/'text-verification.json',result)
    return result

if __name__=='__main__': print(json.dumps(verify(),ensure_ascii=False))
