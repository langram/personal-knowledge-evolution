"""Verify source bytes and exact, reversible editorial replacement before activation."""
import difflib
import json
from prepare import ARCHIVE, OLD, OUT, cid, sha, write_json

def verify():
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    assert [e['ref'] for e in events]==['EDITION-TEN-RESPONSE','ABILITY-RESOURCE-REPLY']
    byref={e['ref']:e for e in events}
    for e in events:
        c=e['capture'];data=(ARCHIVE/'raw'/(c['raw']+'.bin')).read_bytes()
        assert sha(data)==c['sha256'] and cid(data,0x55)==c['raw']
        record=json.loads(data);p=record['payload']
        assert p['role']==e['role'] and record['timestamp']==e['time']
        if e['role']=='assistant':assert p.get('phase')=='final_answer'
        assert any(x.get('text')==e['text'] for x in p['content'])
        with open(c['native_file'],'rb') as stream:
            stream.seek(c['native_start']);assert stream.read(c['bytes'])==data
        assert sha(e['text'].encode())==e['text_sha256']
        assert (OUT/('00-'+e['ref'].lower()+'.txt')).read_bytes()==e['text'].encode()
    manifest=json.loads((OUT/'revision-manifest.json').read_bytes());row=manifest['replacements'][0]
    assert len(manifest['replacements'])==1
    old=OLD.read_bytes();whole=(OUT/'02-new-principles.md').read_bytes()
    prior=(OUT/row['before_file']).read_bytes();section=(OUT/row['file']).read_bytes()
    a,b=row['old_byte_span'];x,y=row['new_byte_span']
    assert a==x and old[a:b]==prior and whole[x:y]==section
    assert sha(old)==manifest['baseline_sha256'] and sha(whole)==manifest['combined_sha256']
    assert sha(prior)==row['before_sha256'] and sha(section)==row['after_sha256']
    assert old[:a]+section+old[b:]==whole
    assert whole[:x]+prior+whole[y:]==old
    marker='## 附录　对理论基础与实践可行性的自我反思'.encode()
    assert old[old.index(marker):]==whole[whole.index(marker):]
    assert whole.rfind(b'\n## ')+1==whole.index(marker)
    counts=[]
    for fname,mname,statsname in [('01-section.md','passage-manifest.json','editorial-statistics.json'),
                                  ('draft-01-section.md','draft-01-passages.json','draft-01-statistics.json')]:
        text=(OUT/fname).read_text(encoding='utf-8')
        frame=json.loads((OUT/mname).read_bytes())['sections'][0]
        rebuilt='#'*frame['level']+' '+frame['title']+'\n\n';source_ranges=[];adaptations=0
        full=(old[:a]+text.encode()+old[b:]).decode()
        assert sha(full.encode())==json.loads((OUT/statsname).read_bytes())['combined_sha256']
        for p in frame['items']:
            assert text[slice(*p['section_span'])]==p['text']
            assert full[slice(*p['document_span'])]==p['text']
            if 'ref' in p:
                source=byref[p['ref']]['text'];i,j=p['source_span'];original=source[i:j]
                assert sha(original.encode())==p['source_sha256']
                edited=original
                for op in reversed(p['edits']):
                    u,v=op['source_span'];assert original[u-i:v-i]==op['before']
                    edited=edited[:u-i]+op['after']+edited[v-i:]
                assert edited==p['text'];source_ranges.append((i,j));adaptations+=1
            if p['kind']=='inherited-text':assert prior.decode()[slice(*p['baseline_section_span'])]==p['text']
            rebuilt+=p['text']+'\n\n'
        assert rebuilt==text and adaptations==3
        assert all(left[1]==right[0] for left,right in zip(source_ranges,source_ranges[1:]))
        counts.append({'file':fname,'passage_units':len(frame['items']),'source_adaptations':adaptations})
    for before,after,target in [('05-previous-section.md','01-section.md','06-section-revision.patch'),
                                ('draft-01-section.md','01-section.md','07-draft-refinement.patch')]:
        patch=''.join(difflib.unified_diff((OUT/before).read_text(encoding='utf-8').splitlines(keepends=True),
                    (OUT/after).read_text(encoding='utf-8').splitlines(keepends=True),fromfile=before,tofile=after))
        assert patch.encode()==(OUT/target).read_bytes()
    report={'status':'pass','source_events':len(events),'drafts':counts,'replacements':1,
            'outside_replacement':'byte-identical','last_appendix':'byte-identical and still last',
            'current_sha256':sha(whole),'boundary':'Text/provenance checks; not evidence of normality, causal effect or institutional effectiveness.'}
    write_json(ARCHIVE/'text-verification.json',report)
    return report

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
