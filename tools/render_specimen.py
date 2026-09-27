"""Render the README's images into docs/images/.

Usage: python3 tools/render_specimen.py

GitHub READMEs can't load web fonts, so the SVGs are committed; rerun this after changing
glyphs or ligatures and commit the result. The images are laid out glyph by glyph from
HarfBuzz's shaping, so samples can be spaced out and sized freely while ligatures still form.
They follow the viewer's light or dark color scheme, in GitHub's colors.
"""
import argparse
import functools
import json
import re
import subprocess
import sys

from project import ADVANCE, ROOT, SFD

FONT = ROOT / "fonts" / "ComicCaret-Regular.ttf"
OUT = ROOT / "docs" / "images"
WIDTH = 800               # px; within a README column at 1:1
MARGIN, PADDING = 24, 20  # around each image, and inside its panel
CAP_HEIGHT = 0.668        # the top of H, in em
LINE = 1.25               # the line box, in em: hhea and typo ascent 900 and descent 350
ASCENT = 0.72             # the ascender's share of a line: 900 of 1250
LIGHT, DARK = "#1f2328", "#e6edf3"  # GitHub's text colors
COLORS = {  # class: (light, dark), GitHub's syntax and terminal colors
    "comment": ("#59636e", "#9198a1"),
    "keyword": ("#cf222e", "#ff7b72"),
    "type": ("#953800", "#ffa657"),
    "function": ("#6639ba", "#d2a8ff"),
    "number": ("#0550ae", "#79c0ff"),
    "string": ("#0a3069", "#a5d6ff"),
    "muted": ("#59636e", "#9198a1"),
    "green": ("#1a7f37", "#3fb950"),
    "red": ("#d1242f", "#f85149"),
    "yellow": ("#9a6700", "#d29922"),
    "blue": ("#0969da", "#58a6ff"),
    "purple": ("#8250df", "#bc8cff"),
}
PANEL = {"fill": ("#f6f8fa", "#151b23"), "stroke": ("#d1d9e0", "#3d444d")}  # a code block's

# The look-alikes: the groups "Why Comic Caret" tells apart, large enough to see how.
LOOKALIKES = ("Il1|", "O0o", "ij", ":;", "()[]{}")

# The specimen: a large Aa beside spaced-out rows of samples, above a terminal whose prompt,
# progress bar and table show the symbols at work. Terminal lines mark colored spans as
# {class:text}.
SAMPLES = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789 (){}[]<>=+-*/@&",
    "Il1| O0o ;: àéîõüçñøłşßæœ",
    "→⇒↔ ≠≈≤≥∞ ±×÷ €£ ©½λ",
)
TERMINAL = (
    "{blue:~/comic-caret} {muted:on} {purple:main} {muted:⇡1 ⇣2}",
    "{green:❯} cargo test",
    "{blue:⠹} Compiling naïve-café v0.1.0",
    "{purple:━━━━━━━━━━━━━━━━╸}{muted:━━━━━━━━━}  58%",
    "{green:✔} 41 passed  {red:✖} 1 failed",
    "{yellow:⚠} 3 warnings  {blue:ℹ} 2 skipped",
)
TABLE = (  # right of the terminal lines, its lines drawn muted
    "╭───────────┬─────────╮",
    "│ city      │ load    │",
    "├───────────┼─────────┤",
    "│ Łódź      │ ▂▄▆█▇▅▃ │",
    "│ São Paulo │ ▁▃▅▇█▆▄ │",
    "╰───────────┴─────────╯",
)

# The ligatures: each group's sequences above the characters typed for them, then code that
# uses them.
LIGATURES = (
    ("Arrows", ("->", "=>", "<->", "<==", "--->", "->>", ">=>", "~>", "<~")),
    ("Compare", ("==", "!=", "!==", "<=", ">=", ":=", "<>")),
    ("Lines", ("---", "===", "___", "###", "~~~")),
    ("Pipes, tags", ("|>", "<|", "<|>", "<!--", "-->")),
    ("Together", ("::", "...", "&&", "||", "//", "??", "?.", "<<", ">>=", "<$>", "..=")),
)
CODE = (
    "// The users seen in the last `days` days, with a name.",
    "export const recent = (users: User[], days = 7): User[] =>",
    "  users.filter((u) => u.lastSeen?.getTime() >= since(days))",
    "       .map((u) => ({ ...u, name: u.name ?? \"anonymous\" }));",
    "",
    "if (recent(all).length !== 0 && verbose) log(\"found\", count);",
)
# Enough of TypeScript for CODE. At each position the first class that matches wins; text that
# none match, operators included, keeps the text color.
TYPESCRIPT = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in {
    "comment": r"//.*",
    "string": r'"[^"]*"',
    "keyword": r"\b(?:export|const|if)\b",
    "type": r"\b[A-Z]\w*\b",
    "function": r"\b\w+(?=\()",
    "number": r"\b\d+\b",
}.items()))


