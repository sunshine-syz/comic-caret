"""Font Bakery's universal profile finds exactly the known problems in each built font.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md. Skips without uvx.
Each font is checked on its own: together, the TTF and the OTF read as two fonts of one style
and fail the family checks.
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
from project import ROOT, SFD

# Pinned, so that a release with new checks can't fail the suite; bump it on purpose. It runs
# with --skip-network: its version check asks PyPI for a newer Font Bakery and its name check
# asks a web service, so offline, or once a newer one is out, they fail a sound font.
FONTBAKERY = "fontbakery==1.1.0"
# Font Bakery's statuses that report nothing wrong.
QUIET = {"PASS", "SKIP", "INFO", "DEBUG"}
FONTS = {ext: ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("ttf", "otf")}
# How a message names its glyphs, by message code; other messages name none.
GLYPH_NAMES = {
    "contour-count": r"Glyph name: (\S+)",
    "decomposed-outline": r"^(\S+) is decomposed",
    "unreachable-glyphs": r"^\t- (\S+)$",
}


def run_fontbakery(font):
    """The JSON report of the universal profile on one font, with glyph lists in full."""
    with tempfile.TemporaryDirectory() as tmp:
        report = pathlib.Path(tmp) / "report.json"
        # It exits non-zero whenever a check fails or errors; the report says which.
        result = subprocess.run(["uvx", FONTBAKERY, "check-universal", "--skip-network",
                                 "--full-lists", "--json", str(report), str(font)],
                                capture_output=True, text=True, check=False)
        if not report.exists():
            raise AssertionError(f"Font Bakery wrote no report for {font.name}:\n"
                                 f"{result.stderr[-2000:]}")
        return json.loads(report.read_text(encoding="utf-8"))


def findings(report):
    """{(status, check, message code, glyph names)} for each result that isn't quiet."""
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
    """Glyphs with no character of their own that other glyphs are built from."""
    sfd = fontforge.open(str(SFD))
    used = {name for glyph in sfd.glyphs() for name, *_ in glyph.references}
    return frozenset(g.glyphname for g in sfd.glyphs() if g.unicode < 0 and g.glyphname in used)


def known():
    """The problems each built font is expected to have, each with the reason it stays."""
    # U+00AD is kept, since terminals give it a cell.
    soft_hyphen = ("WARN", "soft_hyphen", "softhyphen", frozenset())
    return {
        "ttf": {
            soft_hyphen,
            # FontForge writes one more hmtx entry than needed: 4, where the spec asks for 3
            # after the zero-width .null.
            ("WARN", "opentype/monospace", "bad-numberOfHMetrics", frozenset()),
            # ď is a reference to d and caron.alt, which the check can't inspect.
            ("WARN", "alt_caron", "decomposed-outline", frozenset({"dcaron"})),
            # ∄ is E and a slash as two references, where the check expects 3 contours; the soft
            # hyphen is drawn, as above, where it expects none.
            ("WARN", "contour_count", "contour-count", frozenset({"uni2204", "uni00AD"})),
            # FontForge adds nonmarkingreturn to every TTF.
            ("WARN", "unreachable_glyphs", "unreachable-glyphs",
             frozenset({"nonmarkingreturn"})),
        },
        "otf": {
            soft_hyphen,
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
        for font in FONTS.values():
            if not font.exists() or font.stat().st_mtime < SFD.stat().st_mtime:
                raise AssertionError(f"{font.name} is missing or older than {SFD.name}; "
                                     "run ./build.sh")
        cls.known = known()

    def test_fonts_have_only_the_known_problems(self):
        for ext, font in FONTS.items():
            with self.subTest(font=font.name):
                self.assertEqual(findings(run_fontbakery(font)), self.known[ext])


if __name__ == "__main__":
    unittest.main()
