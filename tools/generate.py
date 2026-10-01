"""Generate one font file from the SFD; build.sh runs it once per format.

Usage: fontforge -quiet -script tools/generate.py SOURCE.sfd OUTPUT.otf|OUTPUT.ttf
"""
import pathlib
import struct
import sys

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mark_advances import read_tables, write_tables, zero_mark_advances

CMAP_HEADER = struct.Struct(">HH")   # version and subtable count
CMAP_RECORD = struct.Struct(">HHL")  # platform, encoding and subtable offset
MAC_ROMAN = (1, 0)                   # the platform and encoding of the subtable to drop


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


def drop_mac_roman_cmap(path):
    """Rewrite the font file at `path` without its Mac Roman cmap subtable."""
    version, search, tables = read_tables(path.read_bytes())
    path.write_bytes(write_tables(version, search,
                                  [(tag, without_mac_roman(table) if tag == b"cmap" else table)
                                   for tag, table in tables]))


def main(source, output):
    # Glyphs edited since they were last hinted get autohinted while generating only if the
    # user's AutoHint preference allows it, so pin it to keep the OTF the same on every machine.
    fontforge.setPrefs("AutoHint", True)
    font = fontforge.open(source)
    # The unique ID in the form fontmake gives it, which names the release, where FontForge's
    # names the day of the build.
    font.appendSFNTName("English (US)", "UniqueID",
                        f"{font.version};{font.os2_vendor};{font.fontname}")
    # FontForge dates head.modified by the SFD's ModificationTime until a glyph changes, and
    # then by SOURCE_DATE_EPOCH (the time now without it), as flattening does in the TTF.
    # Setting the blank space's advance to itself changes a glyph and nothing that ships, so
    # both formats get the same date.
    space = font["space"]
    space.width = space.width
    # CFF has no components, so only the TTF needs this. Leaving the OTF path alone keeps its
    # stored hints valid.
    if output.endswith(".ttf"):
        flatten_nested_references(font)
    # Explicit flags replace FontForge's defaults, so "opentype" is needed to keep GDEF.
    # "no-mac-names" drops the platform-1 name records that nothing current reads, and
    # "no-FFTM-table" FontForge's record of when it and the font were made.
    font.generate(output, flags=("opentype", "no-mac-names", "no-FFTM-table"))
    path = pathlib.Path(output)
    drop_mac_roman_cmap(path)
    if output.endswith(".ttf"):
        zero_mark_advances(path)


if __name__ == "__main__":
    main(*sys.argv[1:])
