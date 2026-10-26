"""Independent saved-object replay followed by compare-and-swap activation."""
import json, re, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from prepare import ROOT, BASE, WORK, OUT, ARCHIVE, C, write_json, sha
from pkst_codec import cid, cid_bytes, decode, encode, check_sets, links
from query_catalog import search

def verify_activate():
    baseline=json.loads((ARCHIVE/'baseline.json').read_bytes())
    report=json.loads((ARCHIVE/'report.json').read_bytes())
    pointer=json.loads((ARCHIVE/'staged-pointer.json').read_bytes())
    selected=json.loads((ARCHIVE/'selected-sources.json').read_bytes())
    manifest=json.loads((OUT/'passage-manifest.json').read_bytes())
    stats=json.loads((OUT/'editorial-statistics.json').read_bytes())
    textcheck=json.loads((ARCHIVE/'text-verification.json').read_bytes())
    oldcat=json.loads((C/'catalog'/baseline['pointer']['report']).read_bytes())
    cat=json.loads((C/'catalog'/pointer['report']).read_bytes())
    assert json.loads((C/'catalog/current.json').read_bytes())==baseline['pointer']
    db=sqlite3.connect((BASE/pointer['database']).as_uri()+'?mode=ro',uri=True)
    checked=set()
    def get(k):
        row=db.execute('SELECT path,offset,size FROM blocks WHERE cid=?',(k,)).fetchone();assert row,k
        with (BASE/row[0]).open('rb') as f:f.seek(row[1]);b=f.read(row[2])
        assert cid(b,cid_bytes(k)[1])==k;checked.add(k)
        if cid_bytes(k)[1]==0x55:return b
        obj=decode(b);assert encode(obj)==b;check_sets(obj)
        return obj
    for k in report['new_catalog_blocks']:get(k)
    for f in report['files']:
        data=get(f['raw']['$link']);assert data==(BASE/f['path']).read_bytes()
        assert len(data)==f['bytes'] and sha(data)==f['sha256']
    document=get(report['document']);chapterobj=get(report['chapter'])
    assert document['previous']['$link']==baseline['old_document']
    assert chapterobj['document']['$link']==report['document']
    oldobj=get(baseline['old_document']);old=get(oldobj['raw']['$link'])
    assert old==(BASE/baseline['old_manuscript']).read_bytes()
    assert sha(old)==baseline['old_manuscript_sha256']
    chapter=get(chapterobj['raw']['$link']);whole=get(document['raw']['$link'])
    assert chapter==(OUT/'01-chapter.md').read_bytes()
    assert whole==(OUT/'02-new-principles.md').read_bytes()
    assert sha(chapter)==stats['chapter_sha256']==textcheck['chapter_sha256']
    assert sha(whole)==stats['combined_sha256']==textcheck['combined_sha256']
    insertion=json.loads(get(document['insertion']['$link']))
    pos=insertion['insert_at_utf8_byte'];assert old[:pos]+chapter+old[pos:]==whole
    body=chapter.decode();full=whole.decode();assembled='## '+manifest['title']+'\n\n';quote_count=0
    assert [p['$link'] for p in chapterobj['passages']]==report['passages']
    for key,x in zip(report['passages'],manifest['items'],strict=True):
        p=get(key);assert p['text']==x['text'] and p['ordinal']==x['ordinal']
        a,b=p['chapter_span'];u,v=p['document_span']
        assert body[a:b]==full[u:v]==p['text']
        assembled+=p['text']+'\n\n'
        if x.get('ref'):
            quote_count+=1;r=selected[x['ref']];a,b=x['source_span'];q=get(p['quote']['$link'])
            assert q['text']==r['text'][a:b] and q['force']=='quote'
            assert q['holder']['kind']=='unknown'
            assert p['source']['$link']==report['sources'][x['ref']]
        else:assert p['quote'] is None and p['source'] is None
    assert assembled==body and quote_count==len(report['quotes'])==stats['source_blocks']
    for ref,r in selected.items():
        s=get(report['sources'][ref]);assert s['occurrence']['$link']==r['occurrence']
        assert get(r['content'])['text']==r['text']
        assert s['event_time']==get(r['occurrence'])['event_time']==r['native_event_time']
        for a in r['anchors']:assert get(a)['occurrence']['$link']==r['occurrence']
    for k in report['timepoints']:
        t=get(k);s=get(t['source']['$link']);assert t['event_time']==s['event_time']
    for k in report['relations']:
        r=get(k);assert r['to']['$link']==report['concept'] and r['basis']=='inferred'
    req=selected['MATH-REQUEST'];cap=req['capture'];prefix=get(cap['raw'])
    assert sha(prefix)==cap['sha256']
    native=json.loads(prefix[cap['start']:cap['end']])
    assert [x['text'] for x in native['payload']['content'] if x['type']=='input_text']==[req['text']]
    assert native['timestamp']==req['time']
    found=search(db,'我觉得这是一个解释我设想的新架构的绝佳例子',10,'user','codex-local')
    assert req['occurrence'] in [r['occurrence'] for r in found]
    change=get(report['change']);assert change['operation']=='extend'
    assert change['from_versions'][0]['$link']==baseline['old_document']
    assert change['to_versions'][0]['$link']==report['document']
    assert get(report['snapshot'])['parents'][0]['$link']==baseline['old_dossier_root']
    assert get(pointer['snapshot'])['parents'][0]['$link']==baseline['pointer']['snapshot']
    assert cat['pinned_sources'][:-1]==oldcat['pinned_sources']
    assert cat['pinned_sources'][-1]['report_sha256']==sha((ARCHIVE/'report.json').read_bytes())
    count=db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count==oldcat['unique_current_events']+1==report['current_events']
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0]==0
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    db.close()
    result={'schema':'math/archive-verification@1','status':'pass','recorded_at':datetime.now(timezone.utc).isoformat(),
            'snapshot':report['snapshot'],'federated_snapshot':pointer['snapshot'],
            'chapter_sha256':stats['chapter_sha256'],'combined_sha256':stats['combined_sha256'],
            'source_entries_checked':len(selected),'source_passages_replayed':quote_count,
            'all_passage_units':len(report['passages']),'frozen_files_checked':len(report['files']),
            'archive_blocks_checked':len(checked),'current_native_events':count,
            'old_body_byte_preserved':True,'request_retrieval_passed':True,
            'full_reference_graph_nodes_checked_at_staging':report['full_reference_graph_nodes'],
            'review_scope':'Codex saved-object replay using shared codec; no Claude or author acceptance asserted',
            'publication':False}
    write_json(ARCHIVE/'verification.json',result)
    current=C/'catalog/current.json'
    assert json.loads(current.read_bytes())==baseline['pointer'],'Another writer changed catalog'
    temp=C/'catalog/current.math.tmp';assert not temp.exists()
    write_json(temp,pointer);temp.replace(current)
    write_json(ARCHIVE/'status.json',{'status':'activated-after-verification','recorded_at':datetime.now(timezone.utc).isoformat(),'pointer':pointer,'verification':'verification.json','text_verification':'text-verification.json','author_adoption':False,'public_release':False})
    receipt=f'''# 新增数学案例章节归档收据

已将《从数学家的灵感到文明的共同创造》接入个人知识 Merkle-DAG 库和《新原理》全文。

- 新章 {stats['chapter_cjk_characters']:,} 汉字；接入后的全文 {stats['combined_cjk_characters']:,} 汉字。
- 复用10条此前消息，新增本次写作请求1条。当前目录 {count:,} 条来源事件；编辑正文不伪装成用户发言。
- {quote_count} 个来源选取单元、{len(report['passages'])} 个含标题的编辑单元，均核对区间和原话。新章与旧稿的插入可逐字节重建，旧版未覆盖。
- 新案例与既有9个理论主题建立带范围的编辑关系；11个来源保留各自原生时间。关系不表示所有理论已证实或作者已采纳全部改写。
- 新专题引用闭包 {report['closure_blocks']} 个块，{len(report['files'])} 份文稿与附录文件。完整目录引用图 {report['full_reference_graph_nodes']:,} 个节点在暂存时检查闭合且无环；另以保存后的对象复核正文、文件、请求检索和数据库完整性。
- 旧来源沿用此前原生解析收据，本轮重新核对所选CID字节、正文、时间和锚目标；新请求从固定原件前缀重新解析。没有重新宣称全库思想提炼完毕。

本版专题根：`{report['snapshot']}`。

当前统一根：`{pointer['snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

新章 SHA-256：`{stats['chapter_sha256']}`。

全文 SHA-256：`{stats['combined_sha256']}`。

[文字重放核验](../../contributions/codex/mathematics-contribution-20261026/text-verification.json) · [归档核验](../../contributions/codex/mathematics-contribution-20261026/verification.json) · [对象清单](../../contributions/codex/mathematics-contribution-20261026/report.json) · [启用状态](../../contributions/codex/mathematics-contribution-20261026/status.json)

资料仅本地保存，尚无本轮新的Claude审阅或作者逐句采纳。本收据在根生成后写入，不参与自身根的哈希。
'''
    (OUT/'09-archive-receipt.md').write_bytes(receipt.encode())
    readme=BASE/'README.md';text=readme.read_bytes().decode('utf-8')
    text=text.replace('**212,354 个当前来源记录**','**212,355 个当前来源记录**',1)
    anchor='2026 年 10 月 26 日扩充修订稿：'
    assert text.count(anchor)==1
    latest=f'2026 年 10 月 26 日新增数学案例：**[《从数学家的灵感到文明的共同创造》，{stats["chapter_cjk_characters"]:,} 汉字](dossiers/2026-10-26-mathematics-and-contribution/01-chapter.md)**；[接入后的《新原理》全文，{stats["combined_cjk_characters"]:,} 汉字](dossiers/2026-10-26-mathematics-and-contribution/02-new-principles.md)。保留原话、改写对照、来源时间及历史核对；上一版正文保持不动。[归档收据](dossiers/2026-10-26-mathematics-and-contribution/09-archive-receipt.md)。\n\n'
    text=text.replace(anchor,latest+anchor,1)
    a=text.index('当前统一入口为');b=text.index('[ChatGPT 导入时的目录报告]',a)
    text=text[:a]+f'当前统一入口为 [2026-10-26 数学案例增量目录](contributions/codex/catalog/{pointer["report"]})，[启用状态](contributions/codex/mathematics-contribution-20261026/status.json)记录核验后切换。现有 {count:,} 条来源事件；相比[扩充稿目录](contributions/codex/catalog/{baseline["pointer"]["report"]})仅增加本次数学案例写作请求。10条此前发言复用原身份；新章、编辑来源和关系作为单独对象。旧稿、旧目录保留。\n\n'+text[b:]
    readme.write_bytes(text.encode())
    missing=[]
    for path in OUT.glob('*.md'):
        for target in re.findall(r'\]\(([^\s)]+)\)',path.read_bytes().decode()):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
            local=unquote(target.split('#',1)[0])
            if local and not (path.parent/local).exists():missing.append((path.name,target))
    assert not missing,missing
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':verify_activate()
