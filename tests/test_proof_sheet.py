"""Tests for tools/proof_sheet.py. Needs hb-view and the built fonts (./build.sh).

Run: python3 -m unittest discover tests
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "proof_sheet.py"
TTF, OTF = (ROOT / "fonts" / f"ComicCaret-Regular.{ext}" for ext in ("ttf", "otf"))


class ProofSheetTest(unittest.TestCase):
    def sheet(self, *fonts):
        """(output directory, text of index.html) for a sheet of `fonts`."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out = pathlib.Path(tmp.name)
        subprocess.run([sys.executable, str(SCRIPT), str(out), *map(str, fonts)],
                       check=True, capture_output=True)
        return out, (out / "index.html").read_text(encoding="utf-8")

    def test_shows_every_block_at_every_size(self):
        out, page = self.sheet(TTF)
        sources = re.findall(r'src="([^"]+)"', page)
        # Two blocks at five sizes; the four small sizes also appear magnified.
        self.assertEqual(len(sources), 2 * (4 * 2 + 1))
        for source in sources:
            self.assertTrue((out / source).is_file(), source)

    def test_labels_each_row_with_its_font(self):
        _, page = self.sheet(TTF, OTF)
        self.assertIn("fonts/ComicCaret-Regular.ttf", page)
        self.assertIn("fonts/ComicCaret-Regular.otf", page)

    def test_rejects_a_missing_font(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "unused", "no-such-font.ttf"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("no such font", result.stderr)


if __name__ == "__main__":
    unittest.main()
