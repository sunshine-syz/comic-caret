"""Western and Central European Latin: the characters that complete the Windows code pages.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

# Characters still to come; the set shrinks as each group lands.
NOT_YET = set()
BAR = (79, 4)  # the hyphen's stroke across its straight part, 76-81
SMALL = ("one", "two", "three", "four", "a", "o", "T", "M", "C", "R")
SMALL_STEM = (74, 4)  # 82 % of a regular stem, as the references' superscripts are 73-83 %
# ™ © ® are lighter, as in every reference (43-66): an M at 74 has no room left for its
# counters, and a ring at our full weight crowds the letter inside it.
SIGN_STEM = (56, 4)


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
             "R": (0.75, 0)}

    def test_stems(self):
        for base, (height, index) in self.STEMS.items():
            with self.subTest(glyph=f"{base}.small"):
                layer = self.font[f"{base}.small"].foreground
                _, y0, _, y1 = layer.boundingBox()
                a, b = measure.spans_at_y(layer, y0 + height * (y1 - y0))[index]
                weight, delta = SIGN_STEM if base in "TMCR" else SMALL_STEM
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
        # Letters and figures shrink alike, so ª º match the figures, and ™ © ® one another.
        def ratio(base):
            _, y0, _, y1 = self.font[f"{base}.small"].boundingBox()
            _, b0, _, b1 = self.font[base].boundingBox()
            return (y1 - y0) / (b1 - b0)

        for group in (("one", "two", "three", "four", "a", "o"), ("T", "C", "R")):
            for base in group:
                with self.subTest(glyph=f"{base}.small"):
                    self.assertAlmostEqual(ratio(base), ratio(group[0]), delta=0.03)

    def test_trademark_letters_match(self):
        _, t0, _, t1 = self.font["T.small"].boundingBox()
        _, m0, _, m1 = self.font["M.small"].boundingBox()
        self.assertAlmostEqual(t1 - t0, m1 - m0, delta=4)


class FigureTest(unittest.TestCase):
    """Superscripts, fractions, ordinals and the signs built from the small components."""
    FRACTIONS = {"onequarter": ("one.small", "four.small"),
                 "onehalf": ("one.small", "two.small"),
                 "threequarters": ("three.small", "four.small")}

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def part(self, glyph, component):
        """The component's ink where the glyph places it."""
        [matrix] = [m for r, m, *_ in self.font[glyph].references if r == component]
        layer = layer_of(self.font, component)
        layer.transform(matrix)
        return layer

    def test_superscripts_top_out_together_centered(self):
        for name in ("uni00B9", "uni00B2", "uni00B3"):
            with self.subTest(glyph=name):
                x0, _, x1, top = self.font[name].boundingBox()
                self.assertAlmostEqual(top, 724, delta=5)
                self.assertAlmostEqual((x0 + x1) / 2, ADVANCE / 2, delta=5)

    def test_fractions_run_from_the_baseline_to_cap_height(self):
        for name, (numerator, denominator) in self.FRACTIONS.items():
            with self.subTest(glyph=name):
                self.assertAlmostEqual(self.part(name, numerator).boundingBox()[3], 668, delta=5)
                self.assertAlmostEqual(self.part(name, denominator).boundingBox()[1], 0, delta=5)

    def test_fraction_bar_touches_neither_figure(self):
        for name, figures in self.FRACTIONS.items():
            bar = self.part(name, "slash.fraction")
            for figure in figures:
                with self.subTest(glyph=name, figure=figure):
                    self.assertGreaterEqual(measure.gap(bar, self.part(name, figure)), 20)

    def test_ordinals_stand_over_a_bar(self):
        # As in Fira Code and Intel One Mono: the bar as wide as the letter, clear below it.
        for name, letter in (("ordfeminine", "a.small"), ("ordmasculine", "o.small")):
            with self.subTest(glyph=name):
                x0, y0, x1, y1 = self.part(name, letter).boundingBox()
                b0, _, b1, bar_top = self.part(name, "bar.ordinal").boundingBox()
                self.assertAlmostEqual(y1, 690, delta=5)
                self.assertAlmostEqual(b1 - b0, x1 - x0, delta=10)
                self.assertGreaterEqual(y0 - bar_top, 40)

    def test_trademark_tops_at_cap_height(self):
        self.assertAlmostEqual(self.font["trademark"].boundingBox()[3], 668, delta=5)
        self.assertGreaterEqual(measure.gap(self.part("trademark", "T.small"),
                                            self.part("trademark", "M.small")), 15)

    def test_circled_letters_share_one_ring(self):
        self.assertEqual(self.part("copyright", "circle.copyright").boundingBox(),
                         self.part("registered", "circle.copyright").boundingBox())
        x0, _, x1, _ = self.part("copyright", "circle.copyright").boundingBox()
        self.assertAlmostEqual(x1 - x0, 490, delta=16)  # the references' 474-496

    def test_circled_letters_sit_in_the_middle_with_room(self):
        # At least the 48 units the references leave around their © at the closest point;
        # around ® they leave 16-48.
        for name, letter in (("copyright", "C.small"), ("registered", "R.small")):
            with self.subTest(glyph=name):
                ring = self.part(name, "circle.copyright")
                inside = self.part(name, letter)
                rx0, ry0, rx1, ry1 = ring.boundingBox()
                x0, y0, x1, y1 = inside.boundingBox()
                self.assertAlmostEqual((x0 + x1) / 2, (rx0 + rx1) / 2, delta=5)
                self.assertAlmostEqual((y0 + y1) / 2, (ry0 + ry1) / 2, delta=5)
                self.assertGreaterEqual(measure.gap(ring, inside), 48)


