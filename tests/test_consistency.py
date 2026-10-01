"""Rules whole classes of glyphs share: where they sit in the line and the cell, and how they
are built from other glyphs.

Run: python3 -m unittest discover tests

Each rule covers every glyph of its class, so a glyph added to one is checked without a new
test. Known exceptions are listed here with their reasons.
"""
import collections
import itertools
import math
import pathlib
import statistics
import sys
import unicodedata
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import add_box_drawing
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

LETTER = {"Lu", "Ll", "Lt", "Lo"}  # not Lm: ˆ ˇ are modifier letters, and marks here

# The characters whose bottom (1) or top (3) edge lies on each row.
ROWS = {
    "baseline": (("ABCDEFGHIJKLMNOPRSTUVWXYZÆŒÐÞŁĦŦǷẞØĐĲĿꝚabcdefhiklmnorstuvwxzıĸß0123456789"
                  "¼½¾⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞æœðøđħŀłŧſꝛ"
                  "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαδεθικλνοπστυω₽₩₦₱ℓ"), 1),
    "x-height": ("acemnorsuvwxzıĸµŋæœøȷꝛαγεηικνοπρσςτυφχψω", 3),
    "cap height": (("ABCDEFGHIJKLMNOPQRSTUVWXYZÆŒÐÞŁŊǷẞØĐĲĿꝚ0123456789¼½¾™⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞"
                    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩϏ₹₽₩₦₱"), 3),
    "ascender": ("bdfhklßþðđħŀłſβδζθλξℓ", 3),
    "descender": ("gjpqyþµŋŊƒĳȷƿ¶βγζηξρςφχψϗ", 1),
    "superscript": ("¹²³⁰⁴⁵⁶⁷⁸⁹", 3),
    "superscript baseline": ("¹²³⁰⁴⁵⁶⁷⁸⁹ⁱⁿ", 1),
    "subscript": ("₀₁₂₃₄₅₆₇₈₉", 3),
}
# How far a glyph may stray from its row's median: round letters overshoot by up to 25 (C, 9).
ROW_TOLERANCE = 30
OFF_ROW = {
    ("cap height", "Þ"),  # its stem rises 88 past cap height
    # The slash runs 45 past the bowl at both ends; Fira Code's and Intel One Mono's run
    # further (57 and more), Maple Mono's less (7 to 25).
    ("baseline", "Ø"), ("cap height", "Ø"), ("baseline", "ø"), ("x-height", "ø"),
    # Where a's foot meets e's bowl it dips 26 lower than o; the references' æ go no lower
    # than their o.
    ("baseline", "æ"),
}

# Symmetric glyphs; the brackets, which the legibility pass centered; the figures, and the
# small ones of the superscripts and subscripts, which stand in the middle of the cell like
# them; the spacing accents and low quotes, which Fira Code centers too; and the symbols,
# which the reference fonts center by their ink box.
CENTERED = ("AHIMNOSTUVWXYZosvwxz08!¡|:.'\"*+-=^~_×÷±−≠≈≡∞↔↕↖↗↘↙⇔✗#%…/\\()[]{}╳•°₩₦№"
            "ΑΔΗΘΙΛΜΝΞΟΠΤΥΦΧΨΩοθυφχψω⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼₀₁₂₃₄₅₆₇₈₉₊₋₌∆∇∏∫◊∅″‖⟨⟩"
            "✕✖✘⇕○●◉▷▶▹▸►◀◁◂◃◄▲△▴▵▼▽▾▿◇◆☆★☐☒⚠ℹ⋯⋮"
            "✢✳✶✻✽⏵⏸⏺⧉∴※◯■□▪▫◦❰❱⌘⌥⌃⇧⌫⌦⎋⏎␣⍽↹⇥⇤↵↩↪↳↲↰↱⇑⇓⇦⇨⇩⇪"
            "◐◑◒◓◴◵◶◷◠◡◰◱◲◳▮▯◎⊙⦾⦿◌◍⧆⧇☰☱☲☳☴☵☶☷✷✸✹✺⊶⊷☖☗▰▱∙‼"
            "·¤¦†‡©®↑↓⇡⇣‚„΄΅´¨¯¸˘˙˚˜˝ˆˇ")
# Centered on the hyphen, as the ligatures join them; the symbols line up with them.
ON_AXIS = ("+−=±×÷≠≈≡~<>≤≥←→↔↖↗↘↙⇐⇒⇔↦•◦"
           "✕✖❯❮➜○●◉∅▷▶▹▸►◀◁◂◃◄▲△▴▵▼▽▾▿◇◆☆★☐☒⋯⋮"
           "✢✳✶✻✽⏵⏸⏺⧉※◯■□▪▫❰❱⌘⌥⇧⌫⌦⎋⏎↹⇥⇤⇦⇨⇩"
           "◐◑◒◓◴◵◶◷◰◱◲◳◢◣◤◥▮▯◎⊙⦾⦿◌◍⧆⧇☰☱☲☳☴☵☶☷✷✸✹✺⊶⊷☖☗▰▱∙–—∞")
# The <= >= ligatures, by glyph name: centred on the axis like ≤ ≥, as the references' are.
ON_AXIS_GLYPHS = ("less_equal.liga", "greater_equal.liga")
# The superscript and subscript signs, on the middle of their small figures, as in both
# references that have them.
SMALL_ON_AXIS = {"¹": "⁺⁻⁼⁽⁾", "₁": "₊₋₌₍₎"}
MIRRORED = ("<>", "≤≥", "←→", "⇐⇒", "↖↗", "«»", "‹›", "/\\", "╱╲", "❮❯", "❰❱", "◀▶", "◁▷", "◂▸", "◃▹",
            "◄►", "⇤⇥", "↲↳", "↰↱", "↩↪", "⌫⌦", "⁽⁾", "₍₎", "⟨⟩", "⇦⇨", "◣◢", "◜◝", "◟◞",
            "⊶⊷")
TOLERANCE = 10  # for centering and mirroring; the hand's wobble stays within it
ROUNDING = 1  # an outline's points and a reference's offset are each rounded to whole units
# Left glyphs of MIRRORED that are their right one mirrored exactly, as an outline, since
# validate() flags a mirrored reference.
MIRRORED_OUTLINES = "❮❰◀◁◂◃◄⇤↲↩⌫◣"

# Case pairs whose marks differ by design: ď ť take an apostrophe-like caron, and ģ a turned
# comma above where Ģ has one below.
OWN_ACCENTS = {"dcaron", "tcaron", "gcommaaccent"}
MERGED_BELOW = 10  # a merged ogonek or cedilla lies below this height or inside its letter
MARK_CLEARANCE = 20  # the closest a mark may come to its letter
# Marks above sit on their letter's middle within TOLERANCE, as the references' symmetric marks
# over A O U do (within 4). Ĉ's circumflex leans 22 toward C's open side, and may go as far as
# the references' over C, the edge of the range the three cover: Fira Code's 46 with x scaled
# to our advance (Intel One Mono's 28, Maple Mono's 2).
OFF_CENTER = {"Ccircumflex": 46}
STEM_BASES = {"dotlessi", "dotlessj", "l"}  # their marks sit over the stem, not the ink's middle
# Accents a letter places by hand away from where its anchor puts a combining mark. i's anchor
# is over its dot, where ï ĩ ī put theirs: ì's grave leans 38 left of it and í's acute 19
# right, as Intel One Mono's and Maple Mono's lean (27 to 43); î's circumflex sits 20 left,
# toward the flag, where the references keep theirs over the dot (within 6). Ĉ's circumflex
# sits 21 right of the mark, which C's anchor centres on C (OFF_CENTER).
OWN_PLACEMENT = {("dotlessi", "grave.accent"), ("dotlessi", "acute"),
                 ("dotlessi", "circumflex"), ("C", "circumflex")}

BOX_DRAWING = range(0x2500, 0x2580)
BLOCK_ELEMENTS = range(0x2580, 0x25A0)
SIDES = ("left", "right", "down", "up")
# The lines whose profile each weight of line has where it leaves the cell.
LINES = {"light": "─│", "heavy": "━┃", "double": "═║"}
FRACTIONS = {"ONE EIGHTH": 1 / 8, "ONE QUARTER": 1 / 4, "THREE EIGHTHS": 3 / 8, "HALF": 1 / 2,
             "FIVE EIGHTHS": 5 / 8, "THREE QUARTERS": 3 / 4, "SEVEN EIGHTHS": 7 / 8}
SHADES = {"░": 1 / 4, "▒": 1 / 2, "▓": 3 / 4}
BLOCK_TOLERANCE = 1  # eighths of 550 and 1250 units round to whole units
RHYTHM_TOLERANCE = 2  # dashes and shade pixels span fractions of the cell, rounded
SLIVER = 4  # rows and columns thinner than this join pixels that meet at a corner
COVERAGE_TOLERANCE = 0.01  # those joins add 0.7 % to ▒

BRAILLE = range(0x2800, 0x2900)
# Unicode numbers the dots down the left column (1-3), down the right (4-6), then along the
# bottom (7, 8); dot n is bit n - 1 of the pattern's offset from U+2800.
BRAILLE_DOTS = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))  # (column, row)


