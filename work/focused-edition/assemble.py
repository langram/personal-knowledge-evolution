"""Assemble the chapter files of edition 20 (the focused edition) into book/v20.md and book/v20.en.md.

Edition 18 stays in book/current.md and edition 19 in book/v19.md; nothing here touches them.
Run from the repository root:  python work/focused-edition/assemble.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(ROOT, "work", "focused-edition")
DOSSIER = os.path.join(ROOT, "archive", "dossiers", "2026-11-10-focused-edition")


def assemble(lang, target, dossier_target):
    files = sorted(glob.glob(os.path.join(WORK, lang, "*.md")))
    parts = [open(f, encoding="utf-8").read().strip() for f in files]
    out = "\n\n".join(parts) + "\n"
    for path in (target, dossier_target):
        with open(path, "w", encoding="utf-8", newline="\n") as w:
            w.write(out)
    return files, out


def headings(text):
    return [line for line in text.splitlines() if line.startswith("#")]


zh_files, zh = assemble("zh", os.path.join(ROOT, "book", "v20.md"),
                        os.path.join(DOSSIER, "01-new-principles.zh.md"))
en_files, en = assemble("en", os.path.join(ROOT, "book", "v20.en.md"),
                        os.path.join(DOSSIER, "02-new-principles.en.md"))

print("zh files", len(zh_files), "en files", len(en_files))
print("zh CJK chars", len(re.findall(r"[一-鿿]", zh)))
print("en words", len(en.split()))
if [os.path.basename(f) for f in zh_files] != [os.path.basename(f) for f in en_files]:
    print("FILE LIST MISMATCH")
    sys.exit(1)
bad = False
for zf, ef in zip(zh_files, en_files):
    a = [h.split(" ")[0] for h in headings(open(zf, encoding="utf-8").read())]
    b = [h.split(" ")[0] for h in headings(open(ef, encoding="utf-8").read())]
    za = len([p for p in open(zf, encoding="utf-8").read().split("\n\n") if p.strip()])
    eb = len([p for p in open(ef, encoding="utf-8").read().split("\n\n") if p.strip()])
    if a != b:
        print("HEADING MISMATCH", os.path.basename(zf), len(a), len(b))
        bad = True
    if za != eb:
        print("paragraph count differs", os.path.basename(zf), za, eb)
print("zh headings", len(headings(zh)), "en headings", len(headings(en)))
if bad:
    sys.exit(1)
print("heading structure matches")
