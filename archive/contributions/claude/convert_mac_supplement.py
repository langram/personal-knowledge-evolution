"""Mac Claude supplement -> PKST 0.1 evidence root (raw-only members; no occurrences).

One activity per tar member and one for the tar itself; a separate snapshot root; a CARv1 of its
closure. Member content is archive data and is never executed or interpreted as speech.

Usage: python -I convert_mac_supplement.py <contributions/claude dir> <capture manifest.jsonl> <protocol/PKST-0.1.md> <rules.md>
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

REASONS = {
    "claude-code-subagent-meta": "subagent spawn metadata / prompt-cache state; not speech",
    "claude-code-tool-result": "tool output original referenced by transcripts; not speech",
    "claude-code-project-other": "session custom title; raw-only (titles are not source identity)",
    "claude-code-sessions-index": "session index (entries empty in this capture)",
    "claude-code-project-memory": "Claude Code auto-memory note written by the agent; derived memory, not user speech; "
                                  "extraction awaits a whole-file coordinate rule (see rules proposal)",
    "claude-desktop-session-meta": "desktop session metadata; raw-only",
    "claude-local-agent-mode-meta": "local agent mode metadata; raw-only",
    "claude-local-agent-skill-file": "product skill/plugin file (scripts, prompts, schemas); archive data, never executed, not user content",
    "supplement-control": "collector manifest/report written on the Mac; provenance record",
}


def sorted_links(links):
    uniq = {l.binary: l for l in links}
    return [uniq[b] for b in sorted(uniq)]


def main(base, manifest_path, protocol_path, rules_path):
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

    proto_cid = store_raw(open(protocol_path, "rb").read())
    rules_cid = store_raw(open(rules_path, "rb").read())
    rows = [json.loads(l) for l in open(manifest_path, encoding="utf-8")]
    tar_row, members = rows[0], rows[1:]
    implementation = {"adapter": "mac-claude-supplement@0.1-raw-only",
                      "convert_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
                      "codec_sha256": hashlib.sha256(open(os.path.join(base, "pkst_cbor_claude.py"), "rb").read()).hexdigest(),
                      "python": sys.version.split()[0], "rules": rules_cid}
    actor = {"kind": "ai", "id": "claude"}
    store = ci.Store()
    acts = []
    for r in members:
        raw = pc.Link.parse(r["cid"])
        data = open(os.path.join(raw_dir, r["cid"] + ".bin"), "rb").read()
        if pc.raw_cid(data) != raw or hashlib.sha256(data).hexdigest() != r["sha256"]:
            raise pc.PkstError("raw mismatch " + r["archive_path"])
        cov = {"host": "macbook", "archive_path": r["archive_path"], "category": r["category"],
               "status": "present", "parsed": False, "reason": REASONS[r["category"]],
               "bytes": r["bytes"], "sha256": r["sha256"], "tar": tar_row["cid"]}
        if r.get("mac_source_path") is not None:
            cov["mac_source_path"] = r["mac_source_path"]
            cov["mac_mtime_ns"] = r["mac_mtime_ns"]
        acts.append(store.put({"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at,
                               "actor": actor, "inputs": [raw], "outputs": [], "implementation": implementation,
                               "coverage": cov}))
    cats = collections.Counter(r["category"] for r in members)
    acts.append(store.put({"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at, "actor": actor,
                           "inputs": [pc.Link.parse(tar_row["cid"])], "outputs": [], "implementation": implementation,
                           "coverage": {"host": "macbook", "archive": "pkst-claude-supplement-20261024.tar",
                                        "sha256": tar_row["sha256"], "bytes": tar_row["bytes"], "status": "captured",
                                        "member_count": len(members), "categories": dict(cats)}}))
    snap = {"schema": "pkst/snapshot@0.1", "parents": [], "roots": sorted_links(acts), "protocol": proto_cid,
            "coverage": {"host": "macbook", "platform": "claude-code", "namespace": "owner-claude-account",
                         "scope": "Mac Claude supplemental package: non-JSONL project files, claude-code-sessions, local-agent-mode-sessions",
                         "status": "partial", "occurrences": 0, "members": len(members),
                         "categories": dict(cats), "rules": rules_cid,
                         "gaps": ["Mac Claude Code JSONL transcripts are in the main package, not yet received on Windows",
                                  "auto-memory notes raw-only until whole-file coordinate rule is accepted",
                                  "credentials/config/caches/IndexedDB/VM bundles excluded by the Mac collector"]}}
    scid = store.put(snap)
    written = 0
    for cid, (v, data) in store.objects.items():
        p = os.path.join(obj_dir, cid + ".cbor")
        if not os.path.exists(p):
            open(p, "wb").write(data)
            written += 1
    order = [str(scid)] + [str(a) for a in snap["roots"]]
    header = pc.encode({"roots": [scid], "version": 1})
    car_path = os.path.join(base, ".private", "mac-claude-supplement.car")
    with open(car_path, "wb") as f:
        f.write(pc._uvarint(len(header)) + header)
        for c in order:
            data = store.objects[c][1]
            cb = pc.Link.parse(c).binary
            f.write(pc._uvarint(len(cb) + len(data)) + cb + data)
    summary = {"run": run, "recorded_at": recorded_at, "snapshot": str(scid), "protocol_raw_cid": str(proto_cid),
               "rules_raw_cid": str(rules_cid), "tar_cid": tar_row["cid"], "activities": len(acts), "objects": len(store.objects),
               "written_this_run": written, "categories": dict(cats), "occurrences": 0,
               "car": "contributions/claude/.private/mac-claude-supplement.car",
               "car_sha256": hashlib.sha256(open(car_path, "rb").read()).hexdigest(), "car_blocks": len(order),
               "implementation": {k: str(v) for k, v in implementation.items()}}
    with open(os.path.join(base, "mac-supplement-conversion-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
