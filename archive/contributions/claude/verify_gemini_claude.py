"""Independent semantic-adapter check of the Codex Gemini Takeout CAR (Claude side).

Reads only: the CAR, the Codex gemini raw/ dir, the members manifest. Never extracts the ZIP
to disk, never fetches URLs, never renders HTML. Uses the Claude codec and its own RFC 6901 resolver.

Usage: python -I verify_gemini_claude.py <codex gemini dir> <report.json>
"""

import collections
import datetime
import hashlib
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pkst_cbor_claude as pc  # noqa: E402
import verify_car_claude as vc  # noqa: E402

APP_URL = re.compile(r"^https://gemini\.google\.com/app/([A-Za-z0-9_-]+)$")


def resolve(doc, pointer):
    """RFC 6901; strict array indices; raises on any miss."""
    if pointer == "":
        return doc
    if not pointer.startswith("/"):
        raise KeyError("pointer must start with /")
    node = doc
    for tok in pointer[1:].split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", tok):
                raise KeyError("bad array index %r" % tok)
            node = node[int(tok)]
        elif isinstance(node, dict):
            node = node[tok]
        else:
            raise KeyError("pointer descends into scalar")
    return node


def project(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def main(gdir, out):
    priv = os.path.join(gdir, ".private")
    raw_dir = os.path.join(gdir, "raw")
    car = open(os.path.join(priv, "gemini-evidence.car"), "rb").read()
    blocks = {}
    hl, i = pc._read_uvarint(car, 0)
    header = pc.decode(car[i:i + hl])
    i += hl
    while i < len(car):
        sl, j = pc._read_uvarint(car, i)
        cid, k = vc.read_cid(car, j)
        blocks[str(cid)] = pc.decode(car[k:j + sl])
        i = j + sl
    by_schema = collections.defaultdict(dict)
    for c, v in blocks.items():
        by_schema[v["schema"]][c] = v
    R = {"ran_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "checks": {}, "findings": {}}
    C, F = R["checks"], R["findings"]

    # --- 1. ZIP members re-derived independently from the archive raw block (in memory only).
    cap = [json.loads(l) for l in open([os.path.join(priv, f) for f in os.listdir(priv) if f.startswith("members-")][0], encoding="utf-8")]
    zcid = cap[0]["archive"]
    zbytes = open(os.path.join(raw_dir, zcid + ".bin"), "rb").read()
    zip_ok = str(pc.raw_cid(zbytes)) == zcid
    member_bad, names = 0, collections.Counter()
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        infos = [x for x in z.infolist() if not x.is_dir()]
        for row, info in zip(cap, infos):
            data = z.read(info)
            names[info.filename] += 1
            member_bad += not (row["member_name"] == info.filename and row["raw_cid"] == str(pc.raw_cid(data))
                               and os.path.exists(os.path.join(raw_dir, row["raw_cid"] + ".bin")))
    distinct_member_cids = len({r["raw_cid"] for r in cap})
    C["zip_members"] = {"pass": zip_ok and member_bad == 0 and len(infos) == len(cap), "zip_raw_ok": zip_ok,
                        "members": len(infos), "manifest_rows": len(cap), "mismatches": member_bad,
                        "distinct_member_raw_cids": distinct_member_cids,
                        "duplicate_member_names": sum(1 for n in names.values() if n > 1)}

    # snapshot / activity raw links
    snap = next(iter(by_schema["pkst/snapshot@0.1"].values()))
    raw_links = {str(l) for v in blocks.values() for l in vc.links(v) if l.binary[1] == pc.CODEC_RAW}
    F["zip_archive_raw_linked_from_objects"] = zcid in raw_links
    F["snapshot_protocol"] = str(snap.get("protocol"))
    F["snapshot_roots"] = len(snap["roots"])

    # --- 2. The activity document: strict parse, my own grouping.
    ers = by_schema["pkst/extraction-record@0.1"]
    doc_cids = collections.Counter(str(e["raw"]) for e in ers.values())
    doc_cid = doc_cids.most_common(1)[0][0]
    doc_bytes = open(os.path.join(raw_dir, doc_cid + ".bin"), "rb").read()
    dup_key_error = None
    try:
        doc = json.loads(doc_bytes.decode("utf-8"), object_pairs_hook=pc._no_dup)
    except pc.PkstError as exc:
        dup_key_error = str(exc)
        doc = json.loads(doc_bytes.decode("utf-8"))
    F["document_raw"] = doc_cid
    F["document_raw_used_by_all_extraction_records"] = len(doc_cids) == 1
    F["document_duplicate_keys"] = dup_key_error
    F["entries"] = len(doc)
    titles = collections.Counter()
    url_shapes = collections.Counter()
    ids_per_entry = collections.Counter()
    entry_ids = []
    all_ids = set()
    for e in doc:
        t = e.get("title", "")
        titles[t.split(" ", 1)[0] if t else "<none>"] += 1
        ids = []
        for d in e.get("details", []) or []:
            u = d.get("url") if isinstance(d, dict) else None
            if u is None:
                continue
            m = APP_URL.match(u)
            url_shapes["app-exact" if m else ("gemini-other" if "gemini.google.com" in u else "other")] += 1
            if m:
                ids.append(m.group(1))
        uniq = sorted(set(ids))
        entry_ids.append(uniq)
        ids_per_entry[min(len(uniq), 2)] += 1
        all_ids.update(uniq)
    F["title_first_words"] = dict(titles.most_common(15))
    F["detail_url_shapes"] = dict(url_shapes)
    F["entries_by_distinct_app_ids"] = {"0": ids_per_entry[0], "1": ids_per_entry[1], ">=2": ids_per_entry[2]}
    F["distinct_app_ids_all_entries"] = len(all_ids)
    F["distinct_app_ids_single_id_entries"] = len({x[0] for x in entry_ids if len(x) == 1})
    prefix_exact = sum(1 for e in doc if e.get("title", "").startswith("Prompted "))
    prefix_loose = sum(1 for e in doc if e.get("title", "").lower().startswith("prompted"))
    F["prompted_prefix"] = {"exact 'Prompted '": prefix_exact, "case/space-insensitive": prefix_loose}

    # --- 3. Every occurrence: pointer, content/projection equality, role, time, grouping.
    occs = by_schema["pkst/occurrence@0.1"]
    er_by_occ = {str(e["occurrence"]): e for e in ers.values()}
    srcs = by_schema["pkst/source@0.1"]
    problems = collections.Counter()
    roles = collections.Counter()
    time_formats = collections.Counter()
    examples = {}

    def bad(kind, cid):
        problems[kind] += 1
        examples.setdefault(kind, cid)

    for ocid, o in occs.items():
        loc = o.get("locator")
        er = er_by_occ.get(ocid)
        if er is None:
            bad("no-extraction-record", ocid)
            continue
        if not (isinstance(loc, dict) and loc.get("coordinate") == "json-pointer" and "start" not in loc and "end" not in loc
                and str(loc.get("raw")) == doc_cid and loc.get("pointer") == er.get("pointer")):
            bad("locator-shape-or-mismatch", ocid)
        if er.get("coordinate") != "json-pointer" or "start" in er or "end" in er:
            bad("er-coordinate", ocid)
        if o.get("native_id") is not None:
            bad("native-id-not-null", ocid)
        if o.get("native_parent_ids") is not None:
            bad("parent-ids-not-null", ocid)
        ptr = er["pointer"]
        try:
            node = resolve(doc, ptr)
        except Exception:
            bad("pointer-unresolvable", ocid)
            continue
        m = re.match(r"^/(0|[1-9][0-9]*)(/.*)?$", ptr)
        entry = doc[int(m.group(1))]
        role = o["native_role"]
        roles["%s|%s|%s" % (role, o["actor_kind"], o["process_kind"])] += 1
        items = [blocks[str(l)] for l in o["content"]]
        et = o["event_time"]
        time_formats["%s|%s|%s" % (role.split(":")[0], et.get("format"), et.get("precision"))] += 1
        if role == "Prompted":
            title = entry.get("title", "")
            if ptr != "/%s/title" % m.group(1) or not title.startswith("Prompted "):
                bad("prompted-pointer-or-prefix", ocid)
            elif not (len(items) == 1 and items[0]["schema"] == "pkst/content@0.1" and items[0]["text"] == title[len("Prompted "):]):
                bad("prompted-text-not-verbatim", ocid)
            if et.get("value") != entry.get("time"):
                bad("prompted-time-not-entry-time", ocid)
        elif role == "safeHtmlItem":
            if not re.fullmatch(r"/(0|[1-9][0-9]*)/safeHtmlItem/(0|[1-9][0-9]*)", ptr):
                bad("html-pointer-shape", ocid)
            if not (len(items) == 1 and items[0]["schema"] == "pkst/projection@0.1" and items[0]["text"] == project(node)):
                bad("html-projection-mismatch", ocid)
            if set(node) != {"html"}:
                bad("html-node-extra-keys", ocid)
            if et.get("value") is not None or et.get("format") != "unknown":
                bad("html-time-not-unknown", ocid)
            if o["actor_kind"] != "ai":
                bad("html-actor-not-ai", ocid)
        elif role.startswith("activity:"):
            if not (len(items) == 1 and items[0]["schema"] == "pkst/projection@0.1" and items[0]["text"] == project(entry)):
                bad("activity-projection-mismatch", ocid)
            if o["actor_kind"] != "unknown":
                bad("activity-actor-not-unknown", ocid)
        else:
            bad("unexpected-role", ocid)
        # grouping
        src = srcs[str(o["source"])]
        ids = entry_ids[int(m.group(1))]
        if len(ids) == 1:
            if src["native_thread_id"] != ids[0]:
                bad("thread-id-mismatch", ocid)
        else:
            if src["native_thread_id"] != "raw:%s#/%s" % (doc_cid, m.group(1)):
                bad("fallback-thread-mismatch", ocid)
    C["occurrences"] = {"pass": not problems, "occurrences": len(occs), "problems": dict(problems), "examples": examples}
    F["role_actor_process"] = dict(roles)
    F["time_format_by_role"] = dict(time_formats)

    # --- 4. Entries vs occurrences coverage: every entry produced something; safeHtml count.
    covered = collections.Counter()
    for e in ers.values():
        covered[int(e["pointer"].split("/")[1])] += 1
    F["entries_without_occurrence"] = [k for k in range(len(doc)) if k not in covered][:20]
    F["safeHtmlItem_nodes_in_document"] = sum(len(e.get("safeHtmlItem", []) or []) for e in doc)
    F["entries_with_multiple_safeHtmlItem"] = sum(1 for e in doc if len(e.get("safeHtmlItem", []) or []) > 1)
    F["entries_with_prompt_and_no_html"] = sum(1 for e in doc if e.get("title", "").startswith("Prompted ") and not e.get("safeHtmlItem"))
    tprec = collections.Counter()
    for e in doc:
        t = e.get("time", "")
        frac = t.split(".", 1)[1] if "." in t else ""
        tprec["frac_digits=%d,Z=%s" % (len(frac.rstrip("Z")), t.endswith("Z"))] += 1
    F["entry_time_shapes"] = dict(tprec)

    # --- 5. Attachments.
    atts = by_schema.get("pkst/gemini-attachment@0.1", {})
    member_by_name = collections.defaultdict(set)  # full archive path -> raw CIDs
    for r in cap:
        member_by_name[r["member_name"]].add(r["raw_cid"])
    stat = collections.Counter()
    att_bad = collections.Counter()
    missing_names = []
    for c, a in atts.items():
        stat[a["status"]] += 1
        cands = [str(x) for x in a["candidates"]]
        if len(cands) > 1:
            att_bad["more-than-one-candidate"] += 1
        try:
            fname = resolve(doc, a["document_pointer"] + a["field_pointer"]) if a["field_pointer"].startswith("/") else None
        except Exception:
            fname = None
            att_bad["pointer-unresolvable"] += 1
        exact = member_by_name.get(a["member_name"], set())
        if a["status"] == "resolved" and (len(cands) != 1 or cands[0] not in exact):
            att_bad["resolved-without-exact-member"] += 1
        if a["status"] == "missing":
            if exact:
                att_bad["missing-but-exact-member-exists"] += 1
            missing_names.append(a["member_name"])
        if not (isinstance(fname, str) and a["member_name"].rsplit("/", 1)[-1] == fname):
            att_bad["field-value-differs-from-member_basename"] += 1

    def stem(path):
        base = path.rsplit("/", 1)[-1]
        return base.rsplit(".", 1)[0] if "." in base.rsplit("-", 1)[-1] else base

    stems = collections.defaultdict(set)
    for n in member_by_name:
        stems[stem(n)].add(n.rsplit("/", 1)[-1])
    distinct_missing = sorted(set(missing_names))
    pairs = collections.Counter()
    no_counterpart = []
    for n in distinct_missing:
        others = stems.get(stem(n), set())
        if others:
            for o in others:
                pairs["%s->%s" % (n.rsplit(".", 1)[-1].lower(), o.rsplit(".", 1)[-1].lower() if "." in o.rsplit("-", 1)[-1] else "<none>")] += 1
        else:
            no_counterpart.append(n.rsplit("/", 1)[-1])
    C["attachments"] = {"pass": not att_bad, "objects": len(atts), "status": dict(stat), "problems": dict(att_bad),
                        "missing_objects": len(missing_names), "missing_distinct_names": len(distinct_missing),
                        "missing_with_same_stem_member": len(distinct_missing) - len(no_counterpart),
                        "same_stem_extension_pairs": dict(pairs), "missing_without_counterpart": no_counterpart}
    R["all_pass"] = all(v["pass"] for v in C.values())
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(R, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(R, ensure_ascii=False, indent=1))
    return 0 if R["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