def open_font():
    return fontforge.open(str(SFD))


def outline(layer):
    """The layer's points, contour by contour, in an order that ignores where each starts."""
    return sorted(sorted((p.x, p.y, p.on_curve) for p in contour) for contour in layer)


def box(font, char):
    return font[ord(char)].boundingBox()


def is_mark(glyph):
    return glyph.unicode >= 0 and unicodedata.category(chr(glyph.unicode)) == "Mn"


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
        for name in ON_AXIS_GLYPHS:
            _, b0, _, b1 = self.font[name].boundingBox()
            if abs((b0 + b1) / 2 - (y0 + y1) / 2) > TOLERANCE:
                off[name] = round((b0 + b1) / 2 - (y0 + y1) / 2)
        self.assertEqual(off, {})

    def test_small_signs_sit_on_their_figures_middle(self):
        off = {}
        for figure, signs in SMALL_ON_AXIS.items():
            _, y0, _, y1 = box(self.font, figure)
            for char in signs:
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

    def test_mirrored_outlines_are_their_pair_mirrored(self):
        for left, right in MIRRORED:
            if left in MIRRORED_OUTLINES:
                with self.subTest(pair=left + right):
                    mirrored = geo.mirrored_x(self.font[ord(right)].foreground, ADVANCE / 2)
                    self.assertEqual(outline(self.font[ord(left)].foreground), outline(mirrored))


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
                if bottom >= top and abs(offset) > OFF_CENTER.get(glyph.glyphname, TOLERANCE):
                    off[(glyph.glyphname, name)] = round(offset)
        self.assertEqual(off, {})

    def test_decomposed_letters_compose(self):
        # ccmp makes e + U+0301 the same é as U+00E9, in shapers that don't compose on their
        # own.
        missing = []
        for glyph in self.font.glyphs():
            parts = unicodedata.normalize("NFD", chr(glyph.unicode)) if glyph.unicode >= 0 else ""
            if len(parts) < 2 or any(ord(c) not in self.font for c in parts):
                continue
            names = tuple(self.font[ord(c)].glyphname for c in parts)
            if not any(kind == "Ligature" and tuple(rest) == names
                       for _, kind, *rest in glyph.getPosSub("*")):
                missing.append(glyph.glyphname)
        self.assertEqual(missing, [])

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


