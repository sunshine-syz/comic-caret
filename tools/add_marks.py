"""Build the combining marks into the SFD, with their anchors and the ccmp, mark and mkmk lookups.

Usage: python3 tools/add_marks.py [SFD]

A combining mark has no advance and draws over the cell, where terminals that don't shape text
draw it: over the character before it. Shaped text moves it there with `mark` anchors, which
every other encoded glyph has, one above and one below, and stacks marks with `mkmk`. First,
`ccmp` turns a letter and its marks into the precomposed letter where the font has one, so e +
U+0301 shows the same é as U+00E9, and takes the dot off i and j under a mark above.

Each mark is a reference to its spacing accent, placed as on the lowercase letters. A letter's
anchors put a mark where the font's own accented forms of it do; other letters center it over
their ink, and other glyphs over the cell, as high above the ink as on the capitals.

Replaces everything an earlier run made, so running it again changes nothing but
ModificationTime. Rerun it after adding or redrawing glyphs, then tools/add_ligatures.py, since
a new glyph lands after the generated ones.
"""
import argparse
import pathlib
import statistics
import sys
import tempfile
import unicodedata

import fontforge
import psMat

from project import ADVANCE, SFD, save_checked, validation_errors

# Combining mark -> the spacing accent it is drawn from.
MARKS = {0x300: "grave.accent", 0x301: "acute", 0x302: "circumflex", 0x303: "tilde",
         0x304: "macron", 0x306: "breve", 0x307: "dotaccent", 0x308: "dieresis",
         0x30A: "ring", 0x30B: "hungarumlaut", 0x30C: "caron",
         0x326: "commaaccent", 0x327: "cedilla", 0x328: "ogonek"}
BELOW = {0x326, 0x327, 0x328}
# Soft-dotted letters, which lose their dot under a mark above.
DOTLESS = {"i": "dotlessi", "j": "dotlessj"}

PREFIX = "marks_"  # every lookup this script makes, and no other
SCRIPTS = (("DFLT", ("dflt",)), ("latn", ("dflt",)))
MIDDLE = ADVANCE // 2
# Stacked marks sit this far apart, as far as a capital's mark sits above cap height.
STACK_GAP = 50


def mark_name(code):
    return fontforge.nameFromUnicode(code)


def is_top(code):
    return code not in BELOW


def is_letter(glyph):
    return glyph.unicode >= 0 and unicodedata.category(chr(glyph.unicode)).startswith("L")


def letter_placements(font):
    """[(letter, accent, dx, dy)]: each accented letter's letter and accent references, as the
    accent is moved relative to the letter. Accents built on another accent, such as ΅ on
    the tonos, place nothing."""
    accents = set(MARKS.values())
    out = []
    for glyph in font.glyphs():
        if glyph.unicode < 0 or len(glyph.foreground):
            continue
        refs = {name: matrix for name, matrix, *_ in glyph.references}
        marks = [name for name in refs if name in accents]
        letters = [name for name in refs if name not in accents and is_letter(font[name])]
        if len(marks) != 1 or len(letters) != 1:
            continue
        (mark,), (letter,) = marks, letters
        base, accent = refs[letter], refs[mark]
        out.append((letter, mark, accent[4] - base[4], accent[5] - base[5]))
    return out


def mark_offsets(font, placements):
    """{code: (dx, dy)}: where each mark's reference puts its accent. Centered in the cell, and
    as high as the lowercase letters carry it; marks merged into their letters (cedilla,
    ogonek) keep the accent's own height."""
    offsets = {}
    for code, accent in MARKS.items():
        x0, _, x1, _ = font[accent].boundingBox()
        lowercase = [dy for letter, mark, _, dy in placements
                     if mark == accent and font[letter].unicode >= 0
                     and unicodedata.category(chr(font[letter].unicode)) == "Ll"]
        dy = statistics.median_low(lowercase) if lowercase else 0
        offsets[code] = (round(MIDDLE - (x0 + x1) / 2), dy)
    return offsets


def add_mark_glyphs(font, offsets):
    for code, accent in MARKS.items():
        glyph = font[code] if code in font else font.createChar(code, mark_name(code))
        glyph.foreground = fontforge.layer()
        glyph.references = ((accent, psMat.translate(*offsets[code])),)
        glyph.width = 0
        glyph.glyphclass = "mark"
        glyph.autoHint()


