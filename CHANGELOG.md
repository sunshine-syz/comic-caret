# Changelog

## 2.0.2 (unreleased)

- The outer characters of a pulled-together three, as in `...`, `///`, `&&&`, `<<<`, `>>>` and `|||`, move in twice as far as a pair's. So a three keeps the white of its pair: `0..=n` reads like `0..n`, and `///` like `//`. `..=`, `..<`, `<<=`, `>>=`, `=<<`, `&&=`, `||=` and `??=` do the same on their doubled side. In the bold, a three keeps the regular's white, as a pair does.
- `/**` opens as `/*` does, and its two asterisks stand as far apart as in a plain `**`, in the regular and the bold. They stood half as far apart. Every Javadoc and JSDoc comment opens with it.
- `..` is pulled together in a slice and beside a quote or a bracket, as in `&s[..n]`, `&s[1..]`, `[1..]`, `'a'..'z'`, `Foo { ..x }` and `p()..q`, as it already was in `0..n`. In a path, as in `../`, `cd ..` and `"../.."`, and in Python's relative imports, as in `from .. import` and `from ..models import`, it stays as typed. So does `...` in `from ... import`, which was pulled together.
- Erlang's and Elixir's binaries open as typed, as they close: `<<1, 2, 3>>`, `<<"abc">>`. So does a heredoc, as in `cat <<EOF`, as `<<-EOF` already did, and so do a shell's here-string and PHP's heredoc, as in `<<<"$x"` and `<<<EOT`. A shift is still pulled together, as in `x<<1`, `cout<<x` and `a << b`. `>>` after a quote stays as typed, as it closes `<<"abc">>`.
- The rings of `%` and `‰` have larger holes in every style. No hole is smaller than the smallest reference font's. At 16 to 20 px, `%` showed two small loops on a long slash. The rings stand further out in the corners, so they keep their white to the slash. In the bold, the rings of `%` shrink a little to keep it.
- In the bold, `|` is as heavy as the stems of the letters beside it, as in the reference bolds. It was lighter than every letter's stem, so `||` read thin beside `I|l`. `‖`, the pulled-together `||` and `|||`, and the ticks of `₿` follow. The ticks of `₿` stand further apart, so they keep the regular's white and don't merge.
- `¦` is `|` broken in two, in every style: each piece is as heavy as `|` and has its round ends. Its pieces were a quarter heavier than `|`.
- `|` stands inside the brackets and is centred on them, as in every reference. Its foot hung 30 units below `(`, `[` and `{`, as in `[a|b]` and `{|x| x}`. `¦` and `‖` follow.
- The leg of `₹` ends level with the leg of `R`, in every style. It ended 42 units below the baseline, so at 20 to 24 px its foot showed a pixel under the figures, as in `₹1,250`. The leg keeps its slope and its weight.
- The solid Powerline separators `` and `` run a little into the segment they end, as the Nerd Fonts patcher's round separators do. Where a terminal rounds the cell to whole pixels, a light column showed between a segment and its separator, as at 13 and 16 px.
- The block elements, as `█` `▀` `▄` `▌` `▐` and the quadrants, run a little past the cell and the line box. Where a terminal rounds the cell or the line to whole pixels, light rows and columns showed between stacked blocks, as at 13 to 16 px. The shades `░` `▒` `▓` stay within the cell, so their pattern tiles. Terminals that draw blocks themselves, such as Ghostty and kitty, draw them as before.
- The box-drawing lines across the cell, as `─` `━` `═` and the arms of `┌` `┬` `├`, run a little further into the next cell, as in Intel One Mono and Maple Mono. Where a terminal rounds the cell up to whole pixels, a light notch showed at every seam of a line, as at 11, 16 and 21 px. `╱` `╲` `╳` follow. Terminals that draw box drawing themselves, such as Ghostty and kitty, draw these lines as before.
- The dashed vertical lines `╎` `┆` `┊` `╏` `┇` `┋` end in half a dash at the top and the bottom of the line, and run on into the next line. Where lines stand further apart than the font's own 1.25 em, as 1.5 em, a longer dash marks where two lines meet; a long gap broke the dashes there. At 1.25 em they keep their rhythm. Terminals that draw box drawing themselves, such as Ghostty and kitty, draw them as before.
- `<` and `>` stand in the middle of the cell, as `≤` `≥` do and as in Fira Code and Maple Mono, so `a < b` lines up with `a ≤ b`. Each stood 6.5 units toward its point. The ligatures built on them, as `->` `=>` `->>` `~>` `<<` `<!--`, follow. `→` and `⇒` are `←` and `⇐` mirrored, so the two heads of `<->` and `<==>` stand level: `→` reached 4 units higher than `←`.
- The points of `<=` `>=` and the corners of `<>` turn as round as the point of `>`. Each showed a short flat with a small step on either side, at large sizes.
- In the TTF, each glyph's box is the box of its points. `V`, `∄`, `⏵` and `⏺` had one a unit too large, so tools that measure the points, as the Nerd Fonts patcher does, gave them other extents than ours.

## 2.0.1 (2026-10)

