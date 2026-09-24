"""Render the README's specimen images into docs/images/.

Usage: python3 tools/render_specimen.py

GitHub READMEs can't load web fonts, so the SVGs are committed; rerun this after changing
glyphs and commit the result. Each image follows the viewer's light or dark color scheme, and
the code specimen is highlighted in GitHub's syntax colors.
"""
import argparse
import json
import re
import subprocess
import sys

from project import ROOT, SFD

FONT = ROOT / "fonts" / "ComicCaret-Regular.ttf"
OUT = ROOT / "docs" / "images"
SIZE = 24             # px; the widest image stays within a README column at 1:1
LIGATURE_COLUMN = 28  # characters in the ligatures image's calt-off column
LIGHT, DARK = "#1f2328", "#e6edf3"  # GitHub's text colors
SYNTAX_COLORS = {  # class: (light, dark), GitHub's syntax colors
    "comment": ("#59636e", "#9198a1"),
    "keyword": ("#cf222e", "#ff7b72"),
    "type": ("#953800", "#ffa657"),
    "function": ("#6639ba", "#d2a8ff"),
    "number": ("#0550ae", "#79c0ff"),
}

# Enough of Rust for SPECIMEN, one line at a time. At each position the first class that
# matches wins; text that none match, operators included, keeps the text color.
RUST = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in {
    "comment": r"//.*",
    "keyword": r"\b(?:use|fn|let|mut|for|in)\b",
    "type": r"\b(?:[A-Z]\w*|str|usize)\b",
    "function": r"\b\w+(?=\()",
    "number": r"\b\d+\b",
}.items()))

SPECIMEN = """\
use std::collections::HashMap;

// Count the words that appear at least `min` times.
fn frequent(text: &str, min: usize) -> Vec<(&str, usize)> {
    let mut counts = HashMap::new();
    for word in text.split_whitespace() {
        *counts.entry(word).or_insert(0) += 1;
    }
    counts.into_iter().filter(|&(_, n)| n >= min).collect()
}"""

CHARACTERS = """\
ABCDEFGHIJKLMNOPQRSTUVWXYZ
abcdefghijklmnopqrstuvwxyz
0123456789 +-*/=<>_|\\~^
()[]{} .,:;!? '"` @#$%&
Il1| O0o ij ,; ¡¿ «» ‹›
ÀÁÂÃÄÅ ÇĆČ ÈÉÊË ÑŃŇ ÖŐ ŠŚ ŽŹŻ
àáâãäå çćč èéêë ñńň öő šś žźż
ĄĘĮŲ ąęįų ȘșȚț ďť ÆæŒœÞþ λΛ
ß Øø Łł Đđ Ħħ ½ © ™ § ¹²³
← ↑ → ↓ ≤ ≥ × ± − ∀ ∃ € £ ¥ … •
≠ ≈ ≡ ∞ ↔ ↕ ↗ ⇒ ⇔ ↦ ✓ ✗ \ufffd
┌──────────┐
│ ⠋⠙⠹⠸⠼⠴⠦⠧ │
└──────────┘"""

SEQUENCES = (
    "-> <- <-> => <== <=>",
    "---> <====> ==> <--",
    "== --- __ ### ~~~",
    "!= !== <= >= :=",
    "|> <| :: ... && ++",
    "// /* */ << >> ?? ||",
)

# name: (text, hb-view features, syntax). Each ligatures line shows its sequences twice, and
# the feature's cluster range, which counts from the start of each line, turns calt off on the left.
IMAGES = {
    "specimen": (SPECIMEN, None, RUST),
    "ligatures": ("\n".join(f"{s:<{LIGATURE_COLUMN}}{s}" for s in SEQUENCES),
                  f"-calt[0:{LIGATURE_COLUMN}]", None),
    "characters": (CHARACTERS, "-calt", None),
}


