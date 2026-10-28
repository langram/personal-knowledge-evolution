"""Capture recent visible conversation text with exact local record evidence."""
import collections
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
BASE = ROOT / 'outputs/personal-thought-archive'
C = BASE / 'contributions/codex'
ARCHIVE = C / 'merkle-native-20261029'
OUT = BASE / 'dossiers/2026-10-29-merkle-native'
PUBLIC = ROOT / 'publication/personal-knowledge-evolution'
PRIOR = C / 'protection-and-trust-20261027'
OLD = BASE / 'dossiers/2026-10-27-protection-and-trust/02-new-principles.md'
TARGET = '01a18016-3e9d-7af1-860d-feccfc3c9ffb'
CURRENT = '01a16c8a-f6e1-7580-b378-b6e49f0be965'
LOWER = '2026-10-24T00:00:00Z'
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

def sha(data): return hashlib.sha256(data).hexdigest()
def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())
def raw(data):
    key = cid(data, 0x55); path = ARCHIVE / 'raw' / (key + '.bin')
    if path.exists(): assert path.read_bytes() == data
    else: path.write_bytes(data)
    return key

def prepare():
    if (ARCHIVE / 'capture.json').exists():
        raise RuntimeError('Capture exists; reconcile before rerunning.')
    OUT.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / 'raw').mkdir(parents=True, exist_ok=True)
    pointer = json.loads((C / 'catalog/current.json').read_bytes())
    prior = json.loads((PRIOR / 'report.json').read_bytes())
    assert OLD.read_bytes() == (PUBLIC / 'book/current.md').read_bytes()
    write_json(ARCHIVE / 'baseline.json', {'pointer': pointer, 'document': prior['document'],
        'dossier_root': prior['snapshot'], 'concepts': prior['concepts'],
        'manuscript': str(OLD.relative_to(BASE)), 'sha256': sha(OLD.read_bytes())})
    db = sqlite3.connect((BASE / pointer['database']).as_uri() + '?mode=ro', uri=True)
    prior_events = {}
    for row in db.execute('''SELECT o.cid,s.native_thread_id,o.native_id,o.role,o.event_time,p.ordinal,p.content,c.text
      FROM current_occurrences o JOIN sources s ON s.cid=o.source JOIN parts p ON p.occurrence=o.cid
      LEFT JOIN content c ON c.cid=p.content WHERE s.platform IN ('codex-local','claude-code')
      AND (o.event_time>=? OR o.event_time IS NULL) ORDER BY o.cid,p.ordinal''', (LOWER,)):
        key, thread, native, role, time, ordinal, content, text = row
        entry = prior_events.setdefault(key, {'thread': thread, 'id': native, 'role': role, 'time': time, 'parts': [], 'texts': []})
        entry['parts'].append(content)
        if text is not None: entry['texts'].append(text)
    by_id = {(e['thread'], e['role'], e['id']): key for key, e in prior_events.items() if e['id']}
    by_signature = {(e['thread'], e['role'], e['time'], tuple(e['parts'])): key for key, e in prior_events.items()}
    by_text = {(e['thread'], e['role'], '\n\n'.join(e['texts'])): key for key, e in prior_events.items()}
    store = Store(ARCHIVE); events = []; selected = {}; scans = []; omissions = collections.Counter()
    # Freeze the cutoff at the current author's request, excluding this active response.
    current_files = list(Path('C:/Users/langr/.codex/sessions/2026/10/24').glob('*' + CURRENT + '*'))
    request_times = []
    for path in current_files:
        with path.open('rb') as stream:
            for line in stream:
                if not line.endswith(b'\n'): break
                r = json.loads(line); p = r.get('payload', {})
                if r.get('type') == 'response_item' and p.get('role') == 'user':
                    for block in p.get('content', []):
                        if block.get('text', '').startswith('请将最近会话内容加入merkle个人知识库'):
                            request_times.append(r['timestamp'])
    assert len(request_times) == 1, request_times
    upper = request_times[0]

    def ingest(thread, platform, namespace, role, native, time, texts, data, coordinate, parent=None, phase=None, context=None):
        if not texts or not any(x.strip() for x in texts):
            omissions['no-visible-text'] += 1; return
        text = '\n\n'.join(texts)
        if role == 'user' and text.lstrip().startswith(('# AGENTS.md instructions', '<environment_context>', '<external_codex_apps_open_page>', '<subagent_notification>')):
            omissions['injected-context-envelope'] += 1; return
        sobj = {'schema': 'pkst/source@0.1', 'platform': platform, 'namespace': namespace, 'native_thread_id': thread}
        source = store.put(sobj)
        parts = [store.put({'schema': 'pkst/content@0.1', 'media_type': 'text/plain;charset=utf-8', 'text': t}) for t in texts]
        existing = by_id.get((thread, role, native)) if native else None
        existing = existing or by_signature.get((thread, role, time, tuple(parts)))
        if context: existing = existing or by_text.get((thread, role, text))
        if existing:
            omissions['existing-event-or-replayed-record'] += 1
            return
        rawkey = raw(data)
        native_time = {'value': time, 'format': 'rfc3339' if time else 'unknown',
            'precision': 'millisecond' if time else 'unknown', 'zone_known': bool(time), 'unit': None}
        obj = {'schema': 'pkst/occurrence@0.1', 'source': link(source), 'native_id': native,
            'locator': {'raw': link(rawkey), 'start': 0, 'end': len(data), 'coordinate': 'captured-record-utf8-bytes'},
            'native_role': role, 'actor_kind': 'ai' if role == 'assistant' else 'unknown',
            'process_kind': 'main', 'content': [link(p) for p in parts],
            'native_parent_ids': [parent] if parent else None, 'event_time': native_time}
        if context:
            obj.update({'namespaces': {'mn': 'urn:pkst:merkle-native:1'}, 'mn:time_context': context})
        occurrence = store.put(obj)
        anchor = store.put({'schema': 'pkst/extraction-record@0.1', 'raw': link(rawkey), 'occurrence': link(occurrence),
            'coordinate': 'captured-record-utf8-bytes', 'start': 0, 'end': len(data),
            'parser': 'recent-visible-text-v1', 'role_basis': 'native envelope; role is not automatic original authorship',
            'namespaces': {'mn': 'urn:pkst:merkle-native:1'}, 'mn:origin': coordinate})
        item = {'occurrence': occurrence, 'source': source, 'content': parts, 'anchors': [anchor],
            'role': role, 'platform': platform, 'thread': thread, 'time': time, 'time_format': native_time['format'],
            'native_event_time': native_time, 'native_id': native, 'phase': phase, 'text': text,
            'capture': {'raw': rawkey, 'sha256': sha(data), 'bytes': len(data), 'origin': coordinate}, 'time_context': context}
        events.append(item)
        if native: by_id[(thread, role, native)] = occurrence
        by_signature[(thread, role, time, tuple(parts))] = occurrence
        by_text[(thread, role, text)] = occurrence

    for root, platform in [(Path('C:/Users/langr/.codex/sessions'), 'codex-local'), (Path('C:/Users/langr/.claude/projects'), 'claude-code')]:
        candidates = sorted(p for p in root.rglob('*.jsonl') if p.stat().st_mtime >= 1792771200)
        for path in candidates:
            limit = path.stat().st_size; offset = 0; thread = None; recent = 0
            with path.open('rb') as stream:
                while stream.tell() < limit:
                    start = stream.tell(); line = stream.readline()
                    if not line.endswith(b'\n') or stream.tell() > limit: break
                    record = json.loads(line); p = record.get('payload', {})
                    offset = stream.tell()
                    if platform == 'codex-local':
                        if record.get('type') == 'session_meta': thread = p['id']
                        if record.get('type') != 'response_item' or p.get('type') != 'message': continue
                        if p.get('role') not in {'user', 'assistant'}: continue
                        if p.get('channel') not in {None, 'final', 'commentary'} or p.get('phase') not in {None, 'commentary', 'final_answer'} or p.get('is_summary') or p.get('isMeta'):
                            omissions['internal-or-nonpublic-message'] += 1; continue
                        role = p['role']; time = record.get('timestamp'); native = p.get('id'); parent = p.get('parent_id')
                        texts = [b['text'] for b in p.get('content', []) if b.get('type') in {'input_text', 'output_text', 'text'} and isinstance(b.get('text'), str)]
                        phase = p.get('phase')
                    else:
                        if record.get('type') not in {'user', 'assistant'}: continue
                        if record.get('isMeta') or record.get('isCompactSummary'):
                            omissions['claude-internal-message'] += 1; continue
                        message = record.get('message', {}); role = message.get('role', record['type'])
                        if role not in {'user', 'assistant'}: continue
                        content = message.get('content', [])
                        texts = [content] if isinstance(content, str) else [b['text'] for b in content if b.get('type') == 'text' and isinstance(b.get('text'), str)]
                        time = record.get('timestamp'); native = record.get('uuid'); parent = record.get('parentUuid')
                        thread = record.get('sessionId') or path.stem; phase = None
                    if not time or not LOWER <= time <= upper: continue
                    recent += 1
                    assert thread
                    ingest(thread, platform, 'owner-openai-account' if platform == 'codex-local' else 'owner-claude-account',
                        role, native, time, texts, line, {'kind': 'local-native-record', 'file': str(path), 'start': start, 'end': offset}, parent, phase)
            scans.append({'path': str(path), 'fixed_size': limit, 'complete_line_end': offset, 'platform': platform, 'recent_visible_candidates': recent})

    for path in sorted(WORK.glob('remote-*.json')):
        projection = json.loads(path.read_bytes())
        for page in projection['pages']:
            thread = page['thread']['id']
            for turn in page['turns']:
                turn_time = datetime.fromtimestamp(turn['startedAt'], timezone.utc).isoformat().replace('+00:00', 'Z')
                if not LOWER <= turn_time <= upper: continue
                for item in turn['items']:
                    role = 'user' if item['type'] == 'userMessage' else 'assistant'
                    if item.get('phase') not in {None, 'commentary', 'final_answer'}: continue
                    texts = [item['text']] if 'text' in item else [b['text'] for b in item.get('content', []) if b.get('type') == 'text']
                    data = (json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
                    ingest(thread, 'codex-local', 'owner-openai-account', role, item['id'], None, texts, data,
                        {'kind': 'read-thread-visible-projection', 'thread': thread, 'turn': turn['id'], 'item': item['id'], 'file': str(path)},
                        phase=item.get('phase'), context={'turn_started_at': turn['startedAt'], 'turn_completed_at': turn.get('completedAt'),
                            'boundary': 'turn times are not exact message timestamps; native message time unavailable'})
    db.close()
    target_users = sorted((e for e in events if e['thread'] == TARGET and e['role'] == 'user'), key=lambda e: e['time'])
    for n, event in enumerate(target_users, 1): selected['PLAN-' + str(n).zfill(2)] = event
    current = [e for e in events if e['thread'] == CURRENT and e['text'].startswith('请将最近会话内容加入merkle个人知识库')]
    assert len(current) == 1
    selected['REQUEST'] = current[0]
    write_json(ARCHIVE / 'events.json', events)
    write_json(ARCHIVE / 'selected-sources.json', selected)
    capture = {'schema': 'mn/capture@1', 'captured_at': datetime.now(timezone.utc).isoformat(),
        'window_start': LOWER, 'window_end': upper, 'new_events': len(events),
        'new_by_platform': dict(collections.Counter(e['platform'] for e in events)),
        'new_by_thread': dict(collections.Counter(e['thread'] for e in events)),
        'new_by_role': dict(collections.Counter(e['role'] for e in events)),
        'native_records': sum(e['capture']['origin']['kind'] == 'local-native-record' for e in events),
        'remote_projection_records': sum(e['capture']['origin']['kind'] == 'read-thread-visible-projection' for e in events),
        'omissions': dict(omissions), 'scanned_files': scans,
        'coverage_limits': ['No new official Claude.ai, ChatGPT or Gemini bulk export requested in this pass.',
            'Mac raw filesystem unavailable through Remote Desktop Commander; two visible recent Codex threads read through app API.',
            'Only visible user and assistant text imported; system, developer, tools, hidden reasoning and injected envelopes excluded.',
            'Attachments are referenced in native records; this text import does not claim new attachment collection.']}
    write_json(ARCHIVE / 'capture.json', capture)
    text = '# 本轮作者原话与来源\n\n以下原话按本轮章节材料选取顺序列出；会话中转引他人的文字仍然保留，引用关系在正文选取时另行区分。\n\n'
    for ref, event in selected.items():
        text += f'## {ref} · {event["time"]}\n\n来源事件：`{event["occurrence"]}`。\n\n' + event['text'] + '\n\n'
    (OUT / '00-author-original.md').write_bytes(text.encode())
    print(json.dumps({k: capture[k] for k in ['window_start', 'window_end', 'new_events', 'new_by_platform', 'new_by_role', 'native_records', 'remote_projection_records', 'omissions']}, ensure_ascii=False))
    print(json.dumps([{'ref': k, 'time': v['time'], 'chars': len(v['text']), 'start': v['text'][:65]} for k, v in selected.items()], ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); prepare()
