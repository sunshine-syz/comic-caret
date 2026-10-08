"""Derive src/ComicCaret-Bold.sfd, the bold master, from src/ComicCaret-Regular.sfd.

Usage: python3 tools/make_bold.py [BOLD_SFD]

The bold is the regular with its strokes made heavier, and its pictures kept as they are.
Nothing in the bold SFD is drawn by hand: this script rewrites the whole file from the
regular, so running it again changes nothing but ModificationTime, and
tests/test_make_bold.py fails while it is out of date. Change the regular or this script,
then rerun it and ./build.sh. docs/design-notes.md says how the pen and the rules were chosen,
and each name list's comment gives the reason for its glyphs.

classify() puts every glyph of the regular in one of two sets:

- BOLDER: what a pen writes: letters, figures, the combining marks, punctuation, symbols,
  arrows and the ligatures. Each outline grows outward by an elliptical pen, PEN wide and
  tall (offset()). A stem grows half the pen's width on each side and a level stroke half
  its height, so a bold letter keeps the regular's rows. Some glyphs take another pen
  (pen_of()): the small parts a smaller one (small_pen()), the heavy marks a larger one
  (HEAVY), | and ¦ a wider one (BAR_WEIGHT), and the glyphs of TURNED, ROUND, NARROW and
  OUTWARD the pen as those lists change it.
- SHARED: what is drawn as a picture, which the reference bolds keep as their regulars draw
  them (SHARED_BLOCKS, SHARED_CHARS), and .notdef, a box. Copied unchanged, hints included.

The offset grows every edge alike, so - stays centred on the math axis and the ligature
pieces still match at their seams; a piece's flat cut end past the cell is trimmed back to
the regular's. Not FontForge's changeWeight(): in its LCG mode it grows a level stroke upward
only, which takes - off the axis. The pen opens no white: a notch whose mouth it shuts is
filled (notches_filled()).

The pen must not push ink out of the cell, or past the regular's own overhang; nor any glyph
but a letter or figure nearer the cell's sides than SYMBOL_SIDE (side_bounds()), so two
symbols side by side keep twice that between them. A glyph that would pass its bound is
condensed before the offset, just enough, so every stem still grows by the full pen (fitted()).
A composite whose part would pass it moves its references in toward the cell's centre instead.

A composite keeps its references, so an accented letter follows its base; a glyph with an
outline and references has only its outline offset. Some parts become the glyph's own outline
first (unlinked_parts()): a shared glyph's bolder part keeps the regular's outline, and a part
turned a quarter (⋮ on …) grows as the glyph's outline. A left glyph the regular draws as its
right one mirrored is the bold right one mirrored (mirror_pairs()).

Where the pen alone would break a rule the regular keeps, a name list says what the bold does
instead: parts move apart (APART, DOUBLES, TIGHT); an outline keeps its own box (OWN_BOX,
ACROSS_AS_UP); parts grow on their own (MERGED); pieces give way to each other (PIECES_APART,
SLASHES, LIGHT_PIECES, SHRUNK, OPENED, DASHED, LIFTED, HEADS_APART, TICKED); a bar moves up its
stems (RAISED) or keeps its ends (BLUNT). An accent the pen grows out of the line box moves down
into it (lower_into_line()), and a mark it grows within MARK_CLEARANCE of its letter rises clear
(raise_clear()). Widths, anchors and the lookups carry over as they are.
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
from add_ligatures import GENERATED, THREE_ENDS, TIGHT_KEEP
from add_shapes import CODES
from measure import (
    area,
    covered,
    distance,
    gap,
    ink,
    length,
    outline,
    pieces,
    spans_at_x,
    spans_at_y,
    vertical_edges,
)
from project import (
    ADVANCE,
    BOLD_SFD,
    LINE_TOP,
    MARK_CLEARANCE,
    OVERLAP,
    ROUNDING,
    SFD,
    is_alphanumeric,
    is_letter,
    save_checked,
    validation_errors,
)

# Chosen by proof against the reference bolds on 2026-10-01. In the 550 cell, its ink in a-z
# is 57.5% of the x-height band (the reference bolds' 51-59%), a step of 13.5 points from the
# regular's 44.0% (Maple Mono's, the smallest reference step, is 14), and the counters at our
# x-height, n 172, o 199 and e 109, are each at or above the narrowest reference bold's.
PEN = (35, 14)  # (width, height) of the elliptical pen

SHARED, BOLDER = "shared", "bolder"

# Box Drawing, Block Elements and Geometric Shapes; Braille; the Powerline symbols.
SHARED_BLOCKS = (range(0x2500, 0x2600), range(0x2800, 0x2900), range(0xE000, 0xF900))
# Outside them: the spinner frames but ‼, which is two ! and grows with them, as the italic
# slants it; the other frames of a spinner, so none grows and the spinner doesn't pulse: Claude
# Code's ✢ ✳ ✶ ✻ ✽, ✶ being also the star spinner's first frame, which add_shapes.py draws
# ✷ ✸ ✹ ✺ from; the media controls ⏵ ⏸ ⏺, which status lines show side by side at one height;
# and ☐, which □ and ■ are (tests/test_symbols.py), and ☑ ☒, ☐ marked, so the three boxes stay
# alike.
SHARED_CHARS = (frozenset(map(chr, CODES)) - {"‼"}) | frozenset("✢✳✶✻✽⏵⏸⏺☐☑☒")

# The heavy marks, each drawn as its light glyph pushed out (docs/design-notes.md), and that
# glyph: ✔ ✘ ✖ for ✓ ✗ ✕, ❯ ❮ ❱ ❰ for > <, and ➜ for →. Each grows by the pen scaled by how
# much more ink the regular gives it than its light glyph, so it stays as much heavier
# (tests/test_symbols.py); the full pen would grow the light glyph more for its ink and close
# the difference. The reference bolds keep their heavy marks as their regulars draw them, and
# so lighter against their bold light marks; ours read heavier in every weight.
HEAVY = {"uni2714": "uni2713", "uni2718": "uni2717", "uni2716": "uni2715",
         "uni276F": "greater", "uni276E": "less", "uni2771": "greater", "uni2770": "less",
         "uni279C": "arrowright"}

# Besides the .small glyphs, the parts the regular draws as light as the small figures and
# letters beside them (tests/test_latin.py): the fraction bar, the ordinals' bar and the ring
# of © ®. They take the small pen too, so they stay as heavy as their figures and letters;
# the ring takes it outward only (OUTWARD).
LIGHT_PARTS = ("slash.fraction", "bar.ordinal", "circle.copyright")

# The level bars the regular draws as heavy as the stems beside them, not as a level stroke of
# a letter: ª º's bar, as heavy as the letter's stems above it, and ⇪'s, as heavy as the walls
# of ⇧'s shaft (tests/test_symbols.py). It grows by its pen's width up and down too, so it stays
# as heavy as the bold stems; the level pen leaves it 21 lighter, for ⇪ more than its weight
# test allows.
ROUND = ("bar.ordinal", "uni21EA")

# The glyphs that grow by a share of their pen's width, which keeps more of their white, and
# that share (tests/test_latin.py holds the white over the reference bolds'). Grown as build()
# grows them and measured as the test measures them, share by share in hundredths: ẞ's white
# between the stem and the diagonal is 78 at 0.7, over Maple Mono Bold's 64, as at every share
# up to the full pen's 67.5; the small 4's counter is 0.139 of its height from 0.79 to 0.87,
# over Maple Mono Bold's ¼ (0.136), and closes to 0.134 at 0.88 and 0.128 at the full pen.
# Their stems grow 10.5 and 3.7 less than the others'.
NARROW = {"uni1E9E": 0.7, "four.small": 0.83}

# How heavy the bold draws |, across its middle. The regular draws it lighter than its stems,
# 77 where I is 94, and the pen would grow it to 111, 0.85 of the bold I, under every reference
# bold's 0.896 to 1.112 (tests/test_make_bold.py), so || read thin beside I|l. | and ¦ grow by
# a pen as much wider as brings | to 125, as heavy as the bold l.
BAR_WEIGHT = 125

# The glyphs drawn with two ticks of | through a letter, and that letter: ₿'s, past B's top
# and foot. The letter grows by the pen, and the ticks by |'s, so they stay as heavy as |
# (tests/test_symbols.py); grown in place they would come 4 apart, where the regular keeps 52,
# so each moves away from the other by as far as |'s pen grows it (ticks_apart()).
TICKED = {"uni20BF": "B"}
# How far a moved tick runs into its letter, so it meets B's bowl past the corner it moved over:
# inside ₿'s top and foot strokes (79 and 102 deep), clear of its counters.
TICK_ROOT = 60

# The strokes the regular draws as another stroke turned, and the turn, anticlockwise: the
# tonos is the acute turned 25° steeper, as tests/test_make_bold.py holds the regular's drawing.
# The pen turns with it, so the bold tonos is the bold acute turned. The level pen would grow
# the steeper stroke heavier.
TURNED = {"tonos": math.radians(25)}

# The rings that grow outward only, by twice their pen, so they thicken by its whole width as
# a stem does on its two sides: © ®'s, which the regular draws as heavy as the letter inside
# it (tests/test_latin.py). Its counter stays the regular's, so the letter keeps its room:
# grown both ways, the ring came 35 from ®'s R, under Fira Code Bold's 41 around its ©.
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
# The dots of i j rise, so they stay as far above the stem as the regular's, and the bar of
# ª º moves down, clear of the letter its round pen grows it into. ĳ, one outline, keeps its
# dots 14 lower than i j's: raising them would grow it past the pen, which
# tests/test_make_bold.py holds every outline to.
RIGHT, LEFT, UP, DOWN = (1, 0), (-1, 0), (0, 1), (0, -1)
APART = {"ldot": ("periodcentered", RIGHT), "dcaron": ("caron.alt", RIGHT),
         "lcaron": ("caron.alt", RIGHT), "Lcaron": ("caron.alt", RIGHT),
         **dict.fromkeys(("Alphatonos", "Epsilontonos", "Etatonos", "Iotatonos", "Omicrontonos",
                          "Upsilontonos", "Omegatonos"), ("tonos", LEFT)),
         "dieresistonos": ("dieresis", DOWN),
         **dict.fromkeys(("i", "iogonek", "j"), ("period", UP)),
         **dict.fromkeys(("ordfeminine", "ordmasculine"), ("bar.ordinal", DOWN))}

# The double marks, two copies of one mark side by side: “ ” „ ″ ‖ ‼. The pen grows the copies
# into each other; they move apart, each as far, by the fewest units that keep the regular's
# white between them (spread()), which the reference bolds' keep too (tests/test_symbols.py).
# One moving alone would take the mark off the cell's middle.
DOUBLES = ("quotedblleft", "quotedblright", "quotedblbase", "second", "uni2016", "uni203C")

# The glyphs of a tightened pair or three (add_ligatures.TIGHT_KEEP, THREE_ENDS), each with the
# way and the share of its pen's width it moves back out. The pen grows the two of a pair
# toward each other by half its width each, which would merge && into one shape and all but
# close ??; each moves back that far, so the pair keeps the regular's white, and ++'s bars
# their overlap. A three's middle glyph stays in place, so its outer glyphs move back the
# pen's whole width.
TIGHT = ({f"{name}.{side}": (way, 0.5) for name in TIGHT_KEEP
          for side, way in (("tight_r", LEFT), ("tight_l", RIGHT))}
         | {f"{name}.{side}": (way, 1)
            for side, way in (("tight_r2", LEFT), ("tight_l2", RIGHT))
            for name in THREE_ENDS[side]})

# The outlines condensed to keep their own regular box, where the pen would grow them into
# their neighbours or wider than the reference bolds draw them: ™'s T and M, 23 apart, which
# the small pen would grow until they all but touch, so ™ stays a composite of the two; Θ's
# bar, which would come 21 from the ring, under the reference bolds' 38, and keeps 39; ⌥,
# which Fira Code Bold, the one reference bold that draws it, draws as wide as its regular
# (tests/test_legibility.py); and ď ľ Ľ's caron, which in ď runs on into the next cell, where
# grown 35 wider it would run into an l's flag. It keeps 32 from it (tests/test_latin.py), as
# Maple Mono Bold's keeps 29, and stands steeper and lighter: across its slant it weighs 0.81
# of the stem, as Maple Mono Bold's does (Intel One Mono Bold's 0.74, Fira Code Bold's 0.75).
OWN_BOX = ("T.small", "M.small", "Theta", "uni2325", "caron.alt")

# The glyphs the regular draws as another turned a quarter: ⇕, ⇔ turned with its shaft
# lengthened. Turned, the pen would grow ⇕ as tall as it grows ⇔ wide, past ↑'s height; so ⇕
# grows by the pen as it is, condensed until it grows across only by the pen's height, as ⇔
# grows up and down, and stays as wide as ⇔ is tall (tests/test_symbols.py).
ACROSS_AS_UP = ("uni21D5",)

# Composites drawn as one outline, each part grown on its own: Θ, whose bar beside a reference
# to the bold O fails validate() once saved, as FontForge reads the hint masks O's overlapping
# stems need against Θ's own stems, which the bar's wobble makes overlap too; and ∄, whose
# slash, / turned steeper, grows as an outline (unlinked_parts()) beside ∃'s E the same way.
MERGED = ("Theta", "uni2204")

# Outlines whose pieces stand side by side, which the pen would grow into one: the arrows and
# bars of ⇥ and ↹ (⇤ is ⇥ mirrored), 30 apart, ‰'s two lower zeros, 53 apart, and the letters
# of ℃ ℉ № beside their ring and o, 1 to 36 apart. Each piece grows on its own, and the wider
# is condensed away from the other, or both alike when they are as wide, until the white
# between them is the regular's. Each keeps its far end where the pen grows it, or at the side
# room where the pen would grow it past (‰'s zeros), so ‰ stays at least as wide as % and
# centred: ⇥ ↹'s bar keeps the full pen, and the white twice SYMBOL_SIDE (pieces_apart());
# ℃'s ring stays before its C (tests/test_symbols.py). A glyph the list misses fails a test:
# test_bolder_glyphs_keep_their_pieces_and_counters (tests/test_make_bold.py) where the pen
# joins its pieces (⇥ ↹ №), else a rule on its pieces or its slash in tests/test_symbols.py or
# tests/test_make_bold.py (‰ ℃ ℉). Naming the glyphs keeps the choice between PIECES_APART,
# SHRUNK and OPENED explicit: each gives way in its own way.
PIECES_APART = ("uni21E5", "uni21B9", "perthousand", "uni2103", "uni2109", "uni2116")

# Of those, the ones whose tallest piece is a slash leaning right that the pen grows into a
# piece below its foot: ‰'s, which would come 27 from the zero under it, where the regular
# keeps 46 (Maple Mono Bold's ‰ keeps 21.5). The slash shortens along its length, its top end
# staying, by the fewest units that keep the regular's white, so it ends higher up its slant and
# keeps the weight the pen gives %'s.
SLASHES = ("perthousand",)

# Of those, the ones whose pieces but the tallest the regular draws as light as the small
# figures, which grow by the small pen, so they stay as light: ℃ ℉'s ring and №'s o and bar,
# º's. The full pen would close ℃ ℉'s ring to 42 across, where the small pen leaves 54.
LIGHT_PIECES = ("uni2103", "uni2109", "uni2116")

# Outlines whose pieces the pen grows within twice SYMBOL_SIDE of each other, where condensing
# them apart can't help: ※'s dots in the notches of its X, ⧉'s front square before its back one,
# ⌦'s × in its tag (⌫ is ⌦ mirrored) and %'s rings beside its slash. Each piece grows on its
# own, and of two too close, the one that clears with less shrinks about its point farthest
# from the other, just enough to keep the seam (shrunk()), which the regular keeps and
# tests/test_symbols.py holds them to.
SHRUNK = ("uni203B", "uni29C9", "uni2326", "percent")

# Outlines with a piece through a gap in their ring, which the pen grows shut on it: ⎋'s arrow
# out through its ring. The ring's ends are cut back about its middle, just enough to keep twice
# SYMBOL_SIDE from the grown arrow (opened()). The arrow would have to shrink by a third to clear.
OPENED = ("uni238B",)

# The dashed arrows, a head over dashes: ⇡ (⇣ is ⇡ turned). The pen grows each dash into the
# pieces beside it by its height, as it grows the hyphen's stroke; so each dash first shortens
# at its top by twice the pen's height, and the white above it grows by the pen's height, as
# much as the hyphen's stroke: each gap stays as much wider than the stroke as the regular's,
# so it stays open at 12 px (tests/test_symbols.py).
DASHED = ("uni21E1",)

# The signs whose bars run past their letter on both sides, 43 to 127 units: ₩ ₦ ₱. The pen
# lengthens a round end by half its width, which tapers the bars' run clear of the letter, so
# they would reach the hyphen's weight only near it (tests/test_symbols.py). So the sign keeps
# its regular box, condensed, and also grows by a pen of the full height and next to no width,
# and the two are united: the bars' ends keep the regular's length, as heavy as the hyphen's
# stroke.
BLUNT = ("uni20A9", "uni20A6", "uni20B1")

# The outlines that are another glyph's outline moved, over a bar: ⇪, ⇧ lifted. The bold draws
# that piece as the bold ⇧ moved as far, so it stays ⇧ (tests/test_symbols.py), lifted a little
# further when its bar, grown as heavy as ⇧'s shaft walls (ROUND), comes within twice
# SYMBOL_SIDE of it.
LIFTED = {"uni21EA": "uni21E7"}

# The arrows with two heads, ->> <<-: the pen grows the heads toward each other, leaving 143
# between them, under Fira Code Bold's 155, the one reference bold that draws ->>. The inner
# head, with the shaft it ends, moves along the shaft by the fewest whole units that keep
# HEAD_WHITE between the two (heads_apart()); the shaft runs on under the cell before's. A
# wider HEAD_PITCH in tools/add_ligatures.py would do it too, but would also take the regular's
# white from 171 to 184, past 1.7.0's 173.
HEADS_APART = ("greater.twohead", "less.twohead")
HEAD_WHITE = 309.7 * ADVANCE / 1200  # Fira Code Bold's, 309.7 of its 1200 cell

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


def middle_stroke(layer, name):
    """The width of the one stroke across the middle of the layer's box: glyph `name`'s stem,
    which a pen is measured from."""
    _, y0, _, y1 = layer.boundingBox()
    spans = spans_at_y(layer, (y0 + y1) / 2)
    if len(spans) != 1:
        sys.exit(f"{name}: {len(spans)} strokes cross its middle, where its pen is measured "
                 "from one")
    [(x0, x1)] = spans
    return x1 - x0


def small_pen(font):
    """PEN scaled by how much lighter the regular draws its small parts than its letters: the
    stem of one.small over the stem of one, each at mid-height. A bold superscript is then as
    much bolder as a bold letter."""
    def stem(name):
        return middle_stroke(font[name].foreground, name)
    ratio = stem("one.small") / stem("one")
    return tuple(size * ratio for size in PEN)


def pens(font):
    """{glyph name: (width, height)} for each glyph of the regular, opened as `font`, that grows
    by another pen than PEN: the small_pen() for a small part, for a HEAVY mark PEN scaled by
    its ink over its light glyph's, and for | and ¦ PEN as wide as grows | to BAR_WEIGHT."""
    small = small_pen(font)
    found = {glyph.glyphname: small for glyph in font.glyphs()
             if glyph.glyphname.endswith(".small") or glyph.glyphname in LIGHT_PARTS}
    def weight(name):
        layer = ink(font, name)
        return 2 * area(layer) / length(layer)
    for heavy, light in HEAVY.items():
        found[heavy] = tuple(size * weight(heavy) / weight(light) for size in PEN)
    found["bar"] = found["brokenbar"] = (BAR_WEIGHT - middle_stroke(ink(font, "bar"), "bar"),
                                         PEN[1])
    return found


