"""Helpers the tests share. Not a test module: unittest doesn't collect it, and a test module
imports from here, never from another test module."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from project import ADVANCE, FORMATS, STYLES, nerd_fonts, stale_build

# How far a glyph may stray from its row's median: round letters overshoot by up to 25 (C, 9).
ROW_TOLERANCE = 30


def bullet_seam(font):
    """The white between two ● side by side: as far apart as a symbol's parts must stay to
    read apart at 16 px."""
    x0, _, x1, _ = font[ord("●")].boundingBox()
    return 2 * min(x0, ADVANCE - x1)


def require_current_build(styles=tuple(STYLES), formats=FORMATS):
    """Fail, naming the font, when a built font the test reads predates its SFD."""
    if reason := stale_build(styles, formats):
        raise AssertionError(reason)


class NerdBuilds:
    """Mixin for a TestCase on the Nerd Fonts builds. They are made only by ./build.sh --nerd
    or --release, so a build older than the SFDs is skipped by name, and the whole class when
    none is current. Not a TestCase itself, so unittest doesn't collect it on its own."""

    @classmethod
    def setUpClass(cls):
        cls.fonts, cls.stale = nerd_fonts()
        if not cls.fonts:
            raise unittest.SkipTest("no Nerd Fonts build newer than the SFDs")

    def test_stale_builds_are_skipped(self):
        for font in self.stale:
            with self.subTest(font=font.name):
                self.skipTest("older than the SFDs; rebuild with ./build.sh --nerd")
