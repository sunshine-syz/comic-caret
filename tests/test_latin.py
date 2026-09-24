"""Western and Central European Latin: the characters that complete the Windows code pages.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import measure
from project import SFD

# Characters still to come; the set shrinks as each group lands.
NOT_YET = set("ĸµŋŊƒ‰Ĳĳßð§¶¹²³½¾ª©®º™")
BAR = (79, 4)  # the hyphen's stroke across its straight part, 76-81
SMALL = ("one", "two", "three", "four", "a", "o", "T", "M", "C", "R")
SMALL_STEM = (74, 4)  # 82 % of a regular stem, as the references' superscripts are 73-83 %
# ™ is lighter, as in every reference (43-58): an M at 74 has no room left for its counters.
TRADEMARK_STEM = (56, 4)


def code_page(codec):
    """The printable characters of a Windows code page, and the soft hyphen."""
    chars = set()
    for byte in range(0x20, 0x100):
        try:
            char = bytes([byte]).decode(codec)
        except UnicodeDecodeError:
            continue
        if char.isprintable() or char == "­":
            chars.add(char)
    return chars


def layer_of(font, name):
    """The glyph's ink as one layer, references included."""
    layer = font[name].foreground.dup()
    for ref, matrix, *_ in font[name].references:
        part = layer_of(font, ref)
        part.transform(matrix)
        layer += part
    return layer


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def missing(self, chars):
        return {c for c in chars if ord(c) not in self.font}

    def test_code_pages_are_complete(self):
        for codec in ("cp1252", "cp1250", "cp1257", "cp1254"):
            with self.subTest(codec=codec):
                self.assertEqual(self.missing(code_page(codec)), code_page(codec) & NOT_YET)

    def test_latin_blocks_are_complete(self):
        # Latin-1 Supplement and Latin Extended-A, but ŉ, which Unicode deprecates.
        blocks = {chr(c) for c in range(0xA0, 0x180) if c != 0x149}
        self.assertEqual(self.missing(blocks), blocks & NOT_YET)


class BarTest(unittest.TestCase):
    """Every bar is the hyphen's stroke."""
    # glyph: (x where the line crosses only the bar and the letter's own strokes, bar center)
    BARS = {"Eth": (200, 334), "dcroat": (340, 567), "hbar": (250, 567),
            "Hbar": (275, 515), "Tbar": (150, 334), "tbar": (300, 250)}

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_bars(self):
        for name, (x, center) in self.BARS.items():
            with self.subTest(glyph=name):
                spans = measure.spans_at_x(layer_of(self.font, name), x)
                [(y0, y1)] = [s for s in spans if s[0] <= center <= s[1]]
                self.assertAlmostEqual(y1 - y0, BAR[0], delta=BAR[1])
                self.assertAlmostEqual((y0 + y1) / 2, center, delta=10)

    def test_H_bar_clears_the_crossbar(self):
        # A gap of at least a stem keeps Ħ from reading as a filled block.
        spans = measure.spans_at_x(layer_of(self.font, "Hbar"), 275)
        self.assertEqual(len(spans), 2)
        self.assertGreaterEqual(spans[1][0] - spans[0][1], 80)


class SlashTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_slash_runs_past_the_letter(self):
        # Past O, Ø reads apart from our slashed zero, whose slash stays inside it.
        for slashed, letter in (("Oslash", "O"), ("oslash", "o")):
            with self.subTest(glyph=slashed):
                _, bottom, _, top = self.font[slashed].boundingBox()
                _, letter_bottom, _, letter_top = self.font[letter].boundingBox()
                self.assertGreaterEqual(top - letter_top, 40)
                self.assertGreaterEqual(letter_bottom - bottom, 40)

    def test_zero_slash_stays_inside(self):
        ring = max(self.font["zero"].foreground, key=lambda c: c.boundingBox()[3])
        self.assertEqual(ring.boundingBox(), self.font["zero"].boundingBox())