- `x<-1` no longer shows an arrow. A digit after `<-` makes it a minus sign: x is less than −1. `x<-y`, `a <- b` and `<-ch` keep the arrow, as in JetBrains Mono and Maple Mono.
- `===` draws three bars, as `!==` does and as Fira Code and Maple Mono draw it. So `==` and `===` differ by more than their length. It keeps its bars beside another operator, as in `a===-1`. A run of four or more `=` stays one double line, and so does `+===+`, a table's border.
- The two characters of `&&` no longer touch. They keep about as much white between them as Maple Mono's. In the bold, every pulled-together pair keeps the regular's white, so the bold `&&` no longer merges into one shape and the bold `??` stays apart. The two hooks of `??` keep as much white between them as Maple Mono's, about twice as much as before.
- `///` and `/**` are pulled together like `//` and `/*`, so a doc comment opens as tightly as a plain one. So are `//!`, `/*!`, `///<` and `/**<`, which open Rust's and Doxygen's doc comments.
- `..` between two names or numbers, a range, is pulled together, as `..=`, `..<` and `...` are. So `0..n` and `0..=n` look alike. In a path, as in `../` and `cd ..`, it stays as typed.
- The bar of the `<=` and `>=` ligatures stands further from the arm above it, as far as in Maple Mono. In the 12 px bold, `<=` no longer reads as `<`.
- `?:` stays as typed after a TypeScript property name, as in `name?: T` and `[K]?: T`. Where it is an operator, as in `a ?: b` and `(?:x)`, it is still pulled together.
- The dot of `?` stands further from its hook, as far as in Maple Mono, in the regular and the bold. At 12 px the bold dot no longer joins the hook. ¿ follows.
- `!` is as tall as `?`, at the cap height, and its stem ends higher above the dot. At 12 px the dot no longer joins the stem, in the regular and the bold. ¡ and ‼ follow.
- `a` is double-storey, so it no longer reads as `o` or `α` at small sizes. Its head rises nearly straight to the stem, and its bowl is a flat oval, as wide as `o`. The italic slants it, as Intel One Mono's and Monaspace's italics do. à á â ã ä å ā ă ą æ ª follow.
- `G` no longer reads as `6`. Its bar starts at the middle of the letter, and its right side rises straight up to the bar, as in Monaspace Radon. So `16GB` and `LOG6` read right in every style. Its stroke keeps its weight where the bowl turns up into the right side. Ĝ Ğ Ġ Ģ follow.
- The top of `A` stands in the middle of the cell, and its legs slope alike, as in Fira Code, Maple Mono and Intel One Mono. The accented letters, Α and ∀ follow.
- The upper bowl of `8` and both bowls of `B` are wider, as wide as in Intel One Mono, Fira Code and Maple Mono. The bowl of `d` is as wide as Maple Mono's, and `b` `p` `q` widen with it, so the four stay one width. Their strokes keep their weight.
- On Linux, where FreeType's light hinting is the default, the pieces of `->`, `<-`, `=>`, `-->`, `<==>`, `---` and the other arrows and lines meet on one pixel row in the TTF at every size from 8 to 36 px. Their shafts stepped by a pixel at 14 to 21 px. The bars of the pieces are level, and the lower arms of → ← ⇒ ⇐ and their heads end a little higher. The bold `<=<`'s right end still steps at some sizes.
- The TTF is hinted, by ttfautohint. Where a renderer runs the font's own hints, as FreeType's full and monochrome hinting on Linux do, the TTF was drawn unhinted. There `=` blurred into one grey band at 11 px, letters stood a pixel row off their neighbours, and without antialiasing `8` read as `B`. Linux's default light hinting and macOS draw as before.
- ↑ ↓ ⇑ ⇓ ⇞ ⇟ have the heads of → and ⇒, so an arrow up or down is as big as one along the line. The diagonal arrows ↖ ↗ ↘ ↙ have longer shafts.
- In the OTF, the capitals and figures stand on one pixel row at small sizes, and so do the lowercase letters, in every style. Each style carried the regular's alignment zones, which missed the tops of `A` `C` `E` `G` `L` `M` `N` `S`, the figures and `c` `m` `w`, and every top of the bold. So at 16 px `E` and `T` stood a row above `H`, and the bold's capitals and lowercase letters split into two rows at 13 to 22 px. Every letter whose top or foot reaches an alignment zone carries a hint there, so the bold `E` `Ę` and `U`, the italic `z` `ź` `ż` `ž` and the Greek capitals stand on their neighbours' row too. `Λ` stands 5 units lower, on the baseline as `A` does.
- The dots of Braille stand on an even grid, as far apart inside a character as across characters and lines. So a graph drawn in Braille, as btop and UnicodePlots draw them, no longer breaks into stripes.
- The leg of ₹ runs down to the right, and its bowl turns back under the bar, as in Fira Code, Maple Mono and Intel One Mono.
- `/` and `\` are taller and a little steeper. They are as tall as in Fira Code, Maple Mono and Intel One Mono, and their strokes keep their weight. `//` and `/*` keep their spacing, and the slash of `!=` keeps its size.
- The bars of `=` stand further apart, as far as in Intel One Mono. At 8 px, where FreeType runs the font's own hints, they no longer merge into one band, in any style or format. ≡ ≠ ⇒ ⇐ ⇔ ⇑ ⇓ ⇕ and the ligatures drawn with `=`'s bars, such as `==`, `!=` and `=>`, follow.
- The slash of ∄ is the `/` turned 6° steeper, so ∄ is no wider than ∃, as in Fira Code and Maple Mono.
- `|` stands in the middle of the cell, on the line of `│`, so a table drawn with both lines up. ‖ follows.
- `‘` and `“` are `’` and `”` mirrored exactly, so each pair stands level and leans toward the quoted word. ʻ follows.
- The fonts carry their version as 2.001, in the head table and in the names, so fontconfig and font managers tell 2.0.1 from 2.0.0. Both carried 2.0 in the head table. The release and its zips keep the name 2.0.1.
- Two `-` or two `_` stay as typed, as in `--help`, `i--`, `-- comment` and `__init__`. Three or more still join into a line, and `<!--` keeps its line.
- `<=>` is pulled together as a comparison, as in C++, PHP, Ruby and Perl, and no longer draws an arrow. `<==>` is still an arrow.
- `~>` stays as typed before a version, as in Ruby's and Terraform's `~> 1.0`.
- Pairs beside a name stay as typed where they are no operator: `/*` after one, as in `src/*`, `*/` before one, as in the cron step `*/5`, and `>>` or `>>>` after one, as generics close in `Vec<Vec<u8>>`. A shift is still pulled together: with spaces, as in `a >> b`, and without, where a name or a number follows, as in `cin>>n`, `x>>1` and `a>>>0`.
- `||=`, `&&=`, `??=` and `>>>=` are pulled together, as `<<=` and `>>=` already were. So `x ??= 1` reads like `a ?? b`, as in Fira Code and Maple Mono.
- `::` is pulled together before `<`, `*`, `-` and `~`, as in Rust's `collect::<Vec<_>>()` and `use std::*;`, C++'s `Foo::~Foo()` and Python's `a[::-1]`, and after a `>` before a name, as in `Vec::<u8>::new()` and `vector<int>::iterator`. So `a[::-1]` reads like `a[::2]`.
- `...` is pulled together after a `>`, as in a usage line's `<FILE>...`, as it already was after `]`.
- `!=`, `!==`, `:=`, `<=`, `>=`, `<>`, `&&`, `||`, `??`, `?.` and `?:` keep their ligature before a minus or a not, as in `x!=-1`, `x<=-1` and `a&&!b`, as `x==-1` already did.