def pen_of(name, grows_by):
    """The pen glyph `name` grows by, (width, height, turn): its own in `grows_by` (pens()), else
    PEN; narrower for a NARROW glyph, as tall as wide for a ROUND bar, twice as large for an
    OUTWARD ring, and turned for a TURNED stroke."""
    width, height = grows_by.get(name, PEN)
    width *= NARROW.get(name, 1)
    height = width if name in ROUND else height
    grow = 2 if name in OUTWARD else 1
    return grow * width, grow * height, TURNED.get(name, 0)


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
    cell, as <='s tips, grows like any other, even where it runs straight for a few units at
    its turn, as the points of <| <|> do: only an edge on the overlap line is a cut."""
    if not GENERATED.fullmatch(name):
        return -geo.FAR, geo.FAR
    x0, _, x1, _ = layer.boundingBox()
    flat = {x for x, *_ in vertical_edges(layer)}
    return (x0 if x0 == -OVERLAP and x0 in flat else -geo.FAR,
            x1 if x1 == ADVANCE + OVERLAP and x1 in flat else geo.FAR)


def side_bounds(font, classes):
    """{glyph name: (x0, x1)}: where the bold ink of each glyph must stay, read from the regular,
    opened as `font`. A letter or figure (project.is_alphanumeric(), Ω among them) keeps to the
    cell, or to the regular's own overhang (ď, the tonos capitals). Any other glyph keeps the
    side room the regular gives it, down to SYMBOL_SIDE, so two side by side keep twice that
    between them (tests/test_symbols.py). A part a bolder glyph holds unmoved can't move in
    toward the cell's middle, so it keeps that glyph's bound too: © ®'s ring. A letter held so
    (Δ in ∆, đ in ₫) is never condensed to it (fitted()). A part the bold draws as the glyph's
    own outline (unlinked_parts()), as Θ's O, and a shared glyph's part, which doesn't grow,
    keep their own."""
    side = project.SYMBOL_SIDE
    bounds = {}
    for glyph in font.glyphs():
        if (code := glyph.unicode) >= 0:
            x0, _, x1, _ = glyph.boundingBox()
            room = 0 if is_alphanumeric(code) else side
            bounds[glyph.glyphname] = (min(x0, room), max(x1, ADVANCE - room))
    # Users first, so a part takes the bound its users took from theirs.
    for glyph in sorted(font.glyphs(), key=lambda g: depth(font, g.glyphname), reverse=True):
        bound = bounds.get(glyph.glyphname)
        if bound is None or classes[glyph.glyphname] == SHARED:
            continue
        unlinked = unlinked_parts(glyph, classes)
        for name, matrix, *_ in glyph.references:
            if tuple(matrix) == psMat.identity() and name not in unlinked:
                x0, x1 = bounds.get(name, (-geo.FAR, geo.FAR))
                bounds[name] = (max(x0, bound[0]), min(x1, bound[1]))
    return bounds


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
    which keep the regular's outline; a bolder glyph's shared parts, which grow as its outline;
    a bolder glyph's bolder parts turned a quarter (⋮ on …) or scaled, which grow as its outline, since
    the reference would turn or scale the pen too; and every part of a MERGED glyph."""
    if glyph.glyphname in MERGED:
        return [name for name, *_ in glyph.references]
    # A translation, a 180° turn or a mirror keeps the pen as it is.
    return [name for name, matrix, *_ in glyph.references
            if classes[name] != classes[glyph.glyphname]
            or classes[name] == BOLDER
            and tuple(round(abs(v), 4) for v in matrix[:4]) != (1, 0, 0, 1)]


