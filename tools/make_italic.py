"""Derive src/ComicCaret-Italic.sfd, the italic master, from src/ComicCaret-Regular.sfd.

Usage: python3 tools/make_italic.py [ITALIC_SFD]

The italic is the regular slanted ANGLE degrees, with the graphics kept upright and f given a
descender. Nothing in the italic SFD is drawn by hand: this script rewrites the whole file
from the regular, so running it again changes nothing but ModificationTime, and
tests/test_make_italic.py fails while it is out of date. Change the regular or this script,
then rerun it and ./build.sh.

Every glyph of the regular falls in one of three sets, decided by classify():

- SLANTED: what a pen writes. Letters, figures, the combining marks, punctuation, brackets,
  quotes, currency, superscripts, operators, arrows and the ligatures. Each is sheared by
  x += (y - AXIS) * SLANT, one map for every glyph, pivoting on the hyphen's middle: a stroke
  at any height moves the same in every glyph, so the ligature pieces still meet at the cell
  seams, while - = and the arrow shafts stay where they are and the lowercase stays centred.
  Before the shear, evened() moves the sides of the diagonal strokes a little, so / and \
  come out closer in weight.
- UPRIGHT: what is drawn as a picture: Box Drawing, Block Elements, Braille, Powerline, the
  geometric shapes and the spinner frames and the status marks ✓ ✗ ⚠ ℹ, which Maple Mono and
  Intel One Mono leave untouched in their italics, and the checkboxes ☐ ☑ ☒ and the key hints
  ⌘ ⌥ ⌃ ⇧ ↹ ⇥ ⇤, which Maple Mono slants (docs/design-notes.md says why they stay). Copied
  unchanged, hints included.
- CURSIVE: letters given a cursive form, drawn from the regular's own strokes and then
  sheared. f runs its stem below the baseline, as deep as j, ending in a
  short flick to the left (proofed against ƒ's hook, which Maple Mono's f has, and against
  a plain straight descender).

A composite keeps its references, each matrix conjugated by the shear, so it equals the shear
of the regular's composite exactly: a turned ¿ stays ? turned, and an accent moves right by
its height's share of the slant. Two cannot: an upright glyph built on a slanted one (∙ on
the period) and a slanted glyph whose part is turned a quarter (⋮ on …) are unlinked into
outlines. Anchors move with the shear, so the mark lookups carry over as they are, and so do
the ligature lookups.
"""
import math
import sys

import fontforge
import psMat

import lig_geometry as geo
import project
from add_ligatures import GENERATED
from project import AXIS, ITALIC_SFD, SFD, run_generator, validation_errors

ANGLE = 12  # degrees: between Maple Mono's 10 and Intel One Mono's 16, next to Monaspace's 11
SLANT = math.tan(math.radians(ANGLE))
SHEAR = geo.about(psMat.skew(math.radians(ANGLE)), 0, AXIS)

# The scale of evened()'s moves: an edge goes at most 0.77 of it. 2.5 leaves / and \ 9% apart
# in weight, where the shear alone left 18% and the reference italics have 8–13%; from 3 on,
# the outlines of æ and the small 5 cross.
EVEN = 2.5

SLANTED, UPRIGHT, CURSIVE = "slanted", "upright", "cursive"

# The blocks that stay upright: Miscellaneous Technical (⏺ ⏵ ⏸ ⏹ ⎿ ⌘ ⌥ ⌃ ⌫ ⌦ ⎋ ⏎), Box Drawing
# through Dingbats (the block elements, geometric shapes, ☐ ☑ ☒ ⚠ and ✓ ✗ ✶), Braille,
# Miscellaneous Mathematical Symbols-B (⧉ ⦾ ⦿ ⧇ ⧆), the Powerline symbols and �.
UPRIGHT_BLOCKS = (range(0x2300, 0x2400), range(0x2500, 0x27C0), range(0x2800, 0x2900),
                  range(0x2980, 0x2A00), range(0xE000, 0xF900), range(0xFFF0, 0x10000))
# Inside those blocks, what a pen writes: the heavy > < → of prompts, ⎯ (the -- line's middle
# piece, which must join it) and ⍽, ␣'s sibling.
SLANTED_CHARS = frozenset("❮❯❰❱➜⎯⍽")
# Outside them, what is a picture: the spinner frames ∙ ⊙ ⊶ ⊷ (and ⊙ is built on ∙), • and
# ‣, which are the dot of ◉ and ▸'s triangle, ℹ, which stands beside ⚠, and the white arrows
# ⇧ ⇪ ⇦ ⇨ ⇩ ⇞ ⇟ and the tab keys ↹ ⇥ ⇤, key hints that read with ⌘ ⌥ ⌃ (Maple Mono slants
# them, and has no ⌘). ↵ ↩ are arrows and slant.
UPRIGHT_CHARS = frozenset("∙⊙⊶⊷•‣ℹ⇧⇪⇦⇨⇩⇞⇟↹⇥⇤")

