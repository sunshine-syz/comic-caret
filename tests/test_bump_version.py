"""tools/bump_version.py on copies of the SFD and a changelog, never the real ones."""
import datetime
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import bump_version
from bump_version import VersionError
from project import SFD

RELEASED = "# Changelog\n\n## 1.1.0 (2026-10)\n\n- Two.\n\n## 1.0.0 (2026-09)\n\n- One.\n"
UNRELEASED = "# Changelog\n\n## 1.2.0 (unreleased)\n\n- Three.\n\n" + RELEASED[len("# Changelog\n\n"):]


class BumpVersionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        self.changelog = self.dir / "CHANGELOG.md"

    def sfd_at(self, version):
        """A copy of the SFD whose Version: is `version`, as text: no FontForge save."""
        sfd = self.dir / SFD.name
        text = SFD.read_text(encoding="utf-8")
        sfd.write_text(re.sub(r"^Version: .*$", f"Version: {version}", text, count=1,
                              flags=re.MULTILINE), encoding="utf-8")
        return sfd

    def write_changelog(self, text):
        self.changelog.write_text(text, encoding="utf-8")

    def heads(self):
        return re.findall(r"^## .*$", self.changelog.read_text(encoding="utf-8"), re.MULTILINE)

    def test_start_after_a_release_heads_the_changelog_and_sets_the_sfd(self):
        sfd = self.sfd_at("1.1.0")
        self.write_changelog(RELEASED)
        bump_version.start("1.2.0", sfd, self.changelog)
        self.assertEqual(self.heads(), ["## 1.2.0 (unreleased)", "## 1.1.0 (2026-10)",
                                        "## 1.0.0 (2026-09)"])
        self.assertEqual(bump_version.sfd_version(sfd), "1.2.0")

    def test_start_changes_nothing_else_in_the_sfd(self):
        sfd = self.sfd_at("1.1.0")
        before = sfd.read_text(encoding="utf-8").splitlines()
        self.write_changelog(RELEASED)
        bump_version.start("1.2.0", sfd, self.changelog)
        after = sfd.read_text(encoding="utf-8").splitlines()
        changed = {line.split(":")[0] for line in set(before) ^ set(after)}
        self.assertLessEqual(changed, {"Version", "ModificationTime"})

    def test_start_renames_an_unreleased_head(self):
        sfd = self.sfd_at("1.2.0")
        self.write_changelog(UNRELEASED)
        bump_version.start("2.0.0", sfd, self.changelog)
        self.assertEqual(self.heads()[:2], ["## 2.0.0 (unreleased)", "## 1.1.0 (2026-10)"])
        self.assertIn("- Three.", self.changelog.read_text(encoding="utf-8"))
        self.assertEqual(bump_version.sfd_version(sfd), "2.0.0")

    def test_start_refuses_a_version_that_is_not_above_the_last_release(self):
        sfd = self.sfd_at("1.2.0")
        self.write_changelog(UNRELEASED)
        for version in ("1.1.0", "1.0.9", "1.2", "v1.3.0", "1.3.0-rc1"):
            with self.subTest(version=version), self.assertRaises(VersionError):
                bump_version.start(version, sfd, self.changelog)
        self.assertEqual(self.changelog.read_text(encoding="utf-8"), UNRELEASED)
        self.assertEqual(bump_version.sfd_version(sfd), "1.2.0")

    def test_release_dates_the_unreleased_head(self):
        sfd = self.sfd_at("1.2.0")
        self.write_changelog(UNRELEASED)
        tag = bump_version.release(sfd, self.changelog, datetime.date(2026, 11, 3))
        self.assertEqual(tag, "v1.2.0")
        self.assertEqual(self.heads()[0], "## 1.2.0 (2026-11)")

    def test_release_refuses_a_released_head_or_another_version(self):
        for version, text in (("1.1.0", RELEASED), ("1.3.0", UNRELEASED)):
            with self.subTest(sfd=version):
                sfd = self.sfd_at(version)
                self.write_changelog(text)
                with self.assertRaises(VersionError):
                    bump_version.release(sfd, self.changelog, datetime.date(2026, 11, 3))
                self.assertEqual(self.changelog.read_text(encoding="utf-8"), text)

    def test_check_tag_accepts_only_the_released_version(self):
        sfd = self.sfd_at("1.1.0")
        self.write_changelog(RELEASED)
        bump_version.check_tag("v1.1.0", sfd, self.changelog)
        for tag in ("v1.1.1", "1.1.0", "v1.0.0"):
            with self.subTest(tag=tag), self.assertRaises(VersionError):
                bump_version.check_tag(tag, sfd, self.changelog)

    def test_check_tag_refuses_an_unreleased_version(self):
        sfd = self.sfd_at("1.2.0")
        self.write_changelog(UNRELEASED)
        with self.assertRaises(VersionError):
            bump_version.check_tag("v1.2.0", sfd, self.changelog)


if __name__ == "__main__":
    unittest.main()
