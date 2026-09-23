# CLAUDE.md

Comic Caret is a single-weight monospaced font (MIT), forked from Comic Shanns Mono. The whole
font is `src/ComicCaret-Regular.sfd`; `fonts/` and `build/` hold gitignored build outputs.

## Commands

Needs Homebrew `fontforge` (its module imports from `python3`), HarfBuzz and `uvx`.

```sh
./build.sh                              # SFD -> fonts/ComicCaret-Regular.{otf,ttf}
./build.sh --nerd                       # also Nerd Font Mono copies -> build/nerd/
python3 tools/compare_glyphs.py 'TEXT'  # our glyph positions next to the reference fonts
```

Rebuild after every SFD change, then run the checks:

```sh
# Expect non-550 [], 0x80000 0, and other {'uni2204': '0x4'} only
fontforge -quiet -lang=py -c '
import fontforge, sys
f = fontforge.open(sys.argv[1])
v = {g.glyphname: g.validate(True) for g in f.glyphs()}
print("non-550:", [g.glyphname for g in f.glyphs() if g.width != 550])
print("0x80000:", sum(1 for x in v.values() if x & 0x80000))
print("other:", {n: hex(x) for n, x in v.items() if x & ~0x80001})
' src/ComicCaret-Regular.sfd

hb-shape fonts/ComicCaret-Regular.ttf --text='->'            # --text: a leading '-' reads as an option
uvx fontbakery check-universal fonts/ComicCaret-Regular.ttf  # expect 0 FAIL
uvx --from opentype-sanitizer python -c 'import ots, sys; sys.exit(ots.sanitize(sys.argv[1], "/dev/null").returncode)' fonts/ComicCaret-Regular.otf
```

Ignore the Nerd Fonts patcher's "Fontforge 20251009 produces unusable fonts" warning; it does
not affect this font.

## Editing the SFD

- Edit only through FontForge (GUI or `import fontforge`). `Refer:` lines address glyphs by
  index, so hand edits silently break composites.
- Every glyph, `.notdef` included, is 550 wide.
- Build accented and derived glyphs from references to base glyphs, not copied outlines.
- Give new or changed glyphs integer coordinates and a clean `validate()` (validate again after
  `glyph.round()`), then run `glyph.autoHint()` so no glyph keeps the `H` flag.
- Metrics: em 1000, cap height 668 and x-height 473 (the tops of `H` and `x`), hhea = typo =
  850/−350 with `USE_TYPO_METRICS`. Box-drawing verticals span −360…860.
- Don't hard-code what FontForge derives: OS/2 code pages and Unicode ranges, Win
  ascent/descent, the shipped names and version, `sfntRevision`. `LangName` holds only name IDs
  13 and 14.
- The copyright holders appear in the SFD `Copyright:` field and in `LICENSE.md`; keep both in
  sync.
- SFD diffs are noisy: saves rewrite `ModificationTime` and hints, and deleting a glyph
  renumbers every later index.

## FontForge Python pitfalls

- Assigning `glyph.foreground` drops hint masks; call `glyph.autoHint()` afterwards.
- `glyph.transform()` also shifts `vwidth`; transform `glyph.foreground.dup()` and assign it back.
- Composites keep stale bounds in the process that edited their base glyph; hint them and
  generate from a fresh process.
- `glyph.unicode = -1` switches the font to a `Custom` encoding; set
  `font.encoding = "UnicodeBmp"` afterwards.
- Don't save from a process that validated every glyph; it writes `Validated:` into all of them.

## Designing glyphs

- Before you place, size or redraw a glyph, compare it with Fira Code and Maple Mono
  (`tools/compare_glyphs.py`) and follow what they agree on. Both are OFL: copy measurements,
  never outlines.
- When the hand-drawn style calls for something else, say why in the commit message.
- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- The reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira
  Code 6.2 release and Maple Mono 7.9 Regular (the Nerd Font build works too).

## Other

- Add user-visible changes to `CHANGELOG.md`.
- The font has no GSUB/GPOS yet.
