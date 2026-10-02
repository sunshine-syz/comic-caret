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
  bold letter keeps the regular's rows. The small parts (superscripts, fraction figures,
  ™'s letters) are drawn lighter than full letters, and grow by a pen as much smaller
  (small_pen()).
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

The pen must not push ink out of the cell, or past the regular's own overhang where it has
one. A glyph that would pass it is condensed: its outline scaled horizontally about its ink
centre before the offset, just enough, so every stem still grows by the full pen. A composite
whose part would pass it moves its references in toward the cell's centre instead.

A composite keeps its references, so an accented letter follows its base; a glyph with an
outline and references has only its outline offset. Two kinds of part are unlinked first, as
in the italic: a shared glyph's bolder part (∙ on the period) keeps the regular's outline, and
a bolder glyph's part turned a quarter (⋮ on …) grows as its outline, since the reference
would turn the pen too. A few composites are drawn as one outline, each part grown, and
condensed where it must be, on its own (MERGED). Where the pen grows two parts into each
other, one moves clear (APART) or both are condensed (OWN_BOX), and an accent the pen grows
out of the line box moves down into it. Widths, anchors and the lookups carry over as they
are.
"""
import argparse
import math
import pathlib
import sys
import tempfile

import fontforge
import psMat

import lig_geometry as geo
import project
from add_ligatures import GENERATED
from add_shapes import CODES
from measure import ink, spans_at_y, vertical_edges
from project import (
    ADVANCE,
    BOLD_SFD,
    LINE_TOP,
    ROUNDING,
    SFD,
    save_checked,
    validation_errors,
)

# Chosen by proof against the reference bolds on 2026-10-01. Its ink in a-z is 57.5% of the
# x-height band (the reference bolds' 51-59%), a step of 13.5 points from the regular's 44.0%
# (Maple Mono's, the smallest reference step, is 14). The counters at our x-height, n 172,
# o 199 and e 109, are each at or above the narrowest reference bold's.
PEN = (35, 14)  # (width, height) of the elliptical pen

SHARED, BOLDER = "shared", "bolder"

# Box Drawing, Block Elements and Geometric Shapes; Braille; the Powerline symbols.
SHARED_BLOCKS = (range(0x2500, 0x2600), range(0x2800, 0x2900), range(0xE000, 0xF900))
# Outside them: the spinner frames but ‼, which is two ! and grows with them, as the italic
# slants it; ✶, the star spinner's first frame, which add_shapes.py draws ✷ ✸ ✹ ✺ from rather
# than drawing it; and the heavy marks.
SHARED_CHARS = (frozenset(map(chr, CODES)) - {"‼"}) | frozenset("✶✔✘❯❮❰❱➜")

# Besides the .small glyphs, the parts the regular draws as light as the small figures and
# letters beside them (tests/test_latin.py): the fraction bar, the ordinals' bar and the ring
# of © ®. They take the small pen too, so they stay as heavy as their figures and letters.
LIGHT_PARTS = ("slash.fraction", "bar.ordinal", "circle.copyright")

# Composites drawn as one outline, each part grown on its own and condensed on its own where
# it would pass the glyph's bound (fitted()). An outline beside a reference is hinted with
# overlapping stems and no hint masks, which validate() flags: Θ's bar beside O. The capitals
# whose tonos stands left of them, past the cell, need a tonos of their own: the pen would
# push the shared one past the regular's overhang, and moving it in would run it into the
# capital, so each condenses its own copy, while ΄ and the small letters keep the shared tonos
# at its full width. Their capitals go into the outline too, as Ε and Η beside a tonos fail
# validate() as Θ's O does.
MERGED = ("Theta", "Epsilontonos", "Etatonos", "Iotatonos", "Omicrontonos", "Upsilontonos",
          "Omegatonos")

# The marks the pen grows into the stem beside them, and the part each one is: it moves right
# by the pen's width, what the pen grew the two toward each other, so they keep about the
# regular's gap. ď's caron passes the cell already and goes further still, where
# test_sanity.py's DCARON_OVERHANG holds it, so fit_references() leaves it out.
APART = {"ldot": "periodcentered", "dcaron": "caron.alt", "lcaron": "caron.alt",
         "Lcaron": "caron.alt"}

# ™'s T and M, 23 apart, which the small pen would grow until they all but touch: each is
# condensed to keep its own regular box, so the two keep the regular's gap and ™ stays a
# composite.
OWN_BOX = ("T.small", "M.small")

# A cut exactly on a piece's cut line runs through the points where the pen's round end meets
# the stroke, and intersect() then fails, leaving the stroke uncut or the cutting box behind;
# so the cut runs this far inside it, and rounding puts the end back on the line.
HAIR = 0.01

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


def small_pen(font):
    """PEN scaled by how much lighter the regular draws its small parts than its letters: the
    stem of one.small over the stem of one, each at mid-height. A bold superscript is then as
    much bolder as a bold letter."""
    def stem(name):
        layer = font[name].foreground
        _, y0, _, y1 = layer.boundingBox()
        [(x0, x1)] = spans_at_y(layer, (y0 + y1) / 2)
        return x1 - x0
    ratio = stem("one.small") / stem("one")
    return tuple(size * ratio for size in PEN)


def pen_of(name, small):
    """The pen glyph `name` grows by: `small`, the small_pen(), for a small part."""
    return small if name.endswith(".small") or name in LIGHT_PARTS else PEN


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
    and every part of a MERGED glyph."""
    if glyph.glyphname in MERGED:
        return [name for name, *_ in glyph.references]
    # A translation, a 180° turn or a mirror keeps the pen as it is.
    return [name for name, matrix, *_ in glyph.references if classes[name] == BOLDER
            and (classes[glyph.glyphname] == SHARED
                 or tuple(round(abs(v), 4) for v in matrix[:4]) != (1, 0, 0, 1))]


