"""Shaping tests for the coding ligatures, run with HarfBuzz against both built fonts.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md.
"""
import itertools
import json
import pathlib
import subprocess
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from add_ligatures import GENERATED, OVERLAP
from measure import ink, spans_at_x
from project import ADVANCE, ROOT, SFD

FONTS = [ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("otf", "ttf")]
NERD_DIR = ROOT / "build" / "nerd"


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


def seam(layer, x):
    """(y0, y1) of each straight vertical edge at x, where a piece is cut to meet the next."""
    edges = []
    for contour in layer:
        for i in range(len(contour)):
            a, b = contour[i], contour[(i + 1) % len(contour)]
            if a.on_curve and b.on_curve and abs(a.x - x) < 0.5 and abs(b.x - x) < 0.5:
                edges.append((min(a.y, b.y), max(a.y, b.y)))
    return sorted(edges)


def unmet(edges, other, x, inward, cover):
    """The flat `edges` of one piece that the `other` piece, cut at x, neither repeats edge for
    edge nor covers, just inside its cut (x + inward), with a stroke reaching `cover` past both
    ends."""
    repeated = seam(other, x)
    spans = spans_at_x(other, x + inward)
    return [(y0, y1) for y0, y1 in edges if (y0, y1) not in repeated
            and not any(a <= y0 - cover and b >= y1 + cover for a, b in spans)]


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
    # An arrow's head before a tag: HTML, and JSX's x=><li>. <a> and <A> too: FontForge's
    # feature parser drops the first glyph of a [X-Y] range written without spaces.
    "--><p>": hyphens(3, right="greater.arrow") + ["less", "p", "greater"],
    "--></p>": hyphens(3, right="greater.arrow") + ["less", "slash", "p", "greater"],
    "--><a>": hyphens(3, right="greater.arrow") + ["less", "a", "greater"],
    "--><A>": hyphens(3, right="greater.arrow") + ["less", "A", "greater"],
    "x=><li>": ["x"] + equals(2, right="greater.darrow") + ["less", "l", "i", "greater"],
    "x=><a>": ["x"] + equals(2, right="greater.darrow") + ["less", "a", "greater"],
    # A - run after the > that ends a tag, though >- is otherwise an inward head
    "</p>-->": ["less", "slash", "p", "greater"] + hyphens(3, right="greater.arrow"),
    "<====>": equals(6, "less.darrow", "greater.darrow"),
    # A - and an = family side by side: each part joins on its own
    "-=>": ["hyphen"] + equals(2, right="greater.darrow"),
    "=->": ["equal"] + hyphens(2, right="greater.arrow"),
    "->=": hyphens(2, right="greater.arrow") + ["equal"],
    # Two heads on a - arrow, drawn in the outer cell, the inner > or < carrying the shaft
    "->>": ["hyphen.sta", "greater.shaft", "greater.twohead"],
    "-->>": hyphens(3, right="greater.shaft") + ["greater.twohead"],
    "<<-": ["less.twohead", "less.shaft", "hyphen.end"],
    "x<<-1": ["x", "less.twohead", "less.shaft", "hyphen.end", "one"],
    "x <<- y": ["x", "space", "less.twohead", "less.shaft", "hyphen.end", "space", "y"],
    "<<--": ["less.twohead"] + hyphens(3, left="less.shaft"),
    "<<->>": ["less.twohead"] + hyphens(3, "less.shaft", "greater.shaft") + ["greater.twohead"],
    # >=> <=<: a double arrow with a tail
    ">=>": ["greater.dtail", "equal.mid", "greater.darrow"],
    "f>=>g": ["f", "greater.dtail", "equal.mid", "greater.darrow", "g"],
    "<=<": ["less.darrow", "equal.mid", "less.dtail"],
    # Wave arrows: a > head starts high or low, after whichever the run ends on
    "~>": ["asciitilde.sta", "greater.warrow"],
    "~> 1.0": ["asciitilde.sta", "greater.warrow", "space", "one", "period", "zero"],
    "~~>": ["asciitilde.sta", "asciitilde.mid", "greater.warrow.low"],
    "~~~>": ["asciitilde.sta", "asciitilde.mid", "asciitilde.mid.low", "greater.warrow"],
    "<~": ["less.warrow", "asciitilde.end"],
    "<~~": ["less.warrow", "asciitilde.mid", "asciitilde.end.low"],
    "<~>": ["less.warrow", "asciitilde.mid", "greater.warrow.low"],
    # HTML comments
    "<!--": ["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end"],
    "<!-- x -->": (["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end", "space", "x",
                    "space"] + hyphens(3, right="greater.arrow")),
    "</p><!--": ["less", "slash", "p", "greater", "less.comment", "exclam.tight_r", "hyphen.sta",
                 "hyphen.end"],
    "--><!--": (hyphens(3, right="greater.arrow")
                + ["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end"]),
    # A commented-out element: the opener keeps its ligature before the tag, and the arrow
    # closes after it
    "<!--<": ["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end", "less"],
    "<!--<div>-->": (["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end",
                      "less", "d", "i", "v", "greater"] + hyphens(3, right="greater.arrow")),
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
    # Pipes, <> and tightened pairs
    "|>": ["LIG", "bar_greater.liga"],
    "<|": ["LIG", "less_bar.liga"],
    "<|>": ["LIG", "LIG", "less_bar_greater.liga"],
    "a <|> b": ["a", "space", "LIG", "LIG", "less_bar_greater.liga", "space", "b"],
    "<>": ["LIG", "less_greater.liga"],
    "new List<>()": ["n", "e", "w", "space", "L", "i", "s", "t", "LIG", "less_greater.liga",
                     "parenleft", "parenright"],
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
    "a?.b": ["a", "question.tight_r", "period.tight_l", "b"],
    "x?: T": ["x", "question.tight_r", "colon.tight_l", "space", "T"],
    "(?:a)": ["parenleft", "question.tight_r", "colon.tight_l", "a", "parenright"],
    # Tightened threes: the outer glyphs move in
    "|||": ["bar.tight_r", "bar", "bar.tight_l"],
    "&&&": ["ampersand.tight_r", "ampersand", "ampersand.tight_l"],
    "<<<": ["less.tight_r", "less", "less.tight_l"],
    ">>>": ["greater.tight_r", "greater", "greater.tight_l"],
    ">>=": ["greater.tight_r", "greater", "equal.tight_l"],
    "m >>= f": ["m", "space", "greater.tight_r", "greater", "equal.tight_l", "space", "f"],
    "<<=": ["less.tight_r", "less", "equal.tight_l"],
    "=<<": ["equal.tight_r", "less", "less.tight_l"],
    "<$>": ["less.tight_r", "dollar", "greater.tight_l"],
    "f<*>x": ["f", "less.tight_r", "asterisk", "greater.tight_l", "x"],
    "0..=9": ["zero", "period.tight_r", "period", "equal.tight_l", "nine"],
    "0..<n": ["zero", "period.tight_r", "period", "less.tight_l", "n"],
}

