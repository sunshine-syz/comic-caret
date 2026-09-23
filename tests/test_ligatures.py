"""Shaping tests for the coding ligatures, run with HarfBuzz against both built fonts.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md.
"""
import json
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from add_ligatures import GENERATED
from project import ADVANCE, ROOT, SFD

FONTS = [ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("otf", "ttf")]
NERD_FONTS = [ROOT / "build" / "nerd" / f"ComicCaretNerdFont-Regular.{ext}"
              for ext in ("otf", "ttf")]


def hb_shape(font, text, *options):
    result = subprocess.run(
        ["hb-shape", "--output-format=json", *options,
         str(font), f"--text={text}"],  # --text= form: a leading '-' would read as an option
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def shape(font, text, calt=True):
    """[(glyph name, advance)] for `text` shaped with `font`."""
    glyphs = hb_shape(font, text, f"--features={'+' if calt else '-'}calt")
    return [(g["g"], g["ax"]) for g in glyphs]


def extents(font, text):
    """[(glyph name, x bearing, y bearing, width, height)] for `text` shaped with `font`."""
    glyphs = hb_shape(font, text, "--show-extents")
    return [(g["g"], g["xb"], g["yb"], g["w"], g["h"]) for g in glyphs]


def names(font, text, calt=True):
    return [name for name, _ in shape(font, text, calt)]


def pieces(first, middle, last, count):
    """A run of `count` glyphs: first, count - 2 middles, last."""
    return [first] + [middle] * (count - 2) + [last]


def hyphens(count, left="hyphen.sta", right="hyphen.end"):
    return pieces(left, "hyphen.mid", right, count)


def equals(count, left="equal.sta", right="equal.end"):
    return pieces(left, "equal.mid", right, count)


# Input -> expected glyph names. Letters and digits are named as themselves or spelled out.
LIGATED = {
    # Runs of - and =
    "--": hyphens(2),
    "---": hyphens(3),
    "------": hyphens(6),
    "i--": ["i"] + hyphens(2),
    "--help": hyphens(2) + ["h", "e", "l", "p"],
    "|---|": ["bar"] + hyphens(3) + ["bar"],
    "+----+": ["plus"] + hyphens(4) + ["plus"],
    "==": equals(2),
    "===": equals(3),
    "========": equals(8),
    "a==b": ["a"] + equals(2) + ["b"],
    # Arrows, heads at either or both ends
    "->": hyphens(2, right="greater.arrow"),
    "-->": hyphens(3, right="greater.arrow"),
    "--->": hyphens(4, right="greater.arrow"),
    "------->": hyphens(8, right="greater.arrow"),
    "<-": hyphens(2, left="less.arrow"),
    "<--": hyphens(3, left="less.arrow"),
    "<-----": hyphens(6, left="less.arrow"),
    "<->": hyphens(3, "less.arrow", "greater.arrow"),
    "<---->": hyphens(6, "less.arrow", "greater.arrow"),
    "|->": ["bar"] + hyphens(2, right="greater.arrow"),
    "x<-1": ["x"] + hyphens(2, left="less.arrow") + ["one"],
    "=>": equals(2, right="greater.darrow"),
    "==>": equals(3, right="greater.darrow"),
    "====>": equals(5, right="greater.darrow"),
    "<==": equals(3, left="less.darrow"),
    "<====": equals(5, left="less.darrow"),
    "<=>": equals(3, "less.darrow", "greater.darrow"),
    "<====>": equals(6, "less.darrow", "greater.darrow"),
    # A - and an = family side by side: each part joins on its own
    "-=>": ["hyphen"] + equals(2, right="greater.darrow"),
    "=->": ["equal"] + hyphens(2, right="greater.arrow"),
    "->=": hyphens(2, right="greater.arrow") + ["equal"],
    # != !== :=
    "!=": ["LIG", "exclam_equal.liga"],
    "a!=b": ["a", "LIG", "exclam_equal.liga", "b"],
    "!==": ["LIG", "LIG", "exclam_equal_equal.liga"],
    ":=": ["colon.eq", "equal"],
    "x:=1": ["x", "colon.eq", "equal", "one"],
    # <= >=
    "<=": ["LIG", "less_equal.liga"],
    ">=": ["LIG", "greater_equal.liga"],
    "a<=b": ["a", "LIG", "less_equal.liga", "b"],
    "x >= y": ["x", "space", "LIG", "greater_equal.liga", "space", "y"],
    # Runs of _ # ~
    "__": pieces("underscore.sta", "underscore.mid", "underscore.end", 2),
    "____": pieces("underscore.sta", "underscore.mid", "underscore.end", 4),
    "__init__": ["underscore.sta", "underscore.end", "i", "n", "i", "t",
                 "underscore.sta", "underscore.end"],
    "##": pieces("numbersign.sta", "numbersign.mid", "numbersign.end", 2),
    "#####": pieces("numbersign.sta", "numbersign.mid", "numbersign.end", 5),
    "## Heading": ["numbersign.sta", "numbersign.end", "space", "H", "e", "a", "d", "i", "n", "g"],
    "~~": ["asciitilde.sta", "asciitilde.end"],
    "~~~": ["asciitilde.sta", "asciitilde.mid", "asciitilde.end.low"],
    "~~~~": ["asciitilde.sta", "asciitilde.mid", "asciitilde.mid.low", "asciitilde.end"],
    "~~~~~": ["asciitilde.sta", "asciitilde.mid", "asciitilde.mid.low", "asciitilde.mid",
              "asciitilde.end.low"],
    "~~strike~~": ["asciitilde.sta", "asciitilde.end", "s", "t", "r", "i", "k", "e",
                   "asciitilde.sta", "asciitilde.end"],
    # Pipes and tightened pairs
    "|>": ["LIG", "bar_greater.liga"],
    "<|": ["LIG", "less_bar.liga"],
    "||": ["bar.tight_r", "bar.tight_l"],
    "a || b": ["a", "space", "bar.tight_r", "bar.tight_l", "space", "b"],
    "::": ["colon.tight_r", "colon.tight_l"],
    "a::b": ["a", "colon.tight_r", "colon.tight_l", "b"],
    "...": ["period.tight_r", "period", "period.tight_l"],
    "&&": ["ampersand.tight_r", "ampersand.tight_l"],
    "++": ["plus.tight_r", "plus.tight_l"],
    "//": ["slash.tight_r", "slash.tight_l"],
    "/*": ["slash.tight_r", "asterisk.tight_l"],
    "*/": ["asterisk.tight_r", "slash.tight_l"],
    "<<": ["less.tight_r", "less.tight_l"],
    ">>": ["greater.tight_r", "greater.tight_l"],
    "??": ["question.tight_r", "question.tight_l"],
}

# Input that must shape exactly as it does with calt off.
PLAIN = [
    "-", "=", "a-b", "x=y", "- -", "= =",
    # Malformed arrows: a head pointing inward, doubled or in the middle, at any length
    ">-", "-<", "=<", ">==", "==<", "->>", "<<-", "=>=", ">=>", "<=<",
    "------<", ">------", "=====<", "-->-", "->->", "-><-", "<-<", "<==<",
    # ! or : before a longer = run, and fixed ligatures touching another operator
    "!===", ":==", "!=!", "!=>", "=!=", "::=",
    ">>=", "<<=", "<=-", "=<=",
    # Lone run characters
    "_", "#", "~", "a_b", "#!", "~/",
    # Pairs touching another operator
    "<<<<<<<", ">>>>>>>", "////", "///", "/**", "||=", "&&=", "??=",
    "a::<T>", "https://", "....", "..", "|||", "<||", "|>>",
]


class LigatureShapingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for font in FONTS:
            if not font.exists() or font.stat().st_mtime < SFD.stat().st_mtime:
                raise AssertionError(f"{font.name} is missing or older than {SFD.name}; "
                                     "run ./build.sh")

    def test_ligated_sequences(self):
        for font in FONTS:
            for text, expected in LIGATED.items():
                with self.subTest(font=font.name, text=text):
                    self.assertEqual(names(font, text), expected)

    def test_plain_sequences(self):
        for font in FONTS:
            for text in PLAIN:
                with self.subTest(font=font.name, text=text):
                    self.assertEqual(names(font, text), names(font, text, calt=False))

    def test_every_glyph_advances_one_cell(self):
        for font in FONTS:
            for text in [*LIGATED, *PLAIN]:
                with self.subTest(font=font.name, text=text):
                    advances = [advance for _, advance in shape(font, text)]
                    self.assertEqual(advances, [ADVANCE] * len(text))

    def test_turning_calt_off_turns_every_ligature_off(self):
        for font in FONTS:
            for text in LIGATED:
                with self.subTest(font=font.name, text=text):
                    generated = [n for n in names(font, text, calt=False) if GENERATED.fullmatch(n)]
                    self.assertEqual(generated, [])

    def test_every_generated_glyph_is_reachable(self):
        with open(SFD, encoding="utf-8") as sfd:
            made = {line.split()[1] for line in sfd
                    if line.startswith("StartChar: ") and GENERATED.fullmatch(line.split()[1])}
        reached = {name for font in FONTS for text in LIGATED for name in names(font, text)}
        self.assertEqual(sorted(made - reached), [])


class NerdFontTest(unittest.TestCase):
    """The committed Nerd Fonts builds keep the ligatures through the patcher."""

    def test_patched_fonts_keep_the_ligatures(self):
        for font in NERD_FONTS:
            for text in ("->", "<====>", "!=", ">=", "~~~", "::"):
                with self.subTest(font=font.name, text=text):
                    self.assertEqual(names(font, text), LIGATED[text])

    def test_patched_fonts_draw_the_current_ligatures(self):
        # Git keeps no mtimes, so compare with the plain fonts, which LigatureShapingTest
        # requires to be current: a stale build still shapes, but draws the old outlines.
        text = " ".join(LIGATED)  # reaches every generated glyph
        for nerd, plain in zip(NERD_FONTS, FONTS, strict=True):
            with self.subTest(font=nerd.name):
                self.assertEqual(extents(nerd, text), extents(plain, text))


if __name__ == "__main__":
    unittest.main()
