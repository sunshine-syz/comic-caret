"""Helpers the tests share. Not a test module: unittest doesn't collect it, and a test module
imports from here, never from another test module."""
import pathlib
import shutil
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import measure
from project import ADVANCE, FORMATS, STYLES, nerd_fonts, stale_build

# The Vietnamese letters whose acute or grave stands at the circumflex's upper right.
CIRCUMFLEX_STACKS = "ẤấẦầẾếỀềỐốỒồ"

# How far a glyph may stray from its row's median: round letters overshoot by up to 25 (C, 9).
ROW_TOLERANCE = 30


def hyphen_stroke(font):
    """The stroke's weight: the hyphen's, at its middle."""
    [(h0, h1)] = measure.spans_at_x(font["hyphen"].foreground, ADVANCE / 2)
    return h1 - h0


def assert_lookups_carry_over(test, derived, regular):
    """Fail `test` unless `derived`, a style generated from `regular`, keeps the regular's
    lookups, their subtables and every glyph's substitutions and positions."""
    for kind in ("gsub_lookups", "gpos_lookups"):
        test.assertEqual(getattr(derived, kind), getattr(regular, kind))
        for lookup in getattr(regular, kind):
            with test.subTest(lookup=lookup):
                test.assertEqual(derived.getLookupInfo(lookup), regular.getLookupInfo(lookup))
                test.assertEqual(derived.getLookupSubtables(lookup),
                                 regular.getLookupSubtables(lookup))
    different = [g.glyphname for g in regular.glyphs()
                 if derived[g.glyphname].getPosSub("*") != g.getPosSub("*")]
    test.assertEqual(different, [])


def require_uvx():
    """Skip the tests that run a pinned tool through uvx where it is not installed."""
    if shutil.which("uvx") is None:
        raise unittest.SkipTest("uvx is not installed")


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
