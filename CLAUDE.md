# CLAUDE.md

Comic Caret is a single-weight monospaced font (MIT), derived from Comic Shanns Mono. The whole
font is `src/ComicCaret-Regular.sfd`; the italic, `src/ComicCaret-Italic.sfd`, is generated from
it by `tools/make_italic.py` and never edited by hand. `fonts/`, `build/` and `dist/` hold
gitignored build outputs. Font files are never committed; they ship as GitHub release assets.

## Commands

Needs Homebrew `fontforge` (its module imports from `python3`), HarfBuzz and `uvx`.

```sh
./build.sh                              # SFDs -> fonts/ComicCaret-{Regular,Italic}.{otf,ttf}
./build.sh --nerd                       # also Nerd Fonts patched copies in build/nerd/
./build.sh --release                    # everything, zipped into dist/; needs a clean checkout
python3 tools/add_<what>.py             # regenerate a generated range in the SFD (see below)
python3 tools/make_italic.py            # regenerate the italic SFD from the regular (see below)
python3 tools/proof_sheet.py OUTDIR     # review sheet: ours next to the reference fonts
python3 tools/compare_glyphs.py 'TEXT'  # our glyph positions next to the reference fonts
tools/render_sample.sh OUTDIR           # ligature sample images, calt on and off
python3 tools/render_specimen.py        # the README's images in docs/images/ (committed)
python3 tools/bump_version.py X.Y.Z     # start the next version: both SFDs' Version: and CHANGELOG head
```

`proof_sheet.py` takes `--text=TEXT` (repeatable) and `--features` to proof other glyphs,
`--before REV` to add the font built from that commit's SFD, and `--line-height EM` to check
that box drawing meets across lines.

After every change to the regular, rerun `tools/make_italic.py`, rebuild, rerun
`tools/render_specimen.py`, then run the checks:

```sh
python3 -m unittest discover tests  # SFD rules, built fonts, shaping, ots, Font Bakery, README images
hb-shape fonts/ComicCaret-Regular.ttf --text='->'            # --text: a leading '-' reads as an option
```

## Releasing

The version being worked on heads `CHANGELOG.md` as "unreleased"; `tools/bump_version.py X.Y.Z`
starts the next one, setting both SFDs' `Version:` and the heading together.

1. `python3 tools/bump_version.py --release` gives the heading this month.
2. Commit, run `./build.sh --release`, then the checks above; the tests also check the Nerd
   Fonts builds it made, which they skip otherwise.
3. `python3 tools/bump_version.py --check-tag vX.Y.Z` refuses a tag that isn't that release.
   Tag the commit and attach both zips from `dist/` to a GitHub release.

## The SFD

- Every glyph is drawn in the regular. The italic SFD is its output: `tools/make_italic.py`
  slants the text glyphs, keeps the graphics upright and draws the cursive letters from the
  regular's strokes, so change the regular or the generator, never the italic, and rerun it.
- Edit only through FontForge (GUI or `import fontforge`). `Refer:` lines address glyphs by
  index, so hand edits silently break composites. Before writing FontForge Python, read
  `docs/fontforge-pitfalls.md`: the module's quirks the tools work around.
- Every glyph, `.notdef` included, is 550 wide, except the combining marks (U+0300…), which
  are 0 wide with their ink over the cell, where terminals that don't shape text draw them,
  and the blank zero-width format characters (`project.ZERO_WIDTH`).
- Metrics: em 1000, cap height 668 and x-height 473 (the tops of `H` and `x`), hhea = typo =
  900/−350 (1.25 em) with `USE_TYPO_METRICS`.
- Build accented and derived glyphs from references to base glyphs, not copied outlines.
- Give new or changed glyphs integer coordinates and a clean `validate()` (validate again after
  `glyph.round()`), then run `glyph.autoHint()` so no glyph keeps the `H` flag.
- Don't hard-code what FontForge derives: OS/2 code pages and Unicode ranges, Win
  ascent/descent, the shipped names and version, `sfntRevision`. `LangName` holds only name IDs
  8–14: maker, designer, description, URLs and license.
- The copyright holders appear in the SFD `Copyright:` field and in `LICENSE.md`, and the SFD
  `Version:` heads `CHANGELOG.md`; `tests/test_metadata.py` keeps each pair in sync.
- SFD diffs are noisy: saves rewrite `ModificationTime` and hints, and deleting a glyph
  renumbers every later index.

## Generated glyphs

Each generator owns a range of glyphs and redraws it in place, so a rerun changes nothing; its
`tests/test_add_<what>.py` fails while the SFD is out of date. Change those glyphs only in the
generator, rerun it, then `./build.sh`. Each generator's docstring has the details.

