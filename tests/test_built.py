"""The built fonts keep what the SFD holds: every character, its advance and its outline.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md.
"""
import json
import pathlib
import subprocess
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from project import ADVANCE, ROOT, SFD

FONTS = [ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("otf", "ttf")]
NERD_DIR = ROOT / "build" / "nerd"
# Converting to TrueType's quadratic curves moves an extreme point by up to 4 units.
BOX_TOLERANCE = 5


def shape(font, text):
    """[(glyph name, advance, (x0, y0, x1, y1))] for each character of `text`, ligatures off."""
    result = subprocess.run(
        ["hb-shape", "--output-format=json", "--show-extents", "--features=-calt",
         "--preserve-default-ignorables", str(font), f"--text={text}"],
        capture_output=True, text=True, check=True)
    return [(g["g"], g["ax"], (g["xb"], g["yb"] + g["h"], g["xb"] + g["w"], g["yb"]))
            for g in json.loads(result.stdout)]


class BuiltFontTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for font in FONTS:
            if not font.exists() or font.stat().st_mtime < SFD.stat().st_mtime:
                raise AssertionError(f"{font.name} is missing or older than {SFD.name}; "
                                     "run ./build.sh")
        sfd = fontforge.open(str(SFD))
        glyphs = sorted((g for g in sfd.glyphs() if g.unicode >= 0), key=lambda g: g.unicode)
        cls.text = "".join(chr(g.unicode) for g in glyphs)
        cls.names = [g.glyphname for g in glyphs]
        cls.boxes = [g.boundingBox() for g in glyphs]

    def test_every_character_reaches_its_glyph_one_cell_wide(self):
        for font in FONTS:
            with self.subTest(font=font.name):
                shaped = shape(font, self.text)
                self.assertEqual([name for name, _, _ in shaped], self.names)
                self.assertEqual({advance for _, advance, _ in shaped}, {ADVANCE})

    def test_outlines_keep_their_extent(self):
        # A composite generated in the process that edited its base keeps the old bounds.
        for font in FONTS:
            with self.subTest(font=font.name):
                moved = {name: box for (name, _, box), sfd_box in zip(shape(font, self.text),
                                                                      self.boxes, strict=True)
                         if any(abs(a - b) > BOX_TOLERANCE for a, b in zip(box, sfd_box))}
                self.assertEqual(moved, {})


class NerdFontTest(unittest.TestCase):
    """The Nerd Fonts builds keep our box drawing, block elements and ❮ ❯.

    The patcher swaps in its own box set unless the font has all of U+2500–U+259F, and fills
    U+276C–U+2771 (❬ ❭ ❮ ❯ ❰ ❱) only where the font has no glyph. The builds are made only by
    ./build.sh --nerd or --release, so without a current build the tests skip.
    """

    @classmethod
    def setUpClass(cls):
        cls.fonts = sorted(NERD_DIR.glob("*.[ot]tf"))
        if not cls.fonts or min(f.stat().st_mtime for f in cls.fonts) < SFD.stat().st_mtime:
            raise unittest.SkipTest(f"no Nerd Fonts build newer than {SFD.name}")

    def test_patched_fonts_keep_our_glyphs(self):
        text = "".join(chr(code) for code in range(0x2500, 0x25A0)) + "❮❯"
        plain = {font.suffix: font for font in FONTS}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                self.assertEqual(shape(nerd, text), shape(plain[nerd.suffix], text))


if __name__ == "__main__":
    unittest.main()
