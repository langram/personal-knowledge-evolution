"""FILE-TEXT 0.1: Mac Claude Code auto-memory Markdown -> PKST objects; new Mac supplement root.

Usage: python -I convert_file_text.py <contributions/claude dir> <mac capture manifest.jsonl>
       <protocol/PKST-0.1.md> <FILE-TEXT-0.1.md> <parent supplement snapshot CID>
"""

import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import claude_import_n3 as ci  # noqa: E402

PARSER = "file-text@0.1"
COORD = "file-bytes"
ROLE = "derived-memory:claude-code"
UNKNOWN_TIME = {"value": None, "format": "unknown", "precision": "unknown", "zone_known": False, "unit": None}


def file_objects(raw_bytes, raw_link, archive_path, rules_cid):
    """Return (objects list, error). Strict UTF-8; no occurrence on failure."""
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        return [], "invalid-utf8 at byte %d" % exc.start
    start, end = 0, len(raw_bytes)
    assert isinstance(start, int) and isinstance(end, int) and 0 <= start <= end == len(raw_bytes)
    src = {"schema": "pkst/source@0.1", "platform": "claude-code-memory", "namespace": "owner-claude-account",
           "native_thread_id": "raw:%s" % raw_link}
    content = {"schema": "pkst/content@0.1", "media_type": ci.TEXT, "text": text}
    return [src, content], None