class CompositeTest(unittest.TestCase):
    """Glyphs that are another glyph, or a letter and a mark, as references."""
    REFERENCES = {"uni00AD": {"hyphen"}, "periodcentered": {"period"},
                  "Dcroat": {"Eth"}, "Ldot": {"L", "periodcentered"},
                  "ldot": {"l", "periodcentered"}, "Lcaron": {"L", "caron.alt"},
                  "lcaron": {"l", "caron.alt"}}

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_references(self):
        for name, refs in self.REFERENCES.items():
            with self.subTest(glyph=name):
                self.assertEqual({r for r, *_ in self.font[name].references}, refs)
                self.assertEqual(len(self.font[name].foreground), 0)

    def test_soft_hyphen_is_the_hyphen(self):
        [(_, matrix, *_)] = self.font["uni00AD"].references
        self.assertEqual(matrix, psMat.identity())

    def test_middle_dot_height(self):
        # Centered at 0.65 of the x-height, as the references put it (0.62-0.72).
        _, bottom, _, top = self.font["periodcentered"].boundingBox()
        self.assertAlmostEqual((bottom + top) / 2, 307, delta=5)

    def test_dots_follow_the_stem(self):
        for name, center in (("Ldot", 334), ("ldot", 307)):
            with self.subTest(glyph=name):
                [dot] = [m for r, m, *_ in self.font[name].references if r == "periodcentered"]
                _, bottom, _, top = self.font["periodcentered"].boundingBox()
                self.assertAlmostEqual((bottom + top) / 2 + dot[5], center, delta=5)


class SmallFigureTest(unittest.TestCase):
    """The small figures and letters that superscripts, fractions, ª º ™ © ® are built from:
    the regular glyph scaled down, its strokes thickened back towards a regular stem."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    # base: (height as a fraction of the glyph's, and which of the strokes a line there crosses
    # is upright): the stem, a bowl's side or the round side of 2 and 3.
    STEMS = {"one": (0.5, 0), "two": (0.75, -1), "three": (0.75, -1), "four": (0.12, 0),
             "a": (0.5, 0), "o": (0.5, 0), "T": (0.4, 0), "M": (0.25, 0), "C": (0.5, 0),
             "R": (0.25, 0)}

    def test_stems(self):
        for base, (height, index) in self.STEMS.items():
            with self.subTest(glyph=f"{base}.small"):
                layer = self.font[f"{base}.small"].foreground
                _, y0, _, y1 = layer.boundingBox()
                a, b = measure.spans_at_y(layer, y0 + height * (y1 - y0))[index]
                weight, delta = TRADEMARK_STEM if base in "TM" else SMALL_STEM
                self.assertAlmostEqual(b - a, weight, delta=delta)

    def test_trademark_M_keeps_its_counters(self):
        # Its V stops short, as the references' do, leaving the bottom open; three quarters up,
        # their Ms keep 53-73 units of white.
        layer = self.font["M.small"].foreground
        _, y0, _, y1 = layer.boundingBox()
        self.assertEqual(len(measure.spans_at_y(layer, y0 + 0.25 * (y1 - y0))), 2)
        self.assertGreaterEqual(measure.counter(layer, y0 + 0.75 * (y1 - y0)), 53)

    def test_figures_are_as_big_as_the_references(self):
        # Their superscript and fraction figures are 311-401 tall and 185-267 wide; two of ours
        # side by side must leave room for a fraction's bar.
        for base in ("one", "two", "three", "four"):
            with self.subTest(glyph=f"{base}.small"):
                x0, y0, x1, y1 = self.font[f"{base}.small"].boundingBox()
                self.assertGreaterEqual(y1 - y0, 311)
                self.assertLessEqual(y1 - y0, 401)
                self.assertLessEqual(x1 - x0, 230)

    def test_one_scale_for_all(self):
        # Letters and figures shrink alike, so ™ © ª º match the figures.
        def ratio(base):
            _, y0, _, y1 = self.font[f"{base}.small"].boundingBox()
            _, b0, _, b1 = self.font[base].boundingBox()
            return (y1 - y0) / (b1 - b0)

        for base in SMALL:
            with self.subTest(glyph=f"{base}.small"):
                self.assertAlmostEqual(ratio(base), ratio("one"), delta=0.03)

    def test_trademark_letters_match(self):
        _, t0, _, t1 = self.font["T.small"].boundingBox()
        _, m0, _, m1 = self.font["M.small"].boundingBox()
        self.assertAlmostEqual(t1 - t0, m1 - m0, delta=4)


if __name__ == "__main__":
    unittest.main()