def lifted_piece(font, name, base):
    """(how far up the LIFTED glyph `name` places the outline of `base`, the glyph's other
    pieces) in the regular, opened as `font`."""
    layer = font[base].foreground
    found, rest = [], fontforge.layer()
    for piece in pieces(font[name].foreground):
        rise = piece.boundingBox()[1] - layer.boundingBox()[1]
        if outline(piece) == outline(geo.moved(layer, 0, rise)):
            found.append(rise)
        else:
            rest += piece
    if len(found) != 1:
        sys.exit(f"{name}: no one piece of it is {base} moved up")
    return found[0], rest


def offset(outline, overlap, pen):
    """The outline grown by `pen`: stroked, the stroke's inner edge dropped, and united with
    the outline. `overlap` is how the stroke removes its own overlaps first, if at all."""
    layer = outline.dup()
    layer.stroke("elliptical", *pen, "round", "round", removeinternal=True,
                 removeoverlap=overlap)
    layer += outline.dup()  # removeOverlap() would change the outline's own contours
    layer.removeOverlap()
    return layer


def notches_filled(layer, outline):
    """The grown `layer` with each hole that lies in none of the counters of `outline`, the one
    it grew from, filled. The pen opens no white, so such a hole is a notch whose mouth the pen
    shut (a wave arrow's > head's)."""
    def solid(contour):
        found = fontforge.layer()
        found += contour
        return geo.clockwise(found)
    counters = [solid(c) for c in outline if not c.isClockwise()]
    out = fontforge.layer()
    for contour in layer:
        if contour.isClockwise() or any(covered(solid(contour), c) > 0 for c in counters):
            out += contour
    return out


