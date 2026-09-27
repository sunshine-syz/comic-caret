"""Greek: Google Fonts' Greek Core, the letters built from Latin ones, and the tonos.

Run: python3 -m unittest discover tests

Rows and centering are checked for every letter in test_consistency.py, and accented letters
built on their letter with marks clear of it there too.
"""
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import SFD

# Google Fonts' Greek Core (the glyphsets package), less what Latin Core already covers:
# the numeral signs, question mark, tonos, dialytika tonos and ano teleia, the alphabet with its
# tonos and dialytika letters, and the kai symbols.
GREEK_CORE = [0x374, 0x375, 0x37E, *range(0x384, 0x38B), 0x38C, *range(0x38E, 0x3A2),
              *range(0x3A3, 0x3D0), 0x3D7]
# Where every reference draws two characters alike, one is a reference to the other, so it
# follows every redrawing: the capitals that match Latin, ο and μ, and the characters Unicode
# makes the same (ohm and omega, the question mark and ;, ano teleia and ·, the numeral sign
# and the modifier letter prime).
SAME = {"Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
        "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "ο": "o", "\u03bc": "\u00b5",
        "\u2126": "\u03a9", "\u037e": ";", "\u0387": "\u00b7", "\u0374": "\u02b9"}
CAPITAL_TONOS = "ΆΈΉΊΌΎΏ"
LOWER_TONOS = "άέήίόύώ"
# The white between Θ's bar and its ring, at least the narrowest reference's: Maple Mono's
# 52 (Fira Code's 54) at our cap height and advance.
THETA_GAP = 52


class GreekTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def glyph(self, char):
        return self.font[ord(char)]

    def test_greek_core_is_complete(self):
        self.assertEqual([f"U+{c:04X}" for c in GREEK_CORE if c not in self.font], [])

    def test_same_letters_are_references(self):
        for char, base in SAME.items():
            with self.subTest(glyph=char):
                glyph = self.glyph(char)
                self.assertEqual(len(glyph.foreground), 0)
                [(name, matrix, *_)] = glyph.references
                self.assertEqual(name, self.glyph(base).glyphname)
                self.assertEqual(tuple(matrix[:4]), (1, 0, 0, 1))

    def test_tonos_is_the_acute_turned_steeper(self):
        # The same stroke, only turned, so it needs less room beside a capital.
        tonos, acute = self.glyph("΄").foreground, self.font["acute"].foreground
        self.assertAlmostEqual(measure.area(tonos) / measure.area(acute), 1, delta=0.02)
        t0, u0, t1, u1 = tonos.boundingBox()
        a0, b0, a1, b1 = acute.boundingBox()
        self.assertGreater((u1 - u0) / (t1 - t0), (b1 - b0) / (a1 - a0))

    def tonos_boxes(self, chars):
        """{char: the ink box of the tonos each letter places}."""
        boxes = {}
        for char in chars:
            [matrix] = [m for name, m, *_ in self.glyph(char).references if name == "tonos"]
            ink = self.glyph("΄").foreground.dup()
            ink.transform(matrix)
            boxes[char] = ink.boundingBox()
        return boxes

    def test_tonos_stands_at_one_height(self):
        # On every capital, left of the letter, and on every lowercase letter, above it.
        for chars in (CAPITAL_TONOS, LOWER_TONOS):
            with self.subTest(letters=chars):
                bottoms = {round(box[1]) for box in self.tonos_boxes(chars).values()}
                self.assertEqual(len(bottoms), 1)

    def test_capital_tonos_stands_left_of_the_letter(self):
        # Beside the capital, not over it: left of the letter's ink at the tonos's height,
        # reaching the letter's top.
        for char, (x0, y0, x1, y1) in self.tonos_boxes(CAPITAL_TONOS).items():
            with self.subTest(glyph=char):
                [base] = [name for name, *_ in self.glyph(char).references if name != "tonos"]
                letter = measure.ink(self.font, base)
                beside = geo.trim(letter, y0=y0, y1=y1).boundingBox()[0]
                self.assertLess((x0 + x1) / 2, beside)
                self.assertGreaterEqual(y1, letter.boundingBox()[3])

    def test_theta_bar_stays_clear_of_the_ring(self):
        # Θ is O and a bar; at 12 px a bar that nearly meets the ring reads as ⊖.
        theta = self.glyph("Θ")
        ring = self.font["O"].foreground
        self.assertEqual([name for name, *_ in theta.references], ["O"])
        self.assertGreaterEqual(measure.gap(ring, theta.foreground), THETA_GAP)


if __name__ == "__main__":
    unittest.main()