## 2.0.0 (2026-10)

- Every character is 600 units wide, up from 550, at the same letter height. Most coding fonts are 600 to 620 wide, but their letters are bigger too. The cell is now 1.27 times the x-height, between Source Code Pro's 1.26 and Intel One Mono's 1.32, where 1.7.0's was 1.16. So text reads more open.
- At the same font size, a line holds 8% fewer characters. Lower the size by about one point to keep a terminal's column count. In ComicCaret Nerd Font, the Powerline separators fill the wider cell, and the widest icons, such as the weather icons, grow with it by up to 9%. The other icons, 97% of them, keep their size.
- Letters and figures that the wider cell left narrow are wider. Their strokes lengthen or move apart, and none is scaled, so every stroke keeps its weight.
  - `o` `O` `Q` `0` `e` `g` `a` `b` `d` `p` `q` `c` `3` `5`, `f` `t` `r` `T` `m` `l` `w` `W` `n` `h` `u` `4` `J` `Æ`, and ß ẞ ð Œ Ħ ħ Ł Ð Đ are at least as wide as the narrowest of Fira Code, Maple Mono and Intel One Mono.
  - π γ ε ζ ι κ α β Ξ ϗ ĸ Ĳ are at least as wide as the narrower of Fira Code and Maple Mono. Intel One Mono has none of them.
  - `n` `h` `u` are one width.
  - đ widens as far as ₫ leaves room in the bold.
  - The accented letters and the letters drawn on these follow them, such as ø þ ç µ μ η ρ σ τ.
  - `M` `W` `w` are redrawn after Intel One Mono. The middle of `M` no longer reaches the baseline, nor the middle of `W` and `w` the top. So `M` reads apart from `N` and `H`, and `W` and `w` apart from a row of upright strokes. ₩ and the accented `W` and `w` follow them.
- Symbols, dashes and arrows grow with the cell.
  - `-` `<` `>` `%` `&` `?` `"` `+` − ± ÷ ≤ ≥ – — … € ₺ ¥ ₽ ⁄ are at least as wide as the narrowest of the three reference fonts.
  - ‰ is as wide as Fira Code's, its rings further apart. ₩'s bars run as far out as the cell leaves room for, so ₩ is about as wide as Intel One Mono's.
  - `<` and `>` keep their height, their round point and their point on the math axis.
  - Every arrow along the axis, → ← ↔ ⇒ ⇐ ⇔ ↦ ⇤ ⇥, is one length. The shafts are longer, and the heads stay as they are.
  - ❯ ❮ ❱ ❰ widen with `>`, so a prompt's ❯ still reads apart from `>`, and ❱ apart from ❯.
  - ∞'s loops are taller, so its holes are as tall as Maple Mono's.
  - The two copies of ″ “ ” „ ‖ stand further apart, so the white between them stays at least as wide as the narrowest reference font's.
  - The fractions ¼ ½ ¾ ⅓ … ⅞ are wider. Their figures stand further apart.
- Marks and shapes grow with the cell.
  - ¨ ° • are at least as wide as the narrowest of the three reference fonts. ¨'s dots stand further apart on every letter that carries them.
  - ○ ● are larger and still circles. So "○ main" doesn't read as "o main", nor "A = ∅" as "A = ø". ◯ ◉ ∅ and the spinner frames drawn on ○ ● follow them.
  - ☐ ☑ ☒ are at least as wide as Intel One Mono's, and ■ □ are as large as ☐. The spinner frames drawn on them follow them, such as ◰ ▮ ▰.
  - The bars of ☰ … ☷ stand further apart, so they still span as much of ○'s height as Fira Code's do. ⏺ stays at ⏸'s height.
  - ŀ's dot now ends past the `l`, as in the reference fonts.
- The ligatures follow the wider characters.
  - A `~~~` run has longer waves. Each half-wave is a third of the cell, and no flat shows where two cells meet.
  - The heads of `|>` `<|` `<|>` are as large as Fira Code's and JetBrains Mono's, and centred on the math axis.
  - `<=` `>=` and `<>` keep their size, which matches the reference fonts, while `<` and `>` widen. `<=` is `>=` mirrored, as in Fira Code and Maple Mono, so the two stand at one height.
  - The heads of `->` `=>` `<-` and the other arrow ligatures stay as tall as → and ←. So `->` still reads as →.
  - The inner head of `->>` and `<<-` moves out with the outer one. So the seam between the shaft's two cells lies on the plain shaft, as in `->`.
- The bold grows with the cell.
  - Wide characters such as @ # ∞ « » Æ œ K ✔ ➜ keep their full width, where 1.7.0 condensed them to fit its cell.
  - ‰ is at least as wide as `%`.
  - The two heads of `->>` and `<<-` stand at least as far apart as Fira Code Bold's.
  - A `~~~` run meets at every seam without a step. In 1.7.0, the crest's inner edge stepped 3 units where two pieces met.

## 1.7.0 (2026-10)

