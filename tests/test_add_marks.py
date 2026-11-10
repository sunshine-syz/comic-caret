"""Tests for tools/add_marks.py itself.

Run: python3 -m unittest discover tests

Where the marks sit is checked in test_consistency.py, and how the built fonts shape them in
test_built.py.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from project import ROOT, SFD
from sfd_files import rerun_differences

GENERATORS = [ROOT / "tools" / "add_marks.py", ROOT / "tools" / "add_ligatures.py"]


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when the generator changed without a rerun, when a glyph was added or redrawn
        # since the last run, or when a mark was edited by hand, as well as when a run is not
        # repeatable. tools/add_ligatures.py runs after it, as CLAUDE.md says: FontForge puts
        # a new contextual lookup before the others, so the last of the two to run decides
        # their order in the SFD. This ordered rerun covers add_ligatures.py too, so it has no
        # rerun test of its own. Linux's FontForge writes some of add_ligatures.py's outlines
        # apart from macOS's (less.dtail's level edge as lines, not collinear curves), so the
        # outlines compare within differences()' tolerance.
        self.assertEqual(rerun_differences(SFD, *GENERATORS), [])


if __name__ == "__main__":
    unittest.main()
