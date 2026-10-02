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
import lig_geometry as geo
import make_bold
from add_ligatures import GENERATED
from make_bold import BOLDER, PEN, SHARED
from measure import area, bullet_side, ink, vertical_edges
from project import ADVANCE, BOLD_SFD, ROOT, ROUNDING, SFD, is_alphanumeric
from sfd_files import differences

GENERATOR = ROOT / "tools" / "make_bold.py"
# The pieces cut flat at both sides of the cell, which a row of them joins at.
THROUGH_PIECES = ("hyphen.mid", "equal.mid", "greater.shaft", "less.shaft", "uni23AF")
# Known exception to how far a part may move up or down: ΅'s dieresis moves 29 down, below
# the tonos that the turned pen grows into it, as there is no room above the line box. ΐ ΰ,
# built on ΅, are rare enough that their dieresis may sit that far below ϊ ϋ's.
MOVED_FURTHER = {("dieresistonos", "dieresis")}
# Known exceptions to a letter's bound being the cell: ∆ and ₫, symbols, hold Δ and đ where
# they stand, so the two keep the symbols' side room (make_bold.side_bounds()).
HELD_BY_SYMBOLS = {"uni0394": "∆", "dcroat": "₫"}
# Known exception to how far an outline may grow up: ⇪'s ⇧, the bold ⇧ lifted clear of its bar
# (make_bold.LIFTED), which grows round, as heavy as ⇧'s shaft walls. It rises by no more than
# the pens grew the two toward each other, the round bar's reach up and ⇧'s down, past what
# the pen grows ⇧ itself.
LIFTED_FURTHER = ("uni21EA",)


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

    def outlines(self, name):
        """The bold glyph's own outline, and the regular's it grew from: the glyph's own, with
        the parts the bold drew into it where the regular places them. A part the bold keeps
        as a reference grows as its own glyph, wherever the bold moves it."""
        kept = {part for part, *_ in self.bold[name].references}
        regular = self.regular[name].foreground.dup()
        for part, matrix, *_ in self.regular[name].references:
            if part not in kept:
                regular += geo.transformed(ink(self.regular, part), matrix)
        return self.bold[name].foreground, regular

    def outgrown(self, axis):
        """{name: (bold box, regular box)} for each bolder glyph whose outline reaches past
        the regular's it grew from, along `axis` (0 across, 1 up and down), by more than its
        pen's reach (make_bold.pen_of(): the small parts' is lighter, the heavy marks' heavier,
        the tonos's turned) and a unit of rounding: a stem grows half the pen's width on each
        side, a level stroke half its height; ⇪'s top further (LIFTED_FURTHER). Covers a trim
        or an overlap removal that failed
        and left its box, and a condensed outline, which takes in each side by at most the pen
        it then grows by."""
        pens = make_bold.pens(self.regular)
        found = {}
        for name in self.of_class(BOLDER):
            bold, regular = self.outlines(name)
            if not len(regular):
                continue
            pen = make_bold.pen_of(name, pens)
            limits = [make_bold.reach(pen)[axis] + ROUNDING] * 2  # one side, then the other
            if axis == 1 and name in LIFTED_FURTHER:
                level = make_bold.reach((*PEN, 0))[1]
                limits[1] = 2 * level + make_bold.reach(pen)[1] + ROUNDING
            box, regular_box = bold.boundingBox(), regular.boundingBox()
            if any(abs(box[side] - regular_box[side]) > limit
                   for side, limit in zip((axis, axis + 2), limits, strict=True)):
                found[name] = (box, regular_box)
        return found

    def test_bolder_glyphs_grow_no_taller_than_the_pen(self):
        # So a bold letter keeps the regular's rows.
        self.assertEqual(self.outgrown(1), {})

    def test_bolder_glyphs_grow_no_wider_than_the_pen(self):
        self.assertEqual(self.outgrown(0), {})

    def test_symbols_keep_their_side_room(self):
        # Each glyph but the letters and figures keeps the room from the cell's sides the
        # regular gives it, down to ●'s side, so two side by side stay as far apart as ●●
        # (tests/test_symbols.py). The letterlike symbols, ℓ ℹ among them, count as symbols, but
        # Ω K Å, which are letters (project.is_alphanumeric()). A letter or figure, as the cell
        # is drawn round its stems, keeps to the cell or its overhang, as tests/test_sanity.py
        # holds it.
        side = bullet_side(self.regular)
        wrong = {}
        for glyph in self.regular.glyphs():
            if is_alphanumeric(code := glyph.unicode) or code < 0:
                continue
            x0, _, x1, _ = glyph.boundingBox()
            b0, _, b1, _ = self.bold[glyph.glyphname].boundingBox()
            if b0 < min(x0, side) or b1 > max(x1, ADVANCE - side):
                wrong[glyph.glyphname] = ((b0, b1), (x0, x1))
        self.assertEqual(wrong, {})

    def test_letters_condense_only_to_keep_the_cell(self):
        # A letter or figure grows its pen's whole width, but where that would take it past the
        # cell, or its regular overhang, and there it is condensed to just touch it. A symbol
        # built on it, as Ω (U+2126) is on Ω (U+03A9), doesn't narrow it further.
        pens = make_bold.pens(self.regular)
        wrong = {}
        for name in self.of_class(BOLDER):
            glyph = self.regular[name]
            if (not is_alphanumeric(glyph.unicode) or glyph.references
                    or not len(glyph.foreground) or name in HELD_BY_SYMBOLS):
                continue
            x0, _, x1, _ = glyph.foreground.boundingBox()
            b0, _, b1, _ = self.bold[name].foreground.boundingBox()
            across = make_bold.reach(make_bold.pen_of(name, pens))[0]
            condensed = (b1 - b0) < (x1 - x0) + 2 * (across - ROUNDING)
            if condensed and b0 > min(x0, 0) + ROUNDING and b1 < max(x1, ADVANCE) - ROUNDING:
                wrong[name] = ((b0, b1), (x0, x1))
        self.assertEqual(wrong, {})

    def test_pieces_keep_their_overlap(self):
        # A ligature piece cut flat past the cell, where it overlaps the next piece, ends at the
        # same line as the regular's, so the seams keep their overlap and no rounded corner
        # shows. Its round ends, as <='s tips, grow like any stroke.
        wrong, cut = {}, set()
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
                cut.add((name, side))
                if found.boundingBox()[side] != x:
                    wrong[name, side] = (found.boundingBox()[side], x)
        self.assertLessEqual({(name, side) for name in THROUGH_PIECES for side in (0, 2)}, cut)
        self.assertEqual(wrong, {})

    def test_references_and_lookups_carry_over(self):
        # Every glyph keeps the regular's references but those the bold draws as its outline
        # (make_bold.unlinked_parts()), each turned and scaled as in the regular. A part may
        # move, out of the line box's top, into the cell, or clear of a part or a letter the
        # pen grew it into, by no more than the pen grew the two toward each other, and a unit
        # of rounding: the pen's width across, and up or down, the part's pen's reach and a
        # full pen's (make_bold.reach()).
        pens = make_bold.pens(self.regular)

        def listed(glyph):
            return sorted((name, tuple(matrix)) for name, matrix, *_ in glyph.references)

        def moved_too_far(glyph, found, expected):
            for (part, m), (_, e) in zip(found, expected, strict=True):
                up = make_bold.reach(make_bold.pen_of(part, pens))[1] + PEN[1] / 2
                if (glyph, part) in MOVED_FURTHER:
                    up = PEN[0]
                if abs(m[4] - e[4]) > PEN[0] + ROUNDING or abs(m[5] - e[5]) > up + ROUNDING:
                    return True
            return False
        wrong = {}
        for glyph in self.regular.glyphs():
            name = glyph.glyphname
            unlinked = make_bold.unlinked_parts(glyph, self.classes)
            expected = [ref for ref in listed(glyph) if ref[0] not in unlinked]
            found = listed(self.bold[name])
            if ([(part, m[:4]) for part, m in found] != [(part, m[:4]) for part, m in expected]
                    or moved_too_far(name, found, expected)):
                wrong[name] = (found, expected)
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
