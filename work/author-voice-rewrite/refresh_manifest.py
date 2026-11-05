"""Refresh publication/files.json after the 2026-11-05 author-voice rewrite.

Keeps every path already in the manifest, adds the new edition's dossier and work files,
and recomputes the binary Merkle root with the same leaf scheme as pkst_public verify.
Run from the repository root: python work/author-voice-rewrite/refresh_manifest.py
"""
import datetime
import hashlib
import json
import os
import subprocess

old = json.load(open('publication/files.json', encoding='utf-8'))
oldpaths = set(i['path'] for i in old['files'])
tracked = set(subprocess.check_output(['git', 'ls-files'], text=True).split('\n')) - {''}
print('old', len(oldpaths), 'tracked', len(tracked))
print('old-not-tracked', sorted(oldpaths - tracked)[:5])
print('tracked-not-old', sorted(tracked - oldpaths)[:5])

new = []
for root in ('archive/dossiers/2026-11-05-author-voice-rewrite', 'work/author-voice-rewrite'):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f).replace(os.sep, '/')
            if '__pycache__' in p:
                continue
            new.append(p)

paths = sorted((oldpaths | set(new)) - {'publication/files.json'})
files = []
for p in paths:
    b = open(p, 'rb').read()
    files.append({'path': p, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()})
leaves = [hashlib.sha256(b'\x00' + i['path'].encode() + b'\x00' + bytes.fromhex(i['sha256'])).digest() for i in files]
while len(leaves) > 1:
    if len(leaves) % 2:
        leaves.append(leaves[-1])
    leaves = [hashlib.sha256(b'\x01' + leaves[i] + leaves[i + 1]).digest() for i in range(0, len(leaves), 2)]
man = {'schema': old['schema'], 'recorded_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'merkle_root': leaves[0].hex(), 'files': files}
for k, v in old.items():
    if k not in man:
        man[k] = v
json.dump(man, open('publication/files.json', 'w', encoding='utf-8', newline='\n'), indent=2, ensure_ascii=False)
print('files', len(files), 'added', len(set(paths) - oldpaths))