def with_counters(layer, outline):
    """The grown `layer`'s outer contours with the counters of `outline`, the regular's, in
    place of its own (OUTWARD)."""
    out = fontforge.layer()
    for contour in (*(c for c in layer if c.isClockwise()),
                    *(c for c in outline if not c.isClockwise())):
        out += contour
    return out


def raised(name, outline, rise):
    """The outline of glyph `name` with the bar above its counter moved up by `rise` along its
    stems (RAISED): the stems' straight part beside the counter lengthened by `rise`, and above
    the bar shortened as much, so their ends stay where they are."""
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
    # The stems give up `rise` from the bar halfway to their tops, short of their round ends;
    # where that half is no longer than `rise`, the bar would pass the ends.
    if rise >= (top - bar_top) / 2:
        sys.exit(f"{name}: its stems above the bar are too short to give up {rise}")
    out = stretched(outline, y0 + third, y1 - third, rise)
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
        layer = notches_filled(offset(outline, overlap, pen), outline)
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


def fitted(name, outline, bound, scratch, pen, anchor=None, held=False):
    """emboldened(), condensed first just enough that the bold ink stays within `bound`,
    (x0, x1): the outline scaled horizontally about x = `anchor`, or else its ink centre, so
    every stem still grows by the full pen. A `held` letter, one a symbol holds, exits instead:
    condensed to the symbol's side room, the letter itself would narrow wherever it is typed."""
    layer = emboldened(name, outline, scratch, pen)
    x0, _, x1, _ = outline.boundingBox()
    centre = (x0 + x1) / 2 if anchor is None else anchor
    span = max(x1 - centre, centre - x0)  # how far the further side lies from the centre
    taken = 0
    # Rounding the condensed outline can leave a unit over, which another pass takes in.
    for passes in itertools.count():
        bx0, _, bx1, _ = layer.boundingBox()
        if (excess := max(bound[0] - bx0, bx1 - bound[1])) <= 0:
            return layer
        if held:
            sys.exit(f"{name}: a letter a symbol holds, its ink passes the symbol's {bound}")
        if passes == 3:
            sys.exit(f"{name}: condensed three times, its ink still passes {bound}")
        taken += excess
        narrow = geo.transformed(outline, geo.about(psMat.scale(1 - taken / span, 1), centre, 0))
        layer = emboldened(name, narrow, scratch, pen)


