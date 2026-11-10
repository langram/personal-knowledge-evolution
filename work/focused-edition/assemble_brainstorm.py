"""Assemble the "Extensions: Experimental Hypotheses and Ideas" brainstorm document for edition 20.

It collects, unchanged, the sections of edition 19 (work/author-voice-rewrite) that did not go into
edition 20, in Chinese and English, grouped under three themes plus the author's own assessment.
Run from the repository root:  python work/focused-edition/assemble_brainstorm.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V19 = os.path.join(ROOT, "work", "author-voice-rewrite")
DOSSIER = os.path.join(ROOT, "archive", "dossiers", "2026-11-10-focused-edition")

ALL = "all"
# (group title zh, group title en, [(v19 file, ALL | [zh section headings])])
RECIPE = [
    ("一、数学、范畴论与意识的假说", "I. Hypotheses on mathematics, category theory and consciousness", [
        ("01.md", ALL),
        ("02.md", ALL),
        ("03.md", ["同一个对象的静态面与动态面", "最短的描述与最省力的构造"]),
        ("04.md", ALL),
        ("05.md", ["概念的对应表", "对齐是一种不动点"]),
        ("17.md", ["对齐作为不动点：一个有待完善的方向"]),
        ("22.md", ["数学是在发现，还是在创造"]),
    ]),
    ("二、信息科学与工程的设想", "II. Ideas in information science and engineering", [
        ("11.md", ["通信工具的进化史", "能效比：比较复杂系统的方法", "一种容器语言", "一切都是树",
                   "命名的多样性是人的多样性", "内容身份保证行为差异"]),
        ("12.md", ALL),
        ("13.md", ALL),
        ("14.md", ["收集信息是一切的起点", "本能的冲动怎样安全释放"]),
        ("15.md", ["对象会变化，所以必须进入运行时", "顺序依赖与并行探索怎样结合"]),
    ]),
    ("三、文明与未来的设想", "III. Ideas on civilization and the future", [
        ("15.md", ["单一中枢与内部多样性"]),
        ("21.md", ["自我实现的科幻", "问答"]),
        ("22.md", ["大胆假设，严谨推理", "从研究到文明"]),
    ]),
    ("四、作者对这些内容的定位", "IV. The author's own assessment of this material", [
        ("24-appendix.md", ["假说", "有待完善的"]),
    ]),
]

INTRO_ZH = """# 扩展篇：实验性假说与设想

**《新原理》第二十版的头脑风暴文档**

作者：Tangram Liu（langram）

## 关于这份文档

《新原理》第二十版把论证收拢到有广泛共识的数学和科学理论之上，篇幅缩短了一半。这份文档收的是第十九版中没有进入第二十版的内容：或者是缺乏广泛共识的假说，或者是还没有展开成完整论证的直觉，或者是离主线较远的工程和文明设想。它们是我长期思考的一部分，我不想丢掉；但第二十版的论证不以其中任何一条为前提。

读这份文档时请注意三点。第一，这里的文字保持第十九版的原样，没有按第二十版重新改写，所以其中的章节编号，比如"第三章""第九章说过"，指的都是第十九版的章节。第二，各篇是从原书中按节取出的，彼此之间不保证衔接。第三，哪些是假说，哪些有待完善，我在第十九版附录里的说明附在最后。

第十九版的全文仍然保留，可以对照阅读。"""

INTRO_EN = """# Extensions: Experimental Hypotheses and Ideas

**The brainstorm document for edition 20 of *Nova Principia***

Author: Tangram Liu (langram)

## About this document

Edition 20 of *Nova Principia* gathers its argument onto mathematical and scientific theory that enjoys broad consensus, and is half the length of the edition before it. This document collects the material of edition 19 that did not go into edition 20: hypotheses that lack broad consensus, intuitions not yet developed into complete arguments, and engineering and civilizational ideas that lie some distance from the main line. They are part of my long-running thinking and I do not want to lose them; but the argument of edition 20 does not rest on any of them.

