"""Tests for tools/add_shapes.py and what the spinner frames must keep.

Run: python3 -m unittest discover tests

Their centring, the math axis, mirrored pairs and turned or filled shapes are checked with
every other glyph in test_consistency.py and test_symbols.py.
"""
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import add_shapes
import lig_geometry as geo
import measure
from project import ADVANCE, ROOT, SFD

GENERATOR = ROOT / "tools" / "add_shapes.py"
TOLERANCE = 10  # the hand's wobble, as in test_consistency.py
# A spinner's frames share one box, so it turns without pulsing (the arcs and the stars have
# rules of their own).
FAMILIES = ("◐◑◒◓", "◴◵◶◷", "◰◱◲◳", "☰☱☲☳☴☵☶☷", "⊶⊷", "☖☗", "▰▱", "▮▯", "◎⊙⦾⦿◌◍", "⧆⧇")
# Shape -> the whole shape it holds: a cut of ● or ■ inside it, or pieces inside its counter.
HOLDS = {"◐": "○", "◑": "○", "◒": "○", "◓": "○", "◴": "○", "◵": "○", "◶": "○", "◷": "○",
         "◰": "☐", "◱": "☐", "◲": "☐", "◳": "☐", "◍": "○", "⧆": "☐"}
# Trigram -> which of its lines, top to bottom, are broken (the I Ching's figures).
TRIGRAMS = {"☰": "", "☱": "top", "☲": "middle", "☳": "top middle", "☴": "bottom",
            "☵": "top bottom", "☶": "middle bottom", "☷": "top middle bottom"}
STARS = {"✷": 8, "✸": 8, "✹": 12, "✺": 16}  # points
# ‼'s dots keep at least Maple Mono's white between them (the only reference's, at our em).


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


def box(font, char):
    return font[ord(char)].boundingBox()


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the generator changed without a rerun, or a frame was edited by hand.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / SFD.name
            shutil.copy(SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(SFD))

    def test_the_font_has_every_frame(self):
        font = fontforge.open(str(SFD))
        missing = [f"U+{code:04X}" for code in add_shapes.CODES if code not in font]
        self.assertEqual(missing, [])


class FrameTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def ink(self, char):
        return measure.ink(self.font, self.font[ord(char)].glyphname)

    def cut(self, char, whole):
        """The black part of a cut shape: the ink of a reference glyph's other parts (they
        overlap the whole shape, so the flattened ink can't be measured), or the outline."""
        glyph = self.font[ord(char)]
        if not glyph.references:
            return glyph.foreground
        whole_name = self.font[ord(whole)].glyphname
        parts = [geo.transformed(measure.ink(self.font, name), matrix)
                 for name, matrix, *_ in glyph.references if name != whole_name]
        self.assertEqual(len(parts), 1)
        return parts[0]

    def test_a_spinners_frames_share_one_box(self):
        off = {}
        for family in FAMILIES:
            first = box(self.font, family[0])
            for char in family[1:]:
                if any(abs(a - b) > TOLERANCE for a, b in zip(box(self.font, char), first)):
                    off[char] = box(self.font, char)
        self.assertEqual(off, {})

    def test_cut_shapes_hold_their_whole_shape(self):
        # ○ or ☐ stays whole under the black cut or the pieces inside it: a reference to it,
        # or an outline that covers it.
        wrong = {}
        for char, whole in HOLDS.items():
            glyph = self.font[ord(char)]
            if glyph.references:
                refs = {name: matrix for name, matrix, *_ in glyph.references}
                if refs.get(self.font[ord(whole)].glyphname) != psMat.identity():
                    wrong[char] = whole
            elif measure.covered(self.ink(whole), glyph.foreground) < 0.99:
                wrong[char] = whole
        self.assertEqual(wrong, {})

    def test_black_cuts_lie_inside_the_shape(self):
        # The ink is ○ or ☐ and a part of ● or ■, nothing outside them.
        wrong = {}
        for char, whole in HOLDS.items():
            black = {"○": "●", "☐": "■"}[whole]
            if measure.covered(self.cut(char, whole), self.ink(black)) < 0.99:
                wrong[char] = black
        self.assertEqual(wrong, {})

    def test_halves_and_quadrants_fill_where_their_names_say(self):
        # Ink a sixth of the shape's width from its middle, inside the ring, in each quarter
        # tells the filled quarters.
        wrong = {}
        for char in "◐◑◒◓◴◵◶◷◰◱◲◳":
            x0, y0, x1, y1 = box(self.font, char)
            cx, cy, step = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 6
            ink = self.cut(char, "☐" if "SQUARE" in unicodedata.name(char) else "○")
            filled = set()
            for row, y in (("LOWER", cy - step), ("UPPER", cy + step)):
                for column, x in (("LEFT", cx - step), ("RIGHT", cx + step)):
                    if any(a <= x <= b for a, b in measure.spans_at_y(ink, y)):
                        filled.add(f"{row} {column}")
            words = unicodedata.name(char).split()  # "... WITH LEFT HALF BLACK", "... WITH UPPER LEFT QUADRANT"
            if "HALF" in words:
                side = words[words.index("HALF") - 1]
                want = {f"{row} {column}" for row in ("LOWER", "UPPER")
                        for column in ("LEFT", "RIGHT")
                        if side in (row, column)}
            else:
                want = {" ".join(words[-3:-1])}
            if filled != want:
                wrong[char] = sorted(filled)
        self.assertEqual(wrong, {})

    def test_arcs_are_the_quarters_and_halves_of_the_circle(self):
        # Each arc's box is the part of ○'s box its name gives, cut at the middle.
        x0, y0, x1, y1 = box(self.font, "○")
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        want = {"◜": (x0, cy, cx, y1), "◝": (cx, cy, x1, y1), "◞": (cx, y0, x1, cy),
                "◟": (x0, y0, cx, cy), "◠": (x0, cy, x1, y1), "◡": (x0, y0, x1, cy)}
        off = {char: box(self.font, char) for char, b in want.items()
               if any(abs(a - c) > 1 for a, c in zip(box(self.font, char), b))}
        self.assertEqual(off, {})

    def test_triangles_are_the_squares_corners(self):
        # ◢ fills ■'s lower right half: its box is ■'s, and its ink covers the corner and
        # not the opposite one. ◣ is ◢ mirrored and ◤ ◥ are ◢ ◣ turned (test_consistency
        # and test_symbols).
        x0, y0, x1, y1 = box(self.font, "■")
        ink = self.ink("◢")
        for got, want in zip(ink.boundingBox(), (x0, y0, x1, y1)):
            self.assertAlmostEqual(got, want, delta=TOLERANCE + 2)
        near = (x1 - x0) / 10
        self.assertTrue(any(a <= x1 - near <= b for a, b in measure.spans_at_y(ink, y0 + near)))
        self.assertFalse(any(a <= x0 + near <= b for a, b in measure.spans_at_y(ink, y1 - near)))

    def test_bars_are_the_square_narrowed(self):
        # ▯ keeps ☐'s height and stroke; ▮ is ▯ filled (test_symbols). About half as wide,
        # as Fira Code's, the only reference's.
        _, y0, _, y1 = box(self.font, "☐")
        bx0, by0, bx1, by1 = box(self.font, "▯")
        self.assertAlmostEqual(by0, y0, delta=1)
        self.assertAlmostEqual(by1, y1, delta=1)
        self.assertLess(bx1 - bx0, 0.6 * (by1 - by0))
        box_walls = measure.spans_at_y(self.ink("☐"), (y0 + y1) / 2)
        bar_walls = measure.spans_at_y(self.ink("▯"), (y0 + y1) / 2)
        self.assertEqual(len(bar_walls), 2)
        for (a, b), (c, d) in zip(bar_walls, box_walls):
            self.assertAlmostEqual(b - a, d - c, delta=2)

    def only_reference(self, char):
        glyph = self.font[ord(char)]
        self.assertEqual(len(glyph.foreground), 0)
        [(name, matrix, *_)] = glyph.references
        return name, matrix

    def references(self, char):
        glyph = self.font[ord(char)]
        self.assertEqual(len(glyph.foreground), 0)
        return {name: matrix for name, matrix, *_ in glyph.references}

    def test_ringed_shapes_are_the_ring_over_the_small_shape(self):
        # References, so they follow ○ ☐ ◦ ◉, the bullet operator and the small asterisk.
        circle, box_name = self.font[ord("○")].glyphname, self.font[ord("☐")].glyphname
        bullet = self.font[ord("◦")].glyphname
        for char, parts in (("◎", {circle, bullet}), ("⦾", {self.font[ord("◎")].glyphname}),
                            ("⧇", {box_name, bullet}), ("⧆", {box_name, add_shapes.SMALL_ASTERISK}),
                            ("⊙", {circle, self.font[ord("∙")].glyphname})):
            with self.subTest(glyph=char):
                refs = self.references(char)
                self.assertEqual(set(refs), parts)
                for matrix in refs.values():
                    self.assertEqual(matrix, psMat.identity())
        name, matrix = self.only_reference("⦿")
        self.assertEqual((name, matrix), (self.font[ord("◉")].glyphname, psMat.identity()))

    def test_bullet_operator_is_the_period_on_the_axis(self):
        name, matrix = self.only_reference("∙")
        self.assertEqual(name, "period")
        self.assertEqual(tuple(matrix[:4]), (1, 0, 0, 1))

    def test_dotted_circle_is_the_ring_in_dashes(self):
        # Every dash lies on ○'s ring, they leave gaps, and one sits on each axis so the
        # frame keeps ○'s box.
        ring, dotted = self.ink("○"), self.ink("◌")
        self.assertEqual(len(dotted), add_shapes.DASHES)
        self.assertGreaterEqual(measure.covered(dotted, ring), 0.99)
        self.assertLess(measure.covered(ring, dotted), 0.9)

    def test_filled_circle_has_bars_of_the_small_rings_stroke(self):
        # As thick as ◦'s ring is somewhere round it: the hand's ring varies by a few units.
        _, y0, _, y1 = box(self.font, "○")
        spans = measure.spans_at_y(self.ink("◍"), (y0 + y1) / 2)
        self.assertEqual(len(spans), 2 + add_shapes.FILL_BARS)
        ring = self.ink("◦")
        bx0, by0, bx1, by1 = ring.boundingBox()
        thickness = [b - a for k in range(-2, 3)
                     for a, b in (*measure.spans_at_y(ring, (by0 + by1) / 2 + k * 10),
                                  *measure.spans_at_x(ring, (bx0 + bx1) / 2 + k * 10))]
        for a, b in spans[1:-1]:
            self.assertGreaterEqual(b - a, min(thickness) - 2)
            self.assertLessEqual(b - a, max(thickness) + 2)

    def test_squared_asterisk_keeps_clear_of_its_box(self):
        # At least half of ☐'s stroke of white around the ∗, so it reads inside the box.
        box_ink = self.ink("☐")
        [(a0, a1), *_] = measure.spans_at_y(box_ink, add_shapes.AXIS)
        [matrix] = [m for name, m, *_ in self.font[ord("⧆")].references
                    if name == add_shapes.SMALL_ASTERISK]
        asterisk = geo.transformed(measure.ink(self.font, add_shapes.SMALL_ASTERISK), matrix)
        self.assertGreaterEqual(measure.gap(asterisk, box_ink), (a1 - a0) / 2)

    def test_trigrams_break_the_lines_their_names_say(self):
        # Three bars of the hyphen's stroke; a broken line is two halves with a gap at the
        # middle, where a whole line crosses.
        [(h0, h1)] = measure.spans_at_x(self.ink("-"), ADVANCE / 2)
        wrong = {}
        for char, broken in TRIGRAMS.items():
            ink = self.ink(char)
            side = measure.spans_at_x(ink, 100)
            middle = measure.spans_at_x(ink, ADVANCE / 2)
            lines = ["bottom", "middle", "top"]  # spans come lowest first
            # A line is whole where the middle shows a bar at the side bar's height.
            whole = [lines[i] for i, (a, b) in enumerate(side)
                     if any(abs((a + b) - (c + d)) / 2 < TOLERANCE for c, d in middle)]
            got = sorted(set(lines) - set(whole), key=lines.index, reverse=True)
            if len(side) != 3 or got != broken.split():
                wrong[char] = got
            for a, b in side:
                if abs((b - a) - (h1 - h0)) > 4:
                    wrong[char] = f"bar {b - a:.0f} thick"
        self.assertEqual(wrong, {})

    def test_stars_have_their_points_at_six_stars_radius(self):
        # The tips are the outline's clusters of points near the radius, going round: two
        # points more than half a tip's pitch apart are on different tips, since the
        # rounded tips are far narrower than that. ✶ points up, so its height is two radii.
        x0, y0, x1, y1 = box(self.font, "✶")
        cx, cy, radius = (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0) / 2
        wrong = {}
        for char, points in STARS.items():
            reach = [(math.atan2(p.y - cy, p.x - cx), math.hypot(p.x - cx, p.y - cy))
                     for contour in self.ink(char) for p in contour if p.on_curve]
            far = sorted(angle for angle, r in reach if r > 0.97 * radius)
            gaps = [b - a for a, b in zip(far, far[1:])] + [far[0] + 2 * math.pi - far[-1]]
            tips = sum(1 for gap in gaps if gap > math.pi / points)
            if tips != points or abs(max(r for _, r in reach) - radius) > TOLERANCE:
                wrong[char] = tips
        self.assertEqual(wrong, {})

    def test_joined_rounds_are_a_ring_and_a_disc_joined(self):
        # ⊶ is ○—● and ⊷ ●—○, as STIX and Arial Unicode draw them: one outline with one
        # counter, on the left in ⊶ and the right in ⊷.
        for char, side in (("⊶", -1), ("⊷", 1)):
            with self.subTest(glyph=char):
                layer = self.ink(char)
                self.assertEqual(sorted(c.isClockwise() for c in layer), [False, True])
                [hole] = [c for c in layer if not c.isClockwise()]
                a, _, b, _ = hole.boundingBox()
                self.assertEqual(math.copysign(1, (a + b) / 2 - ADVANCE / 2), side)

    def test_shogi_piece_points_up_and_tapers_down(self):
        # The apex at the top middle, and the base narrower than the shoulders.
        ink = self.ink("☖")
        x0, y0, x1, y1 = ink.boundingBox()
        top = geo.trim(ink, y0=y1 - 10)
        self.assertAlmostEqual(measure.ink_center(top), ADVANCE / 2, delta=TOLERANCE)
        base = measure.spans_at_y(ink, y0 + 20)
        shoulders = measure.spans_at_y(ink, y1 - add_shapes.SHOGI_SHOULDER)
        self.assertLess(base[-1][1] - base[0][0], shoulders[-1][1] - shoulders[0][0])

    def test_parallelogram_leans_right(self):
        ink = self.ink("▱")
        _, y0, _, y1 = ink.boundingBox()
        top, bottom = measure.spans_at_y(ink, y1 - 20), measure.spans_at_y(ink, y0 + 20)
        self.assertGreater(top[0][0], bottom[0][0])
        self.assertGreater(top[-1][1], bottom[-1][1])


if __name__ == "__main__":
    unittest.main()