# f's descender, in the stem's own stroke. From STEM_CUT up the regular's outline is the stem
# alone, above its round end. The end is cut away there and a stroke as wide as the cut is
# welded on along it, so no removeOverlap() decides the joint; the stroke runs down as far as
# j reaches and bends left by FLICK, a quarter ellipse FLATNESS as high as it is wide.
STEM_CUT = 80
FLICK = 70  # how far the end reaches left of the stem's middle; 90 and 100 read busier
FLATNESS = 0.9

IDENTITY, TURNED = (1, 0, 0, 1), (-1, 0, 0, -1)  # the linear parts that commute with a shear
FONTNAME, FULLNAME = "ComicCaret-Italic", "Comic Caret Italic"
ITALIC_BIT = 0x0001  # OS/2 fsSelection; the regular sets 0x0040, REGULAR
# PANOSE (Latin Text) records a slant of more than 5° in its letterform digit, whose oblique
# shapes 9-15 follow the normal ones 2-8 in the same order.
LETTERFORM, NORMAL_FORMS, TO_OBLIQUE = 7, range(2, 9), 7


def oblique_panose(panose):
    """The regular's PANOSE with its letterform made oblique: the italic is the regular
    sheared, and PANOSE measures an oblique font along its slant, so the other digits read the
    same."""
    if panose[LETTERFORM] not in NORMAL_FORMS:
        sys.exit(f"the regular's PANOSE letterform {panose[LETTERFORM]} has no oblique form")
    return (*panose[:LETTERFORM], panose[LETTERFORM] + TO_OBLIQUE, *panose[LETTERFORM + 1:])


def descending_f(font):
    """The regular's f with its stem run below the baseline, ending in a short flick to the
    left."""
    stem = geo.trim(font["f"].foreground, y0=STEM_CUT)
    # The cut's own ends: the stroke, trimmed at the same height, then ends in the same edge,
    # and the weld leaves no step.
    cut = sorted(p.x for contour in stem for p in contour
                 if p.on_curve and abs(p.y - STEM_CUT) < 0.5)
    if len(cut) != 2:
        sys.exit(f"f is not a single stem at y = {STEM_CUT}; measure its stem again")
    x0, x1 = cut
    middle, width = (x0 + x1) / 2, x1 - x0
    depth = -font["j"].boundingBox()[1]  # the descender row
    rx = FLICK - width / 2
    ry = rx * FLATNESS
    bend = -depth + width / 2 + ry  # where the stem starts to bend
    path = fontforge.contour()
    path.moveTo(middle, STEM_CUT + width)  # above the cut, which trims the round cap away
    path.lineTo(middle, bend)
    path.cubicTo((middle, bend - geo.KAPPA * ry), (middle - rx + geo.KAPPA * rx, bend - ry),
                 (middle - rx, bend - ry))
    stroke = geo.stroked(path, width)
    return geo.weld_y(geo.trim(stroke, y1=STEM_CUT), stem, STEM_CUT)


# The cursive letters: name -> the upright outline to shear, drawn from the regular.
CURSIVE_LETTERS = {"f": descending_f}


def encoded_style(code):
    char = chr(code)
    if char in SLANTED_CHARS:
        return SLANTED
    if char in UPRIGHT_CHARS or any(code in block for block in UPRIGHT_BLOCKS):
        return UPRIGHT
    return SLANTED


def unused_style(name):
    if not GENERATED.fullmatch(name):
        sys.exit(f"{name} is unencoded and no glyph uses it: class it upright or slanted in "
                 "make_italic.py")
    return SLANTED


def classify(font):
    """{glyph name: SLANTED, UPRIGHT or CURSIVE} for every glyph of the regular.

    An encoded glyph goes by its character; .notdef, a box, stays upright. An unencoded part
    follows the glyphs built from it, and a ligature piece, which only a substitution reaches,
    is an operator's and slants. Any other unencoded glyph nothing references stops the
    generator: only the generators' glyphs are known to slant, so it has to be classed.
    """
    known = {".notdef": UPRIGHT, **dict.fromkeys(CURSIVE_LETTERS, CURSIVE)}
    return project.classify(font, known, encoded_style, unused_style)


def conjugable(matrix):
    """Whether a reference with this matrix can stay one under the shear: only a translation
    or a 180° turn commutes with it; anything else needs the outline."""
    return tuple(matrix[:4]) in (IDENTITY, TURNED)


def conjugated(matrix):
    """The reference matrix that draws a slanted base where the regular's matrix drew its
    upright base, so the composite is the shear of the regular's. Only a translation or a
    180° turn keeps the shear's form; anything else needs the outline."""
    out = psMat.compose(psMat.compose(psMat.inverse(SHEAR), matrix), SHEAR)
    return (*(round(v, 4) for v in out[:4]), *(round(v) for v in out[4:]))


