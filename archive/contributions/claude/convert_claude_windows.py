"""Full conversion of captured Windows Claude raw blocks into PKST 0.1 (N3) objects.

Usage: python -I convert_claude_windows.py <contributions/claude dir> <manifest.jsonl> <protocol/PKST-0.1.md>
Writes objects/<CID>.cbor, one activity per raw block, one snapshot, and a summary JSON.
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

TRANSCRIPT_KINDS = ("claude-code-transcript", "claude-code-subagent-transcript")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sorted_links(links):
    uniq = {l.binary: l for l in links}
    return [uniq[b] for b in sorted(uniq)]


def write_obj(obj_dir, cid, data):
    path = os.path.join(obj_dir, cid + ".cbor")
    if not os.path.exists(path):
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        return 1
    return 0


def main(base, manifest_path, protocol_path, parent_snapshot=None):
    now = datetime.datetime.now(datetime.timezone.utc)
    run = now.strftime("%Y%m%dT%H%M%SZ")
    recorded_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    obj_dir = os.path.join(base, "objects")
    os.makedirs(obj_dir, exist_ok=True)
    here = os.path.dirname(os.path.abspath(__file__))
    implementation = "claude_import_n3.py@sha256:%s;pkst_cbor_claude.py@sha256:%s;python-%s;profile=%s" % (
        sha(os.path.join(here, "claude_import_n3.py")), sha(os.path.join(here, "pkst_cbor_claude.py")),
        sys.version.split()[0], ci.PROFILE)
    actor = {"kind": "ai", "id": "claude"}

    proto = open(protocol_path, "rb").read()
    proto_cid = pc.raw_cid(proto)
    proto_dest = os.path.join(base, "raw", str(proto_cid) + ".bin")
    if not os.path.exists(proto_dest):
        with open(proto_dest, "wb") as f:
            f.write(proto)

    rows = [json.loads(l) for l in open(manifest_path, encoding="utf-8") if '"failure"' not in l]
    written = 0
    activities = []
    by_schema = collections.Counter()
    totals = collections.Counter()
    gaps = collections.defaultdict(list)
    seen = set()
    for r in rows:
        raw_link = pc.Link.parse(r["cid"])
        data = open(os.path.join(base, "raw", r["cid"] + ".bin"), "rb").read()
        if pc.raw_cid(data) != raw_link:
            raise pc.PkstError("raw block corrupted: " + r["cid"])
        cov = {"raw_kind": r["kind"], "bytes": len(data), "capture_status": r["status"]}
        outputs = []
        if r["kind"] in TRANSCRIPT_KINDS or r["kind"] == "claude-code-prompt-history":
            imp = (ci.import_history if r["kind"] == "claude-code-prompt-history" else ci.import_transcript)(data, raw_link)
            rep = imp["report"]
            for cid, (v, enc) in imp["store"].objects.items():
                written += write_obj(obj_dir, cid, enc)
                outputs.append(pc.Link.parse(cid))
                if cid not in seen:
                    seen.add(cid)
                    by_schema[v["schema"]] += 1
            cov.update({"status": "parsed" if not rep["parse_errors"] and not rep["partial_tail"] else "partial",
                        "parser": ci.HISTORY_PARSER if r["kind"] == "claude-code-prompt-history" else ci.PARSER,
                        "lines": rep["lines"], "occurrences": rep["occurrences"],
                        "parse_errors": rep["parse_errors"], "partial_tail": rep["partial_tail"],
                        "missing_native_id": rep["missing_native_id"], "dangling_parent_ids": rep["dangling_parent_ids"],
                        "missing_paste_content": rep["missing_paste_content"], "blocks": rep["blocks"],
                        "non_occurrence_records": rep["non_occurrence_records"]})
            for k in ("lines", "occurrences", "missing_native_id", "dangling_parent_ids", "missing_paste_content"):
                totals[k] += rep[k]
            totals["parse_errors"] += len(rep["parse_errors"])
            totals["partial_tails"] += bool(rep["partial_tail"])
            if rep["occurrences"] == 0:
                gaps["transcripts_without_occurrences"].append(r["cid"])
            if rep["dangling_parent_ids"]:
                gaps["blocks_with_dangling_parent_ids"].append(r["cid"])
        else:
            cov.update({"status": "present", "parsed": False})
            gaps["present_not_parsed_kinds"].append(r["kind"])
        act = {"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at, "actor": actor,
               "inputs": [raw_link], "outputs": sorted_links(outputs), "implementation": implementation, "coverage": cov}
        enc, acid = pc.object_cid(act)
        pc.check_sets(act)
        written += write_obj(obj_dir, str(acid), enc)
        by_schema[act["schema"]] += 1
        activities.append(acid)

    present_not_parsed = dict(collections.Counter(gaps.pop("present_not_parsed_kinds", [])))
    coverage = {
        "host": "win-main", "platform": "claude-code", "namespace": ci.NAMESPACE,
        "capture_manifest": os.path.basename(manifest_path), "raw_blocks": len(rows),
        "status": "partial",
        "parsed_raw_kinds": ["claude-code-transcript", "claude-code-subagent-transcript", "claude-code-prompt-history"],
        "present_not_parsed": present_not_parsed,
        "not_in_scope": ["claude.ai web/desktop chat/mobile (export pending)", "macbook (transfer pending)",
                         "claude.ai/code cloud sessions (unknown)", "transcripts deleted before capture (unknown count)",
                         "current session after capture cutoff"],
        "totals": dict(totals),
    }
    parents = [pc.Link.parse(parent_snapshot)] if parent_snapshot else []
    snap = {"schema": "pkst/snapshot@0.1", "parents": parents, "roots": sorted_links(activities), "coverage": coverage,
            "protocol": proto_cid}
    enc, scid = pc.object_cid(snap)
    pc.check_sets(snap)
    written += write_obj(obj_dir, str(scid), enc)
    by_schema[snap["schema"]] += 1

    # Verify: every stored object re-hashes, decodes canonically, and all links resolve (closure).
    files = [f for f in os.listdir(obj_dir) if f.endswith(".cbor")]
    bad, dangling = [], 0
    raw_dir = os.path.join(base, "raw")
    for f in files:
        data = open(os.path.join(obj_dir, f), "rb").read()
        cid = f[:-5]
        if str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != cid:
            bad.append(cid)
            continue
        stack = [pc.decode(data)]
        while stack:
            v = stack.pop()
            if isinstance(v, pc.Link):
                p = os.path.join(raw_dir if v.binary[1] == pc.CODEC_RAW else obj_dir,
                                 str(v) + (".bin" if v.binary[1] == pc.CODEC_RAW else ".cbor"))
                dangling += not os.path.exists(p)
            elif isinstance(v, dict):
                stack.extend(v.values())
            elif isinstance(v, list):
                stack.extend(v)
    summary = {
        "run": run, "recorded_at": recorded_at, "snapshot": str(scid), "protocol_raw_cid": str(proto_cid),
        "protocol_sha256": hashlib.sha256(proto).hexdigest(), "implementation": implementation,
        "objects_dir": "contributions/claude/objects", "object_files": len(files), "written_this_run": written,
        "objects_by_schema": dict(by_schema), "activities": len(activities), "totals": dict(totals),
        "gaps": {k: len(v) for k, v in gaps.items()}, "present_not_parsed": present_not_parsed,
        "verify": {"rehash_failures": len(bad), "dangling_links": dangling},
    }
    with open(os.path.join(base, "conversion-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not bad and not dangling else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
