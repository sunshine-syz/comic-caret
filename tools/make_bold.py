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
  (small_pen()). A stroke the regular draws as another turned, the tonos as the acute, grows
  by the pen turned with it (TURNED). ª º's bar, drawn as heavy as the stems above it, grows
  as much up and down (ROUND), and ẞ and the small 4, whose white the full pen would close
  under the reference bolds', grow by a narrower pen (NARROW). © ®'s ring grows outward only,
  keeping its counter clear of the letter inside (OUTWARD).
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
would turn the pen too. Where a shared glyph is such a part alone, □ for ☐, the other shared
glyphs refer to it instead (stand_ins()). Θ is drawn as one outline, each part grown on its
own (MERGED). A left glyph the regular draws as its right one mirrored is the bold right one
mirrored (mirror_pairs()).

Where the pen grows two parts into each other, one moves clear, just far enough to keep the
regular's gap (APART: ª º's bar, the tonos beside a capital); each is condensed
to keep its own box (OWN_BOX); of an outline's pieces, the wider is condensed away from the
other (PIECES_APART: ⇥'s arrow from its bar, ‰'s zeros from each other), and ‰'s slash
shortened at its foot (SLASHES); or, in one outline, Ħ's upper bar moves up its stems
(RAISED). An accent the pen grows out of the line box moves down into it, and a mark it
grows within MARK_CLEARANCE of its letter rises clear, as far on every letter where it
stands as high (raise_clear()). Widths, anchors and the lookups carry over as they are.
"""
import argparse
import collections
import itertools
import math
import pathlib
import sys
import tempfile
import unicodedata

import fontforge
import psMat

import lig_geometry as geo
import project
from add_ligatures import GENERATED
from add_shapes import CODES
from measure import gap, ink, outline, pieces, spans_at_x, spans_at_y, vertical_edges
from project import (
    ADVANCE,
    BOLD_SFD,
    LINE_TOP,
    MARK_CLEARANCE,
    ROUNDING,
    SFD,
    is_letter,
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

# The level bars the regular draws as heavy as the stems of the letters above them, not as a
# level stroke of a letter: ª º's bar. It grows by its pen's width up and down too, so it stays
# as heavy as the bold stems; the level pen leaves it 14 lighter.
ROUND = ("bar.ordinal",)

# The glyphs whose white the full pen closes under the reference bolds', and the share of
# their pen's width they grow by instead (tests/test_latin.py): ẞ, whose white between the
# stem and the diagonal would close to 56, under Maple Mono Bold's 65; and the small 4, whose
# counter would close to 0.128 of its height, under Maple Mono Bold's ¼ (0.137). Their stems
# grow 10.5 and 3.7 less than the others'.
NARROW = {"uni1E9E": 0.7, "four.small": 0.83}

# The strokes the regular draws as another stroke turned, and the turn, anticlockwise: the
# tonos is the acute turned 25° steeper (docs/design-notes.md). The pen turns with it, so the
# bold tonos is the bold acute turned. The level pen would grow the steeper stroke heavier.
TURNED = {"tonos": math.radians(25)}

# The rings that grow outward only, keeping their regular counter: © ®'s, which the regular
# draws lighter than the letter inside it so it doesn't crowd it (tests/test_latin.py). Grown
# inward too, it would come 35 from ®'s R, under Fira Code Bold's 41 around its ©.
OUTWARD = ("circle.copyright",)

# The outlines whose bar above a counter the pen would grow to less than a stroke from the bar
# below it: Ħ, 81 apart against the bold hyphen's 93 (tests/test_latin.py). The bar moves up
# its stems by the pen's height, so the white between the bars stays the regular's (raised()).
RAISED = ("Hbar",)

# The composites whose parts the pen grows into each other, the part of each that moves clear,
# and which way: just far enough to keep the regular's gap between it and the other parts
# (move_apart()). ŀ's dot and the carons of ď ľ Ľ move right, and the tonos beside a capital
# moves left; ď's caron and the tonos pass the cell already and go further still, where
# test_sanity.py holds them, so fit_references() leaves them out. ΅'s dieresis moves down,
# below its tonos, which lower_into_line() takes down into the line box and the turned pen
# grows into the dieresis. With no room above, ΐ ΰ's dieresis then sits 29 below ϊ ϋ's, a row
# break that letters as rare as these may take (tests/test_make_bold.py names it).
# The bar of ª º moves down, clear of the letter its round pen grows it into.
RIGHT, LEFT, DOWN = (1, 0), (-1, 0), (0, -1)
APART = {"ldot": ("periodcentered", RIGHT), "dcaron": ("caron.alt", RIGHT),
         "lcaron": ("caron.alt", RIGHT), "Lcaron": ("caron.alt", RIGHT),
         **dict.fromkeys(("Alphatonos", "Epsilontonos", "Etatonos", "Iotatonos", "Omicrontonos",
                          "Upsilontonos", "Omegatonos"), ("tonos", LEFT)),
         "dieresistonos": ("dieresis", DOWN),
         **dict.fromkeys(("ordfeminine", "ordmasculine"), ("bar.ordinal", DOWN))}

# The outlines condensed to keep their own regular box, so the pen grows them no closer to
# their neighbours than half its width: ™'s T and M, 23 apart, which the small pen would grow
# until they all but touch, so ™ stays a composite of the two; and Θ's bar, which would come
# 21 from the ring, under the reference bolds' 35, and keeps 39.
OWN_BOX = ("T.small", "M.small", "Theta")

# Composites drawn as one outline, each part grown on its own: Θ. Its bar beside a reference
# to the bold O fails validate() once saved: FontForge reads the hint masks O's overlapping
# stems need against Θ's own stems, which the bar's wobble makes overlap too.
MERGED = ("Theta",)

# Outlines whose pieces stand side by side, which the pen would grow into one: the arrows and
# bars of ⇥ and ↹ (⇤ is ⇥ mirrored), 30 apart, and ‰'s two lower zeros, 10 apart. Each piece
# grows on its own, and the wider is condensed away from the other, its far end kept, or both
# alike when they are as wide, until the white between them is the regular's: ⇥ ↹'s bar keeps
# the full pen, and the white ●●'s seam (pieces_apart()).
PIECES_APART = ("uni21E5", "uni21B9", "perthousand")

# Of those, the ones whose tallest piece is a slash leaning right that the pen grows into a
# piece below its foot: ‰'s, which would come 14 from the zero under it, where the regular
# keeps 27 (Maple Mono Bold's ‰ keeps 20). The slash shrinks about its top end, by the fewest
# units at its foot that keep the regular's white, so it ends higher up its slant.
SLASHES = ("perthousand",)

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
    """The pen glyph `name` grows by, (width, height, turn): `small`, the small_pen(), for a
    small part, narrower for a NARROW glyph, as tall as wide for a ROUND bar, and turned for a
    TURNED stroke."""
    width, height = small if name.endswith(".small") or name in LIGHT_PARTS else PEN
    width *= NARROW.get(name, 1)
    return width, width if name in ROUND else height, TURNED.get(name, 0)


def reach(pen):
    """(across, up): how far `pen` reaches from its centre, half its width and height when
    level, and the half extents of its turned ellipse when turned."""
    width, height, turn = pen
    a, b = width / 2, height / 2
    return (math.hypot(a * math.cos(turn), b * math.sin(turn)),
            math.hypot(a * math.sin(turn), b * math.cos(turn)))


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


def stand_ins(font, classes):
    """{bolder glyph: the shared glyph that is it alone, unmoved}: □ for ☐. The stand-in keeps
    the bolder glyph's regular outline, and the other shared glyphs built on that glyph refer
    to the stand-in, rather than each copy the outline (◰ ◱ ◲ ◳ ⧆ ⧇)."""
    found = {}
    for glyph in font.glyphs():
        if (classes[glyph.glyphname] == SHARED and not len(glyph.foreground)
                and len(glyph.references) == 1):
            [(name, matrix, *_)] = glyph.references
            if classes[name] == BOLDER and tuple(matrix) == psMat.identity():
                found.setdefault(name, glyph.glyphname)
    return found


def relinked(glyph, classes, standing):
    """The glyph's references as (name, matrix), a part with a stand-in (`standing`,
    stand_ins()) named by its stand-in in each shared glyph but the stand-in itself."""
    if classes[glyph.glyphname] != SHARED or glyph.glyphname in standing.values():
        return [(name, matrix) for name, matrix, *_ in glyph.references]
    return [(standing.get(name, name), matrix) for name, matrix, *_ in glyph.references]


def mirror_pairs(font, classes):
    """{left glyph: right glyph} for each pair of bolder outlines the regular draws as exact
    mirrors about the cell's middle (⇤ ⇥, ↩ ↪): the left one's Unicode name says LEFT where
    the right one's says RIGHT. The bold draws the left as the bold right mirrored, so the
    pen, which grows a mirrored outline a unit differently here and there, keeps them exact
    mirrors."""
    outlines = {unicodedata.name(chr(glyph.unicode), ""): glyph for glyph in font.glyphs()
                if glyph.unicode >= 0 and len(glyph.foreground) and not glyph.references
                and classes[glyph.glyphname] == BOLDER}
    pairs = {}
    for name, left in outlines.items():
        right = outlines.get(name.replace("LEFT", "RIGHT")) if "LEFT" in name else None
        if right and (outline(right.foreground)
                      == outline(geo.mirrored_x(left.foreground, ADVANCE / 2))):
            pairs[left.glyphname] = right.glyphname
    return pairs


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
    layer.stroke("elliptical", *pen, "round", "round", removeinternal=True,
                 removeoverlap=overlap)
    layer += outline
    layer.removeOverlap()
    return layer


def with_counters(layer, outline):
    """The grown `layer`'s outer contours with the counters of `outline`, the regular's, in
    place of its own (OUTWARD)."""
    out = fontforge.layer()
    for contour in (*(c for c in layer if c.isClockwise()),
                    *(c for c in outline if not c.isClockwise())):
        out += contour
    return out


def raised(outline, rise):
    """The outline with the bar above its counter moved up by `rise` along its stems (RAISED):
    the stems' straight part beside the counter lengthened by `rise`, and above the bar
    shortened as much, so their ends stay where they are."""
    upright = (0, 1, 1, 0, 0, 0)  # swaps x and y, so stretch_span() stretches up and down

    def stretched(layer, y0, y1, dy):
        return geo.transformed(geo.stretch_span(geo.transformed(layer, upright), y0, y1, dy),
                               upright)
    [hole] = [c for c in outline if not c.isClockwise()]
    x0, y0, x1, y1 = hole.boundingBox()
    third = (y1 - y0) / 3
    [bar_top] = [top for bottom, top in spans_at_x(outline, (x0 + x1) / 2)
                 if bottom > (y0 + y1) / 2]
    top = outline.boundingBox()[3]
    out = stretched(outline, y0 + third, y1 - third, rise)
    # Halfway up from the bar, short of the stems' round ends.
    return stretched(out, bar_top + rise, (bar_top + top) / 2 + rise, -rise)


def grew_within_pen(outline, layer, pen, cuts):
    """Whether `layer`, the outline grown by `pen`, reaches past the outline's box by no more
    than the pen's reach() and a unit of rounding on each side, and exactly to each cut end in
    `cuts`. An overlap removal or a trim that fails leaves ink, or its cutting box, beyond."""
    if not len(layer):
        return False
    box, grown = outline.boundingBox(), layer.boundingBox()
    for side, cut in ((0, cuts[0]), (2, cuts[1])):
        if abs(cut) < geo.FAR and grown[side] != cut:
            return False
    limit = [length + ROUNDING for length in reach(pen)]
    return all(abs(grown[side] - box[side]) <= limit[side % 2] for side in range(4))


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
        if name in OUTWARD:
            layer = with_counters(layer, outline)
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


def fitted(name, outline, bound, scratch, pen, anchor=None):
    """emboldened(), condensed first just enough that the bold ink stays within `bound`,
    (x0, x1): the outline scaled horizontally about x = `anchor`, or else its ink centre, so
    every stem still grows by the full pen."""
    layer = emboldened(name, outline, scratch, pen)
    x0, _, x1, _ = outline.boundingBox()
    centre = (x0 + x1) / 2 if anchor is None else anchor
    span = max(x1 - centre, centre - x0)  # how far the further side lies from the centre
    taken = 0
    # Rounding the condensed outline can leave a unit over, which a second pass takes in.
    for _ in range(3):
        bx0, _, bx1, _ = layer.boundingBox()
        if (excess := max(bound[0] - bx0, bx1 - bound[1])) <= 0:
            return layer
        taken += excess
        narrow = geo.transformed(outline, geo.about(psMat.scale(1 - taken / span, 1), centre, 0))
        layer = emboldened(name, narrow, scratch, pen)
    sys.exit(f"{name}: condensed, its ink still passes {bound}")


def pieces_apart(name, outline, bound, scratch, pen):
    """The outline's pieces (PIECES_APART) each fitted() within `bound`, and of two side by
    side, the wider condensed away from the other, about its far end, or both by half when
    they are as wide, until the white between their boxes is the regular's. A SLASHES slash
    then shrinks about its top end until it keeps the regular's white to the pieces below."""
    parts = pieces(outline)
    grown = [fitted(name, part, bound, scratch, pen) for part in parts]
    boxes = [part.boundingBox() for part in parts]
    for a, b in itertools.permutations(range(len(parts)), 2):
        (a0, a1, a2, a3), (b0, b1, b2, b3) = boxes[a], boxes[b]
        white = b0 - a2  # a stands left of b
        if white <= 0 or a3 < b1 or b3 < a1:
            continue
        left, right = grown[a].boundingBox()[2], grown[b].boundingBox()[0]
        if (lack := white - (right - left)) <= 0:
            continue
        wider = (a2 - a0) - (b2 - b0)
        share = 0.5 if abs(wider) <= ROUNDING else float(wider > 0)  # how much a gives way
        if share:
            grown[a] = fitted(name, parts[a], (bound[0], left - share * lack), scratch, pen, a0)
        if share < 1:
            grown[b] = fitted(name, parts[b], (right + (1 - share) * lack, bound[1]), scratch,
                              pen, b2)
    if name in SLASHES:
        i = max(range(len(parts)), key=lambda k: boxes[k][3] - boxes[k][1])
        x0, y0, x1, y1 = boxes[i]
        below = [k for k in range(len(parts)) if boxes[k][3] <= y0]
        wanted = gap(parts[i], geo.union(*(parts[k] for k in below)))
        rest = geo.union(*(grown[k] for k in below))
        length = math.hypot(x1 - x0, y1 - y0)

        def shortened(units):
            scale = geo.about(psMat.scale(1 - units / length), x1, y1)
            return fitted(name, geo.transformed(parts[i], scale), bound, scratch, pen)
        # The least shortening that clears, found by halves: every longer one clears too.
        low, high = 0, 2 * PEN[0]
        if gap(shortened(high), rest) < wanted:
            sys.exit(f"{name}: its slash can't shorten clear of the pieces below it")
        while low < high:
            middle = (low + high) // 2
            low, high = (low, middle) if gap(shortened(middle), rest) >= wanted else (
                middle + 1, high)
        grown[i] = shortened(low)
    return geo.cleanup(geo.union(*grown))


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
    apart, _ = APART.get(glyph.glyphname, (None, None))
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