def least(clears, most):
    """The least whole n from 0 to `most` for which clears(n) holds, found by halves, or None
    if clears(most) doesn't: every n past the least must clear too."""
    if not clears(most):
        return None
    low, high = 0, most
    while low < high:
        middle = (low + high) // 2
        low, high = (low, middle) if clears(middle) else (middle + 1, high)
    return low


def pieces_apart(name, outline, bound, scratch, pen, light):
    """The outline's pieces (PIECES_APART) each fitted() within `bound`, by `pen`, or the ones
    but the tallest by `light` for LIGHT_PIECES; and of two side by side, the wider condensed
    away from the other, or both by half when they are as wide, until the white between their
    boxes is the regular's. A SLASHES slash then shortens along its length, its top end
    staying, until it keeps the regular's white to the pieces below."""
    parts = pieces(outline)
    boxes = [part.boundingBox() for part in parts]
    tallest = max(range(len(parts)), key=lambda k: boxes[k][3] - boxes[k][1])
    own = [light if name in LIGHT_PIECES and k != tallest else pen for k in range(len(parts))]
    grown = [fitted(name, part, bound, scratch, own[k]) for k, part in enumerate(parts)]

    def far_kept(k, side):
        """(parts[k], the x of its far end on `side`, 0 left or 1 right), moved in first as far
        as the pen would grow that end past `bound`."""
        x, out = boxes[k][2 * side], reach(own[k])[0]
        inward = max(bound[0] + out - x, 0) if side == 0 else min(bound[1] - out - x, 0)
        return geo.moved(parts[k], inward, 0), x + inward
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
            part, far = far_kept(a, 0)
            grown[a] = fitted(name, part, (bound[0], left - share * lack), scratch, own[a], far)
        if share < 1:
            part, far = far_kept(b, 1)
            grown[b] = fitted(name, part, (right + (1 - share) * lack, bound[1]), scratch,
                              own[b], far)
    if name in SLASHES:
        i = tallest
        x0, y0, x1, y1 = boxes[i]
        below = [k for k in range(len(parts)) if boxes[k][3] <= y0]
        wanted = gap(parts[i], geo.union(*(parts[k] for k in below)))
        rest = geo.union(*(grown[k] for k in below))
        slant = math.hypot(x1 - x0, y1 - y0)
        # Laid along +x about its top end, where the slash's straight middle lies in the span.
        along = geo.about(psMat.rotate(-math.atan2(y1 - y0, x1 - x0)), x1, y1)
        span = (x1 - 0.7 * slant, x1 - 0.3 * slant)

        def shortened(units):
            # Shorter along its length only, so it keeps its weight and both round ends, and
            # its top end stays.
            flat = geo.stretch_span(geo.transformed(parts[i], along), *span, -units)
            back = psMat.compose(psMat.translate(units, 0), psMat.inverse(along))
            return fitted(name, geo.transformed(flat, back), bound, scratch, pen)
        # The least shortening that clears: every longer one clears too.
        if (units := least(lambda n: gap(shortened(n), rest) >= wanted, 2 * PEN[0])) is None:
            sys.exit(f"{name}: its slash can't shorten clear of the pieces below it")
        grown[i] = shortened(units)
    return geo.cleanup(geo.union(*grown))


