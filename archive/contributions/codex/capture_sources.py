"""Read-only source capture; bounded prefixes, exact raw CIDs, explicit failures."""
import argparse, base64, hashlib, json, os, shutil, time, uuid
from datetime import datetime, timezone
from pathlib import Path

CHUNK = 4 * 1024 * 1024

def now():
    return datetime.now(timezone.utc).isoformat()

def digest_prefix(path, size):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while size:
            chunk = f.read(min(CHUNK, size))
            if not chunk:
                raise EOFError('Source shortened while hashing')
            size -= len(chunk)
            h.update(chunk)
    return h.digest()

def raw_cid(digest):
    return 'b' + base64.b32encode(b'\x01\x55\x12\x20' + digest).decode().lower().rstrip('=')

def capture(path, dest, ordinal):
    start = now()
    before = path.stat()
    size = before.st_size
    temporary = dest / 'staging' / (str(ordinal) + '.part')
    h = hashlib.sha256()
    remaining = size
    last = b''
    with path.open('rb') as src, temporary.open('xb') as out:
        while remaining:
            chunk = src.read(min(CHUNK, remaining))
            if not chunk:
                raise EOFError('Source shortened during capture')
            out.write(chunk)
            h.update(chunk)
            last = chunk[-1:]
            remaining -= len(chunk)
        out.flush()
        os.fsync(out.fileno())
    digest = h.digest()
    if digest_prefix(temporary, size) != digest:
        raise ValueError('Destination digest mismatch')
    after = path.stat()
    # Appending is allowed. Rewriting the captured prefix is reported, never hidden.
    source_verified = digest_prefix(path, size) == digest
    key = raw_cid(digest)
    target = dest / 'raw' / (key + '.bin')
    reused = target.exists()
    if reused:
        if target.stat().st_size != size or digest_prefix(target, size) != digest:
            raise ValueError('Existing content-addressed raw blob is corrupt')
        temporary.unlink()  # Only this run's verified duplicate staging file.
    else:
        temporary.rename(target)
    changed = before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
    return {'path': str(path), 'raw_cid': key, 'sha256': digest.hex(), 'size': size,
            'source_suffix': ''.join(path.suffixes), 'started_at': start, 'completed_at': now(),
            'mtime_ns_before': before.st_mtime_ns, 'mtime_ns_after': after.st_mtime_ns,
            'size_after': after.st_size, 'source_changed': changed,
            'source_prefix_verified': source_verified, 'reused': reused,
            'capture_kind': 'fixed-prefix',
            'partial_tail': (size > 0 and last != b'\n') if path.suffix == '.jsonl' else None,
            'status': 'captured' if source_verified and (path.suffix != '.zst' or not changed) else 'unstable'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', action='append', required=True)
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    base = Path(args.dest).resolve()
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    dest = base
    (dest / 'raw').mkdir(parents=True, exist_ok=True)
    (dest / 'staging').mkdir(exist_ok=True)
    (dest / '.private').mkdir(exist_ok=True)
    paths = sorted({p.resolve() for root in args.root for p in Path(root).rglob('*')
                    if p.is_file() and (p.name.endswith('.jsonl') or p.name.endswith('.jsonl.zst'))})
    total = sum(p.stat().st_size for p in paths)
    if shutil.disk_usage(dest).free < total + 3 * 1024**3:
        raise OSError('Capture would leave less than 3 GiB free')
    manifest = dest / '.private' / ('capture-' + run + '.jsonl')
    t = time.monotonic()
    counts = {'captured': 0, 'unstable': 0, 'failed': 0}
    copied = 0
    # Every staging filename contains the unique run ID.
    with manifest.open('x', encoding='utf-8', newline='\n') as out:
        for ordinal, path in enumerate(paths):
            try:
                row = capture(path, dest, run + '-' + str(ordinal))
                copied += row['size']
            except (OSError, EOFError, ValueError) as exc:
                row = {'path': str(path), 'status': 'failed', 'error_type': type(exc).__name__,
                       'error': str(exc), 'observed_at': now()}
            counts[row['status']] += 1
            out.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
            out.flush()
            if (ordinal + 1) % 200 == 0:
                print(json.dumps({'processed': ordinal + 1, 'of': len(paths), 'counts': counts}), flush=True)
    summary = {'run': run, 'roots': args.root, 'files': len(paths), 'captured_bytes': copied,
               'counts': counts, 'elapsed_seconds': round(time.monotonic() - t, 3),
               'manifest': str(manifest), 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
               'completed_at': now(), 'scope': 'existing JSONL and Zstandard JSONL files only; no database-only messages or attachments'}
    report = dest / ('capture-summary-' + run + '.json')
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
