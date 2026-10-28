"""Append sanitized public conversation objects and the seventh book edition."""
import collections
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from prepare import ARCHIVE, BASE, C, OUT, PUBLIC, WORK, ROOT, sha, write_json
from pkst_codec import Store, cid, encode

sys.path.insert(0,str(ROOT/'work/publishing'))
from safety import tree

def prepare_public():
    report=json.loads((ARCHIVE/'report.json').read_bytes())
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    events=json.loads((ARCHIVE/'events.json').read_bytes())
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    capture=json.loads((ARCHIVE/'capture.json').read_bytes())
    metrics=json.loads((OUT/'editorial-statistics.json').read_bytes())
    coverage=json.loads((PUBLIC/'publication/coverage.json').read_bytes())
    editions=json.loads((PUBLIC/'history/editions.json').read_bytes())
    assert len(editions)==6 and coverage['source_snapshot']==baseline['pointer']['snapshot']
    assert sha((PUBLIC/'book/current.md').read_bytes())==baseline['sha256']
    db=sqlite3.connect((PUBLIC/'.cache/catalog.sqlite').as_uri()+'?mode=ro',uri=True)
    store=Store(ARCHIVE);added={};rows=[]
    redactions=json.loads((PUBLIC/'publication/redactions.json').read_bytes())
    prior_redactions=len(redactions);redacted_originals=set()

    def put(obj):
        clean,found=tree(obj)
        assert not found and clean==obj,'explicit redaction required before adding object'
        key=cid(encode(obj));old=db.execute('SELECT body FROM objects WHERE cid=?',(key,)).fetchone()
        if old:assert json.loads(old[0])==obj
        else:added[key]=obj
        return key

    for event in events:
        assert db.execute('SELECT 1 FROM events WHERE original=?',(event['occurrence'],)).fetchone() is None
        source=put(store.get(event['source']));contents=[];provenance=[]
        for original_key in event['content']:
            obj=store.get(original_key);clean,found=tree(obj);public_key=put(clean);contents.append(public_key)
            provenance.append({'original_content_cid':original_key,'public_content_cid':public_key,
                'transformation':'credential-and-export-url-redaction' if found else None})
            if found and original_key not in redacted_originals:
                redactions.append({'original_cid':original_key,'public_cid':public_key,'source_kind':'content','findings':found})
                redacted_originals.add(original_key)
        original=store.get(event['occurrence'])
        obj={'schema':'pkst-public/event@1','record_kind':'conversation','original_occurrence_cid':event['occurrence'],
            'source':{'$link':source},'native_id':original['native_id'],'native_role':event['role'],
            'actor_kind':original['actor_kind'],'process_kind':original['process_kind'],
            'event_time':event['native_event_time'],'native_parent_ids':original['native_parent_ids'],
            'content':[{'$link':key} for key in contents],'content_provenance':provenance,
            'raw_evidence_status':'Local evidence retained; raw records and account backups excluded from public release'}
        if event['time_context']:obj['time_context']=event['time_context']
        public_event=put(obj)
        rows.append({'cid':public_event,'original_occurrence':event['occurrence'],'source':source,
            'platform':event['platform'],'thread':event['thread'],'role':event['role'],'actor':original['actor_kind'],
            'process':original['process_kind'],'record_kind':'conversation','time':event['time'],
            'time_format':event['time_format'],'content':contents})
    editorial=json.loads((PUBLIC/'corpus/editorial-index.json').read_bytes());previous_editorial=len(editorial)
    for key in report['new_objects']:
        path=ARCHIVE/'objects'/(key+'.cbor')
        if not path.is_file():continue
        obj=store.get(key);schema=obj['schema']
        if not schema.startswith('mn/') and schema not in {'pkst/statement@0.1','pkst/concept@0.1','pkst/relation@0.1','pkst/change@0.1'}:continue
        clean,found=tree(obj)
        assert not found,'Editorial source requires explicit treatment'
        public=put({'schema':'pkst-public/editorial-object@1','original_cid':key,'original_schema':schema,
            'object_projection':clean,'redactions':[],
            'link_scope':'original archive identifiers; see original-to-public event map and omission manifest'})
        editorial.append({'cid':public,'original_cid':key,'schema':schema})
    db.close()

    def merge_shards(kind,new_rows):
        grouped=collections.defaultdict(list)
        for row in new_rows:grouped[sha(row['cid'].encode())[:2]].append(row)
        for shard,extra in grouped.items():
            path=PUBLIC/'corpus'/kind/(shard+'.jsonl')
            prior=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
            combined=prior+extra
            assert len({x['cid'] for x in combined})==len(combined)
            path.write_bytes((''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in sorted(combined,key=lambda x:x['cid']))).encode())

    merge_shards('objects',[{'cid':key,'object':value} for key,value in added.items()])
    merge_shards('events',rows)
    write_json(PUBLIC/'corpus/editorial-index.json',editorial)
    write_json(PUBLIC/'publication/redactions.json',redactions)
    coverage['source_snapshot']=report['federated_snapshot']
    coverage['catalog_events']+=len(events);coverage['published_events']+=len(rows)
    coverage['record_kinds']['conversation']+=len(rows)
    for platform,count in capture['new_by_platform'].items():coverage['events_by_platform'][platform]+=count
    # Keep the historical raw-channel statistic separate from API projections.
    for event in events:
        if event['platform']=='codex-local' and event['capture']['origin']['kind']=='local-native-record':
            native=json.loads((ARCHIVE/'raw'/(event['capture']['raw']+'.bin')).read_bytes())
            channel=str(native['payload'].get('channel'))
            coverage['native_codex_channels'][channel]=coverage['native_codex_channels'].get(channel,0)+1
    coverage['public_objects']+=len(added);coverage['editorial_objects']=len(editorial)
    coverage['redacted_entries']+=len(redactions)-prior_redactions
    update={'edition':'07-merkle-native','source_snapshot':report['federated_snapshot'],
        'window_start':capture['window_start'],'window_end':capture['window_end'],'added_events':len(rows),
        'added_native_records':capture['native_records'],'added_remote_visible_projections':capture['remote_projection_records'],
        'added_public_objects':len(added),'added_editorial_objects':len(editorial)-previous_editorial,
        'new_original_blocks_verified':len(report['new_objects']),'previous_link_targets_verified':report['verified_previous_link_targets'],
        'redacted_content_objects':len(redactions)-prior_redactions,'coverage_limits':capture['coverage_limits'],
        'recorded_at':datetime.now(timezone.utc).isoformat()}
    coverage.setdefault('incremental_updates',[]).append(update)
    write_json(PUBLIC/'publication/coverage.json',coverage)
    receipt=f'''# 入库与公开投影收据

专题根：`{report['snapshot']}`。
联合知识库根：`{report['federated_snapshot']}`。
新全文对象：`{report['document']}`。
新增消息：{len(events)}；原始知识库当前共{report['current_events']}条事件；公开投影共{coverage['published_events']}条事件。

原生记录{capture['native_records']}条，远程接口可见投影{capture['remote_projection_records']}条。正文共{metrics['combined_cjk']}个CJK字符，本章{metrics['chapter_cjk']}个；这些是明确口径的计数，不包含西文、数字与标点。原话摘取、编辑改动与整章插入已经重放核验，旧稿其余部分逐字节保持不变。

公开投影沿用既有脱敏规则。本轮在1个内容对象中移除4个Claude数据导出下载地址；完整原话和原始证据仍在本地知识库。此收据不包含原始账户备份，也不证明所有设备和云端来源已刷新。Git提交和远端发布状态以实际Git记录为准。本收据在专题根生成后写入，不参与自身专题根。
'''
    (OUT/'09-archive-receipt.md').write_bytes(receipt.encode())
    for path in OUT.iterdir():
        if not path.is_file():continue
        value=path.read_text(encoding='utf-8');clean,found=tree(value)
        assert not found and clean==value,'Dossier file requires explicit redaction'
        target=PUBLIC/'archive'/path.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    for name in ['baseline.json','capture.json','selected-sources.json','text-verification.json','report.json','status.json']:
        value=json.loads((ARCHIVE/name).read_bytes())
        if name=='capture.json':
            value={k:v for k,v in value.items() if not isinstance(v,list) or k=='coverage_limits'}
            value['native_scan_locations']='Retained locally in the exact capture evidence.'
        if name=='selected-sources.json':
            for entry in value.values():
                ev=entry['capture'];entry['capture']={k:ev[k] for k in ['raw','sha256','bytes']}
                entry['capture']['origin_status']='Exact source path and offsets retained locally.'
        clean,found=tree(value);assert not found,'Metadata needs explicit redaction'
        target=PUBLIC/'archive/contributions/codex'/ARCHIVE.name/name;target.parent.mkdir(parents=True,exist_ok=True)
        write_json(target,clean)
    write_json(PUBLIC/'archive/contributions/codex'/ARCHIVE.name/'public-update.json',update)
    for path in WORK.glob('*.py'):
        target=PUBLIC/'work/merkle-native'/path.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    for name in ['current.json',pointer['report']]:shutil.copyfile(C/'catalog'/name,PUBLIC/'archive/contributions/codex/catalog'/name)
    shutil.copyfile(OUT/'02-new-principles.md',PUBLIC/'book/current.md')
    edition={'edition':'07-merkle-native','title':'AI时代的Merkle-DAG语言与软件生态',
        'file':'archive/dossiers/'+OUT.name+'/02-new-principles.md','sha256':metrics['combined_sha256'],'cjk_characters':metrics['combined_cjk']}
    editions.append(edition);write_json(PUBLIC/'history/editions.json',editions)
    history=PUBLIC/'history/README.md';text=history.read_text(encoding='utf-8');marker='\n更早的[整体框架'
    assert text.count(marker)==1
    text=text.replace(marker,f'|AI时代的Merkle-DAG语言与软件生态|{metrics["combined_cjk"]:,}|[正文](../{edition["file"]})|\n'+marker)
    text+='\n2026年10月29日新增[AI时代的Merkle-DAG语言与软件生态](../archive/dossiers/'+OUT.name+'/01-chapter.md)，置于MerkleVM章节之后、协作研发章节之前。保存[原话与编辑对照](../archive/dossiers/'+OUT.name+'/03-source-ledger.md)、[讨论演化](../archive/dossiers/'+OUT.name+'/04-evolution-and-placement.md)与[本轮覆盖](../archive/dossiers/'+OUT.name+'/06-import-coverage.md)。\n'
    history.write_bytes(text.encode())
    readme=PUBLIC/'README.md';text=readme.read_text(encoding='utf-8');marker='- [《新原理》当前全文](book/current.md)\n';assert text.count(marker)==1
    text=text.replace(marker,marker+'- [新增：AI时代的Merkle-DAG语言与软件生态](archive/dossiers/'+OUT.name+'/01-chapter.md)\n- [本轮原话、编辑与演化记录](archive/dossiers/'+OUT.name+'/04-evolution-and-placement.md)\n')
    text=text.replace('- [本轮原话与逐项改写对照](archive/dossiers/2026-10-27-protection-and-trust/03-source-ledger.md)',
        '- [本轮原话与逐项改写对照](archive/dossiers/'+OUT.name+'/03-source-ledger.md)')
    text+='\n最近增量（2026年10月29日）：385条可见对话消息，271条本机原生记录、114条远程会话接口投影；不代表所有云端已刷新。完整边界见[覆盖说明](archive/dossiers/'+OUT.name+'/06-import-coverage.md)。\n'
    readme.write_bytes(text.encode())
    print(json.dumps({'prepared':True,'added_public_objects':len(added),'added_events':len(rows),
        'published_events':coverage['published_events'],'editions':len(editions),'chapter_cjk':metrics['chapter_cjk'],
        'redacted_content_objects':len(redactions)-prior_redactions},ensure_ascii=False))

if __name__=='__main__':prepare_public()
