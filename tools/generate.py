"""Generate one font file from the SFD; build.sh runs it once per format.

Usage: fontforge -quiet -script tools/generate.py SOURCE.sfd OUTPUT.otf|OUTPUT.ttf
"""
import os
import pathlib
import struct
import subprocess
import sys
import time

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bump_version import font_version
from mark_advances import zero_mark_advances
from project import is_alphanumeric
from sfnt import (
    HHEA_METRICS,
    MAXP_GLYPHS,
    metrics,
    packed,
    read_tables,
    without_mac_roman,
    write_tables,
)

HEAD_MODIFIED = 28                   # offset of head.modified
HEAD_BOX = 36                        # offset of head.xMin, then yMin, xMax and yMax
HEAD_LOCA_FORMAT = 50                # offset of head.indexToLocFormat
HHEA_BEARINGS = 12                   # offset of hhea.minLeftSideBearing, minRight..., xMaxExtent
BOX = struct.Struct(">hhhh")         # a box: xMin, yMin, xMax, yMax
# glyf's point flags, and its component flags.
ON_X_SHORT, ON_Y_SHORT, REPEAT, X_SAME, Y_SAME = 0x02, 0x04, 0x08, 0x10, 0x20
ARGS_ARE_WORDS, ARGS_ARE_OFFSETS, MORE_COMPONENTS = 0x0001, 0x0002, 0x0020
SCALED = 0x00C8                      # a scale, an x and y scale, or a 2 x 2 matrix
MAC_EPOCH = 2082844800               # seconds from 1904-01-01, where head's dates count, to 1970
# Pinned so the TTF's hints change only when we bump it on purpose.
TTFAUTOHINT = ["uvx", "--with", "ttfautohint-py==0.6.1", "python", "-m", "ttfautohint"]


def is_composite(glyph):
    """True if the TTF stores the glyph as a composite.

    A glyph that mixes outlines and references is written as a simple glyph instead.
    """
    return bool(glyph.references) and not len(glyph.foreground)


def flatten_nested_references(font):
    """Point every composite's references straight at simple glyphs.

    The SFD nests references (Braille patterns are built from smaller patterns), but TrueType
    composites of composites render badly in some environments (Font Bakery
    nested_components).
    """

    def leaves(name, matrix):
        glyph = font[name]
        if not is_composite(glyph):
            return [(name, matrix)]
        return [leaf for ref in glyph.references
                for leaf in leaves(ref[0], psMat.compose(ref[1], matrix))]

    for glyph in font.glyphs():
        refs = glyph.references
        if is_composite(glyph) and any(is_composite(font[ref[0]]) for ref in refs):
            glyph.references = tuple(leaf for ref in refs for leaf in leaves(ref[0], ref[1]))


def decompose_transformed_references(font):
    """Draw every reference that turns or scales its glyph as an outline.

    ttfautohint hints a component as its own glyph and then transforms it, so one turned 180°,
    as in ¡ ∀ ⇓ ▼, lands off the pixel rows its glyph's hints aligned (Font Bakery
    transformed_components). Turned, never mirrored, so the outlines keep their direction.
    """
    for glyph in font.glyphs():
        for name, matrix, *_ in glyph.references:
            if any(abs(a - b) > 1e-6 for a, b in zip(matrix[:4], (1, 0, 0, 1))):
                glyph.unlinkRef(name)


def hint_zones(font):
    """Give every letter and figure a hint edge in each alignment zone that holds its top or
    foot, and every glyph hints the CFF spec defines.

    The CFF hinter aligns hint edges, not the outline's extremes, to the zones. A composite
    keeps the hints its parts had when it was last hinted, which may predate the zones or the
    parts, so letter composites are hinted again. FontForge's autohinter can end a stem just
    outside the zone that holds the extreme, as at the bold E's bar (660 under its 665 top),
    and draws no ghost there, so a ghost marks each extreme a zone holds without an edge. It
    also writes some stems top first, with a negative width the spec leaves undefined; FreeType
    then aligned none of their edges to a zone (the bold U's top), so they are written bottom
    first. Without these, a letter stood a row off the rest at some sizes.
    """
    blues, other = font.private["BlueValues"], font.private["OtherBlues"]
    fuzz = 1  # the CFF default; the SFDs set no BlueFuzz
    tops = list(zip(blues[2::2], blues[3::2]))
    feet = [tuple(blues[:2]), *zip(other[::2], other[1::2])]
    for glyph in font.glyphs():
        letter = is_alphanumeric(glyph.unicode)
        if letter and glyph.references:
            glyph.autoHint()
        # FontForge gives a top ghost as (edge, -20) and a bottom one as (edge + 21, -21).
        hints = [(y + w, -w) if w < 0 and w not in (-20, -21) else (y, w)
                 for y, w in glyph.hhints]
        ghosts = []
        if letter:
            top_edges = [y if w == -20 else y + w for y, w in hints if w != -21]
            foot_edges = [y + w if w == -21 else y for y, w in hints if w != -20]
            _, y0, _, y1 = glyph.boundingBox()
            for y, zones, edges, ghost in ((y1, tops, top_edges, (y1, -20)),
                                           (y0, feet, foot_edges, (y0 + 21, -21))):
                for low, high in zones:
                    if (low - fuzz <= y <= high + fuzz
                            and not any(low - fuzz <= e <= high + fuzz for e in edges)):
                        ghosts.append(ghost)
        # A ghost the autohinter already drew across a new one's span, as m's top ghost at -1
        # over its feet at -21, would share its hint mask: the two edges would cross as they
        # are hinted and throw the points between them past the baseline.
        hints = [hint for hint in hints
                 if hint[1] not in (-20, -21) or not any(overlap(hint, g) for g in ghosts)]
        hints = sorted((*hints, *ghosts), key=lambda hint: min(hint[0], sum(hint)))
        if tuple(hints) != glyph.hhints:
            glyph.hhints = hints  # from the bottom up, or FontForge drops a hint out of order
            glyph.manualHints = True  # else generating hints it again, without these