def anchor(glyph, name, kind):
    """(x, y) of the glyph's anchor of class `name` and type `kind`, or None."""
    return next(((x, y) for cls, what, x, y, *_ in glyph.anchorPoints
                 if cls == name and what == kind), None)


class MarkTest(unittest.TestCase):
    """Combining marks draw over the cell, where terminals that don't shape text put them, and
    their anchors carry them onto the glyph before them in shaped text."""

    @classmethod
    def setUpClass(cls):
        cls.font = open_font()
        cls.marks = [g for g in cls.font.glyphs() if is_mark(g)]
        cls.mark_names = {g.glyphname for g in cls.marks}
        cls.side = {g.glyphname: "top" if anchor(g, "top", "mark") else "bottom"
                    for g in cls.marks}

    def placed(self, base, mark):
        """The mark's ink where its anchor puts it on `base`."""
        side = self.side[mark.glyphname]
        (bx, by), (mx, my) = anchor(self.font[base], side, "base"), anchor(mark, side, "mark")
        return geo.transformed(measure.ink(self.font, mark.glyphname),
                               psMat.translate(bx - mx, by - my))

    def test_marks_are_accents_centered_in_the_cell(self):
        # A reference to the spacing accent, so the mark follows its redrawing.
        wrong = {}
        for mark in self.marks:
            x0, _, x1, _ = mark.boundingBox()
            names = [name for name, *_ in mark.references]
            if len(mark.foreground) or len(names) != 1 or names[0] in self.mark_names:
                wrong[mark.glyphname] = "not one reference to an accent"
            elif abs((x0 + x1) / 2 - ADVANCE / 2) > TOLERANCE:
                wrong[mark.glyphname] = round((x0 + x1) / 2 - ADVANCE / 2)
        self.assertEqual(wrong, {})

    def test_every_glyph_takes_marks(self):
        # A mark after a glyph without an anchor would land on the next cell.
        missing = [g.glyphname for g in self.font.glyphs() if g.unicode >= 0
                   and g.glyphname not in self.mark_names
                   and not (anchor(g, "top", "base") and anchor(g, "bottom", "base"))]
        self.assertEqual(missing, [])

    def test_marks_land_where_the_precomposed_letters_put_their_accents(self):
        # So e + U+0301 looks like é even where nothing composes them.
        accent_marks = {}
        for mark in self.marks:
            [(accent, matrix, *_)] = mark.references
            accent_marks[accent] = (mark, matrix)
        off = {}
        for glyph in self.font.glyphs():
            refs = {name: matrix for name, matrix, *_ in glyph.references}
            accents = [name for name in refs if name in accent_marks]
            # Not ΅, which is the tonos, not a letter, over the dieresis.
            letters = [name for name in refs
                       if name not in accent_marks and is_letter(self.font, name)]
            if glyph.unicode < 0 or len(accents) != 1 or len(letters) != 1:
                continue
            (accent,), (letter,) = accents, letters
            if (letter, accent) in OWN_PLACEMENT:
                continue
            mark, _ = accent_marks[accent]
            ax0, ay0, _, _ = self.placed(letter, mark).boundingBox()
            px0, py0, _, _ = geo.transformed(self.font[accent].foreground,
                                             refs[accent]).boundingBox()
            if abs(ax0 - px0) > TOLERANCE or abs(ay0 - py0) > ROW_TOLERANCE:
                off[(glyph.glyphname, mark.glyphname)] = (round(ax0 - px0), round(ay0 - py0))
        self.assertEqual(off, {})

    def test_marks_above_clear_every_letter(self):
        # Letters without a precomposed form too, and ones that already have a mark.
        acute = self.font[0x301]
        close = {}
        for glyph in self.font.glyphs():
            if glyph.unicode < 0 or not is_letter(self.font, glyph.glyphname):
                continue
            mark = self.placed(glyph.glyphname, acute)
            letter = measure.ink(self.font, glyph.glyphname)
            if mark.boundingBox()[1] - letter.boundingBox()[3] >= MARK_CLEARANCE:
                continue
            if (gap := measure.gap(letter, mark)) < MARK_CLEARANCE:
                close[glyph.glyphname] = round(gap)
        self.assertEqual(close, {})