def _edge_move(a, b):
    """How far right evened() moves the edge from a to b, or None where the two points
    coincide: EVEN * -2 * n.x * n.y along its outward normal n, of which only the part along
    x is kept. Ink lies right of the way a contour runs."""
    length = math.dist(a, b)
    if not length:
        return None
    nx, ny = (a[1] - b[1]) / length, (b[0] - a[0]) / length
    return EVEN * -2 * nx * ny * nx


def evened(layer):
    """The regular's outline with the sides of each / stroke moved apart and those of each
    \\ moved together, to even the two after the shear, which thins a stroke that leans with
    it and thickens one that leans against it.

    Like the shear, it moves points along x only, so every row stays. The move is nothing for
    a level or upright edge, so bars, stems and the seams of the ligature pieces stay too,
    and largest for an edge 55° off level, about where / and the arms of v x A stand. A point
    moves by the mean of the edges on its two sides, and its handles follow it.
    """
    out = layer.dup()
    for contour in out:
        old = [(p.x, p.y) for p in contour]
        n = len(old)
        for i, point in enumerate(contour):
            if not point.on_curve:
                continue
            before = next((m for k in range(1, n)
                           if (m := _edge_move(old[(i - k) % n], old[i])) is not None), None)
            after = next((m for k in range(1, n)
                          if (m := _edge_move(old[i], old[(i + k) % n])) is not None), None)
            if before is None or after is None:
                continue
            for j in (i - 1, i, i + 1):
                if j == i or not contour[j % n].on_curve:
                    contour[j % n].x = old[j % n][0] + (before + after) / 2
    return out


def slant(glyph):
    """Shear the glyph in place: outline, references and anchors, then rehint it."""
    if any(not conjugable(matrix) for _, matrix, *_ in glyph.references):
        sys.exit(f"{glyph.glyphname} keeps a reference the shear cannot express; "
                 "build() unlinks those first")
    if len(glyph.foreground):
        layer = geo.transformed(evened(glyph.foreground), SHEAR)
        # Rounding can move an extremum off its point, so extrema are added between two
        # roundings; "all" because the default skips short segments validate() still checks.
        layer.round()
        layer.addExtrema("all")
        layer.round()
        glyph.foreground = layer
    if glyph.references:
        # FontForge writes references in reverse order.
        glyph.references = tuple((name, conjugated(matrix))
                                 for name, matrix, *_ in reversed(glyph.references))
    glyph.anchorPoints = tuple((name, kind, round(x + (y - AXIS) * SLANT), y, *rest)
                               for name, kind, x, y, *rest in glyph.anchorPoints)
    glyph.autoHint()


def build(font):
    """Turn the regular, opened as `font`, into the italic."""
    panose = oblique_panose(font.os2_panose)
    for name, draw in CURSIVE_LETTERS.items():
        font[name].references = ()
        font[name].foreground = draw(font)
    styles = classify(font)
    # Every unlink comes before any base is sheared: unlinkRef() bakes the base's outline as
    # the composite last saw it, not its current foreground, so an upright glyph on a slanted
    # part and a slanted glyph whose part is turned a quarter must take the regular's outline
    # now, not by luck later.
    for glyph in font.glyphs():
        parts = {styles[name] for name, *_ in glyph.references}
        if styles[glyph.glyphname] == UPRIGHT and parts - {UPRIGHT}:
            for name, *_ in glyph.references:
                glyph.unlinkRef(name)  # one reference per call
            glyph.autoHint()
        elif styles[glyph.glyphname] != UPRIGHT and UPRIGHT in parts:
            sys.exit(f"{glyph.glyphname} slants but is built on an upright glyph")
        elif (styles[glyph.glyphname] != UPRIGHT
              and any(not conjugable(matrix) for _, matrix, *_ in glyph.references)):
            for name, *_ in glyph.references:
                glyph.unlinkRef(name)  # one reference per call; slant() rehints it
    for glyph in font.glyphs():
        if styles[glyph.glyphname] != UPRIGHT:
            slant(glyph)
    font.italicangle = -ANGLE
    font.fontname, font.fullname = FONTNAME, FULLNAME
    font.os2_stylemap = ITALIC_BIT
    font.os2_panose = panose


def invalid(italic):
    """{glyph name: validate() flags} of the italic's glyphs whose flags differ from the
    regular's (∄'s parts overlap in both)."""
    regular = fontforge.open(str(SFD))
    return {g.glyphname: flags for g in italic.glyphs()
            if (flags := validation_errors(g)) != validation_errors(regular[g.glyphname])}


if __name__ == "__main__":
    run_generator(__file__, __doc__, build, invalid, target=ITALIC_SFD, source=SFD, rehint=True)
