"""Copy the staged Mac Claude main-package raw blocks into contributions/claude/raw with full checks.

Reads coordination/.private/mac-inbox/main/claude-manifest.jsonl and claude-raw/ only (scripts there
are data and are never executed). Each block must match the manifest sha256, CIDv1 raw, sizes and
before/after mtime.

Usage: python -I capture_mac_main.py <mac main inbox dir> <contributions/claude dir>
"""

import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402


def main(inbox, out_dir):
    run = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man_bytes = open(os.path.join(inbox, "claude-manifest.jsonl"), "rb").read()
    rows = [json.loads(l) for l in man_bytes.decode("utf-8").splitlines() if l.strip()]
    raw_dir = os.path.join(out_dir, "raw")
    out, bad = [], []
    for r in rows:
        src = os.path.join(inbox, "claude-raw", r["cidv1_raw"] + ".bin")
        b = open(src, "rb").read()
        cid = str(pc.raw_cid(b))
        checks = {"sha256": hashlib.sha256(b).hexdigest() == r["sha256"], "cid": cid == r["cidv1_raw"],
                  "size": len(b) == r["size_before"] == r["size_after"] == r["bytes_copied"],
                  "mtime_stable": r["mtime_before_ns"] == r["mtime_after_ns"], "status": r["status"] == "copied" and r["error"] is None,
                  "jsonl_name": r["source_path"].endswith(".jsonl")}
        if not all(checks.values()):
            bad.append({"source_path": r["source_path"], "failed": [k for k, v in checks.items() if not v]})
        dest = os.path.join(raw_dir, cid + ".bin")
        if not os.path.exists(dest):
            with open(dest + ".tmp", "wb") as f:
                f.write(b)
            os.replace(dest + ".tmp", dest)
        if str(pc.raw_cid(open(dest, "rb").read())) != cid:
            raise pc.PkstError("stored raw does not re-hash " + dest)
        kind = "claude-code-prompt-history" if r["source_group"] == "claude_history" else (
            "claude-code-subagent-transcript" if "/subagents/" in r["source_path"] else "claude-code-transcript")
        out.append({"kind": kind, "cid": cid, "sha256": r["sha256"], "bytes": len(b), "host": "macbook",
                    "source_group": r["source_group"], "source_path": r["source_path"],
                    "mac_mtime_ns": str(r["mtime_before_ns"]), "status": "captured" if all(checks.values()) else "failed"})
    man_path = os.path.join(raw_dir, "_mac-main-capture-%s.jsonl" % run)
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {"run": run, "inbox_manifest_sha256": hashlib.sha256(man_bytes).hexdigest(), "rows": len(rows),
               "distinct_cids": len({r["cid"] for r in out}), "bytes": sum(r["bytes"] for r in out),
               "by_kind": {k: sum(1 for r in out if r["kind"] == k) for k in sorted({r["kind"] for r in out})},
               "failures": bad, "pass": not bad, "manifest": os.path.relpath(man_path, out_dir).replace(chr(92), "/"),
               "manifest_sha256": hashlib.sha256(open(man_path, "rb").read()).hexdigest(),
               "capturer_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()}
    with open(os.path.join(out_dir, "mac-main-capture-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
