"""Compare where glyphs sit in Comic Caret and in the reference fonts, in Comic Caret's units.

Usage: python3 tools/compare_glyphs.py [--anchor cap|x] TEXT [FONT ...]

With no FONT arguments it reads src/ComicCaret-Regular.sfd and every font in
build/cache/reference/ (see "Designing glyphs" in CLAUDE.md). For each character of TEXT it
prints each font's ink box: x scaled so the advance becomes 550, with the center's offset from
the cell center, and y scaled so the reference's cap height (or x-height, with --anchor x)
matches ours. Cap and x-height are the tops of H and x, as in our OS/2 values.
"""
import argparse
import contextlib
import os
import pathlib
import sys

import fontforge

ROOT = pathlib.Path(__file__).resolve().parent.parent
OURS = ROOT / "src" / "ComicCaret-Regular.sfd"
REFERENCE_DIR = ROOT / "build" / "cache" / "reference"
ADVANCE = 550


@contextlib.contextmanager
def quiet_stderr():
    """Silence FontForge's name-vs-codepoint notes, which it prints from C while loading."""
    saved = os.dup(2)
    with open(os.devnull, "w") as devnull:
        os.dup2(devnull.fileno(), 2)
    try:
        yield
    finally:
        os.dup2(saved, 2)
        os.close(saved)


class Font:
    def __init__(self, path, anchor):
        with quiet_stderr():
            self.font = fontforge.open(str(path))
        self.name = pathlib.Path(path).stem
        self.cap = self.font["H"].boundingBox()[3]
        self.xheight = self.font[ord("x")].boundingBox()[3]
        self.sx = ADVANCE / self.font["H"].width
        self.anchor = self.cap if anchor == "cap" else self.xheight
        # FontForge may store hhea values as offsets from the em's ascent and descent.
        self.line_top = self.font.hhea_ascent + (self.font.ascent if self.font.hhea_ascent_add else 0)
        self.line_bottom = self.font.hhea_descent - (self.font.descent if self.font.hhea_descent_add else 0)

    def set_target(self, target):
        self.sy = target / self.anchor

    def row(self, char):
        code = ord(char)
        if code not in self.font:
            return "missing"
        glyph = self.font[code]
        if glyph.width * self.sx != ADVANCE:
            note = f"  (advance {glyph.width * self.sx:.0f})"
        else:
            note = ""
        x0, y0, x1, y1 = glyph.boundingBox()
        if (x0, y0, x1, y1) == (0, 0, 0, 0):
            return "empty" + note
        center = round((x0 + x1) / 2 * self.sx - ADVANCE / 2)
        return (f"x {x0 * self.sx:5.0f}..{x1 * self.sx:<5.0f} center {center:+4d}   "
                f"y {y0 * self.sy:5.0f}..{y1 * self.sy:.0f}{note}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--anchor", choices=("cap", "x"), default="cap",
                        help="scale y by cap height (default) or x-height")
    parser.add_argument("text", help="characters to compare")
    parser.add_argument("fonts", nargs="*", help="fonts to compare; the first sets the scale")
    args = parser.parse_args()

    paths = args.fonts or [OURS, *sorted(p for p in REFERENCE_DIR.glob("*") if p.suffix in (".otf", ".ttf"))]
    if len(paths) < 2:
        sys.exit(f"No reference fonts in {REFERENCE_DIR}; see \"Designing glyphs\" in CLAUDE.md.")
    fonts = [Font(path, args.anchor) for path in paths]
    for font in fonts:
        font.set_target(fonts[0].anchor)
    width = max(len(font.name) for font in fonts)

    for font in fonts:
        print(f"{font.name:{width}}  cap {font.cap * font.sy:4.0f}  x-height {font.xheight * font.sy:4.0f}"
              f"  line box {font.line_bottom * font.sy:.0f}..{font.line_top * font.sy:.0f}")
    for char in args.text:
        print(f"\n{char} U+{ord(char):04X}")
        for font in fonts:
            print(f"  {font.name:{width}}  {font.row(char)}")


if __name__ == "__main__":
    main()
