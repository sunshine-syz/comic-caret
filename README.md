# What it is

Are you the kind of person that uses Comic Sans in presentations? Do you lie awake every night dreaming about a world where you could write your code in Comic Sans where it looks just as beautiful as on your dear presentations? Wait no more! I present to you **Comic Caret**! The Comic Sans inspired monospaced font that's coming to a terminal or editor near you!

Comic Caret is a fork of [Comic Shanns Mono](https://github.com/jesusmgg/comic-shanns-mono) by Jesús González, which grew out of Shannon Miwa's [Comic Shanns](https://github.com/shannpersand/comic-shanns).

## Usage
Build the font (see below), then install `fonts/ComicCaret-Regular.otf` or
`fonts/ComicCaret-Regular.ttf` like any other font. For what changed between releases, see
[CHANGELOG.md](CHANGELOG.md).

## Ligatures

Comic Caret joins common coding sequences into one symbol. Every character still takes its
own cell, so columns line up and the cursor moves one character at a time.

- Arrows of any length: `->` `<-` `<->` `=>` `<==` `<=>` `--->` `<====>`
- Continuous lines of any length: `==` `--` `__` `##` `~~`
- `!=` `!==` as ≠ ≢, `<=` `>=` as ⩽ ⩾, and `:=` with the colon centred on the `=`
- `|>` `<|` as triangles
- Pairs pulled together: `::` `...` `&&` `++` `//` `/*` `*/` `<<` `>>` `??` `||`

Sequences that run into other operators stay as separate characters, for example `->>`,
`<<-`, `==<`, `<<=` or `https://`.

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

## Editing and Building

The source of the font is in `src/ComicCaret-Regular.sfd`. You can open it
with FontForge and export it to whatever format you want.

You can also use the script `build.sh` to build the font from the command line.
It will generate the ttf and otf versions in `fonts`.

Make sure that `fontforge` is installed and in your path. Then run `./build.sh`

```
$ ./build.sh
```

To also build [Nerd Fonts](https://www.nerdfonts.com/) patched copies, pass `--nerd`.
The script downloads a pinned version of the Nerd Fonts patcher on first use (needs
`curl` and `unzip`) and writes an otf and a ttf version to `build/nerd/`, which already
holds prebuilt copies of ComicCaret Nerd Font. Install only one of the two, since they
share a font name:

```
$ ./build.sh --nerd                # ComicCaret Nerd Font: icons overhang the next cell
$ ./build.sh --nerd=default,mono   # also ComicCaret Nerd Font Mono: icons fit one cell
```

The ligatures are generated. Don't edit their glyphs (`LIG`, `*.sta`, `*.liga` and the
like) in FontForge: change `tools/add_ligatures.py` or `src/ligatures.fea`, then run
`python3 tools/add_ligatures.py` and `./build.sh`.

## What does it look like?
Like if someone made a version of Comic Sans that is monospaced.

![image 1](https://user-images.githubusercontent.com/4615568/44279591-c9909780-a206-11e8-9e1d-40db6d6db77e.png)
![image 2](https://user-images.githubusercontent.com/4615568/44279592-ca292e00-a206-11e8-9278-4a7566425c0c.png)
![image](https://user-images.githubusercontent.com/4615568/44279593-ca292e00-a206-11e8-9b25-a4533b50d471.png)

## What's in it?
`ABCDEFGHIJKLMNOPQRSTUVWXYZ`

`abcdefghijklmnopqrstuvwxyz`

`1234567890`

`` `~!@#$%^&*()-—_+=[]{}\|;:'",.<>/? ``

- Some diacritics.
- Some math glyphs.
- Box drawing characters.
- Braille characters.

---
### I need help with it...
File an issue, we'll see.

### License
It is licensed under the MIT License.
