"""Set the font's version in the SFD and CHANGELOG.md together, and check a release tag.

    python3 tools/bump_version.py X.Y               # start the next version
    python3 tools/bump_version.py --release         # date the changelog's unreleased head
    python3 tools/bump_version.py --check-tag vX.Y  # refuse a tag that isn't that release

The SFDs' Version: always heads CHANGELOG.md (tests/test_metadata.py checks the pair); the
italic and the bold are written too, so a bump never leaves them behind the regular they are
derived from. A version is "unreleased" there until --release gives it its month, as in
"## 2.1 (2026-10)". The font files carry X.Y as X.Y00 (font_version).
"""
import argparse
import datetime
import re
import sys

import fontforge

from project import ROOT, STYLES

CHANGELOG = ROOT / "CHANGELOG.md"
SFDS = tuple(STYLES.values())
# One digit of Y, so that X.Y00, the form the font files carry, names one version.
VERSION = re.compile(r"\d+\.\d")
HEADING = re.compile(r"^## (\S+) \((.+)\)$", re.MULTILINE)
FIRST_HEADING = re.compile(r"^## .*$", re.MULTILINE)
VALID_HEADING = re.compile(rf"## ({VERSION.pattern}) \((unreleased|\d{{4}}-(?:0[1-9]|1[0-2]))\)")
UNRELEASED = "unreleased"


class VersionError(Exception):
    """A version or tag that doesn't fit the SFD and the changelog; nothing was written."""


def sfd_version(sfd):
    # Reading the text is enough, and far quicker than opening the SFD in FontForge.
    match = re.search(r"^Version: (.+)$", sfd.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise VersionError(f"{sfd.name} has no Version:")
    return match.group(1)


def headings(text):
    """[(version, month or "unreleased", match)] of the changelog's headings, newest first."""
    return [(match.group(1), match.group(2), match) for match in HEADING.finditer(text)]


def newest(text, changelog):
    """The first `## ` heading, which must be well formed: a skipped one would let an older
    heading's version be read as the head."""
    first = FIRST_HEADING.search(text)
    if first is None:
        raise VersionError(f"{changelog.name} has no version heading")
    valid = VALID_HEADING.fullmatch(first.group())
    if valid is None:
        raise VersionError(f"{changelog.name}'s first heading, {first.group()!r}, is not "
                           f"'## X.Y (unreleased)' or '## X.Y (YYYY-MM)'")
    return valid.group(1), valid.group(2), first


def check_sfds(sfds, version, changelog):
    """Refuse unless every SFD is at `version`, the changelog's head."""
    for sfd in sfds:
        if sfd_version(sfd) != version:
            raise VersionError(f"{changelog.name} heads with {version}, but {sfd.name} is "
                               f"{sfd_version(sfd)}")


def ordered(version):
    return tuple(int(part) for part in version.split("."))


def font_version(version):
    """X.Y as the font files carry it, X.Y00: 2.1 ships as 2.100.

    head.fontRevision holds one decimal number, and Font Bakery reads name ID 5 as one too.
    2.1 stays above 2.001, which 2.0.1, the last X.Y.Z release, shipped as. Intel One Mono
    ships its 1.4.0 the same way, as 1.400.
    """
    major, minor = ordered(version)
    return f"{major}.{minor}00"


def start(version, sfds=SFDS, changelog=CHANGELOG):
    """Make `version` the SFDs' and the changelog's newest, unreleased.

    An unreleased head is renamed, keeping its entries; after a release, a new head goes on top.
    """
    if not VERSION.fullmatch(version):
        raise VersionError(f"{version!r} is not X.Y with Y below 10")
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
    for sfd in sfds:
        font = fontforge.open(str(sfd))
        font.version = version
        font.save(str(sfd))
        font.close()
    changelog.write_text(text, encoding="utf-8")


def release(sfds=SFDS, changelog=CHANGELOG, today=None):
    """Give the changelog's unreleased head this month; returns the tag to make."""
    text = changelog.read_text(encoding="utf-8")
    version, month, head = newest(text, changelog)
    if month != UNRELEASED:
        raise VersionError(f"{version} was released in {month}; start the next version first")
    check_sfds(sfds, version, changelog)
    # The release is named for the maintainer's calendar, not UTC's.
    today = today or datetime.datetime.now().astimezone().date()
    changelog.write_text(text[:head.start()] + f"## {version} ({today:%Y-%m})"
                         + text[head.end():], encoding="utf-8")
    return f"v{version}"


def check_tag(tag, sfds=SFDS, changelog=CHANGELOG):
    """Refuse `tag` unless it names the SFDs' version, released at the changelog's head."""
    version, month, _ = newest(changelog.read_text(encoding="utf-8"), changelog)
    check_sfds(sfds, version, changelog)
    if tag == version:
        raise VersionError(f"{tag} lacks its leading v; the tag is v{version}")
    if tag != f"v{version}":
        raise VersionError(f"{tag} doesn't name the SFD's version; the tag is v{version}")
    if month == UNRELEASED:
        raise VersionError(f"{version} is unreleased; run tools/bump_version.py --release first")


def main(argv=None, sfds=SFDS, changelog=CHANGELOG):
    """Returns the exit code; the files are parameters so tests can use copies."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("version", nargs="?", help="start this version, X.Y")
    action.add_argument("--release", action="store_true",
                        help="date the changelog's unreleased head with this month")
    action.add_argument("--check-tag", metavar="TAG",
                        help="exit non-zero unless TAG is v + the released version")
    args = parser.parse_args(argv)
    try:
        if args.release:
            tag = release(sfds, changelog)
            print(f"Dated {tag[1:]} in {changelog.name}; commit, build and check, then tag {tag}.")
        elif args.check_tag:
            check_tag(args.check_tag, sfds, changelog)
            names = ", ".join(sfd.name for sfd in sfds)
            print(f"{args.check_tag} matches {names} and {changelog.name}.")
        else:
            start(args.version, sfds, changelog)
            names = ", ".join(sfd.name for sfd in sfds)
            print(f"{names} and {changelog.name} are at {args.version}, unreleased.")
    except VersionError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