- A bold, Comic Caret Bold, in the same zips as the regular and the italic and in the Nerd Font zip.
  - Editors and terminals that set text in bold now use it. Before, they thickened the regular themselves.
  - It is the regular drawn with a heavier pen. Stems are 35 units heavier, and level strokes 14 units heavier. So `-` stays on the line of `=` and the arrows, the ligatures keep joining across cells, and every character keeps its cell.
  - Ink fills 57.5% of the x-height band in a–z. The regular fills 44.0%, and the bolds of Fira Code, Intel One Mono, Maple Mono and Monaspace fill 51–59%. The counters of `n`, `o` and `e` stay at least as open as the narrowest of theirs.
  - Letters, digits, marks, punctuation, symbols, arrows and the ligatures grow heavier.
  - Box drawing, block elements, the shapes, Braille, the Powerline symbols, the spinner frames, the media controls ⏵ ⏸ ⏺ and the checkboxes ☐ ☑ ☒ keep the regular's weight, as the reference bolds keep theirs. So borders, tables and progress bars look the same in both weights, and a spinner doesn't pulse.
  - The heavy marks ✔ ✘ ✖ ❯ ➜ grow with the text and stay heavier than ✓ ✗ ✕ > →. The reference bolds keep their heavy marks as their regulars draw them. So in those bolds, the heavy marks are lighter than the light marks.
  - There is no bold italic. An app that asks for one still makes its own.
  - `tools/make_bold.py` generates the bold's source from the regular's.
- R's bowl narrowed toward its top right, so the white inside it, 211 units across at three quarters of the cap height, was narrower than in any of the three reference fonts (Maple Mono's, the narrowest, is 245 at the same letter height). The bowl's shoulder is now filled out, keeping R's own stroke, leg and join, and leaves 255; Ŕ Ř Ŗ follow it.
- The white inside ▹ was 2 units narrower than in Maple Mono's, the only reference font with ▹. ▹ is now 3% larger, its outline as heavy as before, leaving 9 more than Maple Mono's; ▸ ◃ ◂ ▵ ▴ ▿ ▾ ‣, which are built on it, grow with it.
- Seven characters sat outside the range the three reference fonts cover, and now sit within it, each keeping its own strokes:
  - ¬ was larger than any reference's (456 × 289 to their 338–366 × 190–207), its bar high above the hyphen. It is now 350 × 203, its bar on the hyphen's line, as Fira Code's is.
  - ¦ stopped short of `|` at both ends. It now runs as far as `|`, as in Fira Code and Maple Mono, broken in the middle by a gap as tall as theirs.
  - × is 30 units smaller each way, 385 × 369 (the references are 321–400 wide), so it stands further apart from `x`, and ✗ stands as far above it as Maple Mono's does.
  - ¢ sat 100 units above the baseline, its c 40 units wider than `c` and its stroke reaching 783, above the capitals. It is now `c` itself on the baseline, its stroke running from −148 to 640, within the references' reach.
  - ∂'s hook rose to 703, above `6` and the capitals; it now tops out at 676, as Fira Code's does, below `6`.
  - The spacing ogonek ˛ sat 28 units right of the cell's middle and is now centered, as in the references; the combining ogonek (U+0328) and ą ę į ų are unchanged.
  - The Braille patterns sat 14 units right of the cell's middle; the grid is now centered, as Maple Mono's is.
- Three gaps were narrower than the reference fonts leave them, and are now as open as theirs:
  - ✗ stood 83 units under X's top, near enough to read as a capital at text sizes. It now stands 100 under, as Maple Mono's, the only reference with ✗, does; ✘ moves with it.
  - The bars under ª and º came within 70 units of their letters. They now leave 90, as Intel One Mono's do.
  - “ ” „ left about 60 units between their marks at mid-height, where all three references leave 100 or more. Each mark now stands about 20 units further out, leaving 104.
- → ← ⇒ ⇐ were nearly all head: the head stood 578 units tall and its arms swept back over all but 85 units of the shaft. Each arm now turns 8° steeper, to about Fira Code's slope, so the head stands 516 tall and the shaft shows more than twice as long, 184. The arrow ligatures `->` `=>` `<-` `->>` `~>` `>=>` and `<!--` take the same head, so → beside `->` still reads as the same arrow.
- `<` and `>` are 24 units shorter, 506 tall, their arms shortened along their own lines, so the arrowheads stay taller than them; `<=` `>=` `<>` follow them. `|>` `<|` `<|>` keep their size.
- ❯ ❮ were a heavier `>`, squat and wider than `>`, where every coding font that draws them (JetBrains Mono, Cascadia Code, Maple Mono, DejaVu Sans Mono, Menlo, Iosevka) draws a tall angle ornament. They now stand on the baseline as tall as the capitals, about four fifths as wide as `>` and still heavier, so a prompt's ❯ reads apart from `>`.
- ❰ ❱, which Rich marks a traceback's failing line with, were two strokes standing taller than the old ❯, from below the baseline; beside the new ❯ they would read alike. They are now the same tall angle drawn wider and heavier, as in the fonts that draw the two apart: 1.36 times ❯'s width and 1.46 times its ink.
- ď's caron ran 94 units into the next cell, crowding the letter after it. `d` now sits 25 units left inside ď, as in Fira Code and Maple Mono, and the caron is a shorter tick, 154 units tall instead of 230, its top where it was, so it runs 40 past the cell, within the references' 9 to 93. ľ Ľ ť share the caron and take the shorter tick too.

## 1.6.5 (2026-10)

