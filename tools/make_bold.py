"""Derive src/ComicCaret-Bold.sfd, the bold master, from src/ComicCaret-Regular.sfd.

Usage: python3 tools/make_bold.py [BOLD_SFD]

The bold is the regular with its strokes made heavier, and its pictures kept as they are.
Nothing in the bold SFD is drawn by hand: this script rewrites the whole file from the
regular, so running it again changes nothing but ModificationTime, and
tests/test_make_bold.py fails while it is out of date. Change the regular or this script,
then rerun it and ./build.sh.

Every glyph of the regular falls in one of two sets, decided by classify():

- BOLDER: what a pen writes. Letters, figures, the combining marks, punctuation, symbols,
  arrows and the ligatures. Each outline grows outward by an elliptical pen, PEN wide and
  tall: it is stroked with the pen, the stroke's inner edge dropped, and united with the
  outline.
  A stem grows half the pen's width on each side and a level stroke half its height, so a
  bold letter keeps the regular's rows.
- SHARED: what is drawn as a picture, or drawn heavy already, which the reference bolds keep
  as their regulars draw them: Box Drawing, Block Elements and the geometric shapes, which
  meet their neighbours' across the cell; Braille; the Powerline symbols, which fill the line
  box; the spinner frames, which are cut from those shapes and must turn without pulsing; and
  ✔ ✘ ❯ ❮ ❰ ❱ ➜, heavy marks already. .notdef too, a box. Copied unchanged, hints included.

The offset grows every edge alike, so - stays centred on the math axis and the ligature
pieces, offset by the same pen as the - = < > ~ | they continue, still match at their seams.
A piece's flat cut end past the cell is trimmed back to the regular's, so it stays flat and
keeps its overlap with the next piece. Not FontForge's changeWeight(): in its LCG mode it
keeps the letters' heights but grows a level stroke upward only, so -'s top moved from 311 to
341 off the axis, its bottom fixed, and the -- pieces stopped matching at their seams (351
against 341).

A composite keeps its references, so an accented letter follows its base; a glyph with an
outline and references has only its outline offset. Two kinds of part are unlinked first, as
in the italic: a shared glyph's bolder part (∙ on the period) keeps the regular's outline, and
a bolder glyph's part turned a quarter (⋮ on …) grows as its outline, since the reference
would turn the pen too. A composite whose parts the pen makes overlap is unlinked too, so they
grow into one outline (MERGED). Widths, anchors and the lookups carry over as they are.
"""
import argparse
import pathlib
import sys
import tempfile

import fontforge

import lig_geometry as geo
import project
from add_ligatures import GENERATED
from add_shapes import CODES
from measure import vertical_edges
from project import ADVANCE, BOLD_SFD, SFD, save_checked, validation_errors

PEN = (30, 12)  # (width, height) of the elliptical pen

SHARED, BOLDER = "shared", "bolder"

# Box Drawing, Block Elements and Geometric Shapes; Braille; the Powerline symbols.
SHARED_BLOCKS = (range(0x2500, 0x2600), range(0x2800, 0x2900), range(0xE000, 0xF900))
# Outside them: the spinner frames but ‼, which is two ! and grows with them, as the italic
# slants it; ✶, the star spinner's first frame, which add_shapes.py draws ✷ ✸ ✹ ✺ from rather
# than drawing it; and the heavy marks.
SHARED_CHARS = (frozenset(map(chr, CODES)) - {"‼"}) | frozenset("✶✔✘❯❮❰❱➜")

# Composites whose parts sit closer than the pen is wide, so in the bold they overlap, which
# validate() rejects: the caron beside d and l in ď ľ Ľ, ™'s T and M, and Ύ's tonos and Υ,
# each about 24 apart in the regular. Each is unlinked and grows as one outline.
MERGED = ("dcaron", "lcaron", "Lcaron", "trademark", "Upsilontonos")

RESTARTS = 10  # a start the autohinter writes a nan for is rare: 1 of the first 40 of m's

