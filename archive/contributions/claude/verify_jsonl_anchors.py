"""Independent per-anchor verification of a Claude Code JSONL CAR (does not call claude_import_n3).

For every extraction-record: the raw byte range is exactly one JSONL line; the record re-derives the
occurrence identity, role, time, parent rule (N3.1) and the full content sequence; block-references resolve.

Usage: python -I verify_jsonl_anchors.py <contributions/claude dir> <car name> <report.json>
"""

import collections
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402
from verify_gemini_claude import resolve, project  # noqa: E402

TEXT = "text/plain;charset=utf-8"
OPAQUE = {"thinking", "redacted_thinking", "image"}


def expected_items(rec):
    t = rec.get("type")
    out = []
    if t == "attachment":
        a = rec.get("attachment")
        if isinstance(a, dict) and a.get("type") == "queued_command" and isinstance(a.get("prompt"), str):
            out.append(("content", a["prompt"]))
        out.append(("projection", project(a)))
        return out
    if t == "system":
        return [("content", rec["content"])] if isinstance(rec.get("content"), str) else []
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        return [("content", c)]
    for b in c or []:
        bt = b.get("type") if isinstance(b, dict) else None
        if bt == "text" and isinstance(b.get("text"), str):
            out.append(("content", b["text"]))
        elif bt in OPAQUE:
            out.append(("opaque", hashlib.sha256(project(b).encode("utf-8")).hexdigest()))
        else:
            out.append(("projection", project(b)))
    return out


def main(base, car_name, out):
    car = open(os.path.join(base, ".private", car_name), "rb").read()
    hl, i = pc._read_uvarint(car, 0)
    header = pc.decode(car[i:i + hl])
    i += hl
    blocks = {}
    while i < len(car):
        sl, j = pc._read_uvarint(car, i)
        cid, k = vc.read_cid(car, j)
        data = car[k:j + sl]
        assert pc.cid_for(data, pc.CODEC_DAG_CBOR) == cid
        blocks[str(cid)] = pc.decode(data)
        i = j + sl
    raws = {}

    def raw(link):
        s = str(link)
        if s not in raws:
            b = open(os.path.join(base, "raw", s + ".bin"), "rb").read()
            assert str(pc.raw_cid(b)) == s
            raws[s] = b
        return raws[s]

    P = collections.Counter()
    ex = {}

    def bad(k, c):
        P[k] += 1
        ex.setdefault(k, c)

    brs = collections.defaultdict(list)
    for c, v in blocks.items():
        if v["schema"] == "pkst/block-reference@0.1":
            brs[str(v["occurrence"])].append(v)
    roles = collections.Counter()
    n_er = 0
    for c, er in blocks.items():
        if er["schema"] != "pkst/extraction-record@0.1":
            continue
        n_er += 1
        o = blocks[str(er["occurrence"])]
        b = raw(er["raw"])
        s, e = er["start"], er["end"]
        if er["coordinate"] != "decoded-jsonl-utf8-bytes" or not (0 <= s < e <= len(b)) or \
                (s > 0 and b[s - 1:s] != b"\n") or b[e:e + 1] != b"\n" or b"\n" in b[s:e]:
            bad("range-not-one-line", c)
            continue
        rec = json.loads(b[s:e].decode("utf-8"))
        roles["%s|%s|%s" % (o["native_role"], o["actor_kind"], o["process_kind"])] += 1
        if o["actor_kind"] == "human":
            bad("actor-human", c)
        if o["native_id"] is None:  # history.jsonl locator fallback
            loc = o["locator"]
            if loc != {"raw": er["raw"], "start": s, "end": e, "coordinate": er["coordinate"]} or o["native_parent_ids"] is not None:
                bad("history-locator", c)
            if blocks[str(o["content"][0])].get("text") != rec.get("display"):
                bad("history-display", c)
            if o["event_time"]["format"] != "epoch-decimal" or o["event_time"]["value"] != str(rec.get("timestamp")):
                bad("history-time", c)
            continue
        if rec.get("uuid") != o["native_id"] or rec.get("type") != o["native_role"] or o["locator"] is not None:
            bad("identity", c)
        if o["event_time"]["value"] != rec.get("timestamp"):
            bad("time", c)
        want_parents = None if "parentUuid" not in rec else ([] if rec["parentUuid"] is None else [rec["parentUuid"]])
        if o["native_parent_ids"] != want_parents:
            bad("parents", c)
        thread = rec.get("sessionId") + ("/agent-%s" % rec["agentId"] if rec.get("agentId") else "")
        if blocks[str(o["source"])]["native_thread_id"] != thread:
            bad("thread", c)
        got = []
        for l in o["content"]:
            x = blocks[str(l)]
            kind = x["schema"].split("/")[1].split("@")[0]
            if kind == "content":
                got.append(("content", x["text"]))
                if x["media_type"] != TEXT:
                    bad("media-type", c)
            elif kind == "opaque-block":
                got.append(("opaque", x["digest"]))
            else:
                got.append(("projection", x["text"]))
        if got != expected_items(rec):
            bad("content-sequence", c)
        refs = brs.get(str(er["occurrence"]), [])
        if sorted(r["ordinal"] for r in refs) != list(range(len(o["content"]))):
            bad("block-ref-ordinals", c)
        for r in refs:
            try:
                resolve(rec, r["pointer"])
            except Exception:
                bad("block-ref-pointer", c)
    occs = [c for c, v in blocks.items() if v["schema"] == "pkst/occurrence@0.1"]
    with_er = {str(v["occurrence"]) for v in blocks.values() if v["schema"] == "pkst/extraction-record@0.1"}
    rep = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "car_root": str(header["roots"][0]), "car_blocks": len(blocks), "extraction_records": n_er,
           "occurrences": len(occs), "occurrences_without_er": len(set(occs) - with_er),
           "problems": dict(P), "problem_examples": ex, "role_actor_process": dict(roles),
           "pass": not P and not (set(occs) - with_er)}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
