"""Outline operations for drawing glyphs and building them from existing outlines.

The generators (tools/add_*.py) and tools/make_italic.py draw with them.

Each function returns a new layer (or matrix) and leaves its inputs alone; snap_edge is the
exception and edits its argument in place. Outlines are clockwise, as in the SFD.
"""
import math

import fontforge
import psMat

FAR = 3000  # beyond every outline in the font
KAPPA = 4 * (math.sqrt(2) - 1) / 3  # control-point distance of a cubic quarter circle


def rect(x0, y0, x1, y1):
    """A clockwise rectangle, as a layer."""
    contour = fontforge.contour()
    contour.moveTo(x0, y0)
    contour.lineTo(x0, y1)
    contour.lineTo(x1, y1)
    contour.lineTo(x1, y0)
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def about(matrix, x, y):
    """`matrix` applied about the point (x, y) instead of the origin."""
    return psMat.compose(psMat.compose(psMat.translate(-x, -y), matrix), psMat.translate(x, y))


def transformed(layer, matrix):
    out = layer.dup()
    out.transform(matrix)
    return out


def clockwise(layer):
    """Every contour turned to run clockwise, as a filled outline must; a stroked path or a
    polygon can come out the other way, which removeOverlap would take for a hole."""
    out = layer.dup()
    for contour in out:
        if not contour.isClockwise():
            contour.reverseDirection()
    return out


def polygon(points):
    """A closed straight-sided outline through `points`, as a layer, clockwise whichever way
    the points run."""
    contour = fontforge.contour()
    contour.moveTo(*points[0])
    for point in points[1:]:
        contour.lineTo(*point)
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return clockwise(layer)


def circle(cx, cy, r):
    """A clockwise circle of four cubic quarters, as a layer."""
    k = KAPPA * r
    contour = fontforge.contour()
    contour.moveTo(cx, cy + r)
    contour.cubicTo((cx + k, cy + r), (cx + r, cy + k), (cx + r, cy))
    contour.cubicTo((cx + r, cy - k), (cx + k, cy - r), (cx, cy - r))
    contour.cubicTo((cx - k, cy - r), (cx - r, cy - k), (cx - r, cy))
    contour.cubicTo((cx - r, cy + k), (cx - k, cy + r), (cx, cy + r))
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def stroked(path, width):
    """The open contour `path` drawn as a stroke of `width` with round ends and joins,
    clockwise."""
    layer = fontforge.layer()
    layer += path
    return clockwise(layer.stroke("circular", width, "round", "round"))


def line(p0, p1, width):
    """A straight stroke with round ends."""
    contour = fontforge.contour()
    contour.moveTo(*p0)
    contour.lineTo(*p1)
    return stroked(contour, width)


def holes(layer):
    """The outline's contours turned to run the other way, so they cut holes where they lie
    inside another outline."""
    out = layer.dup()
    for contour in out:
        contour.reverseDirection()
    return out


def clip(layer, mask):
    """The part of `layer` inside the one-contour `mask`."""
    out = layer.dup()
    out += clockwise(mask)
    out.intersect()
    return out


def as_ring(layer):
    """The outline with its widest contour clockwise and the others counter-clockwise: a
    ring, whichever way a stroke came out."""
    out = layer.dup()
    widest = max(out, key=lambda c: c.boundingBox()[2] - c.boundingBox()[0])
    for contour in out:
        if contour.isClockwise() != (contour == widest):
            contour.reverseDirection()
    return out


def outer(layer):
    """The outline's clockwise contour: a ring filled in."""
    [contour] = [c for c in layer if c.isClockwise()]
    out = fontforge.layer()
    out += contour
    return out


def moved(layer, dx, dy):
    """`layer` shifted by (dx, dy)."""
    return transformed(layer, psMat.translate(dx, dy))


def centred(layer, cx, cy):
    """`layer` shifted so its bounding box is centred on (cx, cy)."""
    x0, y0, x1, y1 = layer.boundingBox()
    return moved(layer, cx - (x0 + x1) / 2, cy - (y0 + y1) / 2)


def turned(cx, cy):
    """The matrix that turns an outline 180° about (cx, cy)."""
    return about(psMat.rotate(math.pi), cx, cy)


def _reflected(layer, matrix):
    # A reflection reverses every contour; turning each back keeps holes as holes.
    out = transformed(layer, matrix)
    for contour in out:
        contour.reverseDirection()
    return out


def mirrored_x(layer, x):
    """Mirrored left to right about the vertical line at x."""
    return _reflected(layer, about(psMat.scale(-1, 1), x, 0))


def mirrored_y(layer, y):
    """Mirrored top to bottom about the horizontal line at y."""
    return _reflected(layer, about(psMat.scale(1, -1), 0, y))


