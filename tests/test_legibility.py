"""The legibility pass's rules, checked on the SFD with FontForge: look-alikes stay apart,
counters stay open, and : ; and the brackets keep their construction.

Run: python3 -m unittest discover tests

Sizes and positions are judged on the proof sheet (tools/proof_sheet.py), not here.
"""
import itertools
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD


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

    def test_i_and_j_dots_are_periods_well_above_the_x_height(self):
        # One height for all three, at least 90 above the x-height (the references: 63-142).
        _, bottom, _, _ = self.font["period"].boundingBox()
        heights = set()
        for name in ("i", "iogonek", "j"):
            with self.subTest(glyph=name):
                [(_, dy)] = offsets(self.font[name], "period")
                heights.add(dy)
        self.assertEqual(len(heights), 1)
        self.assertGreaterEqual(bottom + heights.pop() - self.font.os2_xheight, 90)

    def test_zero_slash_runs_through_the_middle_of_the_counter(self):
        layer = self.font["zero"].foreground
        _, y0, _, y1 = layer.boundingBox()
        left_ring, slash, right_ring = measure.spans_at_y(layer, (y0 + y1) / 2)
        self.assertLessEqual(abs((slash[0] - left_ring[1]) - (right_ring[0] - slash[1])), 10)

    def test_white_circle_is_wider_than_o(self):
        # So "○ main" doesn't read as "o main": Fira Code's ○ is 78 wider than its o.
        ring, o = self.font[0x25CB].foreground, self.font["o"].foreground
        self.assertGreaterEqual(measure.ink_width(ring) - measure.ink_width(o), 78)


class ColonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_colon_is_two_periods_from_the_baseline_to_the_x_height(self):
        colon = self.font["colon"]
        self.assertEqual(len(colon.foreground), 0)
        lower, upper = offsets(colon, "period")
        self.assertEqual(lower, (0, 0))  # where . sits
        self.assertEqual(upper[0], 0)
        self.assertGreaterEqual(colon.boundingBox()[3], self.font.os2_xheight)

    def test_semicolon_is_the_colon_dot_over_a_comma(self):
        semicolon = self.font["semicolon"]
        self.assertEqual(len(semicolon.foreground), 0)
        self.assertEqual(offsets(semicolon, "period"), offsets(self.font["colon"], "period")[1:])
        [(dx, dy)] = offsets(semicolon, "comma")
        self.assertEqual(dy, 0)
        # The comma's round head, above y 60, sits under the dot.
        head = geo.trim(self.font["comma"].foreground, y0=60)
        self.assertAlmostEqual(measure.ink_center(head) + dx, center(self.font["period"]),
                               delta=5)


PAIRS = {"parenright": "parenleft", "bracketright": "bracketleft", "braceright": "braceleft"}


class BracketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_brackets_share_one_height(self):
        _, bottom, _, top = self.font["parenleft"].boundingBox()
        for name in ("bracketleft", "braceleft", *PAIRS):
            with self.subTest(glyph=name):
                _, y0, _, y1 = self.font[name].boundingBox()
                self.assertAlmostEqual(y0, bottom, delta=5)
                self.assertAlmostEqual(y1, top, delta=5)

    def test_closing_brackets_are_the_opening_ones_turned_in_place(self):
        # Turned 180° about the cell's middle and the bracket's, as ¡ ¿ are.
        for right, left in PAIRS.items():
            with self.subTest(glyph=right):
                glyph = self.font[right]
                self.assertEqual(len(glyph.foreground), 0)
                [(name, matrix, *_)] = glyph.references
                self.assertEqual((name, tuple(matrix[:5])), (left, (-1, 0, 0, -1, ADVANCE)))
                _, y0, _, y1 = self.font[left].boundingBox()
                _, b0, _, b1 = glyph.boundingBox()
                self.assertAlmostEqual(b0, y0, delta=1)
                self.assertAlmostEqual(b1, y1, delta=1)


# The narrowest counter each glyph may have along the line at y: the narrowest reference's at
# the same letter height, or today's for R, which is already narrower.
FLOORS = {
    "n": [(236, 194)], "h": [(236, 194)], "u": [(236, 194)], "d": [(236, 211)],
    "H": [(167, 211)], "N": [(334, 155)], "U": [(334, 217)], "D": [(334, 238)],
    "B": [(167, 232), (501, 218)], "R": [(501, 211)], "eight": [(167, 256), (501, 222)],
}


class CounterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_counters_keep_their_floors(self):
        for name, floors in FLOORS.items():
            for y, floor in floors:
                with self.subTest(glyph=name, y=y):
                    self.assertGreaterEqual(
                        round(measure.counter(self.font[name].foreground, y)), floor)


# Maple Mono 7.9's @, the tightest of the three references, across the middle of its ink box
# at our cap height: 79 of white between the loop and the inner a, and a counter of 107.
AT_GAP, AT_COUNTER = 79, 107


class AtSignTest(unittest.TestCase):
    """@ is an a inside a loop; the white inside it stays as open as in the references."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.at = cls.font["at"].foreground

    def test_loop_stays_open_round_one_counter(self):
        # One outline and the a's counter, as in all three references (and as Font Bakery's
        # contour_count expects): wherever the loop touches the a, it closes off a second hole.
        self.assertEqual(len(self.at), 2)

    def test_counter_and_the_white_round_the_a_keep_their_floors(self):
        _, y0, _, y1 = self.at.boundingBox()
        spans = measure.spans_at_y(self.at, (y0 + y1) / 2)
        self.assertGreaterEqual(len(spans), 3)  # the loop, the a's bowl and its stem, apart
        gaps = [right[0] - left[1] for left, right in itertools.pairwise(spans)]
        self.assertGreaterEqual(min(gaps), AT_GAP)
        self.assertGreaterEqual(max(gaps), AT_COUNTER)

    def test_loop_stays_clear_of_the_stem(self):
        # Down the right-hand stroke, the a's stem, the loop passes with at least the hyphen's
        # thickness of white, so they stay apart at 12 px as ⇡'s dashes do.
        [(h0, h1)] = measure.spans_at_x(self.font["hyphen"].foreground, ADVANCE / 2)
        _, y0, _, y1 = self.at.boundingBox()
        stem = measure.spans_at_y(self.at, (y0 + y1) / 2)[-1]
        spans = measure.spans_at_x(self.at, sum(stem) / 2)
        for lower, upper in itertools.pairwise(spans):
            self.assertGreaterEqual(upper[0] - lower[1], h1 - h0)


class LetterFollowUpTest(unittest.TestCase):
    """Ƿ, G and 5, which the legibility pass left for later, set apart from P and 6."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_wynn_bowl_runs_to_a_point_low_on_the_stem(self):
        # As in ƿ. P's bowl closes halfway up, so a line 200 up crosses only P's stem.
        self.assertEqual(len(measure.spans_at_y(self.font["uni01F7"].foreground, 200)), 2)

    def test_G_terminal_ends_left_of_the_stroke_below_it(self):
        # In the references it ends 11-52 left of it; ours ran 25 past, closing G up like 6.
        G = self.font["G"].foreground
        _, _, terminal, _ = geo.trim(G, y0=540).boundingBox()
        _, _, side, _ = geo.trim(G, y0=150, y1=250).boundingBox()
        self.assertLessEqual(terminal, side - 11)

    def test_five_bowl_ends_low(self):
        # The references' lower terminals top out at 73-113; ours curled up to 154 and nearly
        # closed the bowl, like 6.
        _, _, _, top = geo.trim(self.font["five"].foreground, x1=200, y1=250).boundingBox()
        self.assertLessEqual(top, 100)


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

    def test_ellipsis_dots_are_evenly_spaced(self):
        left, middle, right = self.dots("ellipsis")
        self.assertAlmostEqual(middle[0] - left[2], right[0] - middle[2], delta=1)


class TurnedCommaTest(unittest.TestCase):
    """ģ's mark is a turned comma above, head down, as in Intel One Mono and Comic Sans MS.
    Our comma is a straight stroke, so upright or merely turned it read as an acute."""

    def test_turned_comma_has_its_head_at_the_bottom(self):
        font = fontforge.open(str(SFD))
        [mark] = [name for name, *_ in font["gcommaaccent"].references if name != "g"]
        layer = font[mark].foreground
        _, y0, _, y1 = layer.boundingBox()
        [(head0, head1)] = measure.spans_at_y(layer, y0 + 0.25 * (y1 - y0))
        [(tail0, tail1)] = measure.spans_at_y(layer, y0 + 0.85 * (y1 - y0))
        self.assertGreaterEqual(head1 - head0, 1.4 * (tail1 - tail0))


if __name__ == "__main__":
    unittest.main()
