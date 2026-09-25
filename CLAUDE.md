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
python3 tools/add_box_drawing.py        # rebuild box drawing and block elements in the SFD
tools/render_sample.sh OUTDIR           # ligature sample images, calt on and off
python3 tools/compare_glyphs.py 'TEXT'  # our glyph positions next to the reference fonts
python3 tools/proof_sheet.py OUTDIR     # review sheet: ours next to the reference fonts
python3 tools/render_specimen.py        # the README's images in docs/images/ (committed)
```

`proof_sheet.py` takes `--before HEAD` (any commit) to add the font built from that commit's
SFD, `--text=TEXT` (repeatable) and `--features` to proof other glyphs, and `--line-height EM`
(repeatable) to check that box drawing meets across lines.

Rebuild after every SFD change, then run the checks:

```sh
python3 -m unittest discover tests  # SFD rules, built fonts, shaping, Font Bakery; known exceptions are in the tests
hb-shape fonts/ComicCaret-Regular.ttf --text='->'            # --text: a leading '-' reads as an option
uvx --from opentype-sanitizer python -c 'import ots, sys; sys.exit(ots.sanitize(sys.argv[1], "/dev/null").returncode)' fonts/ComicCaret-Regular.otf
```

`tests/test_fontbakery.py` runs Font Bakery's universal profile on each built font and expects
exactly the problems its `known()` lists, each with its reason; it skips without `uvx`. To read
a full report, run `uvx fontbakery==1.1.0 check-universal fonts/ComicCaret-Regular.ttf`, one
font at a time: together, the two read as one style twice and fail the family checks.

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
  verticals span −485…1035 (they meet up to 1.5 em line height), horizontals −10…560. Block
  elements fill the cell and the line box exactly.
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
- `validate()` flags a mirrored reference (0x10, and 0x8 for its reversed contours) and a glyph
  whose own outline overlaps its reference (0x4). Mirror into an outline with
  `geo.mirrored_x`, and merge a mark that crosses its base into one outline.
- `geo.cleanup()` can move points again on an outline it already cleaned; derive a glyph from
  another's outline as saved in the font, not from the layer before cleanup.

## Designing glyphs

- Before you place, size or redraw a glyph, compare it with Fira Code, Maple Mono and Intel One
  Mono (`tools/compare_glyphs.py`) and follow what they agree on. Where they differ on how
  distinct a character should be, follow Intel One Mono, which was designed with low-vision
  developers, and keep sizes and positions within the range the three cover. All three are OFL:
  copy measurements, never outlines.
- When the hand-drawn style calls for something else, say why in the commit message.
- Draw new strokes in the font's own hand: round ends, the stem weight (about 90), the wobble.
  Reuse an existing stroke where one fits; move and shorten strokes rather than scaling them.
  The exceptions are ∞ (8's loop, scaled to fit; every reference draws ∞ lighter than its
  letters) and the `*.small` components of superscripts, fractions and signs: the
  regular glyph at 0.45 (figures), 0.55 (ª º) or 0.41 (™ © ®), thickened with
  `changeWeight(…, "CJK", …)` (the default picks a method that pushes all the weight down and
  right) so stems measure 54 ± 4, or 56 in ™ © ®; the fraction and ordinal bars are thinned to
  match. ▹ is the same kind of exception: ▷ at 0.59 thinned to a 41 outline, since at the full
  stroke its counter fills in at 16 px. Its white stays 4 short of Maple Mono's, the only
  reference's, whose outline is 37; ▸ ▴ ▵ ▾ ▿ ◂ ◃ follow it.
- Heavy marks (✔ ✘ ✖ ❯ ➜) are their light glyph (✓ ✗ ✕ > →) pushed out 23 on every side, then
  squeezed at the ends to stay 20 inside the cell. No symbol comes closer to the cell's edges
  than ● (15), so two side by side don't touch. Black shapes (● ◆
  ▶ ▸ ★) are their white shape's outer contour; the white shapes are rings of the hyphen's
  stroke, or of `o`'s for ○.
- Never make a counter narrower than the narrowest reference's, compared at the same letter
  height.
- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths; read it before changing them.
- The reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira
  Code 6.2 release, Maple Mono 7.9 Regular (the Nerd Font build works too) and
  `IntelOneMono-Regular.ttf` from the Intel One Mono 1.4.0 release (`ttf.zip`).

## Writing tests

A test fails when the font is broken, never because a glyph was redrawn on purpose. How a glyph
looks is judged on the proof sheet (`tools/proof_sheet.py`), not asserted.

- Put each check where its kind lives:
  - `test_sanity.py`: what breaks text for every glyph: the cell, the line box, `validate()`,
    hints, empty or unused glyphs.
  - `test_consistency.py`: what whole classes share: rows, centering, the math axis, mirrored
    pairs, accented letters built on their letter with marks clear of it, no copied outlines,
    Braille dots.
  - `test_built.py`: what generating the fonts must keep; `test_metadata.py`: names and
    declared metrics.
  - `test_legibility.py`, `test_latin.py`, `test_symbols.py`: rules for single glyphs.
- Prefer a class rule. Add a new glyph to its class in `test_consistency.py` (`ROWS`,
  `CENTERED`, `ON_AXIS`, `MIRRORED`) rather than writing a test for it.
- A test for one glyph states a relation any redesign must keep: look-alikes stay apart, a
  counter or gap is at least the narrowest reference's, parts don't touch, a glyph is built from
  another (a reference, turned or mirrored). Never assert a coordinate, width or offset that only
  records today's design: if the only fix for a failure is to edit the number, don't write it.
- Take thresholds from the font (another glyph, `os2_xheight`, the hyphen's middle) or from a
  reference font's floor, and say in a comment where each number comes from.
- A known exception goes in the test's exception list with its reason.
- Before relying on a new check, break a copy of the SFD the way the check guards against and
  watch it fail.

## Other

- Add user-visible changes to `CHANGELOG.md`.
- Ligatures are generated. `tools/add_ligatures.py` owns every glyph its `GENERATED` pattern
  matches (`LIG`, `*.sta`, `*.liga`, …) and every `lig_*` lookup, and rebuilds them from
  `src/ligatures.fea` on each run. Change them only there, then rerun it and `./build.sh`;
  `tests/test_add_ligatures.py` fails while the SFD is out of date. A new glyph lands after the
  generated ones, so rerun it after adding glyphs too. Its constants are
  measurements of `- = _ # ~ < > | :`; after redrawing one of those, measure again until
  `MeasurementTest` passes, then rerun it.
- Box Drawing and Block Elements (U+2500–U+259F) are generated too, geometric rather than
  hand-drawn so they tile. `tools/add_box_drawing.py` draws each glyph from its Unicode name
  and redraws the range in place; change them only there, then rerun it and `./build.sh`.
  `tests/test_add_box_drawing.py` fails while the SFD is out of date. Keep the range complete:
  the Nerd Fonts patcher replaces all of it unless every glyph is there.
