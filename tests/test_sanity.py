"""Font-wide sanity checks on the SFD source.

Run: python3 -m unittest discover tests

These assert rules every glyph must follow (see CLAUDE.md), not the shape of any one glyph:
what breaking would show as clipped, overlapping or broken text. test_consistency.py holds
the rules classes of glyphs share, and test_built.py the built fonts', which it runs through
ots; test_fontbakery.py runs Font Bakery on them.
"""
import pathlib
import sys
import unicodedata
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import make_italic
from measure import ink
from project import (
    ADVANCE,
    BOLD_SFD,
    CELL_REACH,
    ITALIC_SFD,
    LINE_BOTTOM,
    LINE_TOP,
    OVERLAP,
    SFD,
    WOBBLE,
    ZERO_WIDTH,
    takes_no_cell,
    validation_errors,
)

# Box-drawing verticals run this far past the line box, so they still overlap the next line's
# by 10 units at a 1.5 em line height, which apps get by adding space evenly above and below.
BOX_REACH = (1500 - (LINE_TOP - LINE_BOTTOM)) // 2 + OVERLAP
# Box-drawing horizontals run at least this far into the next cell: Intel One Mono's and Maple
# Mono's run 20. At 10, a grid that rounds the cell up to whole pixels showed a light notch at
# every seam of ─ ━ ═ at 11, 16 and 21 px.
BOX_SIDE_REACH = 20

# Known exceptions.
# How far a glyph may run into the next cell: ď's caron, no further than the furthest
# reference's, Intel One Mono's, give or take the hand's wobble; ⎯, the -- line's middle
# piece, as far as the line's pieces overlap so a row of them joins (OVERLAP in
# tools/project.py); and the tonos left of a capital, which stands in the cell before, as in
# Fira Code and Maple Mono: a word starts there, so that cell holds a space.
# Intel One Mono's ď runs 104 past its 614 cell, 93 of ours (Fira Code's 12, Maple Mono's 9).
DCARON_OVERHANG = round(104 * ADVANCE / 614) + WOBBLE
# The furthest either reference's goes: Fira Code's Ύ, 245 of its 1200 cell, at our advance
# (Maple Mono's 116).
TONOS_OVERHANG = round(245 * ADVANCE / 1200)
TONOS_CAPITALS = ("Epsilontonos", "Etatonos", "Iotatonos", "Omicrontonos", "Upsilontonos",
                  "Omegatonos")
# The solid Powerline separators run CELL_REACH into the cell of the segment they end.
INK_OUTSIDE_CELL = {"dcaron": DCARON_OVERHANG, "uni23AF": OVERLAP,
                    **dict.fromkeys(TONOS_CAPITALS, TONOS_OVERHANG),
                    **dict.fromkeys(("uniE0B0", "uniE0B2"), CELL_REACH)}
# The bold's tonos moves left, clear of the heavier capital, as far as the furthest reference
# bold's goes: Fira Code Bold's Ύ, 425 of its 1200 cell, at our advance (Maple Mono Bold's 153).
BOLD_TONOS_OVERHANG = round(425 * ADVANCE / 1200)
BOLD_INK_OUTSIDE_CELL = {**INK_OUTSIDE_CELL, **dict.fromkeys(TONOS_CAPITALS, BOLD_TONOS_OVERHANG)}
# ∄'s rotated E and slash overlap, and so do the references to ☐ and a quarter of ■ in ◰ ◱ ◲ ◳.
VALIDATE_FLAGS = {"uni2204": 0x4, "uni25F0": 0x4, "uni25F1": 0x4, "uni25F2": 0x4, "uni25F3": 0x4}
# The bold draws ∄ as one outline (make_bold.MERGED).
BOLD_VALIDATE_FLAGS = {name: flags for name, flags in VALIDATE_FLAGS.items() if name != "uni2204"}
# The spaces, the blank Braille pattern and the zero-width format characters.
# The soft hyphen is blank because a terminal that gives it no cell (Alacritty) draws its glyph
# over the letter before it.
BLANK = {"space", "uni00A0", "uni00AD", "uni2009", "uni202F", "uni2800",
         *(f"uni{code:04X}" for code in ZERO_WIDTH)}