- `tools/add_ligatures.py`: the ligatures from `src/ligatures.fea` and ⎯; it owns every glyph
  its `GENERATED` pattern matches and every `lig_*` lookup.
- `tools/add_marks.py`: the combining marks, every glyph's mark anchors and the `ccmp`, `mark`
  and `mkmk` lookups (`marks_*`).
- `tools/add_box_drawing.py`: Box Drawing and Block Elements (U+2500–U+259F).
- `tools/add_powerline.py`: the Powerline symbols (U+E0A0–E0A2, U+E0B0–E0B3).
- `tools/add_shapes.py`: the spinner frames (◐ ◜ ◰ ☰ ✷ …, its `CODES`) and their components.

After adding or redrawing any glyph, run `tools/add_marks.py`, then `tools/add_ligatures.py`
last: a new glyph lands after the generated ones, and the last generator to run decides the
lookups' order. Then `tools/make_italic.py`, which rewrites the whole italic SFD from the
regular; `tests/test_make_italic.py` fails while it is out of date. A new glyph slants unless
its block or character is listed as upright there; a picture, such as a shape or a status
mark, goes in the upright set. Then `./build.sh` and `tools/render_specimen.py`:
`tests/test_render_specimen.py` fails while the README's images in `docs/images/` are out of
date.

## Designing glyphs

- Before you place, size or redraw a glyph, compare it with Fira Code, Maple Mono and Intel One
  Mono (`tools/compare_glyphs.py`) and follow what they agree on. Where they differ on how
  distinct a character should be, follow Intel One Mono, which was designed with low-vision
  developers, and keep sizes and positions within the range the three cover. All three are OFL:
  copy measurements, never outlines.
- When the hand-drawn style calls for something else, say why in the commit message.
- Draw new strokes in the font's own hand: round ends, the stem weight (about 90), the wobble.
  Reuse an existing stroke where one fits; move and shorten strokes rather than scaling them.
- Never make a counter narrower than the narrowest reference's, compared at the same letter
  height, and bring no symbol closer to the cell's edges than ● (15), so two side by side
  don't touch.
- Center symmetric ink in the cell; turned glyphs such as ¡ ¿ are references rotated 180°
  about the cell center.
- `docs/design-notes.md` records how the scaled parts, heavy marks, shapes and Greek were
  sized, how the italic was decided, and where the reference fonts live;
  `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths. Read them before changing what they cover.
- The italic's rules are the regular's: its glyphs are the regular's sheared, and its cursive
  letters are built in `tools/make_italic.py` from the regular's strokes, proofed against the
  Maple Mono and Intel One Mono italics (`build/cache/reference/`, from the same releases).

## Writing tests

A test fails when the font is broken, never because a glyph was redrawn on purpose. How a glyph
looks is judged on the proof sheet, not asserted. Only the checks that generated output is
current (a generator's range, the italic, the README's images) fail after a deliberate change,
and only until it is regenerated.

- Put each check where its kind lives: `test_sanity.py` for what breaks text for every glyph
  (the cell, the line box, `validate()`, hints, empty or unused glyphs); `test_consistency.py`
  for what whole classes share (rows, centering, the math axis, mirrored pairs, accented
  letters, no copied outlines); `test_built.py` for what generating the fonts must keep;
  `test_metadata.py` for names and declared metrics; `test_legibility.py`, `test_latin.py`,
  `test_greek.py` and `test_symbols.py` for rules on single glyphs; `test_make_italic.py` for
  how the italic follows the regular. The sanity, metadata, built-font and shaping suites run
  on both styles; the rules on glyphs and classes run on the regular, which the italic is
  derived from.
- Prefer a class rule: add a new glyph to its class in `test_consistency.py` (`ROWS`,
  `CENTERED`, `ON_AXIS`, `MIRRORED`, `MIRRORED_OUTLINES`, the left glyphs of `MIRRORED` that must be their right one
  mirrored exactly) rather than writing a test for it.
- A test for one glyph states a relation any redesign must keep: look-alikes stay apart, a
  counter or gap is at least the narrowest reference's, parts don't touch, a glyph is built from
  another. Never assert a coordinate, width or offset that only records today's design: if the
  only fix for a failure is to edit the number, don't write it.
- Take thresholds from the font (another glyph, `os2_xheight`, the hyphen's middle) or from a
  reference font's floor, and say in a comment where each number comes from.
- A known exception goes in the test's exception list with its reason.
- Before relying on a new check, break a copy of the SFD the way the check guards against and
  watch it fail.

## Other

- Add user-visible changes to `CHANGELOG.md`.
