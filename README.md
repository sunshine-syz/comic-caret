# What it is

Are you the kind of person that uses Comic Sans in presentations? Do you lie awake every night dreaming about a world where you could write your code in Comic Sans where it looks just as beautiful as on your dear presentations? Wait no more! I present to you **Comic Caret**! The Comic Sans inspired monospaced font that's coming to a terminal or editor near you!

Comic Caret is a fork of [Comic Shanns Mono](https://github.com/jesusmgg/comic-shanns-mono) by Jesús González, which grew out of Shannon Miwa's [Comic Shanns](https://github.com/shannpersand/comic-shanns).

## Changelog

### Update 2026-09 (v2.0.0)
- Renamed the font to **Comic Caret** (files `ComicCaret-Regular.{otf,ttf}`), so it no longer shares a family name with Comic Shanns Mono and both can be installed side by side. Update your editor and terminal font settings to the new name.
- The family name no longer ends in "-Regular", and the font now reports its real version (it said 1.3.0, or 0 in the `head` table).
- `./build.sh --nerd` builds a Nerd Fonts patched copy, "ComicCaret Nerd Font Mono".

### Update 2023-03 (v1.3.0)
- Added aditional characters, like ƿ and ∃.

### Update 2023-02
- Added Braille characters (⢩ ⢪ ⢫ ⢬ ⢯ ⢿ ⣁ ⣂ ⣃ ⣇ ⠿ ⠾ ⠪⠘), usually used for progress indicators in terminals.

### Update 2023-01
- Added simple box drawing characters.
- Removed obsolete versions. Updating the Condensed version is still in consideration.
- Completely separating this fork from the original from now on.

### Update 2022
- Check the version in the mono folder.
- This version has fixed glyphs so that all of them are properly monospaced now.
- Also added a more condensed version.

### Update 2020
- Added terrible accents
- Some math characters
- Adjusted horizontal metrics
- otf and ttf version

## Usage
You can download it and install it like any other font.

## Editing and Building

The source of the font is in `src/ComicCaret-Regular.sfd`. You can open it
with FontForge and export it to whatever format you want.

You can also use the script `build.sh` to build the font from the command line.
It will generate the ttf and otf versions in `fonts`.

Make sure that `fontforge` is installed and in your path. Then run `./build.sh`

```
$ ./build.sh
```

To also build a [Nerd Fonts](https://www.nerdfonts.com/) patched copy, pass `--nerd`.
The script downloads a pinned version of the Nerd Fonts patcher on first use (needs
`curl` and `unzip`) and writes the result to `build/nerd/`:

```
$ ./build.sh --nerd                # Nerd Font Mono: icons fit one cell
$ ./build.sh --nerd=mono,default   # also the variant whose icons overhang the next cell
```

## What does it look like?
Like if someone made a version of Comic Sans that is monospaced.

![image 1](https://user-images.githubusercontent.com/4615568/44279591-c9909780-a206-11e8-9e1d-40db6d6db77e.png)
![image 2](https://user-images.githubusercontent.com/4615568/44279592-ca292e00-a206-11e8-9278-4a7566425c0c.png)
![image](https://user-images.githubusercontent.com/4615568/44279593-ca292e00-a206-11e8-9b25-a4533b50d471.png)

## What's in it?
`ABCDEFGHIJKLMNOPQRSTUVWXYZ`

`abcdefghijklmnopqrstuvwxyz`

`1234567890`

`~!@#$%^&*()-—+=;:"'<>,.?/\|[]{}?`

- Some diacritics.
- Some math glyphs.
- Box drawing characters.
- Braille characters.

---
### I need help with it...
File an issue, we'll see.

### License
It is licensed under the MIT License.
