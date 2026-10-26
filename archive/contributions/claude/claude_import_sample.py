"""Claude Code JSONL -> PKST 0.1 objects (sample importer, not yet for bulk use).

Input is a captured raw block (bytes), never the live source file.
Outputs plain PKST values (dicts with pc.Link) keyed by CID string.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402

PARSER = "claude-code-jsonl@0.1-sample"
NAMESPACE = "owner-claude-account"  # one alias for the user's Claude account, shared by win-main and macbook
OCCURRENCE_TYPES = ("user", "assistant", "system", "attachment")
INJECTED_ORIGINS = ("task-notification", "channel", "scheduled")
COMMAND_MARKERS = ("<command-name>", "<local-command-stdout>", "<local-command-stderr>", "<command-message>")


def _time(ts):
    if not isinstance(ts, str):
        return {"value": None, "precision": "unknown", "zone_known": False}
    frac = ts.split("T", 1)[-1]
    precision = "millisecond" if "." in frac else "second"
    return {"value": ts, "precision": precision, "zone_known": ts.endswith("Z") or "+" in frac}


def _text_of(rec):
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def classify(rec):
    """Return (actor_kind, process_kind, role_basis). Native 'human' marks an input channel, not identity."""
    t = rec.get("type")
    origin = rec.get("origin") or {}
    okind = origin.get("kind") if isinstance(origin, dict) else None
    basis = ["type=%s" % t]
    if okind:
        basis.append("origin.kind=%s" % okind)
    if rec.get("promptSource"):
        basis.append("promptSource=%s" % rec["promptSource"])
    if rec.get("turnOrigin"):
        basis.append("turnOrigin=%s" % rec["turnOrigin"])

    if rec.get("isCompactSummary"):
        return "ai", "compaction", ";".join(basis + ["isCompactSummary"])
    process = "sidechain" if rec.get("isSidechain") else "main"
    if rec.get("isSidechain"):
        basis.append("isSidechain")

    if t == "assistant":
        if rec.get("isApiErrorMessage"):
            return "system", "injected", ";".join(basis + ["isApiErrorMessage"])
        return "ai", process, ";".join(basis)
    if t == "system":
        return "system", "injected", ";".join(basis + ["subtype=%s" % rec.get("subtype")])
    if t == "attachment":
        at = (rec.get("attachment") or {}).get("type")
        basis.append("attachment=%s" % at)
        if at == "queued_command":
            # queued prompt text may be the user's words; sender cannot be confirmed from this record alone
            return "unknown", "unknown", ";".join(basis)
        return "system", "injected", ";".join(basis)
    # type == user
    content = (rec.get("message") or {}).get("content")
    if rec.get("toolUseResult") is not None or (isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content)):
        return "tool", process, ";".join(basis + ["tool_result"])
    if rec.get("isMeta"):
        return "system", "injected", ";".join(basis + ["isMeta"])
    if okind == "peer" or rec.get("turnOrigin") == "peer":
        return "ai", "injected", ";".join(basis)
    if okind in INJECTED_ORIGINS or rec.get("promptSource") == "system" or rec.get("turnOrigin") in ("scheduled", "task_notification"):
        return "system", "injected", ";".join(basis)
    if _text_of(rec).lstrip().startswith(COMMAND_MARKERS):
        return "system", "injected", ";".join(basis + ["command-marker"])
    if rec.get("isSidechain"):
        return "ai", "sidechain", ";".join(basis + ["subagent-prompt"])
    return "unknown", process, ";".join(basis)


def _contents(rec):
    """Ordered content values. Text is kept verbatim; non-text blocks are a JSON projection (raw stays authoritative)."""
    out = []
    if rec.get("type") == "attachment":
        out.append({"schema": "pkst/content@0.1", "media_type": "application/json; pkst-projection=claude-attachment",
                    "text": json.dumps(rec.get("attachment"), ensure_ascii=False, separators=(",", ":"))})
        return out
    if rec.get("type") == "system":
        c = rec.get("content")
        if isinstance(c, str):
            out.append({"schema": "pkst/content@0.1", "media_type": "text/plain; charset=utf-8", "text": c})
        return out
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        out.append({"schema": "pkst/content@0.1", "media_type": "text/plain; charset=utf-8", "text": c})
    elif isinstance(c, list):
        for b in c:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt == "text":
                out.append({"schema": "pkst/content@0.1", "media_type": "text/plain; charset=utf-8", "text": b.get("text", "")})
            elif bt == "thinking":
                out.append({"schema": "pkst/content@0.1", "media_type": "text/plain; charset=utf-8; pkst-block=thinking",
                            "text": b.get("thinking", "")})
            else:
                out.append({"schema": "pkst/content@0.1", "media_type": "application/json; pkst-projection=claude-block-%s" % bt,
                            "text": json.dumps(b, ensure_ascii=False, separators=(",", ":"))})
    return out


def _put(store, value):
    data, cid = pc.object_cid(value)
    pc.check_sets(value)
    store[str(cid)] = value
    return cid


def import_block(raw_bytes, raw_cid=None):
    """Parse one captured JSONL block. Returns dict with objects, occurrences, report."""
    raw_cid = raw_cid or pc.raw_cid(raw_bytes)
    store, occs, ers = {}, [], []
    report = {"lines": 0, "occurrences": 0, "non_occurrence_records": {}, "parse_errors": [], "partial_tail": None,
              "missing_native_id": 0}
    pos = 0
    n = len(raw_bytes)
    while pos < n:
        nl = raw_bytes.find(b"\n", pos)
        if nl == -1:
            report["partial_tail"] = {"start": pos, "end": n}
            break
        start, end = pos, nl
        pos = nl + 1
        line = raw_bytes[start:end]
        if line.endswith(b"\r"):
            line = line[:-1]
        if not line.strip():
            continue
        report["lines"] += 1
        try:
            rec = json.loads(line.decode("utf-8"), object_pairs_hook=pc._no_dup)
        except Exception as exc:
            report["parse_errors"].append({"start": start, "end": end, "error": type(exc).__name__})
            continue
        t = rec.get("type")
        if t not in OCCURRENCE_TYPES:
            report["non_occurrence_records"][t] = report["non_occurrence_records"].get(t, 0) + 1
            continue
        if not rec.get("uuid"):
            report["missing_native_id"] += 1
            continue  # v0.1 sample: no locator fallback emitted for Claude Code yet
        thread = rec.get("sessionId")
        if rec.get("agentId"):
            thread = "%s/agent-%s" % (thread, rec["agentId"])
        src = _put(store, {"schema": "pkst/source@0.1", "platform": "claude-code",
                           "namespace": NAMESPACE, "native_thread_id": thread})
        actor, process, basis = classify(rec)
        content_links = [_put(store, c) for c in _contents(rec)]
        occ = {
            "schema": "pkst/occurrence@0.1", "source": src, "native_id": rec["uuid"], "locator": None,
            "native_role": t, "actor_kind": actor, "process_kind": process, "content": content_links,
            "native_parent_ids": [rec["parentUuid"]] if rec.get("parentUuid") else [],
            "event_time": _time(rec.get("timestamp")),
        }
        ocid = _put(store, occ)
        er = {"schema": "pkst/extraction-record@0.1", "raw": raw_cid, "occurrence": ocid, "start": start, "end": end,
              "coordinate": "decoded-jsonl-utf8-bytes", "parser": PARSER, "role_basis": basis}
        ers.append(_put(store, er))
        occs.append((rec["uuid"], ocid))
        report["occurrences"] += 1
    return {"objects": store, "occurrences": occs, "extraction_records": ers, "report": report}