def harfbuzz(tool, text, features, *options):
    command = [tool, str(FONT), f"--text={text}", *options]  # --text=: text may start with '-'
    if features:
        command.append(f"--features={features}")
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def shape(text, features=None):
    """hb-shape's glyphs for each line of `text`: dicts with the glyph name "g" and cluster "cl"."""
    output = harfbuzz("hb-shape", text, features, "--output-format=json")
    return [json.loads(line) if line else [] for line in output.splitlines()]  # "": empty line


def missing_characters(text):
    """The characters of `text` that the font has no glyph for, which would show as boxes."""
    return sorted({line[glyph["cl"]]
                   for line, glyphs in zip(text.splitlines(), shape(text), strict=True)
                   for glyph in glyphs if glyph["g"] == ".notdef"})


def syntax_classes(text, features, syntax):
    """The `syntax` class of each glyph hb-view draws for `text`, in drawing order; None for
    glyphs no class matches."""
    def line_classes(line):
        classes = [None] * len(line)
        for token in syntax.finditer(line):
            classes[token.start():token.end()] = [token.lastgroup] * len(token.group())
        return classes

    return [line_classes(line)[glyph["cl"]]  # hb-shape clusters count characters
            for line, glyphs in zip(text.splitlines(), shape(text, features), strict=True)
            for glyph in glyphs]


def stylesheet(classes):
    """Glyphs take the text color, or their class's syntax color, from the viewer's scheme."""
    colors = {"svg": (LIGHT, DARK)} | {f".{name}": SYNTAX_COLORS[name] for name in classes}

    def rules(scheme):
        return "".join(f"{selector}{{fill:{pair[scheme]}}}" for selector, pair in colors.items())

    return f"<style>{rules(0)}@media (prefers-color-scheme:dark){{{rules(1)}}}</style>"


def themed(svg, glyph_classes=None):
    """Color cairo's SVG through a light/dark stylesheet and round its coordinates to 0.1 px.

    `glyph_classes` gives each glyph, in drawing order, a syntax class or None.
    """
    svg = re.sub(r' fill="[^"]*" fill-opacity="1"', "", svg)
    if glyph_classes is not None:
        classes = iter(glyph_classes)

        def classed(use):
            name = next(classes, None)
            return f'<use class="{name}"' if name else use.group()

        svg, uses = re.subn(r"<use(?=\s)", classed, svg)
        if uses != len(glyph_classes):
            raise ValueError(f"the SVG draws {uses} glyphs, not {len(glyph_classes)}")

    def tenth(number):
        return f"{round(float(number.group()), 1) + 0.0:.1f}".removesuffix(".0")  # + 0.0: no -0

    def rounded(attribute):
        return attribute.group(1) + re.sub(r"-?\d+\.\d+", tenth, attribute.group(2)) + '"'

    svg = re.sub(r'(\s(?:d|x|y|width|height|viewBox)=")([^"]*)"', rounded, svg)
    style = stylesheet(dict.fromkeys(name for name in glyph_classes or () if name))
    return re.sub(r"(<svg\s[^>]*>)", lambda svg_tag: svg_tag.group() + style, svg, count=1)


def main():
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    if not FONT.exists() or FONT.stat().st_mtime < SFD.stat().st_mtime:
        sys.exit(f"{FONT.name} is missing or older than {SFD.name}; run ./build.sh")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (text, features, syntax) in IMAGES.items():
        if missing := missing_characters(text):
            sys.exit(f"{name}: the font has no glyph for {' '.join(missing)}")
        svg = harfbuzz("hb-view", text, features, f"--font-size={SIZE}", "--margin=16",
                       "--output-format=svg", "--background=00000000")
        classes = syntax_classes(text, features, syntax) if syntax else None
        (OUT / f"{name}.svg").write_text(themed(svg, classes), encoding="utf-8")
    print(f"Wrote {', '.join(f'{OUT.relative_to(ROOT)}/{name}.svg' for name in IMAGES)}")


if __name__ == "__main__":
    main()
