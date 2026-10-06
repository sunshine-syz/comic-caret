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
from sfnt import read_tables, write_tables

CMAP_HEADER = struct.Struct(">HH")   # version and subtable count
CMAP_RECORD = struct.Struct(">HHL")  # platform, encoding and subtable offset
MAC_ROMAN = (1, 0)                   # the platform and encoding of the subtable to drop
HEAD_MODIFIED = 28                   # offset of head.modified
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
    """Hint every letter and figure so that its top and foot reach the alignment zones that
    hold them.

    The CFF hinter aligns hint edges, not the outline's extremes, to the zones. A composite
    keeps the hints its parts had when it was last hinted, which may predate the zones or the
    parts. FontForge's autohinter can also end a stem just outside the zone that holds the
    extreme, as at the bold E's bar (660 under its 665 top), and draws no ghost there. Such a
    letter stands a row off the rest at some sizes. So composites are hinted again, and a
    ghost hint marks each extreme a zone holds without an edge.
    """
    blues, other = font.private["BlueValues"], font.private["OtherBlues"]
    fuzz = 1  # the CFF default; the SFDs set no BlueFuzz
    tops = list(zip(blues[2::2], blues[3::2]))
    feet = [tuple(blues[:2]), *zip(other[::2], other[1::2])]
    for glyph in font.glyphs():
        if not is_alphanumeric(glyph.unicode):
            continue
        if glyph.references:
            glyph.autoHint()
        hints = glyph.hhints
        # FontForge gives a top ghost as (edge, -20) and a bottom one as (edge + 21, -21).
        top_edges = [y if w == -20 else y + w for y, w in hints if w != -21]
        foot_edges = [y + w if w == -21 else y for y, w in hints if w != -20]
        _, y0, _, y1 = glyph.boundingBox()
        ghosts = []
        for y, zones, edges, ghost in ((y1, tops, top_edges, (y1, -20)),
                                       (y0, feet, foot_edges, (y0 + 21, -21))):
            for low, high in zones:
                if (low - fuzz <= y <= high + fuzz
                        and not any(low - fuzz <= e <= high + fuzz for e in edges)):
                    ghosts.append(ghost)
        if ghosts:
            # From the bottom up, or FontForge drops a hint out of order.
            glyph.hhints = sorted((*hints, *ghosts), key=lambda hint: min(hint[0], sum(hint)))
            glyph.manualHints = True  # else generating hints it again, without the ghosts


def without_mac_roman(cmap):
    """`cmap` without its Mac Roman subtable.

    FontForge writes one whatever the flags. It maps 256 characters in an old Mac encoding,
    and every current platform reads the Unicode subtables instead.
    """
    version, count = CMAP_HEADER.unpack_from(cmap)
    records = [CMAP_RECORD.unpack_from(cmap, CMAP_HEADER.size + i * CMAP_RECORD.size)
               for i in range(count)]
    # Records can share a subtable, and each subtable runs to the start of the next.
    starts = sorted({offset for *_, offset in records})
    ends = dict(zip(starts, [*starts[1:], len(cmap)]))
    kept = [record for record in records if record[:2] != MAC_ROMAN]
    moved, subtables = {}, b""
    for start in sorted({offset for *_, offset in kept}):
        moved[start] = CMAP_HEADER.size + len(kept) * CMAP_RECORD.size + len(subtables)
        subtables += cmap[start:ends[start]]
    return (CMAP_HEADER.pack(version, len(kept))
            + b"".join(CMAP_RECORD.pack(platform, encoding, moved[offset])
                       for platform, encoding, offset in kept)
            + subtables)


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


if __name__ == "__main__":
    main(*sys.argv[1:])