def remove_previous(font):
    # Removing a lookup leaves its anchors on the glyphs, and a merged feature file keeps an
    # anchor a glyph already has, so remove the anchor classes first.
    for lookup in font.gpos_lookups:
        if lookup.startswith(PREFIX):
            for subtable in font.getLookupSubtables(lookup):
                for name in font.getLookupSubtableAnchorClasses(subtable):
                    font.removeAnchorClass(name)
    # Chain lookups call the single substitutions, so remove them first.
    for lookup in reversed(font.gsub_lookups + font.gpos_lookups):
        if lookup.startswith(PREFIX):
            font.removeLookup(lookup)


def add_lookup(font, name, kind, feature, after=None):
    features = ((feature, SCRIPTS),) if feature else ()
    if after:
        font.addLookup(name, kind, (), features, after)
    else:
        font.addLookup(name, kind, (), features)
    font.addLookupSubtable(name, name)


def sequences(font, glyph):
    """The sequences of glyphs a precomposed glyph is made of: its full canonical
    decomposition and its one-level one, where every part is in the font and each part after
    the first is one of the marks."""
    char = chr(glyph.unicode)
    out = []
    one_level = unicodedata.decomposition(char)
    candidates = [unicodedata.normalize("NFD", char)]
    if one_level and not one_level.startswith("<"):
        candidates.append("".join(chr(int(part, 16)) for part in one_level.split()))
    for parts in candidates:
        if (len(parts) > 1 and all(ord(c) in MARKS for c in parts[1:])
                and ord(parts[0]) in font):
            names = tuple(font[ord(c)].glyphname for c in parts)
            if names not in out:
                out.append(names)
    return out


def add_compositions(font):
    """ccmp: a letter and its marks become the precomposed letter."""
    add_lookup(font, f"{PREFIX}compose", "gsub_ligature", "ccmp")
    for glyph in font.glyphs():
        if glyph.unicode < 0 or glyph.unicode in MARKS:
            continue
        for names in sequences(font, glyph):
            glyph.addPosSub(f"{PREFIX}compose", names)
            # A ligature's result would otherwise count as a ligature in GDEF, where it is a
            # letter that takes marks.
            glyph.glyphclass = "baseglyph"


def add_dotless(font):
    """ccmp: i and j lose their dot before a mark above."""
    single, chain = f"{PREFIX}dotless_single", f"{PREFIX}dotless"
    add_lookup(font, single, "gsub_single", None, f"{PREFIX}compose")
    for letter, dotless in DOTLESS.items():
        font[letter].addPosSub(single, dotless)
    font.addLookup(chain, "gsub_contextchain", (), (("ccmp", SCRIPTS),), single)
    tops = " ".join(mark_name(code) for code in MARKS if is_top(code))
    font.addContextualSubtable(chain, chain, "coverage",
                               f"| [{' '.join(DOTLESS)}] @<{single}> | [{tops}]")


def base_anchors(font, placements, offsets, top_y):
    """{glyph name: (top, bottom)}: where each encoded glyph takes a mark above and below.

    A letter's come from its accented forms, the median over them. The rest sit STACK_GAP
    above the ink and at the baseline, over the middle of a letter's ink and of any other
    glyph's cell: marks over the ink of ▏ would stick out of the cell.
    """
    by_accent = {accent: code for code, accent in MARKS.items()}
    found = {}
    for letter, accent, dx, dy in placements:
        code = by_accent[accent]
        mx, my = offsets[code]
        spot = (MIDDLE + dx - mx, (top_y if is_top(code) else 0) + dy - my)
        found.setdefault((letter, is_top(code)), []).append(spot)

    def median(spots):
        return (round(statistics.median(x for x, _ in spots)),
                round(statistics.median(y for _, y in spots)))

    anchors = {}
    for glyph in font.glyphs():
        if glyph.unicode < 0 and glyph.glyphname not in DOTLESS.values():
            continue
        if glyph.unicode in MARKS:
            continue
        x0, _, x1, top = glyph.boundingBox()
        letter = unicodedata.category(chr(glyph.unicode)).startswith("L")
        middle = round((x0 + x1) / 2) if letter and x1 > x0 else MIDDLE
        above = found.get((glyph.glyphname, True))
        below = found.get((glyph.glyphname, False))
        anchors[glyph.glyphname] = (
            median(above) if above else (middle, max(top_y, round(top) + STACK_GAP)),
            median(below) if below else (middle, 0))
    return anchors


