"""Helpers the tests share. Not a test module: unittest doesn't collect it, and a test module
imports from here, never from another test module."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))

# How far a glyph may stray from its row's median: round letters overshoot by up to 25 (C, 9).
ROW_TOLERANCE = 30
