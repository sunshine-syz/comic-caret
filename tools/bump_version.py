"""Set the font's version in the SFD and CHANGELOG.md together, and check a release tag.

    python3 tools/bump_version.py X.Y.Z               # start the next version
    python3 tools/bump_version.py --release           # date the changelog's unreleased head
    python3 tools/bump_version.py --check-tag vX.Y.Z  # refuse a tag that isn't that release

The SFD's Version: always heads CHANGELOG.md (tests/test_metadata.py checks the pair). A
version is "unreleased" there until --release gives it its month, as in "## 1.0.0 (2026-09)".
"""
import argparse
import datetime
import re
import sys

import fontforge

from project import ROOT, SFD

CHANGELOG = ROOT / "CHANGELOG.md"
VERSION = re.compile(r"\d+\.\d+\.\d+")
HEADING = re.compile(r"^## (\S+) \((.+)\)$", re.MULTILINE)
UNRELEASED = "unreleased"


class VersionError(Exception):
    """A version or tag that doesn't fit the SFD and the changelog; nothing was written."""


def sfd_version(sfd=SFD):
    # Reading the text is enough, and far quicker than opening the SFD in FontForge.
    match = re.search(r"^Version: (.+)$", sfd.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise VersionError(f"{sfd.name} has no Version:")
    return match.group(1)


def headings(text):
    """[(version, month or "unreleased", match)] of the changelog's headings, newest first."""
    return [(match.group(1), match.group(2), match) for match in HEADING.finditer(text)]


def newest(text, changelog):
    heads = headings(text)
    if not heads:
        raise VersionError(f"{changelog.name} has no version heading")
    return heads[0]


def ordered(version):
    return tuple(int(part) for part in version.split("."))


def start(version, sfd=SFD, changelog=CHANGELOG):
    """Make `version` the SFD's and the changelog's newest, unreleased.

    An unreleased head is renamed, keeping its entries; after a release, a new head goes on top.
    """
    if not VERSION.fullmatch(version):
        raise VersionError(f"{version!r} is not X.Y.Z")
    text = changelog.read_text(encoding="utf-8")
    _, month, head = newest(text, changelog)
    released = [v for v, m, _ in headings(text) if m != UNRELEASED]
    if released and ordered(version) <= ordered(released[0]):
        raise VersionError(f"{version} is not above the last release, {released[0]}")
    heading = f"## {version} ({UNRELEASED})"
    if month == UNRELEASED:
        text = text[:head.start()] + heading + text[head.end():]
    else:
        text = text[:head.start()] + heading + "\n\n" + text[head.start():]
    font = fontforge.open(str(sfd))
    font.version = version
    font.save(str(sfd))
    font.close()
    changelog.write_text(text, encoding="utf-8")


def release(sfd=SFD, changelog=CHANGELOG, today=None):
    """Give the changelog's unreleased head this month; returns the tag to make."""
    text = changelog.read_text(encoding="utf-8")
    version, month, head = newest(text, changelog)
    if month != UNRELEASED:
        raise VersionError(f"{version} was released in {month}; start the next version first")
    if version != sfd_version(sfd):
        raise VersionError(f"{changelog.name} heads with {version}, but {sfd.name} is "
                           f"{sfd_version(sfd)}")
    today = today or datetime.datetime.now(datetime.UTC).date()
    changelog.write_text(text[:head.start()] + f"## {version} ({today:%Y-%m})"
                         + text[head.end():], encoding="utf-8")
    return f"v{version}"


def check_tag(tag, sfd=SFD, changelog=CHANGELOG):
    """Refuse `tag` unless it names the SFD's version, released at the changelog's head."""
    version = sfd_version(sfd)
    if tag != f"v{version}":
        raise VersionError(f"{tag} doesn't name the SFD's version; the tag is v{version}")
    head, month, _ = newest(changelog.read_text(encoding="utf-8"), changelog)
    if head != version:
        raise VersionError(f"{changelog.name} heads with {head}, not {version}")
    if month == UNRELEASED:
        raise VersionError(f"{version} is unreleased; run tools/bump_version.py --release first")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("version", nargs="?", help="start this version, X.Y.Z")
    action.add_argument("--release", action="store_true",
                        help="date the changelog's unreleased head with this month")
    action.add_argument("--check-tag", metavar="TAG",
                        help="exit non-zero unless TAG is v + the released version")
    args = parser.parse_args()
    try:
        if args.release:
            tag = release()
            print(f"Dated {tag[1:]} in {CHANGELOG.name}; commit, build and check, then tag {tag}.")
        elif args.check_tag:
            check_tag(args.check_tag)
            print(f"{args.check_tag} matches {SFD.name} and {CHANGELOG.name}.")
        else:
            start(args.version)
            print(f"{SFD.name} and {CHANGELOG.name} are at {args.version}, unreleased.")
    except VersionError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
