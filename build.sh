#!/bin/bash
# Build the fonts from the SFD, optionally Nerd Fonts patched copies and release zips.
# See usage().
# Written for macOS's bash 3.2: no associative arrays, and no expanding empty arrays under -u.
set -euo pipefail
cd "$(dirname "$0")"

SOURCES="src/ComicCaret-Regular.sfd src/ComicCaret-Italic.sfd src/ComicCaret-Bold.sfd"
OUT_DIR=fonts
NERD_OUT=build/nerd
DIST=dist

# Pinned so patched output changes only when we bump it on purpose. When bumping, update
# both lines; a checksum mismatch prints the new hash.
NERD_FONTS_VERSION=v3.5.1
NERD_FONTS_SHA256=42bcb32145499a35732274c7fc48deb434ad0d2e0e118f98527c1479c6fa251a
PATCHER_DIR=build/cache/FontPatcher-$NERD_FONTS_VERSION

usage() {
  cat <<EOF
Usage: ./build.sh [--nerd[=VARIANTS] | --release]

Builds $OUT_DIR/ComicCaret-{Regular,Italic,Bold}.{otf,ttf} from $SOURCES.

  --nerd[=VARIANTS]  Also patch every built font with Nerd Fonts $NERD_FONTS_VERSION into $NERD_OUT/.
                     VARIANTS is a comma-separated list of:
                       default  icons overhang into the next cell (default)
                       mono     icons fit one cell; every glyph stays 550 wide
                       propo    icons keep their own advance widths (not monospaced)
  --release          From a clean checkout, build the fonts and the default Nerd Font
                     edition, and zip them into $DIST/ for a GitHub release.
EOF
}

# Prints the font-patcher flag for a variant; fails for an unknown one.
nerd_flag() {
  case $1 in
    mono) echo --mono ;;
    default) echo ;;
    propo) echo --variable-width-glyphs ;;
    *) return 1 ;;
  esac
}

fetch_patcher() {
  [[ -f $PATCHER_DIR/font-patcher ]] && return
  local zip=$PATCHER_DIR.zip actual
  mkdir -p "$(dirname "$PATCHER_DIR")"
  curl -fsSL -o "$zip" \
    "https://github.com/ryanoasis/nerd-fonts/releases/download/$NERD_FONTS_VERSION/FontPatcher.zip"
  actual=$(shasum -a 256 "$zip" | cut -d' ' -f1)
  if [[ $actual != "$NERD_FONTS_SHA256" ]]; then
    echo "FontPatcher.zip checksum mismatch: expected $NERD_FONTS_SHA256, got $actual" >&2
    rm -f "$zip"
    exit 1
  fi
  # Extract to a temp dir so an interrupted unzip never passes for a cached patcher.
  rm -rf "$PATCHER_DIR.tmp"
  unzip -q "$zip" -d "$PATCHER_DIR.tmp"
  mv "$PATCHER_DIR.tmp" "$PATCHER_DIR"
  rm -f "$zip"
}

