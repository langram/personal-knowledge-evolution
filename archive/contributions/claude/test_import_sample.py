"""Small-sample importer checks on captured raw blocks (no objects are persisted).

Usage: python -I test_import_sample.py <contributions/claude dir> <manifest.jsonl> <results.json>
Results contain counts, CIDs and native IDs only; no message text.
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import claude_import_sample as ci  # noqa: E402

CURRENT_SESSION = "c3786c20-7156-40f9-af46-1d48236cd965"


def load(base, row):
    data = open(os.path.join(base, "raw", row["cid"] + ".bin"), "rb").read()
    assert str(pc.raw_cid(data)) == row["cid"], "raw block corrupted: " + row["cid"]
    return data


def main(base, manifest, out):
    rows = [json.loads(l) for l in open(manifest, encoding="utf-8")]
    tx = [r for r in rows if r.get("kind") in ("claude-code-transcript", "claude-code-subagent-transcript")]
    main_tx = [r for r in tx if r["kind"] == "claude-code-transcript" and r["bytes"] > 1000]
    res = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "manifest": os.path.basename(manifest), "parser": ci.PARSER, "tests": {}}
    T = res["tests"]

    # Import every captured transcript once (in memory) to find real cases.
    imported = {}
    for r in tx:
        imported[r["cid"]] = ci.import_block(load(base, r), pc.Link.parse(r["cid"]))

    # T1 re-import of the same fixed bytes yields identical object sets.
    sample = sorted(main_tx, key=lambda r: -r["bytes"])[:2] + [r for r in tx if r["kind"] == "claude-code-subagent-transcript"][:1]
    t1 = []
    for r in sample:
        again = ci.import_block(load(base, r), pc.Link.parse(r["cid"]))
        t1.append({"raw": r["cid"], "objects": len(again["objects"]),
                   "identical": set(again["objects"]) == set(imported[r["cid"]]["objects"])})
    T["T1_reimport_idempotent"] = {"pass": all(x["identical"] for x in t1), "cases": t1}

    # T2 native-parent forks are preserved, not linearised.
    forks = collections.Counter()
    example = None
    real_forks = real_kept = 0
    for r in main_tx:
        objs = imported[r["cid"]]["objects"]
        kids = collections.defaultdict(list)
        for uid, ocid in imported[r["cid"]]["occurrences"]:
            o = objs[str(ocid)]
            if o["native_parent_ids"]:
                kids[o["native_parent_ids"][0]].append(o)
        for parent, children in kids.items():
            if len(children) < 2:
                continue
            pattern = "+".join(sorted("%s/%s" % (c["native_role"], c["actor_kind"]) for c in children))
            forks[pattern] += 1
            real_forks += 1
            real_kept += all(c["native_parent_ids"] == [parent] for c in children)
            human_like = [c for c in children if c["native_role"] == "user" and c["actor_kind"] == "unknown"]
            if example is None and len(human_like) >= 2:
                example = {"raw": r["cid"], "parent_native_id": parent,
                           "children_native_ids": [c["native_id"] for c in human_like],
                           "all_kept": all(c["native_parent_ids"] == [parent] for c in human_like)}
    # The corpus has no user edit/rewind fork, so that case is checked on a synthetic fixture.
    fx = "\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"type": "user", "uuid": "u1", "parentUuid": None, "sessionId": "fx", "timestamp": "2026-01-01T00:00:00.000Z",
         "message": {"role": "user", "content": "问题"}},
        {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:01.000Z",
         "message": {"role": "assistant", "content": [{"type": "text", "text": "回答"}]}},
        {"type": "user", "uuid": "u2a", "parentUuid": "a1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:02.000Z",
         "message": {"role": "user", "content": "版本一"}},
        {"type": "user", "uuid": "u2b", "parentUuid": "a1", "sessionId": "fx", "timestamp": "2026-01-01T00:00:03.000Z",
         "message": {"role": "user", "content": "版本二"}},
    ]).encode("utf-8") + b"\n"
    fimp = ci.import_block(fx)
    fo = {u: fimp["objects"][str(c)] for u, c in fimp["occurrences"]}
    synthetic_ok = (fo["u2a"]["native_parent_ids"] == ["a1"] == fo["u2b"]["native_parent_ids"]
                    and fo["u2a"]["content"] != fo["u2b"]["content"] and len(fo) == 4)
    T["T2_fork_preserved"] = {"pass": real_forks > 0 and real_kept == real_forks and synthetic_ok,
                              "real_fork_points": real_forks, "real_forks_all_children_kept": real_kept,
                              "fork_patterns": dict(forks.most_common(12)),
                              "user_edit_or_rewind_example_in_corpus": example,
                              "synthetic_user_rewind_fixture_ok": synthetic_ok}

    # T3 the same session stored under two project dirs (relocation) -> identical occurrence CIDs.
    by_stem = collections.defaultdict(list)
    for r in main_tx:
        by_stem[os.path.basename(r["original_path"])].append(r)
    t3 = []
    for stem, rs in by_stem.items():
        if len(rs) < 2:
            continue
        a, b = (dict(imported[x["cid"]]["occurrences"]) for x in rs[:2])
        shared = set(a) & set(b)
        t3.append({"file": stem, "raws": [x["cid"] for x in rs[:2]], "shared_native_ids": len(shared),
                   "same_occurrence_cid": sum(a[u] == b[u] for u in shared)})
    T["T3_relocated_copy_dedups"] = {"pass": bool(t3) and all(x["shared_native_ids"] == x["same_occurrence_cid"] for x in t3),
                                     "cases": t3}

    # T4 attribution: role/actor/process distribution plus targeted checks.
    dist = collections.Counter()
    checks = {}
    for r in tx:
        imp = imported[r["cid"]]
        for uid, ocid in imp["occurrences"]:
            o = imp["objects"][str(ocid)]
            dist["%s|%s|%s" % (o["native_role"], o["actor_kind"], o["process_kind"])] += 1
    for er in (e for imp in imported.values() for e in imp["extraction_records"]):
        pass
    er_basis = collections.Counter()
    for imp in imported.values():
        for ecid in imp["extraction_records"]:
            e = imp["objects"][str(ecid)]
            o = imp["objects"][str(e["occurrence"])]
            b = e["role_basis"]
            if "origin.kind=human" in b and o["native_role"] == "user":
                er_basis["user+origin.kind=human -> %s" % o["actor_kind"]] += 1
            if "attachment=queued_command" in b:
                er_basis["queued_command -> %s/%s" % (o["actor_kind"], o["process_kind"])] += 1
            if "isCompactSummary" in b:
                er_basis["compact_summary -> %s/%s" % (o["actor_kind"], o["process_kind"])] += 1
    checks["no_user_record_labelled_human"] = not any(k.startswith("user|human") for k in dist)
    checks["tool_results_are_tool"] = dist.get("user|tool|main", 0) > 0
    checks["sidechain_present"] = any(k.endswith("|sidechain") for k in dist)
    checks["compaction_classified"] = any("compaction" in k for k in dist)
    T["T4_attribution"] = {"pass": all(checks.values()), "checks": checks, "distribution": dict(dist.most_common()),
                           "basis_notes": dict(er_basis),
                           "note": "Native origin.kind=human marks the desktop input channel; PKST-N1/N2 typed by Codex via Computer Use carry it too, so actor_kind stays unknown."}

    # T5 truncated tail and corrupted middle line.
    r = sorted(main_tx, key=lambda r: r["bytes"])[len(main_tx) // 2]
    data = load(base, r)
    full = imported[r["cid"]]
    cut = data.rfind(b"\n", 0, len(data) // 2) + 40
    part = ci.import_block(data[:cut])
    full_occ = dict(full["occurrences"])
    same = sum(full_occ.get(u) == c for u, c in part["occurrences"])
    first_nl = data.find(b"\n")
    corrupt = data[:first_nl + 1] + b'{"type":"user","uuid":broken\n' + data[first_nl + 1:]
    cor = ci.import_block(corrupt)
    T["T5_truncated_tail"] = {
        "pass": bool(part["report"]["partial_tail"]) and same == len(part["occurrences"]) and len(part["occurrences"]) > 0
                and len(cor["report"]["parse_errors"]) == 1 and len(cor["occurrences"]) == len(full["occurrences"]),
        "raw": r["cid"], "cut_at": cut, "partial_tail": part["report"]["partial_tail"],
        "occurrences_before_cut": len(part["occurrences"]), "same_occurrence_cid_as_full": same,
        "extraction_records_differ": not set(map(str, part["extraction_records"])) & set(map(str, full["extraction_records"])),
        "corrupt_line_report": cor["report"]["parse_errors"], "occurrences_after_corruption": len(cor["occurrences"]),
    }

    # T6 same text, different events.
    uses = collections.defaultdict(set)
    for imp in imported.values():
        for uid, ocid in imp["occurrences"]:
            o = imp["objects"][str(ocid)]
            if o["native_role"] == "user" and o["actor_kind"] == "unknown":
                for c in o["content"]:
                    uses[str(c)].add(str(ocid))
    multi = {c: s for c, s in uses.items() if len(s) > 1}
    T["T6_same_text_distinct_events"] = {"pass": bool(multi), "shared_content_cids": len(multi),
                                         "max_events_per_content": max((len(s) for s in multi.values()), default=0)}

    # T7 every produced object round-trips through the codec.
    total = bad = 0
    for imp in imported.values():
        for cid, v in imp["objects"].items():
            total += 1
            data, c2 = pc.object_cid(v)
            if str(c2) != cid or pc.encode(pc.decode(data)) != data:
                bad += 1
    T["T7_codec_roundtrip"] = {"pass": bad == 0, "objects": total, "failed": bad}

    rep = collections.Counter()
    nonocc = collections.Counter()
    for imp in imported.values():
        rep["lines"] += imp["report"]["lines"]
        rep["occurrences"] += imp["report"]["occurrences"]
        rep["parse_errors"] += len(imp["report"]["parse_errors"])
        rep["missing_native_id"] += imp["report"]["missing_native_id"]
        rep["partial_tails"] += bool(imp["report"]["partial_tail"])
        nonocc.update(imp["report"]["non_occurrence_records"])
    res["dry_run_totals"] = dict(rep)
    res["non_occurrence_record_types"] = dict(nonocc)
    res["all_pass"] = all(t["pass"] for t in T.values())
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: v["pass"] for k, v in T.items()}), "all_pass=%s" % res["all_pass"])
    print(json.dumps(res["dry_run_totals"]))
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
