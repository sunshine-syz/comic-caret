# Changelog

## 1.0.0 (2026-09)
- Renamed the font to **Comic Caret** (files `ComicCaret-Regular.{otf,ttf}`), so it no longer shares a family name with Comic Shanns Mono and both can be installed side by side. Update your editor and terminal font settings to the new name.
- Coding ligatures, on by default: arrows of any length (`->` `<==>` `--->`), continuous `==` `--` `__` `##` `~~`, `!=` `!==` `<=` `>=` drawn as ≠ ≢ ⩽ ⩾, `:=`, `|>` `<|`, and `::` `...` `&&` `++` `//` `/*` `*/` `<<` `>>` `??` `||` pulled together. Every character keeps its own cell. They use the `calt` feature; the README lists how to turn them on or off in common editors and terminals.
- Easier on the eyes in long sessions, after Intel One Mono's legibility work, keeping the hand-drawn style:
  - `l` ends in a tail, so it no longer looks like `1`. The dots of `i` and `j` sit higher, level with the tops of `l` and `d`, and the slash of `0` runs through the middle of its counter.
  - `:` and `;` use full-size dots and reach from the baseline to the top of the lowercase letters.
  - Parentheses, brackets and braces are taller and easier to tell apart: `( )` curve more, `[ ]` have shorter arms, and `{ }` have arms that bow out and a long point.
  - Letters that crowded their neighbors are narrower, with the same stroke weight: n h u d s B D E F H I J K L N R U Z 1 5 7 8. `d`, `q` and `J` sit a little further left, as in most fonts.
- The family name no longer ends in "-Regular", and the font now reports its real version (it said 1.3.0, or 0 in the `head` table).
- `./build.sh --nerd` builds Nerd Fonts patched copies, "ComicCaret Nerd Font", as OTF and TTF; prebuilt copies are in `build/nerd/`. `--nerd=mono` builds "ComicCaret Nerd Font Mono", whose icons fit one cell.
- Fixed misdrawn characters. ‚ looked like ‘ at the top of the line. − sat higher than + and =. The commas under Ș ș Ț ț Ķ ķ Ļ ļ Ņ ņ Ŗ ŗ Ģ were full-size commas hanging far below their letters; they are now smaller and stay inside the line. The circumflexes on ĥ and Û sat too high. ¿ was mirrored, with its curve facing the wrong way.
- ¡ and ¿ now start at the height of the lowercase letters and hang below the baseline, as in most fonts. ‹ › « » are centered in their cells and no taller than the lowercase letters, and » no longer sticks out to the left. ‚ „ and œ are centered too; œ reached into the next character.
- Added the no-break space (U+00A0), „, λ, Λ and Ꝛ.
- Carons were upside down and looked like small circumflexes. ď and ť now use an apostrophe-like mark instead of a caron.
- Every glyph is exactly 550 units wide. .notdef, the accented i and n letters, λ, ┐ and the Braille block were off the grid.
- Cleaned up the outlines: self-intersections, reversed contours and missing extreme points are fixed in every glyph except ∄.
- Line spacing is now 1.25 em in every app. Windows used 1.73 em, macOS and browsers 1.2 em, and apps that ignored the old line gap (GTK apps, for example) 1.0 em. Letters sit lower in the line than they did on macOS, so tall letters such as `l` `f` `H` no longer crowd the top of the cursor, selections or a highlighted line.
- Box-drawing lines are straight and line up with each other, and they run a little past their cells so boxes stay closed at line spacings up to 1.5 em.
- < > ≤ ≥ ← → × and ~ now sit on the same center line as - = +, so `->`, `<=`, `x<1` and `=~` line up. < > and ≤ ≥ are smaller, closer to the size of +.
- Accents are flatter and the same size on capital and lowercase letters, as in most fonts, so À Â Č Ő Å and the rest fit inside the line and are no longer cut off in terminals. The standalone accents ´ ˆ ˇ ˘ ˜ ˚ ˙ ˝ match them and are centered in their cells.
- The ogonek (Ą ą Ę ę Į į Ų ų) curls back under the point where it joins its letter, as in most fonts, and no longer sticks out of Ą and ą into the next character.
- The font now sets its underline and strikethrough positions and thicknesses (the thicknesses were 0), and its PANOSE data marks it as monospaced.
- Corrected the font's metadata. Its code-page and Unicode-block flags are now computed from the characters it contains: it declares the blocks it covers and no longer claims the Central European code page (cp1250). Its copyright notice and `LICENSE.md` list all five copyright holders.
- The TTF turns on dropout control and ClearType symmetric smoothing, for better rendering on Windows.
- Old Mac-only name records are gone, and building the same source twice now gives identical files.
- Every outline point now sits on a whole font unit. With the other cleanups, both font files are about half the size they were in 1.3.0.

## 1.3.0 (2023-03)
- Added additional characters, like ƿ and ∃.

## 2023-02
- Added Braille characters (⢩ ⢪ ⢫ ⢬ ⢯ ⢿ ⣁ ⣂ ⣃ ⣇ ⠿ ⠾ ⠪⠘), usually used for progress indicators in terminals.

## 2023-01
- Added simple box drawing characters.
- Removed obsolete versions. Updating the Condensed version is still in consideration.
- Completely separating this fork from the original from now on.

## 2022
- This version has fixed glyphs so that all of them are properly monospaced now.
- Also added a more condensed version.

## 2020
- Added terrible accents
- Some math characters
- Adjusted horizontal metrics
- otf and ttf version
