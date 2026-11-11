"""Tests for tools/make_italic.py: the italic is the regular slanted, and nothing else.

Run: python3 -m unittest discover tests

The rules on single glyphs and on classes hold for the regular (test_consistency.py,
test_legibility.py, …) and reach the italic through this derivation; test_sanity.py,
test_metadata.py, test_built.py and test_ligatures.py check every style.
"""
import bisect
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lig_geometry as geo
import make_italic
from helpers import assert_lookups_carry_over
from make_italic import CURSIVE, CURSIVE_LETTERS, REACH, SHEAR, SLANT, SLANTED, STEM_CUT, UPRIGHT
from measure import area, ink, slant, spans_at_y
from project import ADVANCE, AXIS, ITALIC_SFD, ROOT, ROUNDING, SFD
from sfd_files import rerun_differences

GENERATOR = ROOT / "tools" / "make_italic.py"


def points(layer):
    """The outline's on-curve points sorted by x, so two outlines compare whatever their
    contours' order and starting points. Not the control points: adding a point where the
    slant moved an extremum splits a curve and replaces them."""
    return sorted((p.x, p.y) for contour in layer for p in contour if p.on_curve)


def unmatched(expected, found, tolerance=ROUNDING):
    """The points of `expected` that `found` has no point within `tolerance` of (both sorted
    by x, as points() gives them)."""
    xs = [x for x, _ in found]
    missing = []
    for x, y in expected:
        i = bisect.bisect_left(xs, x - tolerance)
        while i < len(found) and found[i][0] <= x + tolerance:
            if abs(found[i][1] - y) <= tolerance:
                break
            i += 1
        else:
            missing.append((x, y))
    return missing


def box(layer):
    return tuple(round(v) for v in layer.boundingBox())


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the regular or the generator changed without a rerun, or when the italic
        # was edited by hand, as well as when a run is not repeatable.
        self.assertEqual(rerun_differences(ITALIC_SFD, GENERATOR), [])

    def test_every_glyph_has_one_style(self):
        font = fontforge.open(str(SFD))
        styles = make_italic.classify(font)
        self.assertEqual(sorted(styles), sorted(g.glyphname for g in font.glyphs()))
        self.assertLessEqual(set(styles.values()),
                            {SLANTED, UPRIGHT, CURSIVE, make_italic.MIRRORED, make_italic.AGAINST})

    def test_unencoded_unreferenced_glyph_must_be_classed(self):
        # Only the generators' glyphs are known to slant; any other one has to be classed.
        font = fontforge.font()
        # glyphs() skips an unencoded glyph until something is set on it.
        font.createChar(-1, "colon.eq").width = ADVANCE
        self.assertEqual(make_italic.classify(font)["colon.eq"], SLANTED)
        font.createChar(-1, "mystery").width = ADVANCE
        with self.assertRaisesRegex(SystemExit, "mystery"):
            make_italic.classify(font)


class ItalicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regular = fontforge.open(str(SFD))
        cls.italic = fontforge.open(str(ITALIC_SFD))
        cls.styles = make_italic.classify(cls.regular)

    def test_glyphs_match_the_regulars(self):
        def listed(font):
            return [(g.glyphname, g.unicode, g.width, g.glyphclass) for g in font.glyphs()]
        self.assertEqual(listed(self.italic), listed(self.regular))

    def test_upright_glyphs_keep_the_regulars_ink(self):
        changed = [name for name, style in self.styles.items() if style == UPRIGHT
                   and points(ink(self.italic, name)) != points(ink(self.regular, name))]
        self.assertEqual(changed, [])

    def test_slanted_glyphs_are_the_regulars_sheared(self):
        # Every on-curve point of the regular's outline, sheared, is one of the italic's
        # within the reach of evened(), which moves the diagonals' sides. The italic may add
        # points where the slant moved an extremum. The contours are the same, and the
        # outline's box within the same reach.
        wrong = {}
        # A glyph built on ‘ or ` follows it through its reference (“ ʻ).
        unsheared = {*make_italic.MIRRORS, *make_italic.AGAINST_SLANT}
        for name, style in self.styles.items():
            if style != SLANTED or {ref for ref, *_ in self.regular[name].references} & unsheared:
                continue
            expected = geo.transformed(ink(self.regular, name), SHEAR)
            found = ink(self.italic, name)
            # A composite's part is rounded, and then its offset.
            tolerance = ROUNDING * (2 if self.regular[name].references else 1) + REACH
            missing = unmatched(points(expected), points(found), tolerance)
            # FontForge boxes a curve loosely until its extrema are points; where those
            # land along a flat curve shifts with rounding, so they aren't compared.
            expected.addExtrema("all")
            boxes = zip(box(expected), box(found)) if len(expected) else ()
            if (len(found) != len(expected) or missing
                    or any(abs(a - b) > tolerance for a, b in boxes)):
                wrong[name] = (len(found), len(expected), missing[:3])
        self.assertEqual(wrong, {})

    def test_diagonals_are_evened(self):
        # A shear keeps a glyph's area but for its points' rounding, which | shows: an
        # upright stem, which evened() leaves alone. The italic's / gains more ink than that
        # and its \ loses more.
        def gain(name):
            return area(ink(self.italic, name)) / area(ink(self.regular, name)) - 1
        rounding = abs(gain("bar"))
        self.assertGreater(gain("slash"), rounding)
        self.assertLess(gain("backslash"), -rounding)

    def test_left_quote_mirrors_the_right(self):
        # As in the regular: sheared, ‘ leaned −11° beside ’'s +34°. Mirrored about the
        # cell's middle as the shear moves it at their height, so ‘ stands where it did.
        for name, pair in make_italic.MIRRORS.items():
            with self.subTest(glyph=name):
                right = ink(self.italic, pair)
                _, y0, _, y1 = right.boundingBox()
                middle = ADVANCE / 2 + ((y0 + y1) / 2 - AXIS) * SLANT
                mirrored = geo.mirrored_x(right, round(2 * middle) / 2)
                self.assertEqual(unmatched(points(mirrored), points(ink(self.italic, name))), [])

    def test_backtick_leans_apart_from_the_left_quote(self):
        # ` and ‘ lean the same way and part by their lean, as in the regular; the mirrored ‘
        # takes the sheared `'s lean, so ` leans against the slant. They keep at least half
        # the regular's difference: a sheared ` left 2°.
        def apart(font):
            return abs(slant(ink(font, "grave")) - slant(ink(font, "quoteleft")))
        self.assertGreaterEqual(apart(self.italic), apart(self.regular) / 2)
        for name in make_italic.AGAINST_SLANT:
            with self.subTest(glyph=name):
                expected = geo.transformed(ink(self.regular, name), SHEAR)
                self.assertTrue(unmatched(points(expected), points(ink(self.italic, name))))

    def test_cursive_letters_differ_from_the_shear(self):
        # So the list can't name a letter the shear alone would give.
        for name in CURSIVE_LETTERS:
            with self.subTest(glyph=name):
                expected = geo.transformed(ink(self.regular, name), SHEAR)
                self.assertTrue(unmatched(points(expected), points(ink(self.italic, name))))

    def test_cursive_f_sits_on_the_descender_row(self):
        # Its descender goes as deep as j's, the shallowest of the regular's descenders; the
        # stroke's lowest point is rounded like every other.
        self.assertAlmostEqual(self.italic["f"].boundingBox()[1],
                               self.regular["j"].boundingBox()[1], delta=ROUNDING)

    def test_cursive_f_descender_is_as_wide_as_the_stem_where_they_meet(self):
        # No ledge or notch where the descender joins the stem at STEM_CUT: rows 2 below and 2
        # above it, clear of the 1-unit band either side that spans_at_y reads, cross strokes
        # of the same width, but for the points' rounding.
        f = ink(self.italic, "f")
        (below,), (above,) = (spans_at_y(f, STEM_CUT + dy) for dy in (-2, 2))
        self.assertAlmostEqual(below[1] - below[0], above[1] - above[0], delta=ROUNDING)

    def test_anchors_move_with_the_shear(self):
        wrong = {}
        for name, style in self.styles.items():
            expected = self.regular[name].anchorPoints
            if style != UPRIGHT:
                expected = tuple((n, kind, round(x + (y - AXIS) * SLANT), y, *rest)
                                 for n, kind, x, y, *rest in expected)
            if self.italic[name].anchorPoints != expected:
                wrong[name] = (self.italic[name].anchorPoints, expected)
        self.assertEqual(wrong, {})

    def test_lookups_carry_over(self):
        assert_lookups_carry_over(self, self.italic, self.regular)


if __name__ == "__main__":
    unittest.main()