# Input that must shape exactly as it does with calt off.
PLAIN = [
    "-", "=", "a-b", "x=y", "- -", "= =",
    # Malformed arrows: a head pointing inward, tripled or in the middle, at any length
    ">-", "-<", "=<", ">==", "==<", "=>=", "=>>", "<<==", "->>>", "<<<-", "->>-", "-<<",
    "------<", ">------", "=====<", "-->-", "->->", "-><-", "<-<", "<==<", ">=>=", ">==>",
    # A shell heredoc's <<-, whatever letter its delimiter starts with
    "cat <<-EOF", "<<-'EOF'", '<<-"EOF"', "<<-\\EOF", "cat <<-ARGS", "<<-abc",
    # An arrow before a < that opens no tag, and a lone - after a tag's >
    "-><", "=><", "-><1", "x>-1",
    # ! or : before a longer = run, and fixed ligatures touching another operator
    "!===", ":==", "!=!", "!=>", "=!=", "::=",
    "<=-", "=<=", "<>=", "<<>>", "<|>>", "<||>", "-<>",
    # Wave arrows followed by another operator, and Ruby's <<~ heredoc
    "~>>", "~>=", "<<~", "=~", "!~",
    # <!-- without its -- run
    "<!-",
    # Lone run characters
    "_", "#", "~", "a_b", "#!", "~/",
    # Pairs and threes touching another operator, and ** (the asterisks would touch)
    "<<<<<<<", ">>>>>>>", "////", "///", "/**", "||=", "&&=", "??=",
    "a::<T>", "https://", "....", "..", "<||", "|>>", "||||", "&&&&", ">>>=", "...=",
    "?..", "??.", "**", "a**b",
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

    def test_joined_pieces_meet_without_a_step(self):
        # A piece that runs on is cut flat at its cell's edge, and the next begins with the
        # same edge or covers it; any step between them shows as a notch in the stroke.
        font = fontforge.open(str(SFD))
        # A stroke hides an edge when it reaches a quarter of a stroke past both its ends, as
        # the inner head of ->> does the shaft's end.
        _, y0, _, y1 = font["hyphen"].boundingBox()
        cover = (y1 - y0) / 4
        for text in LIGATED:
            for left, right in itertools.pairwise(names(FONTS[0], text)):
                with self.subTest(text=text, left=left, right=right):
                    first, second = ink(font, left), ink(font, right)
                    self.assertEqual(unmet(seam(first, ADVANCE + OVERLAP), second,
                                           -OVERLAP, 1, cover), [])
                    self.assertEqual(unmet(seam(second, -OVERLAP), first,
                                           ADVANCE + OVERLAP, -1, cover), [])

    def test_every_generated_glyph_is_reachable(self):
        with open(SFD, encoding="utf-8") as sfd:
            made = {line.split()[1] for line in sfd
                    if line.startswith("StartChar: ") and GENERATED.fullmatch(line.split()[1])}
        reached = {name for font in FONTS for text in LIGATED for name in names(font, text)}
        self.assertEqual(sorted(made - reached), [])


class NerdFontTest(unittest.TestCase):
    """Nerd Fonts builds keep the ligatures through the patcher.

    They are built only by ./build.sh --nerd or --release, so without a current build the
    tests skip; the release steps in CLAUDE.md run them after building.
    """

    @classmethod
    def setUpClass(cls):
        cls.fonts = sorted(NERD_DIR.glob("*.[ot]tf"))
        if not cls.fonts or min(f.stat().st_mtime for f in cls.fonts) < SFD.stat().st_mtime:
            raise unittest.SkipTest(f"no Nerd Fonts build newer than {SFD.name}")

    def test_patched_fonts_keep_the_ligatures(self):
        for font in self.fonts:
            for text in ("->", "<====>", "!=", ">=", "~~~", "::"):
                with self.subTest(font=font.name, text=text):
                    self.assertEqual(names(font, text), LIGATED[text])

    def test_patched_fonts_draw_the_current_ligatures(self):
        # Git keeps no mtimes, so compare with the plain fonts, which LigatureShapingTest
        # requires to be current: a stale build still shapes, but draws the old outlines.
        text = " ".join(LIGATED)  # reaches every generated glyph
        plain = {font.suffix: font for font in FONTS}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                self.assertEqual(extents(nerd, text), extents(plain[nerd.suffix], text))


if __name__ == "__main__":
    unittest.main()
