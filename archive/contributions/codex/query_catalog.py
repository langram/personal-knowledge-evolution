"""Search current native-text events and return evidence CIDs, never execute text."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]


def search(db, term, limit=20, role=None, platform=None):
    if not term:
        raise ValueError('Search term must not be empty')
    clauses, params = ['instr(c.text,?)>0'], [term]
    if role:
        clauses.append('o.role=?')
        params.append(role)
    if platform:
        clauses.append('s.platform=?')
        params.append(platform)
    sql = '''SELECT DISTINCT o.cid,o.source,o.native_id,o.role,o.actor,o.event_time,o.event_format,
        s.platform,s.native_thread_id,c.cid,c.text
        FROM current_occurrences o JOIN sources s ON s.cid=o.source
        JOIN parts p ON p.occurrence=o.cid JOIN current_content c ON c.cid=p.content
        WHERE ''' + ' AND '.join(clauses) + ' ORDER BY o.cid,c.cid LIMIT ?'
    rows = []
    for oc, source, native_id, native_role, actor, et, fmt, platform, thread, content, text in db.execute(sql, params + [limit]):
        start = max(0, text.index(term) - 80)
        rows.append({'occurrence': oc, 'source': source, 'platform': platform, 'native_thread_id': thread,
            'native_id': native_id, 'native_role': native_role, 'actor_kind': actor,
            'event_time': et, 'event_format': fmt, 'content': content, 'excerpt': text[start:start + 500],
            'excerpt_start_unicode_codepoint': start,
            'collections': [r[0] for r in db.execute('SELECT collection FROM membership WHERE cid=? ORDER BY collection', (oc,))],
            'anchors': [{'extraction_record': er, 'raw': raw, 'coordinates': json.loads(coords)} for er, raw, coords in db.execute('SELECT extraction_record,raw,coordinates_json FROM anchors a WHERE occurrence=? AND EXISTS(SELECT 1 FROM membership m WHERE m.cid=a.extraction_record) ORDER BY extraction_record', (oc,))]})
    return rows


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    ap.add_argument('term', nargs='?')
    ap.add_argument('--role')
    ap.add_argument('--platform', help='Exact source platform, for example chatgpt')
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--object', dest='object_cid')
    ap.add_argument('--stats', action='store_true')
    args = ap.parse_args()
    if not 1 <= args.limit <= 500:
        raise ValueError('limit must be 1..500')
    pointer = json.loads((BASE / 'contributions/codex/catalog/current.json').read_text(encoding='utf-8'))
    db = sqlite3.connect((BASE / pointer['database']).as_uri() + '?mode=ro', uri=True)
    if args.stats:
        result = {'snapshot': pointer['snapshot'], 'events': db.execute('SELECT count(*) FROM current_occurrences').fetchone()[0],
            'sources': db.execute('SELECT count(DISTINCT source) FROM current_occurrences').fetchone()[0],
            'roles': dict(db.execute('SELECT role,count(*) FROM current_occurrences GROUP BY role')),
            'cross_source_candidate_groups': db.execute('SELECT count(*) FROM candidates').fetchone()[0]}
    elif args.object_cid:
        from pkst_codec import cid, cid_bytes, decode
        row = db.execute('SELECT path,offset,size FROM blocks WHERE cid=?', (args.object_cid,)).fetchone()
        if not row:
            raise KeyError(args.object_cid)
        if cid_bytes(args.object_cid)[1] == 0x55:
            result = {'raw': args.object_cid, 'path': row[0], 'bytes': row[2], 'handling': 'raw-only; no execution'}
        else:
            with (BASE / row[0]).open('rb') as stream:
                stream.seek(row[1])
                data = stream.read(row[2])
            if cid(data) != args.object_cid:
                raise ValueError('Object changed or index invalid')
            result = decode(data)
    elif args.term:
        result = search(db, args.term, args.limit, args.role, args.platform)
    else:
        ap.error('Provide a term, --stats, or --object CID')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
