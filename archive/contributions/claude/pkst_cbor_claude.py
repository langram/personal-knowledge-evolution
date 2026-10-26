"""PKST-CBOR-1 independent reference codec (Claude side).

Written from protocol/PKST-0.1.md section 2 only; does not import or read
contributions/codex/pkst_codec.py. Standard library only. Run with `python -I`.

Value model (JSON projection -> Python):
  None, bool, int, str, list, dict[str, ...], Link
A JSON object {"$link": "b..."} with exactly that one key is a Link.
"""

import base64
import hashlib
import json

MAX_INT = 9007199254740991
CODEC_RAW = 0x55
CODEC_DAG_CBOR = 0x71
MH_SHA2_256 = 0x12


class PkstError(ValueError):
    pass


# ---------- varint / base32 / CID ----------

def _uvarint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _read_uvarint(buf, i):
    n = shift = 0
    start = i
    while True:
        if i >= len(buf):
            raise PkstError("truncated varint")
        b = buf[i]
        i += 1
        n |= (b & 0x7F) << shift
        if not b & 0x80:
            break
        shift += 7
        if shift > 63:
            raise PkstError("varint too long")
    if _uvarint(n) != buf[start:i]:
        raise PkstError("non-minimal varint")
    return n, i


def _b32(data):
    return base64.b32encode(data).decode("ascii").lower().rstrip("=")


def _unb32(text):
    if not text or text != text.lower() or any(c not in "abcdefghijklmnopqrstuvwxyz234567" for c in text):
        raise PkstError("bad base32 alphabet")
    try:
        data = base64.b32decode(text.upper() + "=" * (-len(text) % 8))
    except Exception as exc:  # binascii.Error
        raise PkstError("bad base32: %s" % exc)
    if _b32(data) != text:
        raise PkstError("non-canonical base32")
    return data


class Link:
    """A CIDv1 link; holds the binary CID (version, codec, multihash)."""

    __slots__ = ("binary",)

    def __init__(self, binary):
        _check_cid_binary(binary)
        self.binary = bytes(binary)

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str) or not text.startswith("b"):
            raise PkstError("CID must be multibase base32 ('b' prefix)")
        return cls(_unb32(text[1:]))

    def __str__(self):
        return "b" + _b32(self.binary)

    def __eq__(self, other):
        return isinstance(other, Link) and other.binary == self.binary

    def __hash__(self):
        return hash(self.binary)

    def __repr__(self):
        return "Link(%s)" % self


def _check_cid_binary(binary):
    version, i = _read_uvarint(binary, 0)
    if version != 1:
        raise PkstError("CID version must be 1")
    codec, i = _read_uvarint(binary, i)
    if codec not in (CODEC_RAW, CODEC_DAG_CBOR):
        raise PkstError("CID codec not allowed: 0x%x" % codec)
    mh, i = _read_uvarint(binary, i)
    if mh != MH_SHA2_256:
        raise PkstError("multihash must be sha2-256")
    ln, i = _read_uvarint(binary, i)
    if ln != 32 or len(binary) - i != 32:
        raise PkstError("sha2-256 digest must be 32 bytes")


def cid_for(data, codec):
    digest = hashlib.sha256(data).digest()
    return Link(_uvarint(1) + _uvarint(codec) + _uvarint(MH_SHA2_256) + _uvarint(32) + digest)


def raw_cid(data):
    return cid_for(data, CODEC_RAW)


# ---------- encoder ----------

def _head(major, n):
    if n < 24:
        return bytes([(major << 5) | n])
    for limit, ai, size in ((0xFF, 24, 1), (0xFFFF, 25, 2), (0xFFFFFFFF, 26, 4), (0xFFFFFFFFFFFFFFFF, 27, 8)):
        if n <= limit:
            return bytes([(major << 5) | ai]) + n.to_bytes(size, "big")
    raise PkstError("length/int too large")


def _check_str(s):
    for ch in s:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            raise PkstError("unpaired surrogate in string")
    return s.encode("utf-8")


def encode(value):
    out = bytearray()
    _enc(value, out)
    return bytes(out)


def _enc(v, out):
    if v is None:
        out.append(0xF6)
    elif v is True:
        out.append(0xF5)
    elif v is False:
        out.append(0xF4)
    elif isinstance(v, int):
        if not -MAX_INT <= v <= MAX_INT:
            raise PkstError("integer out of range")
        out += _head(0, v) if v >= 0 else _head(1, -1 - v)
    elif isinstance(v, float):
        raise PkstError("float not allowed")
    elif isinstance(v, str):
        b = _check_str(v)
        out += _head(3, len(b)) + b
    elif isinstance(v, Link):
        cid = b"\x00" + v.binary
        out += b"\xd8\x2a" + _head(2, len(cid)) + cid
    elif isinstance(v, list):
        out += _head(4, len(v))
        for x in v:
            _enc(x, out)
    elif isinstance(v, dict):
        items = []
        for k, x in v.items():
            if not isinstance(k, str):
                raise PkstError("map keys must be strings")
            items.append((_check_str(k), x))
        items.sort(key=lambda kv: (len(kv[0]), kv[0]))
        for a, b in zip(items, items[1:]):
            if a[0] == b[0]:
                raise PkstError("duplicate map key")
        out += _head(5, len(items))
        for kb, x in items:
            out += _head(3, len(kb)) + kb
            _enc(x, out)
    else:
        raise PkstError("unsupported type %s" % type(v).__name__)


