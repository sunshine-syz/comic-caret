"""Generate one font file from the SFD; build.sh runs it once per format.

Usage: fontforge -quiet -script tools/generate.py SOURCE.sfd OUTPUT.otf|OUTPUT.ttf
"""
import sys

import fontforge
import psMat


def is_composite(glyph):
    """True if the TTF stores the glyph as a composite.

    A glyph that mixes outlines and references is written as a simple glyph instead.
    """
    return bool(glyph.references) and not len(glyph.foreground)


def flatten_nested_references(font):
    """Point every composite's references straight at simple glyphs.

    The SFD nests references (Braille patterns are built from smaller patterns), but TrueType
    composites of composites render badly in some environments (Font Bakery
    nested_components).
    """

    def leaves(name, matrix):
        glyph = font[name]
        if not is_composite(glyph):
            return [(name, matrix)]
        return [leaf for ref in glyph.references
                for leaf in leaves(ref[0], psMat.compose(ref[1], matrix))]

    for glyph in font.glyphs():
        refs = glyph.references
        if is_composite(glyph) and any(is_composite(font[ref[0]]) for ref in refs):
            glyph.references = tuple(leaf for ref in refs for leaf in leaves(ref[0], ref[1]))


def main(source, output):
    # Glyphs edited since they were last hinted get autohinted while generating only if the
    # user's AutoHint preference allows it, so pin it to keep the OTF the same on every machine.
    fontforge.setPrefs("AutoHint", True)
    font = fontforge.open(source)
    # CFF has no components, so only the TTF needs this. Leaving the OTF path alone keeps its
    # stored hints valid.
    if output.endswith(".ttf"):
        flatten_nested_references(font)
    # Explicit flags replace FontForge's defaults, so "opentype" is needed to keep GDEF.
    # "no-mac-names" drops the platform-1 name records that nothing current reads.
    font.generate(output, flags=("opentype", "no-mac-names"))


if __name__ == "__main__":
    main(*sys.argv[1:])