def is_box_drawing(glyph):
    return 0x2500 <= glyph.unicode <= 0x257F


def joins_its_neighbours(glyph):
    # Box-drawing lines and block elements overlap their neighbours on purpose so they join.
    # Their own rules: test_box_drawing_strokes_reach_the_next_cell, and for the blocks
    # test_consistency.BlockElementTest. The shades ░ ▒ ▓ stay within the cell, so their
    # pattern tiles.
    return 0x2500 <= glyph.unicode <= 0x259F and glyph.unicode not in range(0x2591, 0x2594)


class SanityTest(unittest.TestCase):
    sfd = SFD

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))
        cls.glyphs = list(cls.font.glyphs())
        # Composites are positioned by the glyphs that use them, so only what a code point
        # (or a missing one, via .notdef) can show is held to the cell.
        cls.visible = [g for g in cls.glyphs if g.unicode >= 0 or g.glyphname == ".notdef"]

    def test_one_line_box_everywhere(self):
        font = self.font
        self.assertEqual(font.em, 1000)
        # Without USE_TYPO_METRICS, Windows spaces lines by the win ascent and descent instead.
        self.assertTrue(font.os2_use_typo_metrics)
        self.assertEqual((font.hhea_ascent, font.hhea_descent, font.hhea_linegap),
                         (LINE_TOP, LINE_BOTTOM, 0))
        self.assertEqual((font.os2_typoascent, font.os2_typodescent, font.os2_typolinegap),
                         (LINE_TOP, LINE_BOTTOM, 0))
        # GDI apps (PuTTY, gvim, legacy conhost, Office) space lines by the win ascent and
        # descent, and clip each glyph to them; the references set them to the line box too.
        # Set as offsets from the ink, they took the box drawing's overlap: a 1.53 em line.
        self.assertEqual((font.os2_winascent, font.os2_winascent_add,
                          font.os2_windescent, font.os2_windescent_add),
                         (LINE_TOP, False, -LINE_BOTTOM, False))

    def test_box_drawing_strokes_reach_the_next_cell(self):
        # Ink above or below ═, the widest horizontal, is a vertical, and each must end the same
        # distance past the line box; ink past the cell's sides is a horizontal, and must end
        # where ─ does. Dashes keep a rhythm of their own (test_consistency), and diagonals
        # end at the sides.
        left, _, right, _ = self.font[ord("─")].boundingBox()
        _, low, _, high = self.font[ord("═")].boundingBox()
        wrong = {}
        for glyph in self.visible:
            # Private-use code points, such as the Powerline symbols, have no name.
            name = unicodedata.name(chr(glyph.unicode), "") if glyph.unicode >= 0 else ""
            if not is_box_drawing(glyph) or " DASH " in name or " DIAGONAL " in name:
                continue
            x0, bottom, x1, top = glyph.boundingBox()
            if (bottom < low and bottom != LINE_BOTTOM - BOX_REACH
                    or top > high and top != LINE_TOP + BOX_REACH
                    or x0 < 0 and x0 != left or x1 > ADVANCE and x1 != right):
                wrong[glyph.glyphname] = (x0, bottom, x1, top)
        self.assertEqual(wrong, {})

    def test_box_drawing_horizontals_overlap_the_next_cell(self):
        # Every horizontal ends where ─ does (test_box_drawing_strokes_reach_the_next_cell).
        x0, _, x1, _ = self.font[ord("─")].boundingBox()
        self.assertGreaterEqual(min(-x0, x1 - ADVANCE), BOX_SIDE_REACH)

    def test_every_glyph_is_one_cell_wide(self):
        wrong = [g.glyphname for g in self.glyphs
                 if g.width != (0 if takes_no_cell(g.unicode) else ADVANCE)]
        self.assertEqual(wrong, [])

    rounding = 0  # how far ink may miss its allowance through rounding
    outside_cell, validate_flags = INK_OUTSIDE_CELL, VALIDATE_FLAGS

    def box(self, glyph):
        return glyph.boundingBox()

    def test_ink_stays_in_the_cell(self):
        outside = {}
        for glyph in self.visible:
            x0, _, x1, _ = self.box(glyph)
            reach = max(-x0, x1 - ADVANCE) - self.rounding
            allowed = self.outside_cell.get(glyph.glyphname, 0)
            if not joins_its_neighbours(glyph) and reach > allowed:
                outside[glyph.glyphname] = reach
        self.assertEqual(outside, {})

    def test_nothing_hangs_below_the_line(self):
        below = [g.glyphname for g in self.glyphs
                 if not joins_its_neighbours(g) and g.boundingBox()[1] < LINE_BOTTOM]
        self.assertEqual(below, [])

    def test_nothing_rises_above_the_line(self):
        # Many terminals clip glyphs to the line box, so ink above it is cut off.
        above = [g.glyphname for g in self.glyphs
                 if not joins_its_neighbours(g) and g.boundingBox()[3] > LINE_TOP]
        self.assertEqual(above, [])

    def test_unencoded_glyphs_are_used(self):
        # A glyph with no code point ships only as another glyph's part or a substitution's
        # result; one that is neither is dead weight and a Font Bakery WARN.
        used = {".notdef"}
        for glyph in self.glyphs:
            used.update(name for name, *_ in glyph.references)
            for _, kind, *parts in glyph.getPosSub("*"):
                if kind in ("Substitution", "AltSubs", "MultSubs"):
                    used.update(parts)
                elif kind == "Ligature":
                    used.add(glyph.glyphname)
        unused = [g.glyphname for g in self.glyphs if g.unicode < 0 and g.glyphname not in used]
        self.assertEqual(unused, [])

    def test_encoded_glyphs_have_ink(self):
        empty = [g.glyphname for g in self.glyphs
                 if g.unicode >= 0 and g.glyphname not in BLANK
                 and not len(g.foreground) and not g.references]
        self.assertEqual(empty, [])

    def test_outlines_are_clean(self):
        # Covers non-integral points (0x80000), self-intersections, wrong direction, missing
        # extrema and the other validate() problems.
        flags = {g.glyphname: validation_errors(g) for g in self.glyphs}
        self.assertEqual({n: hex(x) for n, x in flags.items() if x},
                         {n: hex(x) for n, x in self.validate_flags.items()})

    def test_reference_offsets_are_whole_units(self):
        # validate() holds the points to whole units; a reference's offset places every point
        # of the glyph it shows, so it is a whole unit too (project.ROUNDING).
        off = {(g.glyphname, name): tuple(m[4:]) for g in self.glyphs
               for name, m, *_ in g.references if any(v != round(v) for v in m[4:])}
        self.assertEqual(off, {})

    def test_hints_are_current(self):
        # FontForge marks a glyph edited since it was last hinted with H in its Flags line.
        stale, name = [], None
        with open(self.sfd, encoding="utf-8") as sfd:
            for line in sfd:
                if line.startswith("StartChar: "):
                    name = line.split(None, 1)[1].strip()
                elif line.startswith("Flags: ") and "H" in line.split(None, 1)[1]:
                    stale.append(name)
        self.assertEqual(stale, [])


class ItalicSanityTest(SanityTest):
    """The same rules for the italic, whose cell is the regular's sheared: a slanted glyph's
    ink is held to the cell the shear took it from, so a descender may reach left of the
    cell and an ascender right of it by the slant's share of its height."""

    sfd = ITALIC_SFD
    rounding = 1  # a sheared outline's points are rounded to units, so un-sheared it misses

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.styles = make_italic.classify(cls.font)

    def box(self, glyph):
        if self.styles[glyph.glyphname] == make_italic.UPRIGHT:
            return glyph.boundingBox()
        unsheared = geo.transformed(ink(self.font, glyph.glyphname),
                                    psMat.inverse(make_italic.SHEAR))
        return unsheared.boundingBox()


class BoldSanityTest(SanityTest):
    """The same rules for the bold, whose strokes grow within the regular's cell and line box."""

    sfd = BOLD_SFD
    outside_cell, validate_flags = BOLD_INK_OUTSIDE_CELL, BOLD_VALIDATE_FLAGS


if __name__ == "__main__":
    unittest.main()
