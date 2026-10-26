"""Audit and fixed-byte capture of the Mac Claude supplement tar (read-only inbox, no extraction).

Checks the tar SHA-256, member safety (regular files only; no absolute, '..', backslash, NUL, drive or
duplicate / case-folded names), and every member against supplement-manifest.jsonl. Stores the tar and
every member as raw/<CID>.bin. Member content is archive data: nothing is executed.

Usage: python -I capture_mac_supplement.py <tar> <expected sha256> <contributions/claude dir>
"""

import collections
import datetime
import hashlib
import io
import json
import os
import posixpath
import sys
import tarfile
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402

BS = chr(92)


def store(raw_dir, data):
    cid = pc.raw_cid(data)
    dest = os.path.join(raw_dir, str(cid) + ".bin")
    if not os.path.exists(dest):
        with open(dest + ".tmp", "wb") as f:
            f.write(data)
        os.replace(dest + ".tmp", dest)
    if pc.raw_cid(open(dest, "rb").read()) != cid:
        raise pc.PkstError("stored block does not re-hash: " + dest)
    return str(cid)


def category(path):
    parts = path.split("/")
    if parts[0] == "claude-projects-non-jsonl":
        if "memory" in parts:
            return "claude-code-project-memory"
        if "subagents" in parts:
            return "claude-code-subagent-meta"
        if "tool-results" in parts:
            return "claude-code-tool-result"
        if parts[-1] == "sessions-index.json":
            return "claude-code-sessions-index"
        return "claude-code-project-other"
    if parts[0] == "claude-app":
        if parts[1] == "claude-code-sessions":
            return "claude-desktop-session-meta"
        if parts[1] == "local-agent-mode-sessions":
            return "claude-local-agent-skill-file" if parts[2] == "skills-plugin" else "claude-local-agent-mode-meta"
        return "claude-app-other"
    return "supplement-control"


def main(tar_path, expected_sha, out_dir):
    run = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = os.path.join(out_dir, "raw")
    st0 = os.stat(tar_path)
    tb = open(tar_path, "rb").read()
    st1 = os.stat(tar_path)
    sha = hashlib.sha256(tb).hexdigest()
    checks = {"tar_sha256_matches": sha == expected_sha, "tar_stable": st0.st_size == st1.st_size == len(tb)
              and st0.st_mtime_ns == st1.st_mtime_ns}
    tar_cid = store(raw_dir, tb)
    t = tarfile.open(fileobj=io.BytesIO(tb), mode="r:")
    members = t.getmembers()
    unsafe, nonreg = [], []
    names, folded = collections.Counter(), collections.Counter()
    for m in members:
        n = m.name
        names[n] += 1
        folded[unicodedata.normalize("NFC", n).casefold()] += 1
        if not m.isreg():
            nonreg.append(n)
        if (n.startswith("/") or BS in n or "\x00" in n or ":" in n or ".." in n.split("/")
                or posixpath.normpath(n) != n):
            unsafe.append(n)
    checks.update({"members": len(members), "all_regular_files": not nonreg, "unsafe_names": unsafe,
                   "duplicate_names": [n for n, c in names.items() if c > 1],
                   "casefold_nfc_collisions": [n for n, c in folded.items() if c > 1]})
    data = {m.name: t.extractfile(m).read() for m in members if m.isreg()}
    manifest = [json.loads(l) for l in data["supplement-manifest.jsonl"].decode("utf-8").splitlines() if l.strip()]
    by_path = {}
    dup_manifest = []
    for r in manifest:
        if r["archive_path"] in by_path:
            dup_manifest.append(r["archive_path"])
        by_path[r["archive_path"]] = r
    sources = set(data) - {"supplement-manifest.jsonl", "supplement-report.txt"}
    mismatch, changed = [], []
    rows = []
    for m in members:
        n = m.name
        b = data[n]
        r = by_path.get(n)
        msha = hashlib.sha256(b).hexdigest()
        if n in sources:
            if r is None or r["sha256"] != msha or r["size_before"] != len(b) or r["size_after_hash"] != len(b):
                mismatch.append(n)
            if r is not None and (r["changed_during_hash"] or r["mtime_before_ns"] != r["mtime_after_hash_ns"]):
                changed.append(n)
        rows.append({"kind": "tar-member", "archive": tar_cid, "archive_path": n, "category": category(n),
                     "bytes": len(b), "sha256": msha, "cid": store(raw_dir, b),
                     "mac_source_path": r["source_path"] if r else None,
                     "mac_mtime_ns": str(r["mtime_before_ns"]) if r else None,
                     "tar_mtime": m.mtime, "manifest_sha256_match": (r["sha256"] == msha) if r else None})
    checks.update({"manifest_rows": len(manifest), "manifest_duplicate_paths": dup_manifest,
                   "manifest_paths_equal_source_members": set(by_path) == sources,
                   "manifest_sha_or_size_mismatch": mismatch, "changed_during_hash": changed})
    ok = (checks["tar_sha256_matches"] and checks["tar_stable"] and checks["all_regular_files"] and not unsafe
          and not checks["duplicate_names"] and not checks["casefold_nfc_collisions"] and not dup_manifest
          and checks["manifest_paths_equal_source_members"] and not mismatch and not changed)
    man_path = os.path.join(raw_dir, "_mac-supplement-capture-%s.jsonl" % run)
    with open(man_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"kind": "tar", "cid": tar_cid, "sha256": sha, "bytes": len(tb),
                            "inbox_path": "coordination/.private/mac-inbox/" + os.path.basename(tar_path)}, ensure_ascii=False) + "\n")
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {"run": run, "tar_cid": tar_cid, "tar_sha256": sha, "tar_bytes": len(tb), "pass": ok, "checks": checks,
               "categories": dict(collections.Counter(r["category"] for r in rows)),
               "distinct_member_cids": len({r["cid"] for r in rows}),
               "capturer_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
               "manifest": os.path.relpath(man_path, out_dir).replace(BS, "/"),
               "manifest_sha256": hashlib.sha256(open(man_path, "rb").read()).hexdigest()}
    with open(os.path.join(out_dir, "mac-supplement-capture-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: summary[k] for k in ("run", "tar_cid", "pass", "categories", "distinct_member_cids")}, ensure_ascii=False))
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in checks.items()}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
