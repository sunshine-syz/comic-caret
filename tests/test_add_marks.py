"""Tests for tools/add_marks.py itself.

Run: python3 -m unittest discover tests

Where the marks sit is checked in test_consistency.py, and how the built fonts shape them in
test_built.py.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from project import ROOT, SFD

GENERATORS = [ROOT / "tools" / "add_marks.py", ROOT / "tools" / "add_ligatures.py"]


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the generator changed without a rerun, when a glyph was added or redrawn
        # since the last run, or when a mark was edited by hand, as well as when a run is not
        # repeatable. tools/add_ligatures.py runs after it, as CLAUDE.md says: FontForge puts
        # a new contextual lookup before the others, so the last of the two to run decides
        # their order in the SFD.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / SFD.name
            shutil.copy(SFD, copy)
            for generator in GENERATORS:
                subprocess.run([sys.executable, str(generator), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(SFD))


if __name__ == "__main__":
    unittest.main()
