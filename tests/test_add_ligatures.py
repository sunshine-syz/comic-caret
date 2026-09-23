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
import lig_geometry as geo  # noqa: E402

GENERATOR = ROOT / "tools" / "add_ligatures.py"


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


def widths_at(layer, y):
    """Widths of the strokes a horizontal line at y crosses, left to right."""
    # A thin band rather than a line; strokes at the same slant gain the same extra width.
    band = geo.trim(layer, y0=y - 1, y1=y + 1)
    return [x1 - x0 for x0, _, x1, _ in sorted(contour.boundingBox() for contour in band)]


def flat_edges(layer, length):
    """Straight horizontal edges at least `length` long, as (y, x0, x1)."""
    edges = []
    for contour in layer:
        for i in range(len(contour)):
            a, b = contour[i], contour[(i + 1) % len(contour)]
            if a.on_curve and b.on_curve and a.y == b.y and abs(a.x - b.x) >= length:
                edges.append((a.y, min(a.x, b.x), max(a.x, b.x)))
    return edges


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

    def test_rejects_head_scales_outside_the_checked_range(self):
        result = subprocess.run([sys.executable, str(GENERATOR), "--head-scale", "1.3",
                                 "/nonexistent.sfd"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--head-scale must be within", result.stderr)


class GlyphShapeTest(unittest.TestCase):
    PIPES = {"bar_greater.liga": "greater", "less_bar.liga": "less"}

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(add_ligatures.SFD))

    def mean_widths(self, name):
        """Mean stroke widths along the upper arm's height, left to right. Hand-drawn strokes
        vary in width along their length, so a single height would compare unlike parts."""
        # Above the arrow shafts, below where the arms of |> <| reach their bar.
        heights = range(add_ligatures.AXIS + 60, add_ligatures.AXIS + 161, 20)
        rows = [widths_at(self.font[name].foreground, y) for y in heights]
        self.assertEqual(len({len(row) for row in rows}), 1, f"{name}: strokes merge")
        return [sum(column) / len(rows) for column in zip(*rows)]

    def test_enlarged_heads_are_no_heavier_than_the_angles(self):
        # Scaling > up would thicken its arms past the shaft or bar they join.
        for glyph, angle in {"greater.arrow": "greater", "less.arrow": "less",
                             **self.PIPES}.items():
            with self.subTest(glyph=glyph):
                [arm] = self.mean_widths(angle)
                strokes = self.mean_widths(glyph)
                head = strokes[-1] if angle == "greater" else strokes[0]
                self.assertAlmostEqual(head, arm, delta=0.05 * arm)
                self.assertGreater(self.font[glyph].boundingBox()[3],
                                   self.font[angle].boundingBox()[3])

    def test_pipe_bars_are_as_heavy_as_the_bar(self):
        [bar] = self.mean_widths("bar")
        for pipe, angle in self.PIPES.items():
            with self.subTest(pipe=pipe):
                strokes = self.mean_widths(pipe)
                self.assertEqual(len(strokes), 2)
                self.assertAlmostEqual(strokes[0] if angle == "greater" else strokes[-1], bar,
                                       delta=0.05 * bar)

    def test_pipe_bars_keep_their_round_ends(self):
        # Every stroke in the font ends round; a bar cut flat shows a straight horizontal
        # edge as wide as the stroke.
        for pipe in self.PIPES:
            with self.subTest(pipe=pipe):
                self.assertEqual(flat_edges(self.font[pipe].foreground, 20), [])

    def test_pipe_corners_are_one_round_end(self):
        # An arm end beside the bar's end would leave two caps with a notch between them.
        for pipe in self.PIPES:
            layer = self.font[pipe].foreground
            _, bottom, _, top = layer.boundingBox()
            for y in (top - 4, top - 10, bottom + 4, bottom + 10):
                with self.subTest(pipe=pipe, y=y):
                    self.assertEqual(len(widths_at(layer, y)), 1)


if __name__ == "__main__":
    unittest.main()
