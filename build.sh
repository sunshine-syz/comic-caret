#!/bin/bash
# Build the fonts from the SFD, and optionally Nerd Fonts patched copies. See usage().
# Written for macOS's bash 3.2: no associative arrays, and no expanding empty arrays under -u.
set -euo pipefail
cd "$(dirname "$0")"

SOURCE=src/ComicCaret-Regular.sfd
OUT=fonts/ComicCaret-Regular
NERD_OUT=build/nerd

# Pinned so patched output changes only when we bump it on purpose. When bumping, update
# both lines; a checksum mismatch prints the new hash.
NERD_FONTS_VERSION=v3.5.1
NERD_FONTS_SHA256=42bcb32145499a35732274c7fc48deb434ad0d2e0e118f98527c1479c6fa251a
PATCHER_DIR=build/cache/FontPatcher-$NERD_FONTS_VERSION

usage() {
  cat <<EOF
Usage: ./build.sh [--nerd[=VARIANTS]]

Builds $OUT.{otf,ttf} from $SOURCE.

  --nerd[=VARIANTS]  Also patch the TTF with Nerd Fonts $NERD_FONTS_VERSION into $NERD_OUT/.
                     VARIANTS is a comma-separated list of:
                       mono     icons fit one cell; every glyph stays 550 wide (default)
                       default  icons overhang into the next cell
                       propo    icons keep their own advance widths (not monospaced)
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

nerd_variants=
for arg in "$@"; do
  case $arg in
    --nerd) nerd_variants=mono ;;
    --nerd=?*) nerd_variants=${arg#--nerd=} ;;
    -h | --help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

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

mkdir -p "$(dirname "$OUT")"
# One process per format: generating the OTF first alters the in-memory outlines, so a
# TTF generated after it in the same session gets a different glyf table.
for ext in otf ttf; do
  fontforge -quiet -lang=ff -c 'Open($1); Generate($2)' "$SOURCE" "$OUT.$ext"
done

if [[ -n $nerd_variants ]]; then
  fetch_patcher
  mkdir -p "$NERD_OUT"
  for variant in "${variants[@]}"; do
    flag=$(nerd_flag "$variant")
    # FontForge prints ~100 name-vs-codepoint notes while loading the icon fonts. Drop them
    # so the patcher's own warnings stay visible; pipefail still reports a patcher failure.
    fontforge -quiet -script "$PATCHER_DIR/font-patcher" --complete ${flag:+"$flag"} \
      --quiet --no-progressbars --outputdir "$NERD_OUT" "$OUT.ttf" 2>&1 |
      { grep -vE '^(The glyph named .* is mapped to|But its name indicates it should be mapped to) U\+' || true; }
  done
fi
