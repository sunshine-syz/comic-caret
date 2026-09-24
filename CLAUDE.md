# CLAUDE.md

Comic Caret is a single-weight monospaced font (MIT), derived from Comic Shanns Mono. The whole
font is `src/ComicCaret-Regular.sfd`; `fonts/`, `build/` and `dist/` hold gitignored build
outputs.

## Commands

Needs Homebrew `fontforge` (its module imports from `python3`), HarfBuzz and `uvx`.

```sh
./build.sh                              # SFD -> fonts/ComicCaret-Regular.{otf,ttf}
./build.sh --nerd                       # also Nerd Fonts patched copies in build/nerd/
./build.sh --release                    # everything, zipped into dist/; needs a clean checkout
python3 tools/add_ligatures.py          # rebuild the ligature glyphs and lookups in the SFD
tools/render_sample.sh OUTDIR           # ligature sample images, calt on and off
python3 tools/compare_glyphs.py 'TEXT'  # our glyph positions next to the reference fonts
python3 tools/proof_sheet.py OUTDIR     # review sheet: ours, the saved build, the references
python3 tools/render_specimen.py        # the README's images in docs/images/ (committed)
```

Rebuild after every SFD change, then run the checks:

```sh
python3 -m unittest discover tests  # SFD rules and ligature shaping; known exceptions are in the tests
hb-shape fonts/ComicCaret-Regular.ttf --text='->'            # --text: a leading '-' reads as an option
uvx fontbakery check-universal fonts/ComicCaret-Regular.ttf  # expect 0 FAIL
uvx --from opentype-sanitizer python -c 'import ots, sys; sys.exit(ots.sanitize(sys.argv[1], "/dev/null").returncode)' fonts/ComicCaret-Regular.otf
```

Ignore the Nerd Fonts patcher's "Fontforge 20251009 produces unusable fonts" warning; it does
not affect this font.

## Releasing

Font files are never committed; they ship as GitHub release assets.

1. Set the SFD `Version:` (through FontForge) and head `CHANGELOG.md` with it. If glyphs
   changed, rerun `tools/render_specimen.py` so the README shows them.
2. Commit, run `./build.sh --release`, then the checks above; the tests also check the Nerd
   Fonts builds it made, which they skip otherwise.
3. Tag the commit `vX.Y.Z` and attach both zips from `dist/` to a GitHub release.

## Editing the SFD

- Edit only through FontForge (GUI or `import fontforge`). `Refer:` lines address glyphs by
  index, so hand edits silently break composites.
- Every glyph, `.notdef` included, is 550 wide.
- Build accented and derived glyphs from references to base glyphs, not copied outlines.
- Give new or changed glyphs integer coordinates and a clean `validate()` (validate again after
  `glyph.round()`), then run `glyph.autoHint()` so no glyph keeps the `H` flag.
- Metrics: em 1000, cap height 668 and x-height 473 (the tops of `H` and `x`), hhea = typo =
  900/−350 (1.25 em) with `USE_TYPO_METRICS`. Box-drawing strokes overlap their neighbours:
  verticals span −485…1035 (they meet up to 1.5 em line height), horizontals −10…560.
- Don't hard-code what FontForge derives: OS/2 code pages and Unicode ranges, Win
  ascent/descent, the shipped names and version, `sfntRevision`. `LangName` holds only name IDs
  8–14: maker, designer, description, URLs and license.
- The copyright holders appear in the SFD `Copyright:` field and in `LICENSE.md`, and the SFD
  `Version:` heads `CHANGELOG.md`; `tests/test_metadata.py` keeps each pair in sync.
- SFD diffs are noisy: saves rewrite `ModificationTime` and hints, and deleting a glyph
  renumbers every later index.

## FontForge Python pitfalls

- Assigning `glyph.foreground` drops hint masks; call `glyph.autoHint()` afterwards.
- `glyph.transform()` also shifts `vwidth`; transform `glyph.foreground.dup()` and assign it back.
- Composites keep stale bounds in the process that edited their base glyph; hint them and
  generate from a fresh process.
- `glyph.unicode = -1` switches the font to a `Custom` encoding; set
  `font.encoding = "UnicodeBmp"` afterwards.
- Don't save from a process that validated glyphs; it writes `Validated:` into each one it
  checked.
- `font.mergeFeature()` prints feature-file errors to stderr and returns normally, merging
  nothing; check that the lookups exist afterwards.
- Saving crashes when an `rsub` rule is made only of bare glyph names; write the input glyph as
  a one-glyph class (`[a]'`).
- `removeOverlap()` mishandles edges that coincide exactly, and `layer.exclude()` returns the
  wrong region; cut with `layer.intersect()` against a box.
- `font.removeGlyph()` keeps the glyph's encoding slot; set `font.encoding = "UnicodeBmp"`
  afterwards or re-created glyphs land in new slots.
- `layer.addExtrema()` skips short segments that `validate()` still flags; pass `"all"`.
- Moving a few points of a contour can leave an extremum that `addExtrema("all")` won't add but
  `validate()` flags (0x20); keep the points next to the moved ones where they are.
- `glyph.references` gives `(name, matrix, selected)` triples; unpack them with
  `name, matrix, *_`. Assigning `(name, matrix)` pairs works, but they are written to the SFD in
  reverse order; assign them reversed to keep the file's order.

## Designing glyphs

- Before you place, size or redraw a glyph, compare it with Fira Code, Maple Mono and Intel One
  Mono (`tools/compare_glyphs.py`) and follow what they agree on. Where they differ on how
  distinct a character should be, follow Intel One Mono, which was designed with low-vision
  developers, and keep sizes and positions within the range the three cover. All three are OFL:
  copy measurements, never outlines.
- When the hand-drawn style calls for something else, say why in the commit message.
- Draw new strokes in the font's own hand: round ends, the stem weight (about 90), the wobble.
  Reuse an existing stroke where one fits; move and shorten strokes rather than scaling them.
  The one exception is the `*.small` components of superscripts, fractions and signs: the
  regular glyph at 0.41, thickened with `changeWeight(…, "CJK", …)` (the default picks a method
  that pushes all the weight down and right) so stems measure 74 ± 4, or 56 in ™ © ®.
- Never make a counter narrower than the narrowest reference's, compared at the same letter
  height.
- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths; read it before changing them.
- The reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira
  Code 6.2 release, Maple Mono 7.9 Regular (the Nerd Font build works too) and
  `IntelOneMono-Regular.ttf` from the Intel One Mono 1.4.0 release (`ttf.zip`).

## Other

- Add user-visible changes to `CHANGELOG.md`.
- Ligatures are generated. `tools/add_ligatures.py` owns every glyph its `GENERATED` pattern
  matches (`LIG`, `*.sta`, `*.liga`, …) and every `lig_*` lookup, and rebuilds them from
  `src/ligatures.fea` on each run. Change them only there, then rerun it and `./build.sh`;
  `tests/test_add_ligatures.py` fails while the SFD is out of date. A new glyph lands after the
  generated ones, so rerun it after adding glyphs too. Its constants are
  measurements of `- = _ # ~ < > | :`; after redrawing one of those, measure again until
  `MeasurementTest` passes, then rerun it.
