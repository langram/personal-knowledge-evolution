"""Append a verified edition and one source event to an immutable catalog copy."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from prepare import ARCHIVE, BASE, C, OLD, OUT, WORK, raw, sha, write_json
from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset

RUN = '20261029-cooperation-feedback-v1'
COLLECTION = 'cooperation-feedback-20261029'
ACTOR = {'kind': 'ai', 'id': 'codex'}
PROTOCOL = 'bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
NS = {'cf': 'urn:pkst:editorial:cooperation-feedback:1'}

def verify_text():
    baseline = json.loads((ARCHIVE / 'baseline.json').read_bytes())
    request = json.loads((ARCHIVE / 'request-capture.json').read_bytes())
    manifest = json.loads((OUT / 'passage-manifest.json').read_bytes())
    insertion = json.loads((OUT / 'insertion-manifest.json').read_bytes())
    original = (OUT / '00-author-original.txt').read_bytes()
    assert original == request['text'].encode() and sha(original) == request['text_sha256']
    capture = request['capture']
    line = (ARCHIVE / 'raw' / (capture['raw'] + '.bin')).read_bytes()
    assert sha(line) == capture['sha256'] and cid(line, 0x55) == capture['raw']
    envelope = json.loads(line)
    assert envelope['payload']['role'] == 'user'
    assert envelope['timestamp'] == request['time']
    assert any(b.get('text') == request['text'] for b in envelope['payload']['content'])
    with open(capture['native_file'], 'rb') as stream:
        stream.seek(capture['native_start'])
        assert stream.read(capture['bytes']) == line
    old = OLD.read_bytes()
    chapter = (OUT / '01-chapter.md').read_bytes()
    whole = (OUT / '02-new-principles.md').read_bytes()
    at = insertion['insert_at_utf8_byte']
    assert sha(old) == baseline['sha256'] == insertion['baseline_sha256']
    assert sha(chapter) == insertion['chapter_sha256']
    assert sha(whole) == insertion['combined_sha256']
    assert old[:at] + chapter + old[at:] == whole
    assert whole[:at] + whole[at+len(chapter):] == old
    replay = '## ' + manifest['title'] + '\n\n'
    spans = []
    for item in manifest['items']:
        assert chapter.decode()[slice(*item['chapter_span'])] == item['text']
        assert whole.decode()[slice(*item['document_span'])] == item['text']
        if 'ref' in item:
            a, b = item['source_span']
            selected = request['text'][a:b]
            assert sha(selected.encode()) == item['source_sha256']
            edited = selected
            for edit in reversed(item['edits']):
                x, y = edit['source_span']
                assert selected[x-a:y-a] == edit['before']
                edited = edited[:x-a] + edit['after'] + edited[y-a:]
            assert edited == item['text']
            spans.append((a, b))
        replay += item['text'] + '\n\n'
    assert replay.encode() == chapter
    spans.sort()
    assert all(b <= c for (a, b), (c, d) in zip(spans, spans[1:]))
    result = {'status': 'pass', 'source_time': request['time'], 'source_characters': len(request['text']),
        'source_spans_replayed': len(spans), 'passages_replayed': len(manifest['items']),
        'chapter_sha256': sha(chapter), 'combined_sha256': sha(whole),
        'original_message_bytes_verified': True, 'outside_chapter_byte_preserved': True,
        'insertion_and_inverse_replayed': True,
        'scope': 'Identity and edit provenance checks, not evidence of institutional safety or fairness.'}
    write_json(ARCHIVE / 'text-verification.json', result)
    return result

def archive():
    if (ARCHIVE / 'report.json').exists():
        raise RuntimeError('A report already exists. Reconcile the saved catalog before retrying.')
    checks = verify_text()
    baseline = json.loads((ARCHIVE / 'baseline.json').read_bytes())
    pointer = baseline['pointer']
    assert json.loads((C / 'catalog/current.json').read_bytes()) == pointer
    previous = json.loads((C / 'catalog' / pointer['report']).read_bytes())
    request = json.loads((ARCHIVE / 'request-capture.json').read_bytes())
    manifest = json.loads((OUT / 'passage-manifest.json').read_bytes())
    now = datetime.now(timezone.utc).isoformat()
    store = Store(ARCHIVE)
    original_db = sqlite3.connect((BASE / pointer['database']).as_uri() + '?mode=ro', uri=True)
    verified_previous = set()

    def previous_object(key):
        schema, path, offset, size = original_db.execute('SELECT schema,path,offset,size FROM blocks WHERE cid=?', (key,)).fetchone()
        with (BASE / path).open('rb') as stream:
            stream.seek(offset)
            data = stream.read(size)
        assert cid(data, cid_bytes(key)[1]) == key
        verified_previous.add(key)
        return None if schema == 'raw' else decode(data)

    previous_object(baseline['document'])
    files = []
    for path in sorted(OUT.iterdir()):
        if not path.is_file() or path.name.startswith('09-'):
            continue
        data = path.read_bytes()
        files.append({'path': str(path.relative_to(BASE)), 'name': path.name,
            'raw': link(raw(data)), 'bytes': len(data), 'sha256': sha(data)})
    file_keys = {x['name']: x['raw'] for x in files}
    document = store.put({'schema': 'cf/document@1', 'namespaces': NS,
        'title': '新原理：现代科学与人类文明的构造', 'raw': file_keys['02-new-principles.md'],
        'previous': link(baseline['document']), 'insertion': file_keys['insertion-manifest.json'],
        'edition': '2026-10-29 cooperation and feedback', 'authorship': 'source-led editorial proposal; adoption of individual edits not asserted'})
    source = store.put({'schema': 'cf/source@1', 'namespaces': NS, 'ref': request['ref'],
        'occurrence': link(request['occurrence']), 'content': link(request['content']),
        'evidence': linkset(request['anchors']), 'event_time': request['native_event_time'],
        'boundary': 'native message time; not first invention date'})
    quotes = []
    passages = []
    for item in manifest['items']:
        quote = None
        if 'ref' in item:
            quote = store.put({'schema': 'pkst/statement@0.1', 'namespaces': NS,
                'text': request['text'][slice(*item['source_span'])], 'force': 'quote',
                'holder': {'kind': 'human', 'id': 'archive-owner'}, 'evidence': linkset([source]),
                'asserted_by': ACTOR, 'lineage': None,
                'cf:source_span': {'coordinate': 'unicode-scalar-half-open', 'range': item['source_span']}})
            quotes.append(quote)
        passages.append(store.put({'schema': 'cf/passage@1', 'namespaces': NS, 'document': link(document),
            **{key: value for key, value in item.items() if key != 'ref'},
            'source': link(source) if quote else None, 'quote': link(quote) if quote else None}))
    chapter = store.put({'schema': 'cf/chapter@1', 'namespaces': NS, 'title': manifest['title'],
        'document': link(document), 'raw': file_keys['01-chapter.md'], 'passages': [link(x) for x in passages],
        'placement': 'after protection and trust, before personal cloud storage', 'author_acceptance': False})
    definitions = [
        ('信息隐瞒与互惠对抗循环', '信息、猜疑、防守和报复可能互相强化；这是机制解释，不是所有冲突的唯一成因。'),
        ('合作起点与可纠错的互惠', '主动合作结合查证、有边界的防护和恢复合作通路，区别于机械复制对方行为。'),
        ('共享依据与实际保护相互支撑', '公开可核查的相关依据，保护私人信息，并把决策影响与执行权限分开。'),
        ('及时救助补偿与基于证据的责任判断', '止损与救助不必等待全部归责结束；事故、过失和故意行为仍应依据证据区分。'),
        ('长期合作中的预期成本与停止条件', '事先说明风险、成本承担、授权和停止条件，失败不自动免除责任。'),
        ('因果理解与合作认知的相互塑造', '理解行为形成过程可减少固定敌我标签，同时保留对伤害的制止和追责。')]
    concepts = [store.put({'schema': 'pkst/concept@0.1', 'label': label, 'definition': definition,
        'evidence': linkset([source, chapter]), 'asserted_by': ACTOR, 'lineage': None}) for label, definition in definitions]
    relations = []
    older = json.loads((C / 'new-principles-20261026/report.json').read_bytes())['concepts']
    related_labels = ('动态权重', '隐私', '资源', '数据主权', '合作', '公共知识')
    related = []
    for name, key in older.items():
        value = previous_object(key)
        if any(word in value.get('label', '') for word in related_labels):
            related.append((name, key, value['label']))
            relations.append(store.put({'schema': 'pkst/relation@0.1', 'predicate': 'applies-to',
                'from': link(key), 'to': link(concepts[1]), 'evidence': linkset([source, chapter]),
                'asserted_by': ACTOR, 'basis': 'inferred',
                'scope': '本章把' + value['label'] + '用于展开互惠、保护与修复机制；编辑解释，未验证现实制度效果。'}))
    for a, b, scope in [(0, 1, '对抗反馈提出合作起点与纠错的必要性'),
                        (1, 2, '正向互惠需要共享依据与实际保护'),
                        (2, 3, '保护失效时需要止损补偿和查证'),
                        (3, 4, '预先安排风险与成本使修复可以落实'),
                        (4, 5, '可核查的合作经历支持理性与情绪变化'),
                        (5, baseline['concept'], '把人的合作认知连接到可核验的文明协作底座')]:
        relations.append(store.put({'schema': 'pkst/relation@0.1', 'predicate': 'explains',
            'from': link(concepts[a]), 'to': link(concepts[b] if isinstance(b, int) else b),
            'evidence': linkset([source, chapter]), 'asserted_by': ACTOR, 'basis': 'inferred',
            'scope': scope + '；有条件的机制设想，不是经验因果确认。'}))
    prior_trust = json.loads((C / 'protection-and-trust-20261027/report.json').read_bytes())
    for old, new_index in [(prior_trust['concepts'][0], 0), (prior_trust['concepts'][1], 2), (prior_trust['concepts'][3], 1)]:
        value = previous_object(old)
        related.append(('protection-and-trust', old, value['label']))
        relations.append(store.put({'schema': 'pkst/relation@0.1', 'predicate': 'applies-to',
            'from': link(old), 'to': link(concepts[new_index]), 'evidence': linkset([source, chapter]),
            'asserted_by': ACTOR, 'basis': 'inferred', 'scope': '在既有保护与信任论述上进一步展开合作反馈；编辑关系。'}))
    web = json.loads((OUT / 'external-sources.json').read_bytes())
    evidence = [store.put({'schema': 'cf/external-source@1', 'namespaces': NS, **item,
        'accessed_at': now, 'method': 'read via web tool', 'full_page_copy': False}) for item in web]
    change = store.put({'schema': 'pkst/change@0.1', 'operation': 'extend',
        'from_versions': linkset([baseline['document']]), 'to_versions': linkset([document]),
        'evidence': linkset([source]), 'asserted_by': ACTOR, 'basis': 'explicit',
        'reason': 'Author requested the common knowledge and cooperative feedback argument be integrated; previous manuscript preserved byte-for-byte.'})
    inputs = [raw((ARCHIVE / name).read_bytes()) for name in ['baseline.json', 'request-capture.json', 'text-verification.json']]
    implementation = [{'path': str(path.relative_to(WORK)), 'raw': link(raw(path.read_bytes()))}
                      for path in sorted(WORK.glob('*.py'))]
    activity = store.put({'schema': 'pkst/activity@0.1', 'namespaces': NS, 'operation': 'integrate',
        'recorded_at': now, 'actor': ACTOR, 'inputs': linkset(inputs),
        'outputs': linkset([document, chapter, source, change] + concepts + relations + evidence + [f['raw']['$link'] for f in files]),
        'implementation': link(raw(__import__('pathlib').Path(__file__).read_bytes())),
        'coverage': {'scope': 'one author message and one new chapter', 'files': files, 'implementation_files': implementation,
            'pending': ['author review of editorial changes'], 'not_asserted': ['institutional effectiveness', 'zero risk', 'universal agreement']}})
    dossier = store.put({'schema': 'pkst/snapshot@0.1', 'parents': linkset([baseline['dossier_root']]),
        'roots': linkset([activity]), 'coverage': {'recorded_cutoff': now, 'scope': 'cooperation feedback editorial extension'}, 'protocol': link(PROTOCOL)})
    pinned = previous['pinned_sources'] + [{'collection': COLLECTION, 'root': dossier,
        'report': str((ARCHIVE / 'report.json').relative_to(BASE))}]
    integration = store.put({'schema': 'pkst/activity@0.1', 'operation': 'integrate', 'recorded_at': now,
        'actor': ACTOR, 'inputs': linkset([x['root'] for x in pinned]), 'outputs': [],
        'implementation': link(raw(__import__('pathlib').Path(__file__).read_bytes())),
        'coverage': {'scope': 'append cooperation feedback; retain previous collections'}})
    snapshot = store.put({'schema': 'pkst/snapshot@0.1', 'parents': linkset([pointer['snapshot']]),
        'roots': linkset([integration]), 'coverage': {'recorded_cutoff': now, 'scope': 'federated source and manuscript archive'}, 'protocol': link(PROTOCOL)})

    # Common full re-import is unnecessary. Verify the append graph against the
    # immutable baseline, then construct a new catalog copy and activate it last.
    new = {}
    for path in sorted((ARCHIVE / 'objects').glob('*.cbor')):
        data = path.read_bytes(); key = path.stem
        assert cid(data) == key
        obj = decode(data); assert encode(obj) == data
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?', (key,)).fetchone():
            new[key] = (obj, path, data)
    for path in sorted((ARCHIVE / 'raw').glob('*.bin')):
        data = path.read_bytes(); key = path.stem
        assert cid(data, 0x55) == key
        if not original_db.execute('SELECT 1 FROM blocks WHERE cid=?', (key,)).fetchone():
            new[key] = (None, path, data)
    gray, black = set(), set()
    def visit(key):
        if key in black:
            return
        assert key not in gray, 'new object dependency cycle'
        if key not in new:
            previous_object(key)
            black.add(key)
            return
        gray.add(key)
        obj = new[key][0]
        if obj:
            for target in links(obj):
                visit(target)
        gray.remove(key); black.add(key)
    for key in new:
        visit(key)
    destination = C / 'catalog/.private' / RUN
    destination.mkdir(exist_ok=False)
    db = sqlite3.connect(destination / 'catalog.sqlite')
    original_db.backup(db); original_db.close()
    for key, (obj, path, data) in new.items():
        schema = obj['schema'] if obj else 'raw'
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)', (key, schema, str(path.relative_to(BASE)), 0, len(data)))
        if obj is None:
            continue
        historical = {x['$link'] for x in obj.get('parents', [])} if schema == 'pkst/snapshot@0.1' else set()
        db.executemany('INSERT INTO edges VALUES(?,?,?)', [(key, t, int(t in historical)) for t in set(links(obj))])
        if schema == 'pkst/source@0.1':
            db.execute('INSERT INTO sources VALUES(?,?,?,?)', (key, obj['platform'], obj['namespace'], obj['native_thread_id']))
        elif schema == 'pkst/content@0.1':
            db.execute('INSERT INTO content VALUES(?,?)', (key, obj['text']))
        elif schema == 'pkst/occurrence@0.1':
            t = obj['event_time']
            db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)', (key, obj['source']['$link'], obj['native_id'],
                obj['native_role'], obj['actor_kind'], obj['process_kind'], t['value'], t['format'], json.dumps(t, ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)', [(key, i, p['$link']) for i, p in enumerate(obj['content'])])
        elif schema == 'pkst/extraction-record@0.1':
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)', (obj['occurrence']['$link'], key, obj['raw']['$link'],
                json.dumps({k: obj[k] for k in ['coordinate', 'start', 'end', 'pointer', 'parser']}, ensure_ascii=False)))
    members, pending = set(), [dossier]
    while pending:
        key = pending.pop()
        if key in members:
            continue
        members.add(key)
        pending.extend(t for t, in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0', (key,)))
    db.executemany('INSERT INTO membership VALUES(?,?)', [(COLLECTION, k) for k in members])
    count = db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    assert count == previous['unique_current_events'] + 1
    assert db.execute('SELECT count(*) FROM edges e LEFT JOIN blocks b ON b.cid=e.dst WHERE b.cid IS NULL').fetchone()[0] == 0
    assert db.execute('SELECT c.text FROM current_content c JOIN parts p ON p.content=c.cid WHERE p.occurrence=?', (request['occurrence'],)).fetchone()[0] == request['text']
    counts = dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema', (COLLECTION,)))
    total_blocks = db.execute('SELECT count(*) FROM blocks').fetchone()[0]
    db.commit()
    assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    db.close()
    report = {'schema': 'cf/archive-report@1', 'status': 'verified', 'recorded_at': now,
        'snapshot': dossier, 'federated_snapshot': snapshot, 'baseline_snapshot': pointer['snapshot'],
        'document': document, 'chapter': chapter, 'source': source, 'occurrence': request['occurrence'],
        'quotes': quotes, 'passages': passages, 'concepts': concepts, 'relations': relations, 'change': change,
        'related_prior_concepts': related, 'web_evidence': evidence, 'files': files,
        'new_native_events': 1, 'current_events': count, 'new_objects': sorted(new), 'closure_blocks': len(members),
        'closure_counts': counts, 'verified_previous_link_targets': len(verified_previous),
        'full_catalog_blocks': total_blocks, 'text_verification': checks,
        'verification_scope': 'new blocks, direct baseline link targets, append graph, SQL links, source lookup and complete text replay; previous graph verification inherited'}
    write_json(ARCHIVE / 'report.json', report)
    pinned[-1]['report_sha256'] = sha((ARCHIVE / 'report.json').read_bytes())
    catreport = {**previous, 'run': RUN, 'recorded_at': now, 'snapshot': snapshot, 'baseline_snapshot': pointer['snapshot'],
        'pinned_sources': pinned, 'database': str((destination / 'catalog.sqlite').relative_to(BASE)),
        'unique_current_events': count, 'current_events_with_anchors': count,
        'current_counts_by_collection': {**previous['current_counts_by_collection'], COLLECTION: counts},
        'all_catalog_blocks_including_history_and_federation': total_blocks,
        'freshly_byte_verified_blocks': len(new) + len(verified_previous), 'status': 'verified',
        'verification_scope': report['verification_scope'], 'baseline_verification_report': pointer['report']}
    write_json(C / 'catalog' / ('report-' + RUN + '.json'), catreport)
    assert json.loads((C / 'catalog/current.json').read_bytes()) == pointer
    next_pointer = {'report': 'report-' + RUN + '.json', 'snapshot': snapshot, 'database': catreport['database']}
    temp = C / 'catalog/current.cooperation-feedback.tmp'
    write_json(temp, next_pointer)
    temp.replace(C / 'catalog/current.json')
    write_json(ARCHIVE / 'status.json', {'status': 'active', 'snapshot': snapshot, 'verified_at': datetime.now(timezone.utc).isoformat()})
    print(json.dumps({k: report[k] for k in ['status', 'snapshot', 'federated_snapshot', 'current_events', 'closure_blocks', 'verified_previous_link_targets']}, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    archive()
