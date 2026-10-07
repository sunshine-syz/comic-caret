"""The built fonts keep what the SFD holds: every character, its advance and its outline, and
the font's names; and they pass ots, the sanitizer browsers run web fonts through.

Run python3 tools/add_ligatures.py and ./build.sh first; see CLAUDE.md.
"""
import itertools
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import zipfile

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared helpers
import sfnt
from bump_version import font_version, sfd_version
from helpers import NerdBuilds, require_current_build
from make_italic import SLANT
from project import (
    ADVANCE,
    AXIS,
    FORMATS,
    ROOT,
    SFD,
    STYLES,
    font_file,
    is_alphanumeric,
    nerd_fonts,
    newest_sfd,
    style_of,
    takes_no_cell,
)

FONTS = {style: [font_file(style, ext) for ext in FORMATS] for style in STYLES}
# Converting to TrueType's quadratic curves moves an extreme point by up to 4 units.
BOX_TOLERANCE = 5
# ots, the sanitizer browsers run web fonts through. Pinned, and resolved as of a day as Font
# Bakery is, so that a stricter release can't fail a sound font; bump them on purpose.
OTS = "opentype-sanitizer==9.2.0"
OTS_EXCLUDE_NEWER = "2026-09-30"
SANITIZE = 'import ots, sys; sys.exit(ots.sanitize(sys.argv[1], "/dev/null").returncode)'
# FreeType, for the light autohinting Linux desktops apply by default; pinned as ots is.
FREETYPE = ["--with", "freetype-py==2.5.1", "--with", "fonttools==4.66.1"]
FREETYPE_EXCLUDE_NEWER = "2026-09-30"
# FreeType's load flags: its light autohinting, and native hinting, which runs the font's own
# hints, as hintfull, monochrome and Windows do.
HINTING = {"light": "FT_LOAD_TARGET_LIGHT", "native": "FT_LOAD_DEFAULT"}
# The pieces that run a bar on into the next cell, by the middle piece of the run they meet.
SEAMED = {"hyphen.mid": ["hyphen.sta", "hyphen.end", "less.arrow", "greater.arrow",
                         "less.twohead", "greater.twohead", "less.shaft", "greater.shaft"],
          "equal.mid": ["equal.sta", "equal.end", "less.darrow", "greater.darrow", "less.dtail",
                        "greater.dtail"],
          "underscore.mid": ["underscore.sta", "underscore.end"],
          "numbersign.mid": ["numbersign.sta", "numbersign.end"]}
