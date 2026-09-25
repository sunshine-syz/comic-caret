"""Render a review sheet: Comic Caret next to an earlier build of itself and the reference fonts.

Usage: python3 tools/proof_sheet.py OUTDIR [FONT ...] [--before REV] [--text TEXT ...]
                                    [--features LIST] [--line-height EM ...]

Writes OUTDIR/index.html and the images it shows; open the page in a browser. With no FONT
arguments it shows fonts/ComicCaret-Regular.ttf and every font in build/cache/reference/.
--before REV adds, second, the font built from the SFD at that commit (HEAD: the last one).
Images are rendered with hb-view and are not committed.
"""
import argparse
import dataclasses
import datetime
import html
import pathlib
import struct
import subprocess
import sys
import tempfile

from project import ROOT, SFD

BUILT = ROOT / "fonts" / "ComicCaret-Regular.ttf"
REFERENCE_DIR = ROOT / "build" / "cache" / "reference"
SFD_PATH = SFD.relative_to(ROOT).as_posix()  # as git names it
SMALL = (12, 13, 14, 16)  # px: common editor and terminal sizes
MAGNIFY = 3               # the small sizes are also shown this much larger, pixels kept hard
LARGE = 64                # px: the outlines themselves
MARGIN = 4                # px of blank around each image

