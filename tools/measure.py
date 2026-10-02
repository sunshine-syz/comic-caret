"""Measurements of glyph outlines, shared by the tests and the glyph-editing scripts.

Outlines are FontForge layers in font units, cubic as in the SFD.
"""
import itertools
import math

import fontforge

import lig_geometry as geo


def spans_at_y(layer, y):
    """(x0, x1) of each stroke a horizontal line at y crosses, left to right."""
    # A thin band rather than a line; strokes at the same slant gain the same extra width.
    band = geo.trim(layer, y0=y - 1, y1=y + 1)
    return [(x0, x1) for x0, _, x1, _ in sorted(contour.boundingBox() for contour in band)]


def spans_at_x(layer, x):
    """(y0, y1) of each stroke a vertical line at x crosses, bottom to top."""
    band = geo.trim(layer, x0=x - 1, x1=x + 1)
    return sorted((y0, y1) for _, y0, _, y1 in (contour.boundingBox() for contour in band))


def _straight_segments(layer):
    """(a, b) for each segment of the outline drawn straight, between two on-curve points."""
    for contour in layer:
        for i in range(len(contour)):
            a, b = contour[i], contour[(i + 1) % len(contour)]
            if a.on_curve and b.on_curve:
                yield a, b


def vertical_edges(layer):
    """(x, y0, y1) of each straight upright edge: where a stroke is cut flat across."""
    return [(a.x, min(a.y, b.y), max(a.y, b.y))
            for a, b in _straight_segments(layer) if abs(a.x - b.x) < 0.5]


def horizontal_edges(layer):
    """(y, x0, x1) of each straight level edge."""
    return [(a.y, min(a.x, b.x), max(a.x, b.x))
            for a, b in _straight_segments(layer) if abs(a.y - b.y) < 0.5]


def counter(layer, y):
    """The white between the strokes a horizontal line at y crosses, summed."""
    spans = spans_at_y(layer, y)
    return sum(right[0] - left[1] for left, right in itertools.pairwise(spans))


def ink_width(layer):
    x0, _, x1, _ = layer.boundingBox()
    return x1 - x0


def ink_center(layer):
    x0, _, x1, _ = layer.boundingBox()
    return (x0 + x1) / 2


def ink(font, glyph):
    """The glyph's outline as one layer, its references resolved at any depth."""
    layer = font[glyph].foreground.dup()
    for name, matrix, *_ in font[glyph].references:
        layer += geo.transformed(ink(font, name), matrix)
    return layer


def area(layer, steps=16):
    """The ink's area. Outer contours run clockwise and holes counter-clockwise, so holes
    subtract."""
    total = 0
    for contour in layer:
        points = _polyline(contour, steps)
        total -= sum(x0 * y1 - x1 * y0
                     for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])) / 2
    return total


def covered(inner, outer):
    """The share of `inner`'s ink that `outer` covers. Neither may overlap itself."""
    both = inner.dup()
    both += outer.dup()
    both.intersect()
    return area(both) / area(inner)


def outline(contours):
    """The points of a layer (or any contours), contour by contour, in an order that ignores
    where each contour starts and which comes first: two drawings of one outline compare
    equal."""
    return sorted(sorted((p.x, p.y, p.on_curve) for p in contour) for contour in contours)


def pieces(layer):
    """Each outline of the layer with the counters inside it, as a layer of its own."""
    contours = list(layer)
    found = []
    for shell in contours:
        if not shell.isClockwise():
            continue
        x0, y0, x1, y1 = shell.boundingBox()
        piece = fontforge.layer()
        piece += shell
        for counter in contours:
            a0, b0, a1, b1 = counter.boundingBox()
            if not counter.isClockwise() and x0 <= a0 and a1 <= x1 and y0 <= b0 and b1 <= y1:
                piece += counter
        found.append(piece)
    return found


def _segments(contour):
    """The contour's segments as point lists: two points for a line, four for a cubic."""
    points = [(p.x, p.y, p.on_curve) for p in contour]
    first = next(i for i, p in enumerate(points) if p[2])
    points = points[first:] + points[:first]
    segments, i = [], 0
    while i < len(points):
        j = i + 1
        while not points[j % len(points)][2]:
            j += 1
        segments.append([points[k % len(points)][:2] for k in range(i, j + 1)])
        i = j
    return segments


def _polyline(contour, steps):
    """Points along the closed contour, `steps` to each segment."""
    out = []
    for segment in _segments(contour):
        if len(segment) == 2:
            (x0, y0), (x1, y1) = segment
            out.extend((x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps)
                       for k in range(steps))
            continue
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = segment
        for k in range(steps):
            t = k / steps
            u = 1 - t
            out.append((u ** 3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x3,
                        u ** 3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y3))
    return out


def _to_segment(point, a, b):
    (px, py), (ax, ay), (bx, by) = point, a, b
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    t = 0 if not length else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def gap(first, second, steps=16):
    """The shortest distance between the ink of two outlines that don't overlap; 0 where they
    touch."""
    lines = [[_polyline(contour, steps) for contour in layer] for layer in (first, second)]
    best = math.inf
    for mine, theirs in (lines, lines[::-1]):
        edges = [(a, b) for line in theirs for a, b in zip(line, line[1:] + line[:1])]
        xs = [x for line in theirs for x, _ in line]
        ys = [y for line in theirs for _, y in line]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        for x, y in (point for line in mine for point in line):
            # Points farther from the other outline's box than the best so far can't beat it.
            if x0 - best <= x <= x1 + best and y0 - best <= y <= y1 + best:
                best = min(best, min(_to_segment((x, y), a, b) for a, b in edges))
    return best


def outline_distance(first, second, steps=16):
    """How far apart two outlines lie: the farthest any point sampled on one lies from the
    other's polyline, either way round (their Hausdorff distance), each flattened to `steps`
    points a segment. Small for two drawings of one path, however their curves are split or
    where their contours start; 0 for two empty layers and infinite when only one is
    empty."""
    lines = [[_polyline(contour, steps) for contour in layer] for layer in (first, second)]
    farthest = 0
    for mine, theirs in (lines, lines[::-1]):
        edges = [(min(ax, bx), max(ax, bx), min(ay, by), max(ay, by), (ax, ay), (bx, by))
                 for line in theirs for (ax, ay), (bx, by) in zip(line, line[1:] + line[:1])]
        start = 0
        for x, y in (point for line in mine for point in line):
            nearest = math.inf
            # The next point along is nearest an edge next to this one's, so search from there.
            for k in itertools.chain(range(start, len(edges)), range(start)):
                x0, x1, y0, y1, a, b = edges[k]
                # An edge whose box lies farther than the nearest so far can't be nearer.
                if not (x0 - nearest <= x <= x1 + nearest and y0 - nearest <= y <= y1 + nearest):
                    continue
                distance = _to_segment((x, y), a, b)
                if distance < nearest:
                    nearest, start = distance, k
                    # A point this near can't raise the farthest.
                    if nearest <= farthest:
                        break
            farthest = max(farthest, nearest)
    return farthest
