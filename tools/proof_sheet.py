"""Render a review sheet: Comic Caret next to its earlier build and the reference fonts.

Usage: python3 tools/proof_sheet.py OUTDIR [FONT ...]

Writes OUTDIR/index.html and the images it shows; open the page in a browser. With no FONT
arguments it shows fonts/ComicCaret-Regular.ttf, build/cache/before/ComicCaret-Regular.ttf if
it exists (saved before the legibility pass), and every font in build/cache/reference/. Images
are rendered with hb-view and are not committed.
"""
import argparse
import html
import pathlib
import struct
import subprocess

from project import ROOT

BUILT = ROOT / "fonts" / "ComicCaret-Regular.ttf"
BEFORE = ROOT / "build" / "cache" / "before" / "ComicCaret-Regular.ttf"
REFERENCE_DIR = ROOT / "build" / "cache" / "reference"
SMALL = (12, 13, 14, 16)  # px: common editor and terminal sizes
MAGNIFY = 3               # the small sizes are also shown this much larger, pixels kept hard
LARGE = 64                # px: the outlines themselves

# (title, text, hb-view features): look-alikes with calt off, so each character shows as
# itself, and code with the default features, so the ligatures show.
BLOCKS = (
    ("Look-alikes", "Il1|i!j 0Oo .,:; ()[]{} ceo aoq gq9 rn m\n"
                    "MAX_BUF_SIZE HIDEN nhu dbqp EFL KRZ 1578\n"
                    "ĺļĹĻ ÑÙŨŃ ĄĘĮŲąęįų şș ďť ∃∄", "-calt"),
    ("Code", "if (x1 != l0) { return O0; } // Il1|\n"
             "let rn = m.clone(); arr[i] = a:b; c.e\n"
             "fn get_g6(q: &str) -> Option<8B> {\n"
             "const MAX_ID = {I: 1, l: 0}; // i j", None),
)

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Proof sheet</title>
<style>
  body {{ margin: 16px; background: #fff; color: #111; font: 14px/1.4 system-ui, sans-serif; }}
  section {{ margin-bottom: 32px; }}
  figure {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; margin: 8px 0; }}
  figcaption {{ flex: 0 0 18em; color: #555; }}
  .magnified {{ image-rendering: pixelated; }}
</style>
{body}
</html>
"""


def default_fonts():
    references = sorted(p for p in REFERENCE_DIR.glob("*") if p.suffix in (".otf", ".ttf"))
    return [BUILT, *([BEFORE] if BEFORE.exists() else []), *references]


def label(font):
    """The font's path from the repository root, or its file name if it lies elsewhere."""
    path = font.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name


def render(font, text, size, features, path):
    """Render `text` to the PNG at `path`; returns the image's (width, height)."""
    command = ["hb-view", str(font), f"--font-size={size}", "--margin=4",
               f"--output-file={path}", f"--text={text}"]  # --text=: text may start with '-'
    if features:
        command.append(f"--features={features}")
    subprocess.run(command, check=True)
    with open(path, "rb") as png:
        return struct.unpack(">II", png.read(24)[16:24])  # from the PNG's IHDR chunk


def sheet(fonts, outdir):
    sections = []
    for b, (title, text, features) in enumerate(BLOCKS):
        for size in (*SMALL, LARGE):
            rows = []
            for f, font in enumerate(fonts):
                name = f"{b}-{size}-{f}.png"
                width, height = render(font, text, size, features, outdir / name)
                alt = html.escape(f"{title} in {label(font)} at {size} px", quote=True)
                images = f'<img src="{name}" width="{width}" height="{height}" alt="{alt}">'
                if size in SMALL:
                    images += (f'<img class="magnified" src="{name}" width="{width * MAGNIFY}"'
                               f' height="{height * MAGNIFY}" alt="{alt}, magnified">')
                rows.append(f"<figure><figcaption>{html.escape(label(font))}</figcaption>"
                            f"{images}</figure>")
            sections.append(f"<section><h2>{html.escape(title)}, {size} px</h2>\n"
                            + "\n".join(rows) + "</section>")
    return PAGE.format(body="\n".join(sections))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument("fonts", nargs="*", type=pathlib.Path, help="default: see above")
    args = parser.parse_args()
    fonts = args.fonts or default_fonts()
    missing = [str(font) for font in fonts if not font.exists()]
    if missing:
        parser.error(f"no such font: {', '.join(missing)}")
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "index.html").write_text(sheet(fonts, args.outdir), encoding="utf-8")
    print(f"Wrote {args.outdir / 'index.html'}")


if __name__ == "__main__":
    main()
