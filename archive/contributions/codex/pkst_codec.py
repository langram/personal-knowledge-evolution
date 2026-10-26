"""PKST-CBOR-1: narrow deterministic DAG-CBOR and CIDv1, no dependencies.

JSON views use a reserved single-key {$link: cid} object for a CID link.
All other values are encoded directly; no Unicode/whitespace normalization.
"""
import base64
import hashlib
import json
from pathlib import Path

MAX_INT = 9007199254740991
SET_FIELDS = {'evidence','roots','inputs','outputs','members','parents','from_versions','to_versions'}

def cid_bytes(value):
    if not isinstance(value,str) or not value.startswith('b') or value != value.lower():
        raise ValueError('CID must use lowercase base32')
    text=value[1:]
    raw=base64.b32decode(text.upper()+'='*((-len(text))%8))
    if len(raw)!=36 or raw[:1]!=b'\x01' or raw[1] not in (0x55,0x71) or raw[2:4]!=b'\x12\x20':
        raise ValueError('Unsupported CID profile')
    if 'b'+base64.b32encode(raw).decode().lower().rstrip('=')!=value:
        raise ValueError('Noncanonical CID')
    return raw

def cid(data, codec=0x71):
    if codec not in (0x55,0x71): raise ValueError('Unsupported codec')
    return 'b'+base64.b32encode(bytes([1,codec,0x12,0x20])+hashlib.sha256(data).digest()).decode().lower().rstrip('=')

def head(major,n):
    prefix=major<<5
    if n<24:return bytes([prefix+n])
    for add,width in ((24,1),(25,2),(26,4),(27,8)):
        if n < 1<<(width*8):return bytes([prefix+add])+n.to_bytes(width,'big')
    raise ValueError('length out of range')

def encode(value):
    if value is None:return b'\xf6'
    if value is False:return b'\xf4'
    if value is True:return b'\xf5'
    if type(value) is int:
        if not -MAX_INT<=value<=MAX_INT:raise ValueError('integer out of range')
        return head(0,value) if value>=0 else head(1,-1-value)
    if isinstance(value,str):
        data=value.encode('utf-8',errors='strict')
        return head(3,len(data))+data
    if isinstance(value,list):return head(4,len(value))+b''.join(encode(x) for x in value)
    if isinstance(value,dict):
        if '$link' in value:
            if set(value)!={'$link'}:raise ValueError('Reserved $link map')
            raw=b'\x00'+cid_bytes(value['$link'])
            return b'\xd8\x2a'+head(2,len(raw))+raw
        if any(not isinstance(k,str) for k in value):raise ValueError('Map keys must be strings')
        keys=sorted(value,key=lambda k:(len(k.encode('utf-8')),k.encode('utf-8')))
        return head(5,len(keys))+b''.join(encode(k)+encode(value[k]) for k in keys)
    raise ValueError('Unsupported value type: '+type(value).__name__)

def link(value):
    cid_bytes(value)
    return {'$link':value}

def linkset(values):
    return [link(c) for c in sorted(set(values),key=cid_bytes)]

def links(value):
    if isinstance(value,dict):
        if set(value)=={'$link'}:yield value['$link']
        else:
            for v in value.values():yield from links(v)
    elif isinstance(value,list):
        for v in value:yield from links(v)

def check_sets(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in SET_FIELDS and isinstance(v,list):
                cs=[x['$link'] for x in v]
                if v!=linkset(cs):raise ValueError('Noncanonical set: '+k)
            check_sets(v)
    elif isinstance(value,list):
        for v in value:check_sets(v)

def pairs(values):
    obj={}
    for k,v in values:
        if k in obj:raise ValueError('Duplicate map key: '+k)
        obj[k]=v
    return obj

def loads(text):
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))

def decode(data):
    """Strict PKST-CBOR-1 decoder; reject nonminimal and noncanonical bytes."""
    pos=0
    def take(n):
        nonlocal pos
        if pos+n>len(data):raise ValueError('Truncated CBOR')
        b=data[pos:pos+n];pos+=n;return b
    def read():
        initial=take(1)[0];major=initial>>5;small=initial&31
        if major==7:
            if small in (20,21,22):return {20:False,21:True,22:None}[small]
            raise ValueError('Unsupported simple/float value')
        if small<24:n=small
        elif small in (24,25,26,27):n=int.from_bytes(take({24:1,25:2,26:4,27:8}[small]),'big')
        else:raise ValueError('Indefinite/reserved length')
        if major in (0,1):
            value=n if major==0 else -1-n
            if not -MAX_INT<=value<=MAX_INT:raise ValueError('Integer out of range')
            return value
        if major==3:return take(n).decode('utf-8',errors='strict')
        if major==4:return [read() for _ in range(n)]
        if major==5:
            obj={}
            for _ in range(n):
                key=read()
                if not isinstance(key,str) or key in obj:raise ValueError('Invalid/duplicate key')
                obj[key]=read()
            return obj
        if major==6 and n==42:
            # This profile only permits 36-byte CIDv1 values, plus the identity prefix.
            if take(2)!=b'\x58\x25' or take(1)!=b'\x00':raise ValueError('Invalid CID link')
            raw=take(36)
            value='b'+base64.b32encode(raw).decode().lower().rstrip('=')
            return link(value)
        raise ValueError('Unsupported CBOR type/tag')
    obj=read()
    if pos!=len(data) or encode(obj)!=data:raise ValueError('Noncanonical/trailing CBOR bytes')
    return obj

class Store:
    def __init__(self,root):
        self.root=Path(root); self.objects=self.root/'objects';self.objects.mkdir(parents=True,exist_ok=True)
        self.created=0;self.reused=0
    def put(self,obj):
        check_sets(obj)
        data=encode(obj); key=cid(data);p=self.objects/(key+'.cbor')
        if p.exists():
            if p.read_bytes()!=data:raise ValueError('Content address collision/corruption')
            self.reused+=1
        else:
            with p.open('xb') as f:f.write(data)
            self.created+=1
        view=self.objects/(key+'.json')
        if not view.exists():
            with view.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
        elif encode(loads(view.read_text(encoding='utf-8')))!=data:raise ValueError('Projection mismatch')
        return key
    def get(self,key):
        cid_bytes(key)
        data=(self.objects/(key+'.cbor')).read_bytes()
        if cid(data)!=key:raise ValueError('Corrupt block')
        obj=decode(data)
        view=self.objects/(key+'.json')
        if view.exists() and encode(loads(view.read_text(encoding='utf-8')))!=data:raise ValueError('Projection mismatch')
        check_sets(obj)
        return obj