def shrunk(name, outline, bound, scratch, pen, wanted):
    """The outline's pieces (SHRUNK) each fitted() within `bound`; then of two the pen grew
    within `wanted` of each other, the one that clears with fewer units shrinks first, about its
    outline point farthest from the other, by the fewest units that leave `wanted` between the
    two grown."""
    parts = pieces(outline)
    grown = [fitted(name, part, bound, scratch, pen) for part in parts]

    def shrinking(mine, other):
        """(the least units that clear, the piece `mine` shrunk by them), or None."""
        points = [(p.x, p.y) for contour in parts[mine] for p in contour if p.on_curve]
        anchor = max(points, key=lambda point: distance(point, parts[other]))
        size = max(math.dist(anchor, point) for point in points)

        def shrinks(units):
            matrix = geo.about(psMat.scale(1 - units / size), *anchor)
            return fitted(name, geo.transformed(parts[mine], matrix), bound, scratch, pen)
        # Every larger shrinking clears too.
        units = least(lambda n: gap(shrinks(n), grown[other]) >= wanted, 2 * PEN[0])
        return None if units is None else (units, shrinks(units))
    for a, b in itertools.combinations(range(len(parts)), 2):
        if gap(grown[a], grown[b]) >= wanted:
            continue
        options = [(found, mine) for mine, other in ((a, b), (b, a))
                   if (found := shrinking(mine, other))]
        if not options:
            sys.exit(f"{name}: no piece can shrink clear of another")
        (_, layer), mine = min(options, key=lambda option: option[0][0])
        grown[mine] = layer
    if any(gap(a, b) < wanted for a, b in itertools.combinations(grown, 2)):
        sys.exit(f"{name}: a shrunk piece came within {wanted} of another")
    return geo.cleanup(geo.union(*grown))


def opened(name, outline, bound, scratch, pen, wanted):
    """The OPENED outline's two pieces each fitted() within `bound`, its ring, the one with the
    most ink, first cut back at the ends of its gap: by the fewest whole degrees either side of
    the way from the middle of its box to the other piece's farthest point, that leave `wanted`
    between the two grown."""
    ring, through = sorted(pieces(outline), key=area, reverse=True)
    grown = fitted(name, through, bound, scratch, pen)
    x0, y0, x1, y1 = ring.boundingBox()
    middle = ((x0 + x1) / 2, (y0 + y1) / 2)
    tip = max((math.dist(middle, (p.x, p.y)), (p.x, p.y))
              for contour in through for p in contour if p.on_curve)[1]
    way = math.atan2(tip[1] - middle[1], tip[0] - middle[0])
    far = 2 * (x1 - x0 + y1 - y0)  # past the ring, whichever way

    def cut(degrees):
        """The ring outside the wedge `degrees` either side of the way to the tip, grown."""
        degrees = max(degrees, 1)  # a wedge of none leaves no fan
        turns = [way + math.radians(a) for a in range(degrees, 361 - degrees, 10)]
        turns.append(way + math.radians(360 - degrees))
        fan = [middle, *((middle[0] + far * math.cos(a), middle[1] + far * math.sin(a))
                         for a in turns)]
        # On whole units first, so the cut's ends offset cleanly (docs/fontforge-pitfalls.md).
        return fitted(name, geo.cleanup(geo.clip(ring, geo.polygon(fan))), bound, scratch, pen)
    # Every wider cut clears too. Past 60°, a cut end runs level, which the pen grows past its
    # reach.
    if (degrees := least(lambda n: gap(cut(n), grown) >= wanted, 60)) is None:
        sys.exit(f"{name}: its ring can't open clear of the piece through it")
    return geo.cleanup(geo.union(cut(degrees), grown))


def ticks_apart(name, outline, letter, bound, scratch, pen, bar_pen):
    """The TICKED outline's part inside `letter`'s box fitted() by `pen`, and each of its two
    ticks above and below fitted() by |'s `bar_pen`, moved away from the other by as far as
    that pen grows it toward it, so the two keep the regular's white. Each tick takes the
    outline TICK_ROOT into the letter with it, so it still meets the letter."""
    _, foot, _, top = letter
    grown = [fitted(name, geo.trim(outline, y0=foot, y1=top), bound, scratch, pen)]
    for y, y0, y1 in ((top + 1, top - TICK_ROOT, geo.FAR), (foot - 1, -geo.FAR, foot + TICK_ROOT)):
        (l0, l1), (r0, r1) = spans_at_y(outline, y)
        for x0, x1, way in ((l0, l1, -1), (r0, r1, 1)):
            tick = geo.trim(outline, x0=x0, x1=x1, y0=y0, y1=y1)
            grown.append(fitted(name, geo.moved(tick, way * bar_pen[0] / 2, 0), bound, scratch,
                                bar_pen))
    return geo.cleanup(geo.union(*grown))


def dashed(name, outline, bound, scratch, pen):
    """The DASHED arrow's pieces each fitted() within `bound`: its head, the widest, as it is,
    and each dash shortened at its top by twice the pen's height first."""
    parts = pieces(outline)
    head = max(parts, key=lambda part: part.boundingBox()[2] - part.boundingBox()[0])
    grown = []
    for part in parts:
        if part is not head:
            _, y0, _, y1 = part.boundingBox()
            part = geo.transformed(part, geo.about(psMat.scale(1, 1 - 2 * pen[1] / (y1 - y0)),
                                                   0, y0))
        grown.append(fitted(name, part, bound, scratch, pen))
    return geo.cleanup(geo.union(*grown))


def heads_apart(name, layer):
    """The HEADS_APART glyph's outline with its inner head, the piece with the shaft, moved
    along the shaft until it stands HEAD_WHITE from the outer head."""
    # The inner head is on the shaft's side: right of the outer one in <<-, left in ->>.
    outer, inner = sorted(pieces(layer), key=lambda piece: piece.boundingBox()[0],
                          reverse=name.startswith("greater"))
    way = LEFT if inner.boundingBox()[0] < outer.boundingBox()[0] else RIGHT
    if (steps := clearance(inner, outer, way, HEAD_WHITE)) is None:
        sys.exit(f"{name}: its inner head can't move clear of the outer one")
    return geo.cleanup(geo.union(outer, geo.moved(inner, way[0] * steps, 0)))


def placed(font, glyph):
    """The ink of each of the glyph's references, where the glyph places it."""
    return [geo.transformed(ink(font, name), matrix) for name, matrix, *_ in glyph.references]


