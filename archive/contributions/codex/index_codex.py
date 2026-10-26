"""Rebuildable natural-language index over captured Codex raw logs.

This index is not a semantic assertion store or an authoritative source.
Original bytes remain in raw/. No archive text is executed as instructions.
"""
import argparse, hashlib, json, sqlite3, time
from collections import Counter
from compression import zstd
from pathlib import Path
from pkst_codec import cid, encode

MAX_LINE = 64 * 1024 * 1024

def records(stream):
    offset = 0
    while True:
        line = stream.readline(MAX_LINE + 1)
        if not line:
            return
        start = offset
        offset += len(line)
        if len(line) > MAX_LINE:
            while line and not line.endswith(b'\n'):
                line = stream.readline(MAX_LINE + 1)
                offset += len(line)
            yield start, offset, None, 'line-over-64MiB'
        else:
            yield start, offset, line, None

def index_file(con, row, root):
    raw = row['raw_cid']
    path = root / 'raw' / (raw + '.bin')
    counts = Counter()
    errors = []
    thread = None
    process = 'unknown'
    source = None
    opener = zstd.open if row['source_suffix'].endswith('.zst') else open
    with opener(path, 'rb') as stream:
        for start, end, line, failure in records(stream):
            if failure:
                errors.append({'start': start, 'end': end, 'error': failure})
                continue
            try:
                d = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                errors.append({'start': start, 'end': end, 'error': type(exc).__name__})
                continue
            typ = d.get('type', 'unknown')
            counts['record:' + str(typ)] += 1
            p = d.get('payload', {})
            if not isinstance(p, dict):
                counts['non-map-payload'] += 1
                continue
            if typ == 'session_meta':
                thread = p.get('id') or p.get('session_id')
                source = p.get('source')
                if isinstance(source, dict) and ('subagent' in source or 'agent' in source):
                    process = 'sidechain'
                elif source in ('cli', 'vscode', 'exec', 'app-server'):
                    process = 'main'
                else:
                    process = 'unknown'
            # event_msg UI projections are counted, not duplicated into message text.
            if typ != 'response_item' or p.get('type') != 'message':
                continue
            role = p.get('role', 'unknown')
            counts['message:' + str(role)] += 1
            parts = []
            nontext = []
            for part in p.get('content', []):
                if not isinstance(part, dict):
                    nontext.append(type(part).__name__)
                elif part.get('type') in ('input_text', 'output_text', 'text') and isinstance(part.get('text'), str):
                    parts.append(part['text'])
                else:
                    nontext.append(str(part.get('type', 'unknown')))
            if not parts:
                counts['message-without-text'] += 1
                continue
            # Native role is evidence about envelope role, not proof of human authorship.
            actor = {'assistant': 'ai', 'system': 'system', 'developer': 'system', 'tool': 'tool'}.get(role, 'unknown')
            meta = d.get('metadata')
            proc = 'injected' if p.get('isMeta') is True else process
            if p.get('is_summary') is True:
                proc = 'compaction'
            try:
                contents = []
                for text in parts:
                    obj = {'schema': 'pkst/content@0.1', 'media_type': 'text/plain', 'text': text}
                    key = cid(encode(obj))
                    con.execute('INSERT OR IGNORE INTO content VALUES (?,?)', (key, text))
                    contents.append(key)
                con.execute('INSERT INTO message VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (raw, start, end, thread, p.get('id'), str(role), actor, proc,
                     d.get('timestamp'), json.dumps(contents), json.dumps(nontext),
                     json.dumps(meta, ensure_ascii=False), p.get('phase')))
                counts['indexed-message'] += 1
            except (UnicodeError, ValueError) as exc:
                errors.append({'start': start, 'end': end, 'error': type(exc).__name__})
    status = 'partial' if errors else 'parsed'
    if not counts['indexed-message']:
        status = 'no-message-projection'
    con.execute('INSERT INTO source_file VALUES (?,?,?,?,?,?,?)',
        (raw, row['path'], thread, json.dumps(source), status,
         json.dumps(dict(counts)), json.dumps(errors)))
    return counts, errors, status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--database', required=True)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    root = Path(args.root)
    db = Path(args.database)
    if db.exists():
        raise FileExistsError('Use a new index path; existing evidence is not overwritten')
    con = sqlite3.connect(db)
    con.executescript('''
        CREATE TABLE content(cid TEXT PRIMARY KEY, text TEXT NOT NULL);
        CREATE TABLE message(raw TEXT,start INTEGER,end INTEGER,thread TEXT,native_id TEXT,
          native_role TEXT,actor_kind TEXT,process_kind TEXT,event_time TEXT,content_cids TEXT,
          nontext_parts TEXT,metadata TEXT,phase TEXT,PRIMARY KEY(raw,start));
        CREATE TABLE source_file(raw TEXT PRIMARY KEY,path TEXT,thread TEXT,source TEXT,status TEXT,counts TEXT,errors TEXT);
    ''')
    rows = [json.loads(line) for line in Path(args.manifest).read_text(encoding='utf-8').splitlines()]
    if args.limit:
        rows = rows[:args.limit]
    totals = Counter()
    statuses = Counter()
    failures = []
    seen = set()
    started = time.monotonic()
    for i, row in enumerate(rows):
        if row['status'] != 'captured':
            statuses['capture-not-stable'] += 1
            continue
        if row['raw_cid'] in seen:
            statuses['duplicate-raw'] += 1
            continue
        seen.add(row['raw_cid'])
        try:
            counts, errors, status = index_file(con, row, root)
            totals.update(counts)
            totals['parse-errors'] += len(errors)
            statuses[status] += 1
            con.commit()
        except (OSError, EOFError, ValueError, zstd.ZstdError) as exc:
            con.rollback()
            failures.append({'raw': row['raw_cid'], 'error_type': type(exc).__name__, 'error': str(exc)})
            statuses['failed'] += 1
        if (i + 1) % 200 == 0:
            print(json.dumps({'processed': i + 1, 'of': len(rows), 'indexed_messages': totals['indexed-message'], 'statuses': statuses}), flush=True)
    con.execute('CREATE INDEX messages_by_thread ON message(thread)')
    con.execute('CREATE INDEX messages_by_role_time ON message(native_role,event_time)')
    con.commit()
    unique_content = con.execute('SELECT COUNT(*) FROM content').fetchone()[0]
    con.close()
    report = {'schema': 'pkst.derived-index-report.v0.1', 'manifest': str(args.manifest),
        'manifest_sha256': hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest(),
        'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_files': len(rows), 'counts': dict(totals), 'statuses': dict(statuses), 'failures': failures,
        'unique_content': unique_content, 'database': str(db), 'database_bytes': db.stat().st_size,
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'limitations': ['Response-item message text only; other record kinds remain in raw originals.',
                       'User-role content is not automatically human-authored or an endorsed belief.',
                       'No semantic assertions or causal relationships extracted.',
                       'Missing attachments and database-only histories have not been reconciled.']}
    report_path = db.with_suffix('.report.json')
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
