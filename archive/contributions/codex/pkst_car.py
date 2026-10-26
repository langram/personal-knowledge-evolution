"""CARv1 envelope for PKST blocks; raw evidence may reside in a separate store."""
import base64,hashlib,json,shutil,sqlite3
from pathlib import Path
from pkst_codec import encode,decode,cid,cid_bytes,check_sets,links,linkset

def varint(n):
    if type(n) is not int or n<0:raise ValueError('Expected unsigned integer')
    out=bytearray()
    while n>=128:out.append((n&127)|128);n>>=7
    out.append(n);return bytes(out)

def read_varint(stream):
    n=0;shift=0;seen=bytearray()
    while True:
        b=stream.read(1)
        if not b:
            if not seen:return None
            raise ValueError('Truncated varint')
        seen.extend(b);n|=(b[0]&127)<<shift
        if b[0]<128:
            if bytes(seen)!=varint(n):raise ValueError('Nonminimal varint')
            return n
        shift+=7
        if shift>56:raise ValueError('Oversized varint')

class CarWriter:
    def __init__(self,path):
        self.path=Path(path);self.part=self.path.with_suffix('.blocks.part')
        if self.path.exists():raise FileExistsError(self.path)
        self.stream=self.part.open('xb',buffering=4*1024*1024)
        self.seen=set();self.references=set()
    def put(self,obj):
        check_sets(obj);data=encode(obj);key=cid(data)
        if key not in self.seen:
            section=cid_bytes(key)+data
            self.stream.write(varint(len(section)));self.stream.write(section)
            self.seen.add(key);self.references.update(links(obj))
        return key
    def finish(self,roots,external_raw):
        self.stream.close()
        missing=self.references-self.seen-set(external_raw)
        if missing:raise ValueError('Missing references: '+str(sorted(missing)[:5]))
        if not set(roots)<=self.seen:raise ValueError('Absent CAR root')
        header=encode({'version':1,'roots':linkset(roots)})
        with self.path.open('xb',buffering=4*1024*1024) as out,self.part.open('rb') as src:
            out.write(varint(len(header)));out.write(header);shutil.copyfileobj(src,out,4*1024*1024)
        self.part.unlink()  # Only this writer's completed staging file.
        return {'blocks':len(self.seen),'references':len(self.references),'external_raw':len(self.references-self.seen),'bytes':self.path.stat().st_size}

def inspect_car(path,raw_root,index_path=None):
    seen=set();references=set();schemas={}
    db=None
    if index_path:
        if Path(index_path).exists():raise FileExistsError(index_path)
        db=sqlite3.connect(index_path)
        db.execute('CREATE TABLE blocks(cid TEXT PRIMARY KEY,offset INTEGER,size INTEGER,schema TEXT)')
    with Path(path).open('rb') as f:
        n=read_varint(f)
        if n is None or n>1024*1024:raise ValueError('Invalid CAR header length')
        header=decode(f.read(n))
        if not isinstance(header,dict) or set(header)!={'version','roots'} or type(header['version']) is not int or header['version']!=1:raise ValueError('Invalid CAR header')
        roots=header['roots']
        if not isinstance(roots,list) or not roots or any(not isinstance(x,dict) or set(x)!={'$link'} for x in roots):raise ValueError('Invalid CAR roots')
        check_sets(header)
        while True:
            n=read_varint(f)
            if n is None:break
            if n<36 or n>256*1024*1024:raise ValueError('Invalid block length')
            offset=f.tell();section=f.read(n)
            if len(section)!=n:raise ValueError('Truncated CAR block')
            key='b'+base64.b32encode(section[:36]).decode().lower().rstrip('=')
            cid_bytes(key)
            if cid(section[36:])!=key:raise ValueError('CAR block hash mismatch')
            obj=decode(section[36:]);check_sets(obj)
            if key in seen:raise ValueError('Duplicate CAR block')
            seen.add(key);references.update(links(obj));schema=obj.get('schema','non-schema')
            schemas[schema]=schemas.get(schema,0)+1
            if db:db.execute('INSERT INTO blocks VALUES (?,?,?,?)',(key,offset+36,n-36,schema))
    if not set(links(header['roots']))<=seen:raise ValueError('Missing root block')
    external=references-seen
    for key in external:
        if cid_bytes(key)[1]!=0x55:raise ValueError('Missing structural block')
        h=hashlib.sha256()
        with (Path(raw_root)/(key+'.bin')).open('rb') as f:
            while b:=f.read(4*1024*1024):h.update(b)
        if h.digest()!=cid_bytes(key)[4:]:raise ValueError('Corrupt external raw block')
    if db:db.commit();db.close()
    return {'header':header,'blocks':len(seen),'external_raw_verified':len(external),'schemas':schemas,'status':'all-blocks-and-reference-closure-verified'}
