"""Incrementally prepare the authorized public edition; never copy raw backups."""
import collections
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from prepare import ARCHIVE, BASE, C, OUT, PUBLIC, WORK, ROOT, sha, write_json
from pkst_codec import Store, cid, encode

sys.path.insert(0, str(ROOT / 'work/publishing'))
from safety import tree, sanitize

def prepare_public():
    report = json.loads((ARCHIVE / 'report.json').read_bytes())
    baseline = json.loads((ARCHIVE / 'baseline.json').read_bytes())
    request = json.loads((ARCHIVE / 'request-capture.json').read_bytes())
    metrics = json.loads((OUT / 'editorial-statistics.json').read_bytes())
    coverage = json.loads((PUBLIC / 'publication/coverage.json').read_bytes())
    assert coverage['source_snapshot'] == baseline['pointer']['snapshot']
    assert sha((PUBLIC / 'book/current.md').read_bytes()) == baseline['sha256']
    db = sqlite3.connect((PUBLIC / '.cache/catalog.sqlite').as_uri() + '?mode=ro', uri=True)
    store = Store(ARCHIVE)
    added = {}

    def put(obj):
        clean, findings = tree(obj)
        assert not findings and clean == obj, 'new material requires explicit redaction review'
        key = cid(encode(obj))
        old = db.execute('SELECT body FROM objects WHERE cid=?', (key,)).fetchone()
        if old:
            assert json.loads(old[0]) == obj
        else:
            added[key] = obj
        return key

    source = put(store.get(request['source']))
    content = put(store.get(request['content']))
    original = store.get(request['occurrence'])
    public_event = put({'schema': 'pkst-public/event@1', 'record_kind': 'conversation',
        'original_occurrence_cid': request['occurrence'], 'source': {'$link': source},
        'native_id': original['native_id'], 'native_role': 'user', 'actor_kind': original['actor_kind'],
        'process_kind': 'main', 'event_time': request['native_event_time'], 'native_parent_ids': original['native_parent_ids'],
        'content': [{'$link': content}], 'content_provenance': [{'original_content_cid': content, 'public_content_cid': content, 'transformation': None}],
        'raw_evidence_status': 'retained locally; excluded from public release'})
    event_row = {'cid': public_event, 'original_occurrence': request['occurrence'], 'source': source,
        'platform': 'codex-local', 'thread': request['thread'], 'role': 'user', 'actor': original['actor_kind'],
        'process': 'main', 'record_kind': 'conversation', 'time': request['time'], 'time_format': request['time_format'], 'content': [content]}
    assert db.execute('SELECT 1 FROM events WHERE original=?', (request['occurrence'],)).fetchone() is None
    editorial = json.loads((PUBLIC / 'corpus/editorial-index.json').read_bytes())
    previous_editorial = len(editorial)
    for key in report['new_objects']:
        path = ARCHIVE / 'objects' / (key + '.cbor')
        if not path.is_file():
            continue
        obj = store.get(key)
        schema = obj['schema']
        if not schema.startswith('cf/') and schema not in {'pkst/statement@0.1', 'pkst/concept@0.1', 'pkst/relation@0.1', 'pkst/change@0.1'}:
            continue
        public = put({'schema': 'pkst-public/editorial-object@1', 'original_cid': key, 'original_schema': schema,
            'object_projection': obj, 'redactions': [],
            'link_scope': 'original archive identifiers; see original-to-public event map and omitted manifest'})
        editorial.append({'cid': public, 'original_cid': key, 'schema': schema})
    db.close()

    def merge_shards(kind, rows):
        grouped = collections.defaultdict(list)
        for row in rows:
            grouped[sha(row['cid'].encode())[:2]].append(row)
        for shard, extra in grouped.items():
            path = PUBLIC / 'corpus' / kind / (shard + '.jsonl')
            prior = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []
            combined = prior + extra
            assert len({x['cid'] for x in combined}) == len(combined)
            path.write_bytes((''.join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                for row in sorted(combined, key=lambda x: x['cid']))).encode())

    merge_shards('objects', [{'cid': key, 'object': value} for key, value in added.items()])
    merge_shards('events', [event_row])
    write_json(PUBLIC / 'corpus/editorial-index.json', editorial)
    coverage['source_snapshot'] = report['federated_snapshot']
    coverage['catalog_events'] += 1
    coverage['published_events'] += 1
    coverage['record_kinds']['conversation'] += 1
    coverage['events_by_platform']['codex-local'] += 1
    native = json.loads((ARCHIVE / 'raw' / (request['capture']['raw'] + '.bin')).read_bytes())
    channel = str(native['payload'].get('channel'))
    coverage['native_codex_channels'][channel] = coverage['native_codex_channels'].get(channel, 0) + 1
    coverage['public_objects'] += len(added)
    coverage['editorial_objects'] = len(editorial)
    # This export verifies its new input objects; the original full-export
    # verification counter is historical and must not be silently reinterpreted.
    coverage.setdefault('incremental_updates', []).append({'edition': '08-cooperation-feedback',
        'source_snapshot': report['federated_snapshot'], 'native_source_time': request['time'],
        'added_events': 1, 'added_public_objects': len(added), 'added_editorial_objects': len(editorial)-previous_editorial,
        'new_original_blocks_verified': len(report['new_objects']), 'previous_link_targets_verified': report['verified_previous_link_targets'],
        'recorded_at': datetime.now(timezone.utc).isoformat()})
    write_json(PUBLIC / 'publication/coverage.json', coverage)
    receipt = f'''# 公共知识与合作反馈章节归档收据

新增章节 {metrics['chapter_cjk']:,} 汉字，全文 {metrics['combined_cjk']:,} 汉字。

本轮作者原话、原生时间及取证坐标保留；新增 1 条来源事件，统一索引现有 {report['current_events']:,} 条来源事件。{report['text_verification']['source_spans_replayed']} 个来源片段与 {report['text_verification']['passages_replayed']} 个正文单元均通过重放。章节插入及逆向恢复通过，新增章节之外的前版全文按原字节保留。

专题根：`{report['snapshot']}`。

统一根：`{report['federated_snapshot']}`。

父统一根：`{report['baseline_snapshot']}`。

全文 SHA-256：`{metrics['combined_sha256']}`。

核验范围为新对象身份、新增引用图、旧引用目标、索引可查询性和完整文字重放；既有图的全量核验沿用前版结果。没有把归档通过当作制度的现实有效性验证。

公开版本保留原话、章节、全文、逐项编辑对照、语义对象投影及构稿脚本；原始会话取证记录保留本地。发布前通过公开对象重建及文件清单核验后，再执行 Git 推送。实际提交和推送结果以 Git 记录为准。本收据在专题根生成之后写入，不参与自身专题根。
'''
    (OUT / '09-archive-receipt.md').write_bytes(receipt.encode())
    for path in OUT.iterdir():
        if path.is_file():
            target = PUBLIC / 'archive' / path.relative_to(BASE)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    for name in ['baseline.json', 'request-capture.json', 'text-verification.json', 'report.json', 'status.json']:
        value = json.loads((ARCHIVE / name).read_bytes())
        if name == 'request-capture.json':
            value['capture'] = {'raw': request['capture']['raw'], 'sha256': request['capture']['sha256'],
                'bytes': request['capture']['bytes'], 'captured_at': request['capture']['captured_at'],
                'status': 'Native file location and raw record retained locally; public author text is unchanged.'}
        target = PUBLIC / 'archive/contributions/codex' / ARCHIVE.name / name
        target.parent.mkdir(parents=True, exist_ok=True)
        write_json(target, value)
    for path in WORK.glob('*.py'):
        target = PUBLIC / 'work/cooperation-feedback' / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    pointer = json.loads((C / 'catalog/current.json').read_bytes())
    for name in ['current.json', pointer['report']]:
        shutil.copyfile(C / 'catalog' / name, PUBLIC / 'archive/contributions/codex/catalog' / name)
    shutil.copyfile(OUT / '02-new-principles.md', PUBLIC / 'book/current.md')
    editions = json.loads((PUBLIC / 'history/editions.json').read_bytes())
    assert len(editions) == 7
    edition = {'edition': '08-cooperation-feedback', 'title': '公共知识与合作反馈扩展',
        'file': 'archive/dossiers/' + OUT.name + '/02-new-principles.md',
        'sha256': metrics['combined_sha256'], 'cjk_characters': metrics['combined_cjk']}
    editions.append(edition)
    write_json(PUBLIC / 'history/editions.json', editions)
    history = PUBLIC / 'history/README.md'
    text = history.read_text(encoding='utf-8')
    insertion = f'|公共知识与合作反馈扩展|{metrics["combined_cjk"]:,}|[正文](../{edition["file"]})|\n'
    marker = '\n更早的[整体框架'
    assert text.count(marker) == 1
    text = text.replace(marker, insertion + marker)
    text += '\n2026年10月29日新增[公共知识与合作反馈章节](../archive/dossiers/' + OUT.name + '/01-chapter.md)，置于权力约束与信任章节之后、云存储实践之前。[原话与编辑对照](../archive/dossiers/' + OUT.name + '/03-source-ledger.md)保存本次逐项修改。此次为公开仓库建立后的实际追加修订。\n'
    history.write_bytes(text.encode())
    readme = PUBLIC / 'README.md'
    text = readme.read_text(encoding='utf-8')
    marker = '- [《新原理》当前全文](book/current.md)\n'
    assert text.count(marker) == 1
    text = text.replace(marker, marker + '- [公共知识、互惠与合作的正向循环](archive/dossiers/' + OUT.name + '/01-chapter.md)\n')
    text = text.replace('- [本轮原话与逐项改写对照](archive/dossiers/2026-10-29-merkle-native/03-source-ledger.md)',
        '- [本轮原话与逐项改写对照](archive/dossiers/' + OUT.name + '/03-source-ledger.md)')
    text = text.replace('[本轮原话、编辑与演化记录](archive/dossiers/2026-10-29-merkle-native/04-evolution-and-placement.md)',
        '[Merkle-DAG章节的原话与演化记录](archive/dossiers/2026-10-29-merkle-native/04-evolution-and-placement.md)')
    text = text.replace('最近增量（2026年10月29日）', '会话批量增量（2026年10月29日）')
    text += '\n随后追加作者关于公共知识、互惠与合作反馈的一条原话，形成第八版全文；[编辑说明与事实核查](archive/dossiers/' + OUT.name + '/04-editorial-notes.md)记录本次整理的依据与边界。\n'
    readme.write_bytes(text.encode())
    print(json.dumps({'prepared': True, 'added_public_objects': len(added), 'public_event': public_event,
        'published_events': coverage['published_events'], 'editions': len(editions), 'chapter_cjk': metrics['chapter_cjk']}, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    prepare_public()