- Releases no longer include ComicCaret Nerd Font Mono; the Nerd Font zip holds only the default ComicCaret Nerd Font (Regular and Italic, OTF and TTF). For icons shrunk to one cell, build it from source with `./build.sh --nerd=mono`.
- ☐'s hints in the OTFs counted stems it didn't have and left its top stroke unhinted, as in □ ◰ ◱ ◲ ◳ ⧆ ⧇, which are built on it; FontForge warned whenever it opened them. All of them are now hinted in full.
- The PANOSE classification, which said only that the font is monospaced, now describes the rest of its design: a rounded sans of book weight with no stroke contrast and a large x-height, the italic as its oblique form, so systems that pick a substitute font by PANOSE find a closer one.
- The plain fonts' unique ID (name ID 3) names the release, as `1.6.5;NONE;ComicCaret-Regular`, the form fontmake gives it, where FontForge's held a date.
- `a>--b` and `x>->y` no longer draw a `--` line or a `->` arrow after the `>`: a `-` right after a `>` joins only as `-->`, which closes a comment, as in `<!--<a href="x">-->`, unless the `>` closes a short tag (no attributes, a name of up to 10 letters and digits) such as `<code>`, `</p>` or `<br/>`, so `<code>--help</code>`, `</p>--->` and `<a>->` join as before.
- A wave arrow followed by another operator now loses its `<` head too, not only its `>` one, at any length: `<~>=` and `<~>>` are plain, as `~>=` and `~>>` are, and `<~~>=` keeps only the `~~` that `~~>=` draws.
- The italic's tab keys ↹ ⇥ ⇤ stay upright, like the other key hints ⌘ ⌥ ⌃ ⇧, instead of slanting.
- Ĉ's circumflex sat 22 units right of where Ć Ċ Č center their accents, and î's 20 units left of where ï ĩ ī put theirs, over the place of i's dot. Both now sit with the rest, where a combining circumflex (U+0302) after `C` or `ı` lands too, so the two draw the same Ĉ and î where nothing composes them; each of the three reference fonts places Ĉ's mark as it does Ċ's and Č's, and keeps î's over the dot's place.
- Þ's stem rose 88 units above the other capitals, with the bowl high on it. The stem now stops at the cap height and the bowl is centered on it, as Fira Code, Intel One Mono and Maple Mono draw theirs, so it still reads apart from P.
- “ ” „ set one of their marks about 50 units higher than the other, a handwritten touch. Both marks now stand level, at the height of the single ‘ ’ and the comma, as all three reference fonts keep them, with at least as much white between them as the narrowest reference's, and ”'s left mark is ’ itself rather than a near copy of it.
- The soft hyphen (U+00AD) drew a hyphen, which shaping renderers never show and which Alacritty, giving it no cell, drew over the letter before it; it is now blank and still one cell wide, for the terminals that reserve a cell for it, so nothing strikes through a letter, and Font Bakery no longer reports its outline. Intel One Mono and Maple Mono leave it unmapped; Fira Code draws a hyphen.
- Y's stem ran on down the slant of the right arm, so its foot stood 96 units left of the notch and the letter leaned; it now stands upright under the notch, as in all three reference fonts, and the notch sits 22 units higher, within the range they cover.
- J was the I with a hook: its bar ran 114 units past the stem on the right, the stem stood near the middle of the cell, and the hook rose to a third of the cap height from 28 units off the cell's left edge. The bar now runs left of the stem only, as Fira Code's and Maple Mono's does (Intel One Mono's J has none), the stem stands in the right third of the cell under a round top, where all three set it, and the hook, widened to reach it, starts 45 units in and ends no higher than Intel One Mono's.

## 1.6.0 (2026-09)

- An italic, Comic Caret Italic, in the same zips as the regular and in both Nerd Font editions, so editors and terminals no longer slant the regular themselves. It is the regular slanted 12°, between Maple Mono's 10° and Intel One Mono's 16°, about the line of `-` `=` and the arrows, so the ligatures keep joining across cells and every character keeps its cell. Letters, digits, marks, punctuation, currency, operators and arrows slant, as in both references; box drawing, block elements, Braille, the Powerline symbols, the shapes and spinner frames, the status marks ✓ ✗ ⚠ ℹ, the checkboxes ☐ ☑ ☒ and the key hints ⌘ ⌥ ⌃ ⇧ stay upright. `f` gets a descender as deep as `j`'s, ending in a short flick to the left, in the font's own stroke; the other letters keep their shapes, since the regular's single-storey `a` and `g` already read as italic forms. `tools/make_italic.py` generates the italic's source from the regular's.
- The `<=` and `>=` ligatures hung below the line: their angle kept the height of `<` `>` and the bar went under it, so in `a >= 3` the symbol sat lower than the text around it. They are now centered on the line of `-` `=` and the arrows, as ≤ ≥ and the other ligatures are and as Fira Code and Maple Mono draw theirs, with the angle raised above `<` `>` and the bar reaching below the baseline.

## 1.5.0 (2026-09)

- `^` `~` `_` `%` and `°`, which everyone types, sat outside the range the three reference fonts cover:
  - `^` is narrower and lower, its top level with Fira Code's; it reached almost to the top of the line.
  - `~` swings less, as the references' do, and stays centered on the line of `-` `=` and the arrows; ≈, the `~~` runs and the `~>` wave arrows follow it.
  - `_` sits 15 units lower, where Intel One Mono draws it; ␣ ⍽ and the `__` runs go with it.
  - `%`'s slash no longer dips below its rings.
  - ° is a larger, open ring, lower and centered; its counter closed up at small sizes.