def clearance(mine, rest, way, wanted):
    """The fewest whole units `mine` moves `way`, (dx, dy), to stand `wanted` from `rest`, or
    None if that is past twice the pen's width. tests/test_make_bold.py holds each move to how
    far the pen grew the two parts toward each other; the search goes further, so the test,
    not the search, reports a move that passes it."""
    most = 2 * PEN[0]
    (a0, b0, a1, b1), (c0, d0, c1, d1) = mine.boundingBox(), rest.boundingBox()
    if math.hypot(max(c0 - a1, a0 - c1, 0), max(d0 - b1, b0 - d1, 0)) >= wanted:
        return 0  # outlines are never closer than their boxes, and most marks clear by these
    # Only the rest within reach counts, which makes gap() quicker; the trim's cut edges stay
    # `wanted` from `mine` however far it moves.
    near = wanted + most
    rest = geo.trim(rest, a0 - near, a1 + near, b0 - near, b1 + near)
    dx, dy = way

    def clear(n):
        return gap(geo.moved(mine, dx * n, dy * n), rest) >= wanted

    # The least n that clears, found by halves: every n past it clears too.
    if not clear(most):
        return None
    low, high = 0, most
    while low < high:
        middle = (low + high) // 2
        low, high = (low, middle) if clear(middle) else (middle + 1, high)
    return low


