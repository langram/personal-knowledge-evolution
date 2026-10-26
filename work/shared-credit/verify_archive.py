"""Replay saved objects and chapter replacement before activating this edition."""
import json
import re
import sqlite3
from datetime import datetime, timezone
from urllib.parse import unquote
from prepare import BASE, WORK, OUT, ARCHIVE, C, write_json, sha
from pkst_codec import cid, cid_bytes, decode, encode, check_sets
from query_catalog import search


def verify_activate():
    baseline = json.loads((ARCHIVE / 'baseline.json').read_bytes())
    report = json.loads((ARCHIVE / 'report.json').read_bytes())
    pointer = json.loads((ARCHIVE / 'staged-pointer.json').read_bytes())
    selected = json.loads((ARCHIVE / 'selected-sources.json').read_bytes())
    manifest = json.loads((OUT / 'passage-manifest.json').read_bytes())
    stats = json.loads((OUT / 'editorial-statistics.json').read_bytes())
    textcheck = json.loads((ARCHIVE / 'text-verification.json').read_bytes())
    prior = json.loads((C / 'public-intelligence-20261026/report.json').read_bytes())
    oldcat = json.loads((C / 'catalog' / baseline['pointer']['report']).read_bytes())
    cat = json.loads((C / 'catalog' / pointer['report']).read_bytes())
    current = C / 'catalog/current.json'
    assert json.loads(current.read_bytes()) == baseline['pointer']
    db = sqlite3.connect((BASE / pointer['database']).as_uri() + '?mode=ro', uri=True)
    checked = set()

    def get(key):
        row = db.execute('SELECT path,offset,size FROM blocks WHERE cid=?', (key,)).fetchone()
        assert row, key
        with (BASE / row[0]).open('rb') as stream:
            stream.seek(row[1])
            data = stream.read(row[2])
        assert cid(data, cid_bytes(key)[1]) == key
        checked.add(key)
        if cid_bytes(key)[1] == 0x55:
            return data
        obj = decode(data)
        assert encode(obj) == data
        check_sets(obj)
        return obj

    for key in report['new_catalog_blocks']:
        get(key)
    for item in report['files']:
        data = get(item['raw']['$link'])
        assert data == (BASE / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256']

    document = get(report['document'])
    chapterobj = get(report['chapter'])
    assert document['previous']['$link'] == baseline['old_document']
    assert chapterobj['previous']['$link'] == baseline['old_chapter']
    assert chapterobj['document']['$link'] == report['document']
    old = get(get(baseline['old_document'])['raw']['$link'])
    oldchapter = get(get(baseline['old_chapter'])['raw']['$link'])
    assert old == (BASE / baseline['old_manuscript']).read_bytes()
    assert oldchapter == (BASE / baseline['old_chapter_file']).read_bytes()
    assert sha(old) == baseline['old_manuscript_sha256']
    assert sha(oldchapter) == baseline['old_chapter_sha256']
    chapter = get(chapterobj['raw']['$link'])
    whole = get(document['raw']['$link'])
    assert chapter == (OUT / '01-chapter.md').read_bytes()
    assert whole == (OUT / '02-new-principles.md').read_bytes()
    assert sha(chapter) == stats['chapter_sha256'] == textcheck['chapter_sha256']
    assert sha(whole) == stats['combined_sha256'] == textcheck['combined_sha256']
    replacement = json.loads(get(document['replacement']['$link']))
    pos = replacement['replace_at_utf8_byte']
    assert replacement['removed_bytes'] == len(oldchapter)
    assert replacement['inserted_bytes'] == len(chapter)
    assert old[pos:pos + len(oldchapter)] == oldchapter
    assert old[:pos] + chapter + old[pos + len(oldchapter):] == whole
    assert whole[:pos] + oldchapter + whole[pos + len(chapter):] == old

    body, full = chapter.decode(), whole.decode()
    assembled = '## ' + manifest['title'] + '\n\n'
    quote_count = 0
    retained = []
    assert [p['$link'] for p in chapterobj['passages']] == report['passages']
    for key, item in zip(report['passages'], manifest['items'], strict=True):
        passage = get(key)
        assert passage['text'] == item['text'] and passage['ordinal'] == item['ordinal']
        a, b = passage['chapter_span']
        u, v = passage['document_span']
        assert body[a:b] == full[u:v] == passage['text']
        assembled += passage['text'] + '\n\n'
        if item.get('ref'):
            quote_count += 1
            source = selected[item['ref']]
            a, b = item['source_span']
            quote = get(passage['quote']['$link'])
            assert quote['text'] == source['text'][a:b] and quote['force'] == 'quote'
            assert quote['holder']['kind'] == 'unknown'
            assert passage['source']['$link'] == report['sources'][item['ref']]
        else:
            assert passage['quote'] is None and passage['source'] is None
        origin = item.get('previous_passage')
        if origin:
            assert passage['previous_passage']['$link'] == origin['cid']
            previous = get(origin['cid'])
            assert previous['text'] == passage['text']
            assert prior['passages'][previous['ordinal']] == origin['cid']
            retained.append(previous['ordinal'])
        else:
            assert passage['previous_passage'] is None
    assert assembled == body
    assert quote_count == len(report['quotes']) == stats['source_blocks']
    reorganization = json.loads((OUT / 'reorganization.json').read_bytes())
    assert retained == reorganization['retained_previous_ordinals_in_reading_order']
    assert len(retained) == len(set(retained)) == stats['retained_previous_passages']
    omitted = sorted(set(range(len(prior['passages']))) - set(retained))
    assert omitted == reorganization['omitted_previous_ordinals']
    assert all(get(prior['passages'][i])['text'].startswith('### ') for i in omitted)

    for ref, source in selected.items():
        saved = get(report['sources'][ref])
        assert saved['occurrence']['$link'] == source['occurrence']
        assert get(source['content'])['text'] == source['text']
        assert saved['event_time'] == get(source['occurrence'])['event_time'] == source['native_event_time']
        for anchor in source['anchors']:
            assert get(anchor)['occurrence']['$link'] == source['occurrence']
    for key in report['timepoints']:
        point = get(key)
        assert point['event_time'] == get(point['source']['$link'])['event_time']
    for key in report['relations'][:-1]:
        relation = get(key)
        assert relation['to']['$link'] == report['concept'] and relation['basis'] == 'inferred'
    context = get(report['relations'][-1])
    assert context['from']['$link'] == report['concept']
    assert context['to']['$link'] == baseline['old_concept']
    assert context['predicate'] == 'explains' and context['basis'] == 'inferred'
    assert report['web_evidence'][:len(prior['web_evidence'])] == prior['web_evidence']
    for key in report['web_evidence'][len(prior['web_evidence']):]:
        evidence = get(key)
        if evidence['capture']['status'] == 'captured':
            html = get(evidence['html_raw']['$link'])
            assert sha(html) == evidence['capture']['sha256']
            assert html == (WORK / 'web' / evidence['capture']['file']).read_bytes()
        else:
            assert 'html_raw' not in evidence

    request = selected['CREDIT-REQUEST']
    capture = request['capture']
    prefix = get(capture['raw'])
    assert sha(prefix) == capture['sha256'] and len(prefix) == capture['bytes']
    native = json.loads(prefix[capture['start']:capture['end']])
    assert [x['text'] for x in native['payload']['content'] if x['type'] == 'input_text'] == [request['text']]
    assert native['timestamp'] == request['time']
    found = search(db, '关于文章中的第十点，从学生的灵感，到基层的创造', 10, 'user', 'codex-local')
    assert request['occurrence'] in [r['occurrence'] for r in found]
    change = get(report['change'])
    assert change['operation'] == 'extend'
    assert change['from_versions'][0]['$link'] == baseline['old_document']
    assert change['to_versions'][0]['$link'] == report['document']
    assert get(report['snapshot'])['parents'][0]['$link'] == baseline['old_dossier_root']
    assert get(pointer['snapshot'])['parents'][0]['$link'] == baseline['pointer']['snapshot']
    assert cat['pinned_sources'][:-1] == oldcat['pinned_sources']
    assert cat['pinned_sources'][-1]['report_sha256'] == sha((ARCHIVE / 'report.json').read_bytes())
    count = db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count == oldcat['unique_current_events'] + 1 == report['current_events']
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0] == 0
    assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    db.close()


    assert omitted == [] and retained == list(range(len(prior['passages'])))
    oldtext = oldchapter.decode()
    a, b = oldtext.index('### 十、'), oldtext.index('### 十一、')
    u, v = body.index('### 十、'), body.index('### 十一、')
    assert oldtext[:a] == body[:u] and oldtext[b:] == body[v:]
    assert body[u:v].encode() == (OUT / '05-section-ten.md').read_bytes()
    metrics = json.loads((ARCHIVE / 'section-metrics.json').read_bytes())
    readme = BASE / 'README.md'
    text = readme.read_bytes().decode()
    assert text.count('**212,356 个当前来源记录**') == 1
    text = text.replace('**212,356 个当前来源记录**', '**212,357 个当前来源记录**', 1)
    anchor = '2026 年 10 月 26 日知识与公共智能融合稿：'
    assert text.count(anchor) == 1
    latest = f'2026 年 10 月 26 日第十节扩展稿：**[《从学生的灵感，到基层的创造》，{metrics["section_ten_cjk"]:,} 汉字](dossiers/2026-10-26-shared-credit/05-section-ten.md)**；[完整案例章节](dossiers/2026-10-26-shared-credit/01-chapter.md)；[《新原理》全文，{stats["combined_cjk_characters"]:,} 汉字](dossiers/2026-10-26-shared-credit/02-new-principles.md)。补充贡献记录的技术条件、荣誉分配史、及时分享的反馈与提出和执行的区别。原话和全部旧段落保留。[归档收据](dossiers/2026-10-26-shared-credit/09-archive-receipt.md)。\n\n'
    text = text.replace(anchor, latest.replace('\n','\n') + anchor, 1)
    a = text.index('当前统一入口为')
    b = text.index('[ChatGPT 导入时的目录报告]', a)
    paragraph = f'当前统一入口为 [2026-10-26 共同贡献增量目录](contributions/codex/catalog/{pointer["report"]})，[启用状态](contributions/codex/shared-credit-20261026/status.json)记录核验后切换。现有 {count:,} 条来源事件；相比[公共智能目录](contributions/codex/catalog/{baseline["pointer"]["report"]})仅增加本次对第十节的作者补充。12条此前来源复用原身份；编辑正文、历史核对及关系分别保存。\n\n'
    text = text[:a] + paragraph.replace('\n','\n') + text[b:]
    result = {
        'schema':'sc/archive-verification@1', 'status':'pass',
        'recorded_at':datetime.now(timezone.utc).isoformat(),
        'snapshot':report['snapshot'], 'federated_snapshot':pointer['snapshot'],
        'chapter_sha256':stats['chapter_sha256'], 'combined_sha256':stats['combined_sha256'],
        'source_entries_checked':len(selected), 'source_units_replayed':quote_count,
        'all_passage_units':len(report['passages']), 'all_prior_passages_preserved':len(retained),
        'outside_section_ten_byte_preserved':True, 'standalone_section_replayed':True,
        'frozen_files_checked':len(report['files']), 'archive_blocks_checked':len(checked),
        'current_native_events':count, 'chapter_replacement_and_inverse_passed':True,
        'request_retrieval_passed':True,
        'full_reference_graph_nodes_checked_at_staging':report['full_reference_graph_nodes'],
        'review_scope':'Codex replay of saved objects; no Claude review, publication, or blanket author acceptance',
    }
    write_json(ARCHIVE / 'verification.json', result)
    assert json.loads(current.read_bytes()) == baseline['pointer'], 'Another writer changed catalog'
    temp = C / 'catalog/current.sc.tmp'
    assert not temp.exists()
    write_json(temp, pointer)
    temp.replace(current)
    write_json(ARCHIVE / 'status.json', {
        'status':'activated-after-verification','recorded_at':datetime.now(timezone.utc).isoformat(),
        'pointer':pointer,'verification':'verification.json','text_verification':'text-verification.json',
        'author_adoption':False,'public_release':False,
    })
    receipt = f"""# 第十节共同贡献扩展稿归档收据

第十节 {metrics['section_ten_cjk']:,} 汉字，案例章节 {stats['chapter_cjk_characters']:,} 汉字，《新原理》全文 {stats['combined_cjk_characters']:,} 汉字。

新增本次作者发言1条，复用12个来源；原文、原生时间与取证坐标保持。当前目录共 {count:,} 条来源事件。

42个来源选取单元和90个编辑单元通过重放；前版79个段落单元全部保留，新增只在第十节，其他小节与全书其他章节按原字节保留。单独阅读版与全文中的第十节一致，整章替换和逆向恢复均通过。

历史依据、作者原话、编辑修订分别保存。佩雷尔曼的两次拒奖区分；分享加速与降低错误执行概率保留为有条件的机制设想，不记作实证成功或作者采纳所有改写。

专题闭包 {report['closure_blocks']} 个对象，{len(report['files'])} 份正文及附录文件；暂存时对完整引用图 {report['full_reference_graph_nodes']:,} 个节点检查闭合与无环。另从保存对象重放文件、来源、时间、检索与数据库完整性。旧来源解析沿用此前收据；没有宣称重新提炼全部语料。

专题根：`{report['snapshot']}`。

统一根：`{pointer['snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

章节 SHA-256：`{stats['chapter_sha256']}`。

全文 SHA-256：`{stats['combined_sha256']}`。

[文字核验](../../contributions/codex/shared-credit-20261026/text-verification.json) · [归档核验](../../contributions/codex/shared-credit-20261026/verification.json) · [对象清单](../../contributions/codex/shared-credit-20261026/report.json) · [启用状态](../../contributions/codex/shared-credit-20261026/status.json)

仅本地保存。旧稿与旧目录保留，本轮没有新的Claude审阅。本收据在根生成后写入，不参与自身根的哈希。
"""
    (OUT / '09-archive-receipt.md').write_bytes(receipt.encode())
    readme.write_bytes(text.encode())
    missing = []
    for path in OUT.glob('*.md'):
        for target in re.findall(r'\]\(([^\s)]+)\)', path.read_bytes().decode()):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            local = unquote(target.split('#', 1)[0])
            if local and not (path.parent / local).exists():
                missing.append((path.name, target))
    assert not missing, missing
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    verify_activate()
