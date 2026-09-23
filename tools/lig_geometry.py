"""Outline operations that tools/add_ligatures.py builds ligature glyphs with.

Each function takes FontForge layers and returns a new layer, leaving its inputs alone;
snap_edge is the exception and edits its argument in place. Outlines are clockwise, as in
the SFD.
"""
import fontforge
import psMat

FAR = 3000  # beyond every outline in the font


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

    removeOverlap mishandles edges that coincide exactly; join those with weld instead.
    """
    out = fontforge.layer()
    for layer in layers:
        out += layer
    out.removeOverlap()
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


def _edge_start(contour, x):
    """Index of the on-curve point where the contour's straight vertical edge at x begins."""
    count = len(contour)
    for i in range(count):
        a, b = contour[i], contour[(i + 1) % count]
        if a.on_curve and b.on_curve and abs(a.x - x) < 0.5 and abs(b.x - x) < 0.5:
            return i
    raise ValueError(f"no vertical edge at x = {x}")


def weld(left, right, x):
    """Two one-contour outlines joined along the identical flat edge both have at x.

    Splices the point lists, since removeOverlap fails on edges that coincide exactly.
    `left` lies left of x and `right` right of it.
    """
    a, b = left[0].dup(), right[0].dup()
    # Start each contour just after its edge, so the edge becomes its closing segment.
    a.makeFirst((_edge_start(a, x) + 1) % len(a))
    b.makeFirst((_edge_start(b, x) + 1) % len(b))
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
