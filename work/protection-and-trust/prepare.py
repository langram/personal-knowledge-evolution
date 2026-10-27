"""Capture the author message without copying unrelated session internals."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'outputs/personal-thought-archive'
C = BASE / 'contributions/codex'
WORK = Path(__file__).resolve().parent
OUT = BASE / 'dossiers/2026-10-27-protection-and-trust'
ARCHIVE = C / 'protection-and-trust-20261027'
PRIOR = C / 'shared-credit-20261026'
OLD = BASE / 'dossiers/2026-10-26-shared-credit/02-new-principles.md'
PUBLIC = ROOT / 'publication/personal-knowledge-evolution'
sys.path.insert(0, str(C))
from pkst_codec import Store, cid, link

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())

def raw(data):
    key = cid(data, 0x55)
    path = ARCHIVE / 'raw' / (key + '.bin')
    if path.exists():
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    return key

def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / 'raw').mkdir(parents=True, exist_ok=True)
    if (ARCHIVE / 'request-capture.json').exists():
        print('Existing capture retained; inspect it before starting another import.')
        return
    pointer = json.loads((C / 'catalog/current.json').read_bytes())
    previous = json.loads((PRIOR / 'report.json').read_bytes())
    assert (PUBLIC / 'book/current.md').read_bytes() == OLD.read_bytes()
    baseline = {'pointer': pointer, 'document': previous['document'],
                'dossier_root': previous['snapshot'], 'concept': previous['concept'],
                'manuscript': str(OLD.relative_to(BASE)), 'sha256': sha(OLD.read_bytes())}
    write_json(ARCHIVE / 'baseline.json', baseline)
    native = Path('C:/Users/langr/.codex/sessions/2026/10/24/rollout-2026-10-24T14-13-28-01a16c8a-f6e1-7580-b378-b6e49f0be965.jsonl')
    matches = []
    with native.open('rb') as stream:
        while True:
            start = stream.tell()
            line = stream.readline()
            if not line or not line.endswith(b'\n'):
                break
            record = json.loads(line)
            payload = record.get('payload', {})
            if record.get('type') != 'response_item' or payload.get('role') != 'user':
                continue
            for index, block in enumerate(payload.get('content', [])):
                text = block.get('text', '')
                if block.get('type') == 'input_text' and text.startswith('前面说的都是新机制如何对人类社会中的正面发展的促进作用') and text.rstrip().endswith('请你将这部分内容整理一下，添加到文章合适的位置。'):
                    matches.append((start, line, record, index, text))
    assert len(matches) == 1, len(matches)
    offset, line, record, index, text = matches[0]
    store = Store(ARCHIVE)
    rawkey = raw(line)
    source = store.put({'schema': 'pkst/source@0.1', 'platform': 'codex-local',
        'namespace': 'owner-openai-account', 'native_thread_id': '01a16c8a-f6e1-7580-b378-b6e49f0be965'})
    content = store.put({'schema': 'pkst/content@0.1', 'media_type': 'text/plain;charset=utf-8', 'text': text})
    time = {'value': record['timestamp'], 'format': 'rfc3339', 'precision': 'millisecond', 'zone_known': True, 'unit': None}
    occurrence = store.put({'schema': 'pkst/occurrence@0.1', 'source': link(source),
        'native_id': record['payload'].get('id'),
        'locator': {'raw': link(rawkey), 'start': 0, 'end': len(line), 'coordinate': 'decoded-jsonl-utf8-bytes'},
        'native_role': 'user', 'actor_kind': 'human', 'process_kind': 'main', 'content': [link(content)],
        'native_parent_ids': None, 'event_time': time})
    anchor = store.put({'schema': 'pkst/extraction-record@0.1', 'raw': link(rawkey), 'occurrence': link(occurrence),
        'coordinate': 'decoded-jsonl-utf8-bytes', 'start': 0, 'end': len(line),
        'pointer': '/payload/content/' + str(index) + '/text', 'parser': 'protection-trust-native-message-v1',
        'role_basis': 'native user message and explicit author editorial request'})
    request = {'ref': 'PROTECTION-REQUEST', 'source': source, 'occurrence': occurrence, 'content': content,
        'anchors': [anchor], 'role': 'user', 'platform': 'codex-local',
        'thread': '01a16c8a-f6e1-7580-b378-b6e49f0be965', 'time': record['timestamp'],
        'time_format': 'rfc3339', 'native_event_time': time, 'text': text, 'text_sha256': sha(text.encode()),
        'capture': {'native_file': str(native), 'native_start': offset, 'native_end': offset + len(line),
            'raw': rawkey, 'bytes': len(line), 'sha256': sha(line), 'captured_at': datetime.now(timezone.utc).isoformat(),
            'scope': 'exact single user record; unrelated session internals not copied'}}
    write_json(ARCHIVE / 'request-capture.json', request)
    (OUT / '00-author-original.txt').write_bytes(text.encode())
    print(json.dumps({'time': request['time'], 'characters': len(text),
                      'paragraphs': [{'n': i, 'start': p[:80], 'chars': len(p)} for i, p in enumerate(text.split('\n\n'))]}, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    prepare()
