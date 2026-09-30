"""Tests for tools/make_italic.py: the italic is the regular slanted, and nothing else.

Run: python3 -m unittest discover tests

The rules on single glyphs and on classes hold for the regular (test_consistency.py,
test_legibility.py, …) and reach the italic through this derivation; test_sanity.py,
test_metadata.py, test_built.py and test_ligatures.py check both styles.
"""
import bisect
import pathlib
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import make_italic
from make_italic import AXIS, CURSIVE, CURSIVE_LETTERS, SHEAR, SLANT, SLANTED, UPRIGHT
from measure import ink
from project import ITALIC_SFD, ROOT, SFD

GENERATOR = ROOT / "tools" / "make_italic.py"
# A sheared outline's points and a reference's offset are each rounded to whole units.
ROUNDING = 1


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


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
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / ITALIC_SFD.name
            subprocess.run([sys.executable, str(GENERATOR), str(out)], check=True)
            self.assertEqual(without_timestamp(out), without_timestamp(ITALIC_SFD))

    def test_every_glyph_has_one_style(self):
        font = fontforge.open(str(SFD))
        styles = make_italic.classify(font)
        self.assertEqual(sorted(styles), sorted(g.glyphname for g in font.glyphs()))
        self.assertLessEqual(set(styles.values()), {SLANTED, UPRIGHT, CURSIVE})


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
        # Every on-curve point of the regular's outline, sheared, is one of the italic's,
        # which may add points where the slant moved an extremum; the contours and the
        # outline's box are the same.
        wrong = {}
        for name, style in self.styles.items():
            if style != SLANTED:
                continue
            expected = geo.transformed(ink(self.regular, name), SHEAR)
            found = ink(self.italic, name)
            # A composite's part is rounded, and then its offset.
            tolerance = ROUNDING * (2 if self.regular[name].references else 1)
            missing = unmatched(points(expected), points(found), tolerance)
            # FontForge boxes a curve loosely until its extrema are points; where those
            # land along a flat curve shifts with rounding, so they aren't compared.
            expected.addExtrema("all")
            boxes = zip(box(expected), box(found)) if len(expected) else ()
            if (len(found) != len(expected) or missing
                    or any(abs(a - b) > tolerance for a, b in boxes)):
                wrong[name] = (len(found), len(expected), missing[:3])
        self.assertEqual(wrong, {})

    def test_cursive_letters_differ_from_the_shear(self):
        # So the list can't name a letter the shear alone would give.
        for name in CURSIVE_LETTERS:
            with self.subTest(glyph=name):
                expected = geo.transformed(ink(self.regular, name), SHEAR)
                self.assertTrue(unmatched(points(expected), points(ink(self.italic, name))))

    def test_cursive_f_sits_on_the_descender_row(self):
        # Its descender goes as deep as j's, the shallowest of the regular's descenders.
        self.assertEqual(self.italic["f"].boundingBox()[1], self.regular["j"].boundingBox()[1])

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
        for kind in ("gsub_lookups", "gpos_lookups"):
            self.assertEqual(getattr(self.italic, kind), getattr(self.regular, kind))
            for lookup in getattr(self.regular, kind):
                with self.subTest(lookup=lookup):
                    self.assertEqual(self.italic.getLookupInfo(lookup),
                                     self.regular.getLookupInfo(lookup))
                    self.assertEqual(self.italic.getLookupSubtables(lookup),
                                     self.regular.getLookupSubtables(lookup))
        different = [g.glyphname for g in self.regular.glyphs()
                     if self.italic[g.glyphname].getPosSub("*") != g.getPosSub("*")]
        self.assertEqual(different, [])


if __name__ == "__main__":
    unittest.main()
