"""Official captured ChatGPT shards -> PKST evidence CAR. Never execute source text."""
import hashlib,json,re,sys,time
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from pkst_codec import cid,link,linkset,loads,pairs
from pkst_car import CarWriter,inspect_car

BASE=Path(__file__).resolve().parents[2]
ROOT=BASE/'contributions/codex/chatgpt'
PARSER='chatgpt-export-json-pointer@0.1'
OPAQUE={'thoughts','reasoning_recap','reasoning','thinking','analysis','encrypted','encrypted_content'}

def jtext(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def projection(o,kind):return {'schema':'pkst/projection@0.1','native_type':kind,'profile':'python-json-v1','text':jtext(o)}
def esc(s):return s.replace('~','~0').replace('/','~1')
def timestamp(value):
    if value is None:return dict(value=None,format='unknown',precision='unknown',zone_known=False,unit=None)
    if not isinstance(value,(Decimal,int)) or isinstance(value,bool):raise ValueError('Unsupported native time')
    v=Decimal(value)
    if not v.is_finite():raise ValueError('Nonfinite time')
    digits=max(0,-v.as_tuple().exponent)
    return dict(value=format(v,'f'),format='epoch-decimal',precision='second' if not digits else 'millisecond' if digits<=3 else 'microsecond' if digits<=6 else 'unknown',zone_known=True,unit='s')

def raw_put(data):
    key=cid(data,0x55);path=ROOT/'raw'/(key+'.bin')
    if path.exists():
        if path.read_bytes()!=data:raise ValueError('Raw mismatch')
    else:path.write_bytes(data)
    return key

def parts_of(m):
    c=m['content'];typ=c.get('content_type','unknown')
    if typ in OPAQUE or m.get('channel')=='analysis':
        return [(dict(schema='pkst/opaque-block@0.1',native_type=typ,profile='python-json-v1',digest=hashlib.sha256(jtext(c).encode()).hexdigest(),handling='raw-only'),'/content',typ)]
    if typ in ('text','multimodal_text'):
        if not isinstance(c.get('parts'),list):raise ValueError('Expected content parts list')
        return [(dict(schema='pkst/content@0.1',media_type='text/plain;charset=utf-8',text=p) if isinstance(p,str) else projection(p,'chatgpt-content-part'),'/content/parts/'+str(i),typ if isinstance(p,str) else p.get('content_type','structured') if isinstance(p,dict) else 'structured') for i,p in enumerate(c['parts'])]
    return [(projection(c,'chatgpt-'+typ),'/content',typ)]

def resolve_ref(value,members):
    if not isinstance(value,str):return []
    name=value
    if value.startswith(('file-service://','sedim://')):name=value.split('://',1)[1]
    if re.fullmatch(r'file[-_][A-Za-z0-9]+',name):name+='.dat'
    if name in members:return [members[name]['raw_cid']]
    return []

def convert(convs,precise,raw,put,members):
    roots=[];anchors=[];conversations=[];attachments=[];counts=Counter();gaps=[];times=[]
    if not isinstance(convs,list) or len(convs)!=len(precise):raise ValueError('Invalid conversations shard')
    for ci,(c,pc) in enumerate(zip(convs,precise)):
        tid=c['id']
        if not isinstance(tid,str) or not tid or c.get('conversation_id',tid)!=tid:raise ValueError('Conflicting conversation IDs')
        source=put(dict(schema='pkst/source@0.1',platform='chatgpt',namespace='owner-openai-account',native_thread_id=tid))
        cp='/'+str(ci);mapping=c['mapping'];topology={}
        children=Counter(n.get('parent') for n in mapping.values() if n.get('parent') is not None)
        counts['fork_nodes']+=sum(n>1 for n in children.values())
        for nk,n in mapping.items():
            topology[nk]={'id':n.get('id'),'parent':n.get('parent'),'message_id':n['message'].get('id') if n.get('message') else None}
            if n.get('parent') is not None and n['parent'] not in mapping:gaps.append({'thread':tid,'node':nk,'kind':'missing-mapping-parent','parent':n['parent']})
        # Parent cycles are a source anomaly and cannot be silently linearized.
        done=set()
        for start in mapping:
            trail=set();k=start
            while k in mapping and k not in done:
                if k in trail:raise ValueError('Native mapping parent cycle '+tid)
                trail.add(k);k=mapping[k].get('parent')
            done.update(trail)
        cc=put({'schema':'pkst/chatgpt-conversation@0.1','source':link(source),'raw':link(raw),'pointer':cp,
          'metadata':link(put(projection({k:v for k,v in c.items() if k!='mapping'},'chatgpt-conversation-metadata'))),
          'topology':link(put(projection(topology,'chatgpt-native-mapping-topology')))})
        roots.append(cc);conversations.append({'thread':tid,'object':cc,'source':source,'pointer':cp,'raw':raw,'title':c.get('title'),'nodes':len(mapping)})
        counts['conversations']+=1;counts['mapping_nodes']+=len(mapping)
        if c.get('current_node') not in mapping:gaps.append({'thread':tid,'kind':'current-node-not-in-mapping','value':c.get('current_node')})
        for nk,n in mapping.items():
            m=n.get('message')
            if m is None:counts['empty_nodes']+=1;continue
            mp=cp+'/mapping/'+esc(nk)+'/message';role=m['author'].get('role');typ=m['content'].get('content_type','unknown')
            native=m.get('id');pm=pc['mapping'][nk]['message'];blocks=parts_of(m)
            content=[link(put(x[0])) for x in blocks]
            locator=None if native else dict(raw=link(raw),coordinate='json-pointer',pointer=mp)
            metadata=m.get('metadata') or {};alternate=metadata.get('parent_id')
            if alternate is not None and alternate!=n.get('parent'):counts['parent_field_disagreements']+=1
            if nk!=native:counts['node_message_id_disagreements']+=1
            et=timestamp(pm.get('create_time'))
            if et['value'] is not None:times.append(et['value'])
            o=dict(schema='pkst/occurrence@0.1',source=link(source),native_id=native,locator=locator,native_role=role,
                actor_kind={'assistant':'ai','system':'system','tool':'tool'}.get(role,'unknown'),process_kind='unknown',content=content,
                native_parent_ids=None if 'parent' not in n else [] if n['parent'] is None else [n['parent']],event_time=et,
                **{'chatgpt:node_id':nk,'chatgpt:content_type':typ,'chatgpt:metadata_parent_id':alternate})
            occurrence=put(o)
            er=put(dict(schema='pkst/extraction-record@0.1',raw=link(raw),occurrence=link(occurrence),coordinate='json-pointer',pointer=mp,parser=PARSER,
                role_basis='native author.role; user authorship unknown; mapping.parent preserved separately from metadata.parent_id',
                **{'chatgpt:message_metadata':link(put(projection({k:v for k,v in m.items() if k!='content'},'chatgpt-message-metadata')))}))
            roots.append(er)
            for i,(_,ptr,btyp) in enumerate(blocks):
                roots.append(put(dict(schema='pkst/block-reference@0.1',raw=link(raw),occurrence=link(occurrence),ordinal=i,coordinate='json-pointer',document_pointer=mp,pointer=ptr,native_type=btyp)))
            refs=[('/metadata/attachments/'+str(i)+'/id',x.get('id')) for i,x in enumerate(metadata.get('attachments',[]))]
            refs.extend(('/content/parts/'+str(i)+'/asset_pointer',p['asset_pointer']) for i,p in enumerate(m['content'].get('parts',[])) if isinstance(p,dict) and 'asset_pointer' in p)
            for suffix,ref in refs:
                candidates=resolve_ref(ref,members);status='exact-export-name' if len(candidates)==1 else 'unresolved-in-this-export'
                ar=put(dict(schema='pkst/chatgpt-attachment@0.1',occurrence=link(occurrence),raw=link(raw),pointer=mp+suffix,reference=ref,resolution=status,candidates=linkset(candidates)))
                roots.append(ar);attachments.append({'object':ar,'raw':raw,'pointer':mp+suffix,'reference':ref,'status':status,'candidates':candidates});counts['attachment:'+status]+=1
            anchors.append({'occurrence':occurrence,'extraction_record':er,'raw':raw,'pointer':mp,'thread':tid,'node':nk,'role':role,'type':typ})
            counts['messages']+=1;counts['role:'+str(role)]+=1;counts['type:'+typ]+=1
            counts['opaque_messages' if any(x[0]['schema']=='pkst/opaque-block@0.1' for x in blocks) else 'nonopaque_messages']+=1
    return dict(roots=roots,anchors=anchors,conversations=conversations,attachments=attachments,counts=dict(counts),gaps=gaps,times=times)

def main():
    start=time.monotonic();now=datetime.now(timezone.utc).isoformat();capture=loads((ROOT/'capture-current.json').read_bytes())
    assert capture['status']=='captured'
    manifestbytes=(ROOT/capture['manifest']).read_bytes();assert hashlib.sha256(manifestbytes).hexdigest()==capture['manifest_sha256']
    rows=[loads(x) for x in manifestbytes.splitlines()];members={r['member_name']:r for r in rows}
    if len(members)!=len(rows):raise ValueError('Duplicate export member names')
    def read(name):
        key=members[name]['raw_cid'];b=(ROOT/'raw'/(key+'.bin')).read_bytes();assert cid(b,0x55)==key;return b
    official=loads(read('export_manifest.json'));listed={x['path']:x['size_bytes'] for x in official['export_files']}
    if len(listed)!=len(official['export_files']):raise ValueError('Duplicate official manifest path')
    expected=set(members)-{official['manifest_file']}
    assert set(listed)==expected
    assert all(members[n]['bytes']==size for n,size in listed.items())
    shards=official['logical_files']['conversations.json']['files'];assert shards and len(set(shards))==len(shards)
    assert set(shards)=={n for n in members if re.fullmatch(r'conversations(?:-\d+)?\.json',n)}
    private=ROOT/'.private';output=private/'chatgpt-evidence-v1.car';writer=CarWriter(output)
    aggregate={'roots':[],'anchors':[],'conversations':[],'attachments':[],'gaps':[],'times':[]};counts=Counter();failures=[]
    for name in shards:
        b=read(name)
        try:
            native=loads(b);precise=json.loads(b,parse_float=Decimal,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            result=convert(native,precise,members[name]['raw_cid'],writer.put,members)
        except (ValueError,KeyError,TypeError,UnicodeError) as e:
            failures.append({'member':name,'type':type(e).__name__,'error':str(e)})
            (ROOT/'parse-failures.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2),encoding='utf-8');continue
        for key in aggregate:aggregate[key].extend(result[key])
        counts.update(result['counts']);print(json.dumps({'parsed':name,'conversations':result['counts']['conversations'],'messages':result['counts']['messages']}),flush=True)
    if failures:raise ValueError('Incomplete shard import; raw retained, catalog unchanged')
    tids=[x['thread'] for x in aggregate['conversations']]
    if len(tids)!=len(set(tids)):raise ValueError('Duplicate conversation identity needs explicit version handling')
    library=loads(read('library_files.json'));librows=[]
    for i,row in enumerate(library):
        candidates=resolve_ref(row.get('file_id'),members)
        libro={'index':i,'file_id':row.get('file_id'),'candidates':candidates,'status':'exact-export-name' if candidates else 'unresolved-in-this-export'};librows.append(libro)
    asset_names=loads(read('conversation_asset_file_names.json'))
    asset_missing=[n for n in asset_names if n not in members]
    evidence={k:v for k,v in aggregate.items() if k not in ('roots','times')};evidence['library']=librows;evidence['asset_name_map_unresolved']=asset_missing
    anchorbytes=json.dumps(evidence,ensure_ascii=False,indent=2).encode();(private/'anchors-v1.json').write_bytes(anchorbytes)
    rawroots=set(x['raw_cid'] for x in rows)|{capture['original']['raw_cid']}
    protocol=raw_put((BASE/'protocol/PKST-0.1.md').read_bytes());profile=raw_put((BASE/'protocol/CHATGPT-EXPORT-0.1.md').read_bytes())
    implementation=raw_put(Path(__file__).read_bytes());capture_impl=raw_put((BASE/'contributions/codex/capture_gemini_takeout.py').read_bytes());manifest=raw_put(manifestbytes);evidencekey=raw_put(anchorbytes);captureraw=raw_put((ROOT/'capture-current.json').read_bytes())
    rawroots.update([protocol,profile,implementation,capture_impl,manifest,evidencekey,captureraw])
    activity=writer.put(dict(schema='pkst/activity@0.1',operation='import',recorded_at=now,actor={'kind':'ai','id':'codex'},
        inputs=linkset([manifest,profile,captureraw]),outputs=linkset(aggregate['roots']),implementation=link(implementation),
        coverage={'counts':dict(counts),'evidence':link(evidencekey),'capture_implementation':link(capture_impl),'python':sys.version.split()[0],
        'library_entries':len(library),'library_exact_matches':sum(bool(x['candidates']) for x in librows),'asset_name_map_unresolved':len(asset_missing),
        'semantic_extraction':'not-performed','privacy':'local-only','native_parent_policy':'mapping parent and metadata parent separate'}))
    snapshot=writer.put(dict(schema='pkst/snapshot@0.1',parents=[],roots=linkset([activity]+list(rawroots)),protocol=link(protocol),
        coverage={'platform':'chatgpt','recorded_cutoff':now,'scope':'one official export ZIP, all manifest shards and all members',
        'event_time_min':min(aggregate['times'],key=Decimal),'event_time_max':max(aggregate['times'],key=Decimal),
        'gaps':aggregate['gaps'],'external_raw':True,'review':'Codex verification pending; no Claude review',
        'limitations':['Export completeness beyond this ZIP unknown','Reasoning and recap blocks raw-only','Parent fields disagree; no inferred causal chain','Unresolved file IDs do not prove permanent loss','No belief or authorship inference']}))
    envelope=writer.finish([snapshot],rawroots);verified=inspect_car(output,ROOT/'raw',private/'chatgpt-evidence-v1.index.sqlite')
    report={'schema':'pkst.chatgpt-evidence-report@0.1','recorded_at':now,'root':snapshot,'protocol':protocol,'profile':profile,
        'archive':capture['original'],'shards':shards,'members':len(rows),'counts':dict(counts),'gaps':aggregate['gaps'],
        'library_entries':len(librows),'library_exact_matches':sum(bool(x['candidates']) for x in librows),'asset_name_map_entries':len(asset_names),'asset_name_map_unresolved':asset_missing,
        'event_time_min':min(aggregate['times'],key=Decimal),'event_time_max':max(aggregate['times'],key=Decimal),
        'car':str(output.relative_to(BASE)),'index':str((private/'chatgpt-evidence-v1.index.sqlite').relative_to(BASE)),
        'anchors':str((private/'anchors-v1.json').relative_to(BASE)),'envelope':envelope,'structural_verification':verified,
        'elapsed_seconds':round(time.monotonic()-start,3),'status':'source-field-verification-pending','semantic_extraction':'not-performed'}
    (ROOT/'import-report-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('structural_verification','gaps')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
