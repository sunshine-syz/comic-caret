"""The legibility pass's rules, checked on the SFD with FontForge.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

X_HEIGHT = 473


def offsets(glyph, name):
    """(dx, dy) of each of the glyph's references to `name`, sorted."""
    # FontForge gives each reference as (name, matrix, selected).
    return sorted((matrix[4], matrix[5]) for ref, matrix, *_ in glyph.references if ref == name)


def center(glyph, dx=0):
    """The middle of the glyph's ink, moved dx."""
    x0, _, x1, _ = glyph.boundingBox()
    return (x0 + x1) / 2 + dx


class LookalikeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_l_ends_in_a_tail_where_1_has_a_foot(self):
        # 30 units up, 1's foot spans the glyph; l's tail covers little more than half as much
        # (the references: 54-59 %).
        [(l0, l1)] = measure.spans_at_y(self.font["l"].foreground, 30)
        [(f0, f1)] = measure.spans_at_y(self.font["one"].foreground, 30)
        self.assertLessEqual(l1 - l0, 0.6 * (f1 - f0))

    def test_l_is_balanced_in_the_cell(self):
        self.assertAlmostEqual(center(self.font["l"]), ADVANCE / 2, delta=10)

    def test_l_marks_stay_on_its_stem(self):
        stem = geo.trim(self.font["l"].foreground, y0=300, y1=500)
        for name, mark in (("lacute", "acute"), ("lcommaaccent", "commaaccent")):
            with self.subTest(glyph=name):
                [(dx, _)] = offsets(self.font[name], mark)
                self.assertAlmostEqual(center(self.font[mark], dx), measure.ink_center(stem),
                                       delta=10)

    def test_i_and_j_dots_are_periods_well_above_the_x_height(self):
        _, bottom, _, _ = self.font["period"].boundingBox()
        for name in ("i", "iogonek", "j"):
            with self.subTest(glyph=name):
                [(_, dy)] = offsets(self.font[name], "period")
                self.assertEqual(dy, 584)
                self.assertGreaterEqual(bottom + dy - X_HEIGHT, 90)

    def test_zero_slash_runs_through_the_middle_of_the_counter(self):
        layer = self.font["zero"].foreground
        _, y0, _, y1 = layer.boundingBox()
        left_ring, slash, right_ring = measure.spans_at_y(layer, (y0 + y1) / 2)
        self.assertLessEqual(abs((slash[0] - left_ring[1]) - (right_ring[0] - slash[1])), 10)


class ColonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_colon_is_two_periods_from_the_baseline_past_the_x_height(self):
        colon = self.font["colon"]
        self.assertEqual(len(colon.foreground), 0)
        self.assertEqual(offsets(colon, "period"), [(0, 0), (0, 356)])
        self.assertEqual(colon.boundingBox()[3], 487)

    def test_semicolon_is_the_colon_dot_over_a_comma(self):
        semicolon = self.font["semicolon"]
        self.assertEqual(len(semicolon.foreground), 0)
        self.assertEqual(offsets(semicolon, "period"), [(0, 356)])
        [(dx, dy)] = offsets(semicolon, "comma")
        self.assertEqual(dy, 0)
        # The comma's round head, above y 60, sits under the dot.
        head = geo.trim(self.font["comma"].foreground, y0=60)
        self.assertAlmostEqual(measure.ink_center(head) + dx, center(self.font["period"]),
                               delta=5)


BRACKETS = {"parenleft": 320, "bracketleft": 290, "braceleft": 410}  # target ink widths
PAIRS = {"parenright": "parenleft", "bracketright": "bracketleft", "braceright": "braceleft"}
TURNED = (-1, 0, 0, -1, ADVANCE, 655)  # 180 degrees about (275, 327.5), the brackets' middle


class BracketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_brackets_share_one_height(self):
        for name in (*BRACKETS, *PAIRS):
            with self.subTest(glyph=name):
                _, y0, _, y1 = self.font[name].boundingBox()
                self.assertAlmostEqual(y0, -145, delta=5)
                self.assertAlmostEqual(y1, 800, delta=5)

    def test_closing_brackets_are_the_opening_ones_turned(self):
        for right, left in PAIRS.items():
            with self.subTest(glyph=right):
                glyph = self.font[right]
                self.assertEqual(len(glyph.foreground), 0)
                self.assertEqual([(name, tuple(matrix)) for name, matrix, *_ in glyph.references],
                                 [(left, TURNED)])

    def test_brackets_are_centered_at_their_widths(self):
        for name, width in BRACKETS.items():
            with self.subTest(glyph=name):
                self.assertAlmostEqual(center(self.font[name]), ADVANCE / 2, delta=5)
                self.assertAlmostEqual(measure.ink_width(self.font[name].foreground), width,
                                       delta=10)

    def test_paren_is_as_heavy_as_a_stem(self):
        [(x0, x1)] = measure.spans_at_y(self.font["parenleft"].foreground, 327)
        self.assertAlmostEqual(x1 - x0, 90, delta=5)


