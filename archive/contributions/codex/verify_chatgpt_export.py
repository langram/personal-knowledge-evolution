"""Reparse source shards independently and check every exported message against CAR."""
import hashlib,json,sqlite3,time
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from pkst_codec import cid,decode,encode,check_sets,loads

BASE=Path(__file__).resolve().parents[2];ROOT=BASE/'contributions/codex/chatgpt'

def main():
    start=time.monotonic();report=loads((ROOT/'import-report-v1.json').read_bytes())
    evidence=loads((BASE/report['anchors']).read_bytes());capture=loads((ROOT/'capture-current.json').read_bytes())
    manifest=[loads(x) for x in (ROOT/capture['manifest']).read_bytes().splitlines()];members={r['member_name']:r for r in manifest}
    index=sqlite3.connect((BASE/report['index']).as_uri()+'?mode=ro',uri=True);car=(BASE/report['car']).open('rb');cache={}
    def get(key):
        if key not in cache:
            row=index.execute('SELECT offset,size FROM blocks WHERE cid=?',(key,)).fetchone();assert row,key
            car.seek(row[0]);b=car.read(row[1]);assert cid(b)==key
            o=decode(b);check_sets(o);assert encode(o)==b;cache[key]=o
        return cache[key]
    def pointer(d,p):
        for part in p.split('/')[1:]:
            part=part.replace('~1','/').replace('~0','~');d=d[int(part)] if isinstance(d,list) else d[part]
        return d
    def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    def matching_file(ref):
        if not isinstance(ref,str):return []
        import re
        if ref.startswith('file-service://'):ref=ref[15:]
        elif ref.startswith('sedim://'):ref=ref[8:]
        if re.fullmatch(r'file[-_][A-Za-z0-9]+',ref):ref+='.dat'
        return [members[ref]['raw_cid']] if ref in members else []
    all_anchors={(r['raw'],r['pointer']):r for r in evidence['anchors']};assert len(all_anchors)==len(evidence['anchors'])
    block_refs={}
    for (key,) in index.execute("SELECT cid FROM blocks WHERE schema='pkst/block-reference@0.1'"):
        obj=get(key);token=(obj['occurrence']['$link'],obj['ordinal']);assert token not in block_refs;block_refs[token]=obj
    conversations={(r['raw'],r['pointer']):r for r in evidence['conversations']};checked=set();counts=Counter();expected_parts=0;expected_attach=set();all_times=[]
    for name in report['shards']:
        raw=members[name]['raw_cid'];b=(ROOT/'raw'/(raw+'.bin')).read_bytes();assert cid(b,0x55)==raw
        native=json.loads(b);precise=json.loads(b,parse_float=Decimal)
        for ci,c in enumerate(native):
            cp='/'+str(ci);rec=conversations[(raw,cp)];co=get(rec['object']);source=get(co['source']['$link'])
            assert source=={'schema':'pkst/source@0.1','platform':'chatgpt','namespace':'owner-openai-account','native_thread_id':c['id']}
            assert co['raw']['$link']==raw and co['pointer']==cp
            assert json.loads(get(co['metadata']['$link'])['text'])=={k:v for k,v in c.items() if k!='mapping'}
            topo=json.loads(get(co['topology']['$link'])['text']);assert set(topo)==set(c['mapping'])
            child_counts=Counter(n['parent'] for n in c['mapping'].values() if n['parent'] is not None);counts['fork_nodes']+=sum(v>1 for v in child_counts.values())
            for nk,n in c['mapping'].items():
                m=n['message'];assert topo[nk]=={'id':n.get('id'),'parent':n['parent'],'message_id':m.get('id') if m else None}
                if m is None:counts['empty_nodes']+=1;continue
                mp=cp+'/mapping/'+nk.replace('~','~0').replace('/','~1')+'/message';r=all_anchors[(raw,mp)];checked.add((raw,mp))
                o=get(r['occurrence']);er=get(r['extraction_record']);role=m['author']['role'];typ=m['content']['content_type']
                assert er['raw']['$link']==raw and er['pointer']==mp and er['coordinate']=='json-pointer' and er['occurrence']['$link']==r['occurrence']
                assert o['source']==co['source'] and o['native_id']==m['id'] and o['locator'] is None and o['native_role']==role
                assert o['actor_kind']==({'assistant':'ai','system':'system','tool':'tool'}.get(role,'unknown')) and o['process_kind']=='unknown'
                assert o['native_parent_ids']==([] if n['parent'] is None else [n['parent']])
                assert o['chatgpt:node_id']==nk and o['chatgpt:content_type']==typ and o['chatgpt:metadata_parent_id']==(m.get('metadata') or {}).get('parent_id')
                assert json.loads(get(er['chatgpt:message_metadata']['$link'])['text'])=={k:v for k,v in m.items() if k!='content'}
                value=precise[ci]['mapping'][nk]['message']['create_time'];et=o['event_time']
                if value is None:assert et=={'value':None,'format':'unknown','precision':'unknown','zone_known':False,'unit':None}
                else:
                    assert et['value']==format(Decimal(value),'f') and Decimal(et['value'])==Decimal(value) and et['format']=='epoch-decimal' and et['unit']=='s' and et['zone_known'] is True
                    digits=max(0,-Decimal(value).as_tuple().exponent);assert et['precision']==('second' if not digits else 'millisecond' if digits<=3 else 'microsecond' if digits<=6 else 'unknown');all_times.append(et['value'])
                opaque=typ in {'thoughts','reasoning_recap','reasoning','thinking','analysis','encrypted','encrypted_content'} or m.get('channel')=='analysis'
                if opaque:
                    assert len(o['content'])==1
                    block=get(o['content'][0]['$link']);assert block=={'schema':'pkst/opaque-block@0.1','native_type':typ,'profile':'python-json-v1','digest':hashlib.sha256(canonical(m['content']).encode()).hexdigest(),'handling':'raw-only'}
                    native_parts=[m['content']];ptrs=['/content'];counts['opaque_messages']+=1
                else:
                    assert typ in ('text','multimodal_text');native_parts=m['content']['parts'];ptrs=['/content/parts/'+str(i) for i in range(len(native_parts))]
                    assert len(o['content'])==len(native_parts);counts['nonopaque_messages']+=1
                    for val,part in zip(native_parts,o['content']):
                        block=get(part['$link'])
                        if isinstance(val,str):assert block=={'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':val}
                        else:assert block['schema']=='pkst/projection@0.1' and block['profile']=='python-json-v1' and block['text']==canonical(val)
                for i,ptr in enumerate(ptrs):
                    br=block_refs[(r['occurrence'],i)];assert br['raw']['$link']==raw and br['document_pointer']==mp and br['pointer']==ptr
                    assert pointer(native,mp+ptr)==native_parts[i]
                expected_parts+=len(ptrs)
                for ai,_ in enumerate((m.get('metadata') or {}).get('attachments',[])):expected_attach.add((raw,mp+'/metadata/attachments/'+str(ai)+'/id'))
                for pi,part in enumerate(m['content'].get('parts',[])):
                    if isinstance(part,dict) and 'asset_pointer' in part:expected_attach.add((raw,mp+'/content/parts/'+str(pi)+'/asset_pointer'))
                counts['messages']+=1;counts['role:'+role]+=1
                alt=(m.get('metadata') or {}).get('parent_id')
                if alt is not None and alt!=n['parent']:counts['parent_field_disagreements']+=1
        for ar in (x for x in evidence['attachments'] if x['raw']==raw):
            obj=get(ar['object']);ref=pointer(native,ar['pointer']);matches=matching_file(ref)
            assert obj['reference']==ref and obj['raw']['$link']==raw and obj['pointer']==ar['pointer']
            assert [x['$link'] for x in obj['candidates']]==matches==ar['candidates']
            assert obj['resolution']==('exact-export-name' if matches else 'unresolved-in-this-export')
            counts['attachment:'+obj['resolution']]+=1
    assert checked==set(all_anchors) and len(conversations)==sum(1 for _ in index.execute("SELECT 1 FROM blocks WHERE schema='pkst/chatgpt-conversation@0.1'"))
    assert len(block_refs)==expected_parts
    assert {(x['raw'],x['pointer']) for x in evidence['attachments']}==expected_attach
    assert counts['messages']==len(all_anchors)==index.execute("SELECT count(*) FROM blocks WHERE schema='pkst/occurrence@0.1'").fetchone()[0]
    for k,v in counts.items():assert report['counts'][k]==v,(k,v,report['counts'].get(k))
    assert min(all_times,key=Decimal)==report['event_time_min'] and max(all_times,key=Decimal)==report['event_time_max']
    library=json.loads((ROOT/'raw'/(members['library_files.json']['raw_cid']+'.bin')).read_bytes())
    assert len(library)==len(evidence['library'])
    for row,entry in zip(library,evidence['library']):assert row['file_id']==entry['file_id'] and matching_file(row['file_id'])==entry['candidates']
    # Behavioral fixtures exercise stable identity, branches, exact time, opaque exclusion.
    from import_chatgpt_export import convert
    raw=cid(b'fixture',0x55);store={}
    def put(obj):
        key=cid(encode(obj));store[key]=obj;return key
    def message(i,typ='text'):
        return {'id':i,'author':{'role':'user' if i!='c' else 'assistant'},'create_time':None,'content':{'content_type':typ,'parts':['same\r\n原话🙂']} if typ=='text' else {'content_type':typ,'thoughts':[{'content':'PRIVATE-FIXTURE-THOUGHT'}]}}
    fixture=[{'id':'test','conversation_id':'test','current_node':'c','mapping':{'root':{'id':'root','message':None,'parent':None},'a':{'id':'a','message':message('a'),'parent':'root'},'b':{'id':'b','message':message('b'),'parent':'a'},'c':{'id':'c','message':message('c','thoughts'),'parent':'a'}}}]
    exact=json.loads(json.dumps(fixture));exact[0]['mapping']['a']['message']['create_time']=Decimal('1700000000.123456789')
    first=convert(fixture,exact,raw,put,{});second=convert(fixture,exact,raw,put,{})
    assert first==second and first['counts']['fork_nodes']==1 and len(first['anchors'])==3
    a,b,c=[store[x['occurrence']] for x in first['anchors']]
    assert first['anchors'][0]['occurrence']!=first['anchors'][1]['occurrence'] and a['content']==b['content']
    assert a['event_time']['value']=='1700000000.123456789' and b['event_time']['value'] is None
    assert store[c['content'][0]['$link']]['schema']=='pkst/opaque-block@0.1'
    assert all('PRIVATE-FIXTURE-THOUGHT' not in x.get('text','') for x in store.values() if x['schema']=='pkst/content@0.1')
    try:loads('{"id":1,"id":2}')
    except ValueError:pass
    else:raise AssertionError('Duplicate keys accepted')
    original=encode(a);damaged=original[:-1]+bytes([original[-1]^1]);assert cid(damaged)!=cid(original)
    # A syntactically valid, altered native text must not pass exact source comparison.
    assert store[a['content'][0]['$link']]['text']!='same\n原话🙂'
    result={'schema':'pkst.chatgpt-source-verification@0.1','recorded_at':datetime.now(timezone.utc).isoformat(),'status':'pass',
        'snapshot':report['root'],'conversations':len(conversations),'messages':len(checked),'block_references':expected_parts,'attachments':len(expected_attach),
        'counts':dict(counts),'library_entries_verified':len(library),'verified_structural_objects_read':len(cache),
        'fixtures':['repeat conversion stable','same text different event IDs','fork retained','unknown and exact decimal time','reasoning absent from content','duplicate JSON keys rejected','mutated object hash rejected','CRLF remains distinct from LF'],
        'source_fields':'all messages: source, native ID, role, content, time, parent fields, native pointers, metadata; all conversation topology and attachment pointers',
        'scope':'separate source-comparison code path, shared codec; Codex self-verification, not Claude review; prior corpus not rehashed',
        'elapsed_seconds':round(time.monotonic()-start,3)}
    (ROOT/'verification-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
