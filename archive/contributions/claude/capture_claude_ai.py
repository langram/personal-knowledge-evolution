"""Fixed-byte capture of the Claude.ai official export ZIPs (read-only inbox).

Stores each ZIP and each member's bytes as raw/<CID>.bin; never extracts to disk paths,
never follows URLs. The download manifest (it carries download URLs) is hashed but not copied.

Usage: python -I capture_claude_ai.py <inbox dir> <contributions/claude dir>
"""

import datetime
import hashlib
import io
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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


def main(inbox, out_dir):
    run = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = os.path.join(out_dir, "raw")
    receipt = json.load(open(os.path.join(inbox, "receipt.json"), encoding="utf-8"))
    expected = {r["filename"]: r for r in receipt["received"]}
    rows, failures = [], []
    started = now()
    for name in sorted(os.listdir(inbox)):
        path = os.path.join(inbox, name)
        st0 = os.stat(path)
        data = open(path, "rb").read()
        st1 = os.stat(path)
        sha = hashlib.sha256(data).hexdigest()
        exp = expected.get(name)
        row = {"kind": "inbox-file", "name": name, "bytes": len(data), "sha256": sha,
               "receipt_sha256_match": (exp["sha256"] == sha) if exp else None,
               "stable": st0.st_size == st1.st_size == len(data) and st0.st_mtime_ns == st1.st_mtime_ns}
        if name.endswith(".zip"):
            row["cid"] = store(raw_dir, data)
            row["kind"] = "export-zip"
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    bad = z.testzip()
                    row["zip_crc_ok"] = bad is None
                    for ordinal, info in enumerate(z.infolist()):
                        if info.is_dir():
                            continue
                        mbytes = z.read(info)
                        rows.append({"kind": "zip-member", "archive": row["cid"], "archive_name": name, "ordinal": ordinal,
                                     "member_path": info.filename, "bytes": len(mbytes),
                                     "sha256": hashlib.sha256(mbytes).hexdigest(), "cid": store(raw_dir, mbytes),
                                     "zip_crc32": "%08x" % info.CRC, "zip_local_time_unzoned": list(info.date_time)})
            except Exception as exc:
                failures.append({"name": name, "error": "%s: %s" % (type(exc).__name__, exc)})
        else:
            row["stored"] = False
            row["reason"] = "not an export archive (receipt or URL-bearing download manifest); hashed only"
        rows.append(row)
    manifest = os.path.join(raw_dir, "_claude-ai-capture-%s.jsonl" % run)
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        for r in rows + [dict(failure=True, **x) for x in failures]:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "run": run, "started_at": started, "finished_at": now(), "inbox": "coordination/.private/claude-cloud-inbox",
        "capturer_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "zips": sum(1 for r in rows if r["kind"] == "export-zip"),
        "members": sum(1 for r in rows if r["kind"] == "zip-member"),
        "all_receipt_hashes_match": all(r["receipt_sha256_match"] for r in rows if r["kind"] == "export-zip"),
        "all_zip_crc_ok": all(r.get("zip_crc_ok") for r in rows if r["kind"] == "export-zip"),
        "all_stable": all(r["stable"] for r in rows if r["kind"] in ("export-zip", "inbox-file")),
        "failures": failures,
        "manifest": os.path.relpath(manifest, out_dir).replace("\\", "/"),
        "manifest_sha256": hashlib.sha256(open(manifest, "rb").read()).hexdigest(),
        "archives": [{k: r[k] for k in ("name", "cid", "bytes", "sha256")} for r in rows if r["kind"] == "export-zip"],
        "members_detail": [{k: r[k] for k in ("archive_name", "member_path", "cid", "bytes")} for r in rows if r["kind"] == "zip-member"],
    }
    with open(os.path.join(out_dir, "claude-ai-capture-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: summary[k] for k in ("run", "zips", "members", "all_receipt_hashes_match", "all_zip_crc_ok", "all_stable", "failures")}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
