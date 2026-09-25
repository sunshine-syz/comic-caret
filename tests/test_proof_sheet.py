"""Tests for tools/proof_sheet.py. Needs HarfBuzz, git, FontForge and the built fonts
(./build.sh).

Run: python3 -m unittest discover tests
"""
import pathlib
import re
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import proof_sheet
from project import ADVANCE, ROOT, SFD

SCRIPT = ROOT / "tools" / "proof_sheet.py"
TTF, OTF = (ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("ttf", "otf"))
# Its own units per em and line box, unlike ours; absent until placed by hand (CLAUDE.md).
FIRA = ROOT / "build" / "cache" / "reference" / "FiraCode-Regular.ttf"
MARGIN = 4  # px: the blank border the script asks hb-view for
# The last commit without ✓ (U+2713); the next one added it.
WITHOUT_CHECK_MARK = "127f69ef38df7c3b799625898a6b242d9480660d"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True)


def has_sfd(commit):
    return git("cat-file", "-e", f"{commit}:{SFD.relative_to(ROOT)}").returncode == 0


def png_size(path):
    """(width, height) from the PNG's IHDR chunk."""
    with open(path, "rb") as png:
        return struct.unpack(">II", png.read(24)[16:24])


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          check=False, capture_output=True, text=True)


class ProofSheetTest(unittest.TestCase):
    def sheet(self, *args):
        """(output directory, text of index.html) for a sheet made with `args`."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name)
        result = run(out, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return out, (out / "index.html").read_text(encoding="utf-8")

    @staticmethod
    def images(out, page, size):
        """The images at `size` px in page order, magnified copies left out."""
        found = re.findall(r'<img [^>]*src="([^"]+)"[^>]* alt="([^"]*)"', page)
        return [out / src for src, alt in found
                if f" at {size} px" in alt and not alt.endswith("magnified")]

    def large(self, *args):
        """The one 64 px image of a sheet of one font and one text."""
        [image] = self.images(*self.sheet(*args), 64)
        return image

    def test_shows_every_block_at_every_size(self):
        out, page = self.sheet(TTF)
        sources = re.findall(r'src="([^"]+)"', page)
        # Two blocks at five sizes; the four small sizes also appear magnified.
        self.assertEqual(len(sources), 2 * (4 * 2 + 1))
        for source in sources:
            self.assertTrue((out / source).is_file(), source)

    def test_labels_each_row_with_its_font(self):
        fonts = [TTF, OTF, *([FIRA] if FIRA.exists() else [])]
        _, page = self.sheet(*fonts)
        self.assertIn("fonts/ComicCaret-Regular.ttf", page)
        self.assertIn("fonts/ComicCaret-Regular.otf", page)
        # Family names come from the fonts; the file names have no spaces.
        captions = re.findall(r"<figcaption>(.*?)</figcaption>", page, re.DOTALL)
        self.assertTrue(any("Comic Caret" in caption for caption in captions))
        if FIRA.exists():
            self.assertTrue(any("Fira Code" in caption for caption in captions))

    def test_names_the_commit_it_was_rendered_at(self):
        _, page = self.sheet(TTF, "--text=a")
        self.assertIn(git("rev-parse", "--short", "HEAD").stdout.strip(), page)

    def test_rejects_a_missing_font(self):
        result = run("unused", "no-such-font.ttf")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such font", result.stderr)

    def test_proofs_the_given_text(self):
        out, page = self.sheet(TTF, "--text=ab")
        # One block instead of the default two: four small sizes, magnified too, and 64 px.
        self.assertEqual(len(re.findall(r'src="', page)), 4 * 2 + 1)
        [image] = self.images(out, page, 64)
        # Two cells at 64 px, and the margins.
        self.assertAlmostEqual(png_size(image)[0], 2 * ADVANCE / 1000 * 64 + 2 * MARGIN,
                               delta=1)

    def test_applies_the_features(self):
        arrow = self.large(TTF, "--text=->").read_bytes()
        plain = self.large(TTF, "--text=->", "--features=-calt").read_bytes()
        self.assertNotEqual(arrow, plain)

    def test_gives_every_font_the_line_height(self):
        fonts = [TTF, *([FIRA] if FIRA.exists() else [])]
        out, page = self.sheet(*fonts, "--text=a\na", "--line-height=1.5")
        images = self.images(out, page, 64)
        self.assertEqual(len(images), len(fonts))
        for image in images:
            # Two lines of 1.5 em at 64 px, and the margins; "a" stays inside the line box.
            self.assertEqual(png_size(image)[1], 2 * 1.5 * 64 + 2 * MARGIN, image.name)

    def test_splits_the_line_height_change_between_top_and_bottom(self):
        # A 900/−350 line box (1.25 em), at a size of one pixel per unit.
        font = proof_sheet.Font(TTF, "", "", 1000, 900, -350)
        for line_height, expected in ((1.5, "1025,475,0"), (1.0, "775,225,0")):
            with self.subTest(line_height=line_height):
                self.assertEqual(proof_sheet.extents(font, 1000, line_height), expected)

    def test_shows_each_line_height(self):
        _, page = self.sheet(TTF, "--text=a", "--line-height=1", "--line-height=1.5")
        self.assertEqual(len(re.findall(r'src="', page)), 2 * (4 * 2 + 1))

    @unittest.skipUnless(has_sfd(WITHOUT_CHECK_MARK), "history not fetched (shallow clone)")
    def test_before_adds_the_font_at_that_commit(self):
        out, page = self.sheet(TTF, f"--before={WITHOUT_CHECK_MARK[:7]}", "--text=✓")
        ours, before = self.images(out, page, 64)
        self.assertIn(WITHOUT_CHECK_MARK[:7], page)
        # That commit's font has no ✓, so it draws another glyph.
        self.assertNotEqual(ours.read_bytes(), before.read_bytes())

    def test_rejects_an_unknown_commit(self):
        result = run("unused", "--before=no-such-commit")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no-such-commit", result.stderr)

    def test_rejects_a_commit_without_the_sfd(self):
        root = git("rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
        if has_sfd(root):
            self.skipTest("the oldest fetched commit has the SFD (shallow clone)")
        result = run("unused", f"--before={root}")
        self.assertEqual(result.returncode, 2)
        self.assertIn(root, result.stderr)


if __name__ == "__main__":
    unittest.main()