def object_cid(value):
    data = encode(value)
    return data, cid_for(data, CODEC_DAG_CBOR)


# ---------- strict decoder (rejects anything encode() would not produce) ----------

def decode(data):
    v, i = _dec(data, 0, 0)
    if i != len(data):
        raise PkstError("trailing bytes")
    if encode(v) != data:
        raise PkstError("non-canonical encoding")
    return v


def _arg(data, i, ai):
    if ai < 24:
        return ai, i
    size = {24: 1, 25: 2, 26: 4, 27: 8}.get(ai)
    if size is None:
        raise PkstError("indefinite length / reserved additional info")
    if i + size > len(data):
        raise PkstError("truncated")
    return int.from_bytes(data[i:i + size], "big"), i + size


def _dec(data, i, depth):
    if depth > 256:
        raise PkstError("nesting too deep")
    if i >= len(data):
        raise PkstError("truncated")
    ib = data[i]
    i += 1
    major, ai = ib >> 5, ib & 0x1F
    if major == 7:
        if ai == 20:
            return False, i
        if ai == 21:
            return True, i
        if ai == 22:
            return None, i
        raise PkstError("simple/float value not allowed")
    n, i = _arg(data, i, ai)
    if major == 0:
        if n > MAX_INT:
            raise PkstError("integer out of range")
        return n, i
    if major == 1:
        if n + 1 > MAX_INT:
            raise PkstError("integer out of range")
        return -1 - n, i
    if major in (2, 3):
        if i + n > len(data):
            raise PkstError("truncated string")
        b = data[i:i + n]
        i += n
        if major == 2:
            raise PkstError("bare byte strings not allowed")
        try:
            return b.decode("utf-8"), i
        except UnicodeDecodeError:
            raise PkstError("invalid UTF-8")
    if major == 4:
        arr = []
        for _ in range(n):
            x, i = _dec(data, i, depth + 1)
            arr.append(x)
        return arr, i
    if major == 5:
        m = {}
        for _ in range(n):
            k, i = _dec(data, i, depth + 1)
            if not isinstance(k, str):
                raise PkstError("map key not a string")
            if k in m:
                raise PkstError("duplicate map key")
            m[k], i = _dec(data, i, depth + 1)
        return m, i
    if major == 6:
        if n != 42:
            raise PkstError("unknown tag %d" % n)
        if i >= len(data) or data[i] >> 5 != 2:
            raise PkstError("tag 42 must wrap bytes")
        ln, j = _arg(data, i + 1, data[i] & 0x1F)
        b = data[j:j + ln]
        if len(b) != ln or not b or b[0] != 0:
            raise PkstError("tag 42 bytes must start with 0x00")
        return Link(b[1:]), j + ln
    raise PkstError("unreachable")


# ---------- JSON projection ----------

def _no_dup(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise PkstError("duplicate JSON key %r" % k)
        seen[k] = v
    return seen


def _reject_const(name):
    raise PkstError("non-finite number %s" % name)


def loads_json(text):
    return from_projection(json.loads(text, object_pairs_hook=_no_dup,
                                      parse_float=lambda s: float(s), parse_constant=_reject_const))


def from_projection(v):
    if isinstance(v, dict):
        if "$link" in v:
            if len(v) != 1:
                raise PkstError("$link is reserved; map must have it as its only key")
            return Link.parse(v["$link"])
        return {k: from_projection(x) for k, x in v.items()}
    if isinstance(v, list):
        return [from_projection(x) for x in v]
    if isinstance(v, float):
        raise PkstError("float not allowed")
    return v


def to_projection(v):
    if isinstance(v, Link):
        return {"$link": str(v)}
    if isinstance(v, dict):
        return {k: to_projection(x) for k, x in v.items()}
    if isinstance(v, list):
        return [to_projection(x) for x in v]
    return v


# ---------- schema-level set-array check (section 2) ----------

SET_FIELDS = ("evidence", "roots", "inputs", "outputs", "members", "parents", "from_versions", "to_versions")


def check_sets(obj):
    """Reject unsorted or duplicated set arrays; never silently fixes."""
    if isinstance(obj, dict):
        for k, x in obj.items():
            if k in SET_FIELDS and isinstance(x, list):
                if not all(isinstance(e, Link) for e in x):
                    raise PkstError("set field %s must hold links" % k)
                bins = [e.binary for e in x]
                if bins != sorted(set(bins)):
                    raise PkstError("set field %s not sorted/unique by CID binary" % k)
            check_sets(x)
    elif isinstance(obj, list):
        for x in obj:
            check_sets(x)
