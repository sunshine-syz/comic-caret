"""Paths and font-wide facts that the tools and tests share."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFD = ROOT / "src" / "ComicCaret-Regular.sfd"
ADVANCE = 550  # every glyph's advance width

_VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


def validation_errors(glyph):
    """The glyph's validate() flags, without the bit that only records that it was checked."""
    return glyph.validate(True) & ~_VALIDATED
