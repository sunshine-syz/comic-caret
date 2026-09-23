#!/bin/bash
# Render the ligature sample with calt on and off at 16, 24 and 64 px, for checking shapes
# and seams by eye. Images go to OUTDIR and are not committed.
# Usage: tools/render_sample.sh OUTDIR [FONT]
set -euo pipefail

out=${1:?usage: tools/render_sample.sh OUTDIR [FONT]}
font=${2:-$(dirname "$0")/../fonts/ComicCaret-Regular.ttf}

sample='-> ---> <- <---- <-> <----> => ===> <== <=> <===>
== ===== -- ----- __ ____ ## ##### ~~ ~~~ ~~~~~
!= !== <= >= := |> <| || :: ... && ++ // /* */ << >> ??
if (a >= b && c != d) { x := y |> f; } // i-- x<-1
plain: ->> <<- >== ==< =>= <<<<< //// a::<T> https://x'

mkdir -p "$out"
for size in 16 24 64; do
  for calt in on off; do
    flag=+calt
    [[ $calt == off ]] && flag=-calt
    # --text= form: the sample starts with '-', which would read as an option.
    hb-view "$font" --font-size="$size" --margin=8 --features="$flag" \
      --output-file="$out/sample-$size-$calt.png" --text="$sample"
  done
done
echo "Wrote $out/sample-{16,24,64}-{on,off}.png"
