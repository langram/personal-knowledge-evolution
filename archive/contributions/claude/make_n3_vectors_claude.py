"""N3 object vectors computed with the Claude encoder (synthetic values only).

Usage: python -I make_n3_vectors_claude.py <out.json>
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import claude_import_n3 as ci  # noqa: E402

RAW = pc.raw_cid(b'{"type":"user"}\n')


def main(out):
    vecs = []

    def add(name, value):
        data, cid = pc.object_cid(value)
        assert pc.encode(pc.decode(data)) == data
        vecs.append({"name": name, "value": pc.to_projection(value), "cbor_hex": data.hex(), "cid": str(cid)})
        return cid

    add("event_time/rfc3339-ms", ci.event_time("2026-10-24T07:05:42.328Z"))
    add("event_time/epoch-ms", ci.event_time(1779177431372))
    add("event_time/unknown", ci.event_time(None))
    src = add("source/claude-code-subagent", {"schema": "pkst/source@0.1", "platform": "claude-code",
                                              "namespace": "owner-claude-account", "native_thread_id": "s1/agent-a1"})
    txt = add("content/plain-crlf", ci._content("第一行\r\n第二行"))
    prj = add("projection/tool_use", ci._projection("tool_use", {"type": "tool_use", "name": "Read", "input": {"b": 1, "a": "中"}}))
    opq = add("opaque-block/thinking", ci._opaque("thinking", {"type": "thinking", "thinking": "x", "signature": "y"}))
    occ = add("occurrence/native-id", {
        "schema": "pkst/occurrence@0.1", "source": src, "native_id": "m1", "locator": None, "native_role": "assistant",
        "actor_kind": "ai", "process_kind": "sidechain", "content": [opq, txt, prj], "native_parent_ids": ["m0"],
        "event_time": ci.event_time("2026-10-24T07:05:42.328Z")})
    add("occurrence/locator-fallback", {
        "schema": "pkst/occurrence@0.1", "source": src, "native_id": None,
        "locator": {"raw": RAW, "start": 0, "end": 15, "coordinate": ci.COORD}, "native_role": "prompt-history",
        "actor_kind": "unknown", "process_kind": "unknown", "content": [txt], "native_parent_ids": None,
        "event_time": ci.event_time(1779177431372)})
    add("extraction-record/jsonl-range", {"schema": "pkst/extraction-record@0.1", "raw": RAW, "occurrence": occ,
                                          "coordinate": ci.COORD, "start": 0, "end": 15, "parser": ci.PARSER,
                                          "role_basis": "type=assistant;isSidechain"})
    add("block-reference/ordinal-2", {"schema": "pkst/block-reference@0.1", "raw": RAW, "occurrence": occ, "ordinal": 2,
                                      "coordinate": ci.COORD, "start": 0, "end": 15, "pointer": "/message/content/2",
                                      "native_type": "tool_use"})
    add("concept/lineage-null", {"schema": "pkst/concept@0.1", "label": "测试", "definition": "测试概念",
                                 "evidence": [occ], "asserted_by": {"kind": "ai", "id": "claude"}, "lineage": None})
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"schema": "pkst.test-vectors.n3-objects.claude", "encoder": "contributions/claude/pkst_cbor_claude.py",
                   "projection_profile": ci.PROFILE, "python": sys.version.split()[0],
                   "notes": "Synthetic; computed by the Claude encoder for Codex cross-check. Not a replacement for protocol/test-vectors.json.",
                   "positive": vecs}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(len(vecs), "vectors")


if __name__ == "__main__":
    main(sys.argv[1])
