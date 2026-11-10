"""Refresh publication/files.json so that it lists every file of the repository except itself.

The file set is what git tracks plus untracked files that are not ignored; the binary Merkle root
uses the same leaf scheme as `python -m pkst_public verify`.
Run from the repository root:  python work/focused-edition/refresh_manifest.py
"""
import datetime
import hashlib
import json
import os
import subprocess

old = json.load(open('publication/files.json', encoding='utf-8'))
oldpaths = set(i['path'] for i in old['files'])
listed = subprocess.check_output(
    ['git', '-c', 'core.quotepath=false', 'ls-files', '--cached', '--others', '--exclude-standard'],
    text=True, encoding='utf-8').split('\n')
paths = sorted(p for p in set(listed) - {'', 'publication/files.json'} if os.path.isfile(p))
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
print('files', len(files), 'added', len(set(paths) - oldpaths), 'removed', len(oldpaths - set(paths)))
