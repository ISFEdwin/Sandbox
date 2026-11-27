"""Diff a submission deck against a base deck, and check it against the entry gates.

Usage:
    python3 scripts/deck_diff.py "deliverables/Sandbox Pitch Deck (DeepTech100+) v2.pptx"
    python3 scripts/deck_diff.py NEW.pptx --base "deliverables/Sandbox Pitch Deck (CCMF) Final.pptx"

Why: the submission deck is being produced separately from the CCMF source, so the
comparison has to be mechanical rather than by eye. This reads the .pptx directly
(no PowerPoint, no LibreOffice), so it runs anywhere the repository does.

What it reports, in order:
  1. deck facts, and every gate a DeepTech100+ entry has to pass;
  2. the slide list, matched to the base by title, not by position;
  3. text that differs on a matched slide;
  4. slides that exist in only one of the two decks.

It is a reader, not a writer: it never modifies either file.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

MAX_SLIDES = 15

# Strings that must not survive into a DeepTech100+ submission.
FOREIGN_PROGRAMME = [
    ("CCMF", "a CCMF label; this is not the CCMF intake"),
    ("Cyberport", "a Cyberport programme; DeepTech100+ feeds HKSTP Ideation/Incubation"),
    ("HONG KONG PROGRAMME", "the CCMF cover wording"),
]

# Figures on the proof slide, and what the repository actually holds on 26 Nov 2026.
# The number sits on its own line, immediately above its label, so the pair is what
# gets checked — "US$185 a month" on the competitor slide must not trip this.
EXPECTED_COUNTS = {
    "API routes in the engine": "47",
    "backend test functions": "333",
    "commits since 5 October 2026": "212",
}


@dataclass
class Slide:
    number: int
    title: str
    lines: list[str] = field(default_factory=list)
    page_number: str | None = None
    has_notes: bool = False


def _paragraphs(xml: bytes) -> list[str]:
    root = ET.fromstring(xml)
    out: list[str] = []
    for para in root.iter(f"{{{A}}}p"):
        line = "".join(t.text or "" for t in para.iter(f"{{{A}}}t")).strip()
        if line:
            out.append(line)
    return out


def read_deck(path: Path) -> list[Slide]:
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels}
        order = [
            target[s.get(f"{{{R}}}id")]
            for s in pres.find(f"{{{P}}}sldIdLst")
        ]

        slides: list[Slide] = []
        for i, t in enumerate(order, 1):
            lines = _paragraphs(z.read(f"ppt/{t}"))
            notes_part = f"ppt/notesSlides/notesSlide{t.removeprefix('slides/slide').removesuffix('.xml')}.xml"
            has_notes = notes_part in names
            page = None
            for line in reversed(lines):
                if re.fullmatch(r"\d{1,2}", line):
                    page = line
                    break
            slides.append(
                Slide(
                    number=i,
                    title=lines[0] if lines else "(untitled)",
                    lines=lines,
                    page_number=page,
                    has_notes=has_notes,
                )
            )
        return slides


def gates(slides: list[Slide]) -> list[tuple[bool, str]]:
    checks: list[tuple[bool, str]] = []
    checks.append(
        (
            len(slides) <= MAX_SLIDES,
            f"{len(slides)} slides (limit {MAX_SLIDES})",
        )
    )

    mismatched = [s for s in slides[1:] if s.page_number != str(s.number)]
    checks.append(
        (
            not mismatched,
            "page numbers run 1..n"
            if not mismatched
            else "page number off on slides " + ", ".join(str(s.number) for s in mismatched),
        )
    )

    no_notes = [str(s.number) for s in slides if not s.has_notes]
    checks.append(
        (
            not no_notes,
            "every slide has speaker notes" if not no_notes else "no notes on slides " + ", ".join(no_notes),
        )
    )

    body = "\n".join(line for s in slides for line in s.lines)
    found = [
        f"{needle} ({why})"
        for needle, why in FOREIGN_PROGRAMME
        if needle.casefold() in body.casefold()
    ]
    checks.append((not found, "no foreign-programme wording" if not found else "; ".join(found)))

    stale: list[str] = []
    for s in slides:
        for value, label in zip(s.lines, s.lines[1:]):
            expected = EXPECTED_COUNTS.get(label)
            if expected is None:
                continue
            if not re.fullmatch(r"\d{1,6}", value):
                continue
            if value != expected:
                stale.append(f"slide {s.number}: {label} is {value}, repository says {expected}")
    checks.append(
        (
            not stale,
            "proof-slide counts match the repository" if not stale else "; ".join(stale),
        )
    )
    return checks


def normalise(lines: list[str]) -> Counter[str]:
    return Counter(line.strip() for line in lines)


def diff(base: list[Slide], new: list[Slide]) -> None:
    base_by_title = {s.title: s for s in base}
    new_by_title = {s.title: s for s in new}

    print("\nSlides only in the base")
    only_base = [s for s in base if s.title not in new_by_title]
    print("  none" if not only_base else "")
    for s in only_base:
        print(f"  - {s.title}")

    print("\nSlides only in the new deck")
    only_new = [s for s in new if s.title not in base_by_title]
    print("  none" if not only_new else "")
    for s in only_new:
        print(f"  + {s.title}")

    print("\nText changes on matched slides")
    changed = 0
    for s in new:
        b = base_by_title.get(s.title)
        if b is None:
            continue
        removed = normalise(b.lines) - normalise(s.lines)
        added = normalise(s.lines) - normalise(b.lines)
        # page numbers are expected to move when slides are dropped
        removed.pop(str(b.number), None)
        added.pop(str(s.number), None)
        if not removed and not added:
            continue
        changed += 1
        print(f"\n  {s.title}")
        for line in sorted(removed):
            print(f"    - {line}")
        for line in sorted(added):
            print(f"    + {line}")
    if changed == 0:
        print("  none")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", type=Path, help="the deck to check")
    ap.add_argument(
        "--base",
        type=Path,
        default=Path("deliverables/Sandbox Pitch Deck (CCMF) Final.pptx"),
        help="the deck to diff against (default: the CCMF source)",
    )
    args = ap.parse_args()

    if not args.deck.exists():
        print(f"missing {args.deck}", file=sys.stderr)
        return 2

    slides = read_deck(args.deck)
    print(f"DECK  {args.deck.name}")
    print(f"      {len(slides)} slides\n")

    print("GATES")
    ok = True
    for passed, message in gates(slides):
        print(f"  [{'ok' if passed else 'FAIL'}] {message}")
        ok &= passed

    print("\nSLIDES")
    for s in slides:
        print(f"  {s.number:2d}. {s.title}")

    if args.base.exists() and args.base.resolve() != args.deck.resolve():
        print(f"\nDIFF AGAINST {args.base.name}")
        diff(read_deck(args.base), slides)
    elif not args.base.exists():
        print(f"\n(no base at {args.base}; skipped the diff)")

    print("\nRESULT", "passes every gate" if ok else "has failures above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
