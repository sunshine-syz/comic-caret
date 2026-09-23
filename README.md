# What it is

Are you the kind of person that uses Comic Sans in presentations? Do you lie awake every night dreaming about a world where you could write your code in Comic Sans where it looks just as beautiful as on your dear presentations? Wait no more! I present to you **Comic Caret**! The Comic Sans inspired monospaced font that's coming to a terminal or editor near you!

Comic Caret is a fork of [Comic Shanns Mono](https://github.com/jesusmgg/comic-shanns-mono) by Jesús González, which grew out of Shannon Miwa's [Comic Shanns](https://github.com/shannpersand/comic-shanns).

## Usage
Build the font (see below), then install `fonts/ComicCaret-Regular.otf` or
`fonts/ComicCaret-Regular.ttf` like any other font. For what changed between releases, see
[CHANGELOG.md](CHANGELOG.md).

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