def main(base, manifest_path, protocol_path, rules_path, parent_snapshot):
    now = datetime.datetime.now(datetime.timezone.utc)
    run = now.strftime("%Y%m%dT%H%M%SZ")
    recorded_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_dir = os.path.join(base, "raw")
    obj_dir = os.path.join(base, "objects")

    def store_raw(data):
        cid = pc.raw_cid(data)
        p = os.path.join(raw_dir, str(cid) + ".bin")
        if not os.path.exists(p):
            open(p, "wb").write(data)
        return cid

    def load_obj(c):
        data = open(os.path.join(obj_dir, c + ".cbor"), "rb").read()
        if str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != c:
            raise pc.PkstError("stored object corrupted " + c)
        return pc.decode(data), data

    proto_cid = store_raw(open(protocol_path, "rb").read())
    rules_cid = store_raw(open(rules_path, "rb").read())
    rows = [json.loads(l) for l in open(manifest_path, encoding="utf-8")][1:]
    mem_rows = [r for r in rows if r["category"] == "claude-code-project-memory"]
    implementation = {"adapter": PARSER, "rules": rules_cid,
                      "convert_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                      "codec_sha256": hashlib.sha256(open(os.path.join(base, "pkst_cbor_claude.py"), "rb").read()).hexdigest(),
                      "python": sys.version.split()[0]}
    store = ci.Store()
    acts, report = [], {"files": len(mem_rows), "occurrences": 0, "invalid_utf8": [], "bom": 0, "crlf": 0,
                        "shared_raw": 0}
    seen_raw = {}
    for r in mem_rows:
        raw = pc.Link.parse(r["cid"])
        b = open(os.path.join(raw_dir, r["cid"] + ".bin"), "rb").read()
        if pc.raw_cid(b) != raw or hashlib.sha256(b).hexdigest() != r["sha256"] or len(b) != r["bytes"]:
            raise pc.PkstError("raw mismatch " + r["archive_path"])
        objs, err = file_objects(b, raw, r["archive_path"], rules_cid)
        outputs = []
        cov = {"host": "macbook", "archive_path": r["archive_path"], "mac_source_path": r["mac_source_path"],
               "mac_mtime_ns": r["mac_mtime_ns"], "bytes": len(b), "sha256": r["sha256"],
               "use": "derived memory written by the agent; not user speech; not a conversation message"}
        if err:
            report["invalid_utf8"].append(r["archive_path"])
            cov.update({"status": "raw-only", "reason": err})
        else:
            report["shared_raw"] += r["cid"] in seen_raw
            seen_raw[r["cid"]] = r["archive_path"]
            src, content = (store.put(o) for o in objs)
            occ = store.put({"schema": "pkst/occurrence@0.1", "source": src, "native_id": None,
                             "locator": {"raw": raw, "coordinate": COORD, "start": 0, "end": len(b)},
                             "native_role": ROLE, "actor_kind": "unknown", "process_kind": "unknown",
                             "content": [content], "native_parent_ids": None, "event_time": dict(UNKNOWN_TIME)})
            er = store.put({"schema": "pkst/extraction-record@0.1", "raw": raw, "occurrence": occ, "coordinate": COORD,
                            "start": 0, "end": len(b), "parser": PARSER,
                            "role_basis": "Mac supplement auto-memory directory; archive_path=%s; rules=%s; "
                                          "derived memory, not user speech" % (r["archive_path"], rules_cid)})
            outputs = [src, content, occ, er]
            report["occurrences"] += 1
            report["bom"] += objs[1]["text"].startswith("﻿")
            report["crlf"] += "\r\n" in objs[1]["text"]
            cov.update({"status": "parsed"})
        uniq = {l.binary: l for l in outputs}
        acts.append(store.put({"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at,
                               "actor": {"kind": "ai", "id": "claude"}, "inputs": [raw],
                               "outputs": [uniq[k] for k in sorted(uniq)], "implementation": implementation,
                               "coverage": cov}))
    parent, _ = load_obj(parent_snapshot)
    roots = {l.binary: l for l in list(parent["roots"]) + acts}
    cov = dict(parent["coverage"])
    cov.update({"occurrences": report["occurrences"], "file_text_rules": rules_cid,
                "gaps": [g for g in parent["coverage"]["gaps"] if not g.startswith("auto-memory")] +
                        ["auto-memory event times unknown by rule (mtime kept as provenance only)"]})
    snap = {"schema": "pkst/snapshot@0.1", "parents": [pc.Link.parse(parent_snapshot)],
            "roots": [roots[k] for k in sorted(roots)], "protocol": proto_cid, "coverage": cov}
    scid = store.put(snap)
    written = 0
    for c, (v, data) in store.objects.items():
        p = os.path.join(obj_dir, c + ".cbor")
        if not os.path.exists(p):
            open(p, "wb").write(data)
            written += 1
    # CAR: current root closure plus the parent snapshot block (its own closure is already in mac-claude-supplement.car)
    def get(c):
        return store.objects[c] if c in store.objects else load_obj(c)
    order, seen, stack = [], set(), [str(scid)]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        order.append(c)
        v, _ = get(c)
        for l in pc_links(v):
            if l.binary[1] == pc.CODEC_DAG_CBOR:
                stack.append(str(l))
    header = pc.encode({"roots": [scid], "version": 1})
    car_path = os.path.join(base, ".private", "mac-claude-supplement-file-text.car")
    with open(car_path, "wb") as f:
        f.write(pc._uvarint(len(header)) + header)
        for c in order:
            data = get(c)[1]
            cb = pc.Link.parse(c).binary
            f.write(pc._uvarint(len(cb) + len(data)) + cb + data)
    summary = {"run": run, "recorded_at": recorded_at, "snapshot": str(scid), "parent": parent_snapshot,
               "protocol_raw_cid": str(proto_cid), "rules_raw_cid": str(rules_cid), "report": report,
               "new_activities": len(acts), "roots": len(snap["roots"]), "objects_this_run": len(store.objects),
               "written_this_run": written, "car": "contributions/claude/.private/mac-claude-supplement-file-text.car",
               "car_sha256": hashlib.sha256(open(car_path, "rb").read()).hexdigest(), "car_blocks": len(order),
               "implementation": {k: str(v) for k, v in implementation.items()}}
    with open(os.path.join(base, "file-text-conversion-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def pc_links(v):
    if isinstance(v, pc.Link):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from pc_links(x)
    elif isinstance(v, list):
        for x in v:
            yield from pc_links(x)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:6]))
