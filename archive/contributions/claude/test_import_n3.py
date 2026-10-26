"""N3 importer checks on captured raw blocks (in memory; nothing persisted).

Usage: python -I test_import_n3.py <contributions/claude dir> <manifest.jsonl> <results.json>
Results hold counts, CIDs and native IDs only; no message text.
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import claude_import_n3 as ci  # noqa: E402

IDENTITY_SCHEMAS = ("pkst/source@0.1", "pkst/content@0.1", "pkst/projection@0.1", "pkst/opaque-block@0.1",
                    "pkst/occurrence@0.1")
ANCHOR_SCHEMAS = ("pkst/extraction-record@0.1", "pkst/block-reference@0.1")


def links_in(v):
    if isinstance(v, pc.Link):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from links_in(x)
    elif isinstance(v, list):
        for x in v:
            yield from links_in(x)


def codec_of(link):
    return link.binary[1]  # version 0x01 then single-byte codec varint for 0x55 / 0x71


def load(base, row):
    data = open(os.path.join(base, "raw", row["cid"] + ".bin"), "rb").read()
    assert str(pc.raw_cid(data)) == row["cid"], "raw block corrupted: " + row["cid"]
    return data


def occ(imp, cid):
    return imp["store"].objects[str(cid)][0]


def main(base, manifest, out):
    rows = [json.loads(l) for l in open(manifest, encoding="utf-8")]
    tx = [r for r in rows if r.get("kind") in ("claude-code-transcript", "claude-code-subagent-transcript")]
    main_tx = [r for r in tx if r["kind"] == "claude-code-transcript" and r["bytes"] > 1000]
    hist = [r for r in rows if r.get("kind") == "claude-code-prompt-history"]
    T = {}
    imported = {r["cid"]: ci.import_transcript(load(base, r), pc.Link.parse(r["cid"])) for r in tx}
    himp = ci.import_history(load(base, hist[0]), pc.Link.parse(hist[0]["cid"]))

    # T1 re-import of identical bytes -> identical object sets.
    sample = sorted(main_tx, key=lambda r: -r["bytes"])[:2] + [r for r in tx if "subagent" in r["kind"]][:1]
    t1 = []
    for r in sample:
        again = ci.import_transcript(load(base, r), pc.Link.parse(r["cid"]))
        t1.append({"raw": r["cid"], "objects": len(again["store"].objects),
                   "identical": set(again["store"].objects) == set(imported[r["cid"]]["store"].objects)})
    h2 = ci.import_history(load(base, hist[0]), pc.Link.parse(hist[0]["cid"]))
    t1.append({"raw": hist[0]["cid"], "objects": len(h2["store"].objects),
               "identical": set(h2["store"].objects) == set(himp["store"].objects)})
    T["T1_reimport_idempotent"] = {"pass": all(x["identical"] for x in t1), "cases": t1}

    # T2 forks preserved (real) + synthetic user rewind.
    real = kept = 0
    for r in main_tx:
        imp = imported[r["cid"]]
        kids = collections.defaultdict(list)
        for _, c in imp["occurrences"]:
            o = occ(imp, c)
            if o["native_parent_ids"]:
                kids[o["native_parent_ids"][0]].append(o)
        for p, ch in kids.items():
            if len(ch) > 1:
                real += 1
                kept += all(o["native_parent_ids"] == [p] for o in ch)
    fx = "\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"type": "user", "uuid": "u1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:00.000Z", "message": {"content": "问题"}},
        {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:01.000Z",
         "message": {"content": [{"type": "text", "text": "回答"}]}},
        {"type": "user", "uuid": "u2a", "parentUuid": "a1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:02.000Z", "message": {"content": "版本一"}},
        {"type": "user", "uuid": "u2b", "parentUuid": "a1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:03.000Z", "message": {"content": "版本二"}},
    ]).encode("utf-8") + b"\n"
    fi = ci.import_transcript(fx)
    fo = {u: occ(fi, c) for u, c in fi["occurrences"]}
    syn = (fo["u2a"]["native_parent_ids"] == ["a1"] == fo["u2b"]["native_parent_ids"] and fo["u2a"]["content"] != fo["u2b"]["content"]
           and fo["u1"]["native_parent_ids"] is None)  # fixture u1 has no parentUuid field -> unknown, not root
    nullroot = ci.import_transcript(b'{"type":"user","uuid":"r","parentUuid":null,"sessionId":"fx","message":{"content":"x"}}\n')
    syn = syn and occ(nullroot, nullroot["occurrences"][0][1])["native_parent_ids"] == []
    T["T2_fork_preserved"] = {"pass": real > 0 and kept == real and syn, "real_fork_points": real, "kept": kept,
                              "synthetic_user_rewind_ok": syn}

    # T3 relocated copies -> identical occurrence CIDs.
    by_name = collections.defaultdict(list)
    for r in main_tx:
        by_name[os.path.basename(r["original_path"])].append(r)
    t3 = []
    for name, rs in by_name.items():
        if len(rs) > 1:
            a, b = (dict(imported[x["cid"]]["occurrences"]) for x in rs[:2])
            sh = set(a) & set(b)
            t3.append({"file": name, "shared": len(sh), "same_cid": sum(a[u] == b[u] for u in sh)})
    T["T3_relocated_copy_dedups"] = {"pass": bool(t3) and all(x["shared"] == x["same_cid"] for x in t3), "cases": t3}

    # T4 classification.
    dist = collections.Counter()
    for imp in list(imported.values()) + [himp]:
        for _, c in imp["occurrences"]:
            o = occ(imp, c)
            dist["%s|%s|%s" % (o["native_role"], o["actor_kind"], o["process_kind"])] += 1
    checks = {"no_actor_human": not any("|human|" in k for k in dist),
              "tool_results_tool": dist.get("user|tool|main", 0) > 0,
              "sidechain": any(k.endswith("|sidechain") for k in dist),
              "compaction": any("|compaction" in k for k in dist),
              "history_unknown": dist.get("prompt-history|unknown|unknown", 0) == len(himp["occurrences"]) > 0}
    T["T4_classification"] = {"pass": all(checks.values()), "checks": checks, "distribution": dict(dist.most_common())}

    # T5 truncated tail + corrupted line.
    r = sorted(main_tx, key=lambda r: r["bytes"])[len(main_tx) // 2]
    data = load(base, r)
    full = dict(imported[r["cid"]]["occurrences"])
    cut = data.rfind(b"\n", 0, len(data) // 2) + 40
    part = ci.import_transcript(data[:cut])
    same = sum(full.get(u) == c for u, c in part["occurrences"])
    nl = data.find(b"\n")
    cor = ci.import_transcript(data[:nl + 1] + b'{"type":"user","uuid":broken\n' + data[nl + 1:])
    T["T5_truncated_tail"] = {
        "pass": part["report"]["partial_tail"] == {"start": data.rfind(b"\n", 0, cut) + 1, "end": cut}
                and same == len(part["occurrences"]) > 0 and len(cor["report"]["parse_errors"]) == 1
                and len(cor["occurrences"]) == len(full),
        "raw": r["cid"], "partial_tail": part["report"]["partial_tail"], "occurrences_before_cut": len(part["occurrences"]),
        "same_cid_as_full": same, "corrupt_report": cor["report"]["parse_errors"]}

    # T6 same text, distinct events.
    uses = collections.defaultdict(set)
    for imp in imported.values():
        for _, c in imp["occurrences"]:
            o = occ(imp, c)
            if o["native_role"] == "user" and o["actor_kind"] == "unknown":
                for l in o["content"]:
                    uses[str(l)].add(str(c))
    multi = [s for s in uses.values() if len(s) > 1]
    T["T6_same_text_distinct_events"] = {"pass": bool(multi), "shared_contents": len(multi)}

    # T7 codec round trip; T8 identity objects never reach raw; anchors never linked back.
    total = bad = 0
    raw_in_identity = []
    anchor_cids, linked = set(), set()
    for imp in list(imported.values()) + [himp]:
        for cid, (v, data) in imp["store"].objects.items():
            total += 1
            if pc.encode(pc.decode(data)) != data or str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != cid:
                bad += 1
            if v["schema"] in ANCHOR_SCHEMAS:
                anchor_cids.add(cid)
                continue
            for l in links_in(v):
                linked.add(str(l))
                if codec_of(l) == pc.CODEC_RAW:
                    is_fallback = v["schema"] == "pkst/occurrence@0.1" and v["native_id"] is None and v["locator"] is not None
                    if not is_fallback:
                        raw_in_identity.append(cid)
    T["T7_codec_roundtrip"] = {"pass": bad == 0, "objects": total, "failed": bad}
    T["T8_no_raw_in_identity"] = {"pass": not raw_in_identity and not (anchor_cids & linked),
                                  "identity_objects_with_raw_link": len(raw_in_identity),
                                  "anchors_linked_back": len(anchor_cids & linked),
                                  "note": "only history.jsonl occurrences (native_id=null) carry the raw locator fallback"}

    # T9 history epoch-decimal time; T10 thinking/image never become content.
    h = [occ(himp, c) for _, c in himp["occurrences"]]
    T["T9_history_epoch"] = {"pass": all(o["event_time"]["format"] == "epoch-decimal" and o["event_time"]["unit"] == "ms"
                                         and o["event_time"]["value"].isdigit() and o["native_parent_ids"] is None for o in h),
                             "occurrences": len(h), "missing_paste_content": himp["report"]["missing_paste_content"]}
    br_types = collections.Counter()
    for imp in imported.values():
        for b in imp["block_references"]:
            v = imp["store"].objects[str(b)][0]
            target = occ(imp, v["occurrence"])["content"][v["ordinal"]]
            br_types[(v["native_type"], imp["store"].objects[str(target)][0]["schema"])] += 1
    leak = {"%s->%s" % k: n for k, n in br_types.items() if k[0] in ci.OPAQUE_BLOCKS and k[1] != "pkst/opaque-block@0.1"}
    T["T10_opaque_blocks"] = {"pass": not leak, "leaks": leak,
                              "block_types": {"%s->%s" % k: n for k, n in br_types.most_common()}}

    res = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "parser": ci.PARSER, "python": sys.version.split()[0], "tests": T,
           "all_pass": all(t["pass"] for t in T.values())}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: v["pass"] for k, v in T.items()}), "all_pass=%s" % res["all_pass"])
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
