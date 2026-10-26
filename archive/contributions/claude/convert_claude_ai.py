"""Claude.ai official export -> PKST 0.1 objects (adapter candidate per CLAUDE-AI-EXPORT-0.1-proposal.md).

Reads captured raw member blocks only. Writes objects/<CID>.cbor, a snapshot, a CARv1 of the
snapshot closure (raw blocks stay external) and a summary JSON.

Usage: python -I convert_claude_ai.py <contributions/claude dir> <capture-summary.json> <protocol/PKST-0.1.md> <proposal.md>
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

PARSER = "claude-ai-export@0.1.1"
NAMESPACE = "owner-claude-account"
JP = "json-pointer"
# Seen, safe structural block types (rules 0.1.1). thinking and anything unrecognised -> opaque, raw-only.
PROJECTION_TYPES = ("tool_use", "tool_result", "token_budget", "injected_prompt_block", "document")
MEMORY_FILE_BASIS = ("derived memory; not user speech; no native message id; "
                     "event_time=memory_files.updated_at is a version-state time, not creation or authorship time")


def esc(token):
    return str(token).replace("~", "~0").replace("/", "~1")


def sorted_links(links):
    uniq = {l.binary: l for l in links}
    return [uniq[b] for b in sorted(uniq)]


UNRECOGNISED = collections.Counter()


def message_items(m):
    """Ordered (relative pointer, native_type, value) for one chat message (rules 0.1.1 section 3)."""
    out = []
    for i, b in enumerate(m.get("content") or []):
        bt = b.get("type") if isinstance(b, dict) else None
        ptr = "/content/%d" % i
        if bt == "text" and isinstance(b.get("text"), str):
            out.append((ptr, "text", ci._content(b["text"])))
        elif bt in PROJECTION_TYPES:
            out.append((ptr, bt, ci._projection(bt, b)))
        else:
            if bt != "thinking":
                UNRECOGNISED[str(bt)] += 1
            out.append((ptr, str(bt), ci._opaque(str(bt), b)))
    for j, a in enumerate(m.get("attachments") or []):
        out.append(("/attachments/%d" % j, "attachment", ci._projection("attachment", a)))
    for k, f in enumerate(m.get("files") or []):
        out.append(("/files/%d" % k, "file-ref", ci._projection("file-ref", f)))
    joined = "".join(b.get("text", "") for b in m.get("content") or [] if isinstance(b, dict) and b.get("type") == "text")
    if "text" in m and m["text"] != joined:
        out.append(("/text", "message.text", ci._projection("message.text", {"text": m["text"]})))
    return out


def actor_of(m):
    if m.get("sender") == "assistant":
        return "ai", "sender=assistant"
    blocks = m.get("content") or []
    if blocks and all(isinstance(b, dict) and b.get("type") == "tool_result" for b in blocks):
        return "tool", "sender=%s;content=tool_result-only" % m.get("sender")
    return "unknown", "sender=%s;user-channel-authorship-unverified" % m.get("sender")


class Builder:
    def __init__(self):
        self.store = ci.Store()
        self.report = collections.Counter()

    def put(self, v):
        return self.store.put(v)

    def emit(self, raw, src, native_id, locator, role, actor, process, parents, ts, doc_ptr, items, basis):
        links = [self.put(v) for _, _, v in items]
        occ = {"schema": "pkst/occurrence@0.1", "source": src, "native_id": native_id, "locator": locator,
               "native_role": role, "actor_kind": actor, "process_kind": process, "content": links,
               "native_parent_ids": parents, "event_time": ci.event_time(ts) if ts is not None else ci.event_time(None)}
        ocid = self.put(occ)
        outs = [ocid] + links
        outs.append(self.put({"schema": "pkst/extraction-record@0.1", "raw": raw, "occurrence": ocid, "coordinate": JP,
                              "pointer": doc_ptr, "parser": PARSER, "role_basis": basis}))
        for ordinal, (rel, ntype, v) in enumerate(items):
            self.report["block:" + v["schema"].split("/")[1].split("@")[0]] += 1
            outs.append(self.put({"schema": "pkst/block-reference@0.1", "raw": raw, "occurrence": ocid, "ordinal": ordinal,
                                  "coordinate": JP, "document_pointer": doc_ptr, "pointer": rel, "native_type": ntype}))
        self.report["occurrence:" + role.split(":")[0] + (":" + role.split(":")[1] if ":" in role else "")] += 1
        return ocid, outs


def main(base, summary_path, protocol_path, proposal_path, parent_snapshot=None, car_name="claude-ai-evidence.car"):
    now = datetime.datetime.now(datetime.timezone.utc)
    run = now.strftime("%Y%m%dT%H%M%SZ")
    recorded_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    cap = json.load(open(summary_path, encoding="utf-8"))
    members = {m["member_path"]: m for m in cap["members_detail"]}
    raw_dir = os.path.join(base, "raw")
    obj_dir = os.path.join(base, "objects")
    os.makedirs(obj_dir, exist_ok=True)

    def raw_bytes(cid):
        data = open(os.path.join(raw_dir, cid + ".bin"), "rb").read()
        if str(pc.raw_cid(data)) != cid:
            raise pc.PkstError("raw corrupted " + cid)
        return data

    def store_raw(data):
        cid = pc.raw_cid(data)
        p = os.path.join(raw_dir, str(cid) + ".bin")
        if not os.path.exists(p):
            open(p, "wb").write(data)
        return cid

    here = os.path.dirname(os.path.abspath(__file__))
    impl_bytes = open(os.path.abspath(__file__), "rb").read()
    proto_cid = store_raw(open(protocol_path, "rb").read())
    proposal_cid = store_raw(open(proposal_path, "rb").read())
    implementation = {"adapter": PARSER, "convert_sha256": hashlib.sha256(impl_bytes).hexdigest(),
                      "import_n3_sha256": hashlib.sha256(open(os.path.join(here, "claude_import_n3.py"), "rb").read()).hexdigest(),
                      "codec_sha256": hashlib.sha256(open(os.path.join(here, "pkst_cbor_claude.py"), "rb").read()).hexdigest(),
                      "python": sys.version.split()[0], "profile": ci.PROFILE, "rules": proposal_cid}
    actor = {"kind": "ai", "id": "claude"}
    b = Builder()
    activities = []
    gaps = collections.Counter()

    def activity(inputs, outputs, coverage):
        act = {"schema": "pkst/activity@0.1", "operation": "import", "recorded_at": recorded_at, "actor": actor,
               "inputs": sorted_links(inputs), "outputs": sorted_links(outputs), "implementation": implementation,
               "coverage": coverage}
        activities.append(b.put(act))

    # conversations
    m = members["conversations.json"]
    craw = pc.Link.parse(m["cid"])
    convs = json.loads(raw_bytes(m["cid"]).decode("utf-8"), object_pairs_hook=pc._no_dup)
    outs = []
    stats = collections.Counter()
    for c_i, conv in enumerate(convs):
        src = b.put({"schema": "pkst/source@0.1", "platform": "claude-ai", "namespace": NAMESPACE,
                     "native_thread_id": conv["uuid"]})
        ids = {x["uuid"] for x in conv.get("chat_messages") or []}
        stats["conversations"] += 1
        if not conv.get("chat_messages"):
            stats["empty_conversations"] += 1
        for m_i, msg in enumerate(conv.get("chat_messages") or []):
            if "parent_message_uuid" not in msg:
                parents = None
            elif msg["parent_message_uuid"] is None:
                parents = []
            else:
                parents = [msg["parent_message_uuid"]]
                if msg["parent_message_uuid"] not in ids:
                    stats["parent_outside_conversation"] += 1
            act_kind, basis = actor_of(msg)
            _, o = b.emit(craw, src, msg["uuid"], None, msg.get("sender"), act_kind, "unknown", parents,
                          msg.get("created_at"), "/%d/chat_messages/%d" % (c_i, m_i), message_items(msg), basis)
            outs += o
            stats["messages"] += 1
            stats["file_refs_without_bytes"] += len(msg.get("files") or [])
    activity([craw], outs, {"member": "conversations.json", "status": "parsed", "conversations": stats["conversations"],
                            "messages": stats["messages"], "empty_conversations": stats["empty_conversations"],
                            "parent_values_outside_conversation": stats["parent_outside_conversation"],
                            "file_refs_without_bytes": stats["file_refs_without_bytes"],
                            "conversation_name_and_summary": "raw-only",
                            "unrecognised_block_types_opaque": dict(UNRECOGNISED),
                            "process_kind": "unknown (source provides no classification)",
                            "branches": "export contains some forks; completeness of branches unknown"})
    gaps["file_refs_without_bytes"] = stats["file_refs_without_bytes"]

    # projects
    for path, m in sorted(members.items()):
        if not path.startswith("projects/"):
            continue
        praw = pc.Link.parse(m["cid"])
        pj = json.loads(raw_bytes(m["cid"]).decode("utf-8"), object_pairs_hook=pc._no_dup)
        src = b.put({"schema": "pkst/source@0.1", "platform": "claude-ai-project", "namespace": NAMESPACE,
                     "native_thread_id": pj["uuid"]})
        items = [("/description", "description", ci._content(pj.get("description", ""))),
                 ("/prompt_template", "prompt_template", ci._content(pj.get("prompt_template", "")))]
        _, outs = b.emit(praw, src, pj["uuid"], None, "material:project", "unknown", "unknown", None, pj.get("created_at"),
                         "", items, "project record; material, not speech")
        for d_i, doc in enumerate(pj.get("docs") or []):
            _, o = b.emit(praw, src, doc["uuid"], None, "material:project-doc", "unknown", "unknown", None,
                          doc.get("created_at"), "/docs/%d" % d_i, [("/content", "doc.content", ci._content(doc.get("content", "")))],
                          "project doc; material, not speech")
            outs += o
        activity([praw], outs, {"member": path, "status": "parsed", "docs": len(pj.get("docs") or []),
                                "use": "material; not user speech"})

    # memories
    for path, m in sorted(members.items()):
        if not path.startswith("memories/"):
            continue
        mraw = pc.Link.parse(m["cid"])
        mm = json.loads(raw_bytes(m["cid"]).decode("utf-8"), object_pairs_hook=pc._no_dup)
        src = b.put({"schema": "pkst/source@0.1", "platform": "claude-ai-memory", "namespace": NAMESPACE,
                     "native_thread_id": mm["account_uuid"]})
        outs = []
        entries = []
        if "conversations_memory" in mm:
            entries.append(("/conversations_memory", "derived-memory:conversations", None,
                            [("", "conversations_memory", ci._content(mm["conversations_memory"]))]))
        for pid in mm.get("project_memories") or {}:
            entries.append(("/project_memories/%s" % esc(pid), "derived-memory:project", None,
                            [("", "project_memory", ci._content(mm["project_memories"][pid]))]))
        for f_i, f in enumerate(mm.get("memory_files") or []):
            entries.append(("/memory_files/%d" % f_i, "derived-memory:file", f.get("updated_at"),
                            [("/content", "memory_file.content", ci._content(f.get("content", ""))),
                             ("", "memory_file.meta", ci._projection("memory_file.meta",
                                                                     {k: v for k, v in f.items() if k != "content"}))]))
        for ptr, role, ts, items in entries:
            loc = {"raw": mraw, "coordinate": JP, "pointer": ptr}
            basis = MEMORY_FILE_BASIS if role == "derived-memory:file" else \
                "derived memory; not user speech; no native message id; no source time"
            _, o = b.emit(mraw, src, None, loc, role, "unknown", "unknown", None, ts, ptr, items, basis)
            outs += o
        activity([mraw], outs, {"member": path, "status": "parsed", "entries": len(entries),
                                "use": "derived memory; not user speech; event_time of memory_files = updated_at (state time)"})

    # raw-only members and archives
    for path, m in sorted(members.items()):
        if path in ("users.json", "login_history.json"):
            activity([pc.Link.parse(m["cid"])], [], {"member": path, "status": "present", "parsed": False,
                                                     "reason": "account/login metadata; raw-only; excluded from semantic extraction"})
    for a in cap["archives"]:
        names = [x["member_path"] for x in cap["members_detail"] if x["archive_name"] == a["name"]]
        activity([pc.Link.parse(a["cid"])], [], {"archive": a["name"], "status": "captured", "member_paths": names})

    snap = {"schema": "pkst/snapshot@0.1", "parents": [pc.Link.parse(parent_snapshot)] if parent_snapshot else [], "roots": sorted_links(activities), "protocol": proto_cid,
            "coverage": {"platform": "claude-ai", "namespace": NAMESPACE, "source": "official Claude.ai data export (4 ZIPs)",
                         "capture_run": cap["run"], "status": "partial",
                         "conversations": stats["conversations"], "messages": stats["messages"],
                         "event_time_range": [min(x["created_at"] for c in convs for x in c["chat_messages"]),
                                              max(x["created_at"] for c in convs for x in c["chat_messages"])],
                         "gaps": ["file bytes not in export (%d file refs)" % stats["file_refs_without_bytes"],
                                  "branch completeness unknown", "deleted or unexported conversations unknown",
                                  "thinking text not extracted (raw-only)", "conversation summaries raw-only",
                                  "claude.ai/code cloud sessions: not identified in this export"],
                         "adapter_rules": proposal_cid, "adapter_status": "rules-0.1.1-accepted-by-codex-review; independent recomputation pending"}}
    scid = b.put(snap)
    written = 0
    for cid, (v, data) in b.store.objects.items():
        p = os.path.join(obj_dir, cid + ".cbor")
        if not os.path.exists(p):
            open(p, "wb").write(data)
            written += 1

    # CARv1 of the snapshot closure, including parent snapshots (dag-cbor only; raw external)
    def block(c):
        if c in b.store.objects:
            return b.store.objects[c]
        data = open(os.path.join(obj_dir, c + ".cbor"), "rb").read()
        if str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != c:
            raise pc.PkstError("stored object corrupted " + c)
        return pc.decode(data), data

    order, seen, stack = [], set(), [str(scid)]
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        order.append(c)
        v, _ = block(c)
        for l in reversed([x for x in _links(v) if x.binary[1] == pc.CODEC_DAG_CBOR]):
            stack.append(str(l))
    header = pc.encode({"roots": [scid], "version": 1})
    car_path = os.path.join(base, ".private", car_name)
    os.makedirs(os.path.dirname(car_path), exist_ok=True)
    with open(car_path, "wb") as f:
        f.write(pc._uvarint(len(header)) + header)
        for c in order:
            data = block(c)[1]
            cb = pc.Link.parse(c).binary
            f.write(pc._uvarint(len(cb) + len(data)) + cb + data)
    by_schema = collections.Counter(v["schema"] for v, _ in b.store.objects.values())
    summary = {"run": run, "recorded_at": recorded_at, "snapshot": str(scid), "protocol_raw_cid": str(proto_cid),
               "adapter_rules_raw_cid": str(proposal_cid), "implementation": {k: (str(v) if isinstance(v, pc.Link) else v) for k, v in implementation.items()},
               "objects": len(b.store.objects), "written_this_run": written, "objects_by_schema": dict(by_schema),
               "car": "contributions/claude/.private/" + car_name,
               "car_sha256": hashlib.sha256(open(car_path, "rb").read()).hexdigest(), "car_blocks": len(order),
               "counts": dict(b.report), "conversation_stats": dict(stats), "activities": len(activities)}
    with open(os.path.join(base, "claude-ai-conversion-summary-%s.json" % run), "w", encoding="utf-8", newline="\n") as f:
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
    sys.exit(main(*sys.argv[1:7]))