- The basic Powerline symbols (U+E0A0–E0A2 and U+E0B0–E0B3: the branch, line number and padlock, and the solid and thin separators) in the plain font, so Powerlevel10k, Starship, vim-airline and tmux prompts no longer need the Nerd Font edition or fall back to another font. The separators fill the cell and the line box, so a prompt's colored segments meet them without a seam; the thin ones take the box drawing stroke, and the branch, line number and padlock are drawn from the font's own strokes and letters. The Nerd Font editions keep them.
- The currency signs ₹ ₺ ₽ ₩ ₫, drawn from the font's own letters and the hyphen's stroke: ₽ is `P` with a bar, ₩ is `W` with two, ₫ is `đ` with a bar under it, ₺ is `t` with two rising bars in place of its crossbar, and ₹ is two bars over a small bowl with a long leg, the shape the three reference fonts agree on. With them the dash and bullet look-alikes ‣ ‐ ‑ ‒ ― that Markdown and copied text carry, as ▸, the hyphen, the en dash and the em dash.
- The currency signs ₦ ₱ ₿: ₦ is `N` with ₩'s two bars, ₱ is `P` with two bars through its bowl where Intel One Mono puts them, and ₿ is `B` with two ticks of `|`'s stroke through its top and bottom, as Maple Mono draws it.
- The modifier letters ʼ ʻ ʺ, which fell back to another font: ʼ (the apostrophe of Ukrainian and of many African and romanized languages) is ’, ʻ (the Hawaiian ʻokina) is ‘, and ʺ is ″, as the reference fonts that have them draw them.
- The letterlike symbols № ℓ ℮ ℃ ℉: № is a narrowed `N` with º beside it, ℓ is a looped l in the font's hand, ℮ is `e` enlarged with its bar run out to the left, and ℃ ℉ are a small ° before a reduced `C` and `F`, set as Maple Mono sets them.
- The fractions ⅓ ⅔ ⅕ ⅖ ⅗ ⅘ ⅙ ⅚ ⅛ ⅜ ⅝ ⅞, built like ½ ¼ ¾ from the small figures the superscripts use: their figures stand where ½'s do and the slash keeps ½'s clearances.
- The key hints ⇞ ⇟ ⇪ ⇦ ⇨ ⇩ (page up and down, caps lock, and the white arrows that pair with ⇧): ⇦ ⇨ ⇩ are ⇧ turned, ⇪ is ⇧ over a bar, and ⇞ ⇟ are ↑ ↓ with two bars across the shaft.
- The spinner frames of cli-spinners, which Rich, ora, yaspin, Textual and Ink animate: the halves, quarters, arcs and corner cuts of ○ and ☐ (◐ ◑ ◒ ◓, ◴ ◵ ◶ ◷, ◜ ◝ ◞ ◟ ◠ ◡, ◰ ◱ ◲ ◳, ◢ ◣ ◤ ◥, ▮ ▯), the rings ◎ ⦾ ⦿ ⧇ ⧆ ⊙ ∙ ◌ ◍, the trigrams ☰ ☱ ☲ ☳ ☴ ☵ ☶ ☷, the stars ✷ ✸ ✹ ✺, ⊶ ⊷, ☖ ☗, ▰ ▱ and ‼, cut, stacked and turned from the font's own ○ ● ☐ ■ ◦ ✶ `*` and `!`, so the frames of one spinner share a center and size and the animation stands still.
- The spaces that copied text carries, so they no longer show as missing: the thin space and narrow no-break space (a cell each, blank), and the zero-width space, non-joiner and joiner, word joiner and byte order mark (blank and zero wide, like the combining marks, so they take no cell).

## 1.2.0 (2026-09)

- More coding ligatures, drawn in the font's hand from its own `<` `>` `-` `=` `~` `|`:
  - `<>` as a diamond, and `<|>` as the triangles of `<|` and `|>` sharing one bar.
  - `>=>` and `<=<`, Haskell's fish operators, as double arrows with a tail.
  - Arrows with two heads, `->>` and `<<-` (Clojure's thread-last, R's `<<-`), at any length: `-->>`, `<<-->>`. A shell heredoc's `<<-EOF` stays plain.
  - Wave arrows of any length, `~>` `<~` `~~>` `<~>`, for Elixir's and Ruby's version requirements and Scala's `<~`.
  - `<!--` with its `<` drawn as an arrowhead, like the one `-->` already had, and the `!` centered between the arrow and the line, also right after a tag or another comment: `</p><!--`, `--><!--`.
  - `?.` and `?:` pulled together, and threes pulled in from both ends: `<<<` `>>>` `|||` `&&&` `>>=` `<<=` `=<<` `<$>` `<*>` and Rust's and Swift's ranges `..=` `..<`.
- ẞ (U+1E9E), the capital ß: a stem that curves into a flat top like ß's, then a diagonal down to a round bowl, the shape most fonts give it.
- Combining accents (U+0300–U+0304, U+0306–U+0308, U+030A–U+030C, U+0326–U+0328), for decomposed text such as macOS file names and the output of tools that normalize to NFD, which fell back to another font. A letter and its accent show as the precomposed letter, so e followed by U+0301 is the same é as U+00E9. On other letters the accent sits where the font's own accented letters carry it, and i and j drop their dot under it. Terminals that draw accents without shaping text put them over the letter too. With these, the font has all of Google Fonts' Latin Core.
- Symbols that terminal UIs print, which fell back to another font:
  - Claude Code's ⏺ ⎿ ⏵ ⏸ ⧉ ∴ ※ and its spinner ✢ ✳ ✶ ✻ ✽, whose frames share one center and size so it turns without pulsing.
  - ■ □ ▪ ▫ ◦ ◯, for Starship and nested lists; ◦ stands where • does, and ▪ ▫ are small like ▸ ▹.
  - ❰ ❱, which Rich marks a traceback's failing line with, taller and narrower than the prompt's ❯ so the two don't look alike.
  - ⎯, which Vitest draws its dividers with: a row of them joins into the same line as `----`.
- Keyboard, whitespace and return symbols:
  - ⌘ ⌥ ⌃ ⇧ ⌫ ⌦ ⎋ ⏎ for key hints, in one height and one weight, so ⌃⌥⌘⇧ reads evenly.
  - ␣ ⍽ ↵ ⇥ ⏎ for the visible whitespace of VS Code, JetBrains IDEs, Vim and Helix; ␣ and ⍽ lie where `_` does.
  - ↳ ↰ ↱ ↲ ↩ ↪ ⇤ ↹ for outlines, key hints and Vim's `showbreak`, built on the font's own → and ←.
  - ⇑ ⇓, completing the double arrows.
