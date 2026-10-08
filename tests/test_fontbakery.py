"""Font Bakery's universal profile finds exactly the known problems in the built fonts.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md. Skips without uvx.
Each format's styles are checked together, as the family they are, and the two formats
apart: together, the TTF and the OTF of one style read as two fonts of that style and fail
the family checks.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared helpers
from add_ligatures import GENERATED
from helpers import NerdBuilds, require_current_build
from project import FORMATS, SFD, STYLES, font_file

# Pinned, so that a release with new checks can't fail the suite; bump it on purpose. It runs
# with --skip-network: its version check asks PyPI for a newer Font Bakery and its name check
# asks a web service, so offline, or once a newer one is out, they fail a sound font.
FONTBAKERY = "fontbakery==1.1.0"
# The day the findings in known() were last reviewed. With it uv resolves Font Bakery's
# dependencies as of then, so a new fontTools can't change the findings; bump it with them.
EXCLUDE_NEWER = "2026-09-30"
# Font Bakery's statuses that report nothing wrong.
QUIET = {"PASS", "SKIP", "INFO", "DEBUG"}
FONTS = {ext: [font_file(style, ext) for style in STYLES] for ext in FORMATS}
# How a message names its glyphs, by message code; other messages name none.
GLYPH_NAMES = {
    "contour-count": r"Glyph name: (\S+)",
    "decomposed-outline": r"^(\S+) is decomposed",
    "unreachable-glyphs": r"^\t- (\S+)$",
}


def run_fontbakery(fonts):
    """The JSON report of the universal profile on `fonts`, with glyph lists in full."""
    with tempfile.TemporaryDirectory() as tmp:
        report = pathlib.Path(tmp) / "report.json"
        # It exits non-zero whenever a check fails or errors; the report says which.
        command = ["uvx", "--exclude-newer", EXCLUDE_NEWER, FONTBAKERY, "check-universal",
                   "--skip-network", "--full-lists", "--json", str(report), *map(str, fonts)]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if not report.exists():
            raise AssertionError(f"Font Bakery wrote no report for {fonts}:\n"
                                 f"{result.stderr[-2000:]}")
        return json.loads(report.read_text(encoding="utf-8"))


def findings(report):
    """{(status, check, message code, glyph names)} for each result that isn't quiet. A
    problem several styles have counts once, as the glyph names it lists are the same."""
    found = set()
    for section in report["sections"]:
        for check in section["checks"]:
            name = check["key"][1].removeprefix("<FontBakeryCheck:").removesuffix(">")
            for log in check["logs"]:
                if log["status"] not in QUIET:
                    code, text = log["message"]["code"], log["message"]["message"]
                    glyphs = re.findall(GLYPH_NAMES.get(code, r"(?!)"), text, re.MULTILINE)
                    found.add((log["status"], name, code, frozenset(glyphs)))
    return found


def unencoded_components():
    """Glyphs with no character of their own that other glyphs are built from, and that no
    ligature reaches (tests/test_ligatures.py reaches every generated glyph)."""
    sfd = fontforge.open(str(SFD))
    used = {name for glyph in sfd.glyphs() for name, *_ in glyph.references}
    return frozenset(g.glyphname for g in sfd.glyphs() if g.unicode < 0 and g.glyphname in used
                     and not GENERATED.fullmatch(g.glyphname))


def known():
    """The problems each built font is expected to have, each with the reason it stays."""
    # U+00AD is kept, since terminals give it a cell.
    soft_hyphen = ("WARN", "soft_hyphen", "softhyphen", frozenset())
    # FontForge writes no STAT table, and a static family needs none: the check is written
    # for variable fonts, whose instances a STAT table names. Apps pair the regular, the
    # italic and the bold by their names and the OS/2 style bits.
    no_stat = ("FAIL", "opentype/STAT/ital_axis", "no-stat", frozenset())
    # FontForge derives the italic's caret slope from its angle in hundredths, 100/21, which
    # is 11.86°, where the check wants 1000/213: 0.14° on a text cursor.
    caret_slope = ("WARN", "opentype/caret_slope", "caretslope-mismatch", frozenset())
    # The win ascent and descent are the line box, as in Fira Code, JetBrains Mono, Intel One
    # Mono and Cascadia Code, so GDI apps space lines 1.25 em apart, as every other app does.
    # The check wants them to hold the furthest ink: the box drawing's overlap and ╱ ╲ ╳ reach
    # 139 past the line box, which would space GDI's lines 1.53 em apart. GDI clips the overlap.
    win = {("FAIL", "family/win_ascent_and_descent", code, frozenset())
           for code in ("ascent", "descent")}
    contours = frozenset({"uni20B9", "uni20B1", "uni25CC", "uni254E", "uni2506", "uni250A",
                          "uni254F", "uni2507", "uni250B"})
    return {
        "ttf": {
            soft_hyphen, no_stat, caret_slope, *win,
            # tools/mark_advances.py gives the combining marks, which sit mid glyph order, a
            # zero advance, so the run of equal advances the spec lets hmtx drop can only
            # start after the last mark.
            ("WARN", "opentype/monospace", "bad-numberOfHMetrics", frozenset()),
            # ď is a reference to d and caron.alt, which the check can't inspect.
            ("WARN", "alt_caron", "decomposed-outline", frozenset({"dcaron"})),
            # ₹'s bowl closes on its leg, so it has a counter, where the check expects the open
            # shape's one contour; ₱'s upper bar cuts P's counter in two, one contour more than it
            # expects; ◌ is eight dashes, as Maple Mono's, where it expects fewer; and the dashed
            # verticals ╎ ┆ ┊ ╏ ┇ ┋ end in half a dash at the top and the bottom, so they have one
            # contour more than their dashes per cell, which it expects.
            ("WARN", "contour_count", "contour-count", contours),
            # In the regular and the italic, ∄ and ₩ too. ∄ is E and a slash, overlapping, where
            # the check expects 3 contours; the bold draws it as one outline, which has them.
            # ₩'s upper bar crosses the tip of W's middle notch, as Maple Mono's does, so no
            # counter is left above it, one contour fewer than the check expects. The bold's pen
            # closes all but two of its counters, leaving the 3 contours the check expects.
            ("WARN", "contour_count", "contour-count", contours | {"uni2204", "uni20A9"}),
            # FontForge adds nonmarkingreturn to every TTF.
            ("WARN", "unreachable_glyphs", "unreachable-glyphs",
             frozenset({"nonmarkingreturn"})),
        },
        "otf": {
            soft_hyphen, no_stat, caret_slope, *win,
            # A Font Bakery bug: the monospace check reads the glyf table, which CFF has not.
            ("ERROR", "opentype/monospace", "failed-check", frozenset()),
            # CFF has no components, so the glyphs only built into others go unreached.
            ("WARN", "unreachable_glyphs", "unreachable-glyphs", unencoded_components()),
        },
    }


def known_nerd():
    """known(), and the problems the Nerd Fonts patcher's icons bring, which the patcher owns."""
    # Its 10,600 icons are named by their set and name, as cod-account, with a hyphen the
    # naming rules don't allow; they make the font 2.4 MB.
    icons = {("FAIL", "valid_glyphnames", "found-invalid-names", frozenset()),
             ("WARN", "file_size", "large-font", frozenset())}
    plain = known()
    return {"ttf": plain["ttf"] | icons
            # 177 icons, as iec-toggle_power, repeat a segment in their TrueType outlines.
            | {("WARN", "overlapping_path_segments", "overlapping-path-segments", frozenset())},
            "otf": plain["otf"] | icons}


class FontBakeryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        require_current_build()
        cls.known = known()

    def test_fonts_have_only_the_known_problems(self):
        for ext, fonts in FONTS.items():
            with self.subTest(format=ext):
                self.assertEqual(findings(run_fontbakery(fonts)), self.known[ext])


class NerdFontBakeryTest(NerdBuilds, unittest.TestCase):
    """The default Nerd Fonts variant, the one a release ships, finds only the plain fonts'
    known problems and its icons'."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        super().setUpClass()
        cls.known = known_nerd()

    def test_fonts_have_only_the_known_problems(self):
        for ext in FORMATS:
            fonts = [font for font in self.fonts
                     if font.name.startswith("ComicCaretNerdFont-") and font.suffix == f".{ext}"]
            with self.subTest(format=ext):
                if not fonts:
                    self.skipTest("no default Nerd Fonts build")  # as from --nerd=mono
                self.assertEqual(findings(run_fontbakery(fonts)), self.known[ext])


if __name__ == "__main__":
    unittest.main()
