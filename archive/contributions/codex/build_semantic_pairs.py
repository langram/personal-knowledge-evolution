"""Bounded exact-quote interpretation of the ten current cross-source pairs.

Construction choice: reuse immutable events and anchors; no re-import, embeddings,
bulk paraphrase, or automatic causal/version inference. Human-readable projection
is rebuilt from the same pinned evidence. This is a review candidate.
"""
import hashlib
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pkst_codec import Store, cid, cid_bytes, decode, encode, link, links, linkset

BASE = Path(__file__).resolve().parents[2]
CODEX = BASE / 'contributions/codex'
OUT = CODEX / 'semantic-pairs'
CATALOG = '20261024T083500Z'
ACTOR = {'kind': 'ai', 'id': 'codex'}
PROTOCOL = 'bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq'
PREVIOUS = 'bafyreiezaag64fuifl2benocqseegkao3ktbiwvtc4kvekase6bblrvx4u'
SELECTIONS = [
 ('bafyreiabopz32ax6rqgb4wqoz2rlld3xinjnmq5k4zaqoajpquqotw2kba', '不动点、最小化与 AI 模型框架', 'question', '如何将这个世界模型，还有语言大模型，以我的理论框架来重新给出定义，并描述两者之间的关系？'),
 ('bafyreibc7xeawy4nsfbucqn5ewbimekjk6h3wemkpvlux47na3qfhbvulm', 'Merkle-DAG 白盒对象引擎', 'directive', '请你对目前项目的成果进行评价'),
 ('bafyreidbefhysb5zwa4a5kulitcxq4mtkn3ddn6qcqwyb7vzqbjrx6uzme', 'AI 资源成本与用途（个人实务请求）', 'question', '有哪些相对稳定且收益率较高，至少获得的收益要大于烧掉的token成本，最好不要那种AI视频，AI小说一类，需要爆点几率较低的任务'),
 ('bafyreidl2kqrphe7myadmsefeggvp7pjcjccqdedhjhexaojemdhtmpum4', 'hotpath 项目审查', 'question', '为了更好的完成这个理论结合实践，向通用人工智能方向发展，该项目中必须要做哪些重构或调整？'),
 ('bafyreidsrpoun2efkbcsvqcuew4cnlx5l2xn5sl5khgz6iqett23mfymam', '数学研究纲领的验证与收敛', 'question', '其理论对现有的数学理论的发展是否具有价值？是否只是同样数学理论结构的另一种表达范式？'),
 ('bafyreif7qeba646cvqkeql3n5awwxntpd5h3syznkozm6fgminz65w77ia', '不动点、最小化与 AI 模型框架', 'directive', '继续用不动点/最小化的范畴论第一性思考框架，对如今的大模型理论(LLM)，世界模型理论(World Model)，以及最终的通用人工智能理论(AGI)进行重构'),
 ('bafyreifn7qwf3daejj2vngwygcivn6tbjf4xxwntrrzaprtcdphc5jbxwe', '动态范畴与相对无穷的设想', 'question', '是不是我们可以基于这些新的公理，构建一个动态的无穷高阶演化范畴理论？'),
 ('bafyreihjh5nhjhvhywulzqyrecwmkoskwyz7i2ixrykzypv42sgu75thhu', '组成单元与组合能力', 'question', '每次对一个复杂系统的基本组成单元，有了进一步发展，发现其更基本的组成部分，反过来增强了上层系统的灵活性和组合创新能力，这样的现象有没有数学的基础理论基础？'),
 ('bafyreihkiegcw25vcx4qcwqsvympmueclwvuhfladd4qy3onndfk4jvgvi', '动态范畴与相对无穷的设想', 'assert', '在我看来，对于有限测度空间n，n的幂集空间，虽然只是有限的测度空间，但是它相对于构建它的n，却是一种有限无穷大。'),
 ('bafyreihkue2mviuq7h4ny5fuz5porve6rdkhdyuli72u4deuzonzsavede', '数学研究纲领的验证与收敛', 'question', '所以是不是可以固定好这个设想的数学框架vision纲领，然后着眼于与先前数学研究范式不同的部分作为突破点，聚焦完成一个能落地，可验证可发表的论文？'),
]