# Prints {piece: [sizes]}: the pixel sizes, 8 to 36, where the piece's bar ends at a seam on a
# corner of the middle piece's (its first or last point at a height) and lands half a pixel
# or more off the middle piece's there under the hinting a HINTING flag names.
SEAMS = """
import json, sys
import freetype
from fontTools.ttLib import TTFont

path, seamed, flag = sys.argv[1], json.loads(sys.argv[2]), getattr(freetype, sys.argv[3])
order = TTFont(path).getGlyphOrder()
face = freetype.Face(path)

def hinted(name, size):
    face.set_pixel_sizes(0, size)
    face.load_glyph(order.index(name), freetype.FT_LOAD_NO_SCALE)
    points = [tuple(p) for p in face.glyph.outline.points]
    face.load_glyph(order.index(name), flag | freetype.FT_LOAD_NO_BITMAP)
    return dict(zip(points, (y for _, y in face.glyph.outline.points)))

def corners(points):
    heights = {y for _, y in points}
    return ({min(p for p in points if p[1] == y) for y in heights}
            | {max(p for p in points if p[1] == y) for y in heights})

off = {}
for middle, pieces in seamed.items():
    for size in range(8, 37):
        mid = hinted(middle, size)
        for name in pieces:
            piece = hinted(name, size)
            shared = corners(mid) & corners(piece)
            if any(abs(piece[c] - mid[c]) >= 32 for c in shared):
                off.setdefault(name, []).append(size)
print(json.dumps(off))
"""
# Prints {glyph: [glyf box, its points' box, hmtx side bearing]} for each glyph whose box or
# side bearing is not its points', and the head table's box and hhea's extents when they are
# not theirs.
BOXES = """
import json, sys
from fontTools.ttLib import TTFont

font = TTFont(sys.argv[1])
glyf, hmtx, head, hhea = font["glyf"], font["hmtx"], font["head"], font["hhea"]
off, boxes = {}, []
for name in font.getGlyphOrder():
    glyph = glyf[name]
    if glyph.numberOfContours == 0:
        continue
    found = [glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax]
    glyph.recalcBounds(glyf)
    box = [glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax]
    boxes.append(box)
    if found != box or hmtx[name][1] != box[0]:
        off[name] = [found, box, hmtx[name][1]]
union = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes),
         max(b[3] for b in boxes)]
if [head.xMin, head.yMin, head.xMax, head.yMax] != union:
    off["head"] = [[head.xMin, head.yMin, head.xMax, head.yMax], union]
extents = [hhea.minLeftSideBearing, hhea.minRightSideBearing, hhea.xMaxExtent]
hhea.recalc(font)  # from the boxes recalculated above
if extents != [hhea.minLeftSideBearing, hhea.minRightSideBearing, hhea.xMaxExtent]:
    off["hhea"] = [extents, [hhea.minLeftSideBearing, hhea.minRightSideBearing, hhea.xMaxExtent]]
print(json.dumps(off))
"""
# Prints {glyph: {size: contrast}} for = and the pieces of == under native hinting at 8 to 16
# px: how much lighter than the lighter bar the lightest pixel row between the bars is, from 0,
# one grey band, to 1.
EQUALS_BARS = """
import json, sys
import freetype

face = freetype.Face(sys.argv[1])
contrast = {}
for name in json.loads(sys.argv[2]):
    contrast[name] = {}
    for size in range(8, 17):
        face.set_pixel_sizes(0, size)
        face.load_glyph(face.get_name_index(name.encode()),
                        freetype.FT_LOAD_DEFAULT | freetype.FT_LOAD_NO_BITMAP | freetype.FT_LOAD_RENDER)
        bitmap = face.glyph.bitmap
        rows = [max(bitmap.buffer[r * bitmap.pitch:r * bitmap.pitch + bitmap.width]) / 255
                for r in range(bitmap.rows)]
        if len(rows) < 3:  # no row between two bars
            contrast[name][size] = 0
            continue
        gap = min(range(1, len(rows) - 1), key=rows.__getitem__)
        contrast[name][size] = min(max(rows[:gap]), max(rows[gap + 1:])) - rows[gap]
print(json.dumps(contrast))
"""
OPEN = "import fontforge, sys; fontforge.open(sys.argv[1])"
WINDOWS_ENGLISH = (3, 1, 0x409)  # platform, encoding and language of the names apps read
MAC_ROMAN = (1, 0)  # platform and encoding of a cmap subtable
HEAD_REVISION = 4  # offset of head.fontRevision, a 16.16 fixed-point number
HEAD_MODIFIED = 28  # offset of head.modified
HEAD_MAC_STYLE = 44  # offset of head.macStyle; bit 0 is bold
MAC_EPOCH = 2082844800  # seconds from 1904-01-01, where head's dates count from, to 1970-01-01
GENERATE = ROOT / "tools" / "generate.py"