def shifted(moves):
    """The offset for reposition() that moves each part named in `moves` by its (dx, dy)."""
    def offset(_, name, at):
        dx, dy = moves.get(name, (0, 0))
        return at[0] + dx, at[1] + dy
    return offset


def parted(font, glyph, part):
    """(the part's ink, the other parts' ink), each where the glyph places it."""
    mine, rest = fontforge.layer(), fontforge.layer()
    for (name, *_), layer in zip(glyph.references, placed(font, glyph), strict=True):
        if name == part:
            mine += layer
        else:
            rest += layer
    return mine, rest


def move_apart(font, glyph, wanted):
    """Move the part APART names its way until it is `wanted` from the glyph's other parts: the
    regular's gap, which the pen grew the two into."""
    part, (dx, dy) = APART[glyph.glyphname]
    if (steps := clearance(*parted(font, glyph, part), (dx, dy), wanted)) is None:
        sys.exit(f"{glyph.glyphname}: its {part} can't move clear of the rest")
    reposition(glyph, shifted({part: (dx * steps, dy * steps)}))


def marks_above(font, glyph, small):
    """([(name, ink)] of the composite letter's marks above its letter, the letter's ink): the
    letter is its one reference to a letter. A mark is above when it starts no lower than the
    letter's top less how far the pen grew the two toward each other, each by its pen's reach
    up (pen_of(); `small` is the small_pen())."""
    parts = list(zip((name for name, *_ in glyph.references), placed(font, glyph)))
    letters = [(name, layer) for name, layer in parts if is_letter(font[name].unicode)]
    if len(glyph.foreground) or len(letters) != 1:
        return [], None
    [(base, letter)] = letters
    top, grew = letter.boundingBox()[3], reach(pen_of(base, small))[1]
    return [(name, layer) for name, layer in parts if layer is not letter
            and layer.boundingBox()[1] >= top - grew - reach(pen_of(name, small))[1]], letter


