"""Fixed-byte snapshot of Windows Claude sources into contributions/claude/raw/.

Sources are opened read-only. Each file is captured as the prefix of the size
observed at start (append-only growth after that point is excluded and reported).
Raw blocks are stored as raw/<CID>.bin with CIDv1 raw (0x55) + sha2-256.

Usage: python -I capture_claude_windows.py <out_dir>
"""

import datetime
import glob
import hashlib
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402

HOME = os.path.expanduser("~")
APPDATA = os.path.join(HOME, "AppData", "Local", "Claude-Data", "claude_pzs8sxrjxfjjc")

# (kind, root, glob). Credentials, tokens, app config and file-history backups are out of scope.
SCOPE = [
    ("claude-code-project-file", os.path.join(HOME, ".claude", "projects"), "**/*"),
    ("claude-code-prompt-history", os.path.join(HOME, ".claude"), "history.jsonl"),
    ("claude-desktop-session-meta", os.path.join(APPDATA, "claude-code-sessions"), "**/*.json"),
    ("claude-desktop-side-notes", os.path.join(APPDATA, "side-session-notes"), "**/*.md"),
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def classify(kind, path):
    if kind != "claude-code-project-file":
        return kind
    parts = path.replace("\\", "/").split("/")
    if path.endswith(".jsonl"):
        return "claude-code-subagent-transcript" if "subagents" in parts else "claude-code-transcript"
    if "subagents" in parts:
        return "claude-code-subagent-meta"
    if "tool-results" in parts:
        return "claude-code-tool-result"
    return "claude-code-project-other"


def jsonl_stats(data):
    lines = data.split(b"\n")
    tail = lines.pop()  # bytes after last newline: b"" when the prefix ends cleanly
    n = bad = 0
    ts = []
    for line in lines:
        if not line.strip():
            continue
        try:
            o = json.loads(line.decode("utf-8"))
        except Exception:
            bad += 1
            continue
        n += 1
        t = o.get("timestamp") if isinstance(o, dict) else None
        if isinstance(t, (int, float)):
            t = datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(t, str):
            ts.append(t)
    return {"json_records": n, "unparsable_lines": bad, "partial_tail_bytes": len(tail),
            "first_event_ts": min(ts) if ts else None, "last_event_ts": max(ts) if ts else None}


def capture(path, raw_dir):
    st0 = os.stat(path)
    size0 = st0.st_size
    with open(path, "rb") as f:
        data = f.read(size0)
    st1 = os.stat(path)
    status = "captured"
    if len(data) != size0 or st1.st_size < size0:
        status = "unstable-shrunk"
    elif st1.st_size > size0 or st1.st_mtime_ns != st0.st_mtime_ns:
        # verify the captured prefix is unchanged (append-only growth)
        with open(path, "rb") as f:
            again = f.read(size0)
        status = "snapshot-prefix" if again == data else "unstable-rewritten"
    cid = pc.raw_cid(data)
    dest = os.path.join(raw_dir, str(cid) + ".bin")
    if not os.path.exists(dest):
        tmp = dest + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    with open(dest, "rb") as f:
        if pc.raw_cid(f.read()) != cid:
            raise pc.PkstError("stored block does not re-hash to its CID: " + dest)
    return data, cid, size0, st0, st1, status


def main(out_dir):
    run = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    raw_dir = os.path.join(out_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    started = now()
    rows, failures = [], []
    for kind, root, pattern in SCOPE:
        for path in sorted(glob.glob(os.path.join(root, pattern), recursive=True)):
            if not os.path.isfile(path):
                continue
            k = classify(kind, path)
            try:
                t0 = now()
                data, cid, size0, st0, st1, status = capture(path, raw_dir)
                row = {
                    "kind": k, "original_path": path, "cid": str(cid),
                    "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                    "size_at_start": size0, "size_after": st1.st_size,
                    "mtime_at_start": datetime.datetime.fromtimestamp(st0.st_mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "capture_started_at": t0, "capture_finished_at": now(), "status": status,
                }
                if path.endswith(".jsonl"):
                    row.update(jsonl_stats(data))
                rows.append(row)
            except Exception as exc:
                failures.append({"kind": k, "original_path": path, "error": "%s: %s" % (type(exc).__name__, exc)})
    finished = now()
    manifest = os.path.join(raw_dir, "_manifest-%s.jsonl" % run)
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        for r in rows + [dict(failure=True, **x) for x in failures]:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    by_kind = {}
    for r in rows:
        b = by_kind.setdefault(r["kind"], {"files": 0, "bytes": 0})
        b["files"] += 1
        b["bytes"] += r["bytes"]
    statuses = {}
    for r in rows:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    summary = {
        "run": run, "host": "win-main", "capturer": "contributions/claude/capture_claude_windows.py",
        "capturer_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        "started_at": started, "finished_at": finished,
        "scope": [{"kind": k, "root": r, "glob": g} for k, r, g in SCOPE],
        "excluded": ["~/.claude/.credentials*, sessions/*.key, settings, plugins, file-history (edited-file backups), shell-snapshots",
                     "Claude-Data app config, tokens, IndexedDB/Local Storage caches, VM bundles"],
        "files": len(rows), "failed": len(failures),
        "distinct_raw_blocks": len({r["cid"] for r in rows}),
        "captured_bytes": sum(r["bytes"] for r in rows),
        "by_kind": by_kind, "status_counts": statuses,
        "jsonl_partial_tail_files": sum(1 for r in rows if r.get("partial_tail_bytes")),
        "jsonl_unparsable_lines": sum(r.get("unparsable_lines", 0) for r in rows),
        "manifest": os.path.relpath(manifest, out_dir).replace("\\", "/"),
        "manifest_sha256": hashlib.sha256(open(manifest, "rb").read()).hexdigest(),
    }
    with open(os.path.join(out_dir, "capture-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
