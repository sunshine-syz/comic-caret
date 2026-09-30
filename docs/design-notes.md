# Design notes

How the glyphs are sized and placed, in more detail than the rules in `CLAUDE.md`. The
reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira Code
6.2 release, Maple Mono 7.9 Regular (the Nerd Font build works too) and
`IntelOneMono-Regular.ttf` from the Intel One Mono 1.4.0 release (`ttf.zip`). All three are
OFL: copy measurements, never outlines. `tools/compare_glyphs.py` puts our glyph positions
next to theirs, and `tools/proof_sheet.py` renders ours beside them.

## Scaled parts

New strokes are drawn in the font's own hand: round ends, the stem weight (about 90), the
wobble. Reuse an existing stroke where one fits; move and shorten strokes rather than scaling
them. The exceptions:

- ∞ is 8's loop, scaled to fit; every reference draws ∞ lighter than its letters.
- The `*.small` components of superscripts, subscripts, fractions and signs are the regular
  glyph at 0.45 (figures, ⁱ ⁿ and the signs), 0.52 (the small parentheses, which reach past
  the figures as far as the references' do), 0.55 (ª º) or 0.41 (™ © ®), thickened with
  `changeWeight(…, "CJK", …)` (the default picks a method that pushes all the weight down and
  right) so stems measure 54 ± 4, or 56 in ™ © ®; the fraction and ordinal bars are thinned
  to match.
- ▹ is ▷ at 0.59 thinned to a 41 outline, since at the full stroke its counter fills in at
  16 px. Its white stays 4 short of Maple Mono's, the only reference's, whose outline is 37;
  ▸ ▴ ▵ ▾ ▿ ◂ ◃ follow it.
- ▫ (☐ at 0.52) and ◦ (○ at 0.48) are scaled so their rings come out about 41 too.
- ⧉'s squares are the hyphen's stroke at 0.79, so the one behind keeps clear of the one in
  front; ⏺ ⏵ are ● ▶ scaled to ⏸'s height.
- The keyboard symbols ⌘ ⌥ ⌃ ⇧ ⌫ ⌦ ⎋ ⏎ take the same 0.79 stroke, for their detail, so key
  hints such as ⌃⌥⌘⇧ read at one weight.

## Heavy marks and shapes

- Heavy marks (✔ ✘ ✖ ❯ ➜) are their light glyph (✓ ✗ ✕ > →) pushed out 23 on every side,
  then squeezed at the ends to stay 20 inside the cell; ❰ ❱ are two hyphen strokes pushed out
  the same, and ⏸'s bars are `|` pushed out 40, to weigh as much as ⏵ ⏺.
- No symbol comes closer to the cell's edges than ● (15), so two side by side don't touch;
  `tests/test_symbols.py` lists the exceptions.
- Black shapes (● ◆ ▶ ▸ ★ ■ ▪) are their white shape's outer contour; the white shapes are
  rings of the hyphen's stroke, or of `o`'s for ○.
- The spinner frames are cut, stacked and turned from ○ ● ☐ ■ ◦ ✶ `*` and `!`, so the frames
  of one spinner share a center and size; `tools/add_shapes.py` says how each is made.

## Counters and shared cells

- Never make a counter narrower than the narrowest reference's, compared at the same letter
  height.
- Where three strokes share the cell (φ Φ ψ Ψ), the middle one takes the bar's weight (78),
  and the sides reach as far out as `w`'s, to keep up with the references' lighter strokes.

## Greek

Greek follows Fira Code and Maple Mono (Intel One Mono has none). Capitals that match Latin
are references to it; the tonos is the acute turned 25° steeper, and beside a capital it
stands to the left, reaching into the cell before (all but Ά) no further than the references'
112 (`tests/test_sanity.py` lists them).

## Placement

- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths; read it before changing them.
- Box-drawing strokes overlap their neighbours: verticals span −485…1035 (they meet up to
  1.5 em line height), horizontals −10…560. Block elements fill the cell and the line box
  exactly, and the Powerline separators do the same.
