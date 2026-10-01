"""Tests for tools/render_specimen.py. Needs HarfBuzz and the built fonts (./build.sh).

Run: python3 -m unittest discover tests
"""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import render_specimen
from add_ligatures import GENERATED
from project import ADVANCE, ROOT, stale_build
from render_specimen import (
    CODE,
    IMAGES,
    ITALIC,
    LIGATURES,
    OUT,
    WIDTH,
    Layout,
    glyphs,
    highlighted,
    italicized,
    marked,
    ruled,
    shape,
)


def style(svg):
    return svg.split("<style>", 1)[1].split("</style>", 1)[0]


def placed(svg):
    """(x, baseline, scale, class or None) of each glyph the SVG draws."""
    found = re.findall(r'translate\(([-\d.]+) ([-\d.]+)\) scale\(([\d.]+)\)"(?: class="(\w+)")?',
                       svg)
    return [(float(x), float(y), float(scale), name or None) for x, y, scale, name in found]


def ligated(text):
    return any(GENERATED.fullmatch(glyph["g"]) for glyph in shape(text, "calt"))


class GlyphsTest(unittest.TestCase):
    def test_paths_are_in_whole_font_units(self):
        [(path, cell, cluster)] = glyphs("H", False)
        self.assertRegex(path, r"^M -?\d")
        self.assertNotRegex(path, r"\d\.\d")
        self.assertEqual((cell, cluster), (0, 0))

    def test_blank_glyphs_are_left_out(self):
        self.assertEqual(glyphs(" ", False), [])
        self.assertEqual([(cell, cluster) for _, cell, cluster in glyphs("a b", False)],
                         [(0, 0), (2, 2)])

    def test_ligatures_form_only_with_calt_and_keep_their_cells(self):
        on, off = glyphs("->", True), glyphs("->", False)
        self.assertNotEqual([path for path, *_ in on], [path for path, *_ in off])
        self.assertEqual([cell for _, cell, _ in on], [0, 1])

    def test_a_missing_glyph_is_an_error(self):
        with self.assertRaises(ValueError):
            glyphs("a字", False)  # no CJK in the font

    def test_a_combining_mark_is_an_error(self):
        with self.assertRaisesRegex(ValueError, r"q\u0301.*q\u0301"):
            glyphs("q\u0301", False)


class LayoutTest(unittest.TestCase):
    def test_each_glyph_is_defined_once_and_drawn_where_placed(self):
        layout = Layout()
        layout.line(10, 50, "HH H", 20)
        svg = layout.svg(100)
        self.assertEqual(svg.count("<path "), 1)
        self.assertEqual([(x, y) for x, y, *_ in placed(svg)], [(10, 50), (21, 50), (43, 50)])

    def test_gap_spaces_out_the_cells(self):
        layout = Layout()
        layout.line(0, 20, "HH", 20, gap=5)
        self.assertEqual([x for x, *_ in placed(layout.svg(40))], [0, 16])

    def test_classes_color_glyphs_by_character(self):
        layout = Layout()
        layout.spans(0, 20, [("green", "✔"), (None, " ok")], 18)
        svg = layout.svg(40)
        self.assertEqual([name for *_, name in placed(svg)], ["green", None, None])
        light, dark = render_specimen.COLORS["green"]
        self.assertIn(f".green{{fill:{light}}}", style(svg))
        self.assertIn(f".green{{fill:{dark}}}", style(svg))
        self.assertNotIn(".red", style(svg))

    def test_styled_draws_each_character_in_its_style(self):
        # The italic's H is the regular's slanted: another path, at the same cell.
        layout = Layout()
        layout.styled(0, 20, "HH", 20, [False, True])
        svg = layout.svg(40)
        self.assertEqual(svg.count("<path "), 2)
        self.assertEqual([x for x, *_ in placed(svg)], [0, 11])
        [regular] = [path for path, *_ in glyphs("H", False)]
        [slanted] = [path for path, *_ in glyphs("H", False, ITALIC)]
        self.assertNotEqual(regular, slanted)
        self.assertIn(regular, svg)
        self.assertIn(slanted, svg)

    def test_colors_follow_the_viewers_scheme(self):
        css = style(Layout().svg(10))
        light, dark = css.split("@media (prefers-color-scheme:dark)")
        self.assertIn(f"svg{{fill:{render_specimen.LIGHT}}}", light)
        self.assertIn(f"svg{{fill:{render_specimen.DARK}}}", dark)

    def test_marks_split_into_spans(self):
        self.assertEqual(marked("{green:❯} cargo {muted:on}"),
                         [("green", "❯"), (None, " cargo "), ("muted", "on")])
        self.assertEqual(ruled("│ Łódź │ ▂▄ │"),
                         [("muted", "│"), (None, " Łódź "), ("muted", "│"), (None, " ▂▄ "),
                          ("muted", "│")])


class HighlightTest(unittest.TestCase):
    def test_each_character_takes_its_tokens_class(self):
        line = 'export const f = (u: User) => g("x", 7); // done'

        def classes_of(snippet):
            start = line.index(snippet)
            return highlighted(line)[start:start + len(snippet)]

        self.assertEqual(classes_of("export const f"), ["keyword"] * 6 + [None] + ["keyword"] * 5
                         + [None] * 2)
        self.assertEqual(classes_of("User)"), ["type"] * 4 + [None])
        self.assertEqual(classes_of('g("x", 7)'),
                         ["function", None] + ["string"] * 3 + [None] * 2 + ["number", None])
        self.assertEqual(classes_of("// done"), ["comment"] * 7)

    def test_comments_and_keywords_are_italicized(self):
        line = 'export const f = g(7); // done'
        self.assertEqual(italicized(line),
                         [True] * 6 + [False] + [True] * 5 + [False] * 11 + [True] * 7)


class ImageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svgs = {name: draw() for name, draw in IMAGES.items()}

    def test_glyphs_stay_inside_the_image(self):
        for name, svg in self.svgs.items():
            width, height = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
            self.assertEqual(width, WIDTH)
            for x, y, scale, _ in placed(svg):
                with self.subTest(image=name, x=x, y=y):
                    self.assertGreaterEqual(x, 0)
                    self.assertLessEqual(x + ADVANCE * scale, width)
                    self.assertLessEqual(y, height)

    def test_every_sequence_shown_is_a_ligature(self):
        for label, sequences in LIGATURES:
            for sequence in sequences:
                with self.subTest(group=label, sequence=sequence):
                    self.assertTrue(ligated(sequence))

    def test_the_code_uses_ligatures(self):
        self.assertTrue(any(ligated(line) for line in CODE if line))

    def test_the_committed_images_are_current(self):
        # The bytes depend on the toolchain as well: another FontForge, HarfBuzz or cairo
        # (hb-view's SVG output) can move a point by a unit, so the images are rendered with
        # the one that builds the release.
        if reason := stale_build(formats=("ttf",)):
            self.skipTest(reason)
        rerun = "rerun python3 tools/render_specimen.py"
        for name, svg in self.svgs.items():
            image = OUT / f"{name}.svg"
            with self.subTest(image=name):
                self.assertTrue(image.exists(), f"{image.relative_to(ROOT)} is missing; {rerun}")
                self.assertTrue(image.read_bytes() == svg.encode("utf-8"),
                                f"{image.relative_to(ROOT)} differs from a fresh render "
                                f"(a glyph or toolchain change); {rerun}")


if __name__ == "__main__":
    unittest.main()
