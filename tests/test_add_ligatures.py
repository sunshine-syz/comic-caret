"""Tests for tools/add_ligatures.py itself.

Run: python3 -m unittest discover tests
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import fontforge

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import add_ligatures  # noqa: E402

GENERATOR = ROOT / "tools" / "add_ligatures.py"


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when src/ligatures.fea or the generator changed without a rerun, or when a
        # generated glyph was edited by hand, as well as when a run is not repeatable.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / add_ligatures.SFD.name
            shutil.copy(add_ligatures.SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(add_ligatures.SFD))

    def test_generated_names_match_only_generated_glyphs(self):
        # The generator deletes every glyph whose name matches GENERATED before rebuilding, so
        # a hand-made glyph with such a name would silently disappear.
        font = fontforge.open(str(add_ligatures.SFD))
        matching = {g.glyphname for g in font.glyphs()
                    if add_ligatures.GENERATED.fullmatch(g.glyphname)}
        self.assertEqual(matching, set(add_ligatures.build(font)))


if __name__ == "__main__":
    unittest.main()
