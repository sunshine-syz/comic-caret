# CLAUDE.md

Comic Caret is a monospaced font (MIT) in Regular, Italic and Bold, derived from Comic Shanns
Mono. The whole font is `src/ComicCaret-Regular.sfd`. The italic, `src/ComicCaret-Italic.sfd`,
and the bold, `src/ComicCaret-Bold.sfd`, are generated from it by `tools/make_italic.py` and
`tools/make_bold.py` and never edited by hand. `fonts/`, `build/` and `dist/` hold gitignored
build outputs. Font files are never committed; they ship as GitHub release assets.

## Commands

Needs Homebrew `fontforge` (its module imports from `python3`), HarfBuzz and `uvx`.

```sh
./build.sh                              # SFDs -> fonts/ComicCaret-{Regular,Italic,Bold}.{otf,ttf}
./build.sh --nerd                       # also Nerd Fonts patched copies in build/nerd/
./build.sh --release                    # fonts + default Nerd Font, zipped into dist/; clean checkout
python3 tools/add_<what>.py             # regenerate a generated range in the SFD (see below)
python3 tools/make_bold.py              # regenerate the bold SFD from the regular (see below)
python3 tools/make_italic.py            # regenerate the italic SFD from the regular (see below)
python3 tools/proof_sheet.py OUTDIR     # review sheet: ours next to the reference fonts
python3 tools/compare_glyphs.py 'TEXT'  # our glyph positions next to the reference fonts
tools/render_sample.sh OUTDIR           # ligature sample images, calt on and off
python3 tools/render_specimen.py        # the README's images in docs/images/ (committed)
python3 tools/bump_version.py X.Y       # start the next version: every SFD's Version: and CHANGELOG head
```

`proof_sheet.py` takes `--text=TEXT` (repeatable) and `--features` to proof other glyphs,
`--italic` or `--bold` to proof that style against its references, `--before REV` to add the
font built from that commit's SFD, and `--line-height EM` to check that box drawing meets
across lines.

After every change to the regular, rerun `tools/make_bold.py` and `tools/make_italic.py`,
rebuild, rerun `tools/render_specimen.py`, then run the checks:

```sh
python3 -m unittest discover tests  # SFD rules, built fonts, shaping, ots, Font Bakery, README images
hb-shape fonts/ComicCaret-Regular.ttf --text='->'            # --text: a leading '-' reads as an option
```

## Releasing

