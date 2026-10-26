"""Read-only federation of pinned PKST roots; SQLite is a rebuildable view.

Construction choice: avoid copying/re-importing every archive. Resolve existing
CAR/file blocks, verify each fetched CID, and index only current root closure.
History remains reachable in the immutable graph, but is excluded from search.
No embeddings, authored beliefs, copy direction, or semantic merge is inferred.
"""
import argparse
import hashlib
import json
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pkst_codec import Store, check_sets, cid, cid_bytes, decode, encode, link, links, linkset

BASE = Path(__file__).resolve().parents[2]
CODEX = BASE / 'contributions/codex'
PEER = BASE / 'contributions/claude'
OUT = CODEX / 'catalog'
PIN_REPORTS = [
    ('codex-windows', CODEX / '.private/windows-evidence.report.json', 'root'),
    ('claude-windows', PEER / 'conversion-summary-20261024T072716Z.json', 'snapshot'),
    ('gemini', CODEX / 'gemini/.private/gemini-evidence.report.json', 'root'),
    ('claude-ai', PEER / 'claude-ai-conversion-summary-20261024T081738Z.json', 'snapshot'),
    ('semantic-pilot', CODEX / 'pilot/report.json', 'snapshot'),
]


class Resolver:
    def __init__(self):
        self.indexes = []
        for car, index in [
            (CODEX / '.private/windows-evidence.car', CODEX / '.private/windows-evidence.index.sqlite'),
            (CODEX / 'gemini/.private/gemini-evidence.car', CODEX / 'gemini/.private/gemini-evidence.index.sqlite'),
            (CODEX / 'mac/.private/mac-evidence.car', CODEX / 'mac/.private/mac-evidence.index.sqlite'),
            (PEER / '.private/mac-claude-main.car', CODEX / '.private/mac-claude-audit-20261024.sqlite'),
            (PEER / '.private/claude-ai-evidence-0.1.1.car', CODEX / '.private/claude-ai-audit-20261024T081738Z-d0dcc2da38.sqlite'),
        ]:
            db = sqlite3.connect(index.as_uri() + '?mode=ro', uri=True)
            self.indexes.append((car, car.open('rb'), db))
        self.object_dirs = [OUT / 'objects', CODEX / 'pilot/objects', CODEX / 'semantic-pairs/objects', PEER / 'objects']
        self.raw_dirs = [OUT / 'raw', CODEX / 'raw', CODEX / 'gemini/raw', CODEX / 'mac/raw', PEER / 'raw']

    def read(self, key):
        if cid_bytes(key)[1] == 0x55:
            for folder in self.raw_dirs:
                path = folder / (key + '.bin')
                if path.exists():
                    h = hashlib.sha256()
                    with path.open('rb') as stream:
                        for part in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                            h.update(part)
                    if h.digest() != cid_bytes(key)[4:]:
                        raise ValueError('Raw hash mismatch: ' + key)
                    return None, str(path.relative_to(BASE)), 0, path.stat().st_size
            raise FileNotFoundError(key)
        for path, stream, db in self.indexes:
            row = db.execute('SELECT offset,size FROM blocks WHERE cid=?', (key,)).fetchone()
            if row:
                stream.seek(row[0])
                data = stream.read(row[1])
                location, offset = path, row[0]
                break
        else:
            location = next((p / (key + '.cbor') for p in self.object_dirs if (p / (key + '.cbor')).exists()), None)
            if location is None:
                raise FileNotFoundError(key)
            data, offset = location.read_bytes(), 0
        if cid(data) != key:
            raise ValueError('Object hash mismatch: ' + key)
        obj = decode(data)
        check_sets(obj)
        return obj, str(location.relative_to(BASE)), offset, len(data)


