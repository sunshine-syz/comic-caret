# Design notes

How the glyphs are sized and placed, in more detail than the rules in `CLAUDE.md`. The
reference fonts live in `build/cache/reference/`: `FiraCode-Regular.ttf` from the Fira Code
6.2 release, Maple Mono 7.9 Regular (the Nerd Font build works too) and
`IntelOneMono-Regular.ttf` from the Intel One Mono 1.4.0 release (`ttf.zip`). All three are
OFL: copy measurements, never outlines. `tools/compare_glyphs.py` puts our glyph positions
next to theirs, and `tools/proof_sheet.py` renders ours beside them; with `--italic`, both use
the italic references in `build/cache/reference/italic/` and `--bold`, the bold references in
`build/cache/reference/bold/`: `FiraCode-Bold.ttf` (Fira Code 6.2), `IntelOneMono-Bold.ttf`
(Intel One Mono 1.4.0, `ttf.zip`), `MapleMono-NF-Bold.ttf` (Maple Mono 7.9, the Nerd Font
build) and `MonaspaceNeon-Bold.otf` and `MonaspaceRadon-Bold.otf` (Monaspace 1.400,
`monaspace-static-v1.400.zip`).

## Scaled parts

New strokes are drawn in the font's own hand: round ends, the stem weight (about 90), the
wobble. Reuse an existing stroke where one fits; move and shorten strokes rather than scaling
them. The exceptions:

- ∞ is 8's loop, scaled to fit, then its top and bottom strokes moved apart so its holes are
  as tall as Maple Mono's at our cap height; every reference draws ∞ lighter than its letters.
