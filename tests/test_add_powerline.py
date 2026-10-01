"""Tests for tools/add_powerline.py and what its symbols must keep.

Run: python3 -m unittest discover tests
"""
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import add_powerline
import lig_geometry as geo
import measure
from add_box_drawing import LIGHT, LINE_BOTTOM, LINE_TOP
from project import ADVANCE, ROOT, SFD
from sfd_files import differences

GENERATOR = ROOT / "tools" / "add_powerline.py"


def points(layer):
    """The outline as a set of points, so two outlines compare whatever their contours' order
    and starting points."""
    return {(round(p.x), round(p.y), p.on_curve) for contour in layer for p in contour}


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the generator changed without a rerun, or a symbol was edited by hand.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / SFD.name
            shutil.copy(SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(differences(SFD, copy), [])

    def test_the_font_has_every_symbol(self):
        font = fontforge.open(str(SFD))
        missing = [f"U+{code:04X}" for code in add_powerline.CODES if code not in font]
        self.assertEqual(missing, [])


class SeparatorTest(unittest.TestCase):
    """A prompt paints each segment's background over whole cells and draws the separator in
    that colour, so it must reach every edge of its cell and line box, or a gap shows."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_separators_fill_the_cell_and_the_line_box(self):
        for code in (add_powerline.RIGHT_SOLID, add_powerline.RIGHT_THIN,
                     add_powerline.LEFT_SOLID, add_powerline.LEFT_THIN):
            with self.subTest(code=f"U+{code:04X}"):
                self.assertEqual(self.font[code].boundingBox(), (0, LINE_BOTTOM, ADVANCE, LINE_TOP))

    def test_left_separators_mirror_the_right_ones(self):
        for left, right in ((add_powerline.LEFT_SOLID, add_powerline.RIGHT_SOLID),
                            (add_powerline.LEFT_THIN, add_powerline.RIGHT_THIN)):
            with self.subTest(left=f"U+{left:04X}"):
                mirrored = geo.mirrored_x(self.font[right].foreground, ADVANCE / 2)
                self.assertEqual(points(mirrored), points(self.font[left].foreground))

    def test_thin_separators_take_the_box_drawing_stroke(self):
        # The stroke's thickness, measured across the lower arm at right angles to it. The
        # arm's edges run between points rounded to integers, so the span at one height can
        # be off by 1 for each edge.
        layer = self.font[add_powerline.RIGHT_THIN].foreground
        [(x0, x1)] = measure.spans_at_y(layer, 0)
        run, rise = ADVANCE, add_powerline.MIDDLE - LINE_BOTTOM
        across = (x1 - x0) * rise / math.hypot(run, rise)
        self.assertAlmostEqual(across, LIGHT, delta=2 * rise / math.hypot(run, rise))


if __name__ == "__main__":
    unittest.main()
