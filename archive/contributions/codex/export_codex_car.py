"""Turn captured Codex message evidence into immutable PKST objects and CARv1.

Raw records remain complete. This adapter emits response_item/message objects;
reasoning/tool-event records outside that projection stay raw-only, with counts.
"""
import argparse,hashlib,json,re,sys,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from compression import zstd
from pkst_codec import cid,link,linkset,loads
from pkst_car import CarWriter,inspect_car
from index_codex import records

PARSER='codex-response-item@0.1.0'

def event_time(value):
    if not isinstance(value,str):
        return dict(value=None,format='unknown',precision='unknown',zone_known=False,unit=None)
    match=re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.(\d+))?(?:Z|[+-]\d\d:\d\d)',value)
    frac=len(match.group(1) or '') if match else 0
    return dict(value=value,format='rfc3339' if match else 'source-text',
                precision=('second' if frac==0 else 'millisecond' if frac<=3 else 'microsecond' if frac<=6 else 'unknown') if match else 'unknown',
                zone_known=bool(match),unit=None)

def preserve_raw(root,data):
    key=cid(data,0x55);p=root/'raw'/(key+'.bin')
    if p.exists():
        if p.read_bytes()!=data:raise ValueError('Corrupt raw block')
    else:
        with p.open('xb') as f:f.write(data)
    return key