def reposition(glyph, place):
    """Place each of the glyph's references at the offset place(index, name, (dx, dy))
    returns."""
    refs = [(name, (*matrix[:4], *place(i, name, matrix[4:])))
            for i, (name, matrix, *_) in enumerate(glyph.references)]
    glyph.references = tuple(reversed(refs))  # FontForge writes references in reverse order


def unmoved(matrix):
    """The offset across at which a reference with this matrix leaves its part where the part
    stands in the cell: 0, or the advance for a part turned or mirrored about the cell's
    middle (∄'s E)."""
    return ADVANCE if matrix[0] < 0 else 0


def fit_references(font, glyph, bound):
    """Move the composite's references in toward the cell's centre, just enough that their
    ink stays within `bound`, (x0, x1): each part's move from where it stands in the cell
    (unmoved()) is scaled down alike, so the parts keep their order and their weight. A part
    APART moves is placed by its gap instead, and left out."""
    apart, _ = APART.get(glyph.glyphname, (None, None))
    scale = 1
    for (name, matrix, *_), layer in zip(glyph.references, placed(font, glyph), strict=True):
        x0, _, x1, _ = layer.boundingBox()
        dx = matrix[4] - unmoved(matrix)
        # A part passing a side moves in by dx * (1 - scale): only one moved toward that side
        # can.
        for excess, inward in ((bound[0] - x0, -dx), (x1 - bound[1], dx)):
            if name == apart or excess <= 0:
                continue
            if inward <= excess:
                sys.exit(f"{glyph.glyphname}: its {name} passes {bound} and can't move in")
            scale = min(scale, 1 - excess / inward)
    if scale < 1:
        homes = [unmoved(matrix) for _, matrix, *_ in glyph.references]
        # Rounding toward the centre keeps each part in.
        reposition(glyph, lambda i, _, at: (homes[i] + math.trunc((at[0] - homes[i]) * scale),
                                            at[1]))


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

    # Every n past the least that clears clears too.
    return least(lambda n: gap(geo.moved(mine, dx * n, dy * n), rest) >= wanted, most)


def shifted(moves):
    """The place for reposition() that moves each part named in `moves` by its (dx, dy)."""
    def place(_, name, at):
        dx, dy = moves.get(name, (0, 0))
        return at[0] + dx, at[1] + dy
    return place


def parted(font, glyph, part):
    """(the part's ink, the ink of the glyph's own outline and its other parts), each where the
    glyph places it."""
    mine, rest = fontforge.layer(), glyph.foreground.dup()
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


def spread(font, glyph, wanted):
    """Move the two copies of a DOUBLES glyph apart, each by the same whole units, the fewest
    that leave `wanted` between them: the regular's gap, which the pen grew them into."""
    inks = placed(font, glyph)
    left = min(range(2), key=lambda i: glyph.references[i][1][4])
    # Moving the left copy twice as far keeps the same gap as moving each copy once.
    if (steps := clearance(inks[left], inks[1 - left], (-2, 0), wanted)) is None:
        sys.exit(f"{glyph.glyphname}: its copies can't move clear of each other")
    reposition(glyph, lambda i, _, at: (at[0] + (-steps if i == left else steps), at[1]))


def marks_above(font, glyph, grows_by):
    """([(name, ink)] of the composite letter's marks above its letter, the letter's ink): the
    letter is its one reference to a letter. A mark is above when it starts no lower than the
    letter's top less how far the pen grew the two toward each other, each by its pen's reach
    up (pen_of(); `grows_by` is the pens())."""
    parts = list(zip((name for name, *_ in glyph.references), placed(font, glyph)))
    letters = [(name, layer) for name, layer in parts if is_letter(font[name].unicode)]
    if len(glyph.foreground) or len(letters) != 1:
        return [], None
    [(base, letter)] = letters
    top, grew = letter.boundingBox()[3], reach(pen_of(base, grows_by))[1]
    return [(name, layer) for name, layer in parts if layer is not letter
            and layer.boundingBox()[1] >= top - grew - reach(pen_of(name, grows_by))[1]], letter