def current_children(obj):
    # Every snapshot's parents are historical; only roots/coverage/protocol are current.
    return list(links({k: v for k, v in obj.items() if k != 'parents'})) if obj.get('schema') == 'pkst/snapshot@0.1' else list(links(obj))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--extra-pin', nargs=3, action='append', default=[], metavar=('COLLECTION','REPORT','FIELD'))
    ap.add_argument('--previous')
    ap.add_argument('--resume', action='store_true', help='Continue only committed collection transactions in an unfinished derived catalog')
    args = ap.parse_args()
    run = args.run
    if not run.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Invalid run identifier')
    dest = OUT / '.private' / run
    if args.resume:
        if not (dest / 'catalog.sqlite').is_file() or (OUT / ('report-' + run + '.json')).exists():
            raise ValueError('Resume requires an unfinished existing catalog')
    else:
        dest.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    db = sqlite3.connect(dest / 'catalog.sqlite')
    if not args.resume:
        db.executescript('''
        CREATE TABLE blocks(cid TEXT PRIMARY KEY,schema TEXT,path TEXT,offset INTEGER,size INTEGER);
        CREATE TABLE edges(src TEXT,dst TEXT,historical INTEGER,PRIMARY KEY(src,dst,historical));
        CREATE TABLE membership(collection TEXT,cid TEXT,PRIMARY KEY(collection,cid));
        CREATE TABLE sources(cid TEXT PRIMARY KEY,platform TEXT,namespace TEXT,native_thread_id TEXT);
        CREATE TABLE occurrences(cid TEXT PRIMARY KEY,source TEXT,native_id TEXT,role TEXT,actor TEXT,process TEXT,event_time TEXT,event_format TEXT,time_json TEXT);
        CREATE TABLE content(cid TEXT PRIMARY KEY,text TEXT);
        CREATE TABLE parts(occurrence TEXT,ordinal INTEGER,content TEXT,PRIMARY KEY(occurrence,ordinal));
        CREATE TABLE anchors(occurrence TEXT,extraction_record TEXT,raw TEXT,coordinates_json TEXT,PRIMARY KEY(occurrence,extraction_record));
        CREATE TABLE candidates(content TEXT PRIMARY KEY,collections INTEGER,occurrences INTEGER,characters INTEGER);
        ''')
    resolver = Resolver()
    visited = {r[0] for r in db.execute('SELECT cid FROM blocks')} if args.resume else set()
    resumed_blocks = len(visited)
    resume_evidence = json.loads((dest / 'resume-evidence.json').read_text(encoding='utf-8-sig')) if args.resume else None
    if args.resume and db.execute("SELECT count(*) FROM sqlite_master WHERE name='current_occurrences'").fetchone()[0]:
        raise ValueError('This resume path accepts collection/closure stage only, before views are finalized')
    pinned = []
    pins = PIN_REPORTS + [(name, BASE / path, field) for name, path, field in args.extra_pin]
    if len({name for name, _, _ in pins}) != len(pins):
        raise ValueError('Duplicate collection name')
    for name, path, field in pins:
        raw = path.read_bytes()
        pinned.append({'collection': name, 'root': json.loads(raw)[field], 'report': str(path.relative_to(BASE)), 'report_sha256': hashlib.sha256(raw).hexdigest()})

    def load(key):
        if key in visited:
            return
        obj, path, offset, size = resolver.read(key)
        visited.add(key)
        schema = obj.get('schema') if obj is not None else 'raw'
        db.execute('INSERT INTO blocks VALUES(?,?,?,?,?)', (key, schema, path, offset, size))
        if obj is None:
            return
        children = set(current_children(obj))
        all_children = set(links(obj))
        db.executemany('INSERT INTO edges VALUES(?,?,?)', [(key, k, int(k not in children)) for k in all_children])
        if schema == 'pkst/source@0.1':
            db.execute('INSERT INTO sources VALUES(?,?,?,?)', (key, obj['platform'], obj['namespace'], obj['native_thread_id']))
        elif schema == 'pkst/content@0.1':
            db.execute('INSERT INTO content VALUES(?,?)', (key, obj['text']))
        elif schema == 'pkst/occurrence@0.1':
            et = obj['event_time']
            db.execute('INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?,?)', (key, obj['source']['$link'], obj['native_id'], obj['native_role'], obj['actor_kind'], obj['process_kind'], et['value'], et['format'], json.dumps(et, ensure_ascii=False)))
            db.executemany('INSERT INTO parts VALUES(?,?,?)', [(key, i, k['$link']) for i, k in enumerate(obj['content'])])
        elif schema == 'pkst/extraction-record@0.1':
            coords = {k: obj[k] for k in ('coordinate', 'start', 'end', 'pointer', 'parser') if k in obj}
            db.execute('INSERT INTO anchors VALUES(?,?,?,?)', (obj['occurrence']['$link'], key, obj['raw']['$link'], json.dumps(coords, ensure_ascii=False)))

    collection_counts = {}
    for pin in pinned:
        committed = db.execute('SELECT count(*) FROM membership WHERE collection=?', (pin['collection'],)).fetchone()[0]
        if committed:
            if not args.resume or not db.execute('SELECT 1 FROM membership WHERE collection=? AND cid=?', (pin['collection'], pin['root'])).fetchone():
                raise ValueError('Committed collection does not match pinned root')
            collection_counts[pin['collection']] = dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema', (pin['collection'],)))
            print(json.dumps({'collection': pin['collection'], 'reused_verified_committed_blocks': committed}), flush=True)
            continue
        stack, members = [pin['root']], set()
        while stack:
            key = stack.pop()
            if key in members:
                continue
            members.add(key)
            load(key)
            stack.extend(row[0] for row in db.execute('SELECT dst FROM edges WHERE src=? AND historical=0', (key,)))
        db.executemany('INSERT INTO membership VALUES(?,?)', [(pin['collection'], k) for k in members])
        counts = dict(db.execute('SELECT b.schema,count(*) FROM membership m JOIN blocks b ON b.cid=m.cid WHERE m.collection=? GROUP BY b.schema', (pin['collection'],)))
        collection_counts[pin['collection']] = counts
        db.commit()
        print(json.dumps({'collection': pin['collection'], 'current_counts': counts}), flush=True)

    current_block_count = len(visited)
    # Full dependency closure is checked separately, including retained histories.
    stack = [r[0] for r in db.execute('SELECT DISTINCT dst FROM edges WHERE dst NOT IN (SELECT cid FROM blocks)')]
    while stack:
        key = stack.pop()
        if key in visited:
            continue
        load(key)
        stack.extend(row[0] for row in db.execute('SELECT dst FROM edges WHERE src=?', (key,)))
    if db.execute('SELECT count(*) FROM edges WHERE dst NOT IN (SELECT cid FROM blocks)').fetchone()[0]:
        raise ValueError('Incomplete reference closure')
    db.executescript('''
        CREATE INDEX parts_content ON parts(content);
        CREATE INDEX membership_cid ON membership(cid);
        CREATE INDEX occurrences_source ON occurrences(source);
        CREATE VIEW current_occurrences AS SELECT o.* FROM occurrences o WHERE EXISTS(SELECT 1 FROM membership m WHERE m.cid=o.cid);
        CREATE VIEW current_content AS SELECT c.* FROM content c WHERE EXISTS(SELECT 1 FROM membership m WHERE m.cid=c.cid);
        INSERT INTO candidates
        SELECT c.cid,count(DISTINCT m.collection),count(DISTINCT o.cid),length(c.text)
        FROM current_content c JOIN parts p ON p.content=c.cid JOIN current_occurrences o ON o.cid=p.occurrence
        JOIN sources s ON s.cid=o.source
        JOIN membership m ON m.cid=o.cid
        WHERE length(c.text)>=150 AND m.collection IN ('codex-windows','claude-windows','gemini','claude-ai','codex-mac','claude-mac')
        GROUP BY c.cid HAVING count(DISTINCT s.platform)>1 AND count(DISTINCT o.cid)>1;
    ''')
    # Search uses literal substring matching so short Chinese terms also work.
    # Projection/opaque text never enters the native-text table.
    current_events = db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0]
    anchored = db.execute('SELECT count(DISTINCT o.cid) FROM current_occurrences o JOIN anchors a ON a.occurrence=o.cid').fetchone()[0]
    if current_events != anchored:
        raise ValueError('Current event lacks extraction record')
    missing_content = db.execute("SELECT count(*) FROM parts p JOIN current_occurrences o ON p.occurrence=o.cid LEFT JOIN blocks b ON p.content=b.cid WHERE b.cid IS NULL").fetchone()[0]
    if missing_content:
        raise ValueError('Current event part missing')
    candidate_count = db.execute('SELECT count(*) FROM candidates').fetchone()[0]
    raw_count = db.execute("SELECT count(*) FROM blocks WHERE schema='raw'").fetchone()[0]
    store = Store(OUT)
    raw_dir = OUT / 'raw'
    raw_dir.mkdir(exist_ok=True)
    script = Path(__file__).read_bytes()
    implementation = cid(script, 0x55)
    script_path = raw_dir / (implementation + '.bin')
    if not script_path.exists():
        script_path.write_bytes(script)
    actor = {'kind': 'ai', 'id': 'codex'}
    activity = store.put({'schema': 'pkst/activity@0.1', 'operation': 'integrate', 'recorded_at': now, 'actor': actor,
        'inputs': linkset([x['root'] for x in pinned]), 'outputs': [], 'implementation': link(implementation),
        'coverage': {'scope': 'federated catalog of explicitly pinned evidence and interpretation roots',
            'current_events': current_events, 'history_excluded_from_search': True,
            'semantic_extraction': 'only pinned bounded samples; review status preserved by separate receipts', 'same_text_candidates': candidate_count,
            'candidate_status': 'unreviewed derived index, no relation or merge created'}})
    snapshot = store.put({'schema': 'pkst/snapshot@0.1', 'parents': linkset([args.previous]) if args.previous else [], 'roots': linkset([activity]),
        'coverage': {'scope': 'pinned local captures', 'recorded_cutoff': now,
            'event_cutoff': None, 'event_cutoff_basis': 'heterogeneous source timestamps; source roots preserve native time and coverage',
            'pending': ['ChatGPT export', 'other AI sources and writings', 'full semantic extraction'],
            'local_only': True}, 'protocol': link('bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq')})
    # Verify new federation links, without copying referenced source stores.
    stack = [snapshot]
    while stack:
        key = stack.pop()
        if key in visited:
            continue
        load(key)
        stack.extend(r[0] for r in db.execute('SELECT dst FROM edges WHERE src=?', (key,)))
    db.commit()
    integrity = db.execute('PRAGMA integrity_check').fetchall()
    if integrity != [('ok',)]:
        raise ValueError(str(integrity))
    report = {'schema': 'pkst.federated-catalog-report@0.1', 'recorded_at': now, 'run': run, 'snapshot': snapshot,
        'pinned_sources': pinned, 'current_counts_by_collection': collection_counts,
        'unique_current_events': current_events, 'current_events_with_anchors': anchored,
        'unique_current_blocks_including_raw': current_block_count,
        'all_verified_blocks_including_history_and_federation': len(visited), 'raw_blocks_verified': raw_count + 1,
        'exact_long_text_candidate_groups': candidate_count,
        'database': str((dest / 'catalog.sqlite').relative_to(BASE)),
        'status': 'CID, canonical encoding, full dependency closure, current membership and anchors verified',
        'query_rule': 'current snapshot closure only; native text only; literal substring search; no historical parents',
        'limits': ['source capture gaps remain', 'role user/human does not establish authorship', 'exact matches are not originality, copy direction, causality or endorsement', 'SQLite is derived and rebuildable', 'full intellectual graph not extracted'],
        'elapsed_seconds': round(time.monotonic() - started, 3), 'resumed_verified_committed_blocks': resumed_blocks,
        'previous_attempt_elapsed_seconds': resume_evidence['elapsed_before_resume_seconds'] if resume_evidence else 0,
        'execution_note': 'Committed per-collection CID checks reused; interrupted in-flight work rolled back by SQLite. Final closure and search checks run after resume.' if args.resume else 'single process'}
    db.close()
    report_path = OUT / ('report-' + run + '.json')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'current.json').write_text(json.dumps({'report': report_path.name, 'snapshot': snapshot, 'database': report['database']}, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
