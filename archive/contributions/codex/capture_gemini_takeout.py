"""Preserve an official Takeout ZIP and its members without extracting ZIP paths.

Member names are metadata only. All on-disk names are raw CIDs. This captures
evidence, not claims that every Gemini conversation or branch was exported.
"""
import argparse,hashlib,json,os,shutil,sys,uuid,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from pkst_codec import cid_bytes
import base64

CHUNK=4*1024*1024
RESERVE=3*1024**3

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while b:=f.read(CHUNK):h.update(b)
    return h.digest()

def capture_stream(stream,root,expected_size):
    part=root/'staging'/(uuid.uuid4().hex+'.part');h=hashlib.sha256();size=0
    with part.open('xb',buffering=CHUNK) as out:
        while b:=stream.read(CHUNK):
            size+=len(b)
            if size>expected_size:raise ValueError('Stream exceeds declared size')
            out.write(b);h.update(b)
    if size!=expected_size:raise ValueError('Stream size differs from declared size')
    key='b'+base64.b32encode(b'\x01\x55\x12\x20'+h.digest()).decode().lower().rstrip('=')
    target=root/'raw'/(key+'.bin')
    if digest(part)!=h.digest():raise ValueError('Destination hash mismatch')
    if target.exists():
        if digest(target)!=h.digest():raise ValueError('Existing raw block corrupt')
        part.unlink() # Only this invocation's verified duplicate staging file.
    else:part.rename(target)
    return {'raw_cid':key,'sha256':h.hexdigest(),'bytes':size}

def capture(archive,root,max_expanded=10*1024**3,*,platform='gemini',namespace='owner-google-account',archive_format='official-google-takeout-zip',report_schema='pkst.gemini-takeout-capture@0.1'):
    archive=Path(archive).resolve();root=Path(root).resolve()
    if archive.suffix.lower()!='.zip':raise ValueError('Expected completed .zip archive')
    for name in ('raw','staging','.private'): (root/name).mkdir(parents=True,exist_ok=True)
    before=archive.stat()
    if shutil.disk_usage(root).free<before.st_size+RESERVE:raise OSError('Insufficient free space reserve')
    run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex[:8]
    with archive.open('rb') as f:original=capture_stream(f,root,before.st_size)
    after=archive.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or digest(archive).hex()!=original['sha256']:
        raise ValueError('Source changed during capture; copied raw retained, not promoted')
    source=root/'raw'/(original['raw_cid']+'.bin')
    rows=[];failures=[];directories=0
    manifest=root/'.private'/('members-'+run+'.jsonl')
    with zipfile.ZipFile(source) as z,manifest.open('x',encoding='utf-8',newline='\n') as ledger:
        infos=z.infolist();expanded=sum(i.file_size for i in infos if not i.is_dir())
        if expanded>max_expanded:raise ValueError('Archive exceeds explicit expanded-size budget')
        if shutil.disk_usage(root).free<expanded+RESERVE:raise OSError('Insufficient space for members and reserve')
        for ordinal,info in enumerate(infos):
            if info.is_dir():directories+=1;continue
            normalized=info.filename.replace('\\','/')
            parts=PurePosixPath(normalized).parts
            row={'archive':original['raw_cid'],'ordinal':ordinal,'member_name':info.filename,
                 'declared_bytes':info.file_size,'compressed_bytes':info.compress_size,'zip_crc32':format(info.CRC,'08x'),
                 'archive_path_not_used_on_filesystem':True,
                 'nonportable_name':normalized.startswith('/') or '..' in parts or ':' in normalized,
                 'zip_local_time_unzoned':list(info.date_time)}
            try:
                if info.flag_bits&1:raise ValueError('Encrypted member; no decryption attempted')
                with z.open(info) as f:row.update(capture_stream(f,root,info.file_size))
                row['status']='captured'
            except (OSError,ValueError,RuntimeError,zipfile.BadZipFile) as exc:
                row.update(status='failed',error_type=type(exc).__name__,error=str(exc))
                failures.append({'ordinal':ordinal,'error_type':type(exc).__name__,'error':str(exc)})
            ledger.write(json.dumps(row,ensure_ascii=False)+'\n');ledger.flush();rows.append(row)
    report={'schema':report_schema,'recorded_at':datetime.now(timezone.utc).isoformat(),
        'platform':platform,'namespace':namespace,'format':archive_format,
        'original':original,'member_count':len(rows),'directory_entries':directories,
        'captured_members':sum(r['status']=='captured' for r in rows),'failures':failures,
        'declared_expanded_bytes':expanded,'manifest':str(manifest.relative_to(root)),
        'manifest_sha256':digest(manifest).hex(),'status':'captured' if not failures else 'partial',
        'implementation_sha256':digest(__file__).hex(),
        'limitations':['Capture does not prove complete account history','No semantic extraction performed',
                      'ZIP member timestamps lack a source timezone; they are not conversation timestamps']}
    path=root/('capture-summary-'+run+'.json')
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--root',required=True)
    a=p.parse_args();print(json.dumps(capture(a.archive,a.root),ensure_ascii=False,indent=2))
