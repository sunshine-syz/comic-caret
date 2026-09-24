"""Tests for tools/render_specimen.py. Needs HarfBuzz and the built fonts (./build.sh).

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import render_specimen
from add_ligatures import GENERATED
from render_specimen import (IMAGES, LIGATURE_COLUMN, missing_characters, shape, syntax_classes,
                             themed)

CAIRO_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="254.5" height="136" viewBox="0 0 254.5 136">
<defs>
<g id="glyph-0-0">
<path d="M 8.113281 -14.785156 C 9.679688 -0.04 11.75 -14.816406 Z"/>
</g>
</defs>
<g fill="rgb(12.156863%, 13.72549%, 15.686275%)" fill-opacity="1">
<use xlink:href="#glyph-0-0" x="16.03125" y="46.5"/>
<use xlink:href="#glyph-0-0" x="29.2" y="46.5"/>
</g>
</svg>
"""


def style(svg):
    return svg.split("<style>", 1)[1].split("</style>", 1)[0]


class ThemedTest(unittest.TestCase):
    def setUp(self):
        self.svg = themed(CAIRO_SVG)

    def test_glyphs_take_their_color_from_the_stylesheet(self):
        self.assertNotIn("fill=", self.svg)
        light, dark = render_specimen.LIGHT, render_specimen.DARK
        self.assertEqual(style(self.svg), f"svg{{fill:{light}}}"
                                          f"@media (prefers-color-scheme:dark){{svg{{fill:{dark}}}}}")
        self.assertLess(self.svg.index("<svg "), self.svg.index("<style>"))

    def test_coordinates_are_rounded_to_a_tenth(self):
        self.assertIn('d="M 8.1 -14.8 C 9.7 0 11.8 -14.8 Z"', self.svg)
        self.assertIn('x="16" y="46.5"', self.svg)
        self.assertIn('viewBox="0 0 254.5 136"', self.svg)

    def test_leaves_the_xml_declaration_alone(self):
        self.assertTrue(self.svg.startswith('<?xml version="1.0" encoding="UTF-8"?>'))

    def test_classed_glyphs_take_their_syntax_color(self):
        svg = themed(CAIRO_SVG, ["keyword", None])
        self.assertIn('<use class="keyword" xlink:href="#glyph-0-0" x="16"', svg)
        self.assertIn('<use xlink:href="#glyph-0-0" x="29.2"', svg)
        light, dark = render_specimen.SYNTAX_COLORS["keyword"]
        self.assertIn(f".keyword{{fill:{light}}}@media", style(svg))
        self.assertIn(f".keyword{{fill:{dark}}}}}", style(svg))
        self.assertNotIn(".comment", style(svg))

    def test_needs_a_class_for_every_glyph(self):
        with self.assertRaises(ValueError):
            themed(CAIRO_SVG, ["keyword"])


class SyntaxTest(unittest.TestCase):
    def test_each_glyph_takes_its_characters_class(self):
        text, features, syntax = IMAGES["specimen"]
        characters = text.replace("\n", "")
        classes = syntax_classes(text, features, syntax)
        self.assertEqual(len(classes), len(characters))  # ligatures keep a glyph per character

        def classes_of(snippet):
            start = characters.index(snippet)
            return classes[start:start + len(snippet)]

        self.assertEqual(classes_of("use "), ["keyword"] * 3 + [None])
        self.assertEqual(classes_of("// Count"), ["comment"] * 8)
        self.assertEqual(classes_of("fn frequent(text"),
                         ["keyword"] * 2 + [None] + ["function"] * 8 + [None] * 5)
        self.assertEqual(classes_of("usize) -> Vec<"),
                         ["type"] * 5 + [None] * 5 + ["type"] * 3 + [None])
        self.assertEqual(classes_of("HashMap::new()"),
                         ["type"] * 7 + [None] * 2 + ["function"] * 3 + [None] * 2)
        self.assertEqual(classes_of("(0) += 1;"), [None, "number"] + [None] * 5 + ["number", None])


class SampleTest(unittest.TestCase):
    def test_the_font_has_every_sample_character(self):
        for name, (text, *_) in IMAGES.items():
            with self.subTest(image=name):
                self.assertEqual(missing_characters(text), [])

    def test_ligatures_are_off_in_the_left_column_only(self):
        text, features, _ = IMAGES["ligatures"]
        for line in shape(text, features):
            generated = [GENERATED.fullmatch(glyph["g"]) is not None for glyph in line]
            left = [g for glyph, g in zip(line, generated, strict=True)
                    if glyph["cl"] < LIGATURE_COLUMN]
            right = generated[len(left):]
            self.assertFalse(any(left))
            self.assertTrue(any(right))


if __name__ == "__main__":
    unittest.main()
