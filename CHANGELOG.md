# Changelog

## 2.0.0 (2026-09)
- Renamed the font to **Comic Caret** (files `ComicCaret-Regular.{otf,ttf}`), so it no longer shares a family name with Comic Shanns Mono and both can be installed side by side. Update your editor and terminal font settings to the new name.
- The family name no longer ends in "-Regular", and the font now reports its real version (it said 1.3.0, or 0 in the `head` table).
- `./build.sh --nerd` builds a Nerd Fonts patched copy, "ComicCaret Nerd Font Mono".
- Fixed misdrawn characters. ‚ looked like ‘ at the top of the line. − sat higher than + and =. The commas under Ș ș Ț ț Ķ ķ Ļ ļ Ņ ņ Ŗ ŗ Ģ hung far below their letters. The circumflex on ĥ sat too high.
- Added the no-break space (U+00A0) and „.
- Line spacing is now 1.2 em in every app. Windows used 1.73 em, and apps that ignored the old line gap (GTK apps, for example) used 1.0 em. macOS and browsers keep the same line height, but the extra space is now split evenly above and below the text.
- Box-drawing lines now end at the edges of the line instead of reaching into the lines above and below.
- The font now sets its underline and strikethrough positions and thicknesses (the thicknesses were 0), and its PANOSE data marks it as monospaced.

## 1.3.0 (2023-03)
- Added additional characters, like ƿ and ∃.

## 2023-02
- Added Braille characters (⢩ ⢪ ⢫ ⢬ ⢯ ⢿ ⣁ ⣂ ⣃ ⣇ ⠿ ⠾ ⠪⠘), usually used for progress indicators in terminals.

## 2023-01
- Added simple box drawing characters.
- Removed obsolete versions. Updating the Condensed version is still in consideration.
- Completely separating this fork from the original from now on.

## 2022
- Check the version in the mono folder.
- This version has fixed glyphs so that all of them are properly monospaced now.
- Also added a more condensed version.

## 2020
- Added terrible accents
- Some math characters
- Adjusted horizontal metrics
- otf and ttf version
