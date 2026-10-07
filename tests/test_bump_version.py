"""tools/bump_version.py on copies of the SFD and a changelog, never the real ones."""
import contextlib
import datetime
import io
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import bump_version
from bump_version import VersionError
from project import ITALIC_SFD, SFD

RELEASED = "# Changelog\n\n## 1.1 (2026-10)\n\n- Two.\n\n## 1.0.1 (2026-09)\n\n- One.\n"
UNRELEASED = "# Changelog\n\n## 1.2 (unreleased)\n\n- Three.\n\n" + RELEASED[len("# Changelog\n\n"):]


class BumpVersionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)
        self.changelog = self.dir / "CHANGELOG.md"

    def sfd_at(self, version, source=SFD):
        """A copy of `source` whose Version: is `version`, as text: no FontForge save."""
        sfd = self.dir / source.name
        text = source.read_text(encoding="utf-8")
        sfd.write_text(re.sub(r"^Version: .*$", f"Version: {version}", text, count=1,
                              flags=re.MULTILINE), encoding="utf-8")
        return sfd

    def write_changelog(self, text):
        self.changelog.write_text(text, encoding="utf-8")

    def heads(self):
        return re.findall(r"^## .*$", self.changelog.read_text(encoding="utf-8"), re.MULTILINE)

    def test_start_after_a_release_heads_the_changelog_and_sets_the_sfd(self):
        sfd = self.sfd_at("1.1")
        self.write_changelog(RELEASED)
        bump_version.start("1.2", [sfd], self.changelog)
        self.assertEqual(self.heads(), ["## 1.2 (unreleased)", "## 1.1 (2026-10)",
                                        "## 1.0.1 (2026-09)"])
        self.assertEqual(bump_version.sfd_version(sfd), "1.2")

    def test_start_changes_nothing_else_in_the_sfd(self):
        sfd = self.sfd_at("1.1")
        before = sfd.read_text(encoding="utf-8").splitlines()
        self.write_changelog(RELEASED)
        bump_version.start("1.2", [sfd], self.changelog)
        after = sfd.read_text(encoding="utf-8").splitlines()
        changed = {line.split(":")[0] for line in set(before) ^ set(after)}
        self.assertLessEqual(changed, {"Version", "ModificationTime"})

    def test_start_renames_an_unreleased_head(self):
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        bump_version.start("2.0", [sfd], self.changelog)
        self.assertEqual(self.heads()[:2], ["## 2.0 (unreleased)", "## 1.1 (2026-10)"])
        self.assertIn("- Three.", self.changelog.read_text(encoding="utf-8"))
        self.assertEqual(bump_version.sfd_version(sfd), "2.0")

    def test_start_refuses_a_version_that_is_not_above_the_last_release(self):
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        for version in ("1.1", "1.0", "1.3.0", "v1.3", "1.3-rc1"):
            with self.subTest(version=version), self.assertRaises(VersionError):
                bump_version.start(version, [sfd], self.changelog)
        self.assertEqual(self.changelog.read_text(encoding="utf-8"), UNRELEASED)
        self.assertEqual(bump_version.sfd_version(sfd), "1.2")

    def test_start_refuses_a_version_the_fonts_cannot_carry(self):
        # The fonts carry X.Y00: 1.10 would ship as 1.1000, the number 1.1 ships as 1.100.
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        with self.assertRaises(VersionError):
            bump_version.start("1.10", [sfd], self.changelog)
        self.assertEqual(bump_version.sfd_version(sfd), "1.2")

    def test_font_version_keeps_releases_apart_and_in_order(self):
        versions = ["2.1", "2.2", "2.9", "3.0", "10.0"]
        numbers = [float(bump_version.font_version(version)) for version in versions]
        self.assertEqual(numbers, sorted(set(numbers)))
        self.assertEqual(bump_version.font_version("2.1"), "2.100")

    def test_release_dates_the_unreleased_head(self):
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        tag = bump_version.release([sfd], self.changelog, datetime.date(2026, 11, 3))
        self.assertEqual(tag, "v1.2")
        self.assertEqual(self.heads()[0], "## 1.2 (2026-11)")

    def test_release_refuses_a_released_head_or_another_version(self):
        for version, text in (("1.1", RELEASED), ("1.3", UNRELEASED)):
            with self.subTest(sfd=version):
                sfd = self.sfd_at(version)
                self.write_changelog(text)
                with self.assertRaises(VersionError):
                    bump_version.release([sfd], self.changelog, datetime.date(2026, 11, 3))
                self.assertEqual(self.changelog.read_text(encoding="utf-8"), text)

    def test_check_tag_accepts_only_the_released_version(self):
        sfd = self.sfd_at("1.1")
        self.write_changelog(RELEASED)
        bump_version.check_tag("v1.1", [sfd], self.changelog)
        for tag in ("v1.1.0", "1.1", "v1.0.1", "v1.2"):
            with self.subTest(tag=tag), self.assertRaises(VersionError):
                bump_version.check_tag(tag, [sfd], self.changelog)

    def test_check_tag_refuses_an_unreleased_version(self):
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        with self.assertRaises(VersionError):
            bump_version.check_tag("v1.2", [sfd], self.changelog)

    def test_check_tag_names_a_missing_v(self):
        sfd = self.sfd_at("1.1")
        self.write_changelog(RELEASED)
        with self.assertRaisesRegex(VersionError, "leading v"):
            bump_version.check_tag("1.1", [sfd], self.changelog)

    def test_check_tag_refuses_when_the_sfd_and_the_changelog_disagree(self):
        sfd = self.sfd_at("1.0.1")
        self.write_changelog(RELEASED)
        for tag in ("v1.0.1", "v1.1"):
            with self.subTest(tag=tag), self.assertRaisesRegex(VersionError, sfd.name):
                bump_version.check_tag(tag, [sfd], self.changelog)

    def test_release_and_check_tag_refuse_when_only_the_italic_differs(self):
        regular = self.sfd_at("1.2")
        italic = self.sfd_at("1.1", ITALIC_SFD)
        for text, call in ((UNRELEASED, lambda: bump_version.release(
                                [regular, italic], self.changelog, datetime.date(2026, 11, 3))),
                           (RELEASED, lambda: bump_version.check_tag(
                               "v1.1", [self.sfd_at("1.1"), self.sfd_at("1.0.1", ITALIC_SFD)],
                               self.changelog))):
            with self.subTest(text=text[:30]):
                self.write_changelog(text)
                with self.assertRaisesRegex(VersionError, ITALIC_SFD.name):
                    call()
                self.assertEqual(self.changelog.read_text(encoding="utf-8"), text)

    def test_only_the_first_heading_counts_and_it_must_be_well_formed(self):
        sfd = self.sfd_at("1.1")
        older = RELEASED[len("# Changelog\n\n"):]
        for heading in ("## 1.2 (Unreleased)", "## 1.2.0 (unreleased)", "## 1.2 (2026-13)",
                        "## 1.2 (2026-00)", "## 1.2 (2026-9)", "## 1.2", "## 1.2 (soon)",
                        "##  1.2 (unreleased)"):
            text = f"# Changelog\n\n{heading}\n\n- Three.\n\n{older}"
            with self.subTest(heading=heading):
                self.write_changelog(text)
                for call in (lambda: bump_version.release([sfd], self.changelog),
                             lambda: bump_version.check_tag("v1.1", [sfd], self.changelog),
                             lambda: bump_version.start("1.3", [sfd], self.changelog)):
                    with self.assertRaisesRegex(VersionError, re.escape(repr(heading))):
                        call()
                self.assertEqual(self.changelog.read_text(encoding="utf-8"), text)

    def test_release_dates_by_the_local_month_by_default(self):
        sfd = self.sfd_at("1.2")
        self.write_changelog(UNRELEASED)
        today = datetime.datetime.now().astimezone().date()
        bump_version.release([sfd], self.changelog)
        self.assertEqual(self.heads()[0], f"## 1.2 ({today:%Y-%m})")

    def test_main_exit_codes(self):
        regular = self.sfd_at("1.2")
        italic = self.sfd_at("1.2", ITALIC_SFD)
        sfds = [regular, italic]
        self.write_changelog(UNRELEASED)

        def run(*argv):
            return bump_version.main(list(argv), sfds, self.changelog)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run("--check-tag", "v1.2"), 1)  # still unreleased
            self.assertEqual(run("--release"), 0)
            self.assertEqual(run("--release"), 1)  # already dated
            self.assertEqual(run("--check-tag", "v1.2"), 0)
            self.assertEqual(run("--check-tag", "1.2"), 1)
            self.assertEqual(run("1.2"), 1)  # not above the last release
            self.assertEqual(run("1.3"), 0)
            self.assertEqual(bump_version.sfd_version(italic), "1.3")
            self.assertEqual(self.heads()[0], "## 1.3 (unreleased)")
            self.assertEqual(run("1.x"), 1)


if __name__ == "__main__":
    unittest.main()
