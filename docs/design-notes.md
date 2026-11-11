# Design notes

How the glyphs are sized and placed, in more detail than the rules in `CLAUDE.md`. The
reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira Code
6.2 release, Maple Mono 7.9 Regular (the Nerd Font build works too) and
`IntelOneMono-Regular.ttf` from the Intel One Mono 1.4.0 release (`ttf.zip`). All three are
OFL: copy measurements, never outlines. `tools/compare_glyphs.py` puts our glyph positions
next to theirs, and `tools/proof_sheet.py` renders ours beside them. With `--italic`, both use
the italic references in `build/cache/reference/italic/`. With `--bold`, both use the bold
references in `build/cache/reference/bold/`: `FiraCode-Bold.ttf` (Fira Code 6.2),
`IntelOneMono-Bold.ttf` (Intel One Mono 1.4.0, `ttf.zip`), `MapleMono-NF-Bold.ttf` (Maple Mono 7.9,
the Nerd Font build) and `MonaspaceNeon-Bold.otf` and `MonaspaceRadon-Bold.otf` (Monaspace 1.400,
`monaspace-static-v1.400.zip`).

## Scaled parts

New strokes are drawn in the font's own hand: round ends, the stem weight (about 90), the
wobble. Reuse an existing stroke where one fits; move and shorten strokes rather than scaling
them. The exceptions:

- ∞ is 8's loop, scaled to fit, then its top and bottom strokes moved apart so its holes are
  as tall as Maple Mono's at our cap height; every reference draws ∞ lighter than its letters.
- The `*.small` components of superscripts, subscripts, fractions and signs are the regular
  glyph scaled: 0.45 for the figures, ⁱ ⁿ and the signs, 0.52 for the small parentheses, which
  reach past the figures as far as the references' do, 0.55 for ª º and 0.41 for ™ © ®.
  `changeWeight(…, "CJK", …)` thickens them until stems measure 54 ± 4, or 56 in ™ © ®; the
  default picks a method that pushes all the weight down and right. The fraction and ordinal
  bars are thinned to match.
- ▹ is a 41 outline, lighter than ▷'s, since at the full stroke its counter fills in at
  16 px; ▸ ▴ ▵ ▾ ▿ ◂ ◃ follow it. It is 310 wide, Maple Mono's, the only reference's, and the
  white across its middle, 199, stays above Maple Mono's, whose lighter 37 outline leaves 159
  at our cap height. ‣, a text bullet beside •, is ▸'s triangle 278 wide, near Maple Mono's
  ‣ (258).
- ▫ and ◦ are ☐'s and ○'s shapes, 250 across, scaled so their rings come out light too: 41
  and 46.
- ⧉'s squares are the hyphen's stroke at 0.79, so the one behind keeps clear of the one in
  front; ⏺ ⏵ ⏹ are ● ▶ ■ scaled to ⏸'s height.
- ◻ ◼ are ☐ ■ at 0.75, 376 across: midway between ▫ ▪ (250) and □ ■ (502). No reference
  has them; Iosevka's medium squares stand midway too, and Menlo's a little over. ◈ is ◇ with
  ◆ at 0.38 inside, 49 clear of the ring: over twice `SYMBOL_SIDE`, under ◉'s 70, as ◇'s ring
  leaves less room than ○'s (Maple Mono's ◈, the only reference's, keeps 64 in a lighter
  ring).
- ↯ is a bolt in ↓'s stroke that runs into ↓'s own shaft and head, so it stands and weighs as
  the arrows beside it do. No reference has it.
- The keyboard symbols ⌘ ⌥ ⌃ ⇧ ⌫ ⌦ ⎋ ⏎ take the same 0.79 stroke, for their detail, so key
  hints such as ⌃⌥⌘⇧ read at one weight.

## Heavy marks and shapes

- Heavy marks (✔ ✘ ✖) are their light glyph (✓ ✗ ✕) pushed out 23 on every side,
  then squeezed at the ends to at most 510 wide; ✗'s and ✘'s arms then run out to Maple
  Mono's 538 and 550, turning flatter and keeping their weight. ⏸'s bars are `|` pushed out
  40, to weigh as much as ⏵ ⏺.
- ❯ ❮ are not a heavy `>`. They are the tall angle ornament, as every coding font that has
  them draws it (JetBrains Mono, Cascadia Code, Maple Mono, DejaVu Sans Mono, Menlo, Iosevka):
  `>` with its arms lengthened, each turned 25° steeper and pushed out 23. It stands on the
  baseline, as tall as the capitals. The arms turn about the centre of the point's round end,
  since turned about the tip it splits into two bumps, and each arm takes its own length, as
  the hand-drawn arms differ, so the point stays at mid-height. ❯ is 0.78 as wide as `>` and
  carries 1.43 times its ink, between Cascadia Code's 1.39 and Maple Mono's 1.46.
- ❰ ❱ are built the same way, turned 15° and pushed out 50: as tall as ❯, 1.36 times as wide
  and 1.46 times its ink, so Rich's traceback marker stays apart from the prompt, as in the
  fonts that draw them apart (DejaVu Sans Mono's ❱ 1.39 times its ❯'s ink, JetBrains Mono's
  and Maple Mono's 1.50).
- No symbol comes closer to the cell's edges than `project.SYMBOL_SIDE` (15), so two side by
  side don't touch. Letters and figures may, the fractions among them (¼ stands 12 from each
  edge).
- Black shapes (● ◆ ▶ ▸ ★ ■ ▪) are their white shape's outer contour; the white shapes are
  rings of the hyphen's stroke, or of `o`'s for ○.
- The spinner frames are cut, stacked and turned from ○ ● ☐ ■ ◦ ✶ `*` and `!`, so the frames
  of one spinner share a center and size; `tools/add_shapes.py` says how each is made.

## Counters and shared cells

- Never make a counter narrower than the narrowest reference's, compared at the same letter
  height.
- Where three strokes share the cell (φ Φ ψ Ψ), the middle one takes the bar's weight (78),
  and the sides reach as far out as `w`'s, to keep up with the references' lighter strokes.

## Latin

- **`f`** has no foot. Comic Shanns Mono drew a bar 425 wide under it; Fira Code, Intel One
  Mono and Maple Mono draw none, and the user chose the plain stem on proof (2026-11-10) over
  a short serif, a descender and the same letter 25 further right. The stem ends round at
  −20, where `h` `n` `r` `t` end, and stays 50 left of the cell's middle (the references'
  stand 32–40 left): moved 25 right, `fn` closed to 159 and `fl` to 123, and `if` came 132
  wider than `fi` (the references: 60–76). The crossbar is 7 longer to the left, since it and
  the hook now set the width, at Fira Code's 460.
- **`S`**'s top end hangs down, to set it apart from `5`. Its top arm ran level and ended
  in a cut: its lowest ink lay 0.13 of the cap height under the top,
  where `5`'s bar ends (0.13), and the user read the two as alike. Every font compared hangs
  `S`'s end lower than `5`'s bar: Intel One Mono 0.16 against 0.11, Fira Code 0.20 against
  0.10, Maple Mono 0.26 against 0.12 (Menlo and SF Mono too). The arm's end is now a stroke
  of the bottom arm's weight (79; the arm was 74–79) that bends down from under `S`'s highest
  point and ends round 0.25 under the top; the user picked it on proof (2026-11-10) over
  0.18. The opening under the end is 0.259, just over Maple Mono's 0.256, the narrowest; the
  bold's is 0.216 (Maple Mono Bold 0.204). `5` keeps its round corner, as `E` and `F` have,
  where Fira Code and Intel One Mono draw a square one. `$` is its own outline and keeps its
  level end.
- **`5`**'s ends are tidied (2026-11-10, picked on proof over round ends alone). Its bar
  ended in a cut, a flat underside and a corner, and now ends in a round cap; the bar's left
  end stood 10 left of the stem as a bump, and the stem now runs straight up into the round
  corner `E` and `F` have; the bottom end, an outline of small bumps, is one curve that tops
  out at 94, under the 100 that keeps the bowl open. Text sizes show no difference. The small
  5 of `⁵` `₅` and the fractions is its own outline and keeps its ends.
- **`§`** is two hooks, the lower one turned (2026-11-10, picked on proof). Each is an end, a
  bowl, a level spine across the cell and the far side of the middle counter, and ends inside
  the other's spine. Comic Shanns Mono drew it as two copies of `s`, whose bowls overlapped:
  the largest circle in the middle counter was 64 across (Fira Code 145, Maple Mono 198, Intel
  One Mono 246) and the stroke doubled to 168 there, so § read as a knot at every size. The
  counter now holds a circle of 162 (bold 144; Monaspace Neon Bold 108, the narrowest). It
  stands −140…700, 840 tall, 1.19 of `S`'s height as Maple Mono's (Fira Code 1.08, Intel One
  Mono 1.33), and its stroke is 80, 0.97 of `S`'s (the references' 0.90–0.97). The picked
  form has level spines and a round counter, after `S` and `8`, over slanted spines at 800 and
  at 840 tall.
- **`a`** is double-storey, after a hand-drawn reference, so it reads apart from `o` and `α`
  at 12 px; the single-storey one blurred into `o` there. Its head rises nearly straight from
  a terminal at 0.87 of the x-height to a tight shoulder, the stem leans out as the old one
  did, and the bowl, a flat oval, leaves the stem at mid-height and rises back into it above
  the baseline. The bowl's top is at 0.59 of the x-height, Fira Code's and Intel One Mono's
  0.60, and its counter 0.33 tall (Intel One Mono 0.31, Fira Code 0.39). It is drawn on two
  centrelines with an elliptical pen 95 wide and 76 tall, `o`'s sides and top. Its top stays
  at 486, the old `a`'s. `æ`'s a half is the same centrelines
  at 0.62 across with the old `æ`'s pen (72 × 80), and `ª`'s small a is `a` at 0.55.
