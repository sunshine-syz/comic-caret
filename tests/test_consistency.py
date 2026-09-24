"""Rules whole classes of glyphs share: where they sit in the line and the cell, and how they
are built from other glyphs.

Run: python3 -m unittest discover tests

Each rule covers every glyph of its class, so a glyph added to one is checked without a new
test. Known exceptions are listed here with their reasons.
"""
import collections
import math
import pathlib
import statistics
import sys
import unicodedata
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

LETTER = {"Lu", "Ll", "Lt", "Lo"}  # not Lm: ˆ ˇ are modifier letters, and marks here

# The characters whose bottom (1) or top (3) edge lies on each row.
ROWS = {
    "baseline": ("ABCDEFGHIJKLMNOPRSTUVWXYZÆŒÐÞŁĦŦǷabcdefhiklmnorstuvwxzıĸß0123456789¼½¾", 1),
    "x-height": ("acemnorsuvwxzıĸµŋ", 3),
    "cap height": ("ABCDEFGHIJKLMNOPQRSTUVWXYZÆŒÐÞŁŊǷ0123456789¼½¾™", 3),
    "ascender": ("bdfhklßþ", 3),
    "descender": ("gjpqyþµŋŊƒ¶", 1),
    "superscript": ("¹²³", 3),
}
# How far a glyph may stray from its row's median: round letters overshoot by up to 25 (C, 9).
ROW_TOLERANCE = 30
OFF_ROW = {("cap height", "Þ")}  # its stem rises 88 past cap height

# Symmetric glyphs, and the brackets, which the legibility pass centered.
CENTERED = "AHIMNOSTUVWXYZosvwxz08!¡|:.'\"*+-=^~_×÷±−≠≈≡∞↔↕⇔✗#%…/\\()[]{}"
ON_AXIS = "+−=±×÷≠≈≡~<>≤≥←→↔⇐⇒⇔↦"  # centered on the hyphen, as the ligatures join them
MIRRORED = ("<>", "≤≥", "←→", "⇐⇒", "«»", "‹›", "/\\")
TOLERANCE = 10  # for centering and mirroring; the hand's wobble stays within it

# Case pairs whose marks differ by design: ď ť take an apostrophe-like caron, and ģ a turned
# comma above where Ģ has one below.
OWN_ACCENTS = {"dcaron", "tcaron", "gcommaaccent"}
MERGED_BELOW = 10  # a merged ogonek or cedilla lies below this height or inside its letter
MARK_CLEARANCE = 20  # the closest a mark may come to its letter
MARK_OFFCENTER = 30  # C's circumflex, over an open side, sits 22 right of the ink's middle
STEM_BASES = {"dotlessi", "dotlessj", "l"}  # their marks sit over the stem, not the ink's middle

BRAILLE = range(0x2800, 0x2900)
# Unicode numbers the dots down the left column (1-3), down the right (4-6), then along the
# bottom (7, 8); dot n is bit n - 1 of the pattern's offset from U+2800.
BRAILLE_DOTS = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))  # (column, row)


def open_font():
    return fontforge.open(str(SFD))


def box(font, char):
    return font[ord(char)].boundingBox()


def is_letter(font, name):
    code = font[name].unicode
    return code >= 0 and unicodedata.category(chr(code)) in LETTER


class PlacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = open_font()

    def test_letters_and_figures_sit_on_their_rows(self):
        off = {}
        for row, (chars, edge) in ROWS.items():
            edges = {char: box(self.font, char)[edge] for char in chars}
            line = statistics.median(edges.values())
            off.update({(row, char): round(y - line) for char, y in edges.items()
                        if abs(y - line) > ROW_TOLERANCE})
        self.assertEqual(set(off), OFF_ROW, off)

    def test_symmetric_glyphs_are_centered(self):
        off = {}
        for char in CENTERED:
            x0, _, x1, _ = box(self.font, char)
            if abs((x0 + x1) / 2 - ADVANCE / 2) > TOLERANCE:
                off[char] = round((x0 + x1) / 2 - ADVANCE / 2)
        self.assertEqual(off, {})

    def test_operators_sit_on_the_math_axis(self):
        _, y0, _, y1 = self.font["hyphen"].boundingBox()
        off = {}
        for char in ON_AXIS:
            _, b0, _, b1 = box(self.font, char)
            if abs((b0 + b1) / 2 - (y0 + y1) / 2) > TOLERANCE:
                off[char] = round((b0 + b1) / 2 - (y0 + y1) / 2)
        self.assertEqual(off, {})

    def test_mirror_pairs_mirror_each_other(self):
        for left, right in MIRRORED:
            with self.subTest(pair=left + right):
                x0, y0, x1, y1 = box(self.font, left)
                mirrored = (ADVANCE - x1, y0, ADVANCE - x0, y1)
                for got, want in zip(box(self.font, right), mirrored, strict=True):
                    self.assertAlmostEqual(got, want, delta=TOLERANCE)


class CompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = open_font()
        cls.accented = [g for g in cls.font.glyphs() if g.unicode >= 0
                        and unicodedata.category(chr(g.unicode)) in LETTER
                        and len(unicodedata.normalize("NFD", chr(g.unicode))) > 1]

    def base_of(self, glyph):
        """The letter an accented letter is built on: the first character of its canonical
        decomposition, dotless for i and j so a mark takes the dot's place."""
        base = unicodedata.normalize("NFD", chr(glyph.unicode))[0]
        return {"i": "dotlessi", "j": "dotlessj"}.get(base) or self.font[ord(base)].glyphname

    def parts(self, glyph):
        """(letter, [(name, mark)]): a composite letter's own letter and its other parts, as
        placed; the letter is its reference to a letter, or else its own outline."""
        placed = [(name, geo.transformed(measure.ink(self.font, name), matrix))
                  for name, matrix, *_ in glyph.references]
        letters = [ink for name, ink in placed if is_letter(self.font, name)]
        if len(glyph.foreground):
            letters.append(glyph.foreground)
        if len(letters) != 1:
            return None, []
        return letters[0], [(name, ink) for name, ink in placed if ink is not letters[0]]

    def test_accented_letters_are_built_on_their_letter(self):
        # A reference follows every redraw of its letter; a copy doesn't. Ogonek and cedilla
        # letters merge the mark into the letter's outline, which stays the letter's above it.
        wrong = {}
        for glyph in self.accented:
            base = self.base_of(glyph)
            if len(glyph.foreground):
                own = geo.trim(glyph.foreground, y0=MERGED_BELOW).boundingBox()
                letter = geo.trim(self.font[base].foreground, y0=MERGED_BELOW).boundingBox()
                if any(abs(a - b) > 2 for a, b in zip(own, letter, strict=True)):
                    wrong[glyph.glyphname] = f"not {base} above y {MERGED_BELOW}"
            elif base not in {name for name, *_ in glyph.references}:
                wrong[glyph.glyphname] = f"no reference to {base}"
        self.assertEqual(wrong, {})

    def test_capitals_share_accents_with_lowercase(self):
        # As in the reference fonts, a mark keeps one shape and size on either case.
        def marks(glyph):
            # A reference to a whole letter is the base: A in Á, and L in Ŀ, which NFD leaves
            # whole.
            return sorted(r[0] for r in glyph.references if not is_letter(self.font, r[0]))

        differ = []
        for upper in self.font.glyphs():
            if upper.unicode < 0 or not upper.references or not chr(upper.unicode).isupper():
                continue
            lower = chr(upper.unicode).lower()
            if len(lower) != 1 or ord(lower) not in self.font:
                continue
            lower = self.font[ord(lower)]
            if lower.glyphname not in OWN_ACCENTS and marks(upper) != marks(lower):
                differ.append((upper.glyphname, marks(upper), marks(lower)))
        self.assertEqual(differ, [])

    def test_marks_clear_their_letters(self):
        def box_gap(first, second):
            (a0, b0, a1, b1), (c0, d0, c1, d1) = first.boundingBox(), second.boundingBox()
            return math.hypot(max(c0 - a1, a0 - c1, 0), max(d0 - b1, b0 - d1, 0))

        close = {}
        for glyph in self.font.glyphs():
            if glyph.unicode < 0 or not is_letter(self.font, glyph.glyphname):
                continue
            letter, marks = self.parts(glyph)
            for name, mark in marks:
                # Outlines are never closer than their boxes; most marks clear by the boxes.
                if box_gap(letter, mark) >= MARK_CLEARANCE:
                    continue
                if (gap := measure.gap(letter, mark)) < MARK_CLEARANCE:
                    close[(glyph.glyphname, name)] = round(gap)
        self.assertEqual(close, {})

    def test_marks_above_are_centered_on_their_letter(self):
        off = {}
        for glyph in self.accented:
            if self.base_of(glyph) in STEM_BASES:
                continue
            letter, marks = self.parts(glyph)
            if letter is None:
                continue
            x0, _, x1, top = letter.boundingBox()
            for name, mark in marks:
                m0, bottom, m1, _ = mark.boundingBox()
                offset = (m0 + m1) / 2 - (x0 + x1) / 2
                if bottom >= top and abs(offset) > MARK_OFFCENTER:
                    off[(glyph.glyphname, name)] = round(offset)
        self.assertEqual(off, {})

    def test_no_glyph_copies_another(self):
        # Outlines that match once moved: one should be a reference to the other.
        def shape(layer):
            x0, y0, _, _ = layer.boundingBox()
            return tuple(sorted(tuple((p.x - x0, p.y - y0, p.on_curve) for p in contour)
                                for contour in layer))

        shapes = collections.defaultdict(list)
        for glyph in self.font.glyphs():
            if len(glyph.foreground):
                shapes[shape(glyph.foreground)].append(glyph.glyphname)
        self.assertEqual([names for names in shapes.values() if len(names) > 1], [])

    def test_braille_patterns_show_their_dots(self):
        centers = self.dot_centers(0x28FF)  # all eight dots
        xs = sorted(x for x, _ in centers)
        middle = (xs[3] + xs[4]) / 2
        rows = sorted((y for _, y in centers), reverse=True)[::2]  # top to bottom

        def dot(x, y):
            row = min(range(len(rows)), key=lambda r: abs(y - rows[r]))
            return BRAILLE_DOTS.index((int(x > middle), row)) + 1

        wrong = {}
        for code in BRAILLE:
            shown = sorted(dot(x, y) for x, y in self.dot_centers(code))
            wanted = [n + 1 for n in range(8) if (code - BRAILLE.start) >> n & 1]
            if shown != wanted:
                wrong[f"U+{code:04X}"] = shown
        self.assertEqual(wrong, {})

    def dot_centers(self, code):
        """The middle of each dot of a Braille pattern."""
        return [((x0 + x1) / 2, (y0 + y1) / 2)
                for x0, y0, x1, y1 in (c.boundingBox() for c in measure.ink(self.font, code))]


if __name__ == "__main__":
    unittest.main()