def shaped(font, text):
    """hb-shape's JSON glyphs for `text`, ligatures off, with their extents."""
    result = subprocess.run(
        ["hb-shape", "--output-format=json", "--show-extents", "--features=-calt",
         "--preserve-default-ignorables", str(font), f"--text={text}"],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def shape(font, text):
    """[(glyph name, advance, (x0, y0, x1, y1))] for each character of `text`, ligatures off."""
    return [(g["g"], g["ax"], (g["xb"], g["yb"] + g["h"], g["xb"] + g["w"], g["yb"]))
            for g in shaped(font, text)]


def placed(font, text):
    """[(cluster, glyph name, (x0, y0, x1, y1))]: each glyph's ink where shaping puts it."""
    out, pen = [], 0
    for g in shaped(font, text):
        x, y = pen + g["dx"], g["dy"]
        out.append((g["cl"], g["g"], (x + g["xb"], y + g["yb"] + g["h"],
                                      x + g["xb"] + g["w"], y + g["yb"])))
        pen += g["ax"]
    return out


def advances(font):
    """{glyph name: advance} as the font file itself gives them, whatever shaping does."""
    opened = fontforge.open(str(font))
    widths = {glyph.glyphname: glyph.width for glyph in opened.glyphs()}
    opened.close()
    return widths


def english_names(font):
    """{name ID: text} of the font file's Windows English (US) name records."""
    table = sfnt.tables(font)[b"name"]
    _, count, strings = struct.unpack_from(">3H", table)
    names = {}
    for i in range(count):
        *key, name_id, length, offset = struct.unpack_from(">6H", table, 6 + 12 * i)
        if tuple(key) == WINDOWS_ENGLISH:
            start = strings + offset
            names[name_id] = table[start:start + length].decode("utf-16-be")
    return names


def cmap_encodings(font):
    """{(platform, encoding)} of the font file's cmap subtables."""
    cmap = sfnt.tables(font)[b"cmap"]
    count = struct.unpack_from(">H", cmap, 2)[0]
    return {struct.unpack_from(">HH", cmap, 4 + 8 * i) for i in range(count)}


def opening_warnings(font):
    """The lines FontForge prints while it opens `font`. Its C code writes them to the
    process's stderr, past Python's sys.stderr, so a subprocess is the simplest way to catch
    them."""
    result = subprocess.run([sys.executable, "-c", OPEN, str(font)],
                            capture_output=True, text=True, check=True)
    return result.stderr.splitlines()


def sanitize(font):
    """ots run on `font`: its exit status, and what it printed."""
    command = ["uvx", "--exclude-newer", OTS_EXCLUDE_NEWER, "--from", OTS, "python", "-c",
               SANITIZE, str(font)]
    return subprocess.run(command, capture_output=True, text=True, check=False)


class BuiltFontTest(unittest.TestCase):
    style = "Regular"

    @classmethod
    def setUpClass(cls):
        require_current_build((cls.style,))
        cls.fonts = FONTS[cls.style]
        sfd = fontforge.open(str(STYLES[cls.style]))
        glyphs = sorted((g for g in sfd.glyphs() if g.unicode >= 0), key=lambda g: g.unicode)
        cls.text = "".join(chr(g.unicode) for g in glyphs if not takes_no_cell(g.unicode))
        cls.names = [g.glyphname for g in glyphs if not takes_no_cell(g.unicode)]
        cls.boxes = [g.boundingBox() for g in glyphs if not takes_no_cell(g.unicode)]
        cls.marks = [(chr(g.unicode), g.glyphname, g.boundingBox())
                     for g in glyphs if takes_no_cell(g.unicode)]
        cls.widths = {g.glyphname: g.width for g in sfd.glyphs()}
        # The version string takes the form the OpenType spec gives it, and the unique ID the
        # one fontmake gives it, which names the release rather than the day of the build.
        cls.version = font_version(sfd.version)
        cls.font_names = {1: sfd.familyname, 2: cls.style,
                          3: f"{cls.version};{sfd.os2_vendor};{sfd.fontname}", 4: sfd.fullname,
                          5: f"Version {cls.version}", 6: sfd.fontname}

    def test_width_tables_declare_the_cell(self):
        # Apps that size the cell from these tables, not from the glyphs, read the cell here.
        for font in self.fonts:
            with self.subTest(font=font.name):
                tables = sfnt.tables(font)
                avg_char_width = struct.unpack_from(">h", tables[b"OS/2"], 2)[0]
                advance_width_max = struct.unpack_from(">H", tables[b"hhea"], 10)[0]
                is_fixed_pitch = struct.unpack_from(">I", tables[b"post"], 12)[0]
                self.assertEqual(avg_char_width, ADVANCE)
                self.assertEqual(advance_width_max, ADVANCE)
                self.assertNotEqual(is_fixed_pitch, 0)

    def test_every_character_reaches_its_glyph_one_cell_wide(self):
        # But the combining marks and the zero-width format characters, which take no room.
        # Each is shaped alone: a shaper zeroes a mark's advance and puts a run of marks in
        # canonical order.
        for font in self.fonts:
            with self.subTest(font=font.name):
                shaped = shape(font, self.text)
                self.assertEqual([name for name, _, _ in shaped], self.names)
                self.assertEqual({advance for _, advance, _ in shaped}, {ADVANCE})
                marks = [shape(font, char) for char, _, _ in self.marks]
                self.assertEqual([[(name, advance) for name, advance, _ in glyphs]
                                  for glyphs in marks],
                                 [[(name, 0)] for _, name, _ in self.marks])

    def test_outlines_keep_their_extent(self):
        # A composite generated in the process that edited its base keeps the old bounds.
        for font in self.fonts:
            with self.subTest(font=font.name):
                built = shape(font, self.text)
                built += [glyph for char, _, _ in self.marks for glyph in shape(font, char)]
                boxes = self.boxes + [box for _, _, box in self.marks]
                moved = {name: box for (name, _, box), sfd_box in zip(built, boxes, strict=True)
                         if any(abs(a - b) > BOX_TOLERANCE for a, b in zip(box, sfd_box))}
                self.assertEqual(moved, {})

    def test_the_fonts_give_every_glyph_its_advance(self):
        # hb-shape zeroes a mark's advance whatever the font gives it, and FontForge gives
        # every glyph of a TTF one advance when all but the zero-width ones share it.
        for font in self.fonts:
            with self.subTest(font=font.name):
                wrong = {name: width for name, width in advances(font).items()
                         if name in self.widths and width != self.widths[name]}
                self.assertEqual(wrong, {})

    def test_fonts_carry_the_names_of_the_sfd(self):
        # The typographic family and subfamily, where a font has them, name the same family
        # and style as 1 and 2 do for a regular or an italic.
        for font in self.fonts:
            with self.subTest(font=font.name):
                names = english_names(font)
                expected = self.font_names | {typographic: self.font_names[legacy]
                                              for typographic, legacy in ((16, 1), (17, 2))
                                              if typographic in names}
                self.assertEqual({name_id: names.get(name_id) for name_id in expected},
                                 expected)

    def test_head_carries_the_version_of_the_names(self):
        # fontconfig reads the version here, so head must carry name ID 5's X.Y00.
        # 1/0x10000 is the step of the 16.16 number.
        for font in self.fonts:
            with self.subTest(font=font.name):
                revision = struct.unpack_from(">l", sfnt.tables(font)[b"head"], HEAD_REVISION)[0]
                self.assertAlmostEqual(revision / 0x10000, float(self.version),
                                       delta=1 / 0x10000)

    def test_fonts_carry_no_fontforge_table(self):
        # FFTM is FontForge's record of when it and the font were made; nothing else reads it.
        for font in self.fonts:
            with self.subTest(font=font.name):
                self.assertNotIn(b"FFTM", set(sfnt.tables(font)))

    def test_formats_share_the_modification_date(self):
        # Both are dated by SOURCE_DATE_EPOCH, so the two files of one build agree.
        otf, ttf = (struct.unpack_from(">q", sfnt.tables(font)[b"head"], HEAD_MODIFIED)[0]
                    for font in self.fonts)
        self.assertEqual(otf, ttf)

    def test_cmap_has_no_mac_roman_subtable(self):
        # Every current platform reads the Unicode subtables; the Mac Roman one only repeats
        # 256 of their characters in an old encoding.
        for font in self.fonts:
            with self.subTest(font=font.name):
                self.assertNotIn(MAC_ROMAN, cmap_encodings(font))

    def test_hint_masks_name_only_the_glyphs_stems(self):
        # A CFF hint mask has a bit for each of the glyph's stems; one set past them is
        # malformed, and FontForge warns about it as it reads the glyph.
        otf = font_file(self.style, "otf")
        self.assertEqual([line for line in opening_warnings(otf) if "Hint mask" in line], [])

    def test_letters_have_a_hint_edge_in_each_zone_that_holds_them(self):
        # The CFF hinter aligns hint edges, not the outline's extremes, to the alignment zones:
        # a letter or figure whose top or foot lies in a zone where none of its stems or ghosts
        # ends stood a row off the rest, as the bold E did at 14, 20 and 23 px.
        otf = fontforge.open(str(font_file(self.style, "otf")))
        blues, other = otf.private["BlueValues"], otf.private["OtherBlues"]
        fuzz = 1  # the CFF default; the fonts set no BlueFuzz
        tops = list(zip(blues[2::2], blues[3::2]))
        feet = [tuple(blues[:2]), *zip(other[::2], other[1::2])]
        for glyph in otf.glyphs():
            if not is_alphanumeric(glyph.unicode):
                continue
            # FontForge reads a top ghost as (edge, -20) and a bottom one as (edge + 21, -21).
            # Any other negative width is undefined in CFF, and FreeType aligned neither edge
            # of such a stem to a zone: the bold U's top stood a row high at 20 and 23 px.
            # Two ghosts across one span share a hint mask, and their edges cross as they are
            # hinted: the italic m's right foot fell under the baseline at 20 and 22 px.
            hints = glyph.hhints
            ghosts = [sorted((y, y + w)) for y, w in hints if w in (-20, -21)]
            with self.subTest(glyph=glyph.glyphname, hints=hints):
                self.assertTrue(all(w >= 0 or w in (-20, -21) for _, w in hints))
                self.assertFalse(any(a0 < b1 and b0 < a1 for (a0, a1), (b0, b1)
                                     in itertools.combinations(ghosts, 2)))
            top_edges = [y if w == -20 else y + w for y, w in hints if w != -21]
            foot_edges = [y + w if w == -21 else y for y, w in hints if w != -20]
            _, y0, _, y1 = glyph.boundingBox()
            for y, zones, edges in ((y1, tops, top_edges), (y0, feet, foot_edges)):
                for low, high in zones:
                    if low - fuzz <= y <= high + fuzz:
                        with self.subTest(glyph=glyph.glyphname, extreme=y):
                            self.assertTrue(any(low - fuzz <= e <= high + fuzz for e in edges))
        otf.close()

    def test_mac_style_has_the_bold_bit_in_the_bold_alone(self):
        # make_bold leaves macStyle to FontForge, which derives it from the weight.
        for font in self.fonts:
            with self.subTest(font=font.name):
                mac_style = struct.unpack_from(">H", sfnt.tables(font)[b"head"], HEAD_MAC_STYLE)[0]
                self.assertEqual(mac_style & 1, int(self.style == "Bold"))


class GenerateDateTest(unittest.TestCase):
    def test_both_formats_carry_the_build_time(self):
        epoch = 1700000000
        with tempfile.TemporaryDirectory() as tmp:
            for ext in ("otf", "ttf"):
                out = pathlib.Path(tmp) / f"ComicCaret-Regular.{ext}"
                result = subprocess.run(
                    ["fontforge", "-quiet", "-script", str(GENERATE), str(SFD), str(out)],
                    check=False, text=True, capture_output=True,
                    env={**os.environ, "SOURCE_DATE_EPOCH": str(epoch)})
                self.assertEqual(result.returncode, 0, result.stderr)
                with self.subTest(format=ext):
                    head = sfnt.tables(out)[b"head"]
                    self.assertEqual(struct.unpack_from(">q", head, HEAD_MODIFIED)[0],
                                     epoch + MAC_EPOCH)


class ItalicBuiltFontTest(BuiltFontTest):
    style = "Italic"


class BoldBuiltFontTest(BuiltFontTest):
    style = "Bold"


class LigatureSeamTest(unittest.TestCase):
    """Under FreeType's light and native hinting, each ligature piece's bar meets the next
    piece's on the same pixel rows. The autohinter, and ttfautohint's hints, which follow it,
    hint each glyph alone, so a bar edge that strays from its profile, or an arm end aligned to
    the baseline or x-height zone, moves that piece's bar a row off. The seams are checked
    in the TrueType fonts only: FreeType reads the OpenType fonts' own hints. Skips without
    uvx."""

    style = "Regular"

    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        require_current_build((cls.style,))

    known = frozenset()

    def test_pieces_meet_on_the_same_pixel_rows(self):
        for hinting, flag in HINTING.items():
            command = ["uvx", "--exclude-newer", FREETYPE_EXCLUDE_NEWER, *FREETYPE, "python",
                       "-c", SEAMS, str(font_file(self.style, "ttf")), json.dumps(SEAMED), flag]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            with self.subTest(hinting=hinting):
                off = {name: sizes for name, sizes in json.loads(result.stdout).items()
                       if name not in self.known}
                self.assertEqual(off, {})

    def test_equals_keeps_two_bars_under_native_hinting(self):
        # Each font's own hints keep a white row between the bars at text sizes. The unhinted
        # TTF blurred them into one grey band at 11 px (0.02), and every font did at 8 px while
        # the gap was 106. The floors are the references' lowest: Intel One Mono's, 0.33 at 8 px
        # and 0.64 at 9 px, where Fira Code keeps 0.75 and Maple Mono 0.78.
        # The pieces of == are drawn level on a profile of their own (add_ligatures.RUNS).
        floors = {8: 0.33, **dict.fromkeys(range(9, 17), 0.64)}
        glyphs = ["equal", "equal.sta", "equal.mid", "equal.end"]
        for ext in FORMATS:
            command = ["uvx", "--exclude-newer", FREETYPE_EXCLUDE_NEWER, *FREETYPE, "python",
                       "-c", EQUALS_BARS, str(font_file(self.style, ext)), json.dumps(glyphs)]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            for glyph, contrasts in json.loads(result.stdout).items():
                for size, contrast in contrasts.items():
                    with self.subTest(ext=ext, glyph=glyph, size=size):
                        self.assertGreaterEqual(contrast, floors[int(size)])


class GlyphBoxTest(unittest.TestCase):
    """In the TTF each glyph's box is its points' box, as tools that recompute it find it: the
    Nerd Fonts patcher does, so a box FontForge wrote a unit off gave the two builds different
    extents (hb-shape --show-extents). Skips without uvx."""

    style = "Regular"

    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        require_current_build((cls.style,))

    def test_boxes_are_their_points_boxes(self):
        command = ["uvx", "--exclude-newer", FREETYPE_EXCLUDE_NEWER, *FREETYPE, "python", "-c",
                   BOXES, str(font_file(self.style, "ttf"))]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {})