def main():
    report = json.loads((CODEX / f'catalog/report-{CATALOG}.json').read_text(encoding='utf-8'))
    db = sqlite3.connect((BASE / report['database']).as_uri() + '?mode=ro', uri=True)
    store = Store(OUT)
    archive = OUT / 'report-v1.json'
    if not archive.exists():
        original_report = (OUT / 'report.json').read_bytes()
        assert json.loads(original_report)['snapshot'] == PREVIOUS
        archive.write_bytes(original_report)
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    assert {r[0] for r in db.execute('SELECT content FROM candidates')} == {r[0] for r in SELECTIONS}
    raw_cache = {}

    def get(key):
        own = store.objects / (key + '.cbor')
        if own.exists():
            data = own.read_bytes()
        else:
            row = db.execute('SELECT path,offset,size FROM blocks WHERE cid=?', (key,)).fetchone()
            if row is None:
                raise KeyError(key)
            with (BASE / row[0]).open('rb') as stream:
                stream.seek(row[1]); data = stream.read(row[2])
        if cid(data, cid_bytes(key)[1]) != key:
            raise ValueError('CID mismatch: ' + key)
        return data if cid_bytes(key)[1] == 0x55 else decode(data)

    def pointer(document, path):
        for segment in path.split('/')[1:]:
            segment = segment.replace('~1', '/').replace('~0', '~')
            document = document[int(segment)] if isinstance(document, list) else document[segment]
        return document

    rows = []
    all_evidence = set()
    for content, topic, force, quote in SELECTIONS:
        text = get(content)['text']
        assert text.count(quote) == 1
        events = []
        for (key,) in db.execute('SELECT DISTINCT o.cid FROM current_occurrences o JOIN parts p ON p.occurrence=o.cid WHERE p.content=? ORDER BY o.cid', (content,)):
            event = get(key); source = get(event['source']['$link'])
            anchors = [r[0] for r in db.execute('SELECT extraction_record FROM anchors a WHERE occurrence=? AND EXISTS(SELECT 1 FROM membership m WHERE m.cid=a.extraction_record)', (key,))]
            assert anchors and event['actor_kind'] == 'unknown'
            for anchor in anchors:
                er = get(anchor); raw = er['raw']['$link']
                assert er['coordinate'] == 'json-pointer'
                if raw not in raw_cache:
                    raw_cache[raw] = json.loads(get(raw))
                original = pointer(raw_cache[raw], er['pointer'])
                if source['platform'] == 'claude-ai':
                    assert original['text'] == text
                elif source['platform'] == 'gemini':
                    assert er['pointer'].endswith('/title')
                    assert original == 'Prompted ' + text
                else:
                    raise ValueError(source['platform'])
            events.append({'occurrence': key, 'source': event['source']['$link'], 'platform': source['platform'],
                'native_thread_id': source['native_thread_id'], 'native_id': event['native_id'],
                'native_role': event['native_role'], 'actor_kind': event['actor_kind'],
                'event_time': event['event_time'], 'extraction_records': sorted(anchors, key=cid_bytes)})
        assert len(events) == 2 and {x['platform'] for x in events} == {'claude-ai', 'gemini'}
        evidence = {e['occurrence'] for e in events} | {k for e in events for k in e['extraction_records']}
        all_evidence.update(evidence)
        supplements = []
        if content == SELECTIONS[1][0]:
            supplements.append({'quote': '我下一步计划是开始黑盒/灰盒/用户门户入口项目的设计', 'force': 'assert', 'note': '关于计划的自述；与请求分开。与 hotpath 是否为同一项目未经证实。'})
        if content == SELECTIONS[6][0]:
            supplements.append({'quote': text[:text.index('是不是我们')], 'force': 'assert', 'note': '问句中“这些新的公理”的先行语境；源文本自述回忆与理论主张，未验证其数学正确性或被回忆事件。'})
        for extra in supplements:
            assert text.count(extra['quote']) == 1
            extra['quote_start'] = text.index(extra['quote'])
            extra['quote_end'] = extra['quote_start'] + len(extra['quote'])
        rows.append({'content': content, 'topic': '[整理主题] ' + topic, 'force': force, 'quote': quote, 'full_text': text,
            'quote_coordinate': 'Unicode scalar index in the exact content text; half-open',
            'quote_start': text.index(quote), 'quote_end': text.index(quote) + len(quote),
            'events': events, 'evidence': sorted(evidence, key=cid_bytes), 'context_statements': supplements})
    outputs = []
    concepts = {}
    for topic in sorted({r['topic'] for r in rows}):
        evidence = {k for r in rows if r['topic'] == topic for k in r['evidence']}
        concepts[topic] = store.put({'schema': 'pkst/concept@0.1', 'label': topic,
            'definition': 'Codex 为本次有限样本拟定的检索主题标签；不是来源中的逐字术语，不声称已建立理论或用户认可。',
            'evidence': linkset(evidence), 'asserted_by': ACTOR, 'lineage': None})
    outputs.extend(concepts.values())
    for row in rows:
        evidence = linkset(row['evidence'])
        row['statement'] = store.put({'schema': 'pkst/statement@0.1', 'text': row['quote'], 'force': row['force'],
            'holder': {'kind': 'unknown', 'id': 'source-speaker-unverified'}, 'evidence': evidence,
            'asserted_by': ACTOR, 'lineage': None})
        row['about'] = store.put({'schema': 'pkst/relation@0.1', 'predicate': 'about', 'from': link(row['statement']),
            'to': link(concepts[row['topic']]), 'evidence': evidence, 'asserted_by': ACTOR, 'basis': 'inferred',
            'scope': 'Bounded exact-quote sample; editorial topic classification by Codex. Topic grouping is not project or theory identity. Full source context retained.'})
        for extra in row['context_statements']:
            extra['statement'] = store.put({'schema': 'pkst/statement@0.1', 'text': extra['quote'], 'force': extra['force'],
                'holder': {'kind': 'unknown', 'id': 'source-speaker-unverified'}, 'evidence': evidence,
                'asserted_by': ACTOR, 'lineage': None})
            extra['about'] = store.put({'schema': 'pkst/relation@0.1', 'predicate': 'about', 'from': link(extra['statement']),
                'to': link(concepts[row['topic']]), 'evidence': evidence, 'asserted_by': ACTOR, 'basis': 'inferred',
                'scope': extra['note'] + ' assert describes the source speech act, not mathematical truth or verified authorship.'})
            outputs.extend([extra['statement'], extra['about']])
        pair = sorted([e['occurrence'] for e in row['events']], key=cid_bytes)
        row['propagation_candidate'] = store.put({'schema': 'pkst/relation@0.1', 'predicate': 'propagation-candidate',
            'from': link(pair[0]), 'to': link(pair[1]), 'evidence': evidence, 'asserted_by': ACTOR, 'basis': 'inferred',
            'scope': 'Unordered pair serialized by CID order. Exact native text identity; distinct occurrences remain. No copy direction, original author, causality, equivalent belief, theory revision, or endorsement inferred.'})
        outputs.extend(row[k] for k in ('statement', 'about', 'propagation_candidate'))
    implementation = {'method': 'bounded exact-quote extraction; exact native source anchor verification',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    activity = store.put({'schema': 'pkst/activity@0.1', 'operation': 'integrate', 'recorded_at': now,
        'actor': ACTOR, 'inputs': linkset(all_evidence), 'outputs': linkset(outputs), 'implementation': implementation,
        'coverage': {'selection': 'all ten exact long-text cross-source groups in the pinned current catalog; not the whole corpus',
            'source_occurrences': 20, 'statements': 12, 'editorial_concepts': 7, 'status': 'M1-M3-and-force-corrected-awaiting-review',
            'prior_catalog': report['snapshot'], 'limits': ['no AI replies interpreted', 'no change or causality inferred',
                'source attachments and quoted prior material not reconstructed', 'holder unknown; no mathematical truth or user adoption asserted',
                'ChatGPT export remains absent; described three-party exchanges are only partially represented',
                'only identical content CIDs included; near matches, salutation and newline variants excluded',
                'S6 quote covers only the model-reconstruction portion of a longer instruction',
                'S4 AGI direction is a source framing, not an independently established project property'],
            'recognized_but_not_extracted': ['S1 framework self-description', 'S8 category-theory conjecture', 'S10 recollection of multi-AI agreement'],
            'editorial_topic_rule': 'All editorial labels start with [整理主题]; source terms and editorial topics must not be silently equated.'}})
    snapshot = store.put({'schema': 'pkst/snapshot@0.1', 'parents': linkset([PREVIOUS]), 'roots': linkset([activity]), 'protocol': link(PROTOCOL),
        'coverage': {'scope': 'ten exact cross-platform pairs', 'recorded_cutoff': now, 'event_cutoff': None,
            'event_cutoff_basis': 'each occurrence keeps its native timestamp; no common archive completion time asserted',
            'status': 'corrected-review-candidate', 'local_only': True}})
    # This small graph is checked independently of the full catalog membership.
    pending = [snapshot]; visited = set(); adjacency = {}
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key); obj = get(key)
        children = list(links(obj)) if isinstance(obj, dict) else []
        adjacency[key] = children; pending.extend(children)
    grey = set(); black = set()
    def acyclic(key):
        if key in grey: raise ValueError('dependency cycle')
        if key in black: return
        grey.add(key)
        for child in adjacency[key]: acyclic(child)
        grey.remove(key); black.add(key)
    acyclic(snapshot)
    assert all(row['full_text'][row['quote_start']:row['quote_end']] == row['quote'] for row in rows)
    result = {'schema': 'pkst.semantic-pairs-report@0.1', 'status': 'M1-M3-and-force-corrected-awaiting-review', 'recorded_at': now,
        'snapshot': snapshot, 'catalog_snapshot': report['snapshot'], 'concepts': concepts,
        'previous_snapshot': PREVIOUS, 'candidate_groups': 10, 'source_occurrences': 20, 'statements': 12, 'relations': 22,
        'verified_dependency_blocks_including_raw': len(visited), 'raw_documents_independently_parsed': len(raw_cache),
        'quote_and_native_anchors_verified': 20, 'rows': rows,
        'limits': 'This is a bounded interpretation, not a complete thought graph. Dates do not establish influence, copy direction or evolution.'}
    (OUT / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# 跨 AI 主题与时间样本', '', '状态：已按 Claude 第一轮审阅修正，待复核。选取统一索引中的全部 10 组相同长文本，共 20 次独立出现、12 条逐字语义单元。带 [整理主题] 前缀的标题由 Codex 拟定；引文保留原字。原生 human/user 通道不能独立证明作者身份，所有 holder 保持未知。', '',
        '这一视图按主题汇集发言时间；早晚次序不等于复制、继承或因果。问题与假设不作为已成立理论。两次相同发言共享 content，但 occurrence 和取证锚分别保留。', '',
        'assert 表示源话语进行了断言，不表示档案认定该内容为真。ChatGPT 导出尚未加入，三方讨论只覆盖已取得的两方。近似文本、改称呼与换行的变体不在这批同文样本中。', '',
        f'快照：`{snapshot}`', '', '[机器可读报告与完整原话](../contributions/codex/semantic-pairs/report.json)', '']
    for topic in concepts:
        lines.extend(['## ' + topic, ''])
        selected = sorted([r for r in rows if r['topic'] == topic], key=lambda r: min(e['event_time']['value'] for e in r['events']))
        for row in selected:
            for extra in row['context_statements']:
                lines.extend(['上下文（逐字）：', '', '> ' + extra['quote'], '', '类型：`' + extra['force'] + '`。' + extra['note'], ''])
            lines.extend(['> ' + row['quote'], '', '类型：`' + row['force'] + '`。'])
            for event in sorted(row['events'], key=lambda e: e['event_time']['value']):
                lines.extend(['', '- ' + event['event_time']['value'] + ' · ' + event['platform'] + ' · `' + event['occurrence'] + '`'])
            lines.extend(['', '上述原话的语境、消息 ID、JSON Pointer 取证锚与完整内容见机器报告。', ''])
    (BASE / 'reports/semantic-timeline.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('snapshot', 'candidate_groups', 'source_occurrences', 'statements', 'quote_and_native_anchors_verified', 'verified_dependency_blocks_including_raw')}))


if __name__ == '__main__':
    main()