def raise_clear(font, letters, heights, small):
    """Raise each mark that the pen grew within MARK_CLEARANCE of its letter, by the fewest
    whole units that clear it, and the same mark as far on every letter where the regular
    places it as high, so a row of them stays level (the tonos over έ ό, and so over ά ή ί).
    `heights` holds how high the regular places each (letter, mark). One row breaks on
    purpose: ΐ ΰ's dieresis, which ΅ takes down below its tonos (APART)."""
    needs = collections.defaultdict(int)
    for glyph in letters:
        marks, letter = marks_above(font, glyph, small)
        for name, mark in marks:
            if (steps := clearance(mark, letter, (0, 1), MARK_CLEARANCE)) is None:
                sys.exit(f"{glyph.glyphname}: its {name} can't rise clear of the letter")
            row = (name, heights[glyph.glyphname, name])
            needs[row] = max(needs[row], steps)
    for glyph in letters:
        marks, _ = marks_above(font, glyph, small)
        rises = {name: (0, needs[name, heights[glyph.glyphname, name]]) for name, _ in marks}
        if any(dy for _, dy in rises.values()):
            reposition(glyph, shifted(rises))
            glyph.autoHint()
            if ink(font, glyph.glyphname).boundingBox()[3] > LINE_TOP:
                sys.exit(f"{glyph.glyphname}: its marks rise past LINE_TOP")


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
    # Read before anything changes: where each encoded glyph's ink must stay, the cell or the
    # regular's own overhang (ď, the tonos capitals); where the outline of each of OWN_BOX
    # must, its own box; the gap each part APART moves keeps; and how high each mark stands.
    bounds, own = {}, {}
    for glyph in font.glyphs():
        if glyph.unicode >= 0:
            x0, _, x1, _ = glyph.boundingBox()
            bounds[glyph.glyphname] = (min(x0, 0), max(x1, ADVANCE))
        if glyph.glyphname in OWN_BOX:
            x0, _, x1, _ = glyph.foreground.boundingBox()
            own[glyph.glyphname] = (x0, x1)
    gaps = {name: gap(*parted(font, font[name], part)) for name, (part, _) in APART.items()}
    heights = {(glyph.glyphname, name): matrix[5]
               for glyph in font.glyphs() for name, matrix, *_ in glyph.references}
    # A MERGED glyph's own outline and its parts' ink, as the regular draws them.
    merged = {name: (font[name].foreground, placed(font, font[name])) for name in MERGED}
    mirrors = mirror_pairs(font, classes)
    # A shared glyph refers to a stand-in for a bolder part before any part is unlinked.
    standing = stand_ins(font, classes)
    for glyph in font.glyphs():
        if (refs := relinked(glyph, classes, standing)) != [
                (name, matrix) for name, matrix, *_ in glyph.references]:
            glyph.references = tuple(reversed(refs))  # written in reverse, as in reposition()
            glyph.autoHint()
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
        if classes[name] != BOLDER or not len(glyph.foreground) or name in mirrors:
            continue
        bound, pen = bounds.get(name, (-geo.FAR, geo.FAR)), pen_of(name, small)
        if name in PIECES_APART:
            glyph.foreground = pieces_apart(name, glyph.foreground, bound, scratch, pen)
        else:
            outline, parts = merged.get(name, (glyph.foreground, []))
            if name in RAISED:
                outline = raised(outline, PEN[1])
            grown = [fitted(name, layer, box, scratch, pen)
                     for layer, box in [(outline, own.get(name, bound)),
                                        *((part, bound) for part in parts)] if len(layer)]
            glyph.foreground = grown[0] if len(grown) == 1 else geo.cleanup(geo.union(*grown))
        glyph.autoHint()
    for left, right in mirrors.items():
        font[left].foreground = geo.mirrored_x(font[right].foreground, ADVANCE / 2)
        font[left].autoHint()
    # Parts before the glyphs built from them, so each sees its parts as they end up (ΐ's ΅).
    for glyph in sorted(font.glyphs(), key=lambda g: depth(font, g.glyphname)):
        name = glyph.glyphname
        if classes[name] != BOLDER or not glyph.references:
            continue
        before = glyph.references
        if name in bounds:
            fit_references(font, glyph, bounds[name])
        lower_into_line(font, glyph)
        if name in APART:
            move_apart(font, glyph, gaps[name])  # from the parts as lowered (΅'s tonos)
        if glyph.references != before:
            glyph.autoHint()  # a reference assigned leaves the hints stale
    raise_clear(font, [glyph for glyph in font.glyphs()
                       if is_letter(glyph.unicode) and classes[glyph.glyphname] == BOLDER
                       and glyph.references], heights, small)
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
