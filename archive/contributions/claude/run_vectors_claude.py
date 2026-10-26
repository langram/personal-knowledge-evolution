"""Run protocol/test-vectors.json against the Claude-side codec.

Usage: python -I run_vectors_claude.py <test-vectors.json> <results.json>
"""

import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402


def run_positive(vec):
    value = pc.from_projection(vec["value"])
    data, cid = pc.object_cid(value)
    pc.check_sets(value)
    back = pc.decode(data)
    roundtrip = pc.encode(back) == data and pc.to_projection(back) == vec["value"]
    return {
        "name": vec["name"],
        "cbor_hex": data.hex(),
        "cid": str(cid),
        "hex_match": data.hex() == vec["cbor_hex"],
        "cid_match": str(cid) == vec["cid"],
        "decode_roundtrip": roundtrip,
    }


def expect_reject(name, fn):
    try:
        fn()
    except pc.PkstError as exc:
        return {"name": name, "rejected": True, "error": str(exc)}
    return {"name": name, "rejected": False, "error": None}


# Byte-level corruption cases the decoder must refuse (Claude additions).
EXTRA_CBOR_NEGATIVE = [
    ("non-minimal-int", "1817"),            # 23 encoded with 1-byte arg
    ("map-wrong-order","a262616102616201"),  # "aa" before "b": violates length-first
    ("dup-map-key", "a2616101616102"),
    ("float16", "f93c00"),
    ("undefined", "f7"),
    ("indefinite-array", "9fff"),
    ("unknown-tag", "d90100f6"),
    ("bare-bytes", "4100"),
    ("trailing-bytes", "f6f6"),
    ("truncated", "6261"),
    ("bad-utf8", "61ff"),
    ("int-overflow", "1b0020000000000000"),
    ("tag42-no-prefix", "d82a5824015512202cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
    ("tag42-bad-codec", "d82a582500017012202cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"),
]


def main(vec_path, out_path):
    raw = open(vec_path, "rb").read()
    vectors = json.loads(raw.decode("utf-8"), object_pairs_hook=pc._no_dup)

    positives = [run_positive(v) for v in vectors["positive"]]
    negatives = [expect_reject(v["name"], lambda v=v: pc.encode(pc.from_projection(v["value"])))
                 for v in vectors["negative"]]
    negatives += [expect_reject("json:%s" % t, lambda t=t: pc.loads_json(t)) for t in vectors["negative_json"]]

    extra = [expect_reject(n, lambda h=h: pc.decode(bytes.fromhex(h)))
             for n, h in EXTRA_CBOR_NEGATIVE]
    # CID/content mismatch: a stored block whose bytes do not hash to its claimed CID.
    good = positives[0]

    def mismatch():
        if str(pc.cid_for(bytes.fromhex("f5"), pc.CODEC_DAG_CBOR)) != good["cid"]:
            raise pc.PkstError("block bytes do not match claimed CID")
    extra.append(expect_reject("cid-content-mismatch", mismatch))
    extra.append(expect_reject("unsorted-set-evidence", lambda: pc.check_sets({"evidence": [
        pc.Link.parse("bafyreig4mdkigvkzrnglo6d6yqbow6l5mouasatjpnggvarahttoajuu7u"),
        pc.Link.parse("bafyreib3idwh7hsciniu2cmzewhcraco5wwb4xwroozrivc2shfr5e2wji")]})))
    extra.append(expect_reject("uppercase-cid", lambda: pc.Link.parse(
        "bAFYREIG4MDKIGVKZRNGLO6D6YQBOW6L5MOUASATJPNGGVARAHTTOAJUU7U")))
    extra.append(expect_reject("cidv0", lambda: pc.Link.parse("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")))

    ok_pos = sum(p["hex_match"] and p["cid_match"] and p["decode_roundtrip"] for p in positives)
    ok_neg = sum(n["rejected"] for n in negatives)
    ok_extra = sum(n["rejected"] for n in extra)
    result = {
        "implementation": "contributions/claude/pkst_cbor_claude.py",
        "implementation_sha256": hashlib.sha256(open(pc.__file__, "rb").read()).hexdigest(),
        "vectors": vec_path.replace("\\", "/").split("personal-thought-archive/")[-1],
        "vectors_sha256": hashlib.sha256(raw).hexdigest(),
        "python": sys.version.split()[0],
        "ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "positive_pass": "%d/%d" % (ok_pos, len(positives)),
            "negative_rejected": "%d/%d" % (ok_neg, len(negatives)),
            "claude_extra_negative_rejected": "%d/%d" % (ok_extra, len(extra)),
        },
        "positive": positives,
        "negative": negatives,
        "claude_extra_negative": extra,
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result["summary"]))
    for p in positives:
        if not (p["hex_match"] and p["cid_match"] and p["decode_roundtrip"]):
            print("FAIL", p["name"], p)
    for n in negatives + extra:
        if not n["rejected"]:
            print("NOT REJECTED", n["name"])
    return 0 if ok_pos == len(positives) and ok_neg == len(negatives) and ok_extra == len(extra) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
