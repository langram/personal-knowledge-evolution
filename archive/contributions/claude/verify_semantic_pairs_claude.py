"""Independent structural check of contributions/codex/semantic-pairs (Claude side; no Codex code or catalog DB).

Resolves Claude.ai objects from contributions/claude/objects and Gemini objects from the Gemini CAR;
verifies statements, quotes, anchors against raw, relations and closure. Prints counts only.

Usage: python -I verify_semantic_pairs_claude.py <archive root> <report.json>
"""

import collections
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402
from verify_gemini_claude import resolve  # noqa: E402


def main(root, out):
    sp = os.path.join(root, "contributions", "codex", "semantic-pairs")
    mine = os.path.join(root, "contributions", "claude")
    gem = os.path.join(root, "contributions", "codex", "gemini")
    rep = json.load(open(os.path.join(sp, "report.json"), encoding="utf-8"))
    car = open(os.path.join(gem, ".private", "gemini-evidence.car"), "rb").read()
    hl, i = pc._read_uvarint(car, 0)
    i += hl
    gblocks = {}
    while i < len(car):
        sl, j = pc._read_uvarint(car, i)
        cid, k = vc.read_cid(car, j)
        gblocks[str(cid)] = car[k:j + sl]
        i = j + sl
    where = collections.Counter()

    def get(c):
        for d, tag in ((os.path.join(sp, "objects"), "pairs"), (os.path.join(mine, "objects"), "claude")):
            p = os.path.join(d, c + ".cbor")
            if os.path.exists(p):
                data = open(p, "rb").read()
                break
        else:
            data, tag = gblocks.get(c), "gemini-car"
            if data is None:
                raise KeyError(c)
        if str(pc.cid_for(data, pc.CODEC_DAG_CBOR)) != c:
            raise pc.PkstError("hash mismatch " + c)
        where[tag] += 1
        return pc.decode(data)

    raws = {}

    def raw_doc(link):
        s = str(link)
        if s not in raws:
            for d in (os.path.join(mine, "raw"), os.path.join(gem, "raw")):
                p = os.path.join(d, s + ".bin")
                if os.path.exists(p):
                    b = open(p, "rb").read()
                    assert str(pc.raw_cid(b)) == s
                    raws[s] = json.loads(b.decode("utf-8"))
                    break
            else:
                raise KeyError(s)
        return raws[s]

    # closure + acyclicity from the snapshot
    snap_cid = rep["snapshot"]
    seen, order, stack = set(), [], [snap_cid]
    raw_links = set()
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        v = get(c)
        for l in vc.links(v):
            (raw_links.add(str(l)) if l.binary[1] == pc.CODEC_RAW else stack.append(str(l)))
    P = collections.Counter()
    snap = get(snap_cid)
    if str(snap["protocol"]) != "bafkreids4w2sc4l7uwnhrsjofo3hwyxiafaqyzl5rgn6tqjm3nysxd44fq":
        P["snapshot-protocol"] += 1
    rows_out = []
    for row in rep["rows"]:
        st = get(row["statement"])
        content = get(row["content"])
        text = content["text"]
        r = {"quote_len": len(row["quote"]), "force": st["force"]}
        if st["text"] != row["quote"] or text.count(row["quote"]) != 1 or text[row["quote_start"]:row["quote_end"]] != row["quote"]:
            P["quote"] += 1
        if st["holder"]["kind"] != "unknown" or st["asserted_by"] != {"kind": "ai", "id": "codex"} or st["lineage"] is not None:
            P["statement-fields"] += 1
        ev = [str(x) for x in st["evidence"]]
        if ev != sorted(ev, key=lambda s: pc.Link.parse(s).binary) or set(ev) != set(row["evidence"]):
            P["evidence-set"] += 1
        times = []
        for e in row["events"]:
            o = get(e["occurrence"])
            if row["content"] not in [str(x) for x in o["content"]]:
                P["occurrence-lacks-content"] += 1
            if o["actor_kind"] != "unknown":
                P["actor-not-unknown"] += 1
            src = get(str(o["source"]))
            for erc in e["extraction_records"]:
                er = get(erc)
                node = resolve(raw_doc(er["raw"]), er["pointer"])
                if src["platform"] == "claude-ai":
                    ok = node.get("uuid") == o["native_id"] and node.get("text") == text
                else:
                    ok = node == "Prompted " + text
                P["anchor-bad"] += not ok
            times.append((o["event_time"]["value"], src["platform"]))
        times.sort()
        r["earlier_platform"] = times[0][1]
        r["gap"] = [t[0] for t in times]
        ab = get(row["about"])
        if ab["predicate"] != "about" or str(ab["from"]) != row["statement"] or ab["basis"] != "inferred":
            P["about"] += 1
        pcand = get(row["propagation_candidate"])
        ends = [pcand["from"].binary, pcand["to"].binary]
        if pcand["predicate"] != "propagation-candidate" or ends != sorted(ends) or \
                {str(pcand["from"]), str(pcand["to"])} != {e["occurrence"] for e in row["events"]}:
            P["propagation"] += 1
        rows_out.append(r)
    concepts = {lab: get(c) for lab, c in rep["concepts"].items()}
    label_in_source = {}
    for lab in concepts:
        label_in_source[lab] = any(lab in get(row["content"])["text"] for row in rep["rows"])
    result = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "snapshot": snap_cid, "closure_objects": len(seen), "closure_raw": len(raw_links),
              "resolved_from": dict(where), "raw_documents_parsed": len(raws), "problems": dict(P),
              "rows": rows_out, "concept_label_verbatim_in_any_source": label_in_source,
              "pass": not any(P.values())}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if not any(P.values()) else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
