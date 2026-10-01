"""Give the zero-width glyphs of TrueType fonts from FontForge their zero advance.

Usage: python3 tools/mark_advances.py FONT.ttf ...

FontForge 20251009 writes a single advance for every glyph of a TTF whose glyphs are all one
width but for zero-width ones, so the marks and the zero-width format characters come out a
cell wide; its OTFs are right. This rewrites hmtx and hhea.numberOfHMetrics in place, giving
each GDEF mark glyph and each of project.ZERO_WIDTH a zero advance, and leaves a font whose
zero-width glyphs already have none as it is. tools/generate.py runs it on every TTF it
writes, and build.sh on the Nerd Fonts TTFs, which the patcher writes with FontForge too.
"""
import argparse
import pathlib
import struct

import fontforge

from project import ZERO_WIDTH
from sfnt import read_tables, write_tables

HHEA_METRICS = 34                  # offset of hhea.numberOfHMetrics
MAXP_GLYPHS = 4                    # offset of maxp.numGlyphs


def metrics(hmtx, count, long_count):
    """[(advance, left side bearing)] of every glyph: the first `long_count` give both, and
    the rest repeat the last advance."""
    pairs = [struct.unpack_from(">Hh", hmtx, 4 * i) for i in range(long_count)]
    bearings = struct.unpack_from(f">{count - long_count}h", hmtx, 4 * long_count)
    return pairs + [(pairs[-1][0], bearing) for bearing in bearings]


def packed(pairs):
    """hmtx for `pairs`, with the run of equal advances at the end stored once, and its
    numberOfHMetrics."""
    long_count = len(pairs)
    while long_count > 1 and pairs[long_count - 1][0] == pairs[long_count - 2][0]:
        long_count -= 1
    hmtx = b"".join(struct.pack(">Hh", *pair) for pair in pairs[:long_count])
    hmtx += b"".join(struct.pack(">h", bearing) for _, bearing in pairs[long_count:])
    return hmtx, long_count


def zero_mark_advances(path):
    """Rewrite the TTF at `path` so its GDEF mark glyphs and zero-width format characters
    advance by 0; returns how many did not before."""
    font = fontforge.open(str(path))
    marks = {glyph.originalgid for glyph in font.glyphs()
             if glyph.glyphclass == "mark" or glyph.unicode in ZERO_WIDTH}
    font.close()
    version, search, in_file = read_tables(path.read_bytes())
    order = [tag for tag, _ in in_file]
    tables = dict(in_file)
    count = struct.unpack_from(">H", tables[b"maxp"], MAXP_GLYPHS)[0]
    long_count = struct.unpack_from(">H", tables[b"hhea"], HHEA_METRICS)[0]
    pairs = metrics(tables[b"hmtx"], count, long_count)
    wrong = [gid for gid in marks if pairs[gid][0]]
    if not wrong:
        return 0
    for gid in wrong:
        pairs[gid] = (0, pairs[gid][1])
    tables[b"hmtx"], long_count = packed(pairs)
    hhea = bytearray(tables[b"hhea"])
    hhea[HHEA_METRICS:HHEA_METRICS + 2] = struct.pack(">H", long_count)
    tables[b"hhea"] = bytes(hhea)
    path.write_bytes(write_tables(version, search, [(tag, tables[tag]) for tag in order]))
    return len(wrong)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("fonts", nargs="+", type=pathlib.Path)
    for path in parser.parse_args().fonts:
        zero_mark_advances(path)


if __name__ == "__main__":
    main()
