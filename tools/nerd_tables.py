"""Write back what the Nerd Fonts patcher undoes in the fonts tools/generate.py made.

Usage: python3 tools/nerd_tables.py FONT...

The patcher saves through FontForge with its default flags, which bring back the Mac name
records and the Mac Roman cmap subtable that generate.py drops. Its unique ID, name ID 3, is
the full name and the patcher's version ("ComicCaret Nerd Font Bold 3.5.1"), so every release
of a style shares one; this writes the form generate.py gives the plain fonts, which names the
release: version;vendor;PostScript name.
"""
import pathlib
import sys

from sfnt import (
    MAC,
    WINDOWS_ENGLISH,
    name_table,
    names,
    read_tables,
    without_mac_roman,
    write_tables,
)

UNIQUE_ID, VERSION, POSTSCRIPT = 3, 5, 6
OS2_VENDOR = 58  # offset of OS/2.achVendID


def windows_names(table, vendor):
    """The name table without its Mac records, its unique ID naming the release."""
    records = [record for record in names(table) if record[0] != MAC]
    english = {name_id: text.decode("utf-16-be") for *key, name_id, text in records
               if tuple(key) == WINDOWS_ENGLISH}
    # The patcher appends ";Nerd Fonts X.Y.Z" to the version.
    version = english[VERSION].split(";")[0].removeprefix("Version ")
    unique = f"{version};{vendor};{english[POSTSCRIPT]}".encode("utf-16-be")
    return name_table([(*key, name_id, unique if name_id == UNIQUE_ID else text)
                       for *key, name_id, text in records])


def main(paths):
    for path in map(pathlib.Path, paths):
        version, search, tables = read_tables(path.read_bytes())
        vendor = dict(tables)[b"OS/2"][OS2_VENDOR:OS2_VENDOR + 4].decode("ascii")
        out = []
        for tag, table in tables:
            if tag == b"cmap":
                table = without_mac_roman(table)
            elif tag == b"name":
                table = windows_names(table, vendor)
            out.append((tag, table))
        path.write_bytes(write_tables(version, search, out))


if __name__ == "__main__":
    main(sys.argv[1:])
