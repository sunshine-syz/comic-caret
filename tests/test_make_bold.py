"""Tests for tools/make_bold.py: the bold is the regular with its strokes thickened, and
nothing else.

Run: python3 -m unittest discover tests
"""
import math
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lig_geometry as geo
import make_bold
from add_ligatures import GENERATED
from make_bold import BOLDER, PEN, SHARED
from measure import area, ink, length, outline, pieces, spans_at_y, vertical_edges
from project import ADVANCE, BOLD_SFD, OVERLAP, ROOT, ROUNDING, SFD, SYMBOL_SIDE, is_alphanumeric
from sfd_files import differences

THREE_END = re.compile(r".+\.tight_[lr]2")  # the outer glyph of a tightened three

GENERATOR = ROOT / "tools" / "make_bold.py"
# The pieces cut flat at both sides of the cell, which a row of them joins at.
THROUGH_PIECES = ("hyphen.mid", "equal.mid", "greater.shaft", "less.shaft", "uni23AF")
# Known exception to how far a part may move up or down: ΅'s dieresis moves 29 down, below
# the tonos that the turned pen grows into it, as there is no room above the line box. ΐ ΰ,
# built on ΅, are rare enough that their dieresis may sit that far below ϊ ϋ's.
MOVED_FURTHER = {("dieresistonos", "dieresis")}
# Known exceptions to an outline keeping the regular's counters: the pen is wider than the
# narrow wedges of ₦ (39 and 47 wide in the regular) and of ₩'s V's (24 to 29), and shuts them;
# ₩'s white between its bars narrows from 53-57 to 13-17. Maple Mono Bold's close as far: ₩'s to
# 10-16, ₦'s to 20-22. They keep their pieces.
SHUT_COUNTERS = ("uni20A6", "uni20A9")
# Known exception to how far an outline may grow up: ⇪'s ⇧, the bold ⇧ lifted clear of its bar
# (make_bold.LIFTED), which grows round, as heavy as ⇧'s shaft walls. It rises by no more than
# the pens grew the two toward each other, the round bar's reach up and ⇧'s down, past what
# the pen grows ⇧ itself.
LIFTED_FURTHER = ("uni21EA",)
# Known exception to how far an outline may grow across: ->> <<-'s inner head, which moves
# along its shaft, away from the outer head, until the white between them is Fira Code Bold's
# (make_bold.HEADS_APART). It moves no further than the pen's width past what the pen grows it.
HEADS_FURTHER = ("greater.twohead", "less.twohead")
# How heavy | and ¦ are against I's stem, each across its middle: from Fira Code Bold's 0.896,
# the least of the reference bolds, to Monaspace Radon Bold's 1.112, the most (Intel One Mono's
# 0.903, Maple Mono's 1.000, Monaspace Neon's 1.003).
BAR_TO_STEM = (0.896, 1.112)


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
        font.createChar(-1, "colon.eq").width = ADVANCE
        self.assertEqual(make_bold.classify(font)["colon.eq"], BOLDER)
        font.createChar(-1, "mystery").width = ADVANCE
        with self.assertRaisesRegex(SystemExit, "mystery"):
            make_bold.classify(font)

    def test_tonos_is_the_acute_turned(self):
        # The bold turns the tonos's pen by TURNED's angle, so it grows the tonos as the bold
        # acute turned only while the regular draws the tonos as the acute turned by as much.
        font = fontforge.open(str(SFD))
        acute, tonos = font["acute"].foreground.dup(), font["tonos"].foreground.dup()
        x0, y0, x1, y1 = acute.boundingBox()
        acute.transform(geo.about(psMat.rotate(make_bold.TURNED["tonos"]),
                                  (x0 + x1) / 2, (y0 + y1) / 2))
        for layer in (acute, tonos):
            layer.addExtrema("all")  # so the box reaches the curves, not their control points
        (a0, b0, a1, b1), (t0, u0, t1, u1) = acute.boundingBox(), tonos.boundingBox()
        # The tonos is the turned acute on whole units: rounding moves each point at most half a
        # unit each way, so each side of the box at most half a unit, and the width and height
        # within ROUNDING. They tell the angle.
        self.assertAlmostEqual(t1 - t0, a1 - a0, delta=ROUNDING)
        self.assertAlmostEqual(u1 - u0, b1 - b0, delta=ROUNDING)
        # Turning keeps the area, which tells the stroke. Rounding moves the edge at most half a
        # unit's diagonal, so the area within that times the outline's length.
        self.assertAlmostEqual(area(tonos), area(acute), delta=length(acute) * math.sqrt(0.5))


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
        scratch_font = fontforge.font()
        scratch = scratch_font.createChar(-1, "scratch")

        def drawn(font, name):
            # Rounded as the bold rounds a part it unlinks, scaled off the grid (◉'s dot): with
            # a glyph's round(), which rounds a control point's offset from its point, not the
            # control point itself (docs/fontforge-pitfalls.md).
            scratch.foreground = ink(font, name)
            scratch.round()
            return outline(scratch.foreground)
        changed = [name for name in self.of_class(SHARED)
                   if drawn(self.bold, name) != drawn(self.regular, name)]
        self.assertEqual(changed, [])

    def test_anchors_carry_over(self):
        # The marks' anchors place them in shaped text as the regular does; the bold moves none.
        moved = {g.glyphname: (self.bold[g.glyphname].anchorPoints, g.anchorPoints)
                 for g in self.regular.glyphs()
                 if sorted(self.bold[g.glyphname].anchorPoints) != sorted(g.anchorPoints)}
        self.assertEqual(moved, {})

    def test_bolder_glyphs_have_more_ink(self):
        # Parts included: a bolder glyph built on a shared one grows too.
        thinner = {}
        for name in self.of_class(BOLDER):
            found, regular = (area(ink(font, name)) for font in (self.bold, self.regular))
            if not regular:
                continue
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
        side, a level stroke half its height; ⇪'s top further (LIFTED_FURTHER), and ->> <<-'s
        inner head along its shaft (HEADS_FURTHER). Covers a trim or an overlap removal that
        failed and left its box, and a condensed outline, which takes in each side by at most
        the pen it then grows by."""
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
            if axis == 0 and name in HEADS_FURTHER:
                shaft = 0 if regular.boundingBox()[0] < 0 else 1  # the side it runs on into
                limits[shaft] += PEN[0]
            box, regular_box = bold.boundingBox(), regular.boundingBox()
            if any(abs(box[side] - regular_box[side]) > limit
                   for side, limit in zip((axis, axis + 2), limits, strict=True)):
                found[name] = (box, regular_box)
        return found

    def test_bolder_glyphs_keep_their_pieces_and_counters(self):
        # The pen joins no two pieces, splits none, and opens no white: a notch whose mouth it
        # shut would be a new counter. Nor does it shut a counter, but the narrow ones
        # SHUT_COUNTERS names. The regular's outline is united first, as the bold's parts are.
        def count(layer):
            return (sum(c.isClockwise() for c in layer),
                    sum(not c.isClockwise() for c in layer))
        changed = {}
        for name in self.of_class(BOLDER):
            bold, regular = self.outlines(name)
            if not len(regular):
                continue
            (pieces, counters), (was_pieces, was_counters) = count(bold), count(geo.union(regular))
            shut = name in SHUT_COUNTERS and counters < was_counters
            if pieces != was_pieces or (counters != was_counters and not shut):
                changed[name] = ((pieces, counters), (was_pieces, was_counters))
        self.assertEqual(changed, {})

    def test_bolder_glyphs_grow_no_taller_than_the_pen(self):
        # So a bold letter keeps the regular's rows.
        self.assertEqual(self.outgrown(1), {})

    def test_bolder_glyphs_grow_no_wider_than_the_pen(self):
        self.assertEqual(self.outgrown(0), {})

    def test_bars_are_as_heavy_against_the_stems_as_the_reference_bolds(self):
        # The regular draws | lighter than its stems, and a pen that grows every stroke alike
        # would leave the bold || thin beside I|l.
        def weights(name):
            """Each piece's stroke across its middle."""
            found = []
            for piece in pieces(ink(self.bold, name)):
                _, y0, _, y1 = piece.boundingBox()
                [(x0, x1)] = spans_at_y(piece, (y0 + y1) / 2)
                found.append(x1 - x0)
            return found
        [stem] = weights("I")
        low, high = BAR_TO_STEM
        for name in ("bar", "brokenbar"):
            with self.subTest(glyph=name):
                for weight in weights(name):
                    self.assertGreaterEqual(weight / stem, low)
                    self.assertLessEqual(weight / stem, high)

    def test_bitcoin_ticks_keep_the_regulars_white(self):
        # |'s pen grows ₿'s ticks toward each other, which would all but join them; they stand
        # apart as in the regular, so ₿ keeps two ticks at 12 px.
        def whites(font):
            _, foot, _, top = font["B"].boundingBox()
            _, y0, _, y1 = font["uni20BF"].boundingBox()
            found = []
            for y in ((top + y1) / 2, (y0 + foot) / 2):
                (_, a), (b, _) = spans_at_y(font["uni20BF"].foreground, y)
                found.append(b - a)
            return found
        for bold, regular in zip(whites(self.bold), whites(self.regular), strict=True):
            self.assertGreaterEqual(bold, regular - ROUNDING)

    def test_per_mille_and_percent_slashes_grow_by_the_pen(self):
        # ‰'s slash shortens until it clears the zero under it (make_bold.SLASHES). Shortened
        # along its length, it keeps its weight, so the pen grows it as it grows %'s: square to
        # its slant, by the reach both ways of the pen turned with it.
        def weight(font, name):
            """The slash's stroke square to its slant at its middle, and the slant."""
            slash = max(pieces(ink(font, name)),
                        key=lambda piece: piece.boundingBox()[3] - piece.boundingBox()[1])
            _, y0, _, y1 = slash.boundingBox()
            [low], [middle], [high] = (spans_at_y(slash, y0 + t * (y1 - y0))
                                       for t in (0.3, 0.5, 0.7))
            slant = math.atan2(0.4 * (y1 - y0), (sum(high) - sum(low)) / 2)
            return (middle[1] - middle[0]) * math.sin(slant), slant
        for name in ("percent", "perthousand"):
            with self.subTest(glyph=name):
                (bold, slant), (regular, _) = weight(self.bold, name), weight(self.regular, name)
                pen = 2 * make_bold.reach((*PEN, slant))[1]
                self.assertAlmostEqual(bold - regular, pen, delta=ROUNDING)

    def test_symbols_keep_their_side_room(self):
        # Each glyph but the letters and figures keeps the room from the cell's sides the
        # regular gives it, down to SYMBOL_SIDE, so two side by side keep twice that between
        # them (tests/test_symbols.py). The letterlike symbols, ℓ ℹ among them, count as
        # symbols, but Ω K Å, which are letters (project.is_alphanumeric()). A letter or figure,
        # as the cell is drawn round its stems, keeps to the cell or its overhang, as
        # tests/test_sanity.py holds it.
        side = SYMBOL_SIDE
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
                    or not len(glyph.foreground)):
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
        # shows. Its round ends past the cell, as <='s tips and <|'s point, grow like any stroke,
        # but for a tightened glyph's side toward its partner, which moves back to where the
        # regular's stands (make_bold.TIGHT). A three's outer glyph moves back past it, by what
        # the pen grows its unmoved middle neighbour, a copy of its own glyph, toward it.
        wrong, cut = {}, set()
        for name in self.of_class(BOLDER):
            if not (GENERATED.fullmatch(name) or name == "uni23AF"):
                continue
            regular, found = ink(self.regular, name), ink(self.bold, name)
            if not len(regular):
                continue
            x0, _, x1, _ = regular.boundingBox()
            flat = {x for x, *_ in vertical_edges(regular)}
            ends = ((0, x0, x0 < 0, -OVERLAP, -1), (2, x1, x1 > ADVANCE, ADVANCE + OVERLAP, 1))
            for side, x, past, seam, outward in ends:
                grown = found.boundingBox()[side]
                if x == seam and x in flat:
                    cut.add((name, side))
                    if grown != x:
                        wrong[name, side] = (grown, x)
                elif name in make_bold.TIGHT and outward == -make_bold.TIGHT[name][0][0]:
                    beyond = 0
                    if THREE_END.fullmatch(name):
                        middle = name.split(".")[0]
                        r0, _, r1, _ = ink(self.regular, middle).boundingBox()
                        b0, _, b1, _ = ink(self.bold, middle).boundingBox()
                        beyond = r0 - b0 if outward > 0 else b1 - r1
                    if abs(grown - (x - outward * beyond)) > ROUNDING:
                        wrong[name, side] = (grown, x)
                elif past and outward * (grown - x) < ROUNDING:
                    wrong[name, side] = (grown, x)
        self.assertLessEqual({(name, side) for name in THROUGH_PIECES for side in (0, 2)}, cut)
        self.assertEqual(wrong, {})

    def test_references_and_lookups_carry_over(self):
        # Every glyph keeps the regular's references but those the bold draws as its outline
        # (make_bold.unlinked_parts()), each turned and scaled as in the regular. A part may
        # move, out of the line box's top, into the cell, or clear of a part or a letter the
        # pen grew it into, by no more than the pen grew the two toward each other, and a unit
        # of rounding: the wider of the part's pen and the full pen across (|'s is wider), and
        # up or down, the part's pen's reach and a full pen's (make_bold.reach()).
        pens = make_bold.pens(self.regular)

        def listed(glyph):
            return sorted((name, tuple(matrix)) for name, matrix, *_ in glyph.references)

        def moved_too_far(glyph, found, expected):
            for (part, m), (_, e) in zip(found, expected, strict=True):
                pen = make_bold.pen_of(part, pens)
                up = make_bold.reach(pen)[1] + PEN[1] / 2
                if (glyph, part) in MOVED_FURTHER:
                    up = PEN[0]
                across = max(pen[0], PEN[0])
                if abs(m[4] - e[4]) > across + ROUNDING or abs(m[5] - e[5]) > up + ROUNDING:
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
