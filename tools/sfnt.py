"""Reading and writing a font file's tables, for the edits FontForge doesn't make itself."""
import struct

HEADER = struct.Struct(">4sHHHH")  # sfnt version, table count, and the binary search fields
RECORD = struct.Struct(">4sLLL")   # tag, checksum, offset, length
CHECKSUM_MAGIC = 0xB1B0AFBA
HEAD_ADJUSTMENT = 8                # offset of head.checkSumAdjustment
HHEA_METRICS = 34                  # offset of hhea.numberOfHMetrics
MAXP_GLYPHS = 4                    # offset of maxp.numGlyphs
CMAP_HEADER = struct.Struct(">HH")   # version and subtable count
CMAP_RECORD = struct.Struct(">HHL")  # platform, encoding and subtable offset
MAC_ROMAN = (1, 0)                   # the platform and encoding of the Mac Roman subtable
NAME_HEADER = struct.Struct(">HHH")  # format, record count and the strings' offset
NAME_RECORD = struct.Struct(">6H")   # platform, encoding, language, name ID, length, offset
MAC = 1                              # the Macintosh platform ID
WINDOWS_ENGLISH = (3, 1, 0x409)      # platform, encoding and language of the names apps read


def checksum(data):
    padded = data + b"\0" * (-len(data) % 4)
    return sum(struct.unpack(f">{len(padded) // 4}L", padded)) & 0xFFFFFFFF


def read_tables(data):
    """(sfnt version, search fields, [(tag, table bytes)] in the file's order)."""
    version, count, *search = HEADER.unpack_from(data)
    records = [RECORD.unpack_from(data, HEADER.size + i * RECORD.size) for i in range(count)]
    in_file = sorted(records, key=lambda record: record[2])
    return version, search, [(tag, data[offset:offset + length])
                             for tag, _, offset, length in in_file]


def write_tables(version, search, tables):
    """The font file holding `tables`, each placed as before and the directory sorted by tag."""
    directory = HEADER.size + len(tables) * RECORD.size
    offsets, offset = {}, directory
    for tag, table in tables:
        offsets[tag] = offset
        offset += len(table) + (-len(table) % 4)
    tables = dict(tables)
    head = bytearray(tables[b"head"])
    head[HEAD_ADJUSTMENT:HEAD_ADJUSTMENT + 4] = bytes(4)
    tables[b"head"] = bytes(head)
    out = bytearray(HEADER.pack(version, len(tables), *search))
    for tag in sorted(tables):
        out += RECORD.pack(tag, checksum(tables[tag]), offsets[tag], len(tables[tag]))
    for tag in sorted(tables, key=offsets.get):
        out += tables[tag] + b"\0" * (-len(tables[tag]) % 4)
    adjustment = (CHECKSUM_MAGIC - checksum(bytes(out))) & 0xFFFFFFFF
    start = offsets[b"head"] + HEAD_ADJUSTMENT
    out[start:start + 4] = struct.pack(">L", adjustment)
    return bytes(out)


def tables(path):
    """{tag: table bytes} of the font file at `path`."""
    return dict(read_tables(path.read_bytes())[2])


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


def names(table):
    """[(platform, encoding, language, name ID, string bytes)] of a format 0 name table."""
    table_format, count, strings = NAME_HEADER.unpack_from(table)
    assert table_format == 0, f"name table format {table_format}"
    records = []
    for i in range(count):
        *key, length, offset = NAME_RECORD.unpack_from(
            table, NAME_HEADER.size + i * NAME_RECORD.size)
        records.append((*key, table[strings + offset:strings + offset + length]))
    return records


def name_table(records):
    """The format 0 name table holding `records`, as names() gives them, sorted as the spec
    asks."""
    records = sorted(records, key=lambda record: record[:4])
    heads, strings = [], b""
    for *key, text in records:
        heads.append(NAME_RECORD.pack(*key, len(text), len(strings)))
        strings += text
    return (NAME_HEADER.pack(0, len(records), NAME_HEADER.size + len(records) * NAME_RECORD.size)
            + b"".join(heads) + strings)