def overlap(a, b):
    """Whether the spans of the hints `a` and `b`, as (position, width), overlap."""
    (a0, a1), (b0, b1) = sorted((a[0], sum(a))), sorted((b[0], sum(b)))
    return a0 < b1 and b0 < a1


def finish_tables(path, modified):
    """Rewrite the font file at `path` without its Mac Roman cmap subtable, and with
    head.modified set to `modified` (seconds since 1970).

    FontForge dates the OTF by the SFD's ModificationTime, so stamping here gives both formats
    of a build the same date. write_tables recomputes the checksums the edits invalidate.
    """
    version, search, tables = read_tables(path.read_bytes())
    out = []
    for tag, table in tables:
        if tag == b"cmap":
            table = without_mac_roman(table)
        elif tag == b"head":
            table = (table[:HEAD_MODIFIED] + struct.pack(">q", modified + MAC_EPOCH)
                     + table[HEAD_MODIFIED + 8:])
        out.append((tag, table))
    path.write_bytes(write_tables(version, search, out))


def points_box(glyf, start):
    """The box of the points of the simple glyph at `start` in glyf."""
    contours = struct.unpack_from(">h", glyf, start)[0]
    offset = start + 2 + BOX.size
    count = struct.unpack_from(f">{contours}H", glyf, offset)[-1] + 1
    offset += 2 * contours
    offset += 2 + struct.unpack_from(">H", glyf, offset)[0]  # past the instructions
    flags = []
    while len(flags) < count:
        flag = glyf[offset]
        repeat = glyf[offset + 1] if flag & REPEAT else 0
        offset += 2 if flag & REPEAT else 1
        flags += [flag] * (1 + repeat)
    axes = []
    for short, same in ((ON_X_SHORT, X_SAME), (ON_Y_SHORT, Y_SAME)):
        value, values = 0, []
        for flag in flags:
            if flag & short:
                value += glyf[offset] if flag & same else -glyf[offset]
                offset += 1
            elif not flag & same:
                value += struct.unpack_from(">h", glyf, offset)[0]
                offset += 2
            values.append(value)
        axes.append(values)
    xs, ys = axes
    return min(xs), min(ys), max(xs), max(ys)


def components(glyf, start):
    """[(glyph index, dx, dy)] of the composite glyph at `start` in glyf, whose components are
    simple glyphs placed by offsets alone (flatten_nested_references,
    decompose_transformed_references)."""
    offset, found = start + 2 + BOX.size, []
    while True:
        flags, index = struct.unpack_from(">HH", glyf, offset)
        words = flags & ARGS_ARE_WORDS
        dx, dy = struct.unpack_from(">hh" if words else ">bb", glyf, offset + 4)
        offset += 8 if words else 6
        assert flags & ARGS_ARE_OFFSETS and not flags & SCALED, f"component flags {flags:#x}"
        found.append((index, dx, dy))
        if not flags & MORE_COMPONENTS:
            return found


