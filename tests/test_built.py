"""The built fonts keep what the SFD holds: every character, its advance and its outline, and
the font's names; and they pass ots, the sanitizer browsers run web fonts through.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md.
"""
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import unicodedata
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from make_italic import AXIS, SLANT
from mark_advances import read_tables
from project import ADVANCE, SFD, STYLES, ZERO_WIDTH, font_file, nerd_fonts

FONTS = {style: [font_file(style, ext) for ext in ("otf", "ttf")] for style in STYLES}
# Converting to TrueType's quadratic curves moves an extreme point by up to 4 units.
BOX_TOLERANCE = 5
# ots, the sanitizer browsers run web fonts through. Pinned, and resolved as of a day as Font
# Bakery is, so that a stricter release can't fail a sound font; bump them on purpose.
OTS = "opentype-sanitizer==9.2.0"
OTS_EXCLUDE_NEWER = "2026-09-30"
SANITIZE = 'import ots, sys; sys.exit(ots.sanitize(sys.argv[1], "/dev/null").returncode)'
WINDOWS_ENGLISH = (3, 1, 0x409)  # platform, encoding and language of the names apps read


def shaped(font, text):
    """hb-shape's JSON glyphs for `text`, ligatures off, with their extents."""
    result = subprocess.run(
        ["hb-shape", "--output-format=json", "--show-extents", "--features=-calt",
         "--preserve-default-ignorables", str(font), f"--text={text}"],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def shape(font, text):
    """[(glyph name, advance, (x0, y0, x1, y1))] for each character of `text`, ligatures off."""
    return [(g["g"], g["ax"], (g["xb"], g["yb"] + g["h"], g["xb"] + g["w"], g["yb"]))
            for g in shaped(font, text)]


def placed(font, text):
    """[(cluster, glyph name, (x0, y0, x1, y1))]: each glyph's ink where shaping puts it."""
    out, pen = [], 0
    for g in shaped(font, text):
        x, y = pen + g["dx"], g["dy"]
        out.append((g["cl"], g["g"], (x + g["xb"], y + g["yb"] + g["h"],
                                      x + g["xb"] + g["w"], y + g["yb"])))
        pen += g["ax"]
    return out


def takes_no_cell(char):
    """A combining mark or a zero-width format character: shaped alone, since a shaper zeroes
    its advance and puts a run of marks in canonical order."""
    return unicodedata.category(char) == "Mn" or ord(char) in ZERO_WIDTH


def advances(font):
    """{glyph name: advance} as the font file itself gives them, whatever shaping does."""
    opened = fontforge.open(str(font))
    widths = {glyph.glyphname: glyph.width for glyph in opened.glyphs()}
    opened.close()
    return widths


def english_names(font):
    """{name ID: text} of the font file's Windows English (US) name records."""
    _, _, tables = read_tables(font.read_bytes())
    table = dict(tables)[b"name"]
    _, count, strings = struct.unpack_from(">3H", table)
    names = {}
    for i in range(count):
        *key, name_id, length, offset = struct.unpack_from(">6H", table, 6 + 12 * i)
        if tuple(key) == WINDOWS_ENGLISH:
            start = strings + offset
            names[name_id] = table[start:start + length].decode("utf-16-be")
    return names


def sanitize(font):
    """ots run on `font`: its exit status, and what it printed."""
    command = ["uvx", "--exclude-newer", OTS_EXCLUDE_NEWER, "--from", OTS, "python", "-c",
               SANITIZE, str(font)]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def require_current_build(style):
    for font in FONTS[style]:
        if not font.exists() or font.stat().st_mtime < STYLES[style].stat().st_mtime:
            raise AssertionError(f"{font.name} is missing or older than {STYLES[style].name}; "
                                 "run ./build.sh")


def nerd_style(font):
    """The style a Nerd Fonts build was patched from: the last part of its name."""
    return font.stem.split("-")[-1]


class BuiltFontTest(unittest.TestCase):
    style = "Regular"

    @classmethod
    def setUpClass(cls):
        require_current_build(cls.style)
        cls.fonts = FONTS[cls.style]
        sfd = fontforge.open(str(STYLES[cls.style]))
        glyphs = sorted((g for g in sfd.glyphs() if g.unicode >= 0), key=lambda g: g.unicode)
        cls.text = "".join(chr(g.unicode) for g in glyphs if not takes_no_cell(chr(g.unicode)))
        cls.names = [g.glyphname for g in glyphs if not takes_no_cell(chr(g.unicode))]
        cls.boxes = [g.boundingBox() for g in glyphs if not takes_no_cell(chr(g.unicode))]
        cls.marks = [(chr(g.unicode), g.glyphname, g.boundingBox())
                     for g in glyphs if takes_no_cell(chr(g.unicode))]
        cls.widths = {g.glyphname: g.width for g in sfd.glyphs()}
        # Not the unique ID (3), which records the build rather than the font. The version
        # string takes the form the OpenType spec gives it.
        cls.font_names = {1: sfd.familyname, 2: cls.style, 4: sfd.fullname,
                          5: f"Version {sfd.version}", 6: sfd.fontname}

    def test_every_character_reaches_its_glyph_one_cell_wide(self):
        # But the combining marks and the zero-width format characters, which take no room.
        for font in self.fonts:
            with self.subTest(font=font.name):
                shaped = shape(font, self.text)
                self.assertEqual([name for name, _, _ in shaped], self.names)
                self.assertEqual({advance for _, advance, _ in shaped}, {ADVANCE})
                marks = [shape(font, char) for char, _, _ in self.marks]
                self.assertEqual([[(name, advance) for name, advance, _ in glyphs]
                                  for glyphs in marks],
                                 [[(name, 0)] for _, name, _ in self.marks])

    def test_outlines_keep_their_extent(self):
        # A composite generated in the process that edited its base keeps the old bounds.
        for font in self.fonts:
            with self.subTest(font=font.name):
                built = shape(font, self.text)
                built += [glyph for char, _, _ in self.marks for glyph in shape(font, char)]
                boxes = self.boxes + [box for _, _, box in self.marks]
                moved = {name: box for (name, _, box), sfd_box in zip(built, boxes, strict=True)
                         if any(abs(a - b) > BOX_TOLERANCE for a, b in zip(box, sfd_box))}
                self.assertEqual(moved, {})

    def test_the_fonts_give_every_glyph_its_advance(self):
        # hb-shape zeroes a mark's advance whatever the font gives it, and FontForge gives
        # every glyph of a TTF one advance when all but the zero-width ones share it.
        for font in self.fonts:
            with self.subTest(font=font.name):
                wrong = {name: width for name, width in advances(font).items()
                         if name in self.widths and width != self.widths[name]}
                self.assertEqual(wrong, {})

    def test_fonts_carry_the_names_of_the_sfd(self):
        # The typographic family and subfamily, where a font has them, name the same family
        # and style as 1 and 2 do for a regular or an italic.
        for font in self.fonts:
            with self.subTest(font=font.name):
                names = english_names(font)
                expected = self.font_names | {typographic: self.font_names[legacy]
                                              for typographic, legacy in ((16, 1), (17, 2))
                                              if typographic in names}
                self.assertEqual({name_id: names.get(name_id) for name_id in expected},
                                 expected)


class ItalicBuiltFontTest(BuiltFontTest):
    style = "Italic"


class MarkShapingTest(unittest.TestCase):
    """Combining marks in shaped text: composed where the font has the letter, and otherwise
    placed on the glyph before them."""

    style = "Regular"
    slant = 0     # how far ink at a height moves per unit above the math axis
    rounding = 0  # how far a placed mark may miss its cell through rounding

    @classmethod
    def setUpClass(cls):
        require_current_build(cls.style)
        cls.fonts = FONTS[cls.style]
        sfd = fontforge.open(str(STYLES[cls.style]))
        # Not the soft hyphen: shapers skip a default ignorable, and a mark after one goes on
        # the character before it.
        cls.bases = [chr(g.unicode) for g in sfd.glyphs() if g.unicode >= 0
                     and unicodedata.category(chr(g.unicode)) not in ("Mn", "Cf")]
        cls.names = {g.unicode: g.glyphname for g in sfd.glyphs() if g.unicode >= 0}

    def test_marks_land_on_the_glyph_before_them(self):
        # Inside its cell, above or below: a mark after a glyph without anchors would land on
        # the next cell. Each base and its mark make one cluster, two characters long and one
        # cell wide, whether they compose or not. The italic's cell is sheared: ink at a
        # height y may lie left of it below the axis and right of it above, by (y - AXIS)
        # times the slant.
        for font in self.fonts:
            for mark in (0x301, 0x326):
                with self.subTest(font=font.name, mark=f"U+{mark:04X}"):
                    text = "".join(base + chr(mark) for base in self.bases)
                    outside = {}
                    for cluster, name, (x0, y0, x1, y1) in placed(font, text):
                        cell = cluster // 2 * ADVANCE
                        left = cell + (y0 - AXIS) * self.slant - self.rounding
                        right = cell + ADVANCE + (y1 - AXIS) * self.slant + self.rounding
                        if name == self.names[mark] and (x0 < left or x1 > right):
                            outside[self.bases[cluster // 2]] = (round(x0 - cell),
                                                                 round(x1 - cell))
                    self.assertEqual(outside, {})

    def test_stacked_marks_stay_apart(self):
        # Two marks above, or two below, one over the other without touching. Canonical order
        # puts the cedilla (class 202) before the comma below (220).
        for font in self.fonts:
            for text in ("x\u0308\u0301", "x\u0327\u0326"):
                with self.subTest(font=font.name, text=ascii(text)):
                    [_, (_, _, (_, low0, _, high0)), (_, _, (_, low1, _, high1))] = \
                        placed(font, text)
                    self.assertTrue(low1 > high0 or high1 < low0)

    def test_i_and_j_lose_their_dot_under_a_mark_above(self):
        for font in self.fonts:
            with self.subTest(font=font.name):
                self.assertEqual([name for name, _, _ in shape(font, "i\u030C j\u030C i\u0326")],
                                 ["dotlessi", "uni030C", "space", "dotlessj", "uni030C",
                                  "space", "i", "uni0326"])


class ItalicMarkShapingTest(MarkShapingTest):
    style = "Italic"
    slant = SLANT
    rounding = 2  # a sheared outline's points and its anchors are each rounded to units


class SanitizerTest(unittest.TestCase):
    """Every built font passes ots, which rejects a font whose tables break the spec's rules
    before a browser loads it. Skips without uvx."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        for style in STYLES:
            require_current_build(style)
        # The Nerd Fonts builds older than the SFDs are skipped by name in NerdFontTest.
        cls.fonts = [font for fonts in FONTS.values() for font in fonts] + nerd_fonts()[0]

    def test_fonts_pass_the_sanitizer(self):
        for font in self.fonts:
            with self.subTest(font=font.name):
                result = sanitize(font)
                self.assertEqual(result.returncode, 0, result.stderr)


class NerdFontTest(unittest.TestCase):
    """The Nerd Fonts builds keep our box drawing, block elements, Braille, Powerline symbols
    and ❮ ❯ ❰ ❱.

    The patcher swaps in its own box set unless the font has all of U+2500–U+259F, its own
    Braille unless --careful finds all of U+2800–U+28FF, its own Powerline symbols where
    --careful doesn't find ours, and fills U+276C–U+2771 (❬ ❭ ❮ ❯ ❰ ❱) only where the font has
    no glyph. The builds are made only by ./build.sh --nerd or --release, so a font older than
    the SFDs is skipped by name, and the whole class when none is current.
    """

    @classmethod
    def setUpClass(cls):
        cls.fonts, cls.stale = nerd_fonts()
        if not cls.fonts:
            raise unittest.SkipTest("no Nerd Fonts build newer than the SFDs")

    def test_stale_builds_are_skipped(self):
        for font in self.stale:
            with self.subTest(font=font.name):
                self.skipTest("older than the SFDs; rebuild with ./build.sh --nerd")

    def test_patched_fonts_keep_the_zero_widths(self):
        # But in the Mono variant, where the patcher gives every glyph one advance on purpose.
        sfd = fontforge.open(str(SFD))
        marks = {g.glyphname for g in sfd.glyphs() if g.unicode >= 0 and takes_no_cell(chr(g.unicode))}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                widths = advances(nerd)
                advance = ADVANCE if "NerdFontMono-" in nerd.name else 0
                self.assertEqual({name: widths[name] for name in marks},
                                 dict.fromkeys(marks, advance))

    def test_patched_fonts_keep_our_glyphs(self):
        text = "".join(chr(code) for code in [*range(0x2500, 0x25A0), *range(0x2800, 0x2900),
                                              *range(0xE0A0, 0xE0A3), *range(0xE0B0, 0xE0B4)])
        text += "❮❯❰❱"
        plain = {(style, font.suffix): font for style, fonts in FONTS.items() for font in fonts}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                self.assertEqual(shape(nerd, text),
                                 shape(plain[nerd_style(nerd), nerd.suffix], text))


if __name__ == "__main__":
    unittest.main()