class ItalicGlyphBoxTest(GlyphBoxTest):
    style = "Italic"


class BoldGlyphBoxTest(GlyphBoxTest):
    style = "Bold"


class ItalicLigatureSeamTest(LigatureSeamTest):
    style = "Italic"


class BoldLigatureSeamTest(LigatureSeamTest):
    style = "Bold"
    # Known exception: <=<'s tail, whose bars the autohinter, and ttfautohint after it, place
    # from another first edge than ='s at 15-36 px; reshaping its arms only moves the sizes
    # (docs/design-notes.md).
    known = frozenset({"less.dtail"})


class MarkShapingTest(unittest.TestCase):
    """Combining marks in shaped text: composed where the font has the letter, and otherwise
    placed on the glyph before them."""

    style = "Regular"
    slant = 0     # how far ink at a height moves per unit above the math axis
    rounding = 0  # how far a placed mark may miss its cell through rounding

    @classmethod
    def setUpClass(cls):
        require_current_build((cls.style,))
        cls.fonts = FONTS[cls.style]
        sfd = fontforge.open(str(STYLES[cls.style]))
        # Not the soft hyphen: shapers skip a default ignorable, and a mark after one goes on
        # the character before it.
        cls.bases = [chr(g.unicode) for g in sfd.glyphs() if g.unicode >= 0
                     and unicodedata.category(chr(g.unicode)) not in ("Mn", "Cf")]
        cls.names = {g.unicode: g.glyphname for g in sfd.glyphs() if g.unicode >= 0}

    def test_marks_land_on_the_glyph_before_them(self):
        # Inside its cell, above or below: a mark after a glyph without anchors would land on
        # the next cell. Each base and its mark make one cluster, two characters long and one
        # cell wide, whether they compose or not. The italic's cell is sheared: ink at a
        # height y may lie left of it below the axis and right of it above, by (y - AXIS)
        # times the slant.
        for font in self.fonts:
            for mark in (0x301, 0x326):
                with self.subTest(font=font.name, mark=f"U+{mark:04X}"):
                    text = "".join(base + chr(mark) for base in self.bases)
                    outside = {}
                    for cluster, name, (x0, y0, x1, y1) in placed(font, text):
                        cell = cluster // 2 * ADVANCE
                        left = cell + (y0 - AXIS) * self.slant - self.rounding
                        right = cell + ADVANCE + (y1 - AXIS) * self.slant + self.rounding
                        if name == self.names[mark] and (x0 < left or x1 > right):
                            outside[self.bases[cluster // 2]] = (round(x0 - cell),
                                                                 round(x1 - cell))
                    self.assertEqual(outside, {})

    def test_stacked_marks_stay_apart(self):
        # Two marks above, or two below, one over the other without touching. Canonical order
        # puts the cedilla (class 202) before the comma below (220).
        for font in self.fonts:
            for text in ("x\u0308\u0301", "x\u0327\u0326"):
                with self.subTest(font=font.name, text=ascii(text)):
                    [_, (_, _, (_, low0, _, high0)), (_, _, (_, low1, _, high1))] = \
                        placed(font, text)
                    self.assertTrue(low1 > high0 or high1 < low0)

    def test_i_and_j_lose_their_dot_under_a_mark_above(self):
        for font in self.fonts:
            with self.subTest(font=font.name):
                self.assertEqual([name for name, _, _ in shape(font, "i\u030C j\u030C i\u0326")],
                                 ["dotlessi", "uni030C", "space", "dotlessj", "uni030C",
                                  "space", "i", "uni0326"])


class ItalicMarkShapingTest(MarkShapingTest):
    style = "Italic"
    slant = SLANT
    rounding = 2  # a sheared outline's points and its anchors are each rounded to units


class BoldMarkShapingTest(MarkShapingTest):
    style = "Bold"


class SanitizerTest(NerdBuilds, unittest.TestCase):
    """Every built font passes ots, which rejects a font whose tables break the spec's rules
    before a browser loads it. A Nerd Fonts build older than the SFDs is skipped by name, as in
    NerdFontTest. Skips without uvx."""

    @classmethod
    def setUpClass(cls):
        if shutil.which("uvx") is None:
            raise unittest.SkipTest("uvx is not installed")
        require_current_build()
        nerd, cls.stale = nerd_fonts()
        cls.fonts = [font for fonts in FONTS.values() for font in fonts] + nerd

    def test_fonts_pass_the_sanitizer(self):
        for font in self.fonts:
            with self.subTest(font=font.name):
                result = sanitize(font)
                self.assertEqual(result.returncode, 0, result.stderr)


class NerdFontTest(NerdBuilds, unittest.TestCase):
    """The Nerd Fonts builds keep our box drawing, block elements, Braille, Powerline symbols
    and ❮ ❯ ❰ ❱.

    The patcher swaps in its own box set unless the font has all of U+2500–U+259F, its own
    Braille unless --careful finds all of U+2800–U+28FF, its own Powerline symbols where
    --careful doesn't find ours, and fills U+276C–U+2771 (❬ ❭ ❮ ❯ ❰ ❱) only where the font has
    no glyph.
    """

    def test_patched_fonts_keep_the_zero_widths(self):
        # But in the Mono variant, where the patcher gives every glyph one advance on purpose.
        sfd = fontforge.open(str(SFD))
        marks = {g.glyphname for g in sfd.glyphs() if takes_no_cell(g.unicode)}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                widths = advances(nerd)
                advance = ADVANCE if "NerdFontMono-" in nerd.name else 0
                self.assertEqual({name: widths[name] for name in marks},
                                 dict.fromkeys(marks, advance))

    def test_patched_fonts_keep_our_glyphs(self):
        text = "".join(chr(code) for code in [*range(0x2500, 0x25A0), *range(0x2800, 0x2900),
                                              *range(0xE0A0, 0xE0A3), *range(0xE0B0, 0xE0B4)])
        text += "❮❯❰❱"
        plain = {(style, font.suffix): font for style, fonts in FONTS.items() for font in fonts}
        for nerd in self.fonts:
            with self.subTest(font=nerd.name):
                self.assertEqual(shape(nerd, text),
                                 shape(plain[style_of(nerd), nerd.suffix], text))


class ReleaseZipTest(unittest.TestCase):
    """The zips ./build.sh --release makes hold the fonts of this version and nothing else.

    The Nerd Fonts zip takes everything build/nerd/ holds, so a Mono or Propo variant left
    there, or any stray file, would ship. A zip of another version or older than the SFDs
    says nothing about the font as it is now, so the class skips.
    """

    @classmethod
    def setUpClass(cls):
        cls.version = sfd_version(SFD)
        cls.plain = ROOT / "dist" / f"ComicCaret-{cls.version}.zip"
        cls.nerd = ROOT / "dist" / f"ComicCaretNerdFont-{cls.version}.zip"
        newest = newest_sfd()
        for zip_path in (cls.plain, cls.nerd):
            if not zip_path.exists():
                raise unittest.SkipTest(f"no {zip_path.name}; build it with ./build.sh --release")
            if zip_path.stat().st_mtime <= newest:
                raise unittest.SkipTest(f"{zip_path.name} is older than the SFDs")

    @staticmethod
    def fonts(prefix):
        return {f"{prefix}-{style}.{ext}" for style in STYLES for ext in ("otf", "ttf")}

    def test_the_plain_zip_holds_the_fonts_and_the_license(self):
        with zipfile.ZipFile(self.plain) as zf:
            self.assertEqual(sorted(zf.namelist()),
                             sorted(self.fonts("ComicCaret") | {"LICENSE.md"}))

    def test_the_nerd_zip_holds_only_the_default_variant(self):
        with zipfile.ZipFile(self.nerd) as zf:
            self.assertEqual(sorted(zf.namelist()),
                             sorted(self.fonts("ComicCaretNerdFont")
                                    | {"ICON-LICENSES.txt", "LICENSE.md"}))

    def test_every_font_is_of_this_version(self):
        for zip_path in (self.plain, self.nerd):
            with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory() as tmp:
                for name in zf.namelist():
                    if name.endswith((".otf", ".ttf")):
                        with self.subTest(zip=zip_path.name, font=name):
                            font = pathlib.Path(zf.extract(name, tmp))
                            # The Nerd Fonts patcher appends ";Nerd Fonts X.Y.Z" to the version.
                            release = english_names(font)[5].split(";")[0]
                            self.assertEqual(release, f"Version {font_version(self.version)}")

    def test_the_license_is_the_repositorys(self):
        for zip_path in (self.plain, self.nerd):
            with self.subTest(zip=zip_path.name), zipfile.ZipFile(zip_path) as zf:
                self.assertEqual(zf.read("LICENSE.md"), (ROOT / "LICENSE.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
