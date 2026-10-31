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
        if not schema.startswith('rfa/') and schema not in {'pkst/statement@0.1','pkst/concept@0.1','pkst/relation@0.1','pkst/change@0.1'}: continue
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
    update={'edition':'11-ability-resource-formation','source_snapshot':report['federated_snapshot'],
        'window_start':events[0]['time'],'window_end':events[-1]['time'],'added_events':n,
        'added_user_messages':sum(e['role']=='user' for e in events),'added_assistant_final_answers':sum(e['role']=='assistant' for e in events),
        'added_public_objects':len(added),'added_editorial_objects':len(editorial)-prior_editorial,
        'new_original_blocks_verified':len(report['new_objects']),'previous_link_targets_verified':report['verified_previous_link_targets'],
        'recorded_at':datetime.now(timezone.utc).isoformat()}
    coverage.setdefault('incremental_updates',[]).append(update)
    write_json(PUBLIC/'publication/coverage.json',coverage)
    receipt=f'''# 能力形成与资源累积归档收据

本版修改一个动态权重小节。该节 {metrics['section_cjk']:,} 汉字，净增 {metrics['net_added_cjk']:,} 汉字；全书 {metrics['combined_cjk']:,} 汉字。

两条来源记录包含作者本次回应与前一轮AI公开最终答复。原话、来源时间、三个改写片段、两个编辑稿与差异均保留。单节替换之外的旧稿和末尾附录保持原字节。

专题根：`{report['snapshot']}`。

统一根：`{report['federated_snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

全文 SHA-256：`{metrics['combined_sha256']}`。

统一来源事件 {report['current_events']:,} 条，公开事件 {coverage['published_events']:,} 条。

归档及文本校验不证明正态分布、因果效应或制度有效性。新的编辑补写未标记为作者逐句接受。此收据在专题根形成后生成，由公开文件清单和Git保存，不参与自身专题根。
'''
    (OUT/'09-archive-receipt.md').write_bytes(receipt.encode())
    for path in OUT.iterdir():
        if path.is_file():
            target=PUBLIC/'archive'/path.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    for name in ['baseline.json','capture.json','text-verification.json','report.json','status.json']:
        value=json.loads((ARCHIVE/name).read_bytes())
        if name=='capture.json':
            for e in value['events']:
                capture=e['capture'];e['capture']={k:capture[k] for k in ['raw','sha256','bytes','captured_at']}
                e['capture']['status']='Native location and raw envelope retained locally; visible text unchanged.'
        target=PUBLIC/'archive/contributions/codex'/ARCHIVE.name/name;target.parent.mkdir(parents=True,exist_ok=True)
        write_json(target,value)
    for path in WORK.glob('*.py'):
        target=PUBLIC/'work'/WORK.name/path.name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    for name in ['current.json',pointer['report']]:
        shutil.copyfile(C/'catalog'/name,PUBLIC/'archive/contributions/codex/catalog'/name)
    shutil.copyfile(OUT/'02-new-principles.md',PUBLIC/'book/current.md')
    editions=json.loads((PUBLIC/'history/editions.json').read_bytes());assert len(editions)==10
    edition={'edition':'11-ability-resource-formation','title':'能力形成、资源累积与分布的因果区分',
             'file':'archive/dossiers/'+OUT.name+'/02-new-principles.md','sha256':metrics['combined_sha256'],'cjk_characters':metrics['combined_cjk']}
    editions.append(edition);write_json(PUBLIC/'history/editions.json',editions)
    history=PUBLIC/'history/README.md';text=history.read_text(encoding='utf-8');marker='\n更早的[整体框架'
    assert text.count(marker)==1
    text=text.replace(marker,f'|{edition["title"]}|{metrics["combined_cjk"]:,}|[正文](../{edition["file"]})|\n'+marker)
    text+='\n2026年10月31日第十一版重写动态权重中的[能力形成与资源累积讨论](../archive/dossiers/'+OUT.name+'/01-section.md)，保存[原话与修改对照](../archive/dossiers/'+OUT.name+'/03-source-ledger.md)及[编辑说明](../archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\n'
    history.write_bytes(text.encode())
    readme=PUBLIC/'README.md';text=readme.read_text(encoding='utf-8');marker='- [《新原理》当前全文](book/current.md)\n'
    assert text.count(marker)==1
    text=text.replace(marker,marker+'- [本次修订：能力形成、资源累积与分布](archive/dossiers/'+OUT.name+'/01-section.md)\n')
    text=text.replace('本次增补：文明自我治理、权重边界与制度探索','文明自我治理、权重边界与制度探索')
    old='- [本轮原话与逐项改写对照](archive/dossiers/2026-10-31-civilization-self-governance/03-source-ledger.md)'
    assert text.count(old)==1
    text=text.replace(old,'- [本轮原话与逐项改写对照](archive/dossiers/'+OUT.name+'/03-source-ledger.md)')
    text+='\n2026年10月31日第十一版补入作者关于资源参与能力形成的回应，区分现有绩效、成长条件与不同制度下的能力分布。体育项目的比较保留为待检验假说；全文与编辑记录见[说明](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\n'
    readme.write_bytes(text.encode())
    publication=PUBLIC/'publication/README.md';text=publication.read_text(encoding='utf-8')
    start=text.index('截至第十版');end=text.index('\n\n',start)
    replacement=f"截至第十一版（2026年10月31日），原档案当前目录含 {coverage['catalog_events']:,} 条来源记录。公开 {coverage['published_events']:,} 条记录，其中会话 {coverage['record_kinds']['conversation']:,} 条、材料 {coverage['record_kinds']['material']:,} 条；另保存 {coverage['editorial_objects']:,} 个理论与编辑对象的公开投影。数量与逐次增补记录见 [coverage.json](coverage.json)。"
    publication.write_bytes((text[:start]+replacement+text[end:]).encode())
    write_json(WORK/'public-preparation.json',{'status':'prepared','update':update,'events':rows,'editions':len(editions)})
    print(json.dumps({'status':'prepared','added_objects':len(added),'published_events':coverage['published_events'],'editions':len(editions)},ensure_ascii=False))

if __name__=='__main__':publish()
