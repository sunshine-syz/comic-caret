"""Paths and font-wide facts that the tools and tests share."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFD = ROOT / "src" / "ComicCaret-Regular.sfd"  # the master every glyph is drawn in
ITALIC_SFD = ROOT / "src" / "ComicCaret-Italic.sfd"  # derived from it by tools/make_italic.py
STYLES = {"Regular": SFD, "Italic": ITALIC_SFD}
REFERENCE_DIR = ROOT / "build" / "cache" / "reference"  # the italic references are in italic/
NERD_DIR = ROOT / "build" / "nerd"  # the patched fonts of ./build.sh --nerd and --release
ADVANCE = 550  # every glyph's advance width
LINE_TOP, LINE_BOTTOM = 900, -350  # the line box: hhea and typo ascender and descender
AXIS = 269  # the math axis, the hyphen's middle: - = + and the arrows' shafts center on it
OVERLAP = 10  # how far joining strokes (box drawing, the ligatures) reach into the next cell
ROUNDING = 1  # an outline's points and a reference's offset are each rounded to whole units
WOBBLE = 10  # how far the hand's wobble strays; centering and mirroring hold within it
# The format characters that take no cell (their wcwidth is 0), kept blank and zero wide like
# the combining marks: the zero width space, non-joiner and joiner, the word joiner and the
# byte order mark. Not the soft hyphen: terminals give it a cell.
ZERO_WIDTH = frozenset({0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF})

_VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


def font_file(style, ext):
    """The built font of `style` ("Regular" or "Italic") in format `ext` ("otf" or "ttf")."""
    return ROOT / "fonts" / f"ComicCaret-{style}.{ext}"


def reference_fonts(style="Regular"):
    """The reference fonts of `style` ("Regular" or "Italic"), sorted.

    The regulars sit in REFERENCE_DIR and the italics in its italic/ folder; the search is not
    recursive, so the regular list never picks up the italics.
    """
    folder = REFERENCE_DIR / "italic" if style == "Italic" else REFERENCE_DIR
    return sorted(p for p in folder.glob("*") if p.suffix in (".otf", ".ttf"))


def nerd_fonts():
    """The Nerd Fonts builds in NERD_DIR as (current, stale), each sorted.

    A font is current when it is newer than both SFDs, so it was built after the last change to
    the glyphs; a stale one predates them and says nothing about the font as it is now.
    """
    newest_sfd = max(sfd.stat().st_mtime for sfd in STYLES.values())
    fonts = sorted(NERD_DIR.glob("*.[ot]tf"))
    return ([f for f in fonts if f.stat().st_mtime > newest_sfd],
            [f for f in fonts if f.stat().st_mtime <= newest_sfd])


def validation_errors(glyph):
    """The glyph's validate() flags, without the bit that only records that it was checked."""
    return glyph.validate(True) & ~_VALIDATED


def save_checked(font, sfd, script):
    """Save `font` over the SFD at `sfd` once `script --check` passes on the saved copy.

    Validating in this process would write "Validated:" into the saved glyphs, so a fresh
    process checks the copy before it replaces the SFD.
    """
    tmp = sfd.with_name(f".{sfd.name}.tmp")
    font.save(str(tmp))
    if subprocess.run([sys.executable, str(script), "--check", str(tmp)], check=False).returncode:
        tmp.unlink()
        sys.exit(f"{sfd} is unchanged.")
    os.replace(tmp, sfd)
