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
from helpers import require_current_build
from project import SFD, STYLES, font_file

# Pinned, so that a release with new checks can't fail the suite; bump it on purpose. It runs
# with --skip-network: its version check asks PyPI for a newer Font Bakery and its name check
# asks a web service, so offline, or once a newer one is out, they fail a sound font.
FONTBAKERY = "fontbakery==1.1.0"
# The day the findings in known() were last reviewed. With it uv resolves Font Bakery's
# dependencies as of then, so a new fontTools can't change the findings; bump it with them.
EXCLUDE_NEWER = "2026-09-30"
# Font Bakery's statuses that report nothing wrong.
QUIET = {"PASS", "SKIP", "INFO", "DEBUG"}
FONTS = {ext: [font_file(style, ext) for style in STYLES] for ext in ("ttf", "otf")}
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
    problem both styles have counts once, as the glyph names it lists are the same."""
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
    # for variable fonts, whose instances a STAT table names. Apps pair the regular and the
    # italic by their names and the OS/2 style bits.
    no_stat = ("FAIL", "opentype/STAT/ital_axis", "no-stat", frozenset())
    # FontForge derives the italic's caret slope from its angle in hundredths, 100/21, which
    # is 11.86°, where the check wants 1000/213: 0.14° on a text cursor.
    caret_slope = ("WARN", "opentype/caret_slope", "caretslope-mismatch", frozenset())
    return {
        "ttf": {
            soft_hyphen, no_stat, caret_slope,
            # tools/mark_advances.py gives the combining marks, which sit mid glyph order, a
            # zero advance, so the run of equal advances the spec lets hmtx drop can only
            # start after the last mark.
            ("WARN", "opentype/monospace", "bad-numberOfHMetrics", frozenset()),
            # ď is a reference to d and caron.alt, which the check can't inspect.
            ("WARN", "alt_caron", "decomposed-outline", frozenset({"dcaron"})),
            # ∄ is E and a slash as two references, where the check expects 3 contours; ₹'s
            # bowl closes on its leg, so it has a counter, where the check expects the open
            # shape's one contour; ₱'s upper bar cuts P's counter in two, one contour more than it
            # expects; ◌ is eight dashes, as Maple Mono's, where it expects fewer.
            ("WARN", "contour_count", "contour-count",
             frozenset({"uni2204", "uni20B9", "uni20B1", "uni25CC"})),
            # FontForge adds nonmarkingreturn to every TTF.
            ("WARN", "unreachable_glyphs", "unreachable-glyphs",
             frozenset({"nonmarkingreturn"})),
            # In the bold, ☑'s tick, grown into the box, makes a third contour. The four above
            # hold for the bold as well.
            ("WARN", "contour_count", "contour-count",
             frozenset({"uni2204", "uni20B9", "uni20B1", "uni25CC", "uni2611"})),
        },
        "otf": {
            soft_hyphen, no_stat, caret_slope,
            # A Font Bakery bug: the monospace check reads the glyf table, which CFF has not.
            ("ERROR", "opentype/monospace", "failed-check", frozenset()),
            # CFF has no components, so the glyphs only built into others go unreached.
            ("WARN", "unreachable_glyphs", "unreachable-glyphs", unencoded_components()),
        },
    }


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


if __name__ == "__main__":
    unittest.main()