# The icons keep their own licenses (CC BY, OFL, Apache, MIT), which LICENSE.md doesn't cover.
# Writes the patcher's table of icon sets, then the license texts it ships.
write_icon_licenses() {
  local glyphs=$PATCHER_DIR/src/glyphs table dir license
  table=$(awk '/^## /{on = ($0 == "## Icon sets"); next} on' "$glyphs/README.md")
  if [[ $table != *"| license"* ]]; then
    echo "No icon set table in $glyphs/README.md; update write_icon_licenses" >&2
    exit 1
  fi
  {
    cat <<EOF
Icons in ComicCaret Nerd Font

The Nerd Fonts $NERD_FONTS_VERSION font patcher (https://github.com/ryanoasis/nerd-fonts)
added these icons. LICENSE.md covers Comic Caret's own glyphs; each icon set below keeps
its own license. The license texts that come with the patcher follow the table.
$table
EOF
    for dir in "$glyphs"/*/; do
      for license in "$dir"LICENSE* "$dir"OFL.txt; do
        [[ -f $license ]] || continue
        printf '\n\n==== %s ====\n\n' "${license#"$glyphs"/}"
        # Codicons' license starts with a byte-order mark and has CRLF line ends.
        sed $'1s/^\xef\xbb\xbf//; s/\r$//' "$license"
      done
    done
  } >"$1"
}

nerd_variants=
release=
for arg in "$@"; do
  case $arg in
    --nerd) nerd_variants=default ;;
    --nerd=?*) nerd_variants=${arg#--nerd=} ;;
    --release) release=1 ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

if [[ -n $release ]]; then
  if [[ -n $nerd_variants ]]; then
    echo "--release builds its own Nerd Fonts variants; drop --nerd" >&2
    exit 2
  fi
  # The zips are named after the SFD's version, so they must be built from a commit.
  dirty=$(git status --porcelain)
  if [[ -n $dirty ]]; then
    echo "--release needs a clean checkout, but git status found:" >&2
    echo "$dirty" >&2
    exit 1
  fi
  nerd_variants=default
  # Start empty so fonts and variants from earlier builds don't end up in the zips: fonts/ is
  # gitignored, so a stale file there passes the clean-checkout check.
  rm -rf "$OUT_DIR" "$NERD_OUT" "$DIST"
fi

# Reject bad variants before the slow steps.
if [[ -n $nerd_variants ]]; then
  IFS=, read -ra variants <<<"$nerd_variants"
  for variant in "${variants[@]}"; do
    if ! nerd_flag "$variant" >/dev/null; then
      echo "Unknown Nerd Fonts variant: $variant" >&2
      usage >&2
      exit 2
    fi
  done
fi

mkdir -p "$OUT_DIR"
# tools/generate.py stamps head.modified from SOURCE_DATE_EPOCH, or from the time now without
# it. Use the last commit's time, so building the same commit on another day gives the same
# bytes. HEAD rather than the SFD's last commit, because a shallow clone (the CI default)
# can't see the latter. Outside a git checkout, such as a source archive, take one time for
# the whole build: otherwise each process takes its own, and the formats disagree.
if [[ -z ${SOURCE_DATE_EPOCH:-} ]]; then
  epoch=$(git log -1 --format=%ct 2>/dev/null) || epoch=
  export SOURCE_DATE_EPOCH=${epoch:-$(date +%s)}
fi
# One process per format: generating the OTF first alters the in-memory outlines, so a
# TTF generated after it in the same session gets a different glyf table.
for source in $SOURCES; do
  out=$OUT_DIR/$(basename "$source" .sfd)
  for ext in otf ttf; do
    fontforge -quiet -script tools/generate.py "$source" "$out.$ext"
  done
done

if [[ -n $nerd_variants ]]; then
  fetch_patcher
  # Start empty so a variant or font from an earlier run can't pass for a fresh one.
  rm -rf "$NERD_OUT"
  mkdir -p "$NERD_OUT"
  for variant in "${variants[@]}"; do
    flag=$(nerd_flag "$variant")
    # The patcher writes the input's format, so patching each build keeps the OTF's cubic
    # outlines instead of converting the TTF.
    for font in "$OUT_DIR"/ComicCaret-*.otf "$OUT_DIR"/ComicCaret-*.ttf; do
      # --careful keeps every glyph the font has: without it --complete replaces the Braille
      # and the Powerline symbols with the patcher's own. FontForge prints ~100 name-vs-codepoint notes while loading
      # the icon fonts. Drop them so the patcher's own warnings stay visible; pipefail still
      # reports a patcher failure.
      fontforge -quiet -script "$PATCHER_DIR/font-patcher" --complete --careful ${flag:+"$flag"} \
        --quiet --no-progressbars --outputdir "$NERD_OUT" "$font" 2>&1 |
        { grep -vE '^(The glyph named .* is mapped to|But its name indicates it should be mapped to) U\+' || true; }
    done
  done
  # FontForge, which the patcher saves with, gives the TTFs' combining marks a cell's advance.
  # Not in the Mono variant, where the patcher gives every glyph one advance on purpose.
  for font in "$NERD_OUT"/*.ttf; do
    [[ $font == *NerdFontMono-* ]] || python3 tools/mark_advances.py "$font"
  done
  write_icon_licenses "$NERD_OUT/ICON-LICENSES.txt"
fi

if [[ -n $release ]]; then
  version=$(sed -n 's/^Version: //p' "${SOURCES%% *}")
  mkdir -p "$DIST"
  # -j stores bare file names and -X drops macOS extended attributes.
  zip -qjX "$DIST/ComicCaret-$version.zip" "$OUT_DIR"/ComicCaret-*.otf "$OUT_DIR"/ComicCaret-*.ttf LICENSE.md
  zip -qjX "$DIST/ComicCaretNerdFont-$version.zip" "$NERD_OUT"/* LICENSE.md
  echo "Wrote $DIST/ComicCaret-$version.zip and $DIST/ComicCaretNerdFont-$version.zip"
fi