def rounded(spans):
    return [(round(a), round(b)) for a, b in spans]


def merged(spans):
    """Spans sorted, with those that touch joined into one."""
    out = []
    for a, b in sorted(spans):
        if out and a - out[-1][1] < 0.5:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def area(layer):
    """The ink's area, for outlines of straight lines; holes run the other way and subtract."""
    total = 0
    for contour in layer:
        points = [(p.x, p.y) for p in contour]
        total += sum(x0 * y1 - x1 * y0
                     for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]))
    return abs(total) / 2


class BoxDrawingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = open_font()
        cls.bottom, cls.top = cls.font.hhea_descent, cls.font.hhea_ascent

    def ink(self, char):
        return measure.ink(self.font, self.font[ord(char)].glyphname)

    def edges(self, char):
        """The strokes that cross each side of the cell, {side: [(from, to)]}."""
        ink = self.ink(char)
        return {"left": rounded(measure.spans_at_x(ink, 0)),
                "right": rounded(measure.spans_at_x(ink, ADVANCE)),
                "down": rounded(measure.spans_at_y(ink, self.bottom)),
                "up": rounded(measure.spans_at_y(ink, self.top))}

    def profile(self, side, weight):
        horizontal, vertical = LINES[weight]
        return self.edges(horizontal if side in ("left", "right") else vertical)[side]

    def test_lines_leave_the_cell_where_their_names_say(self):
        # Each arm has the profile of ─ ━ ═ or │ ┃ ║ where it leaves the cell, so it joins the
        # line that continues it in the next cell.
        wrong = {}
        for code in BOX_DRAWING:
            words = unicodedata.name(chr(code)).split()[2:]
            if "DASH" in words or "DIAGONAL" in words:
                continue
            named = add_box_drawing.arms([w for w in words if w not in ("AND", "ARC")])
            want = {side: self.profile(side, named[side]) if side in named else []
                    for side in SIDES}
            if (got := self.edges(chr(code))) != want:
                wrong[chr(code)] = got
        self.assertEqual(wrong, {})

    def test_dashes_keep_their_rhythm_across_cells(self):
        # The gap between two cells' dashes matches the gaps inside a cell, and each dash is
        # as thick as the solid line of its weight.
        _, y0, _, y1 = self.font[ord("─")].boundingBox()
        x0, _, x1, _ = self.font[ord("│")].boundingBox()
        wrong = {}
        for code in BOX_DRAWING:
            words = unicodedata.name(chr(code)).split()
            if "DASH" not in words:
                continue
            count = {"DOUBLE": 2, "TRIPLE": 3, "QUADRUPLE": 4}[words[words.index("DASH") - 1]]
            horizontal, vertical = LINES[words[2].lower()]
            ink = self.ink(chr(code))
            if words[-1] == "HORIZONTAL":
                period, dashes = ADVANCE, measure.spans_at_y(ink, (y0 + y1) / 2)
                middle = sum(dashes[0]) / 2
                across = (measure.spans_at_x(ink, middle),
                          measure.spans_at_x(self.ink(horizontal), middle))
            else:
                period, dashes = self.top - self.bottom, measure.spans_at_x(ink, (x0 + x1) / 2)
                middle = sum(dashes[0]) / 2
                across = (measure.spans_at_y(ink, middle),
                          measure.spans_at_y(self.ink(vertical), middle))
            two = dashes + [(a + period, b + period) for a, b in dashes]
            lengths = [b - a for a, b in two]
            gaps = [c - b for (_, b), (c, _) in itertools.pairwise(two)]
            if (len(dashes) != count or max(lengths) - min(lengths) > RHYTHM_TOLERANCE
                    or max(gaps) - min(gaps) > RHYTHM_TOLERANCE or across[0] != across[1]):
                wrong[chr(code)] = (rounded(dashes), rounded(across[0]))
        self.assertEqual(wrong, {})

    def test_diagonals_run_corner_to_corner(self):
        # From corner to corner of the line box, so they continue into their diagonal
        # neighbours: at a quarter, half and three quarters of its height, ╱ crosses a quarter,
        # half and three quarters of the width.
        height = self.top - self.bottom
        off = {}
        for char, directions in {"╱": (1,), "╲": (-1,), "╳": (1, -1)}.items():
            ink = self.ink(char)
            for share in (1 / 4, 1 / 2, 3 / 4):
                centres = sorted((a + b) / 2 for a, b in
                                 measure.spans_at_y(ink, self.bottom + share * height))
                if share == 1 / 2 and len(directions) == 2:
                    centres *= 2  # the strokes of ╳ cross there
                want = sorted(ADVANCE * (share if d > 0 else 1 - share) for d in directions)
                if len(centres) != len(want) or any(
                        abs(got - x) > TOLERANCE for got, x in zip(centres, want)):
                    off[(char, share)] = [round(x) for x in centres]
        self.assertEqual(off, {})


class BlockElementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = open_font()
        cls.bottom, cls.top = cls.font.hhea_descent, cls.font.hhea_ascent

    def ink(self, code):
        return measure.ink(self.font, self.font[code].glyphname)

    def test_blocks_fill_the_part_of_the_cell_their_names_give(self):
        # The cell's width and the line box, split exactly, so bars and graphs line up and
        # neighbouring blocks meet without a seam.
        height = self.top - self.bottom
        middle = (ADVANCE / 2, self.bottom + height / 2)
        wrong = {}
        for code in BLOCK_ELEMENTS:
            name = unicodedata.name(chr(code))
            ink = self.ink(code)
            if name.endswith(" SHADE"):
                continue
            if name.startswith("QUADRANT "):
                named = set(name.removeprefix("QUADRANT ").split(" AND "))
                inked = set()
                for row, y in (("LOWER", middle[1] - height / 4), ("UPPER", middle[1] + height / 4)):
                    for column, x in (("LEFT", ADVANCE / 4), ("RIGHT", 3 * ADVANCE / 4)):
                        if any(a <= x <= b for a, b in measure.spans_at_y(ink, y)):
                            inked.add(f"{row} {column}")
                if inked != named:
                    wrong[chr(code)] = sorted(inked)
                continue
            if name == "FULL BLOCK":
                want = (0, self.bottom, ADVANCE, self.top)
            else:
                side, fraction = name.removesuffix(" BLOCK").split(" ", 1)
                width, tall = FRACTIONS[fraction] * ADVANCE, FRACTIONS[fraction] * height
                want = {"LEFT": (0, self.bottom, width, self.top),
                        "RIGHT": (ADVANCE - width, self.bottom, ADVANCE, self.top),
                        "LOWER": (0, self.bottom, ADVANCE, self.bottom + tall),
                        "UPPER": (0, self.top - tall, ADVANCE, self.top)}[side]
            got = ink.boundingBox()
            if len(ink) != 1 or any(abs(a - b) > BLOCK_TOLERANCE for a, b in zip(got, want)):
                wrong[chr(code)] = (len(ink), got)
        self.assertEqual(wrong, {})

    def test_shades_cover_a_quarter_a_half_and_three_quarters(self):
        cell = ADVANCE * (self.top - self.bottom)
        off = {char: round(coverage, 3) for char, share in SHADES.items()
               if abs((coverage := area(self.ink(ord(char))) / cell) - share) > COVERAGE_TOLERANCE}
        self.assertEqual(off, {})

    def test_shades_tile_without_a_seam(self):
        # Along any row or column, the ink and the gaps that meet or cross the edge between
        # two cells are as long as ones inside a cell.
        height = self.top - self.bottom
        seams = {}
        for char in SHADES:
            ink = self.ink(ord(char))
            points = [p for contour in ink for p in contour]
            # Rows, whose runs repeat every cell width, then columns, every line height.
            for period, spans_at, coordinate in ((ADVANCE, measure.spans_at_y, lambda p: p.y),
                                                 (height, measure.spans_at_x, lambda p: p.x)):
                edges = sorted({coordinate(p) for p in points})
                for a, b in itertools.pairwise(edges):
                    if b - a < SLIVER:
                        continue
                    spans = spans_at(ink, (a + b) / 2)
                    two = merged(spans + [(x0 + period, x1 + period) for x0, x1 in spans])
                    ends = [x for span in two for x in span]
                    runs = list(itertools.pairwise(ends))
                    inside = [y - x for x, y in runs if 0 < x and y < period]
                    for x, y in runs:
                        if x <= period <= y and inside and min(
                                abs(y - x - length) for length in inside) > RHYTHM_TOLERANCE:
                            seams.setdefault(char, []).append((round(x), round(y)))
        self.assertEqual(seams, {})


if __name__ == "__main__":
    unittest.main()
