"""Full-anchor verification of the Claude.ai CAR against the raw export members.

Separate code path from convert_claude_ai.py: reads the CAR with verify_car_claude, resolves every
extraction-record and block-reference with its own RFC 6901 resolver and re-derives expected values
from the raw JSON. Prints counts only (no text).

Usage: python -I verify_claude_ai_anchors.py <contributions/claude dir> <capture-summary.json> <report.json>
"""

import collections
import datetime
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402
from verify_gemini_claude import resolve, project  # noqa: E402

TEXT = "text/plain;charset=utf-8"
SENTINEL = "00000000-0000-4000-8000-000000000000"


PROJECTION_TYPES = {"tool_use", "tool_result", "token_budget", "injected_prompt_block", "document"}


def main(base, summary_path, out, car_name="claude-ai-evidence.car"):
    car = open(os.path.join(base, ".private", car_name), "rb").read()
    hl, i = pc._read_uvarint(car, 0)
    header = pc.decode(car[i:i + hl])
    i += hl
    blocks = {}
    while i < len(car):
        sl, j = pc._read_uvarint(car, i)
        cid, k = vc.read_cid(car, j)
        data = car[k:j + sl]
        if pc.cid_for(data, pc.CODEC_DAG_CBOR) != cid:
            raise pc.PkstError("hash mismatch in CAR")
        blocks[str(cid)] = pc.decode(data)
        i = j + sl
    cap = json.load(open(summary_path, encoding="utf-8"))
    # Check only the root snapshot's own members (its roots' closure), not parent snapshots.
    root = blocks[str(header["roots"][0])]
    member, stack = set(), [str(r) for r in root["roots"]]
    while stack:
        c = stack.pop()
        if c in member or c not in blocks:
            continue
        member.add(c)
        stack.extend(str(l) for l in vc.links(blocks[c]) if l.binary[1] == pc.CODEC_DAG_CBOR)
    parent_count = len(root["parents"])
    blocks = {c: v for c, v in blocks.items() if c in member}
    docs = {}

    def doc(raw):
        s = str(raw)
        if s not in docs:
            b = open(os.path.join(base, "raw", s + ".bin"), "rb").read()
            assert str(pc.raw_cid(b)) == s
            docs[s] = json.loads(b.decode("utf-8"))
        return docs[s]

    P = collections.Counter()
    ex = {}

    def bad(k, c):
        P[k] += 1
        ex.setdefault(k, c)

    seen_msgs, seen_docs, seen_mem = set(), set(), set()
    roles = collections.Counter()
    occ_with_er = set()
    for c, v in blocks.items():
        if v["schema"] != "pkst/extraction-record@0.1":
            continue
        o = blocks.get(str(v["occurrence"]))
        if o is None:
            bad("er-occurrence-missing", c)
            continue
        occ_with_er.add(str(v["occurrence"]))
        if v["coordinate"] != "json-pointer" or "start" in v or "end" in v:
            bad("er-coordinate", c)
        try:
            node = resolve(doc(v["raw"]), v["pointer"])
        except Exception:
            bad("er-pointer-unresolvable", c)
            continue
        role = o["native_role"]
        roles["%s|%s|%s" % (role, o["actor_kind"], o["process_kind"])] += 1
        items = [blocks[str(l)] for l in o["content"]]
        if role in ("human", "assistant"):
            if not re.fullmatch(r"/(0|[1-9]\d*)/chat_messages/(0|[1-9]\d*)", v["pointer"]):
                bad("msg-pointer-shape", c)
            if node.get("uuid") != o["native_id"] or o["locator"] is not None or node.get("sender") != role:
                bad("msg-identity", c)
            seen_msgs.add(node["uuid"])
            if o["native_parent_ids"] != [node["parent_message_uuid"]]:
                bad("msg-parent", c)
            et = o["event_time"]
            if et != {"value": node["created_at"], "format": "rfc3339", "precision": "microsecond", "zone_known": True, "unit": None}:
                bad("msg-time", c)
            expect_actor = "ai" if role == "assistant" else (
                "tool" if node["content"] and all(b.get("type") == "tool_result" for b in node["content"]) else "unknown")
            if o["actor_kind"] != expect_actor:
                bad("msg-actor", c)
            if o["process_kind"] != "unknown":
                bad("msg-process-kind", c)
            # expected item sequence, derived independently from the raw node
            exp = []
            for b in node["content"]:
                t = b.get("type")
                if t == "text":
                    exp.append(("pkst/content@0.1", b["text"]))
                elif t in PROJECTION_TYPES:
                    exp.append(("pkst/projection@0.1", project(b)))
                else:  # thinking and any unrecognised type: fingerprint only
                    exp.append(("pkst/opaque-block@0.1", hashlib.sha256(project(b).encode("utf-8")).hexdigest()))
            exp += [("pkst/projection@0.1", project(a)) for a in node["attachments"]]
            exp += [("pkst/projection@0.1", project(f)) for f in node["files"]]
            if node["text"] != "".join(b.get("text", "") for b in node["content"] if b.get("type") == "text"):
                exp.append(("pkst/projection@0.1", project({"text": node["text"]})))
            got = [(x["schema"], x.get("text") if x["schema"] != "pkst/opaque-block@0.1" else x["digest"]) for x in items]
            if got != exp:
                bad("msg-content-sequence", c)
            if any(x["schema"] == "pkst/content@0.1" and x["media_type"] != TEXT for x in items):
                bad("media-type", c)
        elif role.startswith("material:"):
            if o["native_id"] != node.get("uuid") or o["native_parent_ids"] is not None:
                bad("material-identity", c)
            if role == "material:project":
                if [x.get("text") for x in items] != [node.get("description", ""), node.get("prompt_template", "")]:
                    bad("project-text", c)
            else:
                seen_docs.add(node["uuid"])
                if [x.get("text") for x in items] != [node.get("content", "")]:
                    bad("doc-text", c)
        elif role.startswith("derived-memory:"):
            loc = o["locator"]
            if o["native_id"] is not None or loc != {"raw": v["raw"], "coordinate": "json-pointer", "pointer": v["pointer"]}:
                bad("memory-locator", c)
            seen_mem.add(v["pointer"])
            if role == "derived-memory:file":
                if "version-state time" not in v["role_basis"] or o["event_time"]["value"] != node.get("updated_at"):
                    bad("memory-file-time-basis", c)
            elif o["event_time"]["format"] != "unknown":
                bad("memory-time-not-unknown", c)
            want = node if isinstance(node, str) else node.get("content")
            if items[0]["schema"] != "pkst/content@0.1" or items[0]["text"] != want:
                bad("memory-text", c)
        else:
            bad("unexpected-role", c)
    # block-references
    br_n = 0
    for c, v in blocks.items():
        if v["schema"] != "pkst/block-reference@0.1":
            continue
        br_n += 1
        o = blocks[str(v["occurrence"])]
        try:
            base_node = resolve(doc(v["raw"]), v["document_pointer"])
            resolve(base_node, v["pointer"])
        except Exception:
            bad("br-unresolvable", c)
            continue
        if v["ordinal"] >= len(o["content"]):
            bad("br-ordinal", c)
        if "start" in v or "end" in v:
            bad("br-coordinate", c)
    # coverage against raw
    conv_cid = next(m["cid"] for m in cap["members_detail"] if m["member_path"] == "conversations.json")
    convs = doc(pc.Link.parse(conv_cid))
    all_msgs = {m["uuid"] for c in convs for m in c["chat_messages"]}
    proj_docs = set()
    mem_ptrs = set()
    for m in cap["members_detail"]:
        if m["member_path"].startswith("projects/"):
            proj_docs |= {d["uuid"] for d in doc(pc.Link.parse(m["cid"])).get("docs") or []}
        if m["member_path"].startswith("memories/"):
            mm = doc(pc.Link.parse(m["cid"]))
            mem_ptrs |= {"/conversations_memory"} | {"/project_memories/" + k for k in mm["project_memories"]} | {
                "/memory_files/%d" % i for i in range(len(mm["memory_files"]))}
    occs = [c for c, v in blocks.items() if v["schema"] == "pkst/occurrence@0.1"]
    # tree facts
    roots = forks = outside = 0
    for conv in convs:
        ids = {m["uuid"] for m in conv["chat_messages"]}
        kids = collections.Counter(m["parent_message_uuid"] for m in conv["chat_messages"])
        roots += sum(1 for m in conv["chat_messages"] if m["parent_message_uuid"] == SENTINEL)
        outside += sum(1 for m in conv["chat_messages"] if m["parent_message_uuid"] not in ids and m["parent_message_uuid"] != SENTINEL)
        forks += sum(1 for p, n in kids.items() if n > 1)
    rep = {
        "ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "car_root": str(header["roots"][0]), "root_member_blocks_checked": len(blocks), "root_parents": parent_count,
        "problems": dict(P), "problem_examples": ex,
        "coverage": {"messages_in_export": len(all_msgs), "messages_anchored": len(seen_msgs),
                     "project_docs_in_export": len(proj_docs), "project_docs_anchored": len(seen_docs),
                     "memory_entries_in_export": len(mem_ptrs), "memory_entries_anchored": len(seen_mem),
                     "occurrences_without_extraction_record": len(set(occs) - occ_with_er)},
        "tree": {"sentinel_roots": roots, "fork_points": forks, "parents_outside_conversation_excluding_sentinel": outside},
        "block_references_checked": br_n, "role_actor_process": dict(roles),
    }
    rep["pass"] = (not P and all_msgs == seen_msgs and proj_docs == seen_docs and mem_ptrs == seen_mem
                   and not (set(occs) - occ_with_er))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
