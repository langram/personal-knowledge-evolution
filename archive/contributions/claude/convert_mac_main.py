"""Mac Claude main package (Claude Code JSONL + history) -> PKST 0.1 (N3.1 importer), independent snapshot + CAR.

Same importer and identity rules as Windows (namespace owner-claude-account; source = sessionId), so a
session present on both hosts yields identical occurrence CIDs. Host/path/mtime live only in activity provenance.

Usage: python -I convert_mac_main.py <contributions/claude dir> <mac main capture manifest.jsonl> <protocol/PKST-0.1.md>
"""

import collections
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import claude_import_n3 as ci  # noqa: E402

RELATED = {"mac_supplement_root": "bafyreifpdpydzayyey7lzwztdruiyo3wu6uq6z5nkmvt7ip2cslircitwu",
           "windows_claude_code_root": "bafyreianxmej6c3xojir3it6bf2sjxido6b6fcvbo2l5nwmf2ra2rcxzne"}


def sorted_links(links):
    uniq = {l.binary: l for l in links}
    return [uniq[b] for b in sorted(uniq)]


def main(base, manifest_path, protocol_path):
    now = datetime.datetime.now(datetime.timezone.utc)
    run = now.strftime("%Y%m%dT%H%M%SZ")
    recorded_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_dir = os.path.join(base, "raw")
    obj_dir = os.path.join(base, "objects")
    proto = open(protocol_path, "rb").read()
    proto_cid = pc.raw_cid(proto)
    if str(proto_cid) != "bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq":
        raise pc.PkstError("protocol bytes differ from the frozen CID")
    rows = [json.loads(l) for l in open(manifest_path, encoding="utf-8")]
    implementation = ("claude_import_n3.py@sha256:%s;pkst_cbor_claude.py@sha256:%s;convert_mac_main.py@sha256:%s;python-%s;profile=%s" % (
        hashlib.sha256(open(os.path.join(base, "claude_import_n3.py"), "rb").read()).hexdigest(),
        hashlib.sha256(open(os.path.join(base, "pkst_cbor_claude.py"), "rb").read()).hexdigest(),
        hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), sys.version.split()[0], ci.PROFILE))
    store = ci.Store()
    acts = []
    totals = collections.Counter()
    nonocc = collections.Counter()
    preexisting_occ = 0
    occ_seen = set()
    zero_occ = []
    for r in rows:
        raw = pc.Link.parse(r["cid"])
        data = open(os.path.join(raw_dir, r["cid"] + ".bin"), "rb").read()
        if pc.raw_cid(data) != raw:
            raise pc.PkstError("raw corrupted " + r["cid"])
        fn = ci.import_history if r["kind"] == "claude-code-prompt-history" else ci.import_transcript
        imp = fn(data, raw, ci.Store())
        rep = imp["report"]
        outs = []
        for c, (v, enc) in imp["store"].objects.items():
            if v["schema"] == "pkst/occurrence@0.1" and c not in occ_seen:
                occ_seen.add(c)
                preexisting_occ += os.path.exists(os.path.join(obj_dir, c + ".cbor"))
            store.objects[c] = (v, enc)
            outs.append(pc.Link.parse(c))
        for k in ("lines", "occurrences", "missing_native_id", "dangling_parent_ids", "missing_paste_content"):
            totals[k] += rep.get(k, 0)
        totals["parse_errors"] += len(rep["parse_errors"])
        totals["partial_tails"] += bool(rep["partial_tail"])
        totals["absent_parent_field"] += rep.get("absent_parent_field", 0)
        nonocc.update(rep["non_occurrence_records"])
        if rep["occurrences"] == 0:
            zero_occ.append(r["source_path"])
        cov = {"host": "macbook", "raw_kind": r["kind"], "source_group": r["source_group"], "source_path": r["source_path"],
               "mac_mtime_ns": r["mac_mtime_ns"], "bytes": len(data),
               "status": "parsed" if not rep["parse_errors"] and not rep["partial_tail"] else "partial",
               "parser": ci.HISTORY_PARSER if fn is ci.import_history else ci.PARSER,
               "lines": rep["lines"], "occurrences": rep["occurrences"], "parse_errors": rep["parse_errors"],
               "partial_tail": rep["partial_tail"], "missing_native_id": rep["missing_native_id"],
               "dangling_parent_ids": rep["dangling_parent_ids"], "absent_parent_field": rep.get("absent_parent_field", 0),
               "missing_paste_content": rep["missing_paste_content"], "blocks": rep["blocks"],
               "non_occurrence_records": rep["non_occurrence_records"]}
        acts.append(store.put({"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at,
                               "actor": {"kind": "ai", "id": "claude"}, "inputs": [raw], "outputs": sorted_links(outs),
                               "implementation": implementation, "coverage": cov}))
    by_schema = collections.Counter(v["schema"] for v, _ in store.objects.values())
    snap = {"schema": "pkst/snapshot@0.1", "parents": [], "roots": sorted_links(acts), "protocol": proto_cid,
            "coverage": {"host": "macbook", "platform": "claude-code", "namespace": ci.NAMESPACE,
                         "scope": "Mac main package: ~/.claude/projects/**/*.jsonl (50) and ~/.claude/history.jsonl",
                         "capture_manifest": os.path.basename(manifest_path), "raw_blocks": len(rows), "status": "partial",
                         "totals": dict(totals), "related_roots": RELATED,
                         "gaps": ["Mac transcripts deleted before capture: unknown (only 5 main sessions present)",
                                  "Mac supplement (non-JSONL files, auto-memory) lives in its own root",
                                  "claude.ai cloud conversations live in their own root"]}}
    scid = store.put(snap)
    written = 0
    for c, (v, data) in store.objects.items():
        p = os.path.join(obj_dir, c + ".cbor")
        if not os.path.exists(p):
            open(p, "wb").write(data)
            written += 1
    order, seen, stack = [], set(), [str(scid)]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        order.append(c)
        v, _ = store.objects[c]
        stack.extend(str(l) for l in _links(v) if l.binary[1] == pc.CODEC_DAG_CBOR)
    header = pc.encode({"roots": [scid], "version": 1})
    car_path = os.path.join(base, ".private", "mac-claude-main.car")
    with open(car_path, "wb") as f:
        f.write(pc._uvarint(len(header)) + header)
        for c in order:
            data = store.objects[c][1]
            cb = pc.Link.parse(c).binary
            f.write(pc._uvarint(len(cb) + len(data)) + cb + data)
    summary = {"run": run, "recorded_at": recorded_at, "snapshot": str(scid), "protocol_raw_cid": str(proto_cid),
               "objects": len(store.objects), "written_this_run": written, "objects_by_schema": dict(by_schema),
               "distinct_occurrences": len(occ_seen), "occurrences_already_present_from_windows_or_earlier": preexisting_occ,
               "totals": dict(totals), "non_occurrence_record_types": dict(nonocc), "files_without_occurrences": zero_occ,
               "car": "contributions/claude/.private/mac-claude-main.car",
               "car_sha256": hashlib.sha256(open(car_path, "rb").read()).hexdigest(), "car_blocks": len(order),
               "implementation": implementation}
    with open(os.path.join(base, "mac-main-conversion-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _links(v):
    if isinstance(v, pc.Link):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _links(x)
    elif isinstance(v, list):
        for x in v:
            yield from _links(x)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
