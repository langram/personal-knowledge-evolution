"""Assemble the chapter files of the 2026-11-05 author-voice rewrite into book/v19.md and book/v19.en.md (the previous edition stays in book/current.md).

Run from the repository root:  python work/author-voice-rewrite/assemble.py
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(ROOT, "work", "author-voice-rewrite")


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


zh_files, zh = assemble("zh", os.path.join(ROOT, "book", "v19.md"),
                        os.path.join(ROOT, "archive", "dossiers", "2026-11-05-author-voice-rewrite", "01-new-principles.zh.md"))
en_files, en = assemble("en", os.path.join(ROOT, "book", "v19.en.md"),
                        os.path.join(ROOT, "archive", "dossiers", "2026-11-05-author-voice-rewrite", "02-new-principles.en.md"))

zh_h, en_h = headings(zh), headings(en)
print("zh files", len(zh_files), "en files", len(en_files))
print("zh CJK chars", len(re.findall(r"[一-鿿]", zh)))
print("en words", len(en.split()))
print("zh headings", len(zh_h), "en headings", len(en_h))
levels_zh = [h.split(" ")[0] for h in zh_h]
levels_en = [h.split(" ")[0] for h in en_h]
if levels_zh != levels_en:
    print("HEADING LEVEL MISMATCH")
    for i, (a, b) in enumerate(zip(zh_h, en_h)):
        if a.split(" ")[0] != b.split(" ")[0]:
            print(i, a, "|", b)
            break
    sys.exit(1)
print("heading structure matches")