# Crowding. Target ink widths at full and halfway strength, and the target
# center's offset from the cell's; q only moves. build/legibility/crowding.py reads these too.
WIDTHS = {
    "n": (399, 413, 0), "h": (394, 402, 0), "u": (392, 404, 0), "d": (425, 438, -15),
    "s": (412, 419, 0), "B": (430, 444, 16), "D": (440, 463, 16), "E": (408, 437, 12),
    "F": (404, 436, 9), "H": (407, 427, 0), "I": (371, 420, 0), "J": (427, 450, -22),
    "K": (454, 460, 32), "L": (409, 436, 33), "N": (413, 436, 0), "R": (445, 451, 28),
    "U": (427, 453, 0), "Z": (441, 455, 0), "one": (441, 448, 13), "five": (422, 434, -5),
    "seven": (435, 442, -6), "eight": (440, 450, 0), "q": (None, None, -12),
}
# The narrowest counter each glyph may have along the line at y: the narrowest reference's at
# the same letter height, or today's for R, which is already narrower.
FLOORS = {
    "n": [(236, 194)], "h": [(236, 194)], "u": [(236, 194)], "d": [(236, 211)],
    "H": [(167, 211)], "N": [(334, 155)], "U": [(334, 217)], "D": [(334, 238)],
    "B": [(167, 232), (501, 218)], "R": [(501, 211)], "eight": [(167, 256), (501, 222)],
}
STRENGTH = "half"  # chosen at checkpoint C: "full" or "half"


class CrowdingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_counters_keep_their_floors(self):
        for name, floors in FLOORS.items():
            for y, floor in floors:
                with self.subTest(glyph=name, y=y):
                    self.assertGreaterEqual(
                        round(measure.counter(self.font[name].foreground, y)), floor)

    def test_letters_reach_their_target_widths(self):
        for name, (full, half, _) in WIDTHS.items():
            if full is None:
                continue
            with self.subTest(glyph=name):
                target = full if STRENGTH == "full" else half
                self.assertLessEqual(measure.ink_width(self.font[name].foreground), target + 2)

    def test_letters_sit_on_their_target_centers(self):
        for name, (_, _, target) in WIDTHS.items():
            with self.subTest(glyph=name):
                self.assertAlmostEqual(center(self.font[name]) - ADVANCE / 2, target, delta=5)


# Each mark's ink center minus its letter's, measured before the pass; narrowing keeps them.
MARK_OFFSETS = {
    "Egrave": 0, "Eacute": 0, "Ecircumflex": 0, "Edieresis": 0, "Igrave": 0, "Iacute": 0,
    "Icircumflex": 0, "Idieresis": 0, "Ntilde": 0, "Ugrave": 0, "Uacute": 0, "Ucircumflex": -1,
    "Udieresis": 0, "ntilde": -1, "ugrave": 0, "uacute": 0, "ucircumflex": 0, "udieresis": 0,
    "Dcaron": 3, "Emacron": 0, "Ebreve": 0, "Edotaccent": 0, "Ecaron": 3, "Hcircumflex": 0,
    "hcircumflex": 0, "Itilde": 0, "Imacron": 0, "Ibreve": 0, "Idotaccent": 0,
    "Jcircumflex": -1, "Kcommaaccent": -37, "Lacute": 0, "Lcommaaccent": -7, "Nacute": 0,
    "nacute": 0, "Ncommaaccent": 4, "ncommaaccent": 4, "Ncaron": 4, "ncaron": 3, "Racute": 0,
    "Rcommaaccent": 54, "Rcaron": 3, "sacute": 0, "scircumflex": 0, "scaron": 3, "Utilde": 0,
    "utilde": -1, "Umacron": 0, "umacron": 0, "Ubreve": 0, "ubreve": 0, "Uring": 0,
    "uring": 0, "Uhungarumlaut": 1, "uhungarumlaut": 2, "Zacute": 0, "Zdotaccent": 0,
    "Zcaron": 4, "scommaaccent": -6,
}


class CompositeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_marks_keep_their_place_on_narrowed_letters(self):
        for name, offset in MARK_OFFSETS.items():
            with self.subTest(glyph=name):
                references = self.font[name].references
                [letter] = [ref for ref, *_ in references if ref in WIDTHS]
                [(mark, matrix)] = [(ref, m) for ref, m, *_ in references if ref not in WIDTHS]
                self.assertAlmostEqual(center(self.font[mark], matrix[4])
                                       - center(self.font[letter]), offset, delta=2)

    def test_merged_letters_are_built_on_the_narrowed_letters(self):
        for name, letter in (("Eogonek", "E"), ("Iogonek", "I"), ("Uogonek", "U"),
                             ("uogonek", "u"), ("scedilla", "s")):
            with self.subTest(glyph=name):
                # Above y 10 the ogonek or cedilla lies inside its letter: both have the same ink.
                body = geo.trim(self.font[name].foreground, y0=10).boundingBox()
                own = geo.trim(self.font[letter].foreground, y0=10).boundingBox()
                for got, want in zip(body, own, strict=True):
                    self.assertAlmostEqual(got, want, delta=2)

    def test_turned_e_mirrors_e(self):
        self.assertAlmostEqual(center(self.font["existential"]),
                               ADVANCE - center(self.font["E"]), delta=3)
        self.assertAlmostEqual(center(self.font["uni2204"]),
                               center(self.font["existential"]), delta=3)
        [(dx, _)] = offsets(self.font["uni2204"], "slash")
        self.assertAlmostEqual(center(self.font["slash"], dx),
                               center(self.font["existential"]), delta=3)

    def test_d_caron_hangs_beside_the_stem(self):
        [(dx, _)] = offsets(self.font["dcaron"], "caron.alt")
        [(stem, _)] = measure.spans_at_y(self.font["d"].foreground, 600)
        self.assertAlmostEqual(dx - stem, 58 - 409, delta=2)  # as before the pass


class LetterFollowUpTest(unittest.TestCase):
    """P, Ƿ, G and 5, which the legibility pass left for later."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_P_sits_right_of_center(self):
        # The references put P 19-33 right of center; ours sat 8 left.
        offset = center(self.font["P"]) - ADVANCE / 2
        self.assertGreaterEqual(offset, 19)
        self.assertLessEqual(offset, 33)

    def test_wynn_bowl_runs_to_a_point_low_on_the_stem(self):
        # As in ƿ. P's bowl closes halfway up, so a line 200 up crosses only P's stem.
        self.assertEqual(len(measure.spans_at_y(self.font["uni01F7"].foreground, 200)), 2)

    def test_wynn_stands_as_tall_as_P(self):
        _, bottom, _, top = self.font["uni01F7"].boundingBox()
        _, p_bottom, _, p_top = self.font["P"].boundingBox()
        self.assertAlmostEqual(bottom, p_bottom, delta=3)
        self.assertAlmostEqual(top, p_top, delta=3)


class DotsTest(unittest.TestCase):
    """… and ÷ keep dots smaller than `.`, as in all three references; their spacing was off."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def dots(self, name):
        """The boxes of the glyph's own contours, left to right and bottom to top."""
        return sorted(contour.boundingBox() for contour in self.font[name].foreground)

    def test_divide_dots_clear_the_bar(self):
        # The references leave 81-111 between each dot and the bar; ours left 54-59.
        _, bar_bottom, _, bar_top = self.font["minus"].boundingBox()
        low, high = sorted(self.dots("divide"), key=lambda box: box[1])
        self.assertGreaterEqual(bar_bottom - low[3], 81)
        self.assertGreaterEqual(high[1] - bar_top, 81)

    def test_divide_is_centered_on_its_bar(self):
        _, bar_bottom, _, bar_top = self.font["minus"].boundingBox()
        _, bottom, _, top = self.font["divide"].boundingBox()
        self.assertAlmostEqual(bar_bottom - bottom, top - bar_top, delta=2)

    def test_ellipsis_is_centered_with_even_gaps(self):
        left, middle, right = self.dots("ellipsis")
        self.assertAlmostEqual(center(self.font["ellipsis"]), ADVANCE / 2, delta=1)
        self.assertAlmostEqual(middle[0] - left[2], right[0] - middle[2], delta=1)


class TurnedCommaTest(unittest.TestCase):
    """ģ's mark is a turned comma above, head down, as in Intel One Mono and Comic Sans MS.
    Our comma is a straight stroke, so upright or merely turned it read as an acute."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        [(cls.mark, cls.dx, cls.dy)] = [
            (name, matrix[4], matrix[5])
            for name, matrix, *_ in cls.font["gcommaaccent"].references if name != "g"]

    def test_turned_comma_has_its_head_at_the_bottom(self):
        layer = self.font[self.mark].foreground
        _, y0, _, y1 = layer.boundingBox()
        [(head0, head1)] = measure.spans_at_y(layer, y0 + 0.25 * (y1 - y0))
        [(tail0, tail1)] = measure.spans_at_y(layer, y0 + 0.85 * (y1 - y0))
        self.assertGreaterEqual(head1 - head0, 1.4 * (tail1 - tail0))

    def test_turned_comma_sits_where_the_dot_of_g_dot_does(self):
        [(dot_dx, _)] = offsets(self.font["gdotaccent"], "dotaccent")
        _, dot_bottom, _, _ = self.font["dotaccent"].boundingBox()
        _, bottom, _, _ = self.font[self.mark].boundingBox()
        self.assertAlmostEqual(bottom + self.dy, dot_bottom, delta=5)
        self.assertAlmostEqual(center(self.font[self.mark], self.dx),
                               center(self.font["dotaccent"], dot_dx), delta=5)


if __name__ == "__main__":
    unittest.main()
