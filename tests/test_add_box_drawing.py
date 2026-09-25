"""Tests for tools/add_box_drawing.py itself.

Run: python3 -m unittest discover tests
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import add_box_drawing
from project import ROOT, SFD

GENERATOR = ROOT / "tools" / "add_box_drawing.py"


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the generator changed without a rerun or a glyph in the range was edited
        # by hand, as well as when a run is not repeatable.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / SFD.name
            shutil.copy(SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(SFD))

    def test_the_font_has_every_character_in_the_range(self):
        # The Nerd Fonts patcher swaps in its own set unless the font has all of U+2500–U+259F.
        font = fontforge.open(str(SFD))
        missing = [f"U+{code:04X}" for code in range(0x2500, 0x25A0) if code not in font]
        self.assertEqual(missing, [])


class NameTest(unittest.TestCase):
    """The three ways Box Drawings names give the weight of each arm."""

    def arms(self, name):
        return add_box_drawing.arms([w for w in name.split()[2:] if w != "AND"])

    def test_a_leading_weight_covers_every_side(self):
        self.assertEqual(self.arms("BOX DRAWINGS HEAVY VERTICAL AND LEFT"),
                         {"up": "heavy", "down": "heavy", "left": "heavy"})

    def test_leading_weights_cover_the_sides_after_them(self):
        self.assertEqual(self.arms("BOX DRAWINGS LIGHT LEFT AND HEAVY RIGHT"),
                         {"left": "light", "right": "heavy"})

    def test_trailing_weights_cover_the_sides_before_them(self):
        self.assertEqual(self.arms("BOX DRAWINGS LEFT UP HEAVY AND RIGHT DOWN LIGHT"),
                         {"left": "heavy", "up": "heavy", "right": "light", "down": "light"})
        self.assertEqual(self.arms("BOX DRAWINGS VERTICAL SINGLE AND RIGHT DOUBLE"),
                         {"up": "light", "down": "light", "right": "double"})


if __name__ == "__main__":
    unittest.main()