Versions are X.Y; releases up to 2.0.1 were X.Y.Z. The version being worked on heads
`CHANGELOG.md` as "unreleased"; `tools/bump_version.py X.Y` starts the next one, setting every
SFD's `Version:` and the heading together. The fonts carry it as the decimal X.Y00
(`tools/generate.py`; 2.1 ships as 2.100, above 2.0.1's 2.001), so Y stays below 10.

1. `python3 tools/bump_version.py --release` gives the heading this month.
2. Commit, run `./build.sh --release`, then the checks above; the tests also check the Nerd
   Fonts builds it made, which they skip otherwise.
3. `python3 tools/bump_version.py --check-tag vX.Y` refuses a tag that isn't that release.
   Tag the commit and attach both zips from `dist/` to a GitHub release.

## The SFD

- Every glyph is drawn in the regular. The italic and bold SFDs are its output:
  `tools/make_italic.py` slants the text glyphs, keeps the graphics upright and draws the
  cursive letters from the regular's strokes, and `tools/make_bold.py` grows the strokes by an
  elliptical pen and keeps the pictures as the regular draws them. Change the regular or the
  generators, never the italic or the bold, and rerun them.
- Edit only through FontForge (GUI or `import fontforge`). `Refer:` lines address glyphs by
  index, so hand edits silently break composites. Before writing FontForge Python, read
  `docs/fontforge-pitfalls.md`: the module's quirks the tools work around.
- Every glyph, `.notdef` included, is 600 wide, except the combining marks (U+0300…), which
  are 0 wide with their ink over the cell, where terminals that don't shape text draw them,
  and the blank zero-width format characters (`project.ZERO_WIDTH`).
- Metrics: em 1000, cap height 668 and x-height 473 (the tops of `H` and `x`; the bold's are
  675 and 480), hhea = typo = win = 900/−350 (1.25 em) with `USE_TYPO_METRICS`; the win
  ascent and descent are set, not offsets from the ink, so GDI apps space lines alike.
- Build accented and derived glyphs from references to base glyphs, not copied outlines.
- Give new or changed glyphs integer coordinates and a clean `validate()` (validate again after
  `glyph.round()`), then run `glyph.autoHint()` so no glyph keeps the `H` flag.
- The OTF carries the SFD's hints; `tools/generate.py` hints letter composites again and adds
  a ghost hint where a letter's top or foot lies in a zone without a hint edge. The TTF gets
  ttfautohint's, which replace any TrueType instructions the SFD holds, so the SFD holds none.
- Don't hard-code what FontForge derives: OS/2 code pages and Unicode ranges, the shipped
  names and version, `sfntRevision`. `LangName` holds only name IDs 8–14: maker, designer,
  description, URLs and license.
- The copyright holders appear in the SFD `Copyright:` field and in `LICENSE.md`, and the SFD
  `Version:` heads `CHANGELOG.md`; `tests/test_metadata.py` keeps each pair in sync.
- SFD diffs are noisy: saves rewrite `ModificationTime` and hints, and deleting a glyph
  renumbers every later index.

## Generated glyphs

Each generator owns a range of glyphs and redraws it in place, so a rerun changes nothing; a
rerun test (`tests/test_add_<what>.py`; `test_add_marks.py` holds `add_ligatures`' too, as the
two must run in order) fails while the SFD is out of date. Change those glyphs only in the
generator, rerun it, then `./build.sh`. Each generator's docstring has the details. A new
generator's rerun test compares with `tests/sfd_files.differences()`; see
`docs/fontforge-pitfalls.md`.

- `tools/add_ligatures.py`: the ligatures from `src/ligatures.fea` and ⎯; it owns every glyph
  its `GENERATED` pattern matches and every `lig_*` lookup.
- `tools/add_marks.py`: the combining marks, every glyph's mark anchors and the `ccmp`, `mark`
  and `mkmk` lookups (`marks_*`).
- `tools/add_box_drawing.py`: Box Drawing and Block Elements (U+2500–U+259F).
- `tools/add_powerline.py`: the Powerline symbols (U+E0A0–E0A2, U+E0B0–E0B3).
- `tools/add_shapes.py`: the spinner frames (◐ ◜ ◰ ☰ ✷ …, its `CODES`) and their components.

After adding or redrawing any glyph, run `tools/add_marks.py`, then `tools/add_ligatures.py`
last: a new glyph lands after the generated ones, and the last generator to run decides the
lookups' order. Then `tools/make_bold.py` and `tools/make_italic.py`, which rewrite the whole
bold and italic SFDs from the regular; `tests/test_make_bold.py` and
`tests/test_make_italic.py` fail while they are out of date. A new glyph grows in the bold
unless its block or character is listed as shared in `make_bold.py`; a picture that meets its
neighbours across the cell, fills the line box or is a spinner frame goes in the shared set.
It slants in the italic unless it is listed as upright in `make_italic.py`; a picture, such as
a shape or a status mark, goes in the upright set. Then `./build.sh` and
`tools/render_specimen.py`: `tests/test_render_specimen.py` fails while the README's images in
`docs/images/` are out of date.

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
  height, and bring no symbol closer to the cell's edges than `project.SYMBOL_SIDE` (15), so
  two side by side don't touch.
- Center symmetric ink in the cell; turned glyphs such as ¡ ¿ are references rotated 180°
  about the cell center.
- `docs/design-notes.md` records how the scaled parts, heavy marks, shapes and Greek were
  sized, how the italic and the bold were decided, and where the reference fonts live;
  `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths. Read them before changing what they cover.
- The italic's rules are the regular's: its glyphs are the regular's sheared, and its cursive
  letters are built in `tools/make_italic.py` from the regular's strokes, proofed against the
  Maple Mono and Intel One Mono italics (`build/cache/reference/italic/`, from the same
  releases; `--italic` on `proof_sheet.py` and `compare_glyphs.py` uses them).
- The bold's rules are the regular's too, and its glyphs are held to them: its strokes are
  the regular's grown by `tools/make_bold.py`'s pen, proofed against the Fira Code, Intel One
  Mono, Maple Mono and Monaspace bolds (`build/cache/reference/bold/`; `--bold` on
  `proof_sheet.py` and `compare_glyphs.py` uses them). Where the pen grows two parts together
  or a glyph past its side room, fix it in `make_bold.py`.

## Writing tests

A test fails when the font is broken, never because a glyph was redrawn on purpose. How a glyph
looks is judged on the proof sheet, not asserted. Only the checks that generated output is
current (a generator's range, the italic, the bold, the README's images) fail after a
deliberate change, and only until it is regenerated.

- Put each check where its kind lives: `test_sanity.py` for what breaks text for every glyph
  (the cell, the line box, `validate()`, hints, empty or unused glyphs); `test_consistency.py`
  for what whole classes share (rows, centering, the math axis, mirrored pairs, accented
  letters, no copied outlines); `test_built.py` for what generating the fonts must keep;
  `test_metadata.py` for names and declared metrics; `test_legibility.py`, `test_latin.py`,
  `test_greek.py` and `test_symbols.py` for rules on single glyphs; `test_make_italic.py` and
  `test_make_bold.py` for how the italic and the bold follow the regular. The sanity,
  metadata, built-font and shaping suites run on all three styles. The rules on glyphs and
  classes run on the regular and, through their `Bold` subclasses, on the bold; the italic
  follows the regular through `test_make_italic.py`.
- A new rule class on glyphs the bold grows gets a `Bold` subclass (`sfd = BOLD_SFD`). Where
  the bold needs its own threshold, take it from a reference bold or from the pen, and set it
  on that subclass.
- Prefer a class rule: add a new glyph to its class in `test_consistency.py` (`ROWS`,
  `CENTERED`, `ON_AXIS`, `MIRRORED`, or `MIRRORED_OUTLINES` for the left glyphs of `MIRRORED`
  drawn as exact mirrors of their right) rather than writing a test for it.
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
- Shared helpers have one home: font-wide constants and code-point classes in `tools/project.py`
  (the line box, `AXIS`, `ROUNDING`, `WOBBLE`, `is_letter()`), font-table reading and writing in
  `tools/sfnt.py`, outline measurements in `tools/measure.py`, the outline builders the
  generators share (`polygon`, `stroked`, `clip`, ...) in `tools/lig_geometry.py`, and test-only
  helpers in `tests/helpers.py`. A generator never borrows another generator's helpers (a
  constant such as a stroke weight is fine), and a test module never imports from another test
  module.
