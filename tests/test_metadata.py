"""Checks on the font's names, version, copyright and declared metrics in the SFD.

Run: python3 -m unittest discover tests
"""
import pathlib
import re
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import make_bold
import make_italic
from project import BOLD_SFD, ITALIC_SFD, LINE_BOTTOM, LINE_TOP, ROOT, SFD

HOME = "https://github.com/sunshine-syz/comic-caret"
SET_BY_HAND = range(8, 15)  # name IDs in LangName; FontForge derives 0-7 from other fields
REGULAR_BIT = 0x0040  # OS/2 fsSelection
# What every style of the family declares alike: the names set by hand, the em and the line
# box, the heights, weight and width, the underline, strikeout, subscript and superscript
# metrics, the copyright, version and vendor. PANOSE differs in the letterform alone.
SHARED = ("familyname", "weight", "copyright", "version", "em", "ascent", "descent",
          "hhea_ascent", "hhea_descent", "hhea_linegap", "os2_typoascent", "os2_typodescent",
          "os2_typolinegap", "os2_use_typo_metrics", "os2_capheight", "os2_xheight",
          "os2_weight", "os2_width", "os2_vendor", "os2_version", "upos",
          "uwidth", "os2_strikeypos", "os2_strikeysize", "os2_subxsize", "os2_subysize",
          "os2_subxoff", "os2_subyoff", "os2_supxsize", "os2_supysize", "os2_supxoff",
          "os2_supyoff", "encoding")
# PANOSE 2.0, Latin Text: the places of the digits the tests check, and their values.
FAMILY, WEIGHT, PROPORTION, LETTERFORM = 0, 2, 3, 7
LATIN_TEXT, MONOSPACED = 2, 9
NORMAL_FORMS, TO_OBLIQUE = range(2, 9), 7  # letterforms 2-8 upright, 9-15 the same oblique
# The glyphs whose extremes each alignment zone holds, in BlueValues' order: the baseline,
# then the tops of the x-height letters, the capitals and figures, and the ascenders. J and Q
# reach below the baseline, as the descenders in OtherBlues do.
CAPITALS = "ABCDEFGHIKLMNOPRSTUVWXYZ0123456789"
X_HEIGHT, ASCENDERS, DESCENDERS = "acemnorsuvwxz", "bdhkl", "gjpqy"
TOPS = (X_HEIGHT, CAPITALS, ASCENDERS)


def lang_name_fields(path=SFD):
    """The quoted strings of the SFD's English LangName line, indexed by name ID."""
    with open(path, encoding="utf-8") as sfd:
        for line in sfd:
            if line.startswith("LangName: 1033 "):
                return re.findall(r'"([^"]*)"', line)
    return []