- **Accents.** The marks were redrawn in 2.5 for 11–16 px. Until then the acute (153 × 128)
  was as wide as `i`'s dot and read as one, and every mark sat 40–60 above its letter, where
  the references keep at least 72 over é and 85 over ä.
  - The acute and grave run along their own 34° slant, 240 × 187, Intel One Mono's width
    (246); the acute is 1.59 times the dot's width, over Intel One Mono's 1.45, the widest of
    the references' (Fira Code 1.34, Maple Mono 0.97). The circumflex and caron run both arms
    along their slants to 345 wide (the references' 312–362).
  - Each mark stands over the lowercase letters where its white to each letter reaches the
    narrowest reference's (`MARK_FLOORS`, `tests/test_legibility.py`). For that, 2.5 raised
    the acute and grave 40, the dieresis 43, the dot above 40, the tilde 35, the circumflex 30,
    the caron and breve 28, the ring 19, the macron 58 and the double acute 39. ý's diagonal
    white sets the acute's; the grave stands as high, so è é match.
  - Capitals take the same marks, which fit under the 1000 line top (Á 908, Ö 863), at their
    floors too: 2.5 raised Ê 13, Š 9, Ö 25 and Ā 28. ĥ and ĺ stand their marks over the
    ascender, 81 and 93 above it (the references' floors: 63 and 72).
  - Greek's marks rise to Fira Code's and Maple Mono's floors. Over the lowercase the tonos
    rises 43, ώ's diagonal white setting it, and the dieresis of ϊ ϋ 7 more than Latin's. ΐ ΰ
    raise their ΅ 50, so their dieresis stands level with ϊ ϋ's.
  - The dots stay 152: `.` `·` `∙` `:` and `i`'s dot are one glyph, and at 152 `i`'s dot is
    within the references' (129–156). A period at Maple Mono's 170 would make it wider than
    every reference's `i` dot, and nearer the acute. The acute grows apart from it instead.
- **˚.** 196 across, with a 42 stroke, so its counter is 112 across (Fira Code's 108 at its
  middle). The old ring, 161 wide, kept a counter of 41 × 51, which closed into a dot at
  12 px. å ů Å Ů and U+030A take the same ring; Å tops at 897.
- **ł Ł.** Their bars pass the stem as far as the references' do, so ł doesn't read as l at
  12 px: ł's reaches 111 left and 129 right (Fira Code 105 and 124), Ł's 108 and 173 (the
  references' right: 170–221). The ends move out along the bar's slant, so the bar keeps its
  weight and round ends. Ł is 526 wide, within `WIDTHS`.
- **‹ › « ».** › is `>`'s own arms turned 15.8° steeper about the tip and shortened to ›'s
  height, its point redrawn round, as the arrow heads are: 250 wide (the references' 223–307).
  ‹ is › mirrored. Comic Shanns' own ‹ ›, 5° steeper, had arms 69–96 across where `<`'s are
  77–88. « » place two of them 240 apart, so their white is 90 (Fira Code 80) and the bold's 62
  (Fira Code Bold 54).
  With Comic Shanns' flatter arms, moving the two apart grows the white by only 0.6 of the
  move, and it reaches 80 only 7 from the bold cell's edge. Intel One Mono draws its « chevrons
  narrower than its ‹ too.
- **Ấ ấ Ầ ầ Ế ế Ề ề Ố ố Ồ ồ.** The acute or grave stands at the circumflex's upper right,
  its right end `SYMBOL_SIDE` (15) from the cell's edge, lowered until `MARK_CLEARANCE` (20)
  stands between it and the circumflex: Ấ tops at 1061, ấ 891, Ầ 972, ầ 803 (Intel One Mono
  1029 and 866, Maple Mono 1020 and 900). Centred over the circumflex, Ấ would top at 1160.
  In the italic the acute leans 109–147 past the cell, within the reference italics' 75–226
  (Intel One Mono 127–173). A mark typed after a stack centres on its letter, as after â.
  HarfBuzz composes a typed A ◌̂ ◌́ into U+1EA4, so the precomposed letters reach typed text too. A
  combined mark for ◌̂ ◌́, as the references also draw for other bases, would not: the shaper
  composes Â first and centres the acute over it. The hook above, the dot below and the horn are not
  drawn, so the rest of Vietnamese comes from a fallback font.

## Greek

Greek follows Fira Code and Maple Mono (Intel One Mono has none). Capitals that match Latin
are references to it; the tonos is the acute's stroke turned 25° steeper, and shorter than
the acute, which grew along its slant for small sizes. Beside a capital it
stands to the left, reaching into the cell before (all but Ά) no further than the references'
122 (`tests/test_sanity.py` lists them).

Greek's heights are Latin's, so the autohinter puts both on one pixel row. FreeType's light
mode and ttfautohint's TTF hints give each script its own zones, from its own letters: a
zone's flat height is the middle of its flat tops, its round height the middle of its round
ones, and FreeType scales each script so its round x-height lands on a pixel. Greek's come
from ΓΒΕΖΘΟΩ and αειοπστω, Latin's from THEZOCQS and uvxzoesc. So `ι` `τ` stand at `x`'s 473,
`π` at `v`'s 471, `α` at `s`'s 485, and `Γ` `Ω` at `O`'s 671. Until 2.5 they stood at 459,
456, 480, 479 and 668, and every Greek capital stood a row over `H` at 18–19 px. `Γ`'s bar
rises to its stem's top, so `Γ` reads flat in both styles. With a lower bar, `Β`'s level
top, 671, was the bold Greek's only flat one, and the capitals stood a row under `H` at 8 and
24 px.
Greek's feet follow Latin's the same way. Latin's capitals take their baseline zone's flat
height from `E` `Z` `L` (−14), so `Δ` `Ξ` reach `Z`'s −8: at −2 they set Greek's zone, and
the round capitals stood a row low at 24 px. Latin's small letters take theirs from `z`'s bar
(−8). Greek's small letters had no level foot, so the zone fell to their round feet's −25 and
they stood a row low from 20 px (16 in the bold). `π`'s hook bottom is drawn at −8, and in the TTF
`tools/generate.py` (`level_foot()`) cuts each curve that leaves it within 5 units at 5 and 7
units up, joined by a line: the left one in the regular and italic, both in the bold. The
autohinter reads a foot as level when the points within 5 units of it begin and end on the
curve. In the OTF, whose zones all letters share, the feet of `Σ` `Ω` `Φ` `Ψ` reach −8 and
the tops of `ξ` `δ` stand at `d`'s 719: feet at 1 lay over the baseline zone, and tops at 723
and 722 over the ascender zone. `GreekRowTest` in `tests/test_built.py` checks the
tops, the ascenders and the feet at 8–24 px, in the TTF and the OTF.

## Placement

- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths; read it before changing them.
- Box-drawing strokes overlap their neighbours: verticals span −435…1085 (they meet up to
  1.5 em line height), horizontals −20…620, as in Intel One Mono and Maple Mono (Fira Code's
  run 5). The ligatures' lines run 10 into each neighbour, as Fira Code's and Maple Mono's do.
  With 10, on a grid that rounds the cell up to whole pixels, ─ showed a light notch at every
  seam at 11, 16 and 21 px; with 36 the seams turn dark. ╱ ╲ ╳ run on as far as ─, so they
  reach 148 past the line box: the font's furthest ink. The win ascent and descent are the
  line box, as in Fira Code, JetBrains Mono, Intel One Mono and Maple Mono, so GDI apps space
  lines 1.35 em apart and clip the overlap; set to that ink (1148/498), they would space lines
  1.65 em apart. GDI apps clip the upper of two marks stacked on a capital too: Ấ reaches 1061,
  and Ǜ, which HarfBuzz builds from Ü and a grave, 1139 (the bold's 1114 and 1160). Fira Code
  and Maple Mono clip the same way: their win ascent is their line box as well, and their own
  stacked marks reach 61 and 127 units past it. The Nerd Fonts builds take the same values.
- Only a letter's marks may pass the line box, as in Fira Code (57 letters, up to 112 past
  its top), Intel One Mono (up to 12) and Monaspace Neon (up to 262, with a line gap behind
  it); Maple Mono keeps everything inside. Of the letters drawn, only Ấ Ế Ố pass it
  (1059–1065, the bold's 1113–1116), and in the bold Ầ Ề Ồ (1025–1031) and ĺ (1008) too.
  Nothing hangs below it.
  The letter itself stays inside, and so does every other glyph but those that join their
  neighbours (`test_only_marks_rise_above_the_line` and `test_only_marks_hang_below_the_line`
  in `tests/test_sanity.py`). The line top is 1000 (1.35 em rows) for the marks' sake: a top
  at 900 needs flattened marks on capitals and pushes the bold's marks down onto their
  letters.
- A dashed column puts half a dash at the line box's top and bottom and runs it on into the
  overlap, so lines 1.35 em apart keep the rhythm and lines 1.5 em apart meet in one longer
  dash; Intel One Mono and Maple Mono keep their dashes inside the line box, so at 1.5 em a
  long gap marks each seam. Picked by proof 2026-10-06. Lines closer than 1.35 em lose the
  rhythm. At 1.25 em the seam's dash is 100 short in ╎ ╏ ┆ ┇, and in ┊ ┋ the gaps beside it
  close from 46 to 7, so their seam reads as one dash about three long. At 1.2 em ┊ ┋'s seam
  is one dash 816 long, and ┆ ┇'s gaps beside it close to 24. A dashed row takes half a gap at each
  side, as in the references.
- `⎯` (U+23AF) is the `--` line's middle piece and runs `OVERLAP` into each neighbour, as the
  line's pieces do, so a row of them joins as one line, as Vitest's dividers need; a single one
  beside text touches its neighbour's cell. Its seams keep the line's faint notch at 11, 16 and
  21 px. None of the references has it. Picked by proof 2026-10-06 over drawing it within the
  cell, where a row's seams showed lighter still, and over keeping it 15 from each edge, where
  a row turned dashed.
- Ink that fills the cell runs `CELL_REACH` (36) into the next cell, as far as the Nerd Fonts
  patcher's round separators, so a grid that rounds the cell or the line to whole pixels
  leaves no light row or column: each edge of a block element on the cell's side or the line
  box, and the flat side of a solid Powerline separator. Fira Code and Maple Mono keep blocks
  exact, and their stacked blocks show those lines; Monaspace overlaps 5 units. A block beside
  an empty cell paints a sliver of 0.036 em into it, 0.6 px at 16 px. The shades stay within
  the cell, so their pattern tiles; so do the thin separators, which part two segments of one
  colour and leave no seam to cover.
- Braille's dots stand on an even grid: columns every half cell, rows every quarter of the
  line box, so a graph's dots stand as far apart across cells and lines as inside one. Graphs
  in btop, Rich and UnicodePlots come first; Braille text reads looser than in Maple Mono,
  whose dots stand 1.5 times closer inside a cell across and 3.2 times down.
- `|` stands on the cell's middle, on │'s line, so a table drawn with both meets; ‖ is two `|`,
  and ¦ is `|` broken: each piece is `|`'s stroke, shortened, with its round ends.
- `( [ {` span −145…800, 945 tall, within the references' 927–971. The descenders hang 133
  below them (`p` `y` −278), where the references leave 17–85, because ours keep Comic
  Shanns' depth (the references' reach −172…−244). The brackets stay: lengthened to the
  descenders, they would stand taller than every reference's and drag `⟨ ⟩` and `/ \` with
  them.
- `<` `>` are drawn with a stroke of 84, between the letters' stems (88) and `-` `=` `+`
  (75–80); they were 95, heavier than any letter and 27% over `=`, where Fira Code and Intel
  One Mono draw them at their operators' weight (77 against 74, 70 against 72). The user chose
  84 on proof (2026-11-10) over 88. Each point of the outline moved 6 inward along its normal,
  so the hand's points stay: an inset by FontForge's stroker redrew the arms' round ends, and
  under ttfautohint the `<` pieces' bars then left `-`'s pixel rows at ten sizes. The point
  stays at 513 and the arms are 12 longer, so the width stays Fira Code's 425: the points left
  of x = 300 moved left. Two points of the outer edge lie just right of that line, and each
  handle beside them keeps its offset from its point, so the edge stays smooth there (a
  handle moved alone turned it 12–14°, a bump on every arrow head). The arrow ligatures'
  heads, built from `>`, follow; in the bold `->>` the inner head's lower arm now meets the
  shaft a little inside the seam, where the shaft's edge runs on level. The lighter arms meet
  inside the point at 429, where the heavier met at 413, so a wave arrow's wave ends at 432
  (`WAVE_END`), past that: at 411 the end of a trough a little off the lower arm's middle
  showed beside it, a flat of 10 and a barb.
  The arrows follow, so `→` beside `->` stays one arrow: `→ ⇒` are their ligature heads again,
  moved 61 to the arrow's point and welded to the arrow's own shaft end, and `← ⇐` are those
  mirrored. That shaft end, and those of `↑ ⇑ ⇞`, were narrower round ends below shafts that ran
  on past their start, which left square tabs 3–10 units at the shoulders. They are now the
  start pieces of `-` and `=` the ligatures use (`stroke()`), as `-->` begins, turned upright
  for `↑ ⇑ ⇞`, each bar laid on the arrow's bar and welded 100 from the cell's side (56 under
  `⇞`'s lower crossbar); in `↑ ↔ ↕ ⇑ ⇞ ⇡ ↯` the points of every stroke heavier than 84 moved inward by half
  the excess, and the head's points then back out to the old box, so each arrow keeps its
  place and length (96 to 84 in `↑`). `↓` is `↑` turned, as before, and `⇟` is now a reference
  to `⇞` turned, as `⇣` is to `⇡`: as an outline its bold came out with a doubled segment a
  unit long. `⇥ ↦` carried `>` drawn small, its stroke shrunk with it to 67. Their heads are
  now `>`'s arms at its own stroke, turned 10–11° steeper about the point and shortened until
  the head fills the old one's box, as `add_ligatures.longer_angle()` turns and lengthens them
  for `->`, their straight part and point redrawn smooth as the ligatures' are (see the
  ligatures below). The arms lose about 220 of their straight units, so `ARM_STRAIGHT` starts
  at 140, just past the halves' reach over the axis. The glyph's own shaft, with its round cap
  or bar, runs level from where it is about 84 across into the head's point. `⇤` is `⇥`
  mirrored.
- `/` and `\` reach from −110 to 765: 875 tall, within the references' 867–885, and centred on
  the brackets' middle. Each turned 1.5° steeper about its middle and lengthened along its
  stroke, so it keeps its weight; it spans 503, within Maple Mono's 418 and Intel One Mono's
  520. `//` `/*` keep their pitch through `TIGHT_KEEP` (−41.5), and the `!=` slash, the `/` at
  83 %, stands 726 tall, between Maple Mono's 662 and Fira Code's 786.
- ∄ is ∃ and the `/` turned 6° steeper, so it is no wider than ∃, as Fira Code's and Maple
  Mono's are: both are 437 (Maple Mono's ∄ is 420). Its foot stays at Fira Code's −121. A turned
  part can't stay a reference under the italic's shear or the bold's pen, so the italic draws ∄'s
  two parts as outlines and the bold merges them (`make_bold.MERGED`).
- `‘` is `’` mirrored about the cell's middle, so the two lean toward the quoted word; `“` is
  `”` mirrored and ʻ is `‘`. Every reference draws a 6 and a 9, but `’` keeps no head, and a
  headless stroke turned 180° is itself. A 6 drawn from ģ's turned comma leaned like `’`, so
  GCC's `‘foo’` showed two opening marks. The mirrored `‘` leans like the backtick but stands
  134 lower (426…683 against 560…808).

## Wider cell

2.0 moved every glyph from a 550 cell into a 600 cell, at the same letter height: x-height
473, cap height 668, stems about 90. Against its own letters, the 550 cell was average. The
references look wider at one size because their letters are bigger too. Measured from 24 coding
fonts, in units of a 1000 em:

| Font | Cell | x-height | Cell ÷ x-height |
|---|---|---|---|
| Comic Caret 1.7.0 | 550 | 473 | 1.16 |
| Comic Shanns Mono | 550 | 473 | 1.16 |
| Fira Code | 615 | 540 | 1.14 |
| Maple Mono | 600 | 560 | 1.07 |
| Intel One Mono | 614 | 465 | 1.32 |
| JetBrains Mono | 600 | 550 | 1.09 |
| Monaspace Neon | 620 | 514 | 1.21 |
| Source Code Pro | 600 | 478 | 1.26 |
| Median of the 24 | 600 | 530 | 1.13 |
| Comic Caret 2.0 | 600 | 473 | 1.27 |

The 600 cell with the same letters sits between Source Code Pro and Intel One Mono, so text
reads more open. Half-block pixels ▀ ▄ become almost square, 600 × 675. Our letters fill more
of the cell than the references' do: `n` filled 75% of the 550 cell, theirs fill 67–70%. So
the `n` family fits the 600 cell as it is, moved to the middle.

Monaspace's Regular, SemiWide and Wide cuts (620, 699 and 778 wide) show how one designer
shares out a wider cell. The table gives the ink gained per unit of cell gained, the median
over Argon, Krypton, Neon, Radon and Xenon:

| Glyphs | Share |
|---|---|
| Letters and figures | 0.72–1.03 (`n` 0.91, `o` 0.90, `m` 0.88, `w` 0.72, `i` 0.82) |
| `< > #` | 0.66–0.70 |
| `- + = / \ ( ) [ ] { } @ ~` | 0.37–0.49 |
| `"` `*` | 0.16–0.31 |
| `. , : ; ! ? ' \|` | 0 |
| Arrows | 0.17 |
| Superscripts and subscripts | 0 |
| Box drawing and blocks | 0.5–1 (they fill the cell) |

Monaspace widens every letter. Comic Caret doesn't, as its letters start fuller in the cell.

- **The width rule.** A glyph that widens keeps its ink width within the narrowest and the
  widest of Fira Code, Maple Mono and Intel One Mono, with x scaled to a 600 cell, give or take
  `WOBBLE`; the bold takes its range from the five reference bolds. The drawing aims at the
  larger of the regular's floor and the bold's floor less 35, the bold pen's width: the least
  widening that keeps both styles in range. No glyph is scaled to widen it: its strokes move,
  turn or lengthen.
- **Round letters and figures.** Each bowl lengthens at its top and bottom, where its strokes
  run level, and a stem moves with its side. `o` is 450, `O` 474, `0` 451, `e` 442, `g` 438,
  `a` 458 and `3` 450. `b` `d` `p` `q` are one width, 449, as each reference draws them at one
  width. `c` (425) and `5` (432) take Fira Code's widths, so `c` keeps in step with `e` and `o`,
  and `5` with `3`, as in the three references. `Q` widens with `O`, to 482. `0`'s slash and
  `e`'s bar turn a little. ø Ø þ ƿ đ ą ę, ρ δ σ ∂ on `o`'s bowl, ç ¢ ς and the accented letters
  follow through references or outline copies.
- **`Y` `6` `9` on their rows.** `Y`'s stem ended at −37, 17 under `H`'s foot, and `6` `9`
  topped at 689 and 691 where `2` `3` top at 675; each end moved to its row (2026-11-10), the
  move easing in along the stroke before it, since a level cut across `6`'s slanting arm left
  a jog. `∂` tops out with `6`. `¥`'s foot and the small `6` `9` of `⁶ ⁹ ₆ ₉ ⅙ ⅚` followed
  (2026-11-11), the small ones at 0.45 of the move, to 311 with the small `2` `3`. `a`'s stem
  still ends at −37, 12 under `o`: `ą`'s ogonek and `ª` are built on that foot, and the user
  chose this `a` on proof.
- **Open letters.** Bars, arms and tails lengthen along their straight part: `f` 461, `t` 441,
  `r` 427, `T` 490, `l` 444. `m`'s arches open at the crown, as do `n`'s and `h`'s; `u`'s bowl
  opens at its foot. `n` `h` `u` are one width, 417: Intel One Mono Bold's 452 less the pen's
  35, so their bolds reach the narrowest reference bold. η ŋ ħ µ ų follow as outline copies.
  `4`'s crossbar lengthens right of the stem, to 474: the references' right arm is 0.19–0.24 of
  the width, ours was 0.15. `J`'s bowl opens at the foot, under the top bar, to 425. `Æ`'s three
  bars lengthen right, to Maple Mono's 535.
- **`w` `W` `M`.** Each outer arm of `w` (515) and `W` (510) turns out about the point where it
  meets the next arm, so both are at least as wide as Intel One Mono's. All three references
  stop `M`'s middle above the baseline and the middle peak of `W` and `w` below the top; ours
  follow Intel One Mono's. `M`'s middle V rises 180, to about a quarter of the cap height, and
  ends round; its legs lean 45% less. `W`'s middle peak stops at 0.81 of the cap height, and
  `w`'s at 0.87 of its height. ₩'s upper bar rises 46, so it still crosses the lowered middle
  peak, its top 84 under the peak's top, as in Maple Mono's ₩ at the same cap height; both bars
  run out to the side room, from 15 to 585.
- **Beyond ASCII.** € and Œ open the C and the O at their middle, on the line through their top
  and bottom extremes. ð's bowl opens at its middle, and its rising stroke moves with its right
  side. ß's arch opens at its crown, and ẞ's top bar lengthens. Ħ ħ Ð Đ đ ₽ lengthen their bars
  past the stem, and Ł its bar along its slant. ₺'s tail lengthens along its level bottom, as
  `t`'s does. ¥'s arms turn out about the crotch.
- **Signs.** ₱ ₦'s bars run out to the side room, as ₩'s do: 570, the most `SYMBOL_SIDE`
  allows, within `WOBBLE` of Intel One Mono's 572 and 571. ℃ ℉'s rings move left and the
  letter's strokes run on, the C's top and foot and the F's arms: 569 and 566, against Maple
  Mono's 579 and 565. №'s N widens 40, its diagonal flatter, to Fira Code's 556, and ⌥'s three
  bars run out to Fira Code's 541.
- **Math signs, arrows and shapes.** ∫ ∏ √ ¬ take the narrowest reference's width. ∫'s hooks
  run 15 further each (450), √'s tick 12 (503) and ¬'s bar 20 (370). ∏'s stems move in 15 and
  its bar runs 26 past them, as in Fira Code and Maple Mono (521). ↰ ↱ ↲ ↳ take Fira Code's
  520: the shaft runs 44 further. ↵ ↩ ↪ take the same 44, so the return arrows stay one width.
  ◇ ◆ (540), ▲ ▼ (541) and ◊ (466) take Fira Code's widths, and ▸ ▹ ◂ ◃ Maple Mono's (310).
  Each corner moves out whole, so the edges stay straight. ▲ ▼ are ▶ ◀ turned, so ▶ ◀ grow as
  tall (541). ∴'s lower dots move out 9 each (470), so the bold ∴ is Fira Code Bold's 504. ✗ ✘
  take Maple Mono's 538 and 550, the one reference that draws them.
- **Symbols.** `-` lengthens at its middle, to 365. Each arm of `<` `>` turns flatter about the
  centre of the point's round end and lengthens until its end is back at its height, so `<` `>`
  (425) keep their height within a unit. ≤ ≥'s angle widens by 62 the same way, to 446, and the
  bar lengthens with it. `%`'s rings, `"`'s ticks and the parts of `?` `&` move apart, and the
  slash of `%` and ‰ lengthens: `%` is 564 and ‰ 563, `&` 517, `?` 404, `"` 307. `+` − ± ÷ are 463.
  ❯ ❮ (332) and ❱ ❰ (452) are built on the wider `>` (see Heavy marks and shapes).
- **Dashes and arrows.** – (445) and — (504) are Intel One Mono's lengths at the wider cell. …
  is 483, at least Maple Mono's 480; its dots keep their size and stay evenly spaced. The axis
  arrows → ← ↔ ⇒ ⇐ ⇔ ↦ ⇤ ⇥ are one length, 555: their shafts lengthen, and the heads and bars
  stay. Fira Code draws → ⇤ ⇥ within 4 of each other, and Maple Mono → ↦ within 10
  (`ONE_LENGTH` in `tests/test_consistency.py`).
- **Doubled marks.** The copies of ″ “ ” „ stand 6 to 8 further apart and ‖'s 2, so the white
  between them stays at least the narrowest reference's at the wider cell.
- **⁄ and the fractions.** ⁄ turns 5.9° flatter about its middle and lengthens, its ends at
  their heights, to Fira Code's 565. The fractions' own slash turns 3.8° flatter, each numerator
  moves 25 left and each denominator 25 right: ¼ ½ ¾ are 576, Maple Mono's ¼ ½.
- **Round marks.** ○ ● grow 28 each way, to 548, and stay circles: ○ stays at least as much
  wider than `o`, and ∅ than ø, as Fira Code's. ◯ ◉ ∅ and the spinner frames on ○ ● follow. ⏺
  stays at ⏸'s height. The bars of ☰ … ☷ stand 13 further apart, so they still span 84% of ○'s
  height, as Fira Code's do. ¨'s dots move 20 apart each, to 334: Intel One Mono Bold's 369 less
  the pen. U+0308 and every letter that carries ¨ follow, so the spacing mark and its combining
  twin stay one design. ° (300) and • (240) grow at their middle both ways, so they stay round.
  ◉'s dot keeps its size: the grown • at 0.8488, at the whole-unit offset nearest the centre
  that keeps the white between ring and dot (70).
- **Boxes.** ☐ ☑ ■ □ are 502 each way, Intel One Mono's ☐. The left and bottom walls move out
  and the box moves back by half, so ☑'s check keeps its place against the top and right walls.
  ☒'s quarters move out and its cross's arms lengthen along their diagonals, to 505.
  `add_shapes.py` rebuilds the frames on ☐ ■ (◰ ◱ ◲ ◳ ⧆ ⧇ ▮ ▯ ◢ ◣ ◤ ◥ ☖ ☗ ▰ ▱).
- **ŀ.** The dot moves 34 right and ends 18 past the l's foot, where the bold puts it.
- **The `~~~` run.** Each half-wave of the run, a fall from crest to trough or the rise back,
  is a third of the cell: 200 units. The pieces spread `~`'s own fall across 200 about its
  crest, keeping its height, so every seam meets at the crest's or the trough's height. In the
  550 cell three of `~`'s 174-unit half-waves left 28 units of flat at the seams. A single `~`
  keeps its own 174-unit half-waves, and so does a run's last fall, so the run ends where `~`
  does: after a 200-unit fall it ended 26 further right, 61 from its first cell's edge and 38
  from its last's (bold 44 and 20). `asciitilde.mid` and `.end` are the low pieces mirrored
  about the wave's middle. The crest's profile is a unit thicker than the trough's, so the
  mirror leaves each cut corner a unit off its profile. `snap_edge(level=True)` moves the level
  run that ends at the corner with it. Moving the corner alone leaves a short slant, which the
  bold pen grows into a step of 4 at the crest.
- **The ligatures.** `tools/add_ligatures.py` measures its constants on the widened `-` `<`
  `>` (`TIP`, `ARM_ENDS`, `HYPHEN_SPAN`); `ARM_ENDS` holds the centres of `>`'s round ends,
  and `<`'s are those turned. `longer_angle()` lengthens each arm until its ink reaches the
  height its caller asks: the arrowheads →'s and ←'s, so `->` reads as →, and the heads of
  `|>` `<|` `<|>` a triangle as tall as Fira Code's, centred on the axis. An arrowhead's arms
  come out 100–120 shorter than `>`'s. Squeezed into the 170 of `ARM_SPAN`, the hand's gentle
  bends along the arm (up to 8°) steepened to 15–20° corners, which showed as bumps from about
  150 px; a piece cut out and the ends welded left a corner at the weld. So `reaching()`
  redraws a shortened arm's straight part, `ARM_STRAIGHT`, as one cubic per edge, leaving and
  entering in each side's own slope. The hand's swell along the arm goes with it: the heads
  weigh 0.93–0.97 of the angle there. A swell put back as a bump at the middle made the edges
  wave. Turned apart about the tip, the two halves of `>`'s round point part at the axis in a
  notch; `rounded_point()` runs the outer edges on straight from `POINT_BACK` and joins them
  with one arc that reaches the tip where it was, radius 67 (`>`'s point is 51). Turning the
  halves about the point's own centre instead left small steps where the hand's not quite
  round point met the arms, and easing the turn (`eased()`) kept `>`'s wide point on the
  steeper arms as a bulb. `open_crotch()` cuts the spike along each turned arm's own inner
  edge, from `>`'s inner corner as the arm carries it to where the edge stands 60 off the
  axis. Lines through two sections of `>`'s unturned edge missed the bent arms by up to 5 and
  left a tick beside the crotch, seen inside `⇒ =>`. Their apex now lies 79 in from the tip,
  so a `-` shaft runs 70 in (`SHAFT_INTO_HEAD`, 80 before), past it: at 80 the shaft stopped a
  unit short and left a pinhole of white. The gain that
  widens `<` `>` into `<=` `>=` shrank as `<` `>` grew 64 wider, so the angle keeps its
  reference size: `ANGLE_WIDTH_GAIN` (94) widens it to 519, Fira Code's 1.10 x-heights (Maple
  Mono's is 1.13), its arms as tall as `<` `>`. `<=` is `>=` mirrored, as in Fira Code and
  Maple Mono. `<` is `>` turned, so a `<=` built from its own angle would hang its bar under a
  different hand-drawn arm, and the two bars would stand 9 apart.
- **Seams under light hinting.** FreeType's light autohinter, the default on Linux desktops,
  hints each glyph alone, so the pieces of a ligature meet on one pixel row only where each
  piece's bar rounds the same way. Two things moved a bar a row off. A bar edge that strays
  from its profile toward a cap or a head's point rounds with that stray: `level()` moves
  every point within the wobble of a profile height onto it. And an arm end within reach of
  a zone, which the autohinter aligns first and then places the bar from: → ⇒ ← ⇐ and their
  heads reach 21…527. A lower end at 15 or under, 8 or under in the bold, is
  aligned to the baseline; an upper end at 509 to the x-height; and ← reaching 529 or more
  moves the bars of `<<-` and `<=<`. Measured with freetype-py 2.5.1 (FreeType 2.13.2) at
  8–36 px; `LigatureSeamTest` in `tests/test_built.py` checks every piece. The autohinter
  pairs two level edges that face each other over the same columns as the two edges of one
  stem, and places the glyph's other stems from its lowest. The `<` pieces of the arrows
  (`<-` `<==` `<~` `<<-` `<=<`) are the `>` pieces mirrored, as ← is →. Built from `<`, `>`
  turned, their heads swapped the hand-drawn arms, 11–13% of the head's area apart from ←'s,
  and `<=<`'s tail ended its arms one over the other, so the bold tail's bars stood a pixel
  under `=`'s at 8, 11–12, 20–23 and 28–33 px. The mirror rounds a few TrueType points the
  other way, and with its inner head level `<<-`'s bar stood a row off `-`'s at 15, 18 and
  19 px: the inner head of `->>` and `<<-` stands 2 under the outer (`INNER_DROP`); 1 either
  way still did.
- **The TTF's hints.** FontForge writes no TrueType hints, so `tools/generate.py` gives each
  TTF ttfautohint's, with its default options and one control instruction (below). Without
  them every renderer that runs a font's own hints drew the TTF unhinted: FreeType's native
  and monochrome modes, and Windows GDI (not tested). At 8–24 px under native hinting, 281
  letters of the regular stood off their row (38 after; Fira Code 126, Maple Mono 17), `=`
  blurred into one grey band at 11 px (bar contrast 0.02, 0.93 after) and in monochrome `8`
  read as `B`. Light hinting is unchanged: FreeType's autohinter, which ttfautohint follows,
  hints the TTF there either way. `--composites` and `--fallback-script=latn` changed none of
  these numbers. The control instruction puts ≡ ≠ ⇐ ⇒ ⇔, drawn with level bars of `=`'s
  weight, in `=`'s Latin style: ttfautohint hinted ≠ and ⇔, outside its Latin ranges, in a
  fallback style with stem widths of its own, which put their bars on touching rows at 8 px,
  and in the bold ≠'s at 11–12 px and ⇔'s at 9. `--fallback-script=latn` parts them too, but
  rehints every glyph no script covers. The Latin style snaps an edge within 25 units of one
  of its zones to it and places the bars from there: ≠'s slash foot, at −18, put its bars a
  row off `=`'s at 9–12 px, so the slash runs 40 further each way, to −58 and 602, Maple
  Mono's length (Fira Code's and Intel One Mono's are shorter). The slash is `/`'s stroke,
  shortened along its straight middle and thinned 8% across: `/` swells toward its ends, 92
  across in the middle and up to 107 near them, and only those ends show past the bars, so
  `≠`'s slash read 13% heavier than `/` and 35% heavier than its bars. The double arrows still stand
  off `=`'s rows at some sizes. ttfautohint places `⇔`'s bars from its heads' ends, which puts
  them off at 11–12, 16–17 and 20–21 px in the regular; its control file can keep those ends
  out of the edges only by point number. `⇐` `⇒` `⇔` are off at 22–23 px too (12 in the bold),
  and the bold `≠` at 11, for a cause not found. FreeType's light hinting sets `≠` `⇐` `⇒` `⇔` off
  `=`'s at many sizes: its Latin style covers only Latin's Unicode ranges and hints Arrows and
  Mathematical Operators in a fallback style, which leaves their bars near their unhinted rows.
  Mapped from a Latin character too, `≠` stood on `=`'s rows at every size; a font can't change that
  coverage. At 9 px the italic `H`'s top stands on the row of `E` `T` `I`, but its slanted round
  stem ends fill only half that row (0.50, `N` 0.51), so it can look a row low. ttfautohint's `prep`
  keeps the smart dropout control the SFD's own `prep` carried. ttfautohint hints a component alone
  and then turns it, so the TTF draws every turned reference as an outline: turned, `)` stood a row
  below `(` at 11 px, and `∀` `∃` a row under the baseline.
- **Alignment zones.** The OTF's hints put the extremes inside one zone on one pixel row, so
  each zone runs from the lowest to the highest of its letters' extremes, the hand's wobble
  included: the baseline −37…−5, the x-height 461…493, the capitals and figures 658…692, the
  ascenders 710…719, and the descenders −297…−268 (`OtherBlues`), which runs 19 below its
  letters' lowest foot (`p` `y` −278) and so holds χ's (−284) too. The bold's move out by
  half the pen's height, 7, but its baseline zone keeps its top at −5: FreeType pulls that
  flat edge down by up to 0.6 px at small sizes, and from −12 it sank every bold letter a
  row at 9–12 px. Its BlueScale shrinks with that taller zone. `tests/test_metadata.py`
  checks that every style's letters stay inside. The hinter aligns hint edges, not extremes,
  so a letter needs a stem or ghost edge in each zone that holds its top or foot. FontForge's
  autohinter left some without: the bold `E`'s bar ends at 660 under its 665 top, the
  italic `z`'s bars at 458 and −3, `V`'s foot had none, and composites kept hints from before
  the zones, so the Greek capitals had the Latin ones' old edges or none. It also writes some
  stems top first, with a negative width the CFF spec leaves undefined, and FreeType aligns
  neither of their edges: the bold `U`'s top was one. Each stood a row off at 8–24 px.
  `tools/generate.py` hints every composite again, parts first, writes every stem bottom
  first and adds a ghost at each extreme a zone holds without an edge; `tests/test_built.py` checks
  the built OTFs. It removes a ghost the autohinter drew across the span of one it adds: in the
  italic `m`, a top ghost at −1 crossed the new ghost over its feet at −21, and with both
  hinted the foot fell half a row below the baseline at 20 and 22 px. FontForge's autohinter also
  gives some letters a stem crossing the one a zone holds, as `ε`'s upper end (357–443) beside its
  top (411–489). The two take turns under hint masks, and the top's points handed to the end's stem
  rounded with it: `ε` stood a row over `o` at 13 and 20–22 px. A stem that crosses a zone's by more
  than half a stroke goes, from the letter and its composites: `a`'s, `ą`'s and `ε`'s in the
  regular, `ε`'s in the bold. `a`'s top then ends on `x`'s row at 9–12 and 18 px, where it stood up
  to 0.4 px over it, and `ε`'s foot on the baseline. A stem that crosses a zone's by less stays, as
  at `T`'s bar: it hints the same wobbly stroke, and without such stems the bold `T` and `Œ`
  blurred. Only one outline's stems are compared: a mark's stem can cross its letter's by chance, as
  at `ñ`'s tilde and `ľ`'s caron, and dropping it blurred the mark. Rows off `H` and `x` at 8–24 px,
  native hinting: regular 139 → 112, italic 118 → 112, bold 155 → 85. `Λ`, `V` turned, stands
  5 lower, so its feet reach the baseline zone as `A`'s do; with its top aligned and its feet
  at 0 it stood a row high at 11 and 14 px. FontForge's autohinter gave `⇔` a stem from each
  bar out to its heads' ends, the upper one's top at 486, in the x-height zone; the hinter
  aligned it there and set the bar from it, a row off `=`'s at 9, 11 and 18–24 px in the
  italic, and at most of those sizes in the regular and the bold. `tools/generate.py` leaves
  ≠ ⇐ ⇒ ⇔ only the stems that lie on `=`'s. Taller heads took the ends out of the zone but
  closed the bold's bars into one band at 8 px, in both formats.
- **Unhinted composites.** FontForge wrote a glyph built from a turned or scaled reference
  with hint masks that set none of its stems, so the CFF hinter left it unhinted: `) ] }`
  `¡ ¿ ∀ ∃ ∇ ⏹ ⏺ ◼` and 8 more in the regular, 17 in the italic, 16 in the bold.
  `tools/generate.py` draws those references as outlines in the OTF too, and hints them.
  FontForge then hinted the italic `(` at its foot alone and `)`, `(` turned, at its top
  alone, and the two stood a row apart at 11, 12, 23 and 24 px; a glyph turned about its
  base's middle and that base now take each other's stems where none of their own cross them
  (`share_turned_stems()`), so `( )` `[ ]` `{ }` share their rows at every size.
- **Picture rows.** No zone holds most of the pictures' edges, and the CFF hinter snaps only
  one edge of a stem to the grid, so each picture rounded by its own stems: `⏵ ⏸ ⏺` ended on
  different rows at 10 of 20 sizes from 8 to 36 px, `■` and `☐` at 8. A ghost edge snaps
  alone, so `tools/generate.py` gives the pictures of a row (`PICTURE_ROWS`) one ghost at
  the row's foot and one at its top, and no other level hints; they share their rows at every
  size, and their bars stay sharp. The top of `⏵ ⏸ ⏹ ⏺` (489) lies in the x-height zone, so
  they end on `x`'s row, as `⏸` did. The TTF's pictures still round each by its own outline:
  ttfautohint has no edges per glyph, and its control file moves points only by number and
  size. `--fallback-scaling` levels the boxes but leaves every glyph no script covers
  unhinted, the box drawing too.
- **`--` beside `-`.** FontForge hints `-`'s wobbly bar from its level top and right part,
  235–311, and the pieces and arrows from their profile, 231–310; the CFF hinter snaps one edge
  of each, and `--` stood a row under `-` at 11 and 24 px. The bold pen grows `-`'s sloping
  foot (220 at the left end, 228 at the right) into a second stem, and the two took turns under
  hint masks: the bold `-` stood a row thicker than `--` and `−` there. In the OTF,
  `tools/generate.py` leaves `-` the stem that reaches its top and gives it to every outline
  hinted on the profile, so `-` `--` `->` `−` `–` share their rows at every size. Moving the
  profile to 235–311 instead left the start of `-->` and the bold `->>` off their seams, as
  `-`'s bar lies near 229 at the cut. The TTF's hints follow each outline: ttfautohint places
  `-`'s bar a row over the piece's at 13–14 px (14–15 under light hinting), and `=`'s upper
  bar from its wobbly top edge and the piece's from its foot, so `==`'s upper bar stands a row
  over `=`'s at 22, 23, 32 and 36 px (12 in the bold, for a cause not found).
- **`=`'s gap.** The white between `=`'s bars is 126, Intel One Mono's, between Fira Code's
  114 and Maple Mono's 135 at our cap height. At 106 the fonts' own hints merged the bars
  into one band at 8 px in every style and format (contrast 0; 0.55–0.75 at 126). Each
  bar moved 10 away from the axis. ≡ ≠ ⇒ ⇐ ⇔ ⇑ ⇕ moved theirs the same, ≡'s outer bars 20,
  and where a bar meets an arm or ≠'s slash, the corner slid along it, so the heads and the
  slash keep their size. FreeType's CFF hinter moves each bar whole to the nearer pixel edge,
  so at 8 px the upper bar rounds up, off the lower one, only while its middle lies above 375.
  The ligature pieces, `equal_bars()` and ⇒ ⇐ ⇔ therefore lie on `=`'s own hint edges,
  131–208 and 338–414; at 133–209 and 336–413 they still merged. ≠ and ⇔ merged at 8 px in
  the TTF until ttfautohint hinted them as Latin (above).
- **`|>` `<|`.** `PIPE_HEIGHT` lengthens the head's arms until the triangle is 1.52
  x-heights tall, as Fira Code's and JetBrains Mono's are. Both arms are `>`'s flatter lower
  arm, the upper one mirrored about the height where `>`'s arms meet inside its point, 9 under
  the axis, so both ends meet the bar's round ends, each corner turns as one round end and the
  point closes as `>`'s does. Unturned, that arm makes the triangle 1.29 x-heights wide, past
  Fira Code's 1.240 and JetBrains Mono's 1.245; the steeper arm would make it 1.18, under
  both. So `pipe_head()` turns the arm 1.1° steeper, from 31.3° to 32.4°, until the
  triangle's width over its height is `PIPE_ASPECT`, the mean of theirs (1306 over 1603 and
  685 over 835, 0.818). The arm's end keeps its height, so its reach across changes by the
  run of its middle line, 315, times the change in the slope's cotangent; the triangle comes
  out 589 wide, 1.245 x-heights. Mirrored about the axis instead, the foot of `>`'s upper arm
  would stand inside the point as a notch, and the point's round end would come 15 short and
  blunt. The bar's outer edge stays 295 into its own
  cell, 2 past Fira Code's 293 and 20 past JetBrains Mono's 275 at a 600 cell. The bar keeps
  `|`'s wobble, its edges 6–9 further right at the top than at the foot, so `against()` leans
  the head 0.7° with it: upright, one arm end stood out of the bar's edge as a step.
- **`->>`.** `HEAD_PITCH` (361) leaves 171 of white between the two heads, near the 550
  cell's, since the heads kept their size; Fira Code, the one reference that draws `->>`,
  leaves 145 at a 600 cell. With the lighter `<` `>` (2026-11-10), the old pitch, 369, left
  177. The inner head's crotch lies 68 inside its cell, so the shaft's cut end at the seam lies
  on the open shaft, as in `->`. From a pitch of 399 the crotch reaches that cut end, which
  then shows as a flat, and 426, which keeps the inner head where the 550 cell had it, leaves
  219 between the heads. The bold's pen grows the heads to 144 apart, under Fira Code Bold's
  155, so there the inner head moves along its shaft until the white is Fira Code Bold's
  (`make_bold.HEADS_APART`); a pitch that wide, about 376, would take the regular's white to
  182, further from Fira Code's 145.
- **Tight pairs.** `TIGHT_KEEP` states, for each glyph of a tightened pair (`::` `&&` `++`
  `//` `<<` …), the side bearing it keeps toward its partner, not how far it moves. The white
  between the pair is the sum of the two kept side bearings, so it stays when the cell grows or
  the glyph widens; a shift stated as a number would let the white grow 50 with the cell and
  shrink as `&` `+` `<` `>` `?` widen. `&&` keeps 45 of white, Maple Mono's (Fira
  Code joins its two); much less, and the two read as touching at 12–16 px. `!!` keeps 226,
  Fira Code's (Maple Mono 287). `;` moves as far as `:`, so the dots of `;;` line up with
  those of `::` and keep 214 (Maple Mono 189, Fira Code 238). No pair or three but `++`
  `+++`, whose bars join, keeps less than two symbols side by side, twice `SYMBOL_SIDE`
  (`tests/test_ligatures.py`). A three's middle glyph stays in place, so an outer glyph
  beside a copy of itself moves twice a pair's shift (`THREE_ENDS`), and `...` `///` `<<<`
  `|||` keep their pair's white, and `+++` its pair's overlap; `>>>=`, four glyphs, keeps a
  pair's shifts. `/**` opens as `/*` does, its second asterisk moved with the first, so its
  asterisks keep a plain `**`'s white. So a doc comment opens as tightly as a plain one.
- **The bold's wide characters.** Moved to the middle of the wider cell, the regular's glyphs
  have 25 more room on each side. So the pen pushes none of @ # ∞ « » Æ œ K ✔ ➜ past its side
  room, and `fitted()` keeps them at full width; in the 550 cell it condensed them.

Where a glyph stays under the width rule's floor, the reason and the measurement:

- **`2` and `P`.** The regular `2` (436) and `P` (441) are at their floors. The bold `2` is 472,
  8 under Monaspace Neon Bold's 480, and the bold `P` 476, 6 under its 482: within `WOBBLE`.
- **The fractions ⅓ ⅔ ⅕ … ⅞.** They are 569–580. Intel One Mono's fill the cell (600), Fira
  Code's pass it (611–682), and Maple Mono has none. The bold grows a fraction by 18–22, to
  591–598, and the widest then end at the cell's edge (⅛ at 600): a wider regular puts the
  bold past the cell.
- **¾.** It is 576, 3 under Maple Mono's 579. At 579, the bold ¾ passes the cell.
- **đ and ₫.** đ is 503, 7 under Fira Code's 510, and the bold đ 539, 1 under Monaspace Neon
  Bold's 540. ₫ is 505, 10 under Maple Mono's 515. ₫ holds đ, and in the bold a letter that a
  symbol holds stays within the symbol's `SYMBOL_SIDE`: the bold đ's bar ends at 585.
- **The bold ẞ.** It is 473, 10 under Maple Mono Bold's 483. `NARROW` grows it by 0.7 of the
  pen, chosen by proof over the full pen, which reached 485. The regular is 449, over the floor.
- **ŀ.** It is 462 against Fira Code's 562. The references end the dot 104 (Maple Mono), 118
  (Fira Code) and 148 (Intel One Mono) past their `l`, into the next cell, and their bolds
  65–135. Ours ends 18 past and stays in the cell. `tests/test_latin.py` holds the dot past the
  `l` instead.
- **Ą.** It is 499, `A`'s width, against Maple Mono's 527. Maple Mono's and Intel One Mono's
  ogoneks reach 31 and 29 past their `A`, and Fira Code's 0. Only the mark's place sets their
  width.
- **ĵ Ĵ.** ĵ is 416 against Fira Code's 435: the references' circumflex reaches 83 to 122 past
  their `j`, ours 51. Ĵ is 425 against Fira Code's 440: the references' circumflex reaches 16
  (Fira Code), 109 (Maple Mono) and 141 (Intel One Mono) past their `J`, ours 0. Our `J` is at
  Fira Code's floor.
- **˚.** It is 196 against Fira Code's 222: a proof of both, round, chose 196. The 1000 line
  top would hold 222 over Å too.
- **Superscripts and subscripts.** ⁰–⁹ ₀–₉ (207–219) stay against the references' 276–306,
  and ⁺ ⁻ ⁼ ₊ ₋ ₌ (208–218) against Fira Code's 233–235. Monaspace gives them no share of a
  wider cell (the table above).
- **■ □.** They are 502 against Fira Code's 540. They follow ☐, Intel One Mono's 502, so the
  boxes stay one size.
- **▮ ▯.** They are 264 against Fira Code's 285, the one reference with them: ☐'s height
  times Fira Code's width over height (`add_shapes.NARROW`), so they follow ☐ as ■ □ do.
- **The italic ↦ ⁄.** They slant past the cell, ↦ to −5..579 and ⁄ to −47..664, as Maple Mono
  Italic's do (−53..565 and −73..642).

## Ligatures

The rules live in `src/ligatures.fea`; these are the choices behind them.

- **`===`.** Three bars, as both references and our `!==` draw them, so `==` and `===` differ
  by more than their length. A run of four or more stays one double line.
- **Two `-` or `_`.** A run of exactly two stays as typed: an option (`--help`), a decrement
  (`i--`), an SQL or Lua comment and a Python dunder name (`__init__`) show the characters
  typed. Three or more join into a line, and `<!--` keeps its run.
- **After a tag.** `>-` is otherwise an inward head, so a run or arrow starts after a `>` only
  where the look-back reads a tag: a short one (`<li>---`, `</p>-->`), a name of up to ten
  letters and digits, or any that closes itself, which ends in `/>` whatever it holds
  (`<br />---`, `<img src="x"/>---`). After any other `>`, only `-->` joins, which keeps
  `a>---b` plain. A few non-tags still read as tags: `x<y>---z` and `<1>---` join, as text may
  run into a tag (`Hi<br>---`) and a name may hold digits (`<h1>`), and Haskell's `</>` right
  before `->` draws an arrow (`x</>->y`). One tag goes the other way: `<=<a>---` stays plain,
  as `<=<` joins first. None turns up in real code, so the rules don't single them out.
- **Marks.** A combining mark after a ligature's last character keeps the ligature from
  forming, so the mark sits on a plain character, which has the anchors the ligatures'
  glyphs lack. Giving those glyphs anchors would make `tools/add_marks.py` place them, but
  `tools/add_ligatures.py` draws them again after it runs.
- **`<=>`.** C++'s, PHP's, Ruby's and Perl's comparison is no arrow, so it tightens as a three,
  as `<$>` does. `<==>` is still an arrow.
- **`<+>`.** It takes `<*>`'s brackets, as Maple Mono's does, so they keep 210 of white to the
  `+`, past the references' 152–161, as `<*>` keeps 174 against their 92–116. Brackets of its
  own would be two more pieces for one sequence.
- **`!!` and `;;`.** Fira Code and Maple Mono join them beside other operators too (`x=!!y`,
  `;;&`); here they stay as typed there, as every pair does, except `!!` before Kotlin's `.`
  (`x!!.y`). `;` is no operator in `@Op`, so `x++;` keeps its pair. `;;;` stays as typed, as
  in Fira Code; Maple Mono joins it.
- **`<=` as an assignment.** `<=` draws `⩽` also where Verilog and VHDL assign with it
  (`q <= d`): no context tells the assignment from the comparison. Fira Code and Maple Mono
  draw `⩽` there too and offer `⇐` as an opt-in (`cv20`, `cv63`); Intel One Mono draws no
  ligatures unless asked (`ss01`). Comic Caret has no opt-in for it yet; with `calt` off, `<=`
  shows as typed.
- **Beside a name.** `/*` `/**` stay plain after a name (`src/*`), and so do `*/` before one
  (cron's `*/5`) and `>>` `>>>` after one (`Vec<Vec<u8>>`), unless a name or a number follows,
  as in a shift without spaces (`x>>1`, `cin>>n`). With spaces, `a >> b` still tightens.
- **Binaries and heredocs.** `<<` and `<<<` before a name, a number or a quote stay plain
  unless an operand stands before them. So Erlang's and Elixir's binaries (`<<1, 2>>`,
  `<<"a">>`) open as they close, and heredocs and here-strings (`cat <<EOF`, `<<<"$x"`, PHP's
  `<<<EOT`) show as typed, as `<<-EOF` does; a shift without spaces (`x<<1`, `cout<<x`) still
  tightens. Fira Code tightens a binary at both ends, Maple Mono only where it opens. A quote
  counts as an operand, so `">>"` in a string stays plain where `"<<"` tightens:
  `cout<<"a"<<"b"` can't be told from it.
- **`..`.** A range or a slice tightens: after a name, a number, a closing quote or a bracket,
  or before a name, a number, a quote or a closing bracket (`0..n` `'a'..'z'` `&s[..n]`
  `[1..]` `{ ..x }`), as in Fira Code and Maple Mono. A path stays as typed, quoted or not
  (`../..` `"$DIR/.."` `".."`), and so do Python's relative imports (`from ..models`,
  `from ... import`), which no other context tells from a range.
- **`~>` and `<>`.** Both stay as typed. `~>` ends fish's prompt in the home directory, and
  before a version it means "at least, within" (Ruby's and Terraform's `~> 1.0`); `~~>` and
  longer still join. `<>` opens a React fragment, and no context tells it from Java's diamond
  operator or SQL's `<>`.
- **Prompts.** `>>`, `>>>` and `...` stay as typed at a run's start before a space, as in
  Python's prompts `>>> ` and `... ` and an email quote's `>> ` at a line's start. The REPL
  redraws its line with the cursor at column 0, and Ghostty shapes the cursor's cell alone. So
  at each keystroke `>>> ` jumped between a tightened `>>>` and `>` beside a tightened `>>`, and
  `... ` between a tightened `...` and as typed. Maple Mono joins `>>` and `>>>` only after
  another character, so its prompt stays as typed too. They still tighten after a space
  (`a >>> 2`, an indented doctest) or an opening bracket (Haskell's sections `(>> m)`
  `(>>> g)`, `[... ]`), and `...` after a name, a closing bracket or a straight quote too
  (`wait... what`, `f()... x`). The rule leaves them alone with nothing after, as an editor
  shapes a lone token, and before a name or a bracket (`...rest`). OpenType can't match a run's
  start, so the rules list what may stand before instead (`@SpaceOrOpen`, and `@Operand` for
  `...`). After any other character they stay as typed: an accented letter, `α`, `”`, `}` or
  `;`. Ghostty also starts a run at the cell after the cursor, so with the cursor just before a
  spaced sequence, as on the space of `a >> b` or the `t` of `wait... what`, it shows as typed
  until the cursor moves off. Every rule that reads the character before loses it beside the
  cursor, as the `>>` that closes generics (`Vec<u8>>`) tightens there; the prompt flickered at
  every keystroke only because the REPL puts the cursor at column 0.
- **Kept.** `?.` tightens after a name too, as JavaScript's `a?.b` does; Rust's `x?.y`, `?`
  then a field, can't be told apart from it.

## Italic

The italic is the regular sheared, generated by `tools/make_italic.py`; nothing in its SFD is
drawn by hand. The choices, proofed on 2026-09-30 against Maple Mono 7.9, Intel One Mono
1.4.0 and Monaspace 1.400 (Neon and Radon), with the italic reference fonts in
`build/cache/reference/italic/`:

- **12°**, between Maple Mono's 10° and Intel One Mono's 16°, next to Monaspace's 11°. It
  reads as italic at 14 px, and the worst slashes and tails leave the cell by 49–64 units
  (`/` χ № 49, ⁄ 64), as the references' do. Only a mark at its letter's upper right leans
  further: ď's caron 106, the circumflex stacks' accent up to 147 (see Latin). 10° stayed close to
  the regular in a comment, and 14° and 16° pushed the capitals' tops and the tails further out.
- **One shear for every slanted glyph**, x += (y − 269) × tan 12°, pivoting on the hyphen's
  middle. A stroke at any height moves the same in every glyph, so the ligature pieces still
  meet at the cell seams, `-` `=` and the arrow shafts stay where they are, and the lowercase
  stays centred. Composites keep their references with the matrix conjugated by the shear,
  and anchors move with it, so accents and the mark lookups need nothing of their own.
- **Evened diagonals.** A shear thins a stroke that leans with it and thickens one that leans
  against it: `/` came out 76 and `\` 90, 18% apart, and `x` `X` `v` `A` `k` `W` had one thin
  arm each. The reference italics keep 8% (Intel One Mono), 12% (Maple Mono) and 13% (Monaspace
  Radon). Before the shear, `evened()` moves each edge sideways by 2.5 × −2 n.x² n.y, n being its
  outward normal: `/` 79, `\` 86, 9% apart, chosen on proof over evening them fully (84 and 85,
  more even than any reference). Level and upright edges do not move, so bars, stems and the
  ligature pieces' seams stay; a round letter's sides come in by a unit. The move is along x
  only, as the shear's is, so no row changes. Moved along its normal, `τ`'s top rose a unit,
  and ttfautohint, which takes Greek's x-height zone from `τ` among others, set the Greek
  capitals a row off `H` at 9 px. From 3 on, the outlines of `æ` and the small `5` cross.
- **What slants**: letters, figures, the combining marks, punctuation, brackets, quotes,
  currency, superscripts, operators, arrows and the ligatures. Maple Mono and Intel One Mono
  slant all of these, Maple Mono its arrows included; keeping → upright while `->` slants
  (Monaspace's choice) makes a typed arrow differ from the ligature's head, which the regular built
  → from.
- **What stays upright**: what is drawn as a picture, which Maple Mono and Intel One Mono
  leave as their regulars draw it:
  Box Drawing, Block Elements, Braille, Powerline, the geometric shapes and spinner frames,
  the status marks ✓ ✗ ⚠ ℹ, ⏺ ⏵ ⏸ ⎿ ⧉ and �. Two choices go against Maple Mono, which slants
  them: ☐ ☑ ☒ stay upright because ours are squares of the hyphen's stroke like □ ■, and the
  spinner frames ◰ ◱ ◲ ◳ are built on ☐; the white arrows ⇧ ⇪ ⇦ ⇨ ⇩ ⇞ ⇟ and the tab keys ↹ ⇥ ⇤
  stay upright because they are key hints that read beside ⌘ ⌥ ⌃, which Maple Mono lacks.
  • ∙ stay too, as ◉ ⊙ are built on them; so do ‣, ▸'s triangle, and ℹ, which stands beside ⚠.
- **Dots** shear with the letters, as Maple Mono's and Monaspace's do; round dots that only
  move with the slant looked the same at 14 px and would need a special case.
- **Cursive letters**: only f. The regular's single-storey g already reads as an italic
  form. a slants double-storey, as Intel One Mono's and Monaspace's italics keep theirs, so
  a and o stay apart in italic comments. l keeps the regular's form: Maple Mono's looped l
  made "all" and "full" busy at 15 px and turned l into ℓ, and a plain stem lost the tail that
  keeps l apart from I and 1. f runs its
  stem 268 below the baseline, as deep as j, ending in a flick 70 left of the stem in the
  stem's own stroke, chosen over ƒ's hook (Maple Mono's f), which reached 72 units left of
  the cell, and over a plain straight descender. The descender takes the stem's width where
  the stem's round end is cut away, 80 above the baseline, and is welded on along that cut (`geo.weld_y`),
  so the joint has no ledge and no overlap for `removeOverlap()` to merge. ƒ keeps its own
  outline.
- The italic's f, and any glyph the shear cannot express (∙ built on the period, ⋮ on the
  ellipsis turned a quarter), is an outline in the italic; everything else keeps the regular's
  structure, references included.

## Bold

The bold is the regular with its strokes grown, generated by `tools/make_bold.py`. Nothing in
its SFD is drawn by hand. The choices were proofed on 2026-10-01 against Fira Code 6.2, Intel
One Mono 1.4.0, Maple Mono 7.9 and Monaspace 1.400 (Neon and Radon). The bold reference fonts
are in `build/cache/reference/bold/`.

- **The pen** is an ellipse 35 wide and 14 tall. Each outline is stroked with it, the stroke's
  inner edge dropped, and the rest united with the outline. A stem grows by the pen's width
  and a level stroke by its height, half on each side, so a bold letter keeps the regular's
  rows. Its tops rise by half the pen's height, so the bold declares its own x-height and cap
  height, 480 and 675.
  - When the pen was chosen, in 1.7.0's 550 cell, ink in a–z filled 57.5% of the x-height
    band. The reference bolds fill 51–59%.
  - That was a step of 13.5 points from the regular's 44.0%. Maple Mono's step, the smallest
    reference step, is 14.
  - The counters at our x-height, `n` 172, `o` 199 and `e` 109, were each at or above the
    narrowest reference bold's. The 600 cell's wider letters keep more: `n` 180 and `o` 224.
- **An offset, not `changeWeight()`.** The offset grows every edge alike, so `-` stays centred
  on the math axis.
  - The ligature pieces grow by the same pen as the `-` `=` `<` `>` `~` `|` they continue, so
    they still match at their seams.
  - A piece's flat cut end past the cell is trimmed back to the regular's. It stays flat and
    keeps its overlap with the next piece.
  - FontForge's `changeWeight()`, in its LCG mode, keeps the letters' heights but grows a level
    stroke upward only. `-`'s top moved from 311 to 341, off the axis. The `--` pieces stopped
    matching at their seams (351 against 341).
- **Cracks.** Where a wave arrow's wave (`~~>` `<~` `~~~>`) runs into the head along an arm,
  the regular leaves 35 to 41 of white between them. The pen grows both into it and leaves a
  crack 7 to 36 across, shut at the point and open at the other end: a hairline from 32 px
  (2.6's `~~~>` had one too). `make_bold.PLUGGED` fills it, from the point to where it opens
  out wider than the pen, and the white beyond ends round, on an arc that fits it.
- **Small parts, a smaller pen.** The superscripts, fraction figures and ™'s letters grow by
  the pen scaled by the small `1`'s stem over `1`'s. So do the parts drawn as light as them:
  the fraction bar, the ordinals' bar and © ®'s ring. A bold superscript is then as much
  bolder as a bold letter.
- **What stays as it is** is what is drawn as a picture. The reference bolds keep such
  glyphs as their regulars draw them.
  - Box Drawing, Block Elements and the geometric shapes meet their neighbours across the
    cell.
  - ◦ stays with the shapes, as Maple Mono Bold's does. ‣ is a text bullet, not a shape, so it
    grows with •, as Maple Mono Bold's ‣ does while its ▸ stays.
  - The Powerline separators fill the line box. The branch, line number and padlock stay with
    them. Monaspace Neon and Radon Bold keep all three as their regulars draw them, Maple Mono
    Bold its branch and padlock, and Intel One Mono Bold its padlock; Fira Code Bold grows all
    three.
  - Braille's dots draw graphs and spinners.
  - Every frame of a spinner stays, so the spinner turns in one place and does not pulse. Only
    ‼ grows, as it is two `!`.
  - The media controls ⏵ ⏸ ⏺ stand side by side at one height in status lines.
  - □ is ☐ and ■ its outer contour, so ☐ stays with them. ☑ ☒ are ☐ marked, so the three
    boxes stay alike.
  - These glyphs and .notdef are copied unchanged, then hinted again under the bold's zones.
- **Heavy marks** ✔ ✘ ✖ ❯ ❮ ❰ ❱ ➜ grow by the pen scaled by how much heavier the regular
  draws them than ✓ ✗ ✕ > < →. So they stay as much heavier. The full pen would grow the light
  glyphs more for their ink and close the difference. This departs from the reference bolds,
  which keep their heavy marks as their regulars draw them, lighter than their bold light
  marks. Ours read heavier in every weight.
- **The cell.** The pen pushes no ink out of the cell, or past the regular's own overhang
  where it has one (ď, the tonos capitals).
  - No glyph but a letter or figure comes nearer the cell's sides than `SYMBOL_SIDE`, or the
    regular's ink where that is nearer. So two symbols side by side keep twice that between
    them.
  - A glyph that would pass its bound is condensed. Its outline is scaled across about its ink
    centre before the offset, just enough, so every stem still grows by the full pen.
  - A composite whose part would pass its bound moves its references in toward the cell's
    centre instead.
- **Composites** keep their references, so an accented letter follows its base. A glyph with
  an outline and references has only its outline grown. Three kinds of part are unlinked
  first.
  - A shared glyph's bolder part (∙ on the period) keeps the regular's outline, as in the
    italic.
  - A bolder glyph's shared part grows as its own outline.
  - A bolder glyph's part turned a quarter or scaled (⋮ on …, ⇦ ⇨ on ⇧) grows as its own
    outline, since the reference would turn or scale the pen too.
- **Mirrors and marks.** The pen alone would break two things the regular keeps.
  - A left glyph the regular draws as its right one mirrored (⇤ ⇥, ↩ ↪) is the bold right one
    mirrored, so the two stay exact mirrors.
  - A mark above a letter rises by as much as the pen grew the two toward each other, 14 (the
    ring's 21), so it keeps the regular's white, which the reference bolds' floors stay under
    (`BoldMarkTest`). It rises as far on every letter where it stands as high, so a row of
    them stays level, and must clear `MARK_CLEARANCE` (20), a floor under the regular's
    closest marks over a letter (ď's caron at 22.5) and over the reference bolds' closest,
    Maple Mono Bold's Å ring at 15. The circumflex stacks' accent stands at it, beside its
    circumflex.
  - The anchors carry over, so each combining mark rises as far as its accent does over the
    lowercase letters, and a shaped mark lands where the precomposed letter puts it.
  - A mark beside another (ấ's acute and its circumflex) keeps `SYMBOL_SIDE` from the cell's
    side, so it moves 18 left, where the pen grew it, and rises on until it clears
    `MARK_CLEARANCE` from the circumflex. The pens close the two across, by a full pen, so the
    accent rises 44–50 (Ấ's 46), 30–36 more than the circumflex's 14: Ấ tops at 1114, ấ at
    943. So the acute's foot stands 8–12 over the circumflex's top, above its arm, where the
    reference bolds keep it 5–26 under (Intel One Mono Bold 5–18). Keeping the regular's
    step would take the circumflex 29–41 left of its letter's middle, against Intel One Mono
    Bold's 11 at most.

Where the pen alone would break a rule the regular keeps, `make_bold.py` names the glyphs and
what it does to them:

- `TURNED`: the tonos, the acute's stroke turned 25° steeper, grows by the pen turned with it.
  `test_tonos_is_the_acute_turned` (`tests/test_make_bold.py`) holds the regular's tonos to
  the acute's slant plus 25°. So the bold tonos stays the bold acute's stroke turned.
- `ROUND`: ª º's bar and ⇪'s bar, drawn as heavy as the stems beside them, grow as much up and
  down as across. The level pen would leave them 21 lighter than the bold stems.
- `NARROW`: ẞ and the small 4 grow by 0.7 and 0.83 of the pen's width. ẞ: the full pen keeps
  its white between stem and diagonal at 67.5, over Maple Mono Bold's 64, and makes it 485 wide
  with a stem as heavy as ß's; a proof chose 0.7, which leaves it 473. The small 4: the full pen
  would close its counter to 0.128 of its height, under Maple Mono Bold's ¼ (0.136). Every share
  from 0.79 to 0.87 keeps 0.139, and 0.83 is the middle of that range.
- `BAR_WEIGHT` and `TICKED`: `|` grows by a pen wide enough to bring it to 125 across, as
  heavy as the bold `l`.
  - The regular draws `|` at 77, lighter than its stems (`I` 94). The pen would leave it at
    111, 0.85 of the bold `I`. That is under every reference bold's 0.896 (Fira Code) to 1.112
    (Monaspace Radon). `||` read thin beside `I|l`.
  - ¦ grows by the same pen. So do ₿'s ticks past its B, so they stay as heavy as `|`.
  - Grown in place, the ticks would come 4 apart. So each moves away from the other by as far
    as the pen grows it and keeps the regular's 52.
  - Each tick runs 60 down into the B, so it still meets the bowl.
  - ‖ and the tightened `||` `|||` are references to `|`.
- `OUTWARD`: © ®'s ring grows outward only, by the small pen's whole width. So it stays as
  heavy as its letter and the letter keeps its room. Grown both ways, it came 35 from ®'s R,
  under Fira Code Bold's 41 around its ©. The ring of å ů grows outward only too, by the full
  pen, so its counter stays 112 across, over Fira Code Bold's 89.
- `BLUNT`: ₩ ₦ ₱'s bars run 43 to 127 past their letter on both sides. The pen lengthens their
  round ends. This tapers the bars' run clear of the letter, so the bars would reach the
  hyphen's weight only near it. So the sign keeps its regular box, condensed. A second pen, as
  tall but a unit wide, is united with the first. The bars' ends keep the regular's length and
  weigh as much as the hyphen.
- `ACROSS_AS_UP`: ⇕ is ⇔ turned, and the turned pen would grow it past ↑'s height. So ⇕
  grows by the pen as it stands. It is condensed until it grows across only by the pen's
  height, and stays as wide as ⇔ is tall.
- `MERGED`: Θ is drawn as one outline, each part grown on its own. Its bar beside a reference
  to O fails `validate()` once saved (`docs/fontforge-pitfalls.md`).
- `APART`: where the pen grows two parts of a composite into each other, one moves clear, just
  far enough to keep the regular's gap.
  - i j's dots rise.
  - ŀ's dot and the carons of ď ľ Ľ move right.
  - The tonos beside a capital moves left.
  - ΅'s dieresis and ª º's bar move down.
  - ΐ ΰ's dieresis then sits 30 below ϊ ϋ's, level in the regular. This is a row break that
    letters as rare as these may take.
  - ĳ, one outline, keeps its dots 14 lower than i j's.
- `DOUBLES`: both copies of “ ” „ ″ ‖ ‼ move apart, each as far. So the mark stays on the
  cell's middle and keeps the regular's white between its copies.
- `TIGHT`: each glyph of a tightened pair moves back out by half its pen's width, as far as
  the pen grew it toward its partner. So the pair keeps the regular's white.
  - Unmoved, `&&` would merge into one shape and `??` keep 9. `++`'s bars keep their overlap.
  - A three's outer glyph moves back its pen's whole width, as its unmoved middle glyph grows
    toward it too.
  - A glyph tightened toward an unmoved one of another kind moves back only its own half. Such
    are `=` in `&&=` and `>>=`, and `<` `>` in `<$>` `<=>` `..<`. The unmoved glyph grows
    toward it as toward any neighbour. So the bold keeps about 16 less white there (`||=` 24,
    by `|`'s wider pen).
  - Each operator still groups as typed. Keeping the white would take a piece of its own for
    each glyph beside an unmoved one, as `<` `>` share theirs with `<<` `>>`.
- `OWN_BOX`: ™'s T and M, Θ's bar, ⌥ and the caron of ď ľ Ľ are condensed to keep their own
  regular box.
  - ™'s letters, 23 apart, would all but touch.
  - Θ's bar would come 29 from its ring, under the reference bolds' 38. It keeps 47.
  - Fira Code Bold, the one reference bold with ⌥, draws it as wide as its regular, 541. Grown,
    ours would be 569.
  - ď's caron runs on into the next cell. Grown 35 wider, it would run into an l's flag. It
    keeps 32 from it, as Maple Mono Bold's keeps 29.
  - It stands steeper and lighter. Across its slant it weighs 0.81 of the stem, as Maple Mono
    Bold's does. Intel One Mono Bold's (0.74) and Fira Code Bold's (0.75) are lighter still,
    and run into the l.
- `PIECES_APART`, `LIGHT_PIECES` and `OUTWARD_PIECES`: the pieces of ⇥ ↹ (arrow and bar), ‰
  (its zeros) and ℃ ℉ № (letter and small pieces) grow on their own. The wider is condensed away
  from the other until the white between them is the regular's.
  - Each keeps its far end where the pen grows it, or at the side room. So the bold ‰ stays at
    least as wide as the bold % (569). It is 570, and centred.
  - The small pieces of ℃ ℉ № grow by the small pen, so they stay as light as the small
    figures.
  - ℃ ℉'s ring grows outward only, across by the small pen's whole width, as © ®'s does, and
    up by as much as its letter, and moves in from the side room; the letter gives way. So its
    counter stays the regular's 75 across, over Maple Mono Bold's 62 at our cap height. Grown both
    ways and condensed into the side room, it closed to 43. The ring is 193 wide and the letters 347
    and 315, between Maple Mono Bold's (179; 432 and 359) and Monaspace Neon Bold's (223; 346 and
    294).
  - A glyph the list misses fails a test. `test_bolder_glyphs_keep_their_pieces_and_counters`
    catches ⇥ ↹ № and a rule in `tests/test_symbols.py` or `tests/test_make_bold.py` catches
    ‰ ℃ ℉.
- `SLASHES`: grown, ‰'s slash would come 27 from the zero under it, where the regular keeps
  46, and 28 from the zero beside it, where the regular keeps 48. It first moves right, as far
  as the side room lets it, 14, which leaves 39 beside it. Then it shortens at its foot, along
  its length, until it keeps the regular's white below. Scaled down instead, it would come out
  3 lighter than %'s.
- `SHRUNK`: ※'s dots, ⧉'s front square, ⌫ ⌦'s × and %'s rings shrink just enough to keep
  twice `SYMBOL_SIDE` from the piece beside them, where condensing can't part the two.
- `OPENED`: ⎋'s ring opens wider around its arrow. The arrow would have to shrink by a third
  to clear.
- `DASHED`: ⇡ ⇣'s dashes shorten at their top by twice the pen's height. So each gap stays as
  much wider than the stroke as the regular's and stays open at 12 px.
- `LIFTED`: ⇪'s ⇧ is the bold ⇧, lifted as far as the regular lifts it. It lifts a little
  further where the bar comes within twice `SYMBOL_SIDE` of it.
- `RAISED`: Ħ's upper bar moves up its stems by the pen's height. So the white between its
  bars stays the regular's. Unmoved, it would come 81 from the lower bar, under the bold
  hyphen's 93.