def harfbuzz(tool, text, features, *options):
    command = [tool, str(FONT), f"--text={text}", f"--features={features}", *options]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout  # --text=: text may start with '-'


def shape(text, features):
    """hb-shape's glyphs for one line: dicts with the glyph name "g" and cluster "cl"."""
    return json.loads(harfbuzz("hb-shape", text, features, "--output-format=json"))


@functools.cache
def glyphs(text, calt):
    """(path, cell, cluster) for each glyph with ink that HarfBuzz draws for one line of
    `text`: the path in font units, y down from the glyph's origin on the baseline, the cell it
    starts in, and the character it came from."""
    features = "calt" if calt else "-calt"
    shaped = shape(text, features)
    if missing := sorted({text[glyph["cl"]] for glyph in shaped if glyph["g"] == ".notdef"}):
        raise ValueError(f"the font has no glyph for {' '.join(missing)}")
    # --logical: set the line in its own box, not widened to ink beyond it (box drawing's
    # overlap), so glyphs land on their pen positions.
    svg = harfbuzz("hb-view", text, features, "--font-size=1000", "--margin=0", "--logical",
                   "--output-format=svg")
    paths = {glyph_id: re.sub(r"-?\d+\.\d+", lambda n: str(round(float(n.group()))), path)
             for glyph_id, path in re.findall(r'<g id="(glyph-[\d-]+)">\s*<path[^>]*\sd="([^"]*)"',
                                              svg)}
    # hb-view skips blank glyphs, so match the ones it draws to HarfBuzz's by pen position,
    # which differs for every glyph since every glyph advances a cell.
    clusters, pen = {}, 0
    for glyph in shaped:
        clusters[pen + glyph["dx"]] = glyph["cl"]
        pen += glyph["ax"]
    return [(paths[glyph_id], round(float(x) / ADVANCE), clusters[round(float(x))])
            for glyph_id, x in re.findall(r'<use xlink:href="#(glyph-[\d-]+)" x="([-\d.]+)"', svg)
            if glyph_id in paths]


def tenth(value):
    """`value` rounded to 0.1, written without a trailing .0."""
    return f"{round(value, 1) + 0.0:.1f}".removesuffix(".0")  # + 0.0: no -0


def stylesheet(classes):
    """Glyphs take the text color, or their class's color, from the viewer's scheme; so do
    panels."""
    colors = {"svg": (LIGHT, DARK)} | {f".{name}": COLORS[name] for name in classes}

    def rules(scheme):
        css = "".join(f"{selector}{{fill:{pair[scheme]}}}" for selector, pair in colors.items())
        return css + ".panel{" + ";".join(f"{k}:{v[scheme]}" for k, v in PANEL.items()) + "}"

    return f"<style>{rules(0)}@media (prefers-color-scheme:dark){{{rules(1)}}}</style>"


class Layout:
    """Lines of glyphs placed freely, each glyph defined once and drawn scaled to its size."""

    def __init__(self):
        self.paths, self.drawn, self.classes = {}, [], {}

    def line(self, x, baseline, text, size, gap=0, calt=False, classes=None):
        """Draw one line of `text` from x on the baseline, `gap` px between cells. `classes`
        colors every glyph, as a class name, or each by its character, as a list."""
        if isinstance(classes, str) or classes is None:
            classes = [classes] * len(text)
        pitch = ADVANCE * size / 1000 + gap
        for path, cell, cluster in glyphs(text, calt):
            self.glyph(path, x + cell * pitch, baseline, size, classes[cluster])

    def spans(self, x, baseline, spans, size):
        """Draw (class or None, text) spans one after another."""
        text = "".join(chars for _, chars in spans)
        self.line(x, baseline, text, size,
                  classes=[name for name, chars in spans for _ in chars])

    def glyph(self, path, x, baseline, size, name):
        glyph_id = self.paths.setdefault(path, f"g{len(self.paths)}")
        if name:
            self.classes[name] = None
        attribute = f' class="{name}"' if name else ""
        self.drawn.append(f'<use xlink:href="#{glyph_id}" transform="translate({tenth(x)} '
                          f'{tenth(baseline)}) scale({size / 1000:g})"{attribute}/>')

    def panel(self, y, height):
        """A code block's rounded box across the image, from y down."""
        self.drawn.append(f'<rect class="panel" x="{MARGIN}" y="{tenth(y)}" '
                          f'width="{WIDTH - 2 * MARGIN}" height="{tenth(height)}" rx="8"/>')

    def svg(self, height):
        defs = "".join(f'<path id="{glyph_id}" d="{path}"/>'
                       for path, glyph_id in self.paths.items())
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" '
                f'height="{round(height)}" viewBox="0 0 {WIDTH} {round(height)}">'
                f'{stylesheet(self.classes)}<defs>{defs}</defs>' + "".join(self.drawn)
                + "</svg>\n")


