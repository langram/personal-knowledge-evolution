"""Independent CARv1 verifier (Claude side; does not use contributions/codex/pkst_car.py).

Checks: header is canonical DAG-CBOR {roots, version:1}; every block re-hashes to its CID;
dag-cbor blocks decode canonically with the Claude decoder; every dag-cbor link resolves inside
the CAR; every raw link resolves to <raw_dir>/<CID>.bin and re-hashes; roots are present.

Usage: python -I verify_car_claude.py <file.car> <raw_dir> <report.json>
"""

import collections
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402


def read_cid(buf, i):
    start = i
    version, i = pc._read_uvarint(buf, i)
    codec, i = pc._read_uvarint(buf, i)
    mh, i = pc._read_uvarint(buf, i)
    ln, i = pc._read_uvarint(buf, i)
    i += ln
    if version != 1 or i > len(buf):
        raise pc.PkstError("bad CID in section")
    return pc.Link(buf[start:i]), i


def links(v):
    stack = [v]
    while stack:
        x = stack.pop()
        if isinstance(x, pc.Link):
            yield x
        elif isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)


def main(car_path, raw_dir, out):
    buf = open(car_path, "rb").read()
    hlen, i = pc._read_uvarint(buf, 0)
    header = pc.decode(buf[i:i + hlen])
    i += hlen
    if not (isinstance(header, dict) and header.get("version") == 1 and isinstance(header.get("roots"), list)):
        raise pc.PkstError("bad CARv1 header")
    blocks, errors = {}, collections.Counter()
    schemas = collections.Counter()
    decoded = {}
    dup = 0
    while i < len(buf):
        slen, j = pc._read_uvarint(buf, i)
        end = j + slen
        if end > len(buf):
            errors["truncated-section"] += 1
            break
        cid, k = read_cid(buf, j)
        data = buf[k:end]
        i = end
        codec = cid.binary[1]
        if pc.cid_for(data, codec) != cid:
            errors["hash-mismatch"] += 1
            continue
        if str(cid) in blocks:
            dup += 1
        blocks[str(cid)] = codec
        if codec == pc.CODEC_DAG_CBOR:
            try:
                v = pc.decode(data)
            except pc.PkstError as exc:
                errors["decode:%s" % exc] += 1
                continue
            decoded[str(cid)] = v
            schemas[v.get("schema", "<no schema>") if isinstance(v, dict) else "<non-map>"] += 1
            if isinstance(v, dict):
                try:
                    pc.check_sets(v)
                except pc.PkstError as exc:
                    errors["set:%s" % exc] += 1
    missing_obj = missing_raw = bad_raw = 0
    raw_checked = {}
    for v in decoded.values():
        for l in links(v):
            s = str(l)
            if l.binary[1] == pc.CODEC_DAG_CBOR:
                missing_obj += s not in blocks
            elif s not in blocks:
                if s not in raw_checked:
                    p = os.path.join(raw_dir, s + ".bin")
                    raw_checked[s] = os.path.exists(p) and pc.raw_cid(open(p, "rb").read()) == l
                missing_raw += not raw_checked[s]
    roots = [str(r) for r in header["roots"]]
    rep = {
        "ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "car": os.path.basename(car_path), "car_bytes": len(buf), "car_sha256": hashlib.sha256(buf).hexdigest(),
        "roots": roots, "roots_present": all(r in blocks for r in roots),
        "blocks": len(blocks), "duplicate_sections": dup, "dag_cbor_blocks": len(decoded),
        "raw_blocks_inside_car": sum(1 for c in blocks.values() if c == pc.CODEC_RAW),
        "objects_by_schema": dict(schemas), "errors": dict(errors),
        "dangling_object_links": missing_obj, "external_raw_links_checked": len(raw_checked),
        "external_raw_links_missing_or_bad": missing_raw,
    }
    rep["pass"] = (rep["roots_present"] and not errors and missing_obj == 0 and missing_raw == 0)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