class MetadataTest(unittest.TestCase):
    sfd = SFD
    # PostScript name, full name, the subfamily FontForge derives from them, the italic angle
    # and the OS/2 style bit: what apps pair the styles of a family by.
    style = ("ComicCaret-Regular", "Comic Caret Regular", "Regular", 0, REGULAR_BIT)

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))
        cls.names = {strid: text for lang, strid, text in cls.font.sfnt_names
                     if lang == "English (US)"}

    def test_the_line_box_is_the_one_the_tools_draw_to(self):
        # Box drawing, block elements and the Powerline separators are drawn to
        # LINE_BOTTOM..LINE_TOP.
        self.assertEqual((self.font.hhea_ascent, self.font.hhea_descent),
                         (LINE_TOP, LINE_BOTTOM))
        self.assertEqual((self.font.os2_typoascent, self.font.os2_typodescent),
                         (LINE_TOP, LINE_BOTTOM))

    def test_font_declares_its_style(self):
        font = self.font
        self.assertEqual((font.fontname, font.fullname, self.names.get("SubFamily"),
                          font.italicangle, font.os2_stylemap), self.style)

    def test_license_and_font_list_the_same_copyright_holders(self):
        license_text = (ROOT / "LICENSE.md").read_text(encoding="utf-8")
        in_license = re.findall(r"^Copyright \(c\) (.+)$", license_text, re.MULTILINE)
        prefix = "Copyright (c) "
        self.assertTrue(self.font.copyright.startswith(prefix))
        self.assertEqual(self.font.copyright.removeprefix(prefix).split(", "), in_license)

    def test_lang_name_leaves_derived_names_to_fontforge(self):
        # Hard-coded family, version or unique ID records would override the derived ones.
        set_ids = {i for i, text in enumerate(lang_name_fields(self.sfd)) if text}
        self.assertLessEqual(set_ids, set(SET_BY_HAND))

    def test_font_names_its_maker_and_home(self):
        for strid in ("Manufacturer", "Designer", "Descriptor"):
            self.assertTrue(self.names.get(strid), strid)
        self.assertEqual(self.names.get("Vendor URL"), HOME)
        self.assertTrue(self.names.get("Designer URL", "").startswith("https://"))

    def test_changelog_leads_with_this_version(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## (\S+)", changelog, re.MULTILINE)
        self.assertIsNotNone(newest)
        self.assertEqual(newest.group(1), self.font.version)

    def test_declared_heights_are_the_tops_of_x_and_H(self):
        self.assertEqual(self.font.os2_xheight, self.font["x"].boundingBox()[3])
        self.assertEqual(self.font.os2_capheight, self.font["H"].boundingBox()[3])

    def test_alignment_zones_hold_the_letters_extremes(self):
        # The OTF's hints put every extreme in a zone on one pixel row; one outside it stands
        # a row off the rest, as the bold H and the regular E did over the regular's zones.
        blues, other = self.font.private["BlueValues"], self.font.private["OtherBlues"]
        zones = list(zip(blues[::2], blues[1::2]))
        checks = [(CAPITALS + X_HEIGHT + ASCENDERS, 1, zones[0]), (DESCENDERS, 1, other)]
        checks += [(chars, 3, zone) for chars, zone in zip(TOPS, zones[1:], strict=True)]
        for chars, side, (low, high) in checks:
            for char in chars:
                with self.subTest(glyph=char, side=side):
                    self.assertTrue(low <= self.font[ord(char)].boundingBox()[side] <= high)
        # The CFF spec holds BlueScale times the tallest zone under 1.
        tallest = max(high - low for low, high in [*zones, other])
        self.assertLess(self.font.private["BlueScale"] * tallest, 1)

    def test_strikeout_covers_the_hyphen(self):
        _, bottom, _, top = self.font["hyphen"].boundingBox()
        position, size = self.font.os2_strikeypos, self.font.os2_strikeysize
        self.assertEqual((position - size, position), (bottom, top))

    def test_panose_classifies_the_font(self):
        panose = self.font.os2_panose
        # 0 is "Any": a digit left at it tells font matching nothing.
        self.assertNotIn(0, panose)
        # Proportion 9 because every glyph takes one cell (test_sanity.py); apps that list
        # monospaced fonts read it.
        self.assertEqual((panose[FAMILY], panose[PROPORTION]), (LATIN_TEXT, MONOSPACED))
        # PANOSE's weights, 2 Very Light to 11 Extra Black, run in the order of usWeightClass's
        # hundreds, and for the weights this family ships it keeps the two in step at hundreds
        # plus one, a convention rather than PANOSE's mapping (its Light is 3, where 300 would
        # give 4): the regular measures 6 Medium by PANOSE's rule and the italic, measured
        # across its slant, 5 Book, so both declare 5 with usWeightClass 400, as Intel One
        # Mono's and Maple Mono's 400 do.
        self.assertEqual(panose[WEIGHT], self.font.os2_weight // 100 + 1)


class ItalicMetadataTest(MetadataTest):
    sfd = ITALIC_SFD
    style = (make_italic.FONTNAME, make_italic.FULLNAME, "Italic", -make_italic.ANGLE,
             make_italic.ITALIC_BIT)

    def test_everything_but_the_style_is_the_regulars(self):
        regular = fontforge.open(str(SFD))
        for field in SHARED:
            with self.subTest(field=field):
                self.assertEqual(getattr(self.font, field), getattr(regular, field))
        self.assertEqual(lang_name_fields(ITALIC_SFD), lang_name_fields(SFD))

    def test_panose_is_the_regulars_with_an_oblique_letterform(self):
        # The italic is the regular sheared, and PANOSE measures an oblique font along its
        # slant, so only the letterform changes: the regular's, made oblique by a slant of more
        # than 5°.
        regular = fontforge.open(str(SFD)).os2_panose
        self.assertIn(regular[LETTERFORM], NORMAL_FORMS)
        self.assertGreater(-self.font.italicangle, 5)
        oblique = (*regular[:LETTERFORM], regular[LETTERFORM] + TO_OBLIQUE,
                   *regular[LETTERFORM + 1:])
        self.assertEqual(self.font.os2_panose, oblique)


class BoldMetadataTest(MetadataTest):
    sfd = BOLD_SFD
    style = (make_bold.FONTNAME, make_bold.FULLNAME, "Bold", 0, make_bold.BOLD_BIT)

    def test_everything_but_the_weight_is_the_regulars(self):
        regular = fontforge.open(str(SFD))
        # The bold's own: its heavier strokes move the hyphen and the tops of x and H.
        weight = {"weight", "os2_weight", "os2_strikeypos", "os2_strikeysize", "os2_xheight",
                  "os2_capheight"}
        for field in set(SHARED) - weight:
            with self.subTest(field=field):
                self.assertEqual(getattr(self.font, field), getattr(regular, field))
        self.assertEqual(lang_name_fields(BOLD_SFD), lang_name_fields(SFD))

    def test_panose_is_the_regulars_with_a_bold_weight(self):
        regular = fontforge.open(str(SFD)).os2_panose
        differing = [i for i, (a, b) in enumerate(zip(self.font.os2_panose, regular)) if a != b]
        self.assertEqual(differing, [WEIGHT])
        self.assertEqual(self.font.os2_panose[WEIGHT], 8)


if __name__ == "__main__":
    unittest.main()
