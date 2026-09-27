<p align="center">
  <img src="docs/images/logo.png" width="160" alt="Comic Caret, hand-lettered over a terminal window with lines of code, beside a smiling green caret with arms and legs, among stars, squiggles and a heart">
</p>

<p align="center">
  A casual monospaced font for code and terminals, in the spirit of Comic Sans,<br>
  and made to stay readable through a long day of work.
</p>

<p align="center">
  <b><a href="https://github.com/sunshine-syz/comic-caret/releases/latest">Download the latest release</a></b> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="https://github.com/sunshine-syz/comic-caret/issues">Report a problem</a>
</p>

<p align="center">
  <img src="docs/images/specimen.svg" alt="A large Aa beside the alphabet, digits, look-alike characters, accented letters and symbols, above a terminal with a prompt, a spinner, a progress bar, status marks and a table">
</p>

## Why Comic Caret

- **Friendly, on a strict grid.** Round stroke ends and a slight wobble, but every character is
  the same width and lines are 1.25 em apart, so columns and boxes line up.
- **Look-alikes look different.** `l` ends in a tail, `0` has a slash, the dots of `i` and `j`
  sit high, `:` and `;` are full size, and `( )` `[ ]` `{ }` each have their own shape. These
  choices follow Intel One Mono, which was designed with low-vision developers.
- **Ligatures that keep the grid.** `->` `=>` `!=` `>=` and more join into one symbol, but
  every character keeps its own cell, so the cursor still moves one character at a time.
