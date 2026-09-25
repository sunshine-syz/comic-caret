"""Font-wide sanity checks on the SFD source.

Run: python3 -m unittest discover tests

These assert rules every glyph must follow (see CLAUDE.md), not the shape of any one glyph:
what breaking would show as clipped, overlapping or broken text. test_consistency.py holds
the rules classes of glyphs share, and test_built.py the built fonts'; test_fontbakery.py
runs Font Bakery on the built fonts, and CLAUDE.md gives the OTS command.
"""
import pathlib
import sys
import unicodedata
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from project import ADVANCE, SFD, validation_errors

LINE_TOP, LINE_BOTTOM = 900, -350  # hhea and typo ascender and descender
# Box-drawing verticals run this far past the line box, so they still overlap the next line's
# by 10 units at a 1.5 em line height, which apps get by adding space evenly above and below.
BOX_REACH = (1500 - (LINE_TOP - LINE_BOTTOM)) // 2 + 10

# Known exceptions.
# How far a glyph may run into the next cell: ď's caron, kept by choice, as far as Intel One
# Mono's (93).
INK_OUTSIDE_CELL = {"dcaron": 100}
VALIDATE_FLAGS = {"uni2204": 0x4}      # ∄'s rotated E and slash overlap
BLANK = {"space", "uni00A0", "uni2800"}  # space, no-break space, blank Braille pattern


def is_box_drawing(glyph):
    # Box-drawing lines overlap their neighbours on purpose so they join. Block elements fill
    # the cell and the line box exactly, so the rules for every glyph hold for them.
    return 0x2500 <= glyph.unicode <= 0x257F


class SanityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
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

    def test_box_drawing_strokes_reach_the_next_cell(self):
        # Ink above or below ═, the widest horizontal, is a vertical, and each must end the same
        # distance past the line box; ink past the cell's sides is a horizontal, and must end
        # where ─ does. Dashed lines end short of the cell to keep their gaps even, and
        # diagonals end at the sides.
        left, _, right, _ = self.font[ord("─")].boundingBox()
        _, low, _, high = self.font[ord("═")].boundingBox()
        wrong = {}
        for glyph in self.visible:
            name = unicodedata.name(chr(glyph.unicode)) if glyph.unicode >= 0 else ""
            if not is_box_drawing(glyph) or " DASH " in name or " DIAGONAL " in name:
                continue
            x0, bottom, x1, top = glyph.boundingBox()
            if (bottom < low and bottom != LINE_BOTTOM - BOX_REACH
                    or top > high and top != LINE_TOP + BOX_REACH
                    or x0 < 0 and x0 != left or x1 > ADVANCE and x1 != right):
                wrong[glyph.glyphname] = (x0, bottom, x1, top)
        self.assertEqual(wrong, {})

    def test_every_glyph_is_one_cell_wide(self):
        self.assertEqual([g.glyphname for g in self.glyphs if g.width != ADVANCE], [])

    def test_ink_stays_in_the_cell(self):
        outside = {}
        for glyph in self.visible:
            x0, _, x1, _ = glyph.boundingBox()
            reach = max(-x0, x1 - ADVANCE)
            if not is_box_drawing(glyph) and reach > INK_OUTSIDE_CELL.get(glyph.glyphname, 0):
                outside[glyph.glyphname] = reach
        self.assertEqual(outside, {})

    def test_nothing_hangs_below_the_line(self):
        below = [g.glyphname for g in self.glyphs
                 if not is_box_drawing(g) and g.boundingBox()[1] < LINE_BOTTOM]
        self.assertEqual(below, [])

    def test_nothing_rises_above_the_line(self):
        # Terminals clip glyphs to the line box, so ink above it is cut off.
        above = [g.glyphname for g in self.glyphs
                 if not is_box_drawing(g) and g.boundingBox()[3] > LINE_TOP]
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
                         {n: hex(x) for n, x in VALIDATE_FLAGS.items()})

    def test_hints_are_current(self):
        # FontForge marks a glyph edited since it was last hinted with H in its Flags line.
        stale, name = [], None
        with open(SFD, encoding="utf-8") as sfd:
            for line in sfd:
                if line.startswith("StartChar: "):
                    name = line.split(None, 1)[1].strip()
                elif line.startswith("Flags: ") and "H" in line.split(None, 1)[1]:
                    stale.append(name)
        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
