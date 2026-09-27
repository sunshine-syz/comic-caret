# Changelog

## 1.2.0 (unreleased)

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
- Greek: the whole alphabet, Α–Ω and α–ω with ς, the accented letters ά έ ή ί ό ύ ώ Ά Έ Ή Ί Ό Ύ Ώ ϊ ϋ ΐ ΰ Ϊ Ϋ, the punctuation and numeral signs · ; ʹ ͵ ΄ ΅, and ϗ Ϗ: all of Google Fonts' Greek Core, for identifiers such as `θ` and `Δt` in Julia, Python, Lean and Agda, math in comments, and Greek text. Only λ and Λ were there before. The capitals that look like Latin ones are the Latin letters, and the rest are drawn in the font's hand, many from its own strokes: η is n with a descender, ι is ı's flag on l's tail, κ is k cut to the x-height, τ is t without its top. The tonos stands steeper than the acute, and beside a capital it hangs into the space before the word, as in most coding fonts. Also Ω (U+2126, the ohm sign), drawn as Ω.
- Superscripts and subscripts: ⁰ ⁴–⁹ ⁱ ⁿ ⁺ ⁻ ⁼ ⁽ ⁾ join ¹ ² ³, and ₀–₉ ₊ ₋ ₌ ₍ ₎ are new, for units and formulas in comments (m², CO₂, x₁, 10⁻³), footnotes, and the numbered box titles of btop (¹cpu to ⁴proc). They are the font's own figures and signs made small, at the weight of ¹ ² ³, and each subscript is its superscript lowered.
- Math symbols: ∂ ∆ ∇ ∏ ∑ √ ∫ ◊ ∅ ′ ″ ‖ ⟨ ⟩, for math in comments and Markdown, Lean's anonymous constructors `⟨a, b⟩`, and names such as `∂x` and `∇f`. ∆ is Δ and ∇ is ∆ turned over, ∏ and ∑ are Π and Σ made taller to reach below the baseline, ∫ and ⟨ ⟩ are as tall as the brackets, and ∅ is the wide ○ struck through, so it doesn't read as ø.
- Arrows such as `-->` and `=>` keep their head right before an HTML or JSX tag, as in `--><p>`, `--></div>` and `x=><li>`. Before, any `<` right after an arrow undid it.

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
