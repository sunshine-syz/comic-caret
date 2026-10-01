"""Comparing the SFDs a generator writes, for the tests that check a rerun changes nothing.

Two FontForge builds of one version, Homebrew's on macOS and Linux's, don't write every
outline alike: one splits a curve into more segments than the other, or puts a control point
a unit away, and hints the outline it drew. So differences() compares everything else exactly
and the outlines by how far apart they lie: it reports any edit that moves an outline farther
than its tolerance.
"""
import difflib
import pathlib
import sys

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import measure
from test_consistency import ROUNDING

# The lines FontForge's autohinter writes from a glyph's outline; its hint masks are in the
# SplineSet. Moving a control point of each glyph by a unit, or splitting a curve of each, and
# rehinting changes HStem, VStem and CounterMasks lines; DStem2 holds diagonal stems, which
# neither SFD has.
HINTS = ("HStem:", "VStem:", "DStem2:", "CounterMasks:")


def without_timestamp(path):
    """The SFD's lines but the save time, which every save rewrites."""
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


def _parse(path):
    """The SFD's lines outside the glyphs, and each glyph's lines by name in file order."""
    header, glyphs, block = [], {}, None
    for line in without_timestamp(path):
        if line.startswith("StartChar: "):
            block = glyphs[line.removeprefix("StartChar: ")] = [line]
        elif block is not None:
            block.append(line)
            if line == "EndChar":
                block = None
        else:
            header.append(line)
    return header, glyphs


def _split(block):
    """A glyph's lines as (the foreground's outline, the rest without its hints)."""
    outline, rest, layer, inside = [], [], None, False
    for line in block:
        if line in ("Fore", "Back") or line.startswith("Layer: "):
            layer = line
        if line == "SplineSet" and layer == "Fore":
            inside = True
        if inside:
            outline.append(line)
        elif not line.startswith(HINTS):
            rest.append(line)
        if line == "EndSplineSet":
            inside = False
    return outline, rest


def _changed(expected, found):
    """The lines only `expected` has, marked -, and those only `found` has, marked +."""
    out = []
    matcher = difflib.SequenceMatcher(None, expected, found, autojunk=False)
    for tag, i0, i1, j0, j1 in matcher.get_opcodes():
        if tag != "equal":
            out += [f"-{line}" for line in expected[i0:i1]]
            out += [f"+{line}" for line in found[j0:j1]]
    return out


def differences(expected, found, tolerance=2 * ROUNDING):
    """How the SFD at `found` differs from the one at `expected`, one line each; empty when
    they match.

    They match when every line but the outlines and their hints is the same and each glyph's
    outline lies within `tolerance` of the other's. Each build rounds its points to whole
    units, so one curve drawn by two builds can lie a unit off on each side.
    """
    expected_header, expected_glyphs = _parse(expected)
    found_header, found_glyphs = _parse(found)
    out = [f"header: {line}" for line in _changed(expected_header, found_header)]
    out += [f"glyphs: {line}" for line in _changed(list(expected_glyphs), list(found_glyphs))]
    redrawn = []
    for name in expected_glyphs:
        if name not in found_glyphs or expected_glyphs[name] == found_glyphs[name]:
            continue
        (expected_outline, expected_rest), (found_outline, found_rest) = (
            _split(expected_glyphs[name]), _split(found_glyphs[name]))
        out += [f"{name}: {line}" for line in _changed(expected_rest, found_rest)]
        if expected_outline != found_outline:
            redrawn.append(name)
    if redrawn:
        # Only now, since opening a whole font takes a while and most reruns match exactly.
        fonts = fontforge.open(str(expected)), fontforge.open(str(found))
        for name in redrawn:
            distance = measure.outline_distance(*(font[name].foreground for font in fonts))
            if distance > tolerance:
                out.append(f"{name}: outline {distance:.2f} units away, over {tolerance}")
        for font in fonts:
            font.close()
    return out
