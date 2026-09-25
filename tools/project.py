"""Paths and font-wide facts that the tools and tests share."""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFD = ROOT / "src" / "ComicCaret-Regular.sfd"
ADVANCE = 550  # every glyph's advance width

_VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


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