def marked(line):
    """(class or None, text) spans of a TERMINAL line."""
    return [(span.group(1), span.group(2)) if span.group(1) else (None, span.group())
            for span in re.finditer(r"\{(\w+):([^}]*)\}|[^{]+", line)]


def ruled(line):
    """(class or None, text) spans of a TABLE line, its box drawing muted."""
    return [("muted", rule) if rule else (None, text)
            for rule, text in re.findall(r"([─-╿]+)|([^─-╿]+)", line)]


def highlighted(line):
    """The TYPESCRIPT class of each character of `line`, or None."""
    classes = [None] * len(line)
    for token in TYPESCRIPT.finditer(line):
        classes[token.start():token.end()] = [token.lastgroup] * len(token.group())
    return classes


def lookalikes():
    """The look-alikes image, as SVG: each group spaced out a little, the row centered like
    the images are on the page."""
    layout = Layout()
    size, gap, between = 52, 4, 46  # px: the letters, between their cells, between groups
    widths = [len(group) * (ADVANCE * size / 1000 + gap) - gap for group in LOOKALIKES]
    x = (WIDTH - sum(widths) - between * (len(LOOKALIKES) - 1)) / 2
    baseline = MARGIN + CAP_HEIGHT * size
    for group, width in zip(LOOKALIKES, widths):
        layout.line(x, baseline, group, size, gap)
        x += width + between
    return layout.svg(baseline + (1 - ASCENT) * LINE * size + MARGIN)  # room for j's descender


def specimen():
    """The README's specimen, as SVG."""
    layout = Layout()
    right = WIDTH - MARGIN - PADDING  # where the table, and the longest row, end

    size, lead = 21, 34
    top = MARGIN + 10  # the rows' cap height starts here
    first = top + CAP_HEIGHT * size
    last = first + (len(SAMPLES) - 1) * lead
    hero = (last - top) / CAP_HEIGHT  # an Aa as tall as the rows, from cap height to baseline
    layout.line(MARGIN + 4, last, "Aa", hero)
    x = MARGIN + 4 + 2 * ADVANCE * hero / 1000 + MARGIN
    gap = (right - x) / max(map(len, SAMPLES)) - ADVANCE * size / 1000
    for i, row in enumerate(SAMPLES):
        layout.line(x, first + i * lead, row, size, gap)

    # Lines 1.45 em apart, within the reach of box drawing's verticals, so the table joins.
    size, lead = 18, 26
    top = last + 2 * PADDING
    height = 2 * PADDING + len(TERMINAL) * lead
    layout.panel(top, height)
    baseline = top + PADDING + ASCENT * lead
    for i, line in enumerate(TERMINAL):
        layout.spans(MARGIN + PADDING, baseline + i * lead, marked(line), size)
    x = right - len(TABLE[0]) * ADVANCE * size / 1000
    for i, line in enumerate(TABLE):
        layout.spans(x, baseline + i * lead, ruled(line), size)
    return layout.svg(top + height + MARGIN)


def ligatures():
    """The ligatures image, as SVG."""
    layout = Layout()
    size, caption, drop, gap, lead = 24, 13, 22, 26, 62  # drop: from a sequence to its caption
    left = MARGIN + 120  # the sequences start right of the group labels
    baseline = MARGIN + 28
    for label, sequences in LIGATURES:
        layout.line(MARGIN + 4, baseline, label, 14, classes="muted")
        x = left
        for sequence in sequences:
            width = len(sequence) * ADVANCE * size / 1000
            if x + width > WIDTH - MARGIN - PADDING:
                x, baseline = left, baseline + lead
            layout.line(x, baseline, sequence, size, calt=True)
            below = len(sequence) * ADVANCE * caption / 1000
            layout.line(x + (width - below) / 2, baseline + drop, sequence, caption,
                        classes="muted")
            x += width + gap
        baseline += lead

    top = baseline - lead + drop + 2 * PADDING
    size, lead = 17, 25
    height = 2 * PADDING + len(CODE) * lead
    layout.panel(top, height)
    for i, line in enumerate(CODE):
        if line:
            layout.line(MARGIN + PADDING, top + PADDING + ASCENT * lead + i * lead, line, size,
                        calt=True, classes=highlighted(line))
    return layout.svg(top + height + MARGIN)


IMAGES = {"specimen": specimen, "lookalikes": lookalikes, "ligatures": ligatures}


def main():
    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args()
    if not FONT.exists() or FONT.stat().st_mtime < SFD.stat().st_mtime:
        sys.exit(f"{FONT.name} is missing or older than {SFD.name}; run ./build.sh")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, draw in IMAGES.items():
        try:
            svg = draw()
        except ValueError as error:
            sys.exit(f"{name}: {error}")
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    print(f"Wrote {', '.join(f'{OUT.relative_to(ROOT)}/{name}.svg' for name in IMAGES)}")


if __name__ == "__main__":
    main()