# (title, text, hb-view features): look-alikes with calt off, so each character shows as
# itself, and code with the default features, so the ligatures show.
BLOCKS = (
    ("Look-alikes", ("Il1|i!j 0Oo .,:; ()[]{} ceo aoq gq9 rn m\n"
                     "MAX_BUF_SIZE HIDEN nhu dbqp EFL KRZ 1578\n"
                     "ĺļĹĻ ÑÙŨŃ ĄĘĮŲąęįų şș ďť ∃∄"), "-calt"),
    ("Code", ("if (x1 != l0) { return O0; } // Il1|\n"
              "let rn = m.clone(); arr[i] = a:b; c.e\n"
              "fn get_g6(q: &str) -> Option<8B> {\n"
              "const MAX_ID = {I: 1, l: 0}; // i j"), None),
)

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Proof sheet</title>
<style>
  body {{ margin: 16px; background: #fff; color: #111; font: 14px/1.4 system-ui, sans-serif; }}
  section {{ margin-bottom: 32px; }}
  h2 {{ white-space: pre-wrap; }}
  h3 {{ font-size: 14px; margin: 16px 0 4px; }}
  figure {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; margin: 8px 0; }}
  figcaption {{ flex: 0 0 18em; }}
  .note {{ color: #555; }}
  .magnified {{ image-rendering: pixelated; }}
</style>
<p class="note">Rendered {date} at {commit}.</p>
{body}
</html>
"""


@dataclasses.dataclass(frozen=True)
class Font:
    path: pathlib.Path
    note: str       # where it comes from: its path, or the commit it was built from
    family: str
    upem: int
    ascender: int
    descender: int  # negative: below the baseline


def load(path, note):
    """The font at `path`, with the facts about it that hb-info reports."""
    output = subprocess.run(["hb-info", "--font-size=upem", "--show-family", "--show-upem",
                             "--show-extents", str(path)],
                            check=True, capture_output=True, text=True).stdout
    info = dict(line.split(": ", 1) for line in output.splitlines())
    return Font(path, note, info["Family"], int(info["Units-Per-EM"]),
                int(info["Ascender"]), int(info["Descender"]))


def git(*args, check=True, text=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check, capture_output=True, text=text)


def resolve(parser, rev):
    """The full hash of the commit `rev` names, and how to label its font. Exits through
    `parser` if there is no such commit or it has no SFD."""
    result = git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}", check=False)
    if result.returncode:
        parser.error(f"not a commit: {rev}")
    commit = result.stdout.strip()
    if git("cat-file", "-e", f"{commit}:{SFD_PATH}", check=False).returncode:
        parser.error(f"{rev} has no {SFD_PATH}")
    short = git("rev-parse", "--short", commit).stdout.strip()
    return commit, rev if commit.startswith(rev) else f"{rev} ({short})"


def build_at(commit, directory):
    """The TTF built from the SFD at `commit`, written into `directory`."""
    sfd, ttf = directory / "before.sfd", directory / "before.ttf"
    sfd.write_bytes(git("cat-file", "blob", f"{commit}:{SFD_PATH}", text=False).stdout)
    generate = ROOT / "tools" / "generate.py"
    result = subprocess.run(["fontforge", "-quiet", "-script", str(generate), str(sfd), str(ttf)],
                            check=False, capture_output=True, text=True)
    if result.returncode:
        sys.exit(f"Building the font at {commit} failed:\n{result.stderr}")
    return ttf


def rendered_at():
    """The commit the working tree is at, and whether its sources differ from it."""
    head = git("rev-parse", "--short", "HEAD").stdout.strip()
    source_dir = SFD.parent.relative_to(ROOT).as_posix()
    changed = git("status", "--porcelain", "--", source_dir).stdout
    return head + (f", with uncommitted changes to {source_dir}/" if changed else "")


def default_fonts():
    references = sorted(p for p in REFERENCE_DIR.glob("*") if p.suffix in (".otf", ".ttf"))
    return [BUILT, *references]


def label(path):
    """The font's path from the repository root, or its file name if it lies elsewhere."""
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name


def extents(font, size, line_height):
    """hb-view's --font-extents for lines `line_height` em apart, the space added to (or taken
    from) the font's own line box split evenly between its top and bottom."""
    extra = line_height * font.upem - (font.ascender - font.descender)
    scale = size / font.upem
    ascent, descent = font.ascender + extra / 2, -font.descender + extra / 2
    return f"{ascent * scale:g},{descent * scale:g},0"


def render(font, text, size, features, line_height, path):
    """Render `text` to the PNG at `path`; returns the image's (width, height)."""
    command = ["hb-view", str(font.path), f"--font-size={size}", f"--margin={MARGIN}",
               f"--output-file={path}", f"--text={text}"]  # --text=: text may start with '-'
    if features:
        command.append(f"--features={features}")
    if line_height:
        command.append(f"--font-extents={extents(font, size, line_height)}")
    subprocess.run(command, check=True)
    with open(path, "rb") as png:
        return struct.unpack(">II", png.read(24)[16:24])  # from the PNG's IHDR chunk


def sheet(fonts, blocks, line_heights, outdir):
    sections = []
    for b, (title, text, features) in enumerate(blocks):
        parts = [f"<section><h2>{html.escape(title)}</h2>"]
        for size in (*SMALL, LARGE):
            for h, line_height in enumerate(line_heights):
                where = f"{size} px"
                if line_height:
                    where += f", lines {line_height:g} em apart"
                parts.append(f"<h3>{where}</h3>")
                for f, font in enumerate(fonts):
                    name = f"{b}-{size}-{h}-{f}.png"
                    width, height = render(font, text, size, features, line_height,
                                           outdir / name)
                    alt = html.escape(f"{title} in {font.family} at {where}", quote=True)
                    images = f'<img src="{name}" width="{width}" height="{height}" alt="{alt}">'
                    if size in SMALL:
                        images += (f'<img class="magnified" src="{name}"'
                                   f' width="{width * MAGNIFY}" height="{height * MAGNIFY}"'
                                   f' alt="{alt}, magnified">')
                    parts.append(f"<figure><figcaption>{html.escape(font.family)}<br>"
                                 f'<span class="note">{html.escape(font.note)}</span>'
                                 f"</figcaption>{images}</figure>")
        sections.append("\n".join(parts) + "</section>")
    today = datetime.datetime.now().astimezone().date()
    return PAGE.format(date=today.isoformat(), commit=html.escape(rendered_at()),
                       body="\n".join(sections))


def positive(value):
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError(f"not above 0: {value}")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument("fonts", nargs="*", type=pathlib.Path, help="default: see above")
    parser.add_argument("--before", metavar="REV",
                        help="also show the font built from the SFD at this commit")
    parser.add_argument("--text", action="append",
                        help="proof this instead of the look-alikes and code; repeatable, may "
                             "span lines; write --text=TEXT if it starts with '-'")
    parser.add_argument("--features", metavar="LIST",
                        help="hb-view features for every block, such as -calt")
    parser.add_argument("--line-height", type=positive, action="append", metavar="EM",
                        help="set lines this many em apart in every font; repeatable "
                             "(default: each font's own)")
    args = parser.parse_intermixed_args()
    paths = args.fonts or default_fonts()
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        parser.error(f"no such font: {', '.join(missing)}")
    before = resolve(parser, args.before) if args.before else None
    blocks = [(text, text, None) for text in args.text] if args.text else BLOCKS
    if args.features is not None:
        blocks = [(title, text, args.features) for title, text, _ in blocks]
    args.outdir.mkdir(parents=True, exist_ok=True)
    fonts = [load(path, label(path)) for path in paths]
    with tempfile.TemporaryDirectory() as tmp:
        if before:
            commit, note = before
            fonts.insert(1, load(build_at(commit, pathlib.Path(tmp)), note))
        page = sheet(fonts, blocks, args.line_height or [None], args.outdir)
    (args.outdir / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote {args.outdir / 'index.html'}")


if __name__ == "__main__":
    main()