def raise_clear(font, letters, heights, grows_by):
    """Raise each mark that the pen grew within MARK_CLEARANCE of its letter, by the fewest
    whole units that clear it, and the same mark as far on every letter where the regular
    places it as high, so a row of them stays level (the tonos over έ ό, and so over ά ή ί).
    `heights` holds how high the regular places each (letter, mark). One row breaks on
    purpose: ΐ ΰ's dieresis, which ΅ takes down below its tonos (APART)."""
    needs = collections.defaultdict(int)
    for glyph in letters:
        marks, letter = marks_above(font, glyph, grows_by)
        for name, mark in marks:
            if (steps := clearance(mark, letter, (0, 1), MARK_CLEARANCE)) is None:
                sys.exit(f"{glyph.glyphname}: its {name} can't rise clear of the letter")
            row = (name, heights[glyph.glyphname, name])
            needs[row] = max(needs[row], steps)
    for glyph in letters:
        marks, _ = marks_above(font, glyph, grows_by)
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
    # Most name lists are read only with `in`, which passes a stale name or a glyph two ways
    # claim unseen: each names bolder glyphs, the ways below grow a glyph only one way, and
    # SLASHES and LIGHT_PIECES are read only inside pieces_apart().
    for listed in ("LIGHT_PARTS", "ROUND", "NARROW", "TURNED", "OUTWARD", "RAISED",
                   "APART", "DOUBLES", "OWN_BOX", "ACROSS_AS_UP", "MERGED", "PIECES_APART",
                   "SLASHES", "LIGHT_PIECES", "SHRUNK", "OPENED", "DASHED", "BLUNT", "LIFTED",
                   "HEAVY", "HEADS_APART", "TIGHT", "TICKED"):
        for name in globals()[listed]:
            if classes.get(name) != BOLDER:
                sys.exit(f"make_bold.{listed}: {name} is no bolder glyph of the regular")
    ways = {"PIECES_APART": PIECES_APART, "SHRUNK": SHRUNK, "OPENED": OPENED, "DASHED": DASHED,
            "LIFTED": LIFTED, "TICKED": tuple(TICKED),
            "RAISED, MERGED, OWN_BOX, ACROSS_AS_UP, BLUNT, HEADS_APART":
            RAISED + MERGED + OWN_BOX + ACROSS_AS_UP + BLUNT + HEADS_APART}
    for (a, first), (b, second) in itertools.combinations(ways.items(), 2):
        if both := sorted(set(first) & set(second)):
            sys.exit(f"make_bold: {a} and {b} both name {both}")
    for listed in ("SLASHES", "LIGHT_PIECES"):
        if outside := sorted(set(globals()[listed]) - set(PIECES_APART)):
            sys.exit(f"make_bold.{listed}: {outside} not in PIECES_APART")
    grows_by, light, seam = pens(font), (*small_pen(font), 0), 2 * project.SYMBOL_SIDE
    # The pen raises every top and lowers every bottom by half its height, so the alignment
    # zones move out with them, before any glyph is hinted against them: the first pair of
    # BlueValues and OtherBlues hold bottoms, the rest of BlueValues tops. The baseline zone
    # only grows down: FreeType pulls its flat top edge down by up to 0.6 px at small sizes,
    # and from -12 that sank every letter a row at 9-12 px. BlueScale shrinks with the taller
    # zone, keeping the regular's share of the spec's limit (BlueScale times it under 1).
    def tallest():
        zones = (*font.private["BlueValues"], *font.private["OtherBlues"])
        return max(high - low for low, high in zip(zones[::2], zones[1::2]))

    rise, was = reach((*PEN, 0))[1], tallest()
    blues = font.private["BlueValues"]
    font.private["BlueValues"] = (blues[0] - rise, blues[1], *(y + rise for y in blues[2:]))
    font.private["OtherBlues"] = tuple(y - rise for y in font.private["OtherBlues"])
    font.private["BlueScale"] *= was / tallest()
    # Read before anything changes: where each glyph's ink must stay (side_bounds()); where
    # the outline of each of OWN_BOX, ACROSS_AS_UP and BLUNT must, its own box; the gap each part
    # APART moves keeps, and each DOUBLES glyph's copies; how high each mark stands; where
    # each LIFTED glyph's lifted piece stands and its other pieces; and the box of the letter
    # each TICKED glyph's ticks pass.
    bounds, own = side_bounds(font, classes), {}
    for name in OWN_BOX + ACROSS_AS_UP + BLUNT:
        x0, _, x1, _ = font[name].foreground.boundingBox()
        grow = PEN[1] / 2 if name in ACROSS_AS_UP else 0
        own[name] = (x0 - grow, x1 + grow)
    gaps = {name: gap(*parted(font, font[name], part)) for name, (part, _) in APART.items()}
    gaps.update((name, gap(*placed(font, font[name]))) for name in DOUBLES)
    heights = {(glyph.glyphname, name): matrix[5]
               for glyph in font.glyphs() for name, matrix, *_ in glyph.references}
    # A MERGED glyph's own outline and its parts' ink, as the regular draws them.
    merged = {name: (font[name].foreground, placed(font, font[name])) for name in MERGED}
    lifted = {name: lifted_piece(font, name, base) for name, base in LIFTED.items()}
    letters = {name: font[letter].boundingBox() for name, letter in TICKED.items()}
    mirrors = mirror_pairs(font, classes)
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
        if (classes[name] != BOLDER or not len(glyph.foreground) or name in mirrors
                or name in LIFTED):
            continue
        bound, pen = bounds.get(name, (-geo.FAR, geo.FAR)), pen_of(name, grows_by)
        # A letter's own bound takes in the whole cell, so a narrower one is a symbol's.
        held = is_alphanumeric(glyph.unicode) and (bound[0] > 0 or bound[1] < ADVANCE)
        if name in PIECES_APART:
            glyph.foreground = pieces_apart(name, glyph.foreground, bound, scratch, pen, light)
        elif name in SHRUNK:
            glyph.foreground = shrunk(name, glyph.foreground, bound, scratch, pen, seam)
        elif name in OPENED:
            glyph.foreground = opened(name, glyph.foreground, bound, scratch, pen, seam)
        elif name in DASHED:
            glyph.foreground = dashed(name, glyph.foreground, bound, scratch, pen)
        elif name in TICKED:
            glyph.foreground = ticks_apart(name, glyph.foreground, letters[name], bound, scratch,
                                           pen, pen_of("bar", grows_by))
        else:
            outline, parts = merged.get(name, (glyph.foreground, []))
            if name in RAISED:
                outline = raised(name, outline, PEN[1])
            grown = [fitted(name, layer, box, scratch, pen, held=held)
                     for layer, box in [(outline, own.get(name, bound)),
                                        *((part, bound) for part in parts)] if len(layer)]
            if name in BLUNT:  # a unit wide, as the stroke needs a pen with some width
                grown.append(fitted(name, outline, bound, scratch, (1, pen[1], 0)))
            glyph.foreground = grown[0] if len(grown) == 1 else geo.cleanup(geo.union(*grown))
            if name in HEADS_APART:
                glyph.foreground = heads_apart(name, glyph.foreground)
        glyph.autoHint()
    for left, right in mirrors.items():
        font[left].foreground = geo.mirrored_x(font[right].foreground, ADVANCE / 2)
        font[left].autoHint()
    for name, base in LIFTED.items():
        rise, rest = lifted[name]
        bar = fitted(name, rest, bounds[name], scratch, pen_of(name, grows_by))
        piece = geo.moved(font[base].foreground, 0, rise)
        if (further := clearance(piece, bar, UP, seam)) is None:
            sys.exit(f"{name}: its {base} can't rise clear of the rest")
        font[name].foreground = geo.cleanup(geo.union(geo.moved(piece, 0, further), bar))
        font[name].autoHint()
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
        if name in DOUBLES:
            spread(font, glyph, gaps[name])
        if name in TIGHT:
            ((dx, dy), share), [(part, *_)] = TIGHT[name], glyph.references
            back = round(share * pen_of(part, grows_by)[0])
            reposition(glyph, shifted({part: (dx * back, dy * back)}))
        if glyph.references != before:
            glyph.autoHint()  # a reference assigned leaves the hints stale
    raise_clear(font, [glyph for glyph in font.glyphs()
                       if is_letter(glyph.unicode) and classes[glyph.glyphname] == BOLDER
                       and glyph.references], heights, grows_by)
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
    regular's passes (the regular's ∄ overlaps its references; the bold's is one outline)."""
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