def fit_boxes_to_points(path):
    """Rewrite the TTF at `path` so each glyph's box, its left side bearing, the font's box and
    hhea's extents are those of its points.

    FontForge writes the box of a glyph's cubic outline, which can lie a unit outside the
    quadratic points it writes for it: V's foot at -13 for points at -12. Tools that read the
    points, as the Nerd Fonts patcher does, then give the glyph other extents than ours.
    """
    version, search, in_file = read_tables(path.read_bytes())
    order = [tag for tag, _ in in_file]
    tables = dict(in_file)
    count = struct.unpack_from(">H", tables[b"maxp"], MAXP_GLYPHS)[0]
    long_loca = struct.unpack_from(">h", tables[b"head"], HEAD_LOCA_FORMAT)[0]
    loca = struct.unpack_from(f">{count + 1}{'L' if long_loca else 'H'}", tables[b"loca"])
    starts = [offset if long_loca else 2 * offset for offset in loca]
    glyf = bytearray(tables[b"glyf"])
    drawn = [gid for gid in range(count) if starts[gid] < starts[gid + 1]]
    simple = {gid: struct.unpack_from(">h", glyf, starts[gid])[0] >= 0 for gid in drawn}
    boxes = {gid: points_box(glyf, starts[gid]) for gid in drawn if simple[gid]}
    for gid in (gid for gid in drawn if not simple[gid]):
        placed = [(x0 + dx, y0 + dy, x1 + dx, y1 + dy)
                  for index, dx, dy in components(glyf, starts[gid])
                  for x0, y0, x1, y1 in [boxes[index]]]
        boxes[gid] = (min(b[0] for b in placed), min(b[1] for b in placed),
                      max(b[2] for b in placed), max(b[3] for b in placed))
    long_count = struct.unpack_from(">H", tables[b"hhea"], HHEA_METRICS)[0]
    pairs = metrics(tables[b"hmtx"], count, long_count)
    for gid, box in boxes.items():
        BOX.pack_into(glyf, starts[gid] + 2, *box)
        pairs[gid] = (pairs[gid][0], box[0])
    tables[b"glyf"] = bytes(glyf)
    tables[b"hmtx"], long_count = packed(pairs)
    head = bytearray(tables[b"head"])
    BOX.pack_into(head, HEAD_BOX, min(b[0] for b in boxes.values()),
                  min(b[1] for b in boxes.values()), max(b[2] for b in boxes.values()),
                  max(b[3] for b in boxes.values()))
    tables[b"head"] = bytes(head)
    hhea = bytearray(tables[b"hhea"])
    # xMaxExtent is the largest left side bearing plus ink width, and each bearing is xMin.
    struct.pack_into(">hhh", hhea, HHEA_BEARINGS, min(box[0] for box in boxes.values()),
                     min(pairs[gid][0] - box[2] for gid, box in boxes.items()),
                     max(box[2] for box in boxes.values()))
    struct.pack_into(">H", hhea, HHEA_METRICS, long_count)
    tables[b"hhea"] = bytes(hhea)
    path.write_bytes(write_tables(version, search, [(tag, tables[tag]) for tag in order]))


def autohint(path):
    """Give the TTF at `path` ttfautohint's hints.

    FontForge writes no TrueType hints. Without them, every renderer that runs a font's own
    hints draws the TTF unhinted: FreeType's native and monochrome modes and Windows GDI. There
    = blurs into one grey band at 11 px, and in monochrome 8 reads as B. --no-info keeps the
    version string FontForge writes.
    """
    hinted = path.with_name(f"{path.stem}.hinted{path.suffix}")
    subprocess.run([*TTFAUTOHINT, "--no-info", str(path), str(hinted)], check=True)
    hinted.replace(path)


def main(source, output):
    # Glyphs edited since they were last hinted get autohinted while generating only if the
    # user's AutoHint preference allows it, so pin it to keep the OTF the same on every machine.
    fontforge.setPrefs("AutoHint", True)
    font = fontforge.open(source)
    # FontForge derives head.fontRevision, the CFF version and the names from this.
    font.version = font_version(font.version)
    # The unique ID in the form fontmake gives it, which names the release, where FontForge's
    # names the day of the build.
    font.appendSFNTName("English (US)", "UniqueID",
                        f"{font.version};{font.os2_vendor};{font.fontname}")
    # CFF has no components, so only the TTF needs these, and only the OTF reads the SFD's
    # hints.
    if output.endswith(".ttf"):
        flatten_nested_references(font)
        decompose_transformed_references(font)
    else:
        hint_zones(font)
    # Explicit flags replace FontForge's defaults, so "opentype" is needed to keep GDEF.
    # "no-mac-names" drops the platform-1 name records that nothing current reads, and
    # "no-FFTM-table" FontForge's record of when it and the font were made.
    font.generate(output, flags=("opentype", "no-mac-names", "no-FFTM-table"))
    path = pathlib.Path(output)
    # Before finish_tables, which dates the font: ttfautohint dates it the time now.
    if output.endswith(".ttf"):
        autohint(path)
    # build.sh sets it to the last commit's time so a rebuild gives the same bytes; a direct run
    # (proof_sheet.py --before) takes the time now.
    modified = int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
    finish_tables(path, modified)
    if output.endswith(".ttf"):
        zero_mark_advances(path)
        # Last, so hhea's extents count the marks' zero advances, as FontForge's do.
        fit_boxes_to_points(path)


if __name__ == "__main__":
    main(*sys.argv[1:])