- **Ready for terminals.** Every box-drawing and block character and all 256 Braille patterns,
  for borders, trees, tables, progress bars, spinners and graphs, plus a
  [Nerd Font edition](#nerd-font-edition) with icons.

<p align="center">
  <img src="docs/images/lookalikes.svg" alt="The look-alikes, large: I l 1 and the bar, O 0 and o, i and j, the colon and semicolon, and the three pairs of brackets">
</p>

## Install

1. Download `ComicCaret-<version>.zip` from the
   [latest release](https://github.com/sunshine-syz/comic-caret/releases/latest). For icons,
   take `ComicCaretNerdFont-<version>.zip` instead.
2. Install one of the two font files; they hold the same font. On Windows take the TTF, which
   carries rendering settings for ClearType; on macOS and Linux either works.
   - macOS: double-click the file, then click **Install**.
   - Windows: right-click the file, then choose **Install**.
   - Linux: copy the file to `~/.local/share/fonts/`, then run `fc-cache -f`.
3. Choose **Comic Caret** in your editor or terminal, for example
   `"editor.fontFamily": "Comic Caret"` in VS Code.

**Coming from Comic Shanns Mono?** Comic Caret has its own family name, so the two can stay
installed side by side; choose Comic Caret in your settings. The
[1.0.0 notes](CHANGELOG.md#100-2026-09) list everything that changed.

## Ligatures

Comic Caret joins common coding sequences into one symbol. Every character still takes its
own cell, so columns line up and the cursor moves one character at a time.

<p align="center">
  <img src="docs/images/ligatures.svg" alt="Arrows, comparisons, lines, pipes, tags and pulled-together pairs, each drawn as a ligature above the characters typed for it, then TypeScript code that uses them">
</p>

- Arrows of any length: `->` `<-` `<->` `=>` `<==` `<=>` `--->` `<====>`, with two heads
  (`->>` `<<-`) or a wave (`~>` `<~` `~~>`), and `>=>` `<=<` with a tail
- Continuous lines of any length: `==` `--` `__` `##` `~~`
- `!=` `!==` as ≠ ≢, `<=` `>=` as ⩽ ⩾, and `:=` with the colon centered on the `=`
- `|>` `<|` `<|>` as triangles, `<>` as a diamond, and `<!--` with an arrowhead like `-->`'s
- Pulled together: `::` `...` `&&` `++` `//` `/*` `*/` `<<` `>>` `??` `||` `?.` `?:`, and
  `<<<` `>>>` `|||` `&&&` `>>=` `<<=` `=<<` `<$>` `<*>` `..=` `..<`

Sequences that run into other operators stay as separate characters, for example `->>>`,
`<<<-`, `==<`, `<<==` or `https://`.

The ligatures use the `calt` (contextual alternates) OpenType feature:

| App | On | Off |
|---|---|---|
| VS Code | `"editor.fontLigatures": true` | `false` (the default) |
| JetBrains IDEs | Settings → Editor → Font → Enable ligatures | Clear it (the default) |
| iTerm2 | Settings → Profiles → Text → Use ligatures | Clear it (the default) |
| kitty | On by default | `disable_ligatures always` |
| WezTerm | On by default | `harfbuzz_features = { 'calt=0' }` |
| Ghostty | On by default | `font-feature = -calt` |
| Windows Terminal | On by default | `"font": { "features": { "calt": 0 } }` in the profile |

## Nerd Font edition

`ComicCaretNerdFont-<version>.zip` adds the [Nerd Fonts](https://www.nerdfonts.com/) icons
(Powerline symbols, file-type, Git and OS icons). It holds two families; install the OTF or
the TTF of the one you want:

| Family | Icons |
|---|---|
| ComicCaret Nerd Font | Full size; wide icons overhang into the next cell |
| ComicCaret Nerd Font Mono | Shrunk to fit one cell, for terminals that clip wider glyphs |

Both install alongside plain Comic Caret and keep its ligatures. The icons come from the icon
sets Nerd Fonts collects and keep their own licenses, such as CC BY 4.0, Apache 2.0 and OFL
1.1; `ICON-LICENSES.txt` in the zip lists them.

## Character set

| Block | Coverage |
|---|---|
| **Latin** | Complete: Basic Latin (ASCII), Latin-1 Supplement, Latin Extended-A (all but the deprecated ŉ) and Google Fonts' Latin Core, so Western, Central European, Baltic and Turkish text, with ẞ and the combining accents that decomposed text such as macOS file names needs. |
| **Greek** | Complete: Google Fonts' Greek Core, for modern Greek text and the letters math and code use as names (θ Δt λ). |
| **Box Drawing, Block Elements, Braille** | Complete, for borders, trees, tables, progress bars, spinners and graphs. |
| **Symbols** | In part: the arrows, math signs and currency code tends to use (← ⇒ ↕ ≠ ≈ ≡ ≤ ∞ ∑ ∫ √ ∂ ∇ ⟨ ⟩ € £), superscript and subscript figures and signs (m² 10⁻³ CO₂), the check marks ✓ ✗ and �, the prompt and status symbols of shells and CLI tools (❯ ➜ ⇡ ✔ ✖ ⚠ ● ▶ ☐), those of terminal UIs such as Claude Code, Rich and Vitest (⏺︎ ⎿ ✻ ⏸︎ ❱ ⎯), key hints (⌘ ⌥ ⌃ ⇧ ⏎) and editors' visible whitespace (␣ ↵ ⇥). |
| **Cyrillic** | Not yet. |

## Building from source

You need [FontForge](https://fontforge.org/) (`brew install fontforge` on macOS). The Nerd Fonts
builds also need `curl` and `unzip`, and the tests need HarfBuzz (`hb-shape`, `hb-view`). The
Font Bakery test runs it through [`uv`](https://docs.astral.sh/uv/)'s `uvx`, which fetches it
the first time, and skips without `uvx`.

```sh
./build.sh                          # fonts/ComicCaret-Regular.otf and .ttf
./build.sh --nerd                   # also ComicCaret Nerd Font in build/nerd/
./build.sh --nerd=default,mono      # ... and ComicCaret Nerd Font Mono
./build.sh --release                # both release zips in dist/, from a clean checkout
python3 -m unittest discover tests  # after building
```

The source is `src/ComicCaret-Regular.sfd`; edit it in FontForge. The ligatures, combining
marks and box drawing are generated by the scripts in `tools/`, so change them there and rerun
the script rather than editing their glyphs. [CLAUDE.md](CLAUDE.md) lists the rules the source
follows and the checks to run after changing it.

## Credits

Comic Caret is based on [Comic Shanns Mono](https://github.com/jesusmgg/comic-shanns-mono) by
Jesús González, with contributions from Rodrigo Batista de Moraes, Fini Jastrow, Kyle Beechly
and others. Comic Shanns Mono is a monospaced version of Shannon Miwa's
[Comic Shanns](https://github.com/shannpersand/comic-shanns).

Glyph sizes and positions were measured against
[Fira Code](https://github.com/tonsky/FiraCode),
[Maple Mono](https://github.com/subframe7536/maple-font) and
[Intel One Mono](https://github.com/intel/intel-one-mono); no outlines were copied from them.

## License

MIT; see [LICENSE.md](LICENSE.md). The icons in the [Nerd Font edition](#nerd-font-edition)
keep their own licenses.
