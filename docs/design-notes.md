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

- ∞ is 8's loop, scaled to fit; every reference draws ∞ lighter than its letters.
- The `*.small` components of superscripts, subscripts, fractions and signs are the regular
  glyph at 0.45 (figures, ⁱ ⁿ and the signs), 0.52 (the small parentheses, which reach past
  the figures as far as the references' do), 0.55 (ª º) or 0.41 (™ © ®), thickened with
  `changeWeight(…, "CJK", …)` (the default picks a method that pushes all the weight down and
  right) so stems measure 54 ± 4, or 56 in ™ © ®; the fraction and ordinal bars are thinned
  to match.
- ▹ is ▷ at 0.61 thinned to a 41 outline, since at the full stroke its counter fills in at
  16 px; ▸ ▴ ▵ ▾ ▿ ◂ ◃ follow it. Its size keeps the white across its middle, 168, above Maple
  Mono's, the only reference's, whose lighter 37 outline leaves 159 at our cap height.
- ▫ (☐ at 0.52) and ◦ (○ at 0.48) are scaled so their rings come out about 41 too.
- ⧉'s squares are the hyphen's stroke at 0.79, so the one behind keeps clear of the one in
  front; ⏺ ⏵ are ● ▶ scaled to ⏸'s height.
- The keyboard symbols ⌘ ⌥ ⌃ ⇧ ⌫ ⌦ ⎋ ⏎ take the same 0.79 stroke, for their detail, so key
  hints such as ⌃⌥⌘⇧ read at one weight.

## Heavy marks and shapes

- Heavy marks (✔ ✘ ✖) are their light glyph (✓ ✗ ✕) pushed out 23 on every side,
  then squeezed at the ends to stay 20 inside the cell; ⏸'s bars are `|` pushed out 40, to
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

## Italic

The italic is the regular sheared, generated by `tools/make_italic.py`; nothing in its SFD is
drawn by hand. The choices, proofed on 2026-09-30 against Maple Mono 7.9, Intel One Mono
1.4.0 and Monaspace 1.400 (Neon and Radon), with the italic reference fonts in
`build/cache/reference/italic/`:

- **12°**, between Maple Mono's 10° and Intel One Mono's 16°, next to Monaspace's 11°. It
  reads as italic at 14 px, and the worst text glyphs leave the cell by about 65 units, as
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
- **Cursive letters**: only f. The regular's single-storey a and g already read as italic
  forms; Maple Mono's looped l made "all" and "full" busy at 15 px and turned l into ℓ; a
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
  height, 480 and 675. Ink in a–z fills 57.5% of the x-height band, within the reference
  bolds' 51–59%. That is a step of 13.5 points from the regular's 44.0%; Maple Mono's, the
  smallest reference step, is 14. The counters at our x-height, `n` 172, `o` 199 and `e` 109,
  are each at or above the narrowest reference bold's.
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
  cell's sides than ●'s side bearing, or the regular's ink where that is nearer, so two
  symbols side by side stay as far apart as ●●. A glyph that would pass its bound is
  condensed: its outline is scaled across about its ink centre before the offset, just
  enough, so every stem still grows by the full pen. A composite whose part would pass its
  bound moves its references in toward the cell's centre instead.
- **Composites** keep their references, so an accented letter follows its base; a glyph with
  an outline and references has only its outline grown. Three kinds of part are unlinked
  first. A shared glyph's bolder part (∙ on the period) keeps the regular's outline, as in the
  italic. A bolder glyph's part turned a quarter or scaled (⋮ on …, ⇦ ⇨ on ⇧) grows as its
  own outline, since the reference would turn or scale the pen too. A letter that a symbol
  holds unmoved (∆'s Δ, ₫'s đ) grows as the symbol's own outline, condensed to the symbol's
  side room, so the letter itself keeps its full width: a letter outranks a rare symbol's
  reference. A left glyph the regular draws as its right one mirrored (⇤ ⇥, ↩ ↪) is the bold
  right one mirrored, so the two stay exact mirrors. An accent the pen grows out of the line
  box moves down into it (ĥ's circumflex). A mark the pen grows within `MARK_CLEARANCE` of its
  letter rises clear, as far on every letter where it stands as high, so a row of them stays
  level.

Where the pen alone would break a rule the regular keeps, `make_bold.py` names the glyphs and
what it does to them:

- `TURNED`: the tonos, the acute turned 25° steeper, grows by the pen turned with it, so it
  stays the bold acute turned.
- `ROUND`: ª º's bar and ⇪'s bar, drawn as heavy as the stems beside them, grow as much up and
  down as across. The level pen would leave them 21 lighter than the bold stems.
- `NARROW`: ẞ and the small 4 grow by 0.7 and 0.83 of the pen's width. The full pen would
  close ẞ's white between stem and diagonal to 56, under Maple Mono Bold's 65, and the small
  4's counter to 0.128 of its height, under Maple Mono Bold's ¼ (0.137).
- `OUTWARD` and `SCALED`: © ®'s ring grows outward only, by the small pen's whole width, so it
  stays as heavy as its letter and the letter keeps its room; grown both ways, it came 35 from ®'s R,
  under Fira Code Bold's 41 around its ©. It comes 8 from the cell's edges, as Fira Code
  Bold's © does. The ring and its letter scale together about the ring's middle: condensed
  alone, the ring would come out lighter than C and close on the letter.
- `BLUNT`: ₩ ₦ ₱'s bars run past their letter out to the side room. The pen lengthens their
  round ends, and the side room takes that length back, so the bars would reach the hyphen's
  weight only inside the letter. A second pen, as tall but a unit wide, is united with the
  first, so the bars' ends keep the regular's length and weigh as much as the hyphen.
- `ACROSS_AS_UP`: ⇕ is ⇔ turned, and the turned pen would grow it past ↑'s height. So ⇕
  grows by the pen as it stands, condensed until it grows across only by the pen's height,
  and stays as wide as ⇔ is tall.
- `MERGED`: Θ and ∀ are drawn as one outline, each part grown on its own. Θ's bar beside a
  reference to O fails `validate()` once saved (`docs/fontforge-pitfalls.md`), and ∀'s turned
  A would grow past ∀'s side room on both sides.
- `APART`: where the pen grows two parts of a composite into each other, one moves clear,
  just far enough to keep the regular's gap. i j's dots rise; ŀ's dot and the carons of ď ľ Ľ
  move right; the tonos beside a capital moves left; ΅'s dieresis and ª º's bar move down.
  ΐ ΰ's dieresis then sits 29 below ϊ ϋ's, a row break that letters as rare as these may take,
  and ĳ, one outline, keeps its dots 14 lower than i j's.
- `DOUBLES`: both copies of “ ” „ ″ ‖ ‼ move apart, each as far, so the mark stays on the
  cell's middle and keeps the regular's white between its copies.
- `OWN_BOX`: ™'s T and M, and Θ's bar, are condensed to keep their own regular box. ™'s
  letters, 23 apart, would all but touch, and Θ's bar would come 21 from its ring, under the
  reference bolds' 35; it keeps 39.
- `PIECES_APART` and `LIGHT_PIECES`: the pieces of ⇥ ↹ (arrow and bar), ‰ (its zeros) and
  ℃ ℉ № (letter and small pieces) grow on their own, and the wider is condensed away from the
  other until the white between them is the regular's. The small pieces of ℃ ℉ № grow by the
  small pen, so ℃'s ring stays clear of its C and №'s o of its bar.
- `SLASHES`: grown, ‰'s slash would come 14 from the zero under it, where the regular keeps
  27. It shortens at its foot until it keeps the regular's white.
- `SHRUNK`: ※'s dots, ⧉'s front square and ⌫ ⌦'s × shrink just enough to keep ●●'s seam
  from the piece beside them, where condensing can't part the two.
- `OPENED`: ⎋'s ring opens wider around its arrow; the arrow would have to shrink by a third
  to clear.
- `DASHED`: ⇡ ⇣'s dashes shorten at their top by twice the pen's height, so each gap stays as
  much wider than the stroke as the regular's and stays open at 12 px.
- `LIFTED`: ⇪'s ⇧ is the bold ⇧, lifted as far as the regular lifts it, and a little further
  where the bar comes within ●●'s seam.
- `RAISED`: Ħ's upper bar moves up its stems by the pen's height, so the white between its
  bars stays the regular's; it would come 81 from the lower bar, under the bold hyphen's 93.
