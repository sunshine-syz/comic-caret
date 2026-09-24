"""Measurements of glyph outlines, shared by the tests and the glyph-editing scripts.

Outlines are FontForge layers in font units, cubic as in the SFD. Stroke depth is measured
along the outline's inward normal, the way a pen's width shows across a stroke.
"""
import math

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


def counter(layer, y):
    """The white between the strokes a horizontal line at y crosses, summed."""
    spans = spans_at_y(layer, y)
    return sum(right[0] - left[1] for left, right in zip(spans, spans[1:]))


def ink_width(layer):
    x0, _, x1, _ = layer.boundingBox()
    return x1 - x0


def ink_center(layer):
    x0, _, x1, _ = layer.boundingBox()
    return (x0 + x1) / 2


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


def _outline(layer, steps):
    """Sample points along the outline, the edges between them, and the unit vector into the
    ink at each sample (None where the outline doubles back on itself)."""
    lines = [_polyline(contour, steps) for contour in layer]
    samples = [point for line in lines for point in line]
    edges = [(a, b) for line in lines for a, b in zip(line, line[1:] + line[:1])]
    normals = []
    for line in lines:
        for i in range(len(line)):
            (ax, ay), (bx, by) = line[i - 1], line[(i + 1) % len(line)]
            length = math.hypot(bx - ax, by - ay)
            # Outer contours run clockwise and holes counter-clockwise, so the ink always lies
            # right of the direction of travel.
            normals.append(((by - ay) / length, (ax - bx) / length) if length else None)
    return samples, edges, normals


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


def _depth(edges, origin, direction, reach, square):
    """(distance, edge index) from `origin` along `direction` to the first edge, or None when
    no edge lies within `reach` or the first one meets the ray at a glancing angle."""
    px, py = origin
    nx, ny = direction
    ex, ey = px + nx * reach, py + ny * reach
    left, right, bottom, top = min(px, ex), max(px, ex), min(py, ey), max(py, ey)
    best, hit = reach, None
    for index, ((x0, y0), (x1, y1)) in enumerate(edges):
        if max(x0, x1) < left or min(x0, x1) > right or max(y0, y1) < bottom or min(y0, y1) > top:
            continue
        dx, dy = x1 - x0, y1 - y0
        cross = nx * dy - ny * dx
        if cross == 0:
            continue  # parallel
        qx, qy = x0 - px, y0 - py
        distance = (qx * dy - qy * dx) / cross
        along = (qx * ny - qy * nx) / cross
        if 1e-6 < distance < best and 0 <= along <= 1:
            # |cross| / |edge| is the sine of the angle between the ray and the edge.
            best, hit = distance, index if abs(cross) / math.hypot(dx, dy) >= square else None
    return None if hit is None else (best, hit)


def depth_changes(before, after, steps=8, reach=200, square=0.8):
    """[(change, (x, y))]: how much the ink's depth changes at each sample point of `before`.

    `after` must be `before` with its points moved, so both sample alike. Both are measured
    along before's normals, so a stroke that the move turned still compares like with like.
    Rays longer than `reach`, or meeting the far edge less squarely than `square` (the sine of
    the angle), run along a stroke rather than across it and are skipped; so are rays that
    cross a different stretch of outline afterwards, such as one through a gap that closed.
    """
    samples, edges, normals = _outline(before, steps)
    moved, moved_edges, _ = _outline(after, steps)
    out = []
    for origin, target, normal in zip(samples, moved, normals, strict=True):
        if normal is None:
            continue
        old = _depth(edges, origin, normal, reach, square)
        new = _depth(moved_edges, target, normal, reach, square)
        if old and new and abs(old[1] - new[1]) <= steps:
            out.append((abs(new[0] - old[0]), origin))
    return out


def thickness_change(before, after, **options):
    """(change, (x, y)): the largest change in stroke depth between the outlines, and where on
    `before` it happens; (0, None) if nothing could be compared."""
    return max(depth_changes(before, after, **options), default=(0, None))
