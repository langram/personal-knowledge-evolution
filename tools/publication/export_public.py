"""Export public conversation and theory projections without exposing private raw backups."""
import collections,hashlib,io,json,os,sqlite3,sys
from pathlib import Path
from html.parser import HTMLParser
from compression import zstd
from safety import tree,sanitize

ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'outputs/personal-thought-archive'
HERE=Path(__file__).resolve().parent;DEST=ROOT/'publication/personal-knowledge-evolution'
sys.path.insert(0,str(BASE/'contributions/codex'))
from pkst_codec import cid,encode,decode,cid_bytes

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')

class PlainHTML(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.hidden+=1
        if tag in {'p','div','br','li','h1','h2','h3','pre','tr'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'}:self.hidden=max(0,self.hidden-1)
        if tag in {'p','div','li','pre','tr'}:self.parts.append('\n')
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    pointer=json.loads((BASE/'contributions/codex/catalog/current.json').read_bytes())
    db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    blocks={row[0]:row[1:] for row in db.execute('SELECT cid,path,offset,size,schema FROM blocks')}
    streams={};verified=set()
    def read(key):
        path,offset,size,schema=blocks[key]
        if path.endswith('.car'):
            if path not in streams:streams[path]=(BASE/path).open('rb')
            stream=streams[path];stream.seek(offset);data=stream.read(size)
        else:
            with (BASE/path).open('rb') as stream:
                stream.seek(offset);data=stream.read(size)
        assert cid(data,cid_bytes(key)[1])==key
        verified.add(key)
        return data if schema=='raw' else decode(data)

    # Inspect native Codex envelopes, because the older catalog omits the channel field.
    groups=collections.defaultdict(list)
    for oc,raw,coords in db.execute('''SELECT a.occurrence,a.raw,a.coordinates_json FROM anchors a
      JOIN current_occurrences o ON o.cid=a.occurrence JOIN sources s ON s.cid=o.source
      WHERE s.platform='codex-local' AND o.role IN ('user','assistant')'''):
        meta=json.loads(coords)
        if 'start' in meta:groups[raw].append((oc,meta['start'],meta['end']))
    visibility={};channels=collections.Counter()
    for raw,targets in groups.items():
        original=read(raw)
        if original.startswith(bytes.fromhex('28b52ffd')):
            with zstd.open(io.BytesIO(original),'rb') as stream:original=stream.read()
        for oc,start,end in targets:
            native=json.loads(original[start:end]);payload=native.get('payload',{})
            channel=payload.get('channel');reason=None
            if payload.get('role') not in {'user','assistant'}:reason='non-conversation-role'
            elif channel not in {None,'final','commentary'}:reason='nonpublic-channel:'+str(channel)
            elif payload.get('is_summary') or payload.get('isMeta'):reason='internal-summary-or-injected'
            if oc in visibility:assert visibility[oc]==reason
            visibility[oc]=reason;channels[str(channel)]+=1
    print(json.dumps({'phase':'native-visibility','codex_envelopes':len(visibility),'channels':channels},ensure_ascii=False),flush=True)

    objects={};events=[];omitted=[];redactions=[];platforms=collections.Counter();html_count=0
    def put(obj):
        key=cid(encode(obj));objects[key]=obj;return key
    def public_content(key):
        obj=read(key)
        if obj['schema']=='pkst/content@0.1':
            clean,found=tree(obj)
            if not found:
                assert cid(encode(obj))==key;objects[key]=obj;return key,None
            pub=put({'schema':'pkst-public/content@1','text':clean['text'],'media_type':obj['media_type'],
              'original_content_cid':key,'transformation':'credential redaction','redactions':found})
            redactions.append({'source_kind':'content','original_cid':key,'public_cid':pub,'findings':found})
            return pub,'redacted'
        if obj['schema']=='pkst/projection@0.1' and obj.get('native_type')=='gemini-safeHtmlItem':
            item=json.loads(obj['text']);assert isinstance(item,dict) and set(item)=={'html'} and isinstance(item['html'],str)
            parser=PlainHTML();parser.feed(item['html']);parser.close()
            plain=''.join(parser.parts)
            clean,found=sanitize(plain)
            pub=put({'schema':'pkst-public/content@1','text':clean,'media_type':'text/plain;charset=utf-8',
              'original_content_cid':key,'transformation':'Gemini HTML to inert plain text; no execution','redactions':found})
            if found:redactions.append({'source_kind':'html-projection','original_cid':key,'public_cid':pub,'findings':found})
            return pub,'html-to-text'
        return None,None

    rows=db.execute('''SELECT o.cid,o.source,o.role,o.actor,o.process,o.event_time,o.event_format,s.platform,s.native_thread_id
      FROM current_occurrences o JOIN sources s ON s.cid=o.source ORDER BY o.cid''').fetchall()
    for oc,source,role,actor,process,event_time,event_format,platform,thread in rows:
        reason=None
        material=role.startswith(('material:','derived-memory:')) or role=='prompt-history'
        if role not in {'user','human','assistant','Prompted','safeHtmlItem'} and not material:reason='non-conversation-record'
        elif actor in {'tool','system'} or process in {'injected','compaction'}:reason='tool-or-internal-record'
        elif platform=='codex-local':reason=visibility.get(oc,'native-envelope-not-verified')
        if reason:
            omitted.append({'occurrence':oc,'reason':reason});continue
        obj=read(oc);parts=[];part_refs=[]
        for original in obj['content']:
            key,transform=public_content(original['$link'])
            if key:
                parts.append({'$link':key});part_refs.append({'original_content_cid':original['$link'],'public_content_cid':key,'transformation':transform})
                if transform=='html-to-text':html_count+=1
        if not parts:
            omitted.append({'occurrence':oc,'reason':'no-publishable-text'});continue
        sobj=read(source);clean,found=tree(sobj)
        assert not found,'Source identity unexpectedly requires redaction'
        objects[source]=sobj
        obj_public={'schema':'pkst-public/event@1','record_kind':'material' if material else 'conversation','original_occurrence_cid':oc,'source':{'$link':source},
          'native_id':obj['native_id'],'native_role':role,'actor_kind':actor,'process_kind':process,
          'event_time':obj['event_time'],'native_parent_ids':obj['native_parent_ids'],'content':parts,
          'content_provenance':part_refs,'raw_evidence_status':'retained locally; excluded from public release'}
        key=put(obj_public)
        events.append({'cid':key,'original_occurrence':oc,'source':source,'platform':platform,'thread':thread,
          'role':role,'actor':actor,'process':process,'record_kind':'material' if material else 'conversation','time':event_time,'time_format':event_format,
          'content':[p['$link'] for p in parts]})
        platforms[platform]+=1

    # Publish all preserved theory/editorial objects as explicit projections. Original links may be private.
    editorial=[]
    allowed={'pkst/concept@0.1','pkst/statement@0.1','pkst/relation@0.1','pkst/change@0.1','pkst/assessment@0.1'}
    for key,(_,_,_,schema) in blocks.items():
        if schema not in allowed and not schema.startswith(('np/','np2/','math/','pi/','sc/')):continue
        obj=read(key);clean,found=tree(obj)
        projection={'schema':'pkst-public/editorial-object@1','original_cid':key,'original_schema':schema,
          'object_projection':clean,'redactions':found,'link_scope':'original archive identifiers; see original-to-public event map and omitted manifest'}
        public=put(projection);editorial.append({'cid':public,'original_cid':key,'schema':schema})
        if found:redactions.append({'source_kind':'editorial-object','original_cid':key,'public_cid':public,'findings':found})

    def shards(kind,items):
        folder=DEST/'corpus'/kind;folder.mkdir(parents=True,exist_ok=True)
        grouped=collections.defaultdict(list)
        for item in items:grouped[hashlib.sha256(item['cid'].encode()).hexdigest()[:2]].append(item)
        for name,rows2 in sorted(grouped.items()):
            path=folder/(name+'.jsonl')
            with path.open('w',encoding='utf-8',newline='\n') as out:
                for row in sorted(rows2,key=lambda r:r['cid']):out.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    shards('objects',[{'cid':key,'object':value} for key,value in objects.items()])
    shards('events',events)
    dump(DEST/'corpus/editorial-index.json',editorial)
    dump(DEST/'publication/omitted-events.json',omitted)
    dump(DEST/'publication/redactions.json',redactions)
    summary={'schema':'pkst-public/coverage@1','source_snapshot':pointer['snapshot'],'catalog_events':len(rows),
      'published_events':len(events),'omitted_events':len(omitted),'omission_counts':dict(collections.Counter(x['reason'] for x in omitted)),
      'events_by_platform':dict(platforms),'record_kinds':dict(collections.Counter(e['record_kind'] for e in events)),'public_objects':len(objects),'editorial_objects':len(editorial),
      'redacted_entries':len(redactions),'gemini_html_projections':html_count,'native_codex_channels':dict(channels),
      'source_blocks_cid_verified':len(verified),'raw_backup_public':False,
      'boundary':'Public conversation and editorial projection, not a byte-complete raw backup. All preserved editorial versions are included; overwritten/unrecorded intermediate edits cannot be reconstructed.'}
    dump(DEST/'publication/coverage.json',summary)
    dump(HERE/'export-summary.json',summary)
    for stream in streams.values():stream.close()
    db.close();print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