def offset(outline, overlap, pen):
    """The outline grown by `pen`: stroked, the stroke's inner edge dropped, and united with
    the outline. `overlap` is how the stroke removes its own overlaps first, if at all."""
    layer = outline.dup()
    layer.stroke("elliptical", *pen, 0, "round", "round", removeinternal=True,
                 removeoverlap=overlap)
    layer += outline
    layer.removeOverlap()
    return layer


def grew_within_pen(outline, layer, pen, cuts):
    """Whether `layer`, the outline grown by `pen`, reaches past the outline's box by no more
    than half the pen and a unit of rounding on each side, and exactly to each cut end in
    `cuts`. An overlap removal or a trim that fails leaves ink, or its cutting box, beyond."""
    if not len(layer):
        return False
    box, grown = outline.boundingBox(), layer.boundingBox()
    for side, cut in ((0, cuts[0]), (2, cuts[1])):
        if abs(cut) < geo.FAR and grown[side] != cut:
            return False
    reach = (pen[0] / 2 + ROUNDING, pen[1] / 2 + ROUNDING)
    return all(abs(grown[side] - box[side]) <= reach[side % 2] for side in range(4))


def emboldened(name, outline, scratch, pen):
    """The outline of glyph `name` offset by `pen`, its cut ends trimmed back, on whole units.

    FontForge's overlap removal fails on a few outlines (an open contour at v's crotch, a
    crossing in ↵), different ones whether or not the stroke removes its own overlaps first and
    different ones for each pen. So each way is tried in turn, and the first outline that
    validate() passes and that grew by no more than the pen is kept. It is checked on
    `scratch`, a glyph of another font, so the bold's own glyphs save without validate()'s
    marks.
    """
    cuts = cut_ends(name, outline)
    for overlap in ("layer", "none"):
        layer = offset(outline, overlap, pen)
        if cuts != (-geo.FAR, geo.FAR):
            layer = geo.trim(layer, x0=cuts[0] + HAIR, x1=cuts[1] - HAIR)
        # The pen can pinch a counter's narrow corner off into a speck of white (p's).
        layer = geo.without_specks(layer, pen[1])
        # Rounding can push a sliver the union left (h's arch) across the outline, which
        # validate() flags; rounding before the cleanup lets its removeOverlap() merge it.
        layer.round()
        layer = geo.cleanup(layer)
        scratch.foreground = layer
        scratch.autoHint()  # validate() reads the outline as autoHint() leaves it
        if not validation_errors(scratch) and grew_within_pen(outline, layer, pen, cuts):
            return layer
    sys.exit(f"{name}: no offset of its outline passes validate() and stays within the pen")


def fitted(name, outline, bound, scratch, pen):
    """emboldened(), condensed first just enough that the bold ink stays within `bound`,
    (x0, x1): the outline scaled horizontally about its ink centre, so every stem still grows
    by the full pen."""
    layer = emboldened(name, outline, scratch, pen)
    x0, _, x1, _ = outline.boundingBox()
    centre, half = (x0 + x1) / 2, (x1 - x0) / 2
    taken = 0
    # Rounding the condensed outline can leave a unit over, which a second pass takes in.
    for _ in range(3):
        bx0, _, bx1, _ = layer.boundingBox()
        if (excess := max(bound[0] - bx0, bx1 - bound[1])) <= 0:
            return layer
        taken += excess
        narrow = geo.transformed(outline, geo.about(psMat.scale(1 - taken / half, 1), centre, 0))
        layer = emboldened(name, narrow, scratch, pen)
    sys.exit(f"{name}: condensed, its ink still passes {bound}")


def placed(font, glyph):
    """The ink of each of the glyph's references, where the glyph places it."""
    return [geo.transformed(ink(font, name), matrix) for name, matrix, *_ in glyph.references]


def reposition(glyph, offset):
    """Place each of the glyph's references at the offset offset(index, name, (dx, dy))
    returns."""
    refs = [(name, (*matrix[:4], *offset(i, name, matrix[4:])))
            for i, (name, matrix, *_) in enumerate(glyph.references)]
    glyph.references = tuple(reversed(refs))  # FontForge writes references in reverse order