def union(*layers):
    """Outlines merged where they cross.

    removeOverlap mishandles edges that coincide exactly; join those with weld or weld_y
    instead.
    """
    out = fontforge.layer()
    for layer in layers:
        # Adding to an empty layer hands back the added layer itself, so add a copy.
        out += layer.dup()
    out.removeOverlap()
    return out


def without_specks(layer, size):
    """The outline with every hole no wider or taller than `size` filled."""
    out = fontforge.layer()
    for contour in layer:
        x0, y0, x1, y1 = contour.boundingBox()
        if contour.isClockwise() or x1 - x0 > size or y1 - y0 > size:
            out += contour
    return out


def trim(layer, x0=-FAR, x1=FAR, y0=-FAR, y1=FAR):
    """The part of the outline inside the box, cut flat along its sides."""
    # layer.exclude() returns the wrong region, so intersect with the box instead.
    out = layer.dup()
    out += rect(x0, y0, x1, y1)
    out.intersect()
    return out


def stretch(layer, cut, dx, band=(-FAR, FAR)):
    """Strokes lengthened by moving every point beyond the vertical line `cut` by dx.

    dx > 0 moves the points right of the line, dx < 0 those left of it. With `band`, only
    points whose y lies inside it move, so one crossbar grows while the rest stays put.
    """
    out = layer.dup()
    for contour in out:
        for point in contour:
            beyond = point.x > cut if dx > 0 else point.x < cut
            if beyond and band[0] <= point.y <= band[1]:
                point.x += dx
    return out


def stretch_span(layer, x0, x1, dx):
    """The outline between the vertical lines x0 < x1 made dx longer, or shorter for dx < 0,
    with everything beyond x1 moved along unchanged.

    Unlike stretch, points inside the span are spaced out evenly rather than left behind, so
    shortening never folds the outline. Keep the span on the straight part of a stroke.
    """
    factor = (x1 - x0 + dx) / (x1 - x0)
    out = layer.dup()
    for contour in out:
        for point in contour:
            if point.x > x1:
                point.x += dx
            elif point.x > x0:
                point.x = x0 + (point.x - x0) * factor
    return out


def snap_edge(layer, x, profile):
    """Move the corners of the flat edge at x onto the nearest height in `profile`.

    Pieces cut at the same seam then meet at identical heights. Edits `layer` in place and
    returns it.
    """
    for contour in layer:
        for point in contour:
            if point.on_curve and abs(point.x - x) < 0.5:
                point.y = min(profile, key=lambda y: abs(y - point.y))
    return layer


def _edge_start(contour, on_edge, edge):
    """Index of the on-curve point where the contour's straight edge begins: the first
    segment between two on-curve points that are both on_edge."""
    count = len(contour)
    for i in range(count):
        a, b = contour[i], contour[(i + 1) % count]
        if a.on_curve and b.on_curve and on_edge(a) and on_edge(b):
            return i
    raise ValueError(f"no {edge}")


def weld(left, right, x):
    """Two one-contour outlines joined along the identical flat edge both have at x.

    Splices the point lists, since removeOverlap fails on edges that coincide exactly.
    `left` lies left of x and `right` right of it.
    """
    return _spliced(left, right, lambda p: abs(p.x - x) < 0.5, f"vertical edge at x = {x}")


def weld_y(below, above, y):
    """weld() along the identical flat edge both outlines have at y: `below` lies below y
    and `above` above it."""
    return _spliced(below, above, lambda p: abs(p.y - y) < 0.5, f"horizontal edge at y = {y}")


def _spliced(first, second, on_edge, edge):
    """Join the two outlines along their shared edge. Each is one contour with exactly one flat
    edge on the line; the two run in opposite directions along it, and the first match is the
    one taken."""
    a, b = first[0].dup(), second[0].dup()
    # Start each contour just after its edge, so the edge becomes its closing segment.
    a.makeFirst((_edge_start(a, on_edge, edge) + 1) % len(a))
    b.makeFirst((_edge_start(b, on_edge, edge) + 1) % len(b))
    joined = fontforge.contour()
    for point in [a[i] for i in range(len(a))] + [b[i] for i in range(1, len(b) - 1)]:
        joined += point
    joined.closed = True
    out = fontforge.layer()
    out += joined
    return out


def cleanup(layer):
    """Overlaps removed, points on whole units and at the extrema.

    Rounding can move an extremum off its point, so extrema are added between two roundings;
    "all" because the default skips short segments that validate() still checks.
    """
    out = layer.dup()
    out.removeOverlap()
    out.round()
    out.addExtrema("all")
    out.round()
    return out