class ReshapedTest(unittest.TestCase):
    """Letters made from our own strokes, moved and shortened."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def box(self, name):
        return layer_of(self.font, name).boundingBox()

    def test_descenders_reach_ours(self):
        for name, like in (("mu", "p"), ("eng", "dotlessj"), ("Eng", "dotlessj"),
                           ("florin", "dotlessj")):
            with self.subTest(glyph=name):
                self.assertAlmostEqual(self.box(name)[1], self.box(like)[1], delta=3)

    def test_kra_is_a_short_k(self):
        # The stem stops at the x-height, as n's and u's do; the arms stay k's, whose upper one
        # flicks up to 498.
        kra = self.font["kgreenlandic"]
        _, _, _, stem_top = geo.trim(kra.foreground, x1=200).boundingBox()
        self.assertGreaterEqual(stem_top, 473)
        self.assertLessEqual(stem_top, 481)
        arms = geo.trim(kra.foreground, x0=200).boundingBox()
        k_arms = geo.trim(self.font["k"].foreground, x0=200).boundingBox()
        for edge, k_edge in zip(arms, k_arms):
            self.assertAlmostEqual(edge, k_edge, delta=1)  # cleanup rounds a new extremum

    def test_per_mille_rings_are_percent_rings(self):
        def rings(name):
            # Outer contours of the rings: the slash is the one taller than 300.
            return sorted(c.boundingBox() for c in self.font[name].foreground
                          if c.isClockwise() and c.boundingBox()[3] - c.boundingBox()[1] < 300)

        [upper, lower] = sorted(rings("percent"), key=lambda b: -b[1])
        per_mille = rings("perthousand")
        self.assertEqual(len(per_mille), 3)
        for ring in per_mille:
            self.assertAlmostEqual(ring[2] - ring[0], lower[2] - lower[0], delta=3)
        left, right = sorted((r for r in per_mille if r[3] < 300), key=lambda b: b[0])
        self.assertGreaterEqual(right[0] - left[2], 5)

    def test_per_mille_slash_clears_the_rings(self):
        contours = list(self.font["perthousand"].foreground)
        slash = fontforge.layer()
        slash += max(contours, key=lambda c: c.boundingBox()[3] - c.boundingBox()[1])
        for contour in contours:
            if contour.isClockwise() and contour.boundingBox()[3] < 300:
                ring = fontforge.layer()
                ring += contour
                self.assertGreaterEqual(measure.gap(slash, ring), 20)

    def test_ij_hook_runs_under_the_i(self):
        # As in Fira Code: j's hook passes under the i, whose stem stops at the baseline.
        ij = self.font["ij"].foreground
        [(stem_left, stem_right), _] = measure.spans_at_y(ij, 200)
        self.assertLess(geo.trim(ij, y1=-100).boundingBox()[0], stem_right)
        _, stem_bottom, _, _ = geo.trim(ij, x0=stem_left, x1=stem_right, y0=-100).boundingBox()
        self.assertGreaterEqual(stem_bottom, -20)


class ShapeTest(unittest.TestCase):
    """ß ð § ¶, drawn from our strokes where the font has no glyph to build them from."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_heights(self):
        for name, bottom, top in (("germandbls", -30, 675), ("section", -120, 700)):
            with self.subTest(glyph=name):
                _, y0, _, y1 = self.font[name].boundingBox()
                self.assertAlmostEqual(y0, bottom, delta=20)
                self.assertAlmostEqual(y1, top, delta=10)

    def test_sharp_s_stays_open_at_the_bottom(self):
        # The 3's lower end stops short of the stem, or ß reads as B.
        layer = self.font["germandbls"].foreground
        self.assertEqual(len(measure.spans_at_y(layer, 60)), 2)
        self.assertEqual(len(layer), 1)

    def test_eth_keeps_the_counter_of_six(self):
        # ð is 6 mirrored: its bowl keeps 6's counter.
        self.assertAlmostEqual(measure.counter(self.font["eth"].foreground, 150),
                               measure.counter(self.font["six"].foreground, 150), delta=2)

    def test_eth_bar_crosses_its_stroke(self):
        # Bar and rising stroke make one outline, the bar reaching past the stroke both sides.
        layer = self.font["eth"].foreground
        crossing = measure.spans_at_y(layer, 540)
        self.assertEqual(len(crossing), 1)
        rising = measure.spans_at_y(layer, 400)[-1]
        self.assertGreater(crossing[0][1] - crossing[0][0], rising[1] - rising[0] + 100)

    def test_pilcrow(self):
        # Two stems down to the descender, as in Fira Code and Maple Mono, beside a filled bowl
        # as wide as theirs (397-471 wide overall).
        glyph = self.font["paragraph"]
        x0, y0, x1, _ = glyph.boundingBox()
        self.assertAlmostEqual(y0, self.font["p"].boundingBox()[1], delta=10)
        self.assertGreaterEqual(x1 - x0, 397)
        self.assertLessEqual(x1 - x0, 471)
        self.assertEqual(len(measure.spans_at_y(glyph.foreground, -150)), 2)
        self.assertTrue(all(contour.isClockwise() for contour in glyph.foreground))


if __name__ == "__main__":
    unittest.main()