- Greek: the whole alphabet, Α–Ω and α–ω with ς, the accented letters ά έ ή ί ό ύ ώ Ά Έ Ή Ί Ό Ύ Ώ ϊ ϋ ΐ ΰ Ϊ Ϋ, the punctuation and numeral signs · ; ʹ ͵ ΄ ΅, and ϗ Ϗ: all of Google Fonts' Greek Core, for identifiers such as `θ` and `Δt` in Julia, Python, Lean and Agda, math in comments, and Greek text. Only λ and Λ were there before. The capitals that look like Latin ones are the Latin letters, and the rest are drawn in the font's hand, many from its own strokes: η is n with a descender, ι is ı's flag on l's tail, κ is k cut to the x-height, τ is t without its top. The tonos stands steeper than the acute, and beside a capital it stands to the left; beside all but Ά it reaches into the space before the word, no further than in Fira Code and Maple Mono. Also Ω (U+2126, the ohm sign), drawn as Ω.
- Superscripts and subscripts: ⁰ ⁴–⁹ ⁱ ⁿ ⁺ ⁻ ⁼ ⁽ ⁾ join ¹ ² ³, and ₀–₉ ₊ ₋ ₌ ₍ ₎ are new, for units and formulas in comments (m², CO₂, x₁, 10⁻³), footnotes, and the numbered box titles of btop (¹cpu to ⁴proc). They are the font's own figures and signs made small, at the weight of ¹ ² ³, and each subscript is its superscript lowered.
- Math symbols: ∂ ∆ ∇ ∏ ∑ √ ∫ ◊ ∅ ′ ″ ‖ ⟨ ⟩, for math in comments and Markdown, Lean's anonymous constructors `⟨a, b⟩`, and names such as `∂x` and `∇f`. ∆ is Δ and ∇ is ∆ turned over, ∏ and ∑ are Π and Σ made taller to reach below the baseline, ∫ and ⟨ ⟩ are as tall as the brackets, and ∅ is the wide ○ struck through, so it doesn't read as ø.
- Arrows such as `-->` and `=>` keep their head right before an HTML or JSX tag, as in `--><p>`, `--></div>` and `x=><li>`. Before, any `<` right after an arrow undid it. A commented-out element keeps both its ligatures too: in `<!--<div>-->` the `<!--` stays before the tag, and the `-->` joins after the tag's `>`.
- → ← ⇒ ⇐ take the heads of the `->` and `=>` ligatures, so a typed arrow beside one reads as the same arrow; they were two-thirds its size, and smaller than in every reference. ↔ ⇔ ↦ and the diagonal arrows keep their smaller heads: two full-size heads, or a head and a bar, don't fit one cell.
- λ stops at the ascender line with b, d and the other Greek ascenders; it rose 78 above them.
- • is the size of Maple Mono's, the smallest reference's (it was smaller still), and sits on the math axis as the references' do, with ◦ beside it; ◉'s dot keeps clear of its ring.
- The Nerd Font editions keep the font's Braille patterns. The patcher replaced all of them with its own square dots, so Braille spinners looked different there.

## 1.1.0 (2026-09)

- All of Box Drawing and Block Elements (U+2500–U+259F), so `tree`, `cargo tree`, `rich` tables and panels, TUI borders, progress bars and graphs no longer fall back to another font:
  - Heavy, double and dashed lines, junctions such as ├ ┼ ┳ ╋ ╬, rounded corners ╭ ╮ ╯ ╰, half lines such as ╴ ╸, diagonals ╱ ╲ ╳, and every mix of light, heavy and double lines. Lines meet their neighbours flush in every combination, and dashes stay evenly spaced from one cell to the next.
  - █ ▀ ▄ ▌ ▐, the eighths ▁–▇ and ▏–▉, the quadrants ▖–▟ and the shades ░ ▒ ▓. They fill the cell and the 1.25 em line exactly, so neighbouring blocks meet without a seam, and the shades' dot patterns run on across cells.
- ━ ┃ ┏ ┓ ┗ ┛, the dashed lines ┄ ┅ ┆ ┇ ┈ ┉ ┊ ┋ and corners that mix weights, such as ┍ ┎, were drawn as plain light lines, so `pip` and `rich` progress bars and `rich`'s default table showed thin solid lines instead of heavy or dashed ones.
- The Nerd Font edition now uses these glyphs too. Before, the Nerd Fonts patcher replaced the whole set with its own, because the font lacked part of it, and its boxes opened up at line spacings above 1.25 em.
- Symbols for prompts and CLI output, so they no longer fall back to another font: the prompt characters ❯ ❮ (Starship, Pure, Powerlevel10k) and ➜ (oh-my-zsh), Starship's git arrows ⇡ ⇣ ⇕, the status marks ✔ ✕ ✖ ✘ ⚠ ℹ of `log-symbols`, npm, yarn and Jest, the dots and pointers ● ○ ◉ ◆ ◇ ▶ ▷ ▸ ▹ ► of lazygit, fzf and tmux with the same triangles pointing the other ways (◀ ▲ ▼ ▾ and the rest) for file trees, ★ ☆, the task boxes ☐ ☑ ☒, and ⋯ ⋮. They are drawn in the font's hand: ✔ ✘ ✖ ❯ ➜ are ✓ ✗ ✕ > → drawn heavier, the black shapes are the white ones filled in, and the shapes sit on the same center line as - and →. The Nerd Font edition keeps these ❯ ❮ instead of the patcher's.
- ↑ ↓ ↕ are taller, to match the new ⇡ ⇣ ⇕, whose dashed shafts need the room.
- @ is redrawn by hand. The a inside is larger and its stem rises into the loop, which swings round it and ends in a tail under the stem, so `user@host` stays open at small sizes.

## 1.0.0 (2026-09)

The first release of Comic Caret. It starts from Comic Shanns Mono 1.3.0, and these are the changes since then.

**Coming from Comic Shanns Mono?** Comic Caret has its own family name, so the two can be installed side by side. Choose "Comic Caret" in your editor and terminal settings.