Three things to keep in mind when reading. First, the text here is kept exactly as it stood in edition 19 and has not been rewritten for edition 20, so chapter numbers in it, such as "Chapter 3" or "as Chapter 9 said", all refer to the chapters of edition 19. Second, the pieces were lifted section by section from the original book and are not guaranteed to connect with one another. Third, my own account of which items are hypotheses and which are still to be worked out, from the appendix of edition 19, is attached at the end.

The full text of edition 19 is preserved and can be read alongside."""

# Corrections applied to the copied text (a wrong journal name in edition 19).
FIXES = {
    "zh": [("2019年发表在《科学》上的研究", "2019年发表在《科学进展》上的研究")],
    "en": [("published in Science in 2019", "published in Science Advances in 2019")],
}


def blocks(path):
    """Split a chapter file into (level, heading, body) blocks, in order."""
    out, cur = [], None
    for line in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m:
            cur = [len(m.group(1)), m.group(2).strip(), []]
            out.append(cur)
        elif cur is not None:
            cur[2].append(line)
    return out


def body(lines):
    return "\n".join(lines).strip()


def build(lang):
    parts = [INTRO_ZH if lang == "zh" else INTRO_EN]
    for gzh, gen, items in RECIPE:
        parts.append("## " + (gzh if lang == "zh" else gen))
        for fname, sel in items:
            zb = blocks(os.path.join(V19, "zh", fname))
            lb = zb if lang == "zh" else blocks(os.path.join(V19, "en", fname))
            if [b[0] for b in zb] != [b[0] for b in lb]:
                sys.exit("heading structure differs in " + fname)
            chap = [i for i, b in enumerate(zb) if b[0] == 2]
            if len(chap) != 1:
                sys.exit("expected one chapter heading in " + fname)
            ci = chap[0]
            title = lb[ci][1]
            if sel == ALL:
                head = ("第十九版·" + title) if lang == "zh" else ("Edition 19, " + title)
                picked = [i for i in range(ci + 1, len(zb)) if zb[i][0] == 3]
            else:
                head = ("第十九版·" + title + "（节选）") if lang == "zh" else ("Edition 19, " + title + " (excerpts)")
                picked = []
                for s in sel:
                    hits = [i for i, b in enumerate(zb) if b[0] == 3 and b[1] == s]
                    if len(hits) != 1:
                        sys.exit("section not found exactly once: %s / %s" % (fname, s))
                    picked.append(hits[0])
            parts.append("### " + head)
            if sel == ALL and body(lb[ci][2]):
                parts.append(body(lb[ci][2]))
            for i in picked:
                parts.append("#### " + lb[i][1])
                if body(lb[i][2]):
                    parts.append(body(lb[i][2]))
    text = "\n\n".join(parts) + "\n"
    for old, new in FIXES[lang]:
        if old in text:
            text = text.replace(old, new)
    return text


zh = build("zh")
en = build("en")
targets = {
    os.path.join(ROOT, "book", "v20-brainstorm.md"): zh,
    os.path.join(DOSSIER, "06-brainstorm.zh.md"): zh,
    os.path.join(ROOT, "book", "v20-brainstorm.en.md"): en,
    os.path.join(DOSSIER, "07-brainstorm.en.md"): en,
}
for path, text in targets.items():
    with open(path, "w", encoding="utf-8", newline="\n") as w:
        w.write(text)

zh_h = [l.split(" ")[0] for l in zh.splitlines() if l.startswith("#")]
en_h = [l.split(" ")[0] for l in en.splitlines() if l.startswith("#")]
print("brainstorm zh CJK chars", len(re.findall(r"[一-鿿]", zh)))
print("brainstorm en words", len(en.split()))
print("headings zh", len(zh_h), "en", len(en_h), "match" if zh_h == en_h else "MISMATCH")
if zh_h != en_h:
    sys.exit(1)
