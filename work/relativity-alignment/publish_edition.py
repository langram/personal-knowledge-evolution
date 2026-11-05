"""Prepare the authorized public edition; raw native envelopes remain private."""
import collections
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from prepare import ARCHIVE, BASE, C, EDITION, OUT, PUBLIC, ROOT, WORK, sha, write_json
from pkst_codec import Store, cid, encode
sys.path.insert(0,str(ROOT/'work/publishing'))
from safety import tree

def publish():
    report=json.loads((ARCHIVE/'report.json').read_bytes())
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    events=json.loads((ARCHIVE/'capture.json').read_bytes())['events']
    metrics=json.loads((OUT/'editorial-statistics.json').read_bytes())
    coverage=json.loads((PUBLIC/'publication/coverage.json').read_bytes())
    assert coverage['source_snapshot']==baseline['pointer']['snapshot'], 'Inspect prior publication before retry.'
    assert sha((PUBLIC/'book/current.md').read_bytes())==baseline['sha256']
    assert sha((PUBLIC/'book/current.en.md').read_bytes())==baseline['english_sha256']
    db=sqlite3.connect((PUBLIC/'.cache/catalog.sqlite').as_uri()+'?mode=ro',uri=True)
    store=Store(ARCHIVE);added={};rows=[]
    def put(obj):
        clean,findings=tree(obj)
        assert not findings and clean==obj,'New material requires explicit redaction review.'
        key=cid(encode(obj));old=db.execute('SELECT body FROM objects WHERE cid=?',(key,)).fetchone()
        if old: assert json.loads(old[0])==obj
        elif key in added: assert added[key]==obj
        else: added[key]=obj
        return key
    for e in events:
        source=put(store.get(e['source']));content=put(store.get(e['content']));original=store.get(e['occurrence'])
        assert db.execute('SELECT 1 FROM events WHERE original=?',(e['occurrence'],)).fetchone() is None
        key=put({'schema':'pkst-public/event@1','record_kind':'conversation','original_occurrence_cid':e['occurrence'],
            'source':{'$link':source},'native_id':original['native_id'],'native_role':e['role'],'actor_kind':original['actor_kind'],
            'process_kind':'main','event_time':e['native_event_time'],'native_parent_ids':original['native_parent_ids'],
            'content':[{'$link':content}],'content_provenance':[{'original_content_cid':content,'public_content_cid':content,'transformation':None}],
            'raw_evidence_status':'retained locally; excluded from public release'})
        rows.append({'cid':key,'original_occurrence':e['occurrence'],'source':source,'platform':e['platform'],'thread':e['thread'],
            'role':e['role'],'actor':original['actor_kind'],'process':'main','record_kind':'conversation',
            'time':e['time'],'time_format':e['time_format'],'content':[content]})
    editorial=json.loads((PUBLIC/'corpus/editorial-index.json').read_bytes());prior_editorial=len(editorial)
    for key in report['new_objects']:
        if not (ARCHIVE/'objects'/(key+'.cbor')).exists(): continue
        obj=store.get(key);schema=obj['schema']
        if not schema.startswith('ra/') and schema not in {'pkst/statement@0.1','pkst/concept@0.1','pkst/relation@0.1','pkst/change@0.1'}: continue
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
            combined=prior+extra;assert len({x['cid'] for x in combined})==len(combined)
            path.write_bytes(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
                for x in sorted(combined,key=lambda x:x['cid'])).encode())
    merge('objects',[{'cid':k,'object':v} for k,v in added.items()]);merge('events',rows)
    write_json(PUBLIC/'corpus/editorial-index.json',editorial)
    n=len(events);coverage['source_snapshot']=report['federated_snapshot']
    for key in ['catalog_events','published_events']: coverage[key]+=n
    coverage['record_kinds']['conversation']+=n
    for e in events:
        platform=e['platform'];coverage['events_by_platform'][platform]=coverage['events_by_platform'].get(platform,0)+1
        if platform=='codex-local':
            p=json.loads((ARCHIVE/'raw'/(e['capture']['raw']+'.bin')).read_bytes())['payload']
            channel=str(p.get('channel'));coverage['native_codex_channels'][channel]=coverage['native_codex_channels'].get(channel,0)+1
    coverage['public_objects']+=len(added);coverage['editorial_objects']=len(editorial)
    update={'edition':EDITION,'source_snapshot':report['federated_snapshot'],
        'window_start':next(e['time'] for e in events if e['platform']=='codex-local'),'window_end':events[-1]['time'],'added_events':n,
        'window_scope':'UTC window covers native Codex events only; attached Gemini export has unknown timezone and missing reply times.',
        'added_user_messages':sum(e['role']=='user' for e in events),
        'added_assistant_final_answers':sum(e['role']=='assistant' and e['platform']=='codex-local' for e in events),
        'added_gemini_export_replies':sum(e['role']=='assistant' and e['platform']=='gemini' for e in events),
        'added_by_platform':dict(collections.Counter(e['platform'] for e in events)),
        'added_public_objects':len(added),'added_editorial_objects':len(editorial)-prior_editorial,
        'new_original_blocks_verified':len(report['new_objects']),'previous_link_targets_verified':report['verified_previous_link_targets'],
        'recorded_at':datetime.now(timezone.utc).isoformat()}
    coverage.setdefault('incremental_updates',[]).append(update);write_json(PUBLIC/'publication/coverage.json',coverage)
    receipt=f'''# 第十八版归档收据：相对性与多层级对齐

书名为《新原理：社会科学的数学原理》与 Nova Principia: Mathematical Principles of Social Science。新增第7章认知参考系，第25章补入多层级对齐，第33章补入自我反思。中英文各7处可逆修改；全书33章、{metrics['headings']}个标题；29组章节双语逐字节不变。

新增15条可见来源事件：Gemini导出10段，Codex本机会话5条，共8条作者言论和7条AI回复。原话、编辑限定、中文版本和英文派生关系分别保存。Gemini用户时间无时区、AI回复无时间戳，保留未知；重复请求保留为不同发生事件。本轮语义阅读覆盖新增文字及相关上下文，不称为再次通读全书。

专题根：`{report['snapshot']}`。

统一根：`{report['federated_snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

中文 SHA-256：`{metrics['chinese_sha256']}`。

英文 SHA-256：`{metrics['english_sha256']}`。

统一来源事件{report['current_events']:,}条；公开事件{coverage['published_events']:,}条。

来源、可逆修改、章节引用与对象版本关系经过检查；这不证明理论成立，也不表示编辑措辞已获作者逐句认可。本收据在专题根形成后生成，由公开文件清单与Git保存，不参与自身专题根。
'''
    (OUT/'09-archive-receipt.md').write_bytes(receipt.encode())
    for path in OUT.iterdir():
        if path.is_file():
            target=PUBLIC/'archive'/path.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    for name in ['baseline.json','capture.json','text-verification.json','report.json','status.json']:
        value=json.loads((ARCHIVE/name).read_bytes())
        if name=='capture.json':
            for e in value['events']:
                capture=e['capture'];e['capture']={k:capture[k] for k in ['raw','sha256','bytes','captured_at']}
                e['capture']['status']='Native location and raw envelope retained locally; visible text unchanged.'
        target=PUBLIC/'archive/contributions/codex'/ARCHIVE.name/name;target.parent.mkdir(parents=True,exist_ok=True);write_json(target,value)
    workfiles=list(WORK.glob('*.py'))+[WORK/'references.json']
    for folder in ['fragments','zh-chapters','en-chapters']:workfiles+=list((WORK/folder).glob('*.md'))
    workfiles += list((WORK/'review').glob('*.json')) + list((WORK/'review').glob('*.py'))
    for path in workfiles:
        target=PUBLIC/'work'/WORK.name/path.relative_to(WORK);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    pointer=json.loads((C/'catalog/current.json').read_bytes())
    for name in ['current.json',pointer['report']]:shutil.copyfile(C/'catalog'/name,PUBLIC/'archive/contributions/codex/catalog'/name)
    for source,target in [('01-new-principles.zh.md','current.md'),('02-new-principles.en.md','current.en.md'),('book-readme.md','readme.md')]:
        shutil.copyfile(OUT/source,PUBLIC/'book'/target)
    editions=json.loads((PUBLIC/'history/editions.json').read_bytes());assert len(editions)==17
    edition={'edition':EDITION,'title':'相对性、认知参考系与多层级对齐',
        'book_title_zh':'新原理：社会科学的数学原理','book_title_en':'Nova Principia: Mathematical Principles of Social Science',
        'file':'archive/dossiers/'+OUT.name+'/01-new-principles.zh.md','sha256':metrics['chinese_sha256'],
        'cjk_characters':metrics['chinese_cjk_characters'],'languages':['zh','en'],
        'translations':{'en':{'file':'archive/dossiers/'+OUT.name+'/02-new-principles.en.md',
            'sha256':metrics['english_sha256'],'whitespace_words':metrics['english_whitespace_words'],
            'derived_from_sha256':metrics['chinese_sha256'],'method':'idiomatic adaptation; unchanged chapters inherited from edition 17'}},
        'landing_page':'book/readme.md','previous_edition':'17-cooperative-superintelligence',
        'revision_manifest':'archive/dossiers/'+OUT.name+'/revision-manifest.json'}
    editions.append(edition);write_json(PUBLIC/'history/editions.json',editions)
    history=PUBLIC/'history/README.md';text=history.read_text(encoding='utf-8');marker='\n更早的[整体框架'
    assert text.count(marker)==1
    text=text.replace(marker,f'|{edition["title"]}|{metrics["chinese_cjk_characters"]:,}|[中文](../{edition["file"]}) · [English](../{edition["translations"]["en"]["file"]})|\n'+marker)
    text+='\n2026年11月5日第十八版采用《新原理：社会科学的数学原理》与 Nova Principia 新标题，增加认知参考系、多层级对齐与相应自我反思；Gemini原始导出、作者新论述及编辑补充分别保存。[修改、来源与局部复核记录](../archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\n'
    history.write_bytes(text.encode())
    readme=PUBLIC/'README.md';text=readme.read_text(encoding='utf-8')
    old='- [本轮和平说服论述、原话与中英对照记录](archive/dossiers/2026-11-02-cooperative-superintelligence/04-editorial-notes.md)'
    assert text.count(old)==1
    text=text.replace(old,'- [本轮相对性与对齐论述、原话与中英对照记录](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)')
    text=text.replace('[《新原理》当前全文]','[《新原理：社会科学的数学原理》当前全文]').replace('[New Principles — complete English edition]','[Nova Principia — complete English edition]')
    text+='\n2026年11月5日第十八版采用新书名《新原理：社会科学的数学原理》（Nova Principia），补入认知参考系、多层级对齐和自我反思。作者原话、Gemini回复、编辑限定与思想演化分别保存，详见[本版修改记录](archive/dossiers/'+OUT.name+'/04-editorial-notes.md)。\n'
    readme.write_bytes(text.encode())
    publication=PUBLIC/'publication/README.md';text=publication.read_text(encoding='utf-8')
    start=text.index('截至第十七版');end=text.index('\n\n',start)
    replacement=f"截至第十八版（2026年11月5日），原档案当前目录含 {coverage['catalog_events']:,} 条来源记录。公开 {coverage['published_events']:,} 条记录，其中会话 {coverage['record_kinds']['conversation']:,} 条、材料 {coverage['record_kinds']['material']:,} 条；另保存 {coverage['editorial_objects']:,} 个理论与编辑对象的公开投影。完整中文、英文及双语简介已纳入版本历史。数量与逐次增补记录见 [coverage.json](coverage.json)。"
    publication.write_bytes((text[:start]+replacement+text[end:]).encode())
    write_json(WORK/'public-preparation.json',{'status':'prepared','update':update,'events':rows,'editions':len(editions)})
    print(json.dumps({'status':'prepared','added_objects':len(added),'published_events':coverage['published_events'],'editions':len(editions)},ensure_ascii=False))

if __name__=='__main__':publish()
