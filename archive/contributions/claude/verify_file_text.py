"""Acceptance checks for FILE-TEXT 0.1 (separate code path from convert_file_text.py for the real data).

Usage: python -I verify_file_text.py <contributions/claude dir> <mac capture manifest.jsonl> <car name> <report.json>
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402
import convert_file_text as ft  # noqa: E402  (synthetic cases only)

UNKNOWN = {"value": None, "format": "unknown", "precision": "unknown", "zone_known": False, "unit": None}


def main(base, manifest_path, car_name, out):
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
    rows = [json.loads(l) for l in open(manifest_path, encoding="utf-8")][1:]
    want = {r["cid"]: r for r in rows if r["category"] == "claude-code-project-memory"}
    P = []
    occs = {c: v for c, v in blocks.items() if v["schema"] == "pkst/occurrence@0.1"}
    ers = {str(v["occurrence"]): v for v in blocks.values() if v["schema"] == "pkst/extraction-record@0.1"}
    got_raw = set()
    for c, o in occs.items():
        loc = o["locator"]
        raw = open(os.path.join(base, "raw", str(loc["raw"]) + ".bin"), "rb").read()
        got_raw.add(str(loc["raw"]))
        er = ers.get(c)
        checks = {
            "role": o["native_role"] == "derived-memory:claude-code",
            "ids": o["native_id"] is None and o["native_parent_ids"] is None,
            "actor_process": o["actor_kind"] == "unknown" and o["process_kind"] == "unknown",
            "time_unknown": o["event_time"] == UNKNOWN,
            "locator": loc["coordinate"] == "file-bytes" and type(loc["start"]) is int and type(loc["end"]) is int
                       and loc["start"] == 0 and loc["end"] == len(raw),
            "er_matches": er is not None and er["coordinate"] == "file-bytes" and er["raw"] == loc["raw"]
                          and er["start"] == loc["start"] and er["end"] == loc["end"] and "pointer" not in er,
            "text_verbatim": len(o["content"]) == 1 and blocks[str(o["content"][0])]["text"] == raw[loc["start"]:loc["end"]].decode("utf-8", "strict")
                             and blocks[str(o["content"][0])]["media_type"] == "text/plain;charset=utf-8",
            "source": blocks[str(o["source"])]["platform"] == "claude-code-memory"
                      and blocks[str(o["source"])]["native_thread_id"] == "raw:%s" % loc["raw"],
            "in_manifest": str(loc["raw"]) in want,
        }
        P += ["%s:%s" % (c[:16], k) for k, ok in checks.items() if not ok]
    human = [c for c, v in blocks.items() if v["schema"] == "pkst/occurrence@0.1" and v["actor_kind"] == "human"]
    semantic = [c for c, v in blocks.items() if v["schema"] in ("pkst/statement@0.1", "pkst/concept@0.1", "pkst/relation@0.1",
                                                              "pkst/change@0.1", "pkst/assessment@0.1")]
    # synthetic acceptance cases
    link = pc.raw_cid(b"x")
    syn = {}
    for name, b in (("crlf-bom-cjk", "﻿第一行\r\n第二行\r\n".encode("utf-8")), ("no-trailing-newline", "末尾无换行".encode("utf-8")),
                    ("empty", b"")):
        objs, err = ft.file_objects(b, link, "fx", link)
        syn[name] = err is None and objs[1]["text"] == b.decode("utf-8") and objs[1]["text"].encode("utf-8") == b
    objs, err = ft.file_objects(b"ok\xff\xfe", link, "fx", link)
    syn["invalid-utf8-rejected"] = err is not None and objs == []
    objs, err = ft.file_objects("\ud800".encode("utf-8", "surrogatepass"), link, "fx", link)
    syn["encoded-surrogate-rejected"] = err is not None
    rep = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "car_root": str(header["roots"][0]), "car_blocks": len(blocks),
           "memory_files_in_manifest": len(want), "occurrences": len(occs),
           "raw_set_equals_manifest": got_raw == set(want), "problems": P,
           "actor_human": len(human), "semantic_objects": len(semantic), "synthetic": syn}
    rep["pass"] = (not P and rep["raw_set_equals_manifest"] and len(occs) == len(want) and not human and not semantic
                   and all(syn.values()))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
