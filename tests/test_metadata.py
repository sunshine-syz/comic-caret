"""Checks on the font's names, version and copyright in the SFD.

Run: python3 -m unittest discover tests
"""
import pathlib
import re
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
from project import ROOT, SFD

HOME = "https://github.com/sunshine-syz/comic-caret"
SET_BY_HAND = range(8, 15)  # name IDs in LangName; FontForge derives 0-7 from other fields


def lang_name_fields():
    """The quoted strings of the SFD's English LangName line, indexed by name ID."""
    with open(SFD, encoding="utf-8") as sfd:
        for line in sfd:
            if line.startswith("LangName: 1033 "):
                return re.findall(r'"([^"]*)"', line)
    return []


class MetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.names = {strid: text for lang, strid, text in cls.font.sfnt_names
                     if lang == "English (US)"}

    def test_license_and_font_list_the_same_copyright_holders(self):
        license_text = (ROOT / "LICENSE.md").read_text(encoding="utf-8")
        in_license = re.findall(r"^Copyright \(c\) (.+)$", license_text, re.MULTILINE)
        prefix = "Copyright (c) "
        self.assertTrue(self.font.copyright.startswith(prefix))
        self.assertEqual(self.font.copyright.removeprefix(prefix).split(", "), in_license)

    def test_lang_name_leaves_derived_names_to_fontforge(self):
        # Hard-coded family, version or unique ID records would override the derived ones.
        set_ids = {i for i, text in enumerate(lang_name_fields()) if text}
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


if __name__ == "__main__":
    unittest.main()
