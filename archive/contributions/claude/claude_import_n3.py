"""Claude Code raw blocks -> PKST 0.1 (N3) objects.

Inputs are captured raw blocks only, never live source files.
Identity objects (source, content, projection, opaque-block, occurrence) never link raw
blocks, except the explicit locator fallback for records without a native ID.
Raw anchoring lives in extraction-record and block-reference, which link occurrences
and are never linked back.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402

PARSER = "claude-code-jsonl@0.1-n3"
HISTORY_PARSER = "claude-code-history-jsonl@0.1-n3"
NAMESPACE = "owner-claude-account"
PROFILE = "python-json-v1"
TEXT = "text/plain;charset=utf-8"
COORD = "decoded-jsonl-utf8-bytes"
OCCURRENCE_TYPES = ("user", "assistant", "system", "attachment")
OPAQUE_BLOCKS = ("thinking", "redacted_thinking", "image")
INJECTED_ORIGINS = ("task-notification", "channel", "scheduled")
COMMAND_MARKERS = ("<command-name>", "<local-command-stdout>", "<local-command-stderr>", "<command-message>")


def _reject_constant(name):
    raise pc.PkstError("non-finite number %s" % name)


def parse_line(line):
    return json.loads(line.decode("utf-8"), object_pairs_hook=pc._no_dup, parse_constant=_reject_constant)


def project(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def event_time(ts):
    if isinstance(ts, bool) or ts is None:
        return {"value": None, "format": "unknown", "precision": "unknown", "zone_known": False, "unit": None}
    if isinstance(ts, int):
        return {"value": str(ts), "format": "epoch-decimal", "precision": "millisecond", "zone_known": True, "unit": "ms"}
    if isinstance(ts, str) and "T" in ts:
        clock = ts.split("T", 1)[1]
        zone = clock.endswith("Z") or "+" in clock or "-" in clock
        frac = clock.split(".", 1)[1] if "." in clock else ""
        digits = len(frac.rstrip("Z").split("+")[0].split("-")[0])
        precision = {0: "second", 3: "millisecond", 6: "microsecond"}.get(digits, "unknown")
        return {"value": ts, "format": "rfc3339", "precision": precision, "zone_known": zone, "unit": None}
    return {"value": str(ts), "format": "source-text", "precision": "unknown", "zone_known": False, "unit": None}


def _origin_kind(o):
    return o.get("kind") if isinstance(o, dict) else None


def classify(rec):
    """(actor_kind, process_kind, role_basis). Native 'human' marks an input channel, not identity."""
    t = rec.get("type")
    okind = _origin_kind(rec.get("origin"))
    basis = ["type=%s" % t]
    for key, val in (("origin.kind", okind), ("promptSource", rec.get("promptSource")), ("turnOrigin", rec.get("turnOrigin"))):
        if val:
            basis.append("%s=%s" % (key, val))
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
        att = rec.get("attachment") or {}
        basis.append("attachment=%s" % att.get("type"))
        if att.get("type") == "queued_command":
            aorigin = _origin_kind(att.get("origin"))
            if aorigin:
                basis.append("attachment.origin.kind=%s" % aorigin)
            if att.get("isMeta"):
                return "system", "injected", ";".join(basis + ["attachment.isMeta"])
            if aorigin == "peer":
                return "ai", "injected", ";".join(basis)
            if aorigin in INJECTED_ORIGINS:
                return "system", "injected", ";".join(basis)
            return "unknown", "unknown", ";".join(basis)
        return "system", "injected", ";".join(basis)
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
    text = content if isinstance(content, str) else "\n".join(
        b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")
    if text.lstrip().startswith(COMMAND_MARKERS):
        return "system", "injected", ";".join(basis + ["command-marker"])
    if rec.get("isSidechain"):
        return "ai", "sidechain", ";".join(basis + ["subagent-prompt"])
    return "unknown", process, ";".join(basis)


def _content(text):
    return {"schema": "pkst/content@0.1", "media_type": TEXT, "text": text}


def _projection(native_type, value):
    return {"schema": "pkst/projection@0.1", "native_type": native_type, "profile": PROFILE, "text": project(value)}


def _opaque(native_type, value):
    return {"schema": "pkst/opaque-block@0.1", "native_type": native_type, "profile": PROFILE,
            "digest": hashlib.sha256(project(value).encode("utf-8")).hexdigest(), "handling": "raw-only"}


def blocks_of(rec):
    """Yield (pointer, native_type, value) in source order."""
    t = rec.get("type")
    if t == "attachment":
        att = rec.get("attachment")
        if isinstance(att, dict) and att.get("type") == "queued_command" and isinstance(att.get("prompt"), str):
            yield "/attachment/prompt", "queued_command.prompt", _content(att["prompt"])
        yield "/attachment", "attachment/%s" % (att or {}).get("type"), _projection("attachment/%s" % (att or {}).get("type"), att)
        return
    if t == "system":
        if isinstance(rec.get("content"), str):
            yield "/content", "system.content", _content(rec["content"])
        return
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        yield "/message/content", "string", _content(c)
    elif isinstance(c, list):
        for i, b in enumerate(c):
            ptr = "/message/content/%d" % i
            bt = b.get("type") if isinstance(b, dict) else type(b).__name__
            if bt == "text" and isinstance(b.get("text"), str):
                yield ptr, "text", _content(b["text"])
            elif bt in OPAQUE_BLOCKS:
                yield ptr, bt, _opaque(bt, b)
            else:
                yield ptr, bt, _projection(bt, b)


class Store:
    def __init__(self):
        self.objects = {}

    def put(self, value):
        data, cid = pc.object_cid(value)
        pc.check_sets(value)
        self.objects[str(cid)] = (value, data)
        return cid


def _lines(raw_bytes, report):
    pos, n = 0, len(raw_bytes)
    while pos < n:
        nl = raw_bytes.find(b"\n", pos)
        if nl == -1:
            report["partial_tail"] = {"start": pos, "end": n}
            return
        start, end = pos, nl
        pos = nl + 1
        if raw_bytes[start:end].strip():
            yield start, end, raw_bytes[start:end]


def _new_report():
    return {"lines": 0, "occurrences": 0, "non_occurrence_records": {}, "parse_errors": [], "partial_tail": None,
            "missing_native_id": 0, "dangling_parent_ids": 0, "missing_paste_content": 0,
            "blocks": {"content": 0, "projection": 0, "opaque-block": 0}}


def _emit(store, out, raw_cid, rec, start, end, src, native_id, locator, role, actor, process, basis, parser, parents, ts, blocks):
    links, kinds = [], []
    for ptr, ntype, value in blocks:
        links.append(store.put(value))
        kinds.append((ptr, ntype, value["schema"].split("/")[1].split("@")[0]))
    occ = {"schema": "pkst/occurrence@0.1", "source": src, "native_id": native_id, "locator": locator,
           "native_role": role, "actor_kind": actor, "process_kind": process, "content": links,
           "native_parent_ids": parents, "event_time": event_time(ts)}
    ocid = store.put(occ)
    er = {"schema": "pkst/extraction-record@0.1", "raw": raw_cid, "occurrence": ocid, "coordinate": COORD,
          "start": start, "end": end, "parser": parser, "role_basis": basis}
    out["extraction_records"].append(store.put(er))
    for ordinal, (ptr, ntype, kind) in enumerate(kinds):
        out["report"]["blocks"][kind] += 1
        br = {"schema": "pkst/block-reference@0.1", "raw": raw_cid, "occurrence": ocid, "ordinal": ordinal,
              "coordinate": COORD, "start": start, "end": end, "pointer": ptr, "native_type": ntype}
        out["block_references"].append(store.put(br))
    out["occurrences"].append((native_id, ocid))
    out["report"]["occurrences"] += 1
    return ocid


def import_transcript(raw_bytes, raw_cid=None, store=None):
    raw_cid = raw_cid or pc.raw_cid(raw_bytes)
    store = store or Store()
    out = {"store": store, "occurrences": [], "extraction_records": [], "block_references": [], "report": _new_report()}
    rep = out["report"]
    seen = set()
    parents_wanted = []
    for start, end, line in _lines(raw_bytes, rep):
        rep["lines"] += 1
        try:
            rec = parse_line(line)
        except Exception as exc:
            rep["parse_errors"].append({"start": start, "end": end, "error": type(exc).__name__})
            continue
        t = rec.get("type") if isinstance(rec, dict) else None
        if t not in OCCURRENCE_TYPES:
            rep["non_occurrence_records"][str(t)] = rep["non_occurrence_records"].get(str(t), 0) + 1
            continue
        if not rec.get("uuid"):
            rep["missing_native_id"] += 1
            continue
        thread = rec.get("sessionId")
        if rec.get("agentId"):
            thread = "%s/agent-%s" % (thread, rec["agentId"])
        src = store.put({"schema": "pkst/source@0.1", "platform": "claude-code", "namespace": NAMESPACE,
                         "native_thread_id": thread})
        actor, process, basis = classify(rec)
        # absent field -> null (unknown); explicit parentUuid=null -> [] (known root)
        if "parentUuid" not in rec:
            parents = None
            rep["absent_parent_field"] = rep.get("absent_parent_field", 0) + 1
        else:
            parents = [rec["parentUuid"]] if rec["parentUuid"] is not None else []
            parents_wanted += parents
        seen.add(rec["uuid"])
        _emit(store, out, raw_cid, rec, start, end, src, rec["uuid"], None, t, actor, process, basis, PARSER,
              parents, rec.get("timestamp"), list(blocks_of(rec)))
    rep["dangling_parent_ids"] = sum(1 for p in parents_wanted if p not in seen)
    return out


def import_history(raw_bytes, raw_cid=None, store=None):
    """~/.claude/history.jsonl: no native message ID -> explicit raw+range locator (not stable across exports)."""
    raw_cid = raw_cid or pc.raw_cid(raw_bytes)
    store = store or Store()
    out = {"store": store, "occurrences": [], "extraction_records": [], "block_references": [], "report": _new_report()}
    rep = out["report"]
    for start, end, line in _lines(raw_bytes, rep):
        rep["lines"] += 1
        try:
            rec = parse_line(line)
        except Exception as exc:
            rep["parse_errors"].append({"start": start, "end": end, "error": type(exc).__name__})
            continue
        sid = rec.get("sessionId")
        thread = sid if isinstance(sid, str) and sid else None
        if thread is None:
            rep["missing_native_id"] += 1
            continue
        src = store.put({"schema": "pkst/source@0.1", "platform": "claude-code", "namespace": NAMESPACE,
                         "native_thread_id": thread})
        blocks = []
        if isinstance(rec.get("display"), str):
            blocks.append(("/display", "display", _content(rec["display"])))
        pasted = rec.get("pastedContents") or {}
        for key in pasted:  # source order
            item = pasted[key]
            ptr = "/pastedContents/%s" % key.replace("~", "~0").replace("/", "~1")
            if isinstance(item, dict) and isinstance(item.get("content"), str):
                blocks.append((ptr + "/content", "pasted.content", _content(item["content"])))
            else:
                rep["missing_paste_content"] += 1
            blocks.append((ptr, "pastedContents.item", _projection("pastedContents.item", item)))
        locator = {"raw": raw_cid, "start": start, "end": end, "coordinate": COORD}
        _emit(store, out, raw_cid, rec, start, end, src, None, locator, "prompt-history", "unknown", "unknown",
              "history.jsonl;no-native-message-id;no-parent-field", HISTORY_PARSER, None, rec.get("timestamp"), blocks)
    return out
