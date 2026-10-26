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
    prior = json.loads((C / 'mathematics-contribution-20261026/report.json').read_bytes())
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

    request = selected['INTELLIGENCE-REQUEST']
    capture = request['capture']
    prefix = get(capture['raw'])
    assert sha(prefix) == capture['sha256'] and len(prefix) == capture['bytes']
    native = json.loads(prefix[capture['start']:capture['end']])
    assert [x['text'] for x in native['payload']['content'] if x['type'] == 'input_text'] == [request['text']]
    assert native['timestamp'] == request['time']
    found = search(db, '我读了你写的增量部分，很有感触', 10, 'user', 'codex-local')
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

    readme = BASE / 'README.md'
    text = readme.read_bytes().decode()
    assert text.count('**212,355 个当前来源记录**') == 1
    text = text.replace('**212,355 个当前来源记录**', '**212,356 个当前来源记录**', 1)
    anchor = '2026 年 10 月 26 日新增数学案例：'
    assert text.count(anchor) == 1
    latest = f'2026 年 10 月 26 日知识与公共智能融合稿：**[修订章节，{stats["chapter_cjk_characters"]:,} 汉字](dossiers/2026-10-26-public-intelligence/01-chapter.md)**；[《新原理》全文，{stats["combined_cjk_characters"]:,} 汉字](dossiers/2026-10-26-public-intelligence/02-new-principles.md)。新增知识与智能相互生成、从知识共享到智能共享、共同智能的组织机制三节；保留此前数学案例正文，旧稿不覆盖。[原话与改写对照](dossiers/2026-10-26-public-intelligence/03-source-ledger.md) · [归档收据](dossiers/2026-10-26-public-intelligence/09-archive-receipt.md)。\n\n'
    text = text.replace(anchor, latest + anchor, 1)
    a = text.index('当前统一入口为')
    b = text.index('[ChatGPT 导入时的目录报告]', a)
    text = text[:a] + f'当前统一入口为 [2026-10-26 公共智能融合目录](contributions/codex/catalog/{pointer["report"]})，[启用状态](contributions/codex/public-intelligence-20261026/status.json)记录核验后切换。现有 {count:,} 条来源事件；相比[数学案例目录](contributions/codex/catalog/{baseline["pointer"]["report"]})仅增加本次关于知识、智能及公共组织的作者发言。11条此前来源复用原身份；修订正文、引文核对及编辑关系单独保存，旧稿、旧目录保留。\n\n' + text[b:]
    result = {
        'schema': 'pi/archive-verification@1', 'status': 'pass',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'snapshot': report['snapshot'], 'federated_snapshot': pointer['snapshot'],
        'chapter_sha256': stats['chapter_sha256'], 'combined_sha256': stats['combined_sha256'],
        'source_entries_checked': len(selected), 'source_passages_replayed': quote_count,
        'all_passage_units': len(report['passages']), 'prior_passages_preserved': len(retained),
        'only_omitted_prior_headings': omitted, 'frozen_files_checked': len(report['files']),
        'archive_blocks_checked': len(checked), 'current_native_events': count,
        'chapter_replacement_and_inverse_passed': True, 'outside_chapter_byte_preserved': True,
        'request_retrieval_passed': True,
        'full_reference_graph_nodes_checked_at_staging': report['full_reference_graph_nodes'],
        'review_scope': 'Codex saved-object replay using shared codec; no Claude or blanket author acceptance asserted',
        'publication': False,
    }
    write_json(ARCHIVE / 'verification.json', result)
    assert json.loads(current.read_bytes()) == baseline['pointer'], 'Another writer changed catalog'
    temp = C / 'catalog/current.pi.tmp'
    assert not temp.exists()
    write_json(temp, pointer)
    temp.replace(current)
    write_json(ARCHIVE / 'status.json', {
        'status': 'activated-after-verification', 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'pointer': pointer, 'verification': 'verification.json', 'text_verification': 'text-verification.json',
        'author_adoption': False, 'public_release': False,
    })
    receipt = f'''# 知识与公共智能融合稿归档收据

修订章节《从数学家的灵感到文明的共同创造》已接入个人知识 Merkle-DAG 库和《新原理》全文。

- 章节 {stats['chapter_cjk_characters']:,} 汉字；全文 {stats['combined_cjk_characters']:,} 汉字。
- 复用11条此前来源，新增本次作者发言1条。当前目录 {count:,} 条来源事件；编辑正文不冒充用户原话。
- {quote_count} 个来源选取单元、{len(report['passages'])} 个含标题的编辑单元核对区间和原话。保留此前 {len(retained)} 个正文及标题单元的原字；只替换7个旧节标题。篇章替换与逆向重建均逐字节通过，其他章节保持原字节，旧稿保留。
- 12个来源保留原生时间，9条既有主题关系和1条对数学案例的解释关系分别保存。作者的肯定反馈已留存，但不自动扩展为对本版全部文字的采纳。
- 杰斐逊书信、自由软件说明、引语归属及AI部署成本按各自范围核对；可取得的公开HTML保存原字节，失败的页面取证如实保留状态。
- 专题闭包 {report['closure_blocks']} 个块，{len(report['files'])} 份文稿与附录。暂存时核对完整引用图 {report['full_reference_graph_nodes']:,} 个节点闭合且无环；本次另从保存对象重放正文、文件、版本关系、请求检索和数据库完整性。
- 旧来源沿用此前解析收据，本次核对所选CID字节、正文、时间与锚目标；新请求从固定原件前缀重新解析。这不是全库语义提炼完成或新机制效果验证。

专题根：`{report['snapshot']}`。

当前统一根：`{pointer['snapshot']}`。

父统一根：`{baseline['pointer']['snapshot']}`。

章节 SHA-256：`{stats['chapter_sha256']}`。

全文 SHA-256：`{stats['combined_sha256']}`。

[文字核验](../../contributions/codex/public-intelligence-20261026/text-verification.json) · [归档核验](../../contributions/codex/public-intelligence-20261026/verification.json) · [对象清单](../../contributions/codex/public-intelligence-20261026/report.json) · [启用状态](../../contributions/codex/public-intelligence-20261026/status.json)

仅本地保存。本轮没有新的Claude审阅；本收据在根生成后写入，不参与自身根的哈希。
'''
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
