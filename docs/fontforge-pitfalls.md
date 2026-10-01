# FontForge pitfalls

What FontForge's Python module (Homebrew's FontForge 20251009) does that the tools work
around. Read this before writing code that edits the SFD.

## Glyphs and references

- Assigning `glyph.foreground` drops hint masks; call `glyph.autoHint()` afterwards.
- `glyph.transform()` also shifts `vwidth`; transform `glyph.foreground.dup()` and assign it
  back.
- Assigning `glyph.anchorPoints` or `glyph.references` marks the glyph's hints stale (`H` in
  its `Flags:` line), a composite's too; `glyph.autoHint()` afterwards clears it on both.
- FontForge derives the family, subfamily, full and PostScript names, the style bits and the
  caret slope from `fontname`, `fullname`, `italicangle` and `os2_stylemap`; `tools/make_italic.py`
  sets only those. It writes the italic's caret slope in hundredths (100/21 for 12°).
- Composites keep stale bounds in the process that edited their base glyph; hint them and
  generate from a fresh process. `glyph.unlinkRef()` likewise bakes the base's outline as the
  composite last saw it, not the base's current `foreground`: unlink before editing the base,
  as `tools/make_italic.py` does before it shears anything.
- `glyph.unicode = -1` switches the font to a `Custom` encoding; set
  `font.encoding = "UnicodeBmp"` afterwards. `font.removeGlyph()` keeps the glyph's encoding
  slot; set the encoding again afterwards or re-created glyphs land in new slots.
- Don't save from a process that validated glyphs; it writes `Validated:` into each one it
  checked. `project.save_checked()` validates in a fresh process instead.
- `glyph.references` gives `(name, matrix, selected)` triples; unpack them with
  `name, matrix, *_`. Assigning `(name, matrix)` pairs works, but they are written to the SFD
  in reverse order; assign them reversed to keep the file's order.
- `validate()` flags a mirrored reference (0x10, and 0x8 for its reversed contours) and a
  glyph whose own outline overlaps its reference (0x4). Mirror into an outline with
  `geo.mirrored_x`, and merge a mark that crosses its base into one outline.
- Adding an anchor from Python marks the glyph's hints stale, and so does `autoHint()` on
  every glyph (a few come out different); add anchors through a merged feature file, which
  doesn't. `removeLookup()` leaves the lookup's anchors on the glyphs, and a merge keeps an
  anchor a glyph already has; remove the anchor classes first.
- Where a contour starts can make the autohinter write a `nan` into a stem's range. Reading
  the SFD back drops the stems after it but not the hint masks that count them, and FontForge
  then warns of a "Hint mask … with too many hints" whenever it opens the built OTF, which
  `tests/test_built.py` checks. ☐'s counter does this when it starts where its bottom edge
  ends, and so does any glyph hinted with that outline in it; move such a contour's start with
  `contour.makeFirst()` until the hints come out without `nan`.
- References that overlap, as ☐ and the quarter of ■ in ◰–◳ do, make `validate()` flag the
  glyph (0x4), as ∄'s do; `tests/test_sanity.py` lists them.

## Outlines

- `removeOverlap()` mishandles edges that coincide exactly, and `layer.exclude()` returns the
  wrong region; cut with `layer.intersect()` against a box, and join two outlines along a flat
  edge they share with `geo.weld()` or `geo.weld_y()`, which splice the contours instead.
- `layer.addExtrema()` skips short segments that `validate()` still flags; pass `"all"`. It
  splits the curve at each extremum, so the segment's control points change; compare
  outlines by their on-curve points.
- `layer.boundingBox()` of a curve whose extremum is not a point is loose, reaching to the
  control points; add the extrema first.
- Moving a few points of a contour can leave an extremum that `addExtrema("all")` won't add
  but `validate()` flags (0x20); keep the points next to the moved ones where they are.
- `geo.cleanup()` can move points again on an outline it already cleaned; derive a glyph from
  another's outline as saved in the font, not from the layer before cleanup.
- A polygon built from points, and a path `stroke()` draws, can run counter-clockwise, and
  `removeOverlap()` then takes them for holes; turn them clockwise (`add_shapes.clockwise`)
  before a union.

## Features and lookups

- `font.mergeFeature()` prints feature-file errors to stderr and returns normally, merging
  nothing; check that the lookups exist afterwards. It also drops the first glyph of a class
  range written `[A-Z]`; write `[A - Z]`.
- Saving crashes when an `rsub` rule is made only of bare glyph names; write the input glyph
  as a one-glyph class (`[a]'`).
- A new contextual lookup goes before the others in the SFD, so the last generator to run
  decides their order: run `tools/add_marks.py`, then `tools/add_ligatures.py`.

## Generating and checking fonts

- FontForge 20251009 gives every glyph of a TTF one advance when all but the zero-width ones
  share it, so the marks and the zero-width format characters come out a cell wide;
  `tools/mark_advances.py` rewrites the TTF's `hmtx`, and `tools/generate.py` and `build.sh`
  run it. OTFs are right.
- A font's `head.modified` is the SFD's `ModificationTime` until a glyph changes in the
  process, and then `SOURCE_DATE_EPOCH`, or the time now without it; `tools/generate.py`
  sets the blank space's width to itself so that both formats get the latter. A real setter
  redates the font even when it assigns the value already there, but `glyph.changed = True`
  and `font.changed = True` don't.
- Every font FontForge writes has a Mac Roman cmap subtable, whatever the flags, which
  `tools/generate.py` drops.
- Ignore the Nerd Fonts patcher's "Fontforge 20251009 produces unusable fonts" warning; it
  does not affect this font.
- `tests/test_fontbakery.py` runs Font Bakery's universal profile on each built font and
  expects exactly the problems its `known()` lists, each with its reason; it skips without
  `uvx`. To read a full report, run `uvx fontbakery==1.1.0 check-universal --skip-network` on
  one font at a time: together, the two read as one style twice and fail the family checks.
  Its network checks fail offline and whenever a newer Font Bakery is out, so the test skips
  them too.
