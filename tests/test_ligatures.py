"""Shaping tests for the coding ligatures, run with HarfBuzz against every built font.

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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared helpers
import lig_geometry as geo
from add_ligatures import GENERATED, TIGHT_KEEP
from helpers import NerdBuilds, require_current_build
from measure import gap, ink, spans_at_x, vertical_edges
from project import (
    ADVANCE,
    BOLD_SFD,
    FORMATS,
    OVERLAP,
    SFD,
    STYLES,
    SYMBOL_SIDE,
    font_file,
    style_of,
)

# Each built font.
FONTS = [font_file(style, ext) for style in STYLES for ext in FORMATS]
REGULAR = font_file("Regular", "ttf")


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
    return sorted((y0, y1) for ex, y0, y1 in vertical_edges(layer) if abs(ex - x) < 0.5)


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
    # Runs of three or more - and two or more =
    "---": hyphens(3),
    "------": hyphens(6),
    "|---|": ["bar"] + hyphens(3) + ["bar"],
    "+----+": ["plus"] + hyphens(4) + ["plus"],
    "==": equals(2),
    "====": equals(4),
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
    "x<-y": ["x"] + hyphens(2, left="less.arrow") + ["y"],
    "=>": equals(2, right="greater.darrow"),
    "==>": equals(3, right="greater.darrow"),
    "====>": equals(5, right="greater.darrow"),
    "<==": equals(3, left="less.darrow"),
    "<====": equals(5, left="less.darrow"),
    "<==>": equals(4, "less.darrow", "greater.darrow"),
    # An arrow's head before a tag: HTML, and JSX's x=><li>. <a> and <A> too: FontForge's
    # feature parser drops the first glyph of a [X-Y] range written without spaces.
    "--><p>": hyphens(3, right="greater.arrow") + ["less", "p", "greater"],
    "--></p>": hyphens(3, right="greater.arrow") + ["less", "slash", "p", "greater"],
    "--><a>": hyphens(3, right="greater.arrow") + ["less", "a", "greater"],
    "--><A>": hyphens(3, right="greater.arrow") + ["less", "A", "greater"],
    "x=><li>": ["x"] + equals(2, right="greater.darrow") + ["less", "l", "i", "greater"],
    "x=><a>": ["x"] + equals(2, right="greater.darrow") + ["less", "a", "greater"],
    # A run or arrow right after a short tag, though >- is otherwise an inward head
    "</p>-->": ["less", "slash", "p", "greater"] + hyphens(3, right="greater.arrow"),
    "</p>--->": ["less", "slash", "p", "greater"] + hyphens(4, right="greater.arrow"),
    "<li>--- item": ["less", "l", "i", "greater"] + hyphens(3) + ["space", "i", "t", "e", "m"],
    "<a>->": ["less", "a", "greater"] + hyphens(2, right="greater.arrow"),
    "<a>->>": ["less", "a", "greater", "hyphen.sta", "greater.shaft", "greater.twohead"],
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
    # A heredoc written with a space after <<- looks like R's <<- and draws its arrow; the
    # exception in PLAIN covers the delimiter right after the hyphen.
    "cat <<- EOF": ["c", "a", "t", "space", "less.twohead", "less.shaft", "hyphen.end", "space",
                    "E", "O", "F"],
    "<<--": ["less.twohead"] + hyphens(3, left="less.shaft"),
    "<<->>": ["less.twohead"] + hyphens(3, "less.shaft", "greater.shaft") + ["greater.twohead"],
    # >=> <=<: a double arrow with a tail
    ">=>": ["greater.dtail", "equal.mid", "greater.darrow"],
    "f>=>g": ["f", "greater.dtail", "equal.mid", "greater.darrow", "g"],
    "<=<": ["less.darrow", "equal.mid", "less.dtail"],
    # Wave arrows: a > head starts high or low, after whichever the run ends on
    "~>": ["asciitilde.sta", "greater.warrow"],
    "a ~> b": ["a", "space", "asciitilde.sta", "greater.warrow", "space", "b"],
    "~~>": ["asciitilde.sta", "asciitilde.mid", "greater.warrow.low"],
    "~~~>": ["asciitilde.sta", "asciitilde.mid", "asciitilde.mid.low", "greater.warrow"],
    "<~": ["less.warrow", "asciitilde.end"],
    "<~~": ["less.warrow", "asciitilde.mid", "asciitilde.end.low"],
    "<~>": ["less.warrow", "asciitilde.mid", "greater.warrow.low"],
    # A run whose > is no head has no < head either, however long: ~~ is drawn as in ~~>=
    "<~~>=": ["less", "asciitilde.sta", "asciitilde.end", "greater", "equal"],
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
    # After any other tag only --> joins, and a>--b is plain
    '<!--<p id="x">-->': (["less.comment", "exclam.tight_r", "hyphen.sta", "hyphen.end",
                           "less", "p", "space", "i", "d", "equal", "quotedbl", "x", "quotedbl",
                           "greater"] + hyphens(3, right="greater.arrow")),
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
    "___": pieces("underscore.sta", "underscore.mid", "underscore.end", 3),
    "____": pieces("underscore.sta", "underscore.mid", "underscore.end", 4),
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
    "a >> b": ["a", "space", "greater.tight_r", "greater.tight_l", "space", "b"],
    # A shift without spaces: a name or a number follows, which never follows closing generics
    "cin>>n": ["c", "i", "n", "greater.tight_r", "greater.tight_l", "n"],
    "x>>1": ["x", "greater.tight_r", "greater.tight_l", "one"],
    "f()>>2": ["f", "parenleft", "parenright", "greater.tight_r", "greater.tight_l", "two"],
    "a << b": ["a", "space", "less.tight_r", "less.tight_l", "space", "b"],
    "x<<1": ["x", "less.tight_r", "less.tight_l", "one"],
    "cout<<x": ["c", "o", "u", "t", "less.tight_r", "less.tight_l", "x"],
    # An Erlang or Elixir binary opens and closes as typed; what it holds still joins
    "<<x::8>>": ["less", "less", "x", "colon.tight_r", "colon.tight_l", "eight", "greater",
                 "greater"],
    "<<H, T/binary>> -> ok": ["less", "less", "H", "comma", "space", "T", "slash", "b", "i", "n",
                              "a", "r", "y", "greater", "greater", "space", "hyphen.sta",
                              "greater.arrow", "space", "o", "k"],
    # A range or a slice, as ..= ..< tighten: a name, a number, a quote or a bracket on either
    # side
    "0..n": ["zero", "period.tight_r", "period.tight_l", "n"],
    "&s[..n]": ["ampersand", "s", "bracketleft", "period.tight_r", "period.tight_l", "n",
                "bracketright"],
    "&s[1..]": ["ampersand", "s", "bracketleft", "one", "period.tight_r", "period.tight_l",
                "bracketright"],
    "&s[..]": ["ampersand", "s", "bracketleft", "period.tight_r", "period.tight_l",
               "bracketright"],
    "[1..]": ["bracketleft", "one", "period.tight_r", "period.tight_l", "bracketright"],
    "'a'..'z'": ["quotesingle", "a", "quotesingle", "period.tight_r", "period.tight_l",
                 "quotesingle", "z", "quotesingle"],
    "Foo { ..x }": ["F", "o", "o", "space", "braceleft", "space", "period.tight_r",
                    "period.tight_l", "x", "space", "braceright"],
    "p()..q": ["p", "parenleft", "parenright", "period.tight_r", "period.tight_l", "q"],
    # A comment opener before the ! or < of a doc comment
    "//!": ["slash.tight_r", "slash.tight_l", "exclam"],
    "/*!": ["slash.tight_r", "asterisk.tight_l", "exclam"],
    "/* c */": ["slash.tight_r", "asterisk.tight_l", "space", "c", "space", "asterisk.tight_r",
                "slash.tight_l"],
    "??": ["question.tight_r", "question.tight_l"],
    "a?.b": ["a", "question.tight_r", "period.tight_l", "b"],
    "a ?: b": ["a", "space", "question.tight_r", "colon.tight_l", "space", "b"],
    "(?:a)": ["parenleft", "question.tight_r", "colon.tight_l", "a", "parenright"],
    # === as three bars, as !== draws them
    "===": ["LIG", "LIG", "equal_equal_equal.liga"],
    "a === b": ["a", "space", "LIG", "LIG", "equal_equal_equal.liga", "space", "b"],
    "a===-1": ["a", "LIG", "LIG", "equal_equal_equal.liga", "hyphen", "one"],
    "x===+y": ["x", "LIG", "LIG", "equal_equal_equal.liga", "plus", "y"],
    # A table's border of exactly three = stays one line
    "+===+": ["plus", "equal.sta", "equal.mid", "equal.end", "plus"],
    "|===|": ["bar", "equal.sta", "equal.mid", "equal.end", "bar"],
    # Tightened threes: the outer glyphs move in
    "|||": ["bar.tight_r", "bar", "bar.tight_l"],
    "///": ["slash.tight_r", "slash", "slash.tight_l"],
    "/**": ["slash.tight_r", "asterisk", "asterisk.tight_l"],
    "&&&": ["ampersand.tight_r", "ampersand", "ampersand.tight_l"],
    "<<<": ["less.tight_r", "less", "less.tight_l"],
    ">>>": ["greater.tight_r", "greater", "greater.tight_l"],
    ">>=": ["greater.tight_r", "greater", "equal.tight_l"],
    "m >>= f": ["m", "space", "greater.tight_r", "greater", "equal.tight_l", "space", "f"],
    "m>>=f": ["m", "greater.tight_r", "greater", "equal.tight_l", "f"],
    "a>>>0": ["a", "greater.tight_r", "greater", "greater.tight_l", "zero"],
    "///<": ["slash.tight_r", "slash", "slash.tight_l", "less"],
    "/**<": ["slash.tight_r", "asterisk", "asterisk.tight_l", "less"],
    "<<=": ["less.tight_r", "less", "equal.tight_l"],
    "=<<": ["equal.tight_r", "less", "less.tight_l"],
    "<$>": ["less.tight_r", "dollar", "greater.tight_l"],
    "<=>": ["less.tight_r", "equal", "greater.tight_l"],
    "a <=> b": ["a", "space", "less.tight_r", "equal", "greater.tight_l", "space", "b"],
    "f<*>x": ["f", "less.tight_r", "asterisk", "greater.tight_l", "x"],
    "0..=9": ["zero", "period.tight_r", "period", "equal.tight_l", "nine"],
    "0..<n": ["zero", "period.tight_r", "period", "less.tight_l", "n"],
    # An assignment that closes a tightened pair, as <<= and >>= do
    "||=": ["bar.tight_r", "bar", "equal.tight_l"],
    "&&=": ["ampersand.tight_r", "ampersand", "equal.tight_l"],
    "??=": ["question.tight_r", "question", "equal.tight_l"],
    "x ??= 1": ["x", "space", "question.tight_r", "question", "equal.tight_l", "space", "one"],
    ">>>=": ["greater.tight_r", "greater", "greater", "equal.tight_l"],
    "y >>>= 1": ["y", "space", "greater.tight_r", "greater", "greater", "equal.tight_l", "space",
                 "one"],
    # :: before a turbofish, a glob, a destructor or a negative step
    "a::<T>": ["a", "colon.tight_r", "colon.tight_l", "less", "T", "greater"],
    # :: after generics close, before a name
    "Box::<u8>::new()": ["B", "o", "x", "colon.tight_r", "colon.tight_l", "less", "u", "eight",
                         "greater", "colon.tight_r", "colon.tight_l", "n", "e", "w", "parenleft",
                         "parenright"],
    "use std::*;": ["u", "s", "e", "space", "s", "t", "d", "colon.tight_r", "colon.tight_l",
                    "asterisk", "semicolon"],
    "Foo::~Foo()": ["F", "o", "o", "colon.tight_r", "colon.tight_l", "asciitilde", "F", "o",
                    "o", "parenleft", "parenright"],
    "a[::-1]": ["a", "bracketleft", "colon.tight_r", "colon.tight_l", "hyphen", "one",
                "bracketright"],
    "x[:, ::-1]": ["x", "bracketleft", "colon", "comma", "space", "colon.tight_r",
                   "colon.tight_l", "hyphen", "one", "bracketright"],
    # ... after the > of a placeholder
    "<FILE>...": ["less", "F", "I", "L", "E", "greater", "period.tight_r", "period",
                  "period.tight_l"],
    # A ligature before a sign or a not on an operand, as x==-1 joins as a run
    "x!=-1": ["x", "LIG", "exclam_equal.liga", "hyphen", "one"],
    "x!==-1": ["x", "LIG", "LIG", "exclam_equal_equal.liga", "hyphen", "one"],
    "x:=-1": ["x", "colon.eq", "equal", "hyphen", "one"],
    "x<=-1": ["x", "LIG", "less_equal.liga", "hyphen", "one"],
    "x>=-1": ["x", "LIG", "greater_equal.liga", "hyphen", "one"],
    "a<>-1": ["a", "LIG", "less_greater.liga", "hyphen", "one"],
    "a||!b": ["a", "bar.tight_r", "bar.tight_l", "exclam", "b"],
    "a&&!b": ["a", "ampersand.tight_r", "ampersand.tight_l", "exclam", "b"],
    "a&&!(b)": ["a", "ampersand.tight_r", "ampersand.tight_l", "exclam", "parenleft", "b",
                "parenright"],
    "a??-1": ["a", "question.tight_r", "question.tight_l", "hyphen", "one"],
    "a?.-b": ["a", "question.tight_r", "period.tight_l", "hyphen", "b"],
}

# Input that must shape exactly as it does with calt off.
PLAIN = [
    "-", "=", "a-b", "x=y", "- -", "= =",
    # Malformed arrows: a head pointing inward, tripled or in the middle, at any length
    ">-", "-<", "=<", ">==", "==<", "=>=", "=>>", "<<==", "->>>", "<<<-", "->>-", "-<<",
    "------<", ">------", "=====<", "-->-", "->->", "-><-", "<-<", "<==<", ">=>=", ">==>",
    # A shell heredoc's <<-, whatever letter its delimiter starts with
    "cat <<-EOF", "<<-'EOF'", '<<-"EOF"', "<<-\\EOF", "cat <<-ARGS", "<<-abc",
    # An arrow before a < that opens no tag, and a - after a > that closes no short tag and
    # doesn't start -->
    "-><", "=><", "-><1", "x>-1", "a>--b", "x>->y", "0>--->1",
    # <- before a digit is less than a negative number
    "x<-1", "<-12>",
    # A run of exactly two - or _: an option, a decrement, a comment, a dunder name
    "--", "i--", "--help", "-- note", "<code>--help</code>", "<li>-- item", "__", "__init__",
    "a__b",
    # ! or : before a longer = run, and fixed ligatures touching another operator
    "!===", ":==", "!=!", "!=>", "=!=", "::=",
    "<=-", "=<=", "<>=", "<<>>", "<|>>", "<||>", "-<>",
    # One- and two-headed wave arrows followed by another operator, and Ruby's <<~ heredoc
    "~>>", "~>=", "<~>>", "<~>=", "<<~", "=~", "!~",
    # ~> before a version: Ruby's and Terraform's "at least, within"
    "~> 1.0", "~>1.0",
    # <!-- without its -- run
    "<!-",
    # Lone run characters
    "_", "#", "~", "a_b", "#!", "~/",
    # Pairs and threes touching another operator, and ** (the asterisks would touch)
    "<<<<<<<", ">>>>>>>", "////", "/***", "|||=", "&&&=", "???=", ">>>>=", ":::", ">....", ">::=",
    "https://", "....", "..", "<||", "|>>", "||||", "&&&&", "...=",
    "?..", "??.", "**", "a**b", "/**/",
    # A sign or a not that no operand follows
    "x!=-", "a&&!", "a&&!=b", "x<=--", "a??-=",
    # .. in a path, and Python's relative import
    "../x", "cd ..", "from .. import",
    # An Erlang or Elixir binary, and a heredoc, as <<-EOF is
    "<<1, 2, 3>>", '<<"abc">>', "X = <<1, 2>>", "cat <<EOF",
    # TypeScript's optional property, where ?: is no operator
    "x?: T", "[K]?: T",
    # A path's glob, a cron step and closing generics, where a pair after or before a name is
    # no operator
    "src/*", "src/**/*.js", "*/5", "Vec<Vec<u8>>", "A<B<C<D>>>", "Box<dyn Fn()>>",
    "Vec<[u8; 4]>>",
]


class LigatureShapingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_current_build()

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

    def test_a_wave_run_whose_greater_is_no_head_has_no_heads(self):
        # A > before another operator is no head, so a < before the run is none either, and
        # the run draws as it does alone, whatever its length. Runs of 1 to 5 reach every
        # piece and both ends, with and without a < before them.
        for font in FONTS:
            for count in range(1, 6):
                run = "~" * count
                for before, plain in (("", []), ("<", ["less"])):
                    text = before + run + ">="
                    with self.subTest(font=font.name, text=text):
                        self.assertEqual(names(font, text),
                                         plain + names(font, run) + ["greater", "equal"])

    def test_a_run_right_after_a_short_tag_joins_as_it_does_alone(self):
        # >- is otherwise an inward head. A short tag opens, closes or closes itself. The rules
        # cover names of up to 10 letters and digits, enough for HTML's longest (blockquote,
        # figcaption): one name of each length.
        elements = ["a", "h1", "div", "code", "table", "button", "article", "fieldset",
                    "plaintext", "blockquote"]
        for font in FONTS:
            run = names(font, "---")
            for element in elements:
                for tag in (f"<{element}>", f"</{element}>", f"<{element}/>"):
                    with self.subTest(font=font.name, tag=tag):
                        self.assertEqual(names(font, tag + "---"), names(font, tag) + run)

    def test_a_comment_closes_after_a_tag_ending_in_any_character_a_tag_can_end_in(self):
        # A tag's last character before > is a letter or digit, a slash, or a closing quote.
        tags = ["<!--<input disabled>", '<!--<img src="x"/>', '<!--<img alt="x">',
                "<!--<a href='x'>", "<!--<h1>"]
        arrow = hyphens(3, right="greater.arrow")
        for font in FONTS:
            for tag in tags:
                with self.subTest(font=font.name, tag=tag):
                    self.assertEqual(names(font, tag + "-->")[-3:], arrow)

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


class SeamTest(unittest.TestCase):
    """The pieces of a run meet across each seam. On the regular and the bold: the italic's
    pieces are the regular's sheared about one pivot (tests/test_make_italic.py), so they meet
    as those do; the bold's are the regular's grown by the pen, which can grow two pieces'
    ends apart where they leave the seam at different slants."""
    sfd = SFD

    @classmethod
    def setUpClass(cls):
        require_current_build()
        cls.font = fontforge.open(str(cls.sfd))

    def test_joined_pieces_meet_without_a_step(self):
        # A piece that runs on is cut flat at its cell's edge, and the next begins with the
        # same edge or covers it; any step between them shows as a notch in the stroke.
        # A stroke hides an edge when it reaches a quarter of a stroke past both its ends, as
        # the inner head of ->> does the shaft's end.
        _, y0, _, y1 = self.font["hyphen"].boundingBox()
        cover = (y1 - y0) / 4
        for text in LIGATED:
            for left, right in itertools.pairwise(names(REGULAR, text)):
                with self.subTest(text=text, left=left, right=right):
                    first, second = ink(self.font, left), ink(self.font, right)
                    self.assertEqual(unmet(seam(first, ADVANCE + OVERLAP), second,
                                           -OVERLAP, 1, cover), [])
                    self.assertEqual(unmet(seam(second, -OVERLAP), first,
                                           ADVANCE + OVERLAP, -1, cover), [])


class BoldSeamTest(SeamTest):
    sfd = BOLD_SFD


class TightPairTest(unittest.TestCase):
    """A tightened pair keeps at least the white two symbols side by side keep (twice
    SYMBOL_SIDE), so it reads as two characters, not one blot. On the regular and the bold,
    whose pen grows the two toward each other; the italic's are the regular's sheared."""
    sfd = SFD
    TIGHT = frozenset(f"{name}.{side}" for name in TIGHT_KEEP for side in ("tight_r", "tight_l"))
    JOINED = frozenset({("plus.tight_r", "plus.tight_l")})  # ++'s bars join, as Fira Code's do

    @classmethod
    def setUpClass(cls):
        require_current_build()
        cls.font = fontforge.open(str(cls.sfd))

    def test_tightened_glyphs_keep_white_toward_their_neighbours(self):
        for text in LIGATED:
            for left, right in itertools.pairwise(names(REGULAR, text)):
                first, second = ink(self.font, left), ink(self.font, right)
                if ({left, right}.isdisjoint(self.TIGHT) or (left, right) in self.JOINED
                        or not len(first) or not len(second)):  # a space beside it
                    continue
                with self.subTest(text=text, left=left, right=right):
                    white = gap(first, geo.moved(second, ADVANCE, 0))
                    self.assertGreaterEqual(white, 2 * SYMBOL_SIDE)


class BoldTightPairTest(TightPairTest):
    sfd = BOLD_SFD


class NerdFontTest(NerdBuilds, unittest.TestCase):
    """Nerd Fonts builds keep the ligatures through the patcher.

    The release steps in CLAUDE.md run the Nerd Fonts builds after building the fonts.
    """

    def test_patched_fonts_keep_the_ligatures(self):
        for font in self.fonts:
            for text in ("->", "<====>", "!=", ">=", "~~~", "::"):
                with self.subTest(font=font.name, text=text):
                    self.assertEqual(names(font, text), LIGATED[text])

    def test_patched_fonts_draw_the_current_ligatures(self):
        # Git keeps no mtimes, so compare with the plain fonts, which LigatureShapingTest
        # requires to be current: a stale build still shapes, but draws the old outlines.
        text = " ".join(LIGATED)  # reaches every generated glyph
        plain = {(style_of(font), font.suffix): font for font in FONTS}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                style = style_of(nerd)
                self.assertEqual(extents(nerd, text), extents(plain[style, nerd.suffix], text))


if __name__ == "__main__":
    unittest.main()
