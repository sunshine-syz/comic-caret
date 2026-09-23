"""Build Comic Caret's coding ligatures into the SFD: the glyphs, then src/ligatures.fea.

Usage: python3 tools/add_ligatures.py [--head-scale S] [SFD]

Replaces every glyph and GSUB lookup an earlier run made, so running it again changes nothing
but ModificationTime.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

import fontforge
import psMat

import lig_geometry as geo
from lig_geometry import FAR

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFD = ROOT / "src" / "ComicCaret-Regular.sfd"
FEA = ROOT / "src" / "ligatures.fea"

ADVANCE = 550
OVERLAP = 10     # how far joined strokes reach into the neighbouring cell
AXIS = 269       # math axis: the centre of - = + and of the arrow shafts
STRETCH = 600    # pushes a stroke's cap past any cut the pieces need
HEAD_SCALE = 1.0  # arrowheads relative to < >; chosen at the prototype checkpoint
HEAD_SCALES = (0.85, 1.15)  # beyond this, stroke weight drifts from the rest of the font

# The names of everything this script makes, and of nothing else in the font.
GENERATED = re.compile(r"LIG|colon\.eq|.+\.(sta|mid|end|mid\.low|end\.low|arrow|darrow"
                       r"|liga|tight_l|tight_r)")

VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


class Bar(NamedTuple):
    cuts: tuple     # x of the stretch lines, left and right, inside the bar's straight part
    band: tuple     # y range holding this bar, and nothing else, beyond the cuts
    profile: tuple  # canonical (bottom, top) that the bar's flat edges snap to


# Straight run strokes, one Bar per horizontal stroke.
RUNS = {
    "hyphen": (Bar((200, 350), (215, 325), (231, 310)),),
    "equal": (Bar((200, 350), (135, 228), (143, 219)), Bar((200, 350), (318, 410), (326, 403))),
}

# Arrowheads: the point of > and < sits on the axis at these x.
GREATER_TIP, LESS_TIP = 462, 88
SHAFT_INTO_HEAD = 80   # a - shaft ends this far inside the point, where the arms have met
BARS_INTO_HEAD = 162   # = bars end this far inside the point, within both arms


def outline(font, name):
    return font[name].foreground.dup()


def stroke(font, name, x0=None, x1=None):
    """A run character cut flat at x0 and x1, where None keeps that end's cap.

    Each bar is first stretched past both cuts, so any x0 < x1 works.
    """
    layer = outline(font, name)
    bars = RUNS[name]
    for bar in bars:
        if x0 is not None:
            layer = geo.stretch(layer, bar.cuts[0], -STRETCH, bar.band)
        if x1 is not None:
            layer = geo.stretch(layer, bar.cuts[1], STRETCH, bar.band)
    layer = geo.trim(layer, -FAR if x0 is None else x0, FAR if x1 is None else x1)
    profile = [y for bar in bars for y in bar.profile]
    for x in (x0, x1):
        if x is not None:
            geo.snap_edge(layer, x, profile)
    return layer


def run_pieces(font):
    glyphs = {}
    for name in RUNS:
        glyphs[f"{name}.sta"] = stroke(font, name, x1=ADVANCE + OVERLAP)
        glyphs[f"{name}.mid"] = stroke(font, name, -OVERLAP, ADVANCE + OVERLAP)
        glyphs[f"{name}.end"] = stroke(font, name, x0=-OVERLAP)
    return glyphs


def head(font, name, tip, scale):
    return geo.transformed(outline(font, name), geo.about(psMat.scale(scale), tip, AXIS))


def arrowheads(font, scale):
    right, left = GREATER_TIP, LESS_TIP
    return {
        "less.arrow": geo.union(head(font, "less", left, scale),
                                stroke(font, "hyphen", left + SHAFT_INTO_HEAD, ADVANCE + OVERLAP)),
        "greater.arrow": geo.union(head(font, "greater", right, scale),
                                   stroke(font, "hyphen", -OVERLAP, right - SHAFT_INTO_HEAD)),
        "less.darrow": geo.union(head(font, "less", left, scale),
                                 stroke(font, "equal", left + BARS_INTO_HEAD, ADVANCE + OVERLAP)),
        "greater.darrow": geo.union(head(font, "greater", right, scale),
                                    stroke(font, "equal", -OVERLAP, right - BARS_INTO_HEAD)),
    }


def build(font, head_scale=HEAD_SCALE):
    """Every generated glyph in SFD order: name -> outline layer, or a list of
    (glyph, dx, dy) references for pure shifts."""
    glyphs = {}
    glyphs.update(run_pieces(font))
    glyphs.update(arrowheads(font, head_scale))
    return glyphs


def remove_previous(font):
    # Chain lookups call the single substitutions, so remove them first.
    for lookup in reversed(font.gsub_lookups):
        if lookup.startswith("lig_"):
            font.removeLookup(lookup)
    for name in [g.glyphname for g in font.glyphs() if GENERATED.fullmatch(g.glyphname)]:
        font.removeGlyph(name)
    # Removed glyphs keep their encoding slots; re-encoding frees them, so a rerun puts the
    # new glyphs in the same slots.
    font.encoding = "UnicodeBmp"


def add_glyphs(font, glyphs):
    for name, shape in glyphs.items():
        glyph = font.createChar(-1, name)
        glyph.width = ADVANCE
        if isinstance(shape, list):
            for base, dx, dy in shape:
                glyph.addReference(base, psMat.translate(dx, dy))
        else:
            glyph.foreground = geo.cleanup(shape)
            glyph.correctDirection()
        glyph.autoHint()


def merge_features(font):
    font.mergeFeature(str(FEA))
    # On a parse error FontForge prints to stderr and merges nothing, so check the result.
    declared = re.findall(r"^\s*lookup\s+(lig_\w+)\s*\{", FEA.read_text(), re.M)
    missing = sorted(set(declared) - set(font.gsub_lookups))
    if missing:
        sys.exit(f"{FEA.name} did not merge; missing lookups: {', '.join(missing)}")


def check(path):
    """Exit non-zero if a generated glyph in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    failed = {}
    for glyph in font.glyphs():
        if GENERATED.fullmatch(glyph.glyphname):
            flags = glyph.validate(True) & ~VALIDATED
            if flags:
                failed[glyph.glyphname] = hex(flags)
    if failed:
        sys.exit(f"validate() failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sfd", nargs="?", default=str(SFD), help="default: %(default)s")
    parser.add_argument("--head-scale", type=float, default=HEAD_SCALE,
                        help="arrowhead size relative to < > (default %(default)s)")
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        return check(args.sfd)
    if not HEAD_SCALES[0] <= args.head_scale <= HEAD_SCALES[1]:
        parser.error(f"--head-scale must be within {HEAD_SCALES[0]}..{HEAD_SCALES[1]}")

    sfd = pathlib.Path(args.sfd)
    font = fontforge.open(str(sfd))
    remove_previous(font)
    add_glyphs(font, build(font, args.head_scale))
    merge_features(font)
    # Validating in this process would write "Validated:" into the saved glyphs, so a fresh
    # process checks the saved copy before it replaces the SFD.
    tmp = sfd.with_name(f".{sfd.name}.tmp")
    font.save(str(tmp))
    if subprocess.run([sys.executable, __file__, "--check", str(tmp)]).returncode:
        tmp.unlink()
        sys.exit(f"{sfd} is unchanged.")
    os.replace(tmp, sfd)

if __name__ == "__main__":
    main()
