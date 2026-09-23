# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Comic Caret is a single-weight monospaced font inspired by Comic Sans (MIT), forked from Comic Shanns Mono. There is no application code.
The whole font lives in one FontForge source file, `src/ComicCaret-Regular.sfd`. `fonts/*.otf` and `fonts/*.ttf` are build outputs; they are gitignored and not committed.

## Commands

Requires Homebrew `fontforge` on `PATH`. Its Python module is also importable from `python3`, and `hb-shape`/`hb-view` (HarfBuzz) are installed.

```sh
./build.sh           # SFD -> fonts/ComicCaret-Regular.{otf,ttf}
./build.sh --nerd    # also Nerd Font Mono otf+ttf -> build/nerd/ (--nerd=mono,default,propo for more)
```

Run `./build.sh` after every SFD change, before the checks below. Build outputs are never
committed: both `fonts/` and the Nerd Fonts output in `build/` are gitignored. The patcher version is pinned by
`NERD_FONTS_VERSION` + `NERD_FONTS_SHA256` in `build.sh`. The patcher's "Fontforge 20251009
produces unusable fonts" warning is about a monospace TTF `hmtx` bug; HarfBuzz reads correct
550 advances from our patched output, so it does not apply here.

Builds are reproducible: `build.sh` sets `SOURCE_DATE_EPOCH` to the SFD's last commit time,
because FontForge writes the date into the unique ID (name ID 3). It generates with the flags
`opentype` (keeps `GDEF`) and `no-mac-names`.

There is no test suite. These are the checks in use:

```sh
# Monospace invariant + FontForge validation, split into the pre-existing 0x80000 flag vs everything else
fontforge -quiet -lang=py -c '
import fontforge, sys
f = fontforge.open(sys.argv[1])
v = {g.glyphname: g.validate(True) for g in f.glyphs()}
print("non-550:", [g.glyphname for g in f.glyphs() if g.width != 550])
print("0x80000:", sum(1 for x in v.values() if x & 0x80000))
print("other:", {n: hex(x) for n, x in v.items() if x & ~0x80001})
' src/ComicCaret-Regular.sfd

# Shaping check against a built font (use --text; a leading '-' is parsed as an option)
hb-shape fonts/ComicCaret-Regular.ttf --text='->'
hb-shape --output-format=json fonts/ComicCaret-Regular.otf --text='a='
```

The baseline at HEAD was already this, so a later change did not cause it:
- `other` is only `uni2204` (∄, self-intersecting, `0x4`).
- `0x80000` is set on 175 glyphs. For most of them `glyph.round()` clears it, so it marks non-integral points. Glyphs you add should not raise either count.

## Working with the SFD

- **Edit through FontForge** (GUI or `import fontforge`), not with text edits to glyph bodies. `Refer:` lines point at other glyphs by glyph index (`Refer: <gid> <unicode> ...`). Accented and derived glyphs are built from references to base glyphs (the "Replace with Reference" pass), so deleting or reordering glyphs by hand silently breaks composites. FontForge rewrites the indices when it saves.
- **Metrics:** em 1000 (ascent 750 / descent 250). OS/2 cap height 668 and x-height 473 are the tops of `H` and `x`. **Every glyph, including `.notdef`, has advance width 550.** Keep that true for any glyph you add.
- **Line box:** hhea = typo = 850/−350/0 with `USE_TYPO_METRICS`, so every platform uses the same 1.2 em line. Win ascent/descent are offsets of 0 from the bbox, so they follow the tallest and deepest glyph with no hand-synced numbers. Box-drawing verticals span the line box plus 10 units (−360…860); new box glyphs should match.
- **Computed OS/2 bits:** the SFD has no `OS2CodePages`/`OS2UnicodeRanges` lines, so FontForge computes both from the cmap when it generates. Setting either from Python or Font Info hard-codes it again.
- **TTF rendering:** the TTF is unhinted. The SFD carries a `prep` table (`TtTable: prep`) that turns on smart dropout control, and gasp v1 `0x000A`.
- **Glyph hygiene:** new or redrawn glyphs should have integer coordinates and pass FontForge Validate. Recent history is mostly cleanup of these two problems, and it is not finished (see the baseline above).
- **No OpenType layout yet:** the font has no GSUB/GPOS lookups and no kerning.
- **Noisy diffs:** each save changes `ModificationTime` and can rewrite hint (`HStem`/`VStem`) and `Validated:` lines on glyphs that were touched.
- **Python pitfalls:** assigning `glyph.foreground` drops per-point hint masks (validate flags `0x800000` when stems overlap); `glyph.autoHint()` restores them. `glyph.transform()` shifts `vwidth` too. After editing a base glyph, generate from a fresh process, because composites keep stale bounds in the same session.
- **Name records and version:** FontForge derives the shipped names (family, full, PostScript, `Version x.y.z`) and `head.fontRevision` from `FontName`/`FamilyName`/`FullName`/`Version:`. `LangName` holds only the license summary (name ID 13) and license URL (ID 14), and there is no `sfntRevision` line; adding either override brings back hand-synced duplicates.
- **Duplicated metadata:** the five copyright holders are listed in both the SFD `Copyright:` field (name ID 0) and `LICENSE.md`. Keep them in sync by hand.

## Changelog

`CHANGELOG.md` holds the user-facing changelog, newest release first; the README has none. New glyph sets, features and user-visible fixes get an entry there.
