"""Tests for tools/make_bold.py: the bold is the regular with its strokes thickened, and
nothing else.

Run: python3 -m unittest discover tests
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_bold
from add_ligatures import GENERATED
from make_bold import BOLDER, PEN, SHARED
from measure import area, ink, vertical_edges
from project import ADVANCE, BOLD_SFD, ROOT, ROUNDING, SFD
from sfd_files import differences

GENERATOR = ROOT / "tools" / "make_bold.py"


def points(layer):
    """The outline's on-curve points on whole units, sorted, so two outlines compare whatever
    their contours' order and starting points. A part scaled off the grid is rounded where the
    bold unlinks it, as the build rounds it anyway."""
    return sorted((round(p.x), round(p.y)) for contour in layer for p in contour if p.on_curve)


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the regular or the generator changed without a rerun, or when the bold
        # was edited by hand, as well as when a run is not repeatable.
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / BOLD_SFD.name
            # FontForge reports the overlaps it trips on to stderr; shown only on a failure.
            run = subprocess.run([sys.executable, str(GENERATOR), str(out)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(differences(BOLD_SFD, out), [])

    def test_every_glyph_has_one_class(self):
        font = fontforge.open(str(SFD))
        classes = make_bold.classify(font)
        self.assertEqual(sorted(classes), sorted(g.glyphname for g in font.glyphs()))
        self.assertLessEqual(set(classes.values()), {SHARED, BOLDER})

    def test_unencoded_unreferenced_glyph_must_be_classed(self):
        # Only the generators' glyphs are known to grow; any other one has to be classed.
        font = fontforge.font()
        # glyphs() skips an unencoded glyph until something is set on it.
        font.createChar(-1, "colon.eq").width = 550
        self.assertEqual(make_bold.classify(font)["colon.eq"], BOLDER)
        font.createChar(-1, "mystery").width = 550
        with self.assertRaisesRegex(SystemExit, "mystery"):
            make_bold.classify(font)


class BoldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regular = fontforge.open(str(SFD))
        cls.bold = fontforge.open(str(BOLD_SFD))
        cls.classes = make_bold.classify(cls.regular)

    def of_class(self, kind):
        return [name for name, found in self.classes.items() if found == kind]

    def test_glyphs_match_the_regulars(self):
        def listed(font):
            return [(g.glyphname, g.unicode, g.width, g.glyphclass) for g in font.glyphs()]
        self.assertEqual(listed(self.bold), listed(self.regular))

    def test_shared_glyphs_keep_the_regulars_ink(self):
        changed = [name for name in self.of_class(SHARED)
                   if points(ink(self.bold, name)) != points(ink(self.regular, name))]
        self.assertEqual(changed, [])

    def test_bolder_glyphs_have_more_ink(self):
        thinner = {}
        for name in self.of_class(BOLDER):
            if not len(self.regular[name].foreground):
                continue
            found, regular = (area(font[name].foreground) for font in (self.bold, self.regular))
            if found <= regular:
                thinner[name] = (round(found), round(regular))
        self.assertEqual(thinner, {})

    def test_bolder_glyphs_grow_no_taller_than_the_pen(self):
        # The pen grows a horizontal edge by half its height, and rounding moves it a unit
        # more, so a bold letter keeps the regular's rows.
        limit = PEN[1] / 2 + ROUNDING
        taller = {}
        for name in self.of_class(BOLDER):
            found, regular = ink(self.bold, name), ink(self.regular, name)
            if not len(regular):
                continue
            (_, y0, _, y1), (_, ry0, _, ry1) = found.boundingBox(), regular.boundingBox()
            if abs(y0 - ry0) > limit or abs(y1 - ry1) > limit:
                taller[name] = ((y0, y1), (ry0, ry1))
        self.assertEqual(taller, {})

    def test_pieces_keep_their_overlap(self):
        # A ligature piece cut flat past the cell, where it overlaps the next piece, ends at the
        # same line as the regular's, so the seams keep their overlap and no rounded corner
        # shows. Its round ends, as <='s tips, grow like any stroke.
        wrong, cut = {}, []
        for name in self.of_class(BOLDER):
            if not (GENERATED.fullmatch(name) or name == "uni23AF"):
                continue
            regular, found = ink(self.regular, name), ink(self.bold, name)
            if not len(regular):
                continue
            x0, _, x1, _ = regular.boundingBox()
            flat = {x for x, *_ in vertical_edges(regular)}
            ends = [(0, x0)] if x0 < 0 and x0 in flat else []
            ends += [(2, x1)] if x1 > ADVANCE and x1 in flat else []
            for side, x in ends:
                cut.append(name)
                if found.boundingBox()[side] != x:
                    wrong[name] = (found.boundingBox()[side], x)
        self.assertIn("hyphen.mid", cut)
        self.assertEqual(wrong, {})

    def test_references_and_lookups_carry_over(self):
        # Every glyph keeps the regular's references but those the bold draws as its outline
        # (make_bold.unlinked_parts()).
        def listed(glyph):
            return sorted((name, tuple(matrix)) for name, matrix, *_ in glyph.references)
        wrong = {}
        for glyph in self.regular.glyphs():
            name = glyph.glyphname
            unlinked = make_bold.unlinked_parts(glyph, self.classes)
            expected = [ref for ref in listed(glyph) if ref[0] not in unlinked]
            if listed(self.bold[name]) != expected:
                wrong[name] = (listed(self.bold[name]), expected)
        self.assertEqual(wrong, {})
        for kind in ("gsub_lookups", "gpos_lookups"):
            self.assertEqual(getattr(self.bold, kind), getattr(self.regular, kind))
            for lookup in getattr(self.regular, kind):
                with self.subTest(lookup=lookup):
                    self.assertEqual(self.bold.getLookupInfo(lookup),
                                     self.regular.getLookupInfo(lookup))
                    self.assertEqual(self.bold.getLookupSubtables(lookup),
                                     self.regular.getLookupSubtables(lookup))
        different = [g.glyphname for g in self.regular.glyphs()
                     if self.bold[g.glyphname].getPosSub("*") != g.getPosSub("*")]
        self.assertEqual(different, [])

    def test_names_and_weight(self):
        font = self.bold
        self.assertEqual((font.fontname, font.fullname, font.os2_weight, font.os2_stylemap),
                         (make_bold.FONTNAME, make_bold.FULLNAME, make_bold.WEIGHT,
                          make_bold.BOLD_BIT))


if __name__ == "__main__":
    unittest.main()