def block_object(part):
    typ=str(part.get('type','unknown')) if isinstance(part,dict) else 'non-map'
    if isinstance(part,dict) and typ in ('input_text','output_text','text') and isinstance(part.get('text'),str):
        return {'schema':'pkst/content@0.1','media_type':'text/plain;charset=utf-8','text':part['text']}
    text=json.dumps(part,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    if any(word in typ.lower() for word in ('reason','think','image','audio','encrypt')):
        return {'schema':'pkst/opaque-block@0.1','native_type':typ,'profile':'python-json-v1',
                'digest':hashlib.sha256(text.encode('utf-8')).hexdigest(),'handling':'raw-only'}
    return {'schema':'pkst/projection@0.1','native_type':typ,'profile':'python-json-v1','text':text}

def convert_file(writer,row,root,protocol):
    raw=row['raw_cid'];path=root/'raw'/(raw+'.bin')
    source_id=None;process='unknown';source_cid=None
    counts=Counter();errors=[];roots=[raw]
    opener=zstd.open if row['source_suffix'].endswith('.zst') else open
    with opener(path,'rb') as stream:
        for start,end,line,failure in records(stream):
            if failure:
                errors.append({'start':start,'end':end,'error':failure});continue
            # Coordinate excludes LF, keeps CR. Parsed final complete JSON without LF is retained.
            anchor_end=end-1 if line.endswith(b'\n') else end
            try:d=loads(line)
            except (ValueError,UnicodeError) as exc:
                errors.append({'start':start,'end':anchor_end,'error':type(exc).__name__});continue
            typ=d.get('type','unknown');p=d.get('payload',{});counts[str(typ)]+=1
            if not isinstance(p,dict):continue
            if typ=='session_meta':
                source_id=p.get('id') or p.get('session_id')
                native_source=p.get('source')
                process='sidechain' if isinstance(native_source,dict) and 'subagent' in native_source else 'unknown'
                source_cid=None
            if typ!='response_item' or p.get('type')!='message':continue
            if not source_cid:
                source_cid=writer.put({'schema':'pkst/source@0.1','platform':'codex-local',
                    'namespace':'owner-openai-account','native_thread_id':str(source_id or 'raw:'+raw)})
            parts=p.get('content',[])
            if not isinstance(parts,list):raise ValueError('Message content must be an ordered list')
            content=[writer.put(block_object(part)) for part in parts]
            native_id=p.get('id') if isinstance(p.get('id'),str) and p.get('id') else None
            locator=None if native_id else {'raw':link(raw),'start':start,'end':anchor_end,'coordinate':'decoded-jsonl-utf8-bytes'}
            role=str(p.get('role','unknown'))
            actor={'assistant':'ai','developer':'system','system':'system','tool':'tool'}.get(role,'unknown')
            parents=None
            if 'parent_id' in p:
                parents=[] if p['parent_id'] is None else [str(p['parent_id'])]
            occurrence={'schema':'pkst/occurrence@0.1','source':link(source_cid),'native_id':native_id,'locator':locator,
                'native_role':role,'actor_kind':actor,'process_kind':process,'content':[link(k) for k in content],
                'native_parent_ids':parents,'event_time':event_time(d.get('timestamp'))}
            ocid=writer.put(occurrence)
            er={'schema':'pkst/extraction-record@0.1','raw':link(raw),'occurrence':link(ocid),
                'start':start,'end':anchor_end,'coordinate':'decoded-jsonl-utf8-bytes','parser':PARSER,
                'role_basis':'response_item.role='+role+'; user channel authorship unverified'}
            roots.append(writer.put(er));counts['emitted-occurrence']+=1
    coverage={'source_raw':link(raw),'status':'partial' if errors else 'parsed',
              'projection':'response_item.message; other record kinds remain raw-only',
              'counts':dict(counts),'parse_errors':errors,'attachments':'not-reconciled',
              'source_native_id_available':source_id is not None}
    snap=writer.put({'schema':'pkst/snapshot@0.1','parents':[],'roots':linkset(roots),'coverage':coverage,'protocol':link(protocol)})
    return snap,counts,errors

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',required=True);ap.add_argument('--manifest',required=True)
    ap.add_argument('--protocol',required=True);ap.add_argument('--output',required=True)
    ap.add_argument('--host',default='windows-main')
    ap.add_argument('--provenance',action='append',default=[])
    args=ap.parse_args();root=Path(args.root);output=Path(args.output)
    protocol=preserve_raw(root,Path(args.protocol).read_bytes())
    implementation=preserve_raw(root,Path(__file__).read_bytes())
    manifest_bytes=Path(args.manifest).read_bytes();manifest_cid=preserve_raw(root,manifest_bytes)
    provenance=[preserve_raw(root,Path(path).read_bytes()) for path in args.provenance]
    rows=[json.loads(line) for line in manifest_bytes.decode('utf-8').splitlines()]
    external={r['raw_cid'] for r in rows if r.get('status')=='captured'}|{protocol,implementation,manifest_cid}|set(provenance)
    writer=CarWriter(output);snapshots=[];totals=Counter();failures=[];seen=set();t=time.monotonic()
    for i,row in enumerate(rows):
        if row.get('status')!='captured':
            failures.append({'source':row.get('raw_cid'),'error':'capture-not-stable'});continue
        if row['raw_cid'] in seen:continue
        seen.add(row['raw_cid'])
        snap,counts,errors=convert_file(writer,row,root,protocol)
        snapshots.append(snap);totals.update(counts)
        if errors:failures.append({'source':row['raw_cid'],'errors':errors})
        if (i+1)%400==0:print(json.dumps({'processed':i+1,'of':len(rows),'blocks':len(writer.seen)}),flush=True)
    activity=writer.put({'schema':'pkst/activity@0.1','operation':'import',
        'recorded_at':datetime.now(timezone.utc).isoformat(),'actor':{'kind':'ai','id':'codex'},
        'inputs':linkset([manifest_cid]+provenance),'outputs':linkset(snapshots),'implementation':link(implementation),
        'coverage':{'files':len(seen),'counts':dict(totals),'failures':failures,'python':sys.version.split()[0]}})
    snapshot=writer.put({'schema':'pkst/snapshot@0.1','parents':[],'roots':linkset([activity]),
        'coverage':{'platform':'codex-local','host':args.host,'source_files':len(seen),
                    'source_scope':'captured sessions and archived_sessions JSONL/Zstandard JSONL',
                    'external_raw':True,'semantic_extraction':'not-performed'},'protocol':link(protocol)})
    envelope=writer.finish([snapshot],external)
    verified=inspect_car(output,root/'raw',output.with_suffix('.index.sqlite'))
    report={'schema':'pkst.car-report.v0.1','root':snapshot,'protocol':protocol,'car':str(output),
            'envelope':envelope,'verification':verified,'counts':dict(totals),'failures':failures,
            'elapsed_seconds':round(time.monotonic()-t,3),'scope':'message evidence, not extracted beliefs'}
    output.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