FONTNAME, FULLNAME = "ComicCaret-Bold", "Comic Caret Bold"
BOLD_BIT = 0x0020  # OS/2 fsSelection; the regular sets 0x0040, REGULAR
WEIGHT = 700  # OS/2 usWeightClass, Bold
PANOSE_WEIGHT = 2  # the place of PANOSE's weight digit, kept at usWeightClass's hundreds + 1


def encoded_class(code):
    if chr(code) in SHARED_CHARS or any(code in block for block in SHARED_BLOCKS):
        return SHARED
    return BOLDER


def unused_class(name):
    if not GENERATED.fullmatch(name):
        sys.exit(f"{name} is unencoded and no glyph uses it: class it shared or bolder in "
                 "make_bold.py")
    return BOLDER


def classify(font):
    """{glyph name: SHARED or BOLDER} for every glyph of the regular.

    An encoded glyph goes by its character; .notdef, a box, is shared. An unencoded part
    follows the glyphs built from it, and a ligature piece, which only a substitution reaches,
    is an operator's and grows. Any other unencoded glyph nothing references stops the
    generator: only the generators' glyphs are known to grow, so it has to be classed.
    """
    return project.classify(font, {".notdef": SHARED}, encoded_class, unused_class)


def cut_ends(name, layer):
    """(x0, x1): where the regular's outline of `name` is cut flat past the cell, a ligature
    piece's end that overlaps the next piece's, else beyond any outline. A round end past the
    cell, as <='s tips, grows like any other."""
    if not GENERATED.fullmatch(name):
        return -geo.FAR, geo.FAR
    x0, _, x1, _ = layer.boundingBox()
    flat = {x for x, *_ in vertical_edges(layer)}
    return (x0 if x0 < 0 and x0 in flat else -geo.FAR,
            x1 if x1 > ADVANCE and x1 in flat else geo.FAR)


def unlinked_parts(glyph, classes):
    """The glyph's references the bold draws as its own outline: a shared glyph's bolder parts,
    which keep the regular's outline; a bolder glyph's bolder parts turned a quarter (⋮ on …)
    or scaled, which grow as its outline, since the reference would turn or scale the pen too;
    and every part of a MERGED glyph, which grow into one outline."""
    if glyph.glyphname in MERGED:
        return [name for name, *_ in glyph.references]
    # A translation, a 180° turn or a mirror keeps the pen as it is.
    return [name for name, matrix, *_ in glyph.references if classes[name] == BOLDER
            and (classes[glyph.glyphname] == SHARED
                 or tuple(round(abs(v), 4) for v in matrix[:4]) != (1, 0, 0, 1))]


def offset(outline, overlap):
    """The outline grown by the pen: stroked, the stroke's inner edge dropped, and united with
    the outline. `overlap` is how the stroke removes its own overlaps first, if at all."""
    layer = outline.dup()
    layer.stroke("elliptical", *PEN, 0, "round", "round", removeinternal=True,
                 removeoverlap=overlap)
    layer += outline
    layer.removeOverlap()
    return layer


def emboldened(name, outline, scratch):
    """The outline of glyph `name` offset by the pen, its cut ends trimmed back, on whole units.

    FontForge's overlap removal fails on a few outlines (an open contour at v's crotch, a
    crossing in ↵), different ones whether or not the stroke removes its own overlaps first and
    different ones for each pen. So each way is tried in turn, and the first outline that
    validate() passes is kept. It is checked on `scratch`, a glyph of another font, so the
    bold's own glyphs save without validate()'s marks.
    """
    x0, x1 = cut_ends(name, outline)
    for overlap in ("layer", "none"):
        layer = offset(outline, overlap)
        if (x0, x1) != (-geo.FAR, geo.FAR):
            layer = geo.trim(layer, x0=x0, x1=x1)
        # The pen can pinch a counter's narrow corner off into a speck of white (p's).
        layer = geo.without_specks(layer, PEN[1])
        # Rounding can push a sliver the union left (h's arch) across the outline, which
        # validate() flags; rounding before the cleanup lets its removeOverlap() merge it.
        layer.round()
        layer = geo.cleanup(layer)
        scratch.foreground = layer
        scratch.autoHint()  # validate() reads the outline as autoHint() leaves it
        if not validation_errors(scratch):
            return layer
    sys.exit(f"{name}: no offset of its outline passes validate()")


