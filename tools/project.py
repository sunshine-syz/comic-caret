"""Paths and font-wide facts that the tools and tests share."""
import os
import pathlib
import subprocess
import sys
import unicodedata

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
# Not Lm: ˆ ˇ are modifier letters, which the font draws and places as accents.
LETTERS = frozenset({"Lu", "Ll", "Lt", "Lo"})

_VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


def font_file(style, ext):
    """The built font of `style` ("Regular" or "Italic") in format `ext` ("otf" or "ttf")."""
    return ROOT / "fonts" / f"ComicCaret-{style}.{ext}"


def is_letter(code):
    """Whether the code point is a letter other than a modifier letter; False for -1, an
    unencoded glyph."""
    return code >= 0 and unicodedata.category(chr(code)) in LETTERS


def is_mark(code):
    """Whether the code point is a combining mark, which draws over the character before it."""
    return code >= 0 and unicodedata.category(chr(code)) == "Mn"


def takes_no_cell(code):
    """A combining mark, or a format character that terminals give no cell: zero wide."""
    return is_mark(code) or code in ZERO_WIDTH


def reference_fonts(style="Regular"):
    """The reference fonts of `style` ("Regular" or "Italic"), sorted.

    The regulars sit in REFERENCE_DIR and the italics in its italic/ folder; the search is not
    recursive, so the regular list never picks up the italics.
    """
    folder = REFERENCE_DIR / "italic" if style == "Italic" else REFERENCE_DIR
    return sorted(p for p in folder.glob("*") if p.suffix in (".otf", ".ttf"))


FORMATS = ("otf", "ttf")


def newest_sfd():
    """When either SFD last changed: a build older than this predates the glyphs it shows."""
    return max(sfd.stat().st_mtime for sfd in STYLES.values())


def stale_build(styles=tuple(STYLES), formats=FORMATS):
    """Why the built fonts of `styles` in `formats` don't show their SFD's glyphs, or None."""
    for style in styles:
        for ext in formats:
            font, sfd = font_file(style, ext), STYLES[style]
            if not font.exists() or font.stat().st_mtime < sfd.stat().st_mtime:
                return f"{font.name} is missing or older than {sfd.name}; run ./build.sh"
    return None


def style_of(font):
    """The style of a built font, plain or Nerd Fonts patched: the last part of its name."""
    return font.stem.split("-")[-1]


def nerd_fonts():
    """The Nerd Fonts builds in NERD_DIR as (current, stale), each sorted.

    A font is current when it is newer than both SFDs, so it was built after the last change to
    the glyphs; a stale one predates them and says nothing about the font as it is now.
    """
    newest = newest_sfd()
    fonts = sorted(NERD_DIR.glob("*.[ot]tf"))
    return ([f for f in fonts if f.stat().st_mtime > newest],
            [f for f in fonts if f.stat().st_mtime <= newest])


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