def mark_boxes(font, offsets):
    """{code: ink box} of each mark, from its accent: a glyph whose references were just
    replaced keeps stale bounds in this process."""
    boxes = {}
    for code, accent in MARKS.items():
        x0, y0, x1, y1 = font[accent].boundingBox()
        dx, dy = offsets[code]
        boxes[code] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    return boxes


def positioning(anchors, boxes, top_y):
    """The mark and mkmk lookups, as feature file text.

    FontForge marks a glyph's hints stale when Python adds an anchor to it, but not when a
    feature file does.
    """
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    stacks = {True: [], False: []}
    # A mark below hangs from the baseline, but the cedilla and ogonek rise into their letter;
    # one stacked under another mark hangs that much lower, so it doesn't run into it.
    rise = max(boxes[code][3] for code in MARKS if not is_top(code))
    for code in MARKS:
        name, top = mark_name(code), is_top(code)
        side = "top" if top else "bottom"
        y = top_y if top else 0
        lines.append(f"markClass [{name}] <anchor {MIDDLE} {y}> @{side};")
        lines.append(f"markClass [{name}] <anchor {MIDDLE} {y}> @{side}_mkmk;")
        _, bottom, _, height = boxes[code]
        stack_y = round(height + STACK_GAP) if top else round(bottom - STACK_GAP - rise)
        stacks[top].append(f"  pos mark {name} <anchor {MIDDLE} {stack_y}> mark @{side}_mkmk;")
    lines.append(f"lookup {PREFIX}base {{")
    for name, ((tx, ty), (bx, by)) in anchors.items():
        lines.append(f"  pos base {name} <anchor {tx} {ty}> mark @top"
                     f" <anchor {bx} {by}> mark @bottom;")
    lines.append(f"}} {PREFIX}base;")
    # A mark under another needs an anchor for every class of its lookup, so marks above and
    # below stack in lookups of their own.
    for top, side in ((True, "top"), (False, "bottom")):
        lines += [f"lookup {PREFIX}stack_{side} {{", *stacks[top], f"}} {PREFIX}stack_{side};"]
    lines += [f"feature mark {{ lookup {PREFIX}base; }} mark;",
              f"feature mkmk {{ lookup {PREFIX}stack_top; lookup {PREFIX}stack_bottom; }} mkmk;"]
    return "\n".join(lines) + "\n"


def merge_positioning(font, text):
    with tempfile.TemporaryDirectory() as tmp:
        fea = pathlib.Path(tmp) / "marks.fea"
        fea.write_text(text, encoding="utf-8")
        font.mergeFeature(str(fea))
    # On a parse error FontForge prints to stderr and merges nothing, so check the result.
    wanted = {f"{PREFIX}base", f"{PREFIX}stack_top", f"{PREFIX}stack_bottom"}
    if missing := wanted - set(font.gpos_lookups):
        sys.exit(f"the mark lookups did not merge; missing: {', '.join(sorted(missing))}")


def build(font):
    remove_previous(font)
    placements = letter_placements(font)
    offsets = mark_offsets(font, placements)
    add_mark_glyphs(font, offsets)
    boxes = mark_boxes(font, offsets)
    # A mark above rests where the acute does on the lowercase letters.
    top_y = round(boxes[0x301][1])
    add_compositions(font)
    add_dotless(font)
    anchors = base_anchors(font, placements, offsets, top_y)
    merge_positioning(font, positioning(anchors, boxes, top_y))


def check(path):
    """Exit non-zero if a mark in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    failed = {font[code].glyphname: hex(flags) for code in MARKS
              if (flags := validation_errors(font[code]))}
    if failed:
        sys.exit(f"validate() failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sfd", nargs="?", default=str(SFD), help="default: %(default)s")
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        return check(args.sfd)

    sfd = pathlib.Path(args.sfd)
    font = fontforge.open(str(sfd))
    build(font)
    save_checked(font, sfd, __file__)


if __name__ == "__main__":
    main()