- Coding ligatures: arrows of any length (`->` `<==>` `--->`), continuous `==` `--` `__` `##` `~~`, `!=` `!==` `<=` `>=` drawn as ≠ ≢ ⩽ ⩾, `:=`, `|>` `<|`, and `::` `...` `&&` `++` `//` `/*` `*/` `<<` `>>` `??` `||` pulled together. Every character keeps its own cell. They use the `calt` feature, which most terminals turn on by default; the README lists how to turn them on or off in common editors and terminals.
- Easier on the eyes in long sessions, after Intel One Mono's legibility work, keeping the hand-drawn style:
  - `l` ends in a tail, so it no longer looks like `1`. The dots of `i` and `j` sit higher, level with the tops of `l` and `d`, and the slash of `0` runs through the middle of its counter.
  - `:` and `;` use full-size dots and reach from the baseline to the top of the lowercase letters.
  - Parentheses, brackets and braces are taller and easier to tell apart: `( )` curve more, `[ ]` have shorter arms, and `{ }` have arms that bow out and a long point.
  - Letters that crowded their neighbors are narrower, with the same stroke weight: n h u d s B D E F H I J K L N R U Z 1 5 7 8. `d`, `q` and `J` sit a little further left, as in most fonts, and `P` a little further right.
  - The bowl of `5` ends lower, leaving it open so it is easier to tell from `6`, and the top of `G` ends sooner.
  - The dots of `÷` stand clear of its bar.
- A Nerd Fonts edition with icons comes with each release: "ComicCaret Nerd Font", and "ComicCaret Nerd Font Mono", whose icons fit one cell, both as OTF and TTF. The icons keep their own licenses, listed in `ICON-LICENSES.txt` in its zip. `./build.sh --nerd` builds them from source.
- Fixed misdrawn characters. ģ's comma stuck out of the top of the line and looked like an acute accent; it is now a turned comma, head down. Ƿ looked like P; it now has the pointed bowl of ƿ. ‚ looked like ‘ at the top of the line. − sat higher than + and =. The commas under Ș ș Ț ț Ķ ķ Ļ ļ Ņ ņ Ŗ ŗ Ģ were full-size commas hanging far below their letters; they are now smaller and stay inside the line. The circumflexes on ĥ and Û sat too high. ¿ was mirrored, with its curve facing the wrong way.
- ¡ and ¿ now start at the height of the lowercase letters and hang below the baseline, as in most fonts. ‹ › « » are centered in their cells and no taller than the lowercase letters, and » no longer sticks out to the left. ‚ „ … and œ are centered too; œ reached into the next character.
- Added the characters that complete Western, Central European, Baltic and Turkish text (the Windows code pages 1252, 1250, 1257 and 1254) and the rest of Latin Extended-A: ß Ø ø Ð ð Ł ł Ľ ľ Đ đ Ħ ħ Ĳ ĳ Ŀ ŀ Ŋ ŋ Ŧ ŧ ĸ Ţ ţ, the soft hyphen, § © ® ª º ¹ ² ³ µ ¶ · ½ ¾ ƒ ‰ ™. Also the no-break space (U+00A0), „, λ, Λ and Ꝛ.
- Added symbols for code and terminal output: ≠ ≈ ≡ ∞, the arrows ↔ ↕ ↖ ↗ ↘ ↙ ⇐ ⇒ ⇔ ↦, the check marks ✓ ✗ and the replacement character � (U+FFFD).
- ¼ has a diagonal slash, like the new ½ and ¾, instead of a stacked bar.
- Carons were upside down and looked like small circumflexes. ď and ť now use an apostrophe-like mark instead of a caron.
- Every glyph is exactly 550 units wide. .notdef, the accented i and n letters, λ, ┐ and the Braille block were off the grid.
- Cleaned up the outlines: self-intersections, reversed contours and missing extreme points are fixed in every glyph except ∄.
- Line spacing is now 1.25 em in every app. Windows used 1.73 em, macOS and browsers 1.2 em, and apps that ignored the old line gap (GTK apps, for example) 1.0 em. Letters sit lower in the line than they did on macOS, so tall letters such as `l` `f` `H` no longer crowd the top of the cursor, selections or a highlighted line.
- Box-drawing lines are straight and line up with each other, and they run a little past their cells so boxes stay closed at line spacings up to 1.5 em.
- < > ≤ ≥ ← → × and ~ now sit on the same center line as - = +, so `->`, `<=`, `x<1` and `=~` line up. < > and ≤ ≥ are smaller, closer to the size of +.
- Accents are flatter and the same size on capital and lowercase letters, as in most fonts, so À Â Č Ő Å and the rest fit inside the line and are no longer cut off in terminals. The standalone accents ´ ˆ ˇ ˘ ˜ ˚ ˙ ˝ match them and are centered in their cells.
- The ogonek (Ą ą Ę ę Į į Ų ų) curls back under the point where it joins its letter, as in most fonts, and no longer sticks out of Ą and ą into the next character.
- The font now sets its underline and strikethrough positions and thicknesses (the thicknesses were 0), and its PANOSE data marks it as monospaced.
- Corrected the font's metadata. Its code-page and Unicode-block flags are now computed from the characters it contains, so it declares only the blocks and code pages it covers. Its copyright notice and `LICENSE.md` list every copyright holder, and its name records give its maker and home page.
- The TTF turns on dropout control and ClearType symmetric smoothing, for better rendering on Windows.
- Old Mac-only name records are gone, and building the same source twice now gives identical files.
- Every outline point now sits on a whole font unit. With the other cleanups, both font files are about half the size of Comic Shanns Mono 1.3.0's.

## Origins

Comic Caret continues [Comic Shanns Mono](https://github.com/jesusmgg/comic-shanns-mono) (2020–2024) by Jesús González and contributors, a monospaced version of Shannon Miwa's [Comic Shanns](https://github.com/shannpersand/comic-shanns) (2018). Their releases up to Comic Shanns Mono 1.3.0 are described in the Comic Shanns Mono repository.
