"""Build the DeepTech100+ cut of the CCMF deck.

Reads the CCMF deck, removes two slides (product overview, illustrative
scenario), rebrands the cover and the ask, updates the timeline to the
HKSTP Ideation year, and refreshes the repository counts on the proof
slide. Writes a new file; the CCMF deck is left untouched.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape, unescape

SRC = Path("deliverables/Sandbox Pitch Deck (CCMF) Final.pptx")
DST = Path("deliverables/Sandbox Pitch Deck (DeepTech100+) v1.pptx")

DROP = {2, 7}  # product overview (redundant), illustrative 18% scenario

# New page number for each kept slide, in presentation order.
ORDER = [1, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
NEW_NUM = {old: i + 1 for i, old in enumerate(ORDER)}

TEXT_EDITS: dict[int, list[tuple[str, str]]] = {
    1: [
        ("CCMF · HONG KONG PROGRAMME", "HKU DEEPTECH100+ · COHORT 8"),
    ],
    5: [
        (
            "Simplified. Stages from Town Planning Board, EIA Ordinance and Buildings Department guidance.",
            "Simplified from TPB, EIAO and BD guidance. Broad-brush fit read only — two gates, EIAO and town planning.",
        ),
    ],
    13: [
        ("2027", "2027–28"),
        ("Q1 · R&D", "MTH 1–3 · R&D"),
        ("Q2 · Prototype 1", "MTH 4–6 · Prototype 1"),
        ("Q3 · Prototype 2, demo", "MTH 7–9 · Prototype 2, demo"),
        ("Q4 · Launch", "MTH 10–12 · Launch"),
        ("CCMF result expected in February; sign agreement", "DeepTech100+ result Jan–Feb; Ideation agreement"),
        ("Interim report; licence and data-use terms", "Milestone 2 review; licence and data-use terms"),
        ("Final report; register company", "Milestone 3 review; register company"),
        ("Cyberport Incubation application", "HKSTP Incubation application"),
        (
            "Dates follow the 1 Dec 2026 intake and assume a six-month project from about March",
            "Ideation runs 12 months from about March 2027; month numbers, not calendar quarters",
        ),
    ],
    15: [
        ("46", "47"),
        ("247", "333"),
        ("185", "212"),
    ],
    17: [
        (
            "HK$100k takes us from prototype to a paid evaluation",
            "Ideation funding takes us from prototype to a paid evaluation",
        ),
        ("ON SIGNING · HK$10K", "MILESTONE 1 · HK$10K"),
        ("INTERIM REPORT · HK$45K", "MILESTONE 2 · HK$45K"),
        ("FINAL REPORT · HK$45K", "MILESTONE 3 · HK$45K"),
        ("A route into Cyberport Incubation", "A route into HKSTP Incubation, up to HK$1.29M"),
    ],
}

NOTES_EDITS: dict[int, list[tuple[str, str]]] = {
    1: [
        (
            "About 30 seconds.",
            "About 30 seconds. "
            "Dropped from the 15-slide cut: the product-overview slide (3D engine and workspace, "
            "licensed to planning consultancies, broad-brush answers in minutes with every assumption shown), "
            "whose facts sit on slides 2, 5 and 7; and the illustrative Hung Shui Kiu scenario with its example 18%, "
            "whose point (two layouts, same weather, compare) sits on slides 2 and 5.",
        )
    ],
    13: [
        (
            "Q1 is only R&D and refining. One consultancy gets an early-access release in Q2; the full launch is Q4.",
            "Month 1–3 is only R&D and refining. One consultancy gets an early-access release in month 4–6; the full launch is month 10–12. The four columns are months of the 12-month Ideation year, not calendar quarters.",
        )
    ],
    15: [("25 November 2026", "26 November 2026")],
    17: [
        (
            "The three payments follow CCMF’s own stages: HK$10,000 on signing, HK$45,000 after the interim report, "
            "HK$45,000 on completion.",
            "The three payments are our proposed split of the HK$100k Ideation grant, one tranche per milestone; "
            "HKSTP sets the final milestone schedule.",
        )
    ],
}

T_OPEN = re.compile(r"<a:t>(.*?)</a:t>", re.S)


def edit_runs(xml: str, pairs: list[tuple[str, str]]) -> tuple[str, int]:
    hits = 0

    def sub(m: re.Match[str]) -> str:
        nonlocal hits
        text = unescape(m.group(1))
        for old, new in pairs:
            if old and old in text:
                text = text.replace(old, new)
                hits += 1
        return "<a:t>" + escape(text, {'"': "&quot;"}) + "</a:t>"

    return T_OPEN.sub(sub, xml), hits


def renumber(xml: str, number: int) -> tuple[str, int]:
    """Replace the static page number in the bottom-right corner."""
    changed = 0
    out = []
    pos = 0
    for m in re.finditer(r"<p:sp>.*?</p:sp>", xml, re.S):
        block = m.group(0)
        off = re.search(r'<a:off x="(\d+)" y="(\d+)"/>', block)
        text = "".join(unescape(t) for t in re.findall(r"<a:t>(.*?)</a:t>", block, re.S))
        if off and int(off.group(2)) >= 6_000_000 and re.fullmatch(r"\d{1,2}", text):
            new_block = re.sub(r"<a:t>\d{1,2}</a:t>", f"<a:t>{number}</a:t>", block)
            out.append(xml[pos : m.start()])
            out.append(new_block)
            pos = m.end()
            changed += 1
    out.append(xml[pos:])
    return "".join(out), changed


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")
    if DST.exists():
        DST.unlink()

    with zipfile.ZipFile(SRC) as zin:
        items = {i.filename: zin.read(i.filename) for i in zin.infolist()}
        infos = {i.filename: i for i in zin.infolist()}

    removed = set()
    for n in DROP:
        removed |= {
            f"ppt/slides/slide{n}.xml",
            f"ppt/slides/_rels/slide{n}.xml.rels",
            f"ppt/notesSlides/notesSlide{n}.xml",
            f"ppt/notesSlides/_rels/notesSlide{n}.xml.rels",
        }

    # presentation order
    pres = items["ppt/presentation.xml"].decode("utf-8")
    ids = re.findall(r'<p:sldId id="(\d+)" r:id="(rId\d+)"/>', pres)
    if len(ids) != 17:
        raise SystemExit(f"expected 17 slides, found {len(ids)}")
    keep = [pair for i, pair in enumerate(ids) if (i + 1) not in DROP]
    pres = re.sub(
        r"<p:sldIdLst>.*?</p:sldIdLst>",
        "<p:sldIdLst>" + "".join(f'<p:sldId id="{a}" r:id="{b}"/>' for a, b in keep) + "</p:sldIdLst>",
        pres,
        flags=re.S,
    )
    items["ppt/presentation.xml"] = pres.encode("utf-8")

    # presentation relationships
    rels = items["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    for n in DROP:
        rels, k = re.subn(
            rf'<Relationship Id="rId\d+" Type="[^"]+/slide" Target="slides/slide{n}\.xml"/>',
            "",
            rels,
        )
        if k != 1:
            raise SystemExit(f"slide{n} relationship not found")
    items["ppt/_rels/presentation.xml.rels"] = rels.encode("utf-8")

    # content types
    ct = items["[Content_Types].xml"].decode("utf-8")
    for n in DROP:
        ct, k = re.subn(
            rf'<Override PartName="/ppt/(?:slides|notesSlides)/(?:slide|notesSlide){n}\.xml"[^>]*/>',
            "",
            ct,
        )
        if k != 2:
            raise SystemExit(f"content-type overrides for {n}: {k}")
    items["[Content_Types].xml"] = ct.encode("utf-8")

    for name in removed:
        items.pop(name, None)

    # slide text edits and page numbers
    for n in ORDER:
        name = f"ppt/slides/slide{n}.xml"
        xml = items[name].decode("utf-8")
        if n in TEXT_EDITS:
            xml, hits = edit_runs(xml, TEXT_EDITS[n])
            if hits == 0:
                raise SystemExit(f"no text edit applied on slide {n}")
        xml, k = renumber(xml, NEW_NUM[n])
        expected = 0 if n == 1 else 1
        if k != expected:
            raise SystemExit(f"page number on slide {n}: {k} shapes")
        items[name] = xml.encode("utf-8")

    # notes
    for n, pairs in NOTES_EDITS.items():
        name = f"ppt/notesSlides/notesSlide{n}.xml"
        xml = items[name].decode("utf-8")
        xml, hits = edit_runs(xml, pairs)
        if hits == 0:
            raise SystemExit(f"no note edit applied on notes {n}")
        xml = re.sub(
            r'(<a:fld[^>]*type="slidenum"[^>]*>.*?)<a:t>\d+</a:t>',
            lambda m: m.group(1) + f"<a:t>{NEW_NUM[n]}</a:t>",
            xml,
            flags=re.S,
        )
        items[name] = xml.encode("utf-8")

    # document properties: 15 slides, 15 notes, new title and date
    app = items["docProps/app.xml"].decode("utf-8")
    app = app.replace("<Slides>17</Slides>", "<Slides>15</Slides>")
    app = app.replace("<Notes>17</Notes>", "<Notes>15</Notes>")
    app = re.sub(
        r"(<vt:lpstr>Slide Titles</vt:lpstr>\s*</vt:variant>\s*<vt:variant>)<vt:i4>17</vt:i4>",
        r"\1<vt:i4>15</vt:i4>",
        app,
    )
    app = re.sub(
        r'(<vt:vector size=")20(" baseType="lpstr">)',
        r"\g<1>18\g<2>",
        app,
    )
    app = re.sub(r"<vt:lpstr>Slide 1[67]</vt:lpstr>", "", app)
    items["docProps/app.xml"] = app.encode("utf-8")

    core = items["docProps/core.xml"].decode("utf-8")
    core = core.replace(
        "<dc:title>Sandbox Pitch Deck (CCMF)</dc:title>",
        "<dc:title>Sandbox Pitch Deck (DeepTech100+)</dc:title>",
    )
    core = core.replace("2026-11-24T15:54:11Z", "2026-11-26T14:00:00Z")
    items["docProps/core.xml"] = core.encode("utf-8")

    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            info = infos.get(name)
            if info is None:
                zout.writestr(name, data)
            else:
                zout.writestr(info, data)

    print(f"wrote {DST} with {len(keep)} slides")


if __name__ == "__main__":
    main()
