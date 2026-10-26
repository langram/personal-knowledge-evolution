"""Import captured Gemini activity evidence; no HTML execution or belief extraction."""
import argparse, hashlib, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from pkst_codec import cid, link, linkset, loads
from pkst_car import CarWriter, inspect_car

PARSER = 'gemini-takeout-json-pointer@0.1.0'
URL = re.compile(r'https://gemini\.google\.com/app/([A-Za-z0-9_-]+)')

def timestamp(value=None):
    match = re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.(\d+))?Z', value or '')
    digits = len(match.group(1) or '') if match else 0
    return dict(value=value, format='rfc3339' if match else 'unknown' if value is None else 'source-text',
                precision=('second' if digits == 0 else 'millisecond' if digits <= 3 else 'microsecond' if digits <= 6 else 'unknown') if match else 'unknown',
                zone_known=bool(match), unit=None)

def projection(value, kind):
    return dict(schema='pkst/projection@0.1', native_type=kind, profile='python-json-v1',
                text=json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))

def preserve(root, data):
    key = cid(data, 0x55); path = root / 'raw' / (key + '.bin')
    if path.exists():
        if path.read_bytes() != data: raise ValueError('Existing raw mismatch')
    else:
        with path.open('xb') as f: f.write(data)
    return key

def pointer(document, value):
    if value == '': return document
    if not value.startswith('/'): raise ValueError('Invalid JSON pointer')
    for part in value[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        document = document[int(part)] if isinstance(document, list) else document[part]
    return document

def convert(document, raw, member_name, members, put):
    if not isinstance(document, list): raise ValueError('Expected JSON array')
    roots = []; checks = []; counts = Counter(); gaps = []; source_ids = set(); attachment_refs = []
    by_name = {}
    for member in members:
        if member.get('status') == 'captured':
            by_name.setdefault(member['member_name'], set()).add(member['raw_cid'])
    parent = PurePosixPath(member_name).parent
    for i, row in enumerate(document):
        if not isinstance(row, dict) or row.get('header') != 'Gemini Apps' or not isinstance(row.get('title'), str):
            raise ValueError('Unrecognized Gemini activity at /' + str(i))
        record_pointer = '/' + str(i)
        ids = set()
        for detail in row.get('details', []):
            m = URL.fullmatch(detail.get('url', ''))
            if m: ids.add(m.group(1))
        native_thread = next(iter(ids)) if len(ids) == 1 else 'raw:' + raw + '#' + record_pointer
        if len(ids) == 1: source_ids.add(native_thread)
        else: gaps.append({'pointer':record_pointer, 'reason':'missing-or-ambiguous-conversation-id', 'ids':sorted(ids)})
        source = put(dict(schema='pkst/source@0.1', platform='gemini', namespace='owner-google-account', native_thread_id=native_thread))

        def emit(relative, obj, role, actor, time_value, basis):
            node_pointer = record_pointer + relative
            content = put(obj)
            locator = dict(raw=link(raw), coordinate='json-pointer', pointer=node_pointer)
            occurrence = put(dict(schema='pkst/occurrence@0.1', source=link(source), native_id=None,
                locator=locator, native_role=role, actor_kind=actor, process_kind='unknown',
                content=[link(content)], native_parent_ids=None, event_time=timestamp(time_value)))
            roots.append(put(dict(schema='pkst/extraction-record@0.1', raw=link(raw), occurrence=link(occurrence),
                coordinate='json-pointer', pointer=node_pointer, parser=PARSER, role_basis=basis)))
            roots.append(put(dict(schema='pkst/block-reference@0.1', raw=link(raw), occurrence=link(occurrence), ordinal=0,
                coordinate='json-pointer', document_pointer=record_pointer, pointer=relative, native_type=role)))
            checks.append({'occurrence':occurrence,'content':content,'pointer':node_pointer,'kind':role})
            counts[role] += 1
            return occurrence

        if row['title'].startswith('Prompted '):
            main = emit('/title', dict(schema='pkst/content@0.1', media_type='text/plain;charset=utf-8', text=row['title'][len('Prompted '):]),
                        'Prompted', 'unknown', row.get('time'), 'title: exact ASCII Prompted prefix removed; remaining characters unchanged; human authorship unverified')
        else:
            role = 'activity:' + row['title'].split(' ', 1)[0]
            main = emit('', projection(row, 'gemini-nonmessage-activity'), role, 'unknown', row.get('time'),
                        'Whole nonmessage activity projection; not treated as user speech')
        html_items = row.get('safeHtmlItem', [])
        if not isinstance(html_items, list): raise ValueError('safeHtmlItem must be an array')
        for j, item in enumerate(html_items):
            if not isinstance(item, dict) or set(item) != {'html'} or not isinstance(item['html'], str):
                raise ValueError('Unexpected safeHtmlItem shape')
            emit('/safeHtmlItem/' + str(j), projection(item, 'gemini-safeHtmlItem'), 'safeHtmlItem', 'ai', None,
                 'Exported response HTML, verified against same conversation UI; model and individual response time absent; order not assumed to be branches')
        refs = [('/attachedFiles/' + str(j), x) for j, x in enumerate(row.get('attachedFiles', []))]
        if 'imageFile' in row: refs.append(('/imageFile', row['imageFile']))
        refs.extend(('/subtitles/' + str(j) + '/url', s['url']) for j, s in enumerate(row.get('subtitles', [])) if 'url' in s)
        for field, name in refs:
            if not isinstance(name, str): raise ValueError('Attachment reference must be string')
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', name):
                counts['external-subtitle-url-not-fetched'] += 1
                continue
            member = str(parent / name)
            matches = by_name.get(member, set())
            status = 'resolved' if len(matches) == 1 else 'missing' if not matches else 'ambiguous'
            roots.append(put(dict(schema='pkst/gemini-attachment@0.1', occurrence=link(main), document_raw=link(raw),
                document_pointer=record_pointer, field_pointer=field, member_name=member,
                candidates=linkset(matches) if len(matches) == 1 else [], status=status)))
            attachment_refs.append({'pointer':record_pointer + field,'status':status,'member_name':member,'raw_candidates':sorted(matches)})
            counts['attachment:' + status] += 1
    return roots, checks, dict(counts), gaps, source_ids, attachment_refs

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--capture', required=True)
    ap.add_argument('--protocol', required=True); ap.add_argument('--profile', required=True); ap.add_argument('--output', required=True)
    args = ap.parse_args(); root = Path(args.root); output = Path(args.output)
    capture = loads(Path(args.capture).read_bytes())
    if capture['status'] != 'captured': raise ValueError('Capture incomplete')
    manifest_path = root / capture['manifest']; manifest_bytes = manifest_path.read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != capture['manifest_sha256']: raise ValueError('Manifest hash mismatch')
    members = [loads(line) for line in manifest_bytes.splitlines()]
    documents = [m for m in members if m['status'] == 'captured' and m['member_name'].endswith('.json')]
    if len(documents) != 1: raise ValueError('Expected exactly one activity JSON document; inspect new format')
    doc = documents[0]; raw = doc['raw_cid']; raw_bytes = (root / 'raw' / (raw + '.bin')).read_bytes()
    if cid(raw_bytes, 0x55) != raw: raise ValueError('Activity JSON hash mismatch')
    document = loads(raw_bytes)
    protocol = preserve(root, Path(args.protocol).read_bytes()); profile = preserve(root, Path(args.profile).read_bytes())
    implementation = preserve(root, Path(__file__).read_bytes()); manifest = preserve(root, manifest_bytes)
    writer = CarWriter(output)
    roots, checks, counts, gaps, source_ids, attachments = convert(document, raw, doc['member_name'], members, writer.put)
    raw_roots = set(m['raw_cid'] for m in members) | {capture['original']['raw_cid'], protocol, profile, implementation, manifest}
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    activity = writer.put(dict(schema='pkst/activity@0.1', operation='import', recorded_at=now, actor=dict(kind='ai', id='codex'),
        inputs=linkset([manifest, profile]), outputs=linkset(roots), implementation=link(implementation),
        coverage=dict(entries=len(document), counts=counts, native_conversation_ids=len(source_ids),
                      identity_gaps=gaps, python=sys.version.split()[0], semantic_extraction='not-performed')))
    snapshot = writer.put(dict(schema='pkst/snapshot@0.1', parents=[], roots=linkset([activity] + list(raw_roots)), protocol=link(protocol),
        coverage=dict(platform='gemini', source='one official Gemini Apps Takeout archive', adapter_profile=link(profile),
                      adapter_status='implemented-candidate-awaiting-independent-review', external_raw=True,
                      entry_time_min=min(r['time'] for r in document), entry_time_max=max(r['time'] for r in document),
                      response_times='unknown', missing_history='unknown; no complete-account claim')))
    envelope = writer.finish([snapshot], raw_roots)
    verified = inspect_car(output, root / 'raw', output.with_suffix('.index.sqlite'))
    check_path = root / '.private' / (output.stem + '.anchors.json')
    check_path.write_text(json.dumps({'document_raw':raw,'checks':checks,'attachments':attachments},ensure_ascii=False),encoding='utf-8')
    report = dict(schema='pkst.gemini-evidence-report@0.1', recorded_at=now, root=snapshot, protocol=protocol, profile=profile,
                  document_raw=raw, entries=len(document), native_conversation_ids=len(source_ids),
                  native_conversation_id_missing_or_ambiguous=len(gaps), counts=counts, envelope=envelope, verification=verified,
                  entry_time_min=min(r['time'] for r in document), entry_time_max=max(r['time'] for r in document),
                  anchors_manifest=str(check_path.relative_to(root)), semantic_extraction='not-performed',
                  limitations=['No native message IDs; capture-local JSON pointers','HTML is a projection, not native plain text',
                               'Response times, branches, deleted or unretained history unknown','Adapter independent review pending'])
    output.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