- The `*.small` components of superscripts, subscripts, fractions and signs are the regular
  glyph at 0.45 (figures, ⁱ ⁿ and the signs), 0.52 (the small parentheses, which reach past
  the figures as far as the references' do), 0.55 (ª º) or 0.41 (™ © ®), thickened with
  `changeWeight(…, "CJK", …)` (the default picks a method that pushes all the weight down and
  right) so stems measure 54 ± 4, or 56 in ™ © ®; the fraction and ordinal bars are thinned
  to match.
- ▹ is ▷ at 0.61 thinned to a 41 outline, since at the full stroke its counter fills in at
  16 px; ▸ ▴ ▵ ▾ ▿ ◂ ◃ follow it. Its size keeps the white across its middle, 168, above Maple
  Mono's, the only reference's, whose lighter 37 outline leaves 159 at our cap height.
- ▫ (☐ at 0.52) and ◦ (a ring of ○'s shape, 250 across) are scaled so their rings come out
  about 41 too.
- ⧉'s squares are the hyphen's stroke at 0.79, so the one behind keeps clear of the one in
  front; ⏺ ⏵ are ● ▶ scaled to ⏸'s height.
- The keyboard symbols ⌘ ⌥ ⌃ ⇧ ⌫ ⌦ ⎋ ⏎ take the same 0.79 stroke, for their detail, so key
  hints such as ⌃⌥⌘⇧ read at one weight.

## Heavy marks and shapes

- Heavy marks (✔ ✘ ✖) are their light glyph (✓ ✗ ✕) pushed out 23 on every side,
  then squeezed at the ends to at most 510 wide; ⏸'s bars are `|` pushed out 40, to
  weigh as much as ⏵ ⏺.
- ❯ ❮ are no heavy `>` but the tall angle ornament that every coding font drawing them
  (JetBrains Mono, Cascadia Code, Maple Mono, DejaVu Sans Mono, Menlo, Iosevka) draws: `>`
  with its arms lengthened and each turned 25° steeper, pushed out 23, standing on the
  baseline as tall as the capitals. The arms turn about the centre of the point's round end,
  since turned about the tip it splits into two bumps, and each arm takes its own length, as
  the hand-drawn arms differ, so the point stays at mid-height. ❯ is 0.78 as wide as `>` and
  carries 1.43 times its ink, between Cascadia Code's 1.39 and Maple Mono's 1.46.
- ❰ ❱ are built the same way, turned 15° and pushed out 50: as tall as ❯, 1.36 times as wide
  and 1.46 times its ink, so Rich's traceback marker stays apart from the prompt, as in the
  fonts that draw them apart (DejaVu Sans Mono's ❱ 1.39 times its ❯'s ink, JetBrains Mono's
  and Maple Mono's 1.50).
- No symbol comes closer to the cell's edges than `project.SYMBOL_SIDE` (15), so two side by
  side don't touch.
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

- **`a`** is double-storey, after a hand-drawn reference, so it reads apart from `o` and `α`
  at 12 px; the single-storey one blurred into `o` there. Its head rises nearly straight from
  a terminal at 0.87 of the x-height to a tight shoulder, the stem leans out as the old one
  did, and the bowl, a flat oval, leaves the stem at mid-height and rises back into it above
  the baseline. The bowl's top is at 0.59 of the x-height, Fira Code's and Intel One Mono's
  0.60, and its counter 0.33 tall (Intel One Mono 0.31, Fira Code 0.39). It is drawn on two
  centrelines with an elliptical pen 95 wide and 76 tall, `o`'s sides and top. Its top stays
  at 486, the old `a`'s, so å's ring keeps 24 of white. `æ`'s a half is the same centrelines
  at 0.62 across with the old `æ`'s pen (72 × 80), and `ª`'s small a is `a` at 0.55.

## Greek

Greek follows Fira Code and Maple Mono (Intel One Mono has none). Capitals that match Latin
are references to it; the tonos is the acute turned 25° steeper, and beside a capital it
stands to the left, reaching into the cell before (all but Ά) no further than the references'
122 (`tests/test_sanity.py` lists them).

## Placement

- Center symmetric ink in the cell. Make turned glyphs such as ¡ ¿ 180° rotated references,
  rotated about the cell center.
- `tests/test_legibility.py` holds the rules for confusable characters, the colon and
  semicolon, brackets and letter widths; read it before changing them.
- Box-drawing strokes overlap their neighbours: verticals span −485…1035 (they meet up to
  1.5 em line height), horizontals −10…610. Block elements fill the cell and the line box
  exactly, and the Powerline separators do the same.
- Braille's dots stand on an even grid: columns every half cell, rows every quarter of the
  line box, so a graph's dots stand as far apart across cells and lines as inside one. Graphs
  in btop, Rich and UnicodePlots come first; Braille text reads looser than in Maple Mono,
  whose dots stand 1.5 times closer inside a cell across and 3.2 times down.
- `|` stands on the cell's middle, on │'s line, so a table drawn with both meets; ‖ is two `|`.
- `( [ {` span −145…800, 945 tall, within the references' 927–971. The descenders hang 133–152
  below them (`p` −278, `y` −297), where the references leave 17–85, because ours keep Comic
  Shanns' depth (the references' reach −172…−244). The brackets stay: lengthened to the
  descenders, they would stand taller than every reference's and drag `⟨ ⟩` and `/ \` with
  them.
- `/` and `\` reach from −110 to 765: 875 tall, within the references' 867–885, and centred on
  the brackets' middle. Each turned 1.5° steeper about its middle and lengthened along its
  stroke, so it keeps its weight; it spans 503, within Maple Mono's 418 and Intel One Mono's
  520. `//` `/*` keep their pitch through `TIGHT_KEEP` (−41.5), and the `!=` slash, the `/` at
  83 %, stands 726 tall, between Maple Mono's 662 and Fira Code's 786.
- ∄ is ∃ and the `/` turned 6° steeper, so it is no wider than ∃, as Fira Code's and Maple
  Mono's are: 421 against Maple Mono's 420. Its foot stays at Fira Code's −121. A turned part
  can't stay a reference under the italic's shear or the bold's pen, so the italic draws ∄'s
  two parts as outlines and the bold merges them (`make_bold.MERGED`).
- `‘` is the turned comma ģ carries, head down like a 6, moved 77 down to stand level with
  `’`; `“` is two of it and ʻ is it. Drawn as a reversed 9, it read as a misplaced `’`.

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
reads more open. Half-block pixels ▀ ▄ become almost square, 600 × 625. Our letters fill more
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
  `a` 452 and `3` 450. `b` `d` `p` `q` are one width, 441, as each reference draws them at one
  width. `c` (425) and `5` (432) take Fira Code's widths, so `c` keeps in step with `e` and `o`,
  and `5` with `3`, as in the three references. `Q` widens with `O`, to 482. `0`'s slash and
  `e`'s bar turn a little. ø Ø þ ƿ đ ą ę, ρ δ σ ∂ on `o`'s bowl, ç ¢ ς and the accented letters
  follow through references or outline copies.
- **Open letters.** Bars, arms and tails lengthen along their straight part: `f` 460, `t` 441,
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
  run from 31 to 570.
- **Beyond ASCII.** € and Œ open the C and the O at their middle, on the line through their top
  and bottom extremes. ð's bowl opens at its middle, and its rising stroke moves with its right
  side. ß's arch opens at its crown, and ẞ's top bar lengthens. Ħ ħ Ð Đ đ ₽ lengthen their bars
  past the stem, and Ł its bar along its slant. ₺'s tail lengthens along its level bottom, as
  `t`'s does. ¥'s arms turn out about the crotch.
- **Symbols.** `-` lengthens at its middle, to 365. Each arm of `<` `>` turns flatter about the
  centre of the point's round end and lengthens until its end is back at its height, so `<` `>`
  (425) keep their height within a unit. ≤ ≥'s angle widens by 62 the same way, to 446, and the
  bar lengthens with it. `%`'s rings, `"`'s ticks and the parts of `?` `&` move apart, and the
  slash of `%` and ‰ lengthens: `%` and ‰ are 543, `&` 517, `?` 404, `"` 307. `+` − ± ÷ are 463.
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
  keeps its own 174-unit half-waves. `asciitilde.mid` and `.end` are the low pieces mirrored
  about the wave's middle. The crest's profile is a unit thicker than the trough's, so the
  mirror leaves each cut corner a unit off its profile. `snap_edge(level=True)` moves the level
  run that ends at the corner with it. Moving the corner alone leaves a short slant, which the
  bold pen grows into a step of 4 at the crest.
- **The ligatures.** `tools/add_ligatures.py` measures its constants on the widened `-` `<`
  `>` (`TIP`, `ARM_ENDS`, `HYPHEN_SPAN`); `ARM_ENDS` holds the centres of `>`'s round ends,
  and `<`'s are those turned. `longer_angle()` lengthens each arm until its ink reaches the
  height its caller asks: the arrowheads →'s and ←'s, so `->` reads as →, and the heads of
  `|>` `<|` `<|>` a triangle as tall as Fira Code's, centred on the axis. The gains that
  widen `<` `>` into other ligatures shrank as `<` `>` grew 64 wider, so the shapes keep their
  reference sizes: `ANGLE_WIDTH_GAIN` (94) widens the angle of `<=` `>=` to 519, Fira Code's
  1.10 x-heights (Maple Mono's is 1.13), its arms as tall as `<` `>`, and `DIAMOND_WIDTH_GAIN`
  (35) keeps `<>` 1.70 x-heights wide, between Maple Mono's 1.67 and Fira Code's 1.76. `<=`
  is `>=` mirrored, as in Fira Code and Maple Mono: `<` is `>` turned, so each built from its
  own angle, the bar would hang under a different hand-drawn arm and stand the two 9 apart.
- **Seams under light hinting.** FreeType's light autohinter, the default on Linux desktops,
  hints each glyph alone, so the pieces of a ligature meet on one pixel row only where each
  piece's bar rounds the same way. Two things moved a bar a row off. A bar edge that strays
  from its profile toward a cap or a head's point rounds with that stray: `level()` moves
  every point within the wobble of a profile height onto it. And an arm end within reach of
  a zone, which the autohinter aligns first and then places the bar from: → ⇒ and their
  heads reach 21…531 and ← ⇐ 21…527. A lower end at 15 or under, 8 or under in the bold, is
  aligned to the baseline; an upper end at 509 to the x-height; and ← reaching 529 or more
  moves the bars of `<<-` and `<=<`. Measured with freetype-py 2.5.1 (FreeType 2.13.2) at
  8–36 px; `LigatureSeamTest` in `tests/test_built.py` checks every piece. The bold `<=<`
  still steps: its pen grows the tail's arms across the bars a few units off their edges.
- **Alignment zones.** The OTF's hints put the extremes inside one zone on one pixel row, so
  each zone runs from the lowest to the highest of its letters' extremes, the hand's wobble
  included: the baseline −37…−5, the x-height 461…493, the capitals and figures 658…692, the
  ascenders 710…719, and the descenders −297…−268 (`OtherBlues`). The bold's move out by
  half the pen's height, 7, but its baseline zone keeps its top at −5: FreeType pulls that
  flat edge down by up to 0.6 px at small sizes, and from −12 it sank every bold letter a
  row at 9–12 px. Its BlueScale shrinks with that taller zone. `tests/test_metadata.py`
  checks that every style's letters stay inside.
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
  blunt. In the 550 cell it was 1.27 by 0.88. The bar's outer edge stays 295 into its own
  cell, 2 past Fira Code's 293 and 20 past JetBrains Mono's 275 at a 600 cell.
- **`->>`.** `HEAD_PITCH` (375) keeps the white between the two heads at 174, as in the 550
  cell, since the heads kept their size; Fira Code, the one reference that draws `->>`, leaves
  145 at a 600 cell. The inner head's crotch then lies 38 inside its cell, so the shaft's cut
  end at the seam lies on the open shaft, as in `->`. A pitch from 388 to 429 puts the crotch
  onto that cut end, which then shows as a flat, and 432, which kept the inner head where the
  550 cell had it, left 218 between the heads. The bold's pen grows the heads to 147 apart,
  under Fira Code Bold's 155, so there the inner head moves along its shaft until the white is
  Fira Code Bold's (`make_bold.HEADS_APART`); a pitch that wide would take the regular's white
  to 183, past 1.7.0's 173.
- **Tight pairs.** `TIGHT_KEEP` states, for each glyph of a tightened pair (`::` `&&` `++`
  `//` `<<` …), the side bearing it keeps toward its partner, not how far it moves. The white
  between the pair is the sum of the two kept side bearings, so it stays when the cell grows or
  the glyph widens; a shift stated as a number would let the white grow 50 with the cell and
  shrink as `&` `+` `<` `>` `?` widen. `&&` keeps 46 of white, about Maple Mono's 45 (Fira
  Code joins its two); much less, and the two read as touching at 12–16 px. No pair but `++`,
  whose bars join, keeps less than two symbols side by side, twice `SYMBOL_SIDE`
  (`tests/test_ligatures.py`). `///` and `/**` tighten as threes, as `|||` `<<<` do, so a doc
  comment opens as tightly as a plain one.
- **The bold's wide characters.** Moved to the middle of the wider cell, the regular's glyphs
  have 25 more room on each side. So the pen no longer pushes @ # ∞ « » Æ œ K ✔ ➜ past their
  side room, and `fitted()` keeps them at full width, where 1.7.0 condensed them.

Where a glyph stays under the width rule's floor, the reason and the measurement:

- **`2` and `P`.** The regular `2` (436) and `P` (441) are at their floors. The bold `2` is 472,
  8 under Monaspace Neon Bold's 480, and the bold `P` 476, 6 under its 482: within `WOBBLE`.
- **The fractions ⅓ ⅔ ⅕ … ⅞.** They are 571–580. Intel One Mono's fill the cell (600), Fira
  Code's pass it (611–682), and Maple Mono has none. The bold grows a fraction by about 22, so
  a regular wider than about 578 puts the bold past the cell. The bolds are 593–598.
- **¾.** It is 576, 3 under Maple Mono's 579. At 579, the bold ¾ passes the cell.
- **đ and ₫.** đ is 503, 7 under Fira Code's 510, and the bold đ 539, 1 under Monaspace Neon
  Bold's 540. ₫ is 505, 10 under Maple Mono's 515. ₫ holds đ, and in the bold a letter that a
  symbol holds stays within the symbol's `SYMBOL_SIDE`: the bold đ's bar ends at 585.
- **The bold ẞ.** It is 473, 10 under Maple Mono Bold's 483. `NARROW` grows it by 0.7 of the
  pen to keep the white between its stem and diagonal. The regular is 449, over the floor.
- **ŀ.** It is 462 against Fira Code's 562. The references end the dot 104 (Maple Mono), 118
  (Fira Code) and 148 (Intel One Mono) past their `l`, into the next cell, and their bolds
  65–135. Ours ends 18 past and stays in the cell. `tests/test_latin.py` holds the dot past the
  `l` instead.
- **Ą.** It is 499, `A`'s width, against Maple Mono's 527. Maple Mono's and Intel One Mono's
  ogoneks reach 31 and 29 past their `A`, and Fira Code's 0. Only the mark's place sets their
  width.
- **ĵ Ĵ.** ĵ is 395 against Fira Code's 436: the references' circumflex reaches 83 to 122 past
  their `j`, ours 30. Ĵ is 425 against Fira Code's 440: the references' circumflex reaches 16
  (Fira Code), 109 (Maple Mono) and 141 (Intel One Mono) past their `J`, ours 0. Our `J` is at
  Fira Code's floor.
- **˚.** It is 161 against Fira Code's 222. In Å, the ring stands 20 above the apex (678) and
  ends at 849, 51 under the line box's top (900). A round ring 222 wide is 61 taller. It fits
  only with 10 left above the apex and its top at 900, and the bold pen then takes the bold Å
  past the line box.
- **Superscripts and subscripts.** ⁰–⁹ ₀–₉ (207–219) stay against the references' 276–306.
  Monaspace gives them no share of a wider cell (the table above).
- **■ □.** They are 502 against Fira Code's 540. They follow ☐, Intel One Mono's 502, so the
  boxes stay one size.
- **The italic ↦ ⁄.** They slant past the cell, ↦ to −5..579 and ⁄ to −47..664, as Maple Mono
  Italic's do (−53..565 and −73..642).

## Ligatures

The rules live in `src/ligatures.fea`; these are the choices behind them.

- **`===`.** Three bars, as both references and our `!==` draw them, so `==` and `===` differ
  by more than their length. A run of four or more stays one double line.
- **Two `-` or `_`.** A run of exactly two stays as typed: an option (`--help`), a decrement
  (`i--`), an SQL or Lua comment and a Python dunder name (`__init__`) show the characters
  typed. Three or more join into a line, and `<!--` keeps its run.
- **`<=>`.** C++'s, PHP's, Ruby's and Perl's comparison is no arrow, so it tightens as a three,
  as `<$>` does. `<==>` is still an arrow.
- **Beside a name.** `~>` before a version (Ruby's and Terraform's `~> 1.0`) stays plain, and
  so do `/*` `/**` after a name (`src/*`), `*/` before one (cron's `*/5`) and `>>` `>>>` after
  one (`Vec<Vec<u8>>`). With spaces, `a >> b` still tightens; `a>>b` stays plain, the price
  of closing generics as typed.
- **Kept.** `<>` stays a diamond: Java's diamond operator is named for the shape, and SQL's
  `<>` stands for nothing else. `?.` tightens after a name too, as JavaScript's `a?.b` does;
  Rust's `x?.y`, `?` then a field, can't be told apart from it.

## Italic

The italic is the regular sheared, generated by `tools/make_italic.py`; nothing in its SFD is
drawn by hand. The choices, proofed on 2026-09-30 against Maple Mono 7.9, Intel One Mono
1.4.0 and Monaspace 1.400 (Neon and Radon), with the italic reference fonts in
`build/cache/reference/italic/`:

- **12°**, between Maple Mono's 10° and Intel One Mono's 16°, next to Monaspace's 11°. It
  reads as italic at 14 px, and the worst text glyphs leave the cell by about 45 units, as
  the references' do; 10° stayed close to the regular in a comment, and 14° and 16° pushed
  the capitals' tops and the tails further out.
- **One shear for every slanted glyph**, x += (y − 269) × tan 12°, pivoting on the hyphen's
  middle. A stroke at any height moves the same in every glyph, so the ligature pieces still
  meet at the cell seams, `-` `=` and the arrow shafts stay where they are, and the lowercase
  stays centred. Composites keep their references with the matrix conjugated by the shear,
  and anchors move with it, so accents and the mark lookups need nothing of their own.
- **What slants**: letters, figures, the combining marks, punctuation, brackets, quotes,
  currency, superscripts, operators, arrows and the ligatures. Both references slant all of
  these, Maple Mono its arrows included; keeping → upright while `->` slants (Monaspace's
  choice) makes a typed arrow differ from the ligature's head, which the regular built → from.
- **What stays upright**: what is drawn as a picture, which both references leave identical:
  Box Drawing, Block Elements, Braille, Powerline, the geometric shapes and spinner frames,
  the status marks ✓ ✗ ⚠ ℹ, ⏺ ⏵ ⏸ ⎿ ⧉ and �. Two choices go against Maple Mono, which slants
  them: ☐ ☑ ☒ stay upright because ours are squares of the hyphen's stroke like □ ■, and the
  spinner frames ◰ ◱ ◲ ◳ are built on ☐; the white arrows ⇧ ⇪ ⇦ ⇨ ⇩ ⇞ ⇟ and the tab keys ↹ ⇥ ⇤
  stay upright because they are key hints that read beside ⌘ ⌥ ⌃, which Maple Mono lacks.
  • ‣ ∙ stay too, as ◉ ⊙ and ▸ are built on them, and ℹ, which stands beside ⚠.
- **Dots** shear with the letters, as Maple Mono's and Monaspace's do; round dots that only
  move with the slant looked the same at 14 px and would need a special case.
- **Cursive letters**: only f. The regular's single-storey g already reads as an italic
  form. a slants double-storey, as Intel One Mono's and Monaspace's italics keep theirs, so
  a and o stay apart in italic comments; Maple Mono's looped l made "all" and "full" busy at 15 px and turned l into ℓ; a
  plain stem lost the tail that keeps l apart from I and 1. f drops its foot and runs its
  stem 268 below the baseline, as deep as j, ending in a flick 70 left of the stem in the
  stem's own stroke, chosen over ƒ's hook (Maple Mono's f), which reached 72 units left of
  the cell, and over a plain straight descender. The descender takes the stem's width where
  the foot is cut away, 80 above the baseline, and is welded on along that cut (`geo.weld_y`),
  so the joint has no ledge and no overlap for `removeOverlap()` to merge. ƒ keeps its own
  outline.
- The italic's f, and any glyph the shear cannot express (∙ built on the period, ⋮ on the
  ellipsis turned a quarter), is an outline in the italic; everything else keeps the regular's
  structure, references included.

## Bold

The bold is the regular with its strokes grown, generated by `tools/make_bold.py`; nothing in
its SFD is drawn by hand. The choices, proofed on 2026-10-01 against Fira Code 6.2, Intel One
Mono 1.4.0, Maple Mono 7.9 and Monaspace 1.400 (Neon and Radon), with the bold reference fonts
in `build/cache/reference/bold/`:

- **The pen**, an ellipse 35 wide and 14 tall. Each outline is stroked with it, the stroke's
  inner edge dropped, and the rest united with the outline. A stem grows by the pen's width
  and a level stroke by its height, half on each side, so a bold letter keeps the regular's
  rows. Its tops rise by half the pen's height, so the bold declares its own x-height and cap
  height, 480 and 675. In the 550 cell, ink in a–z fills 57.5% of the x-height band, within
  the reference bolds' 51–59%: a step of 13.5 points from the regular's 44.0%, where Maple
  Mono's, the smallest reference step, is 14. There the counters at our x-height, `n` 172,
  `o` 199 and `e` 109, are each at or above the narrowest reference bold's.
- **An offset, not `changeWeight()`.** The offset grows every edge alike, so `-` stays centred
  on the math axis. The ligature pieces grow by the same pen as the `-` `=` `<` `>` `~` `|`
  they continue, so they still match at their seams. A piece's flat cut end past the cell is
  trimmed back to the regular's, so it stays flat and keeps its overlap with the next piece.
  FontForge's `changeWeight()`, in its LCG mode, keeps the letters' heights but grows a level
  stroke upward only: `-`'s top moved from 311 to 341, off the axis, and the `--` pieces
  stopped matching at their seams (351 against 341).
- **Small parts, a smaller pen.** The superscripts, fraction figures and ™'s letters, and the
  parts drawn as light as them (the fraction bar, the ordinals' bar, © ®'s ring), grow by the
  pen scaled by the small `1`'s stem over `1`'s. A bold superscript is then as much bolder as
  a bold letter.
- **What stays as it is**: what is drawn as a picture, which the reference bolds keep as
  their regulars draw it. Box Drawing, Block Elements and the geometric shapes meet their
  neighbours across the cell, and the Powerline symbols fill the line box. Braille's dots draw
  graphs and spinners. Every frame of a spinner stays, so the spinner turns in one place and
  does not pulse; only ‼ grows, as it is two `!`. The media controls ⏵ ⏸ ⏺ stand side by side
  at one height in status lines. □ is ☐ and ■ its outer contour, so ☐ stays with them, and
  ☑ ☒ are ☐ marked, so the three boxes stay alike. These glyphs and .notdef are copied
  unchanged, hints included.
- **Heavy marks** ✔ ✘ ✖ ❯ ❮ ❰ ❱ ➜ grow by the pen scaled by how much heavier the regular
  draws them than ✓ ✗ ✕ > < →, so they stay as much heavier; the full pen would grow the light
  glyphs more for their ink and close the difference. This departs from the reference bolds,
  which keep their heavy marks as their regulars draw them, lighter than their bold light
  marks. Ours read heavier in every weight.
- **The cell.** The pen pushes no ink out of the cell, or past the regular's own overhang
  where it has one (ď, the tonos capitals). No glyph but a letter or figure comes nearer the
  cell's sides than `SYMBOL_SIDE`, or the regular's ink where that is nearer, so two symbols
  side by side keep twice that between them. A glyph that would pass its bound is
  condensed: its outline is scaled across about its ink centre before the offset, just
  enough, so every stem still grows by the full pen. A composite whose part would pass its
  bound moves its references in toward the cell's centre instead.
- **Composites** keep their references, so an accented letter follows its base; a glyph with an
  outline and references has only its outline grown. Two kinds of part are unlinked first. A
  shared glyph's bolder part (∙ on the period) keeps the regular's outline, as in the italic. A
  bolder glyph's part turned a quarter or scaled (⋮ on …, ⇦ ⇨ on ⇧) grows as its own outline,
  since the reference would turn or scale the pen too. A left glyph the regular draws as its
  right one mirrored (⇤ ⇥, ↩ ↪) is the bold right one mirrored, so the two stay exact mirrors.
  An accent the pen grows out of the line box moves down into it (ĥ's circumflex). A mark the
  pen grows within `MARK_CLEARANCE` of its letter rises clear, as far on every letter where it
  stands as high, so a row of them stays level.

Where the pen alone would break a rule the regular keeps, `make_bold.py` names the glyphs and
what it does to them:

- `TURNED`: the tonos, the acute turned 25° steeper, grows by the pen turned with it, so it
  stays the bold acute turned.
- `ROUND`: ª º's bar and ⇪'s bar, drawn as heavy as the stems beside them, grow as much up and
  down as across. The level pen would leave them 21 lighter than the bold stems.
- `NARROW`: ẞ and the small 4 grow by 0.7 and 0.83 of the pen's width. The full pen would
  close ẞ's white between stem and diagonal to 56, under Maple Mono Bold's 65, and the small
  4's counter to 0.128 of its height, under Maple Mono Bold's ¼ (0.136).
- `OUTWARD`: © ®'s ring grows outward only, by the small pen's whole width, so it stays as
  heavy as its letter and the letter keeps its room; grown both ways, it came 35 from ®'s R,
  under Fira Code Bold's 41 around its ©.
- `BLUNT`: ₩ ₦'s bars run 31 to 52 past their letter on both sides. The pen lengthens their
  round ends, which tapers the bars' run clear of the letter, so the bars would reach the
  hyphen's weight only inside it. So the sign keeps its regular box, condensed, and a second
  pen, as tall but a unit wide, is united with the first: the bars' ends keep the regular's
  length and weigh as much as the hyphen. ₱'s bars run 70 left of its P and reach that weight
  there with the pen alone.
- `ACROSS_AS_UP`: ⇕ is ⇔ turned, and the turned pen would grow it past ↑'s height. So ⇕
  grows by the pen as it stands, condensed until it grows across only by the pen's height,
  and stays as wide as ⇔ is tall.
- `MERGED`: Θ is drawn as one outline, each part grown on its own: its bar beside a reference
  to O fails `validate()` once saved (`docs/fontforge-pitfalls.md`).
- `APART`: where the pen grows two parts of a composite into each other, one moves clear,
  just far enough to keep the regular's gap. i j's dots rise; ŀ's dot and the carons of ď ľ Ľ
  move right; the tonos beside a capital moves left; ΅'s dieresis and ª º's bar move down.
  ΐ ΰ's dieresis then sits 29 below ϊ ϋ's, a row break that letters as rare as these may take,
  and ĳ, one outline, keeps its dots 14 lower than i j's.
- `DOUBLES`: both copies of “ ” „ ″ ‖ ‼ move apart, each as far, so the mark stays on the
  cell's middle and keeps the regular's white between its copies.
- `TIGHT`: each glyph of a tightened pair moves back out by half the pen's width, as far as
  the pen grew it toward its partner, so the pair keeps the regular's white. Unmoved, `&&`
  would merge into one shape and `??` keep 9; `++`'s bars keep their overlap.
- `OWN_BOX`: ™'s T and M, and Θ's bar, are condensed to keep their own regular box. ™'s
  letters, 23 apart, would all but touch, and Θ's bar would come 21 from its ring, under the
  reference bolds' 38; it keeps 39.
- `PIECES_APART` and `LIGHT_PIECES`: the pieces of ⇥ ↹ (arrow and bar), ‰ (its zeros) and
  ℃ ℉ № (letter and small pieces) grow on their own, and the wider is condensed away from the
  other until the white between them is the regular's. Each keeps its far end where the pen
  grows it, or at the side room, so the bold ‰ stays at least as wide as the bold % (562): it
  is 570, and centred. The small pieces of ℃ ℉ № grow by the small pen, so they stay as light
  as the small figures; the full pen would close ℃'s ring to 42 across, where the small pen
  leaves 54.
- `SLASHES`: grown, ‰'s slash would come 14 from the zero under it, where the regular keeps
  27. It shortens at its foot until it keeps the regular's white.
- `SHRUNK`: ※'s dots, ⧉'s front square and ⌫ ⌦'s × shrink just enough to keep twice
  `SYMBOL_SIDE` from the piece beside them, where condensing can't part the two.
- `OPENED`: ⎋'s ring opens wider around its arrow; the arrow would have to shrink by a third
  to clear.
- `DASHED`: ⇡ ⇣'s dashes shorten at their top by twice the pen's height, so each gap stays as
  much wider than the stroke as the regular's and stays open at 12 px.
- `LIFTED`: ⇪'s ⇧ is the bold ⇧, lifted as far as the regular lifts it, and a little further
  where the bar comes within twice `SYMBOL_SIDE` of it.
- `RAISED`: Ħ's upper bar moves up its stems by the pen's height, so the white between its
  bars stays the regular's; it would come 81 from the lower bar, under the bold hyphen's 93.
