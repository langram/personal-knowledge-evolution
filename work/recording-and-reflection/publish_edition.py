"""Prepare the authorized public projection without publishing private raw records."""
import collections
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from prepare import ARCHIVE, BASE, C, OUT, PUBLIC, ROOT, WORK, sha, write_json
from pkst_codec import Store, cid, encode
sys.path.insert(0,str(ROOT/'work/publishing'))
from safety import tree

def publish():
    report=json.loads((ARCHIVE/'report.json').read_bytes())
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    metrics=json.loads((OUT/'editorial-statistics.json').read_bytes())
    coverage=json.loads((PUBLIC/'publication/coverage.json').read_bytes())
    assert coverage['source_snapshot']==baseline['pointer']['snapshot']
    assert sha((PUBLIC/'book/current.md').read_bytes())==baseline['sha256']
    db=sqlite3.connect((PUBLIC/'.cache/catalog.sqlite').as_uri()+'?mode=ro',uri=True)
    store=Store(ARCHIVE); added={}; rows=[]
    def put(obj):
        clean,findings=tree(obj)
        assert not findings and clean==obj,'New material requires explicit redaction review.'
        key=cid(encode(obj)); old=db.execute('SELECT body FROM objects WHERE cid=?',(key,)).fetchone()
        if old: assert json.loads(old[0])==obj
        else:
            if key in added: assert added[key]==obj
            added[key]=obj
        return key
    for e in events:
        source=put(store.get(e['source'])); content=put(store.get(e['content'])); original=store.get(e['occurrence'])
        assert db.execute('SELECT 1 FROM events WHERE original=?',(e['occurrence'],)).fetchone() is None
        key=put({'schema':'pkst-public/event@1','record_kind':'conversation','original_occurrence_cid':e['occurrence'],
            'source':{'$link':source},'native_id':original['native_id'],'native_role':e['role'],'actor_kind':original['actor_kind'],
            'process_kind':'main','event_time':e['native_event_time'],'native_parent_ids':original['native_parent_ids'],
            'content':[{'$link':content}],'content_provenance':[{'original_content_cid':content,'public_content_cid':content,'transformation':None}],
            'raw_evidence_status':'retained locally; excluded from public release'})
        rows.append({'cid':key,'original_occurrence':e['occurrence'],'source':source,'platform':e['platform'],'thread':e['thread'],
            'role':e['role'],'actor':original['actor_kind'],'process':'main','record_kind':'conversation',
            'time':e['time'],'time_format':e['time_format'],'content':[content]})
    editorial=json.loads((PUBLIC/'corpus/editorial-index.json').read_bytes()); prior_editorial=len(editorial)
    for key in report['new_objects']:
        path=ARCHIVE/'objects'/(key+'.cbor')
        if not path.exists(): continue
        obj=store.get(key); schema=obj['schema']
        if not schema.startswith('rr/') and schema not in {'pkst/statement@0.1','pkst/concept@0.1','pkst/relation@0.1','pkst/change@0.1'}: continue
        public=put({'schema':'pkst-public/editorial-object@1','original_cid':key,'original_schema':schema,
            'object_projection':obj,'redactions':[],
            'link_scope':'original archive identifiers; see original-to-public event map and omitted manifest'})
        editorial.append({'cid':public,'original_cid':key,'schema':schema})
    db.close()
    def merge(kind,new_rows):
        shards=collections.defaultdict(list)
        for row in new_rows: shards[sha(row['cid'].encode())[:2]].append(row)
        for shard,extra in shards.items():
            path=PUBLIC/'corpus'/kind/(shard+'.jsonl')
            prior=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
            combined=prior+extra; assert len({x['cid'] for x in combined})==len(combined)
            path.write_bytes(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
                for x in sorted(combined,key=lambda x:x['cid'])).encode())
    merge('objects',[{'cid':k,'object':v} for k,v in added.items()]); merge('events',rows)
    write_json(PUBLIC/'corpus/editorial-index.json',editorial)
    n=len(events)
    coverage['source_snapshot']=report['federated_snapshot']
    for key in ['catalog_events','published_events']: coverage[key]+=n
    coverage['record_kinds']['conversation']+=n; coverage['events_by_platform']['codex-local']+=n
    for e in events:
        p=json.loads((ARCHIVE/'raw'/(e['capture']['raw']+'.bin')).read_bytes())['payload']
        channel=str(p.get('channel'))
        coverage['native_codex_channels'][channel]=coverage['native_codex_channels'].get(channel,0)+1
    coverage['public_objects']+=len(added); coverage['editorial_objects']=len(editorial)
    update={'edition':'09-recording-and-reflection','source_snapshot':report['federated_snapshot'],
        'window_start':events[0]['time'],'window_end':events[-1]['time'],'added_events':n,
        'added_user_messages':sum(e['role']=='user' for e in events),'added_assistant_final_answers':sum(e['role']=='assistant' for e in events),
        'added_public_objects':len(added),'added_editorial_objects':len(editorial)-prior_editorial,
        'new_original_blocks_verified':len(report['new_objects']),'previous_link_targets_verified':report['verified_previous_link_targets'],
        'recorded_at':datetime.now(timezone.utc).isoformat()}
    coverage.setdefault('incremental_updates',[]).append(update)
    write_json(PUBLIC/'publication/coverage.json',coverage)
    receipt=f'''# 个人信息采集与自我反思归档收据

新增正文 {metrics['chapter_cjk']:,} 汉字，末尾附录 {metrics['appendix_cjk']:,} 汉字，全文 {metrics['combined_cjk']:,} 汉字。

四条作者发言与三条AI完整答复，保留角色、原话与原生时间。24处来源片段、72个成文单元通过逐项重放；两处插入和逆向恢复通过，前版其他字节保持不变。自我反思附录位于后记之后，是最后一个一级章节。独立检查了线性迭代反例及假设码率下的存储估算。

专题根：`{report['snapshot']}`。

统一根：`{report['federated_snapshot']}`。

父统一根：`{report['baseline_snapshot']}`。

全文 SHA-256：`{metrics['combined_sha256']}`。

统一来源事件 {report['current_events']:,} 条，公开事件 {coverage['published_events']:,} 条。新语义节点、关系与讨论演化记录连接既有理论；它们是可审查的编辑判断，不冒充作者已经逐项接受或现实因果已获确认。

本次核验针对内容身份、引用、新增索引和编辑重放，不证明新公理、统一物理、监控硬件或文明制度有效。原始本机会话取证与完整私有数据库仍保留本地。Git提交与推送以实际Git记录为准。此收据在专题根形成后生成，不参与自身专题根。
'''
    (OUT/'09-archive-receipt.md').write_bytes(receipt.encode())
    for path in OUT.iterdir():
        if path.is_file():
            target=PUBLIC/'archive'/path.relative_to(BASE); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    for name in ['baseline.json','capture.json','text-verification.json','report.json','status.json']:
        value=json.loads((ARCHIVE/name).read_bytes())
        if name=='capture.json':
            for e in value['events']:
                c=e['capture']; e['capture']={k:c[k] for k in ['raw','sha256','bytes','captured_at']}
                e['capture']['status']='Native location and raw envelope retained locally; visible source text unchanged.'
        target=PUBLIC/'archive/contributions/codex'/ARCHIVE.name/name; target.parent.mkdir(parents=True,exist_ok=True)
        write_json(target,value)
    for path in WORK.glob('*.py'):
        target=PUBLIC/'work/recording-and-reflection'/path.name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    for name in ['current.json',pointer['report']]: shutil.copyfile(C/'catalog'/name,PUBLIC/'archive/contributions/codex/catalog'/name)
    shutil.copyfile(OUT/'02-new-principles.md',PUBLIC/'book/current.md')
    editions=json.loads((PUBLIC/'history/editions.json').read_bytes()); assert len(editions)==8
    edition={'edition':'09-recording-and-reflection','title':'个人信息采集与全书自我反思',
        'file':'archive/dossiers/'+OUT.name+'/02-new-principles.md','sha256':metrics['combined_sha256'],'cjk_characters':metrics['combined_cjk']}
    editions.append(edition); write_json(PUBLIC/'history/editions.json',editions)
    history=PUBLIC/'history/README.md'; text=history.read_text(encoding='utf-8'); marker='\n更早的[整体框架'
    assert text.count(marker)==1
    text=text.replace(marker,f'|{edition["title"]}|{metrics["combined_cjk"]:,}|[正文](../{edition["file"]})|\n'+marker)
    text+='\n2026年10月30日新增[个人信息采集与技术落地](../archive/dossiers/'+OUT.name+'/01-chapter.md)，并在后记之后追加全书最后的[自我反思附录](../archive/dossiers/'+OUT.name+'/05-self-reflection-appendix.md)，覆盖数学、基础科学、社会与工程可行性。[原话与逐项编辑](../archive/dossiers/'+OUT.name+'/03-source-ledger.md)及[说明](../archive/dossiers/'+OUT.name+'/04-editorial-notes.md)同时保留。\n'
    history.write_bytes(text.encode())
    readme=PUBLIC/'README.md'; text=readme.read_text(encoding='utf-8'); marker='- [《新原理》当前全文](book/current.md)\n'
    assert text.count(marker)==1
    text=text.replace(marker,marker+'- [个人信息采集、数据主权与技术落地](archive/dossiers/'+OUT.name+'/01-chapter.md)\n- [书末附录：对理论基础与实践可行性的自我反思](archive/dossiers/'+OUT.name+'/05-self-reflection-appendix.md)\n')
    text=text.replace('- [本轮原话与逐项改写对照](archive/dossiers/2026-10-29-cooperation-feedback/03-source-ledger.md)',
        '- [本轮原话与逐项改写对照](archive/dossiers/'+OUT.name+'/03-source-ledger.md)')
    text+='\n2026年10月30日追加七条来源讨论，形成第九版全文；个人信息采集与技术落地进入正文，涵盖数学和基础科学的自我反思成为书末最后附录。详见[本次编辑说明](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\n'
    readme.write_bytes(text.encode())
    write_json(WORK/'public-preparation.json',{'status':'prepared','update':update,'events':rows,'editions':len(editions)})
    print(json.dumps({'status':'prepared','added_objects':len(added),'published_events':coverage['published_events'],'editions':len(editions)},ensure_ascii=False))

if __name__=='__main__': publish()
