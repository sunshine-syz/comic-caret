# Changelog

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
- A Nerd Fonts edition with icons comes with each release: "ComicCaret Nerd Font", and "ComicCaret Nerd Font Mono", whose icons fit one cell, both as OTF and TTF. `./build.sh --nerd` builds them from source.
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
