"""Verify visible sources, editorial replay, historical anchors and two replacements."""
import difflib
import json
from prepare import ARCHIVE, OLD, OUT, cid, sha, write_json

def verify():
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    expected=['EDITION-ELEVEN-RESPONSE','DEVELOPMENT-GOALS','GOALS-REVIEW','AUTHOR-REVISION','COOPERATION-SYNTHESIS','INTEGRATION-REQUEST']
    assert [e['ref'] for e in events]==expected
    byref={e['ref']:e for e in events}
    for e in events:
        c=e['capture'];data=(ARCHIVE/'raw'/(c['raw']+'.bin')).read_bytes()
        assert sha(data)==c['sha256'] and cid(data,0x55)==c['raw']
        record=json.loads(data);p=record['payload'];assert p['role']==e['role'] and record['timestamp']==e['time']
        if e['role']=='assistant':assert p.get('phase')=='final_answer'
        assert any(x.get('text')==e['text'] for x in p['content'])
        with open(c['native_file'],'rb') as stream:
            stream.seek(c['native_start']);assert stream.read(c['bytes'])==data
        assert sha(e['text'].encode())==e['text_sha256']
        assert (OUT/('00-'+e['ref'].lower()+'.txt')).read_bytes()==e['text'].encode()
    historical=json.loads((OUT/'00-historical-sources.json').read_bytes());byref.update({e['ref']:e for e in historical})
    assert len(historical)==2 and all(e['already_imported'] and e['role']=='user' for e in historical)
    manifest=json.loads((OUT/'revision-manifest.json').read_bytes());old=OLD.read_bytes();whole=(OUT/'02-new-principles.md').read_bytes()
    assert sha(old)==manifest['baseline_sha256'] and sha(whole)==manifest['combined_sha256']
    assert len(manifest['replacements'])==2
    rebuilt=b'';cursor=0
    for row in manifest['replacements']:
        a,b=row['old_byte_span'];x,y=row['new_byte_span'];prior=(OUT/row['before_file']).read_bytes();after=(OUT/row['file']).read_bytes()
        assert old[a:b]==prior and whole[x:y]==after
        assert sha(prior)==row['before_sha256'] and sha(after)==row['after_sha256']
        rebuilt+=old[cursor:a];assert len(rebuilt)==x;rebuilt+=after;assert len(rebuilt)==y;cursor=b
        patch=''.join(difflib.unified_diff(prior.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile=row['before_file'],tofile=row['file']))
        assert patch.encode()==(OUT/row['patch']).read_bytes()
    assert rebuilt+old[cursor:]==whole
    inverse=whole
    for row in reversed(manifest['replacements']):
        x,y=row['new_byte_span'];inverse=inverse[:x]+(OUT/row['before_file']).read_bytes()+inverse[y:]
    assert inverse==old
    marker='## 附录　对理论基础与实践可行性的自我反思'.encode()
    assert old[old.index(marker):]==whole[whole.index(marker):]
    assert whole.rfind(b'\n## ')+1==whole.index(marker)
    units=0;roles={'user':0,'assistant':0}
    for frame in json.loads((OUT/'passage-manifest.json').read_bytes())['sections']:
        text=(OUT/frame['file']).read_text(encoding='utf-8');built=('#'*frame['level']+' '+frame['title']+'\n\n') if frame['level'] else ''
        for p in frame['items']:
            units+=1;assert text[slice(*p['section_span'])]==p['text'] and whole.decode()[slice(*p['document_span'])]==p['text']
            if 'ref' in p:
                e=byref[p['ref']];source=e['text'];i,j=p['source_span'];original=source[i:j]
                assert sha(original.encode())==p['source_sha256'] and p['source_role']==e['role']
                edited=original
                for op in reversed(p['edits']):
                    u,v=op['source_span'];assert original[u-i:v-i]==op['before'];edited=edited[:u-i]+op['after']+edited[v-i:]
                assert edited==p['text'];roles[e['role']]+=1
            if p['kind']=='inherited-text':assert (OUT/p['baseline_file']).read_text(encoding='utf-8')[slice(*p['baseline_section_span'])]==p['text']
            built+=p['text']+'\n\n'
        assert built==text
    timeline=json.loads((OUT/'07-thought-evolution.json').read_bytes())
    assert len(timeline['stages'])==8 and [s['time'] for s in timeline['stages']]==sorted(s['time'] for s in timeline['stages'])
    for s in timeline['stages']:
        e=byref[s['ref']];assert (s['time'],s['role'],s['content'],s['occurrence'])==(e['time'],e['role'],e['content'],e['occurrence'])
        assert e['text'][slice(*s['source_span'])]==s['quote'] and sha(s['quote'].encode())==s['sha256']
    revision=json.loads((OUT/'author-revision.json').read_bytes())
    for key in ['before','after','acceptance']:
        p=revision[key];assert byref[p['ref']]['text'][slice(*p['source_span'])]==p['quote']
        assert sha(p['quote'].encode())==p['sha256']
    assert revision['acceptance']['quote'].startswith('是的，我同意你的修正')
    assert '重要的不是让能力去逼近正态分布' in revision['after']['quote']
    assert '我用正态分布来帮助理解个体需要' not in whole.decode()
    report={'status':'pass','source_events':len(events),'historical_sources':len(historical),'timeline_stages':8,
        'explicit_author_revision':True,'source_adaptations':roles,'passage_units':units,'replacements':2,
        'outside_replacements':'byte-identical','last_appendix':'byte-identical and still last','current_sha256':sha(whole),
        'boundary':'Text, attribution, explicit acceptance and version-link checks; not proof of biological, statistical or institutional hypotheses.'}
    write_json(ARCHIVE/'text-verification.json',report);return report

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
