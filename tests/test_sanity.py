"""Font-wide sanity checks on the SFD source.

Run: python3 -m unittest discover tests

These assert rules every glyph must follow (see CLAUDE.md), not the shape of any one glyph.
Font Bakery and OTS check the built fonts separately; see CLAUDE.md for those commands.
"""
import pathlib
import unittest

import fontforge

SFD = pathlib.Path(__file__).resolve().parent.parent / "src" / "ComicCaret-Regular.sfd"
ADVANCE = 550
LINE_BOTTOM = -350  # hhea and typo descender

# Known exceptions.
INK_OUTSIDE_CELL = {"dcaron"}          # the caron needs a narrower d
VALIDATE_FLAGS = {"uni2204": 0x4}      # ∄'s rotated E and slash overlap
BLANK = {"space", "uni00A0", "uni2800"}  # space, no-break space, blank Braille pattern

VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


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

    def test_encoded_glyphs_have_ink(self):
        empty = [g.glyphname for g in self.glyphs
                 if g.unicode >= 0 and g.glyphname not in BLANK
                 and not len(g.foreground) and not g.references]
        self.assertEqual(empty, [])

    def test_outlines_are_clean(self):
        # Covers non-integral points (0x80000), self-intersections, wrong direction, missing
        # extrema and the other validate() problems.
        flags = {g.glyphname: g.validate(True) & ~VALIDATED for g in self.glyphs}
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