def nan_hinted(font, path):
    """The glyphs whose stems the SFD, saved at `path`, gives a nan in their ranges."""
    font.save(str(path))
    names, name = set(), None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("StartChar: "):
            name = line.removeprefix("StartChar: ")
        elif line.startswith(("HStem:", "VStem:")) and "nan" in line:
            names.add(name)
    return names


def restart(glyph):
    """Start each of the glyph's contours one on-curve point later, and rehint it."""
    layer = glyph.foreground
    for contour in layer:
        contour.makeFirst(next(i for i in range(1, len(contour)) if contour[i].on_curve))
    glyph.foreground = layer
    glyph.autoHint()


def build(font):
    """Turn the regular, opened as `font`, into the bold."""
    classes = classify(font)
    # Every unlink comes before any base grows: unlinkRef() bakes the base's outline as the
    # composite last saw it, not its current foreground, so a shared glyph's bolder part must
    # take the regular's outline now, not by luck later, and a part that grows as an outline
    # must start from the regular's.
    for glyph in font.glyphs():
        if parts := unlinked_parts(glyph, classes):
            for name in parts:
                glyph.unlinkRef(name)  # one reference per call, so a part used twice is named twice
            glyph.round()  # a part scaled off the grid (◉'s dot), as the build rounds it
            glyph.autoHint()
    scratch_font = fontforge.font()
    scratch = scratch_font.createChar(-1, "scratch")
    for glyph in font.glyphs():
        if classes[glyph.glyphname] == BOLDER and len(glyph.foreground):
            glyph.foreground = emboldened(glyph.glyphname, glyph.foreground, scratch)
            glyph.autoHint()
    # Where a contour starts can make the autohinter write a nan into a stem's range, which
    # breaks the hints read back (docs/fontforge-pitfalls.md); so such a glyph's contours start
    # later until none does.
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / BOLD_SFD.name
        for _ in range(RESTARTS):
            if not (names := nan_hinted(font, path)):
                break
            for name in sorted(names):
                restart(font[name])
        else:
            sys.exit(f"every start tried hints {sorted(names)} with a nan")
    # FontForge derives the subfamily and macStyle's bold bit from these.
    font.fontname, font.fullname = FONTNAME, FULLNAME
    font.weight = "Bold"
    font.os2_weight = WEIGHT
    font.os2_stylemap = BOLD_BIT
    panose = font.os2_panose
    font.os2_panose = (*panose[:PANOSE_WEIGHT], WEIGHT // 100 + 1, *panose[PANOSE_WEIGHT + 1:])
    # The strikeout covers the hyphen, which grew.
    _, bottom, _, top = font["hyphen"].boundingBox()
    font.os2_strikeypos, font.os2_strikeysize = round(top), round(top - bottom)


def check(path):
    """Exit non-zero if a glyph of the bold at `path` fails a validate() check that the
    regular's passes (∄'s references overlap in both)."""
    bold, regular = fontforge.open(str(path)), fontforge.open(str(SFD))
    failed = {g.glyphname: hex(flags) for g in bold.glyphs()
              if (flags := validation_errors(g) & ~validation_errors(regular[g.glyphname]))}
    if failed:
        sys.exit(f"validate() failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sfd", nargs="?", default=str(BOLD_SFD), help="default: %(default)s")
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        return check(args.sfd)

    font = fontforge.open(str(SFD))
    build(font)
    save_checked(font, pathlib.Path(args.sfd), __file__)


if __name__ == "__main__":
    main()
