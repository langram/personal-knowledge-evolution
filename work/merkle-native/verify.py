"""Verify original evidence, visible-message extraction and reversible manuscript edits."""
import collections
import json
from pathlib import Path
from prepare import ARCHIVE, OLD, OUT, sha, write_json
from pkst_codec import Store, cid

def visible(record, platform):
    if platform == 'codex-local':
        message = record['payload']
        assert record['type'] == 'response_item' and message['type'] == 'message'
        assert message['role'] in {'user','assistant'}
        assert message.get('channel') in {None,'final','commentary'}
        assert message.get('phase') in {None,'commentary','final_answer'}
        return [b['text'] for b in message['content'] if b.get('type') in {'input_text','output_text','text'} and isinstance(b.get('text'),str)]
    assert record['type'] in {'user','assistant'} and not record.get('isMeta') and not record.get('isCompactSummary')
    content=record['message']['content']
    return [content] if isinstance(content,str) else [b['text'] for b in content if b.get('type')=='text']

def verify():
    capture=json.loads((ARCHIVE/'capture.json').read_bytes())
    events=json.loads((ARCHIVE/'events.json').read_bytes())
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    insertion=json.loads((OUT/'insertion-manifest.json').read_bytes())
    store=Store(ARCHIVE)
    native_count=remote_count=0
    assert len({e['occurrence'] for e in events})==len(events)==capture['new_events']
    for event in events:
        evidence=event['capture']; origin=evidence['origin']
        data=(ARCHIVE/'raw'/(evidence['raw']+'.bin')).read_bytes()
        assert sha(data)==evidence['sha256'] and len(data)==evidence['bytes'] and cid(data,0x55)==evidence['raw']
        record=json.loads(data)
        if origin['kind']=='local-native-record':
            with Path(origin['file']).open('rb') as stream:
                stream.seek(origin['start']); assert stream.read(origin['end']-origin['start'])==data
            texts=visible(record,event['platform'])
            assert record['timestamp']==event['time']
            assert capture['window_start']<=event['time']<=capture['window_end']
            native_count+=1
        else:
            assert record['type'] in {'userMessage','agentMessage'}
            assert record.get('phase') in {None,'commentary','final_answer'}
            texts=[record['text']] if 'text' in record else [b['text'] for b in record.get('content',[]) if b['type']=='text']
            pages=json.loads(Path(origin['file']).read_bytes())['pages']
            matches=[item for page in pages for turn in page['turns'] if turn['id']==origin['turn'] for item in turn['items'] if item['id']==origin['item']]
            assert matches==[record]
            assert event['time'] is None and event['time_context']
            remote_count+=1
        assert '\n\n'.join(texts)==event['text']
        assert [store.get(key)['text'] for key in event['content']]==texts
        occurrence=store.get(event['occurrence'])
        assert occurrence['event_time']==event['native_event_time']
        for anchor in event['anchors']:
            a=store.get(anchor)
            assert a['occurrence']['$link']==event['occurrence'] and a['raw']['$link']==evidence['raw']
    old=OLD.read_bytes(); chapter=(OUT/'01-chapter.md').read_bytes(); whole=(OUT/'02-new-principles.md').read_bytes()
    at=insertion['insert_at_utf8_byte']
    assert sha(old)==baseline['sha256']==insertion['baseline_sha256']
    assert old[:at]+chapter+old[at:]==whole and whole[:at]+whole[at+len(chapter):]==old
    assert sha(chapter)==insertion['chapter_sha256'] and sha(whole)==insertion['combined_sha256']
    replay='## '+manifest['title']+'\n\n'; spans=collections.defaultdict(list)
    for item in manifest['items']:
        assert chapter.decode()[slice(*item['chapter_span'])]==item['text']
        assert whole.decode()[slice(*item['document_span'])]==item['text']
        if 'ref' in item:
            ref=item['ref']; a,b=item['source_span']; text=selected[ref]['text'][a:b]
            assert sha(text.encode())==item['source_sha256']
            changed=text
            for edit in reversed(item['edits']):
                x,y=edit['source_span']; assert text[x-a:y-a]==edit['before']
                changed=changed[:x-a]+edit['after']+changed[y-a:]
            assert changed==item['text']
            spans[ref].append((a,b))
        replay+=item['text']+'\n\n'
    assert replay.encode()==chapter
    for ranges in spans.values():
        ranges.sort(); assert all(b<=c for (a,b),(c,d) in zip(ranges,ranges[1:]))
    result={'status':'pass','events':len(events),'native_records_verified':native_count,'remote_visible_projections_verified':remote_count,
        'remote_exact_message_times_available':False,'source_spans_replayed':sum(map(len,spans.values())),
        'passages_replayed':len(manifest['items']),'chapter_sha256':sha(chapter),'combined_sha256':sha(whole),
        'original_evidence_bytes_verified':True,'outside_chapter_byte_preserved':True,'insertion_and_inverse_replayed':True,
        'scope':'Source and editorial provenance; no proof of universal performance, full device coverage, or institutional effectiveness.'}
    write_json(ARCHIVE/'text-verification.json',result)
    return result

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