def fit_references(font, glyph, bound):
    """Move the composite's references in toward the cell's centre, just enough that their
    ink stays within `bound`, (x0, x1): each offset is scaled about the cell's centre, so the
    parts keep their order and their weight. A part APART moves is placed by its gap instead,
    and left out."""
    apart = APART.get(glyph.glyphname)
    scale = 1
    for (name, matrix, *_), layer in zip(glyph.references, placed(font, glyph), strict=True):
        x0, _, x1, _ = layer.boundingBox()
        dx = matrix[4]
        # A part passing a side moves in by dx * (1 - scale): only one placed off-centre on
        # that side can.
        for excess, inward in ((bound[0] - x0, -dx), (x1 - bound[1], dx)):
            if name == apart or excess <= 0:
                continue
            if inward <= excess:
                sys.exit(f"{glyph.glyphname}: its {name} passes {bound} and can't move in")
            scale = min(scale, 1 - excess / inward)
    if scale < 1:
        # Rounding toward the centre keeps each part in.
        reposition(glyph, lambda _, __, at: (math.trunc(at[0] * scale), at[1]))


def move_apart(glyph):
    """Move the part APART names right by the pen's width."""
    mark = APART[glyph.glyphname]
    reposition(glyph, lambda _, name, at: (at[0] + (PEN[0] if name == mark else 0), at[1]))


def lower_into_line(font, glyph):
    """Move the composite's parts above its base down by as much as its ink passes LINE_TOP,
    which terminals clip to (ĥ's circumflex). The base is the part that reaches lowest; a part
    is above it when it starts no lower than the base's top less the pen's height, what the
    pen grew the two toward each other."""
    if (excess := math.ceil(ink(font, glyph.glyphname).boundingBox()[3] - LINE_TOP)) <= 0:
        return
    boxes = [layer.boundingBox() for layer in placed(font, glyph)]
    if len(glyph.foreground):
        boxes.append(glyph.foreground.boundingBox())  # the glyph's own outline can't move
    base = min(boxes, key=lambda box: box[1])
    above = [box[1] >= base[3] - PEN[1] for box in boxes]
    reposition(glyph, lambda i, _, at: (at[0], at[1] - (excess if above[i] else 0)))
    if ink(font, glyph.glyphname).boundingBox()[3] > LINE_TOP:
        sys.exit(f"{glyph.glyphname}: its base passes LINE_TOP")


def depth(font, name):
    """How many references deep the glyph is built: 0 for an outline."""
    return max((1 + depth(font, part) for part, *_ in font[name].references), default=0)


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
        later = next((i for i in range(1, len(contour)) if contour[i].on_curve), None)
        if later is None:
            sys.exit(f"{glyph.glyphname}: a contour with one on-curve point can't start "
                     "anywhere else")
        contour.makeFirst(later)
    glyph.foreground = layer
    glyph.autoHint()


def build(font):
    """Turn the regular, opened as `font`, into the bold."""
    classes = classify(font)
    small = small_pen(font)
    # Where each encoded glyph's ink must stay: the cell, or the regular's own overhang (ď,
    # the tonos capitals); and each of OWN_BOX, its own box. Read before anything changes.
    bounds = {}
    for glyph in font.glyphs():
        x0, _, x1, _ = glyph.boundingBox()
        if glyph.unicode >= 0:
            bounds[glyph.glyphname] = (min(x0, 0), max(x1, ADVANCE))
        elif glyph.glyphname in OWN_BOX:
            bounds[glyph.glyphname] = (x0, x1)
    # A MERGED glyph's outline and parts, each grown on its own, as the regular draws them.
    merged = {name: [font[name].foreground, *placed(font, font[name])] for name in MERGED}
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
        name = glyph.glyphname
        if classes[name] == BOLDER and len(glyph.foreground):
            bound = bounds.get(name, (-geo.FAR, geo.FAR))
            grown = [fitted(name, part, bound, scratch, pen_of(name, small))
                     for part in merged.get(name, [glyph.foreground]) if len(part)]
            glyph.foreground = grown[0] if len(grown) == 1 else geo.cleanup(geo.union(*grown))
            glyph.autoHint()
    # Parts before the glyphs built from them, so each sees its parts as they end up (ΐ's ΅).
    for glyph in sorted(font.glyphs(), key=lambda g: depth(font, g.glyphname)):
        name = glyph.glyphname
        if classes[name] != BOLDER or not glyph.references:
            continue
        before = glyph.references
        if name in bounds:
            fit_references(font, glyph, bounds[name])
        if name in APART:
            move_apart(glyph)
        lower_into_line(font, glyph)
        if glyph.references != before:
            glyph.autoHint()  # a reference assigned leaves the hints stale
    # Where a contour starts can make the autohinter write a nan into a stem's range, which
    # breaks the hints read back (docs/fontforge-pitfalls.md); so such a glyph's contours start
    # later until none does.
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / BOLD_SFD.name
        names = nan_hinted(font, path)
        for _ in range(RESTARTS):
            if not names:
                break
            for name in sorted(names):
                restart(font[name])
            names = nan_hinted(font, path)
        if names:
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
    # The pen raises the tops by half its height; the reference bolds declare their own heights.
    font.os2_xheight = round(font["x"].boundingBox()[3])
    font.os2_capheight = round(font["H"].boundingBox()[3])


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
