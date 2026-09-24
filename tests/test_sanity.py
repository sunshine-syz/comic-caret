"""Font-wide sanity checks on the SFD source.

Run: python3 -m unittest discover tests

These assert rules every glyph must follow (see CLAUDE.md), not the shape of any one glyph.
Font Bakery and OTS check the built fonts separately; see CLAUDE.md for those commands.
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
INK_OUTSIDE_CELL = {"dcaron"}          # ď's caron, kept by choice
VALIDATE_FLAGS = {"uni2204": 0x4}      # ∄'s rotated E and slash overlap
BLANK = {"space", "uni00A0", "uni2800"}  # space, no-break space, blank Braille pattern
# Case pairs whose marks differ by design: ď ť take an apostrophe-like caron, and ģ a turned
# comma above where Ģ has one below.
OWN_ACCENTS = {"dcaron", "tcaron", "gcommaaccent"}


def is_box_drawing(glyph):
    # Box drawing and block elements overlap their neighbours on purpose so lines join.
    return 0x2500 <= glyph.unicode <= 0x259F


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
        self.assertEqual((font.hhea_ascent, font.hhea_descent, font.hhea_linegap),
                         (LINE_TOP, LINE_BOTTOM, 0))
        self.assertEqual((font.os2_typoascent, font.os2_typodescent, font.os2_typolinegap),
                         (LINE_TOP, LINE_BOTTOM, 0))

    def test_box_drawing_verticals_reach_the_next_line(self):
        # Ink above or below ─ is a vertical, and each must end the same distance past its edge.
        _, low, _, high = self.font["SF100000"].boundingBox()
        wrong = {}
        for glyph in self.visible:
            if not is_box_drawing(glyph):
                continue
            _, bottom, _, top = glyph.boundingBox()
            if (bottom < low and bottom != LINE_BOTTOM - BOX_REACH
                    or top > high and top != LINE_TOP + BOX_REACH):
                wrong[glyph.glyphname] = (bottom, top)
        self.assertEqual(wrong, {})

    def test_every_glyph_is_one_cell_wide(self):
        self.assertEqual([g.glyphname for g in self.glyphs if g.width != ADVANCE], [])

    def test_ink_stays_in_the_cell(self):
        outside = [g.glyphname for g in self.visible
                   if not is_box_drawing(g) and g.glyphname not in INK_OUTSIDE_CELL
                   and (g.boundingBox()[0] < 0 or g.boundingBox()[2] > ADVANCE)]
        self.assertEqual(outside, [])

    def test_nothing_hangs_below_the_line(self):
        below = [g.glyphname for g in self.glyphs
                 if not is_box_drawing(g) and g.boundingBox()[1] < LINE_BOTTOM]
        self.assertEqual(below, [])

    def test_nothing_rises_above_the_line(self):
        # Terminals clip glyphs to the line box, so ink above it is cut off.
        above = [g.glyphname for g in self.glyphs
                 if not is_box_drawing(g) and g.boundingBox()[3] > LINE_TOP]
        self.assertEqual(above, [])

    def test_capitals_share_accents_with_lowercase(self):
        # As in both reference fonts, a mark keeps one shape and size on either case.
        def marks(glyph):
            base = unicodedata.normalize("NFD", chr(glyph.unicode))[0]
            letters = {self.font[ord(base)].glyphname, "dotlessi", "dotlessj"}
            return sorted(r[0] for r in glyph.references if r[0] not in letters)

        differ = []
        for upper in self.glyphs:
            if upper.unicode < 0 or not upper.references or not chr(upper.unicode).isupper():
                continue
            lower = chr(upper.unicode).lower()
            if len(lower) != 1 or ord(lower) not in self.font:
                continue
            lower = self.font[ord(lower)]
            if lower.glyphname not in OWN_ACCENTS and marks(upper) != marks(lower):
                differ.append((upper.glyphname, marks(upper), marks(lower)))
        self.assertEqual(differ, [])

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
