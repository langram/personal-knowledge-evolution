"""Independent check of semantic-pairs v2 against v1 and the raw sources (Claude side).

Usage: python -I verify_semantic_pairs_v2_claude.py <archive root> <report.json> <readable.txt>
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402
import verify_semantic_pairs_claude as v1check  # noqa: E402

PREFIX = "[整理主题]"


def main(root, out, readable):
    sp = os.path.join(root, "contributions", "codex", "semantic-pairs")
    mine = os.path.join(root, "contributions", "claude")
    gem = os.path.join(root, "contributions", "codex", "gemini")
    rep = json.load(open(os.path.join(sp, "report.json"), encoding="utf-8"))
    rep1 = json.load(open(os.path.join(sp, "report-v1.json"), encoding="utf-8"))
    car = open(os.path.join(gem, ".private", "gemini-evidence.car"), "rb").read()
    hl, i = pc._read_uvarint(car, 0)
    i += hl
    gblocks = {}
    while i < len(car):
        sl, j = pc._read_uvarint(car, i)
        cid, k = vc.read_cid(car, j)
        gblocks[str(cid)] = car[k:j + sl]
        i = j + sl

    def get(c):
        for d in (os.path.join(sp, "objects"), os.path.join(mine, "objects")):
            p = os.path.join(d, c + ".cbor")
            if os.path.exists(p):
                data = open(p, "rb").read()
                break
        else:
            data = gblocks[c]
        if str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != c:
            raise pc.PkstError("hash mismatch " + c)
        return pc.decode(data)

    root_cid = rep["snapshot"]
    snap = get(root_cid)
    seen, stack, raws = set(), [root_cid], set()
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        for l in vc.links(get(c)):
            (raws.add(str(l)) if l.binary[1] == pc.CODEC_RAW else stack.append(str(l)))
    objs = {c: get(c) for c in seen}
    by = collections.defaultdict(dict)
    for c, v in objs.items():
        by[v["schema"]][c] = v
    # members of the new root only (exclude the parent snapshot's closure)
    members, stack = set(), [str(r) for r in snap["roots"]]
    while stack:
        c = stack.pop()
        if c in members:
            continue
        members.add(c)
        stack.extend(str(l) for l in vc.links(objs[c]) if l.binary[1] == pc.CODEC_DAG_CBOR and str(l) != rep["previous_snapshot"])
    cur = collections.defaultdict(dict)
    for c in members:
        cur[objs[c]["schema"]][c] = objs[c]
    P = collections.Counter()
    texts = {r["content"]: get(r["content"])["text"] for r in rep1["rows"]}
    w = open(readable, "w", encoding="utf-8")
    stmt_rows = []
    for c, s in cur["pkst/statement@0.1"].items():
        ev = [str(x) for x in s["evidence"]]
        hosts = [ct for ct, t in texts.items() if s["text"] in t]
        verbatim_once = len(hosts) == 1 and texts[hosts[0]].count(s["text"]) == 1
        if not verbatim_once:
            P["statement-not-verbatim-unique"] += 1
        if s["holder"]["kind"] != "unknown" or s["asserted_by"]["id"] != "codex":
            P["holder-or-asserted_by"] += 1
        abouts = [r for r in cur["pkst/relation@0.1"].values() if r["predicate"] == "about" and str(r["from"]) == c]
        topic = [objs[str(a["to"])]["label"] for a in abouts]
        stmt_rows.append((hosts[0] if hosts else None, s["force"], s["text"], topic))
    for host, force, text, topic in sorted(stmt_rows, key=lambda x: (x[0] or "", x[2])):
        w.write("[%s] %s | topic=%s\n    %s\n" % ((host or "?")[:16], force, topic, text))
    labels = [v["label"] for v in cur["pkst/concept@0.1"].values()]
    for l in labels:
        if not l.startswith(PREFIX):
            P["concept-label-prefix"] += 1
    w.write("\nCONCEPTS:\n" + "\n".join("  " + l for l in sorted(labels)) + "\n")
    for v in cur["pkst/concept@0.1"].values():
        w.write("  def: %s\n" % v["definition"])
    pcs_new = sorted(c for c, r in cur["pkst/relation@0.1"].items() if r["predicate"] == "propagation-candidate")
    pcs_old = sorted(r["propagation_candidate"] for r in rep1["rows"])
    if pcs_new != pcs_old:
        P["propagation-candidates-changed"] += 1
    preds = collections.Counter(r["predicate"] for r in cur["pkst/relation@0.1"].values())
    bad_pred = [p for p in preds if p not in ("about", "propagation-candidate")]
    if bad_pred:
        P["unexpected-predicates"] += 1
    if any(s in objs and objs[s]["schema"] == "pkst/change@0.1" for s in members):
        P["change-object-present"] += 1
    if [str(x) for x in snap["parents"]] != [rep["previous_snapshot"]]:
        P["parent"] += 1
    act = list(cur["pkst/activity@0.1"].values())
    w.write("\nACTIVITY COVERAGE:\n%s\n" % json.dumps(pc.to_projection(act[0]["coverage"]) if act else None, ensure_ascii=False, indent=1))
    w.write("\nSNAPSHOT COVERAGE:\n%s\n" % json.dumps(pc.to_projection(snap["coverage"]), ensure_ascii=False, indent=1))
    res = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "snapshot": root_cid, "parent": [str(x) for x in snap["parents"]], "closure_objects": len(seen), "closure_raw": len(raws),
           "current_members": len(members), "statements": len(cur["pkst/statement@0.1"]),
           "concepts": len(cur["pkst/concept@0.1"]), "relations": dict(preds),
           "propagation_candidates_identical_to_v1": pcs_new == pcs_old,
           "forces": dict(collections.Counter(r[1] for r in stmt_rows)), "problems": dict(P), "pass": not any(P.values())}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
